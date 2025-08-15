"""
Intelligent chunk deduplication service with content-based similarity detection.
Implements requirements 10.1, 10.2, 10.4 for task 11.1.
"""
import asyncio
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
import re

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, func, text, desc
from sqlalchemy.dialects.postgresql import insert

from ..core.database import get_db
from ..models.document import Document, DocumentChunk
from ..models.bot import Bot
from ..services.vector_store import VectorService

logger = logging.getLogger(__name__)


@dataclass
class ChunkSimilarity:
    """Represents similarity between two chunks."""
    chunk1_id: UUID
    chunk2_id: UUID
    similarity_score: float
    similarity_type: str  # 'exact', 'high', 'medium', 'low'
    content_overlap: float
    metadata_compatibility: bool


@dataclass
class DeduplicationDecision:
    """Represents a deduplication decision with audit information."""
    decision_id: str
    timestamp: datetime
    action: str  # 'merge', 'preserve', 'remove'
    primary_chunk_id: UUID
    duplicate_chunk_ids: List[UUID]
    similarity_score: float
    reason: str
    preserved_metadata: Dict[str, Any]
    source_attribution: List[Dict[str, Any]]


@dataclass
class DeduplicationResult:
    """Result of deduplication operation."""
    success: bool
    processed_chunks: int
    merged_chunks: int
    removed_chunks: int
    preserved_chunks: int
    decisions: List[DeduplicationDecision]
    audit_trail: List[Dict[str, Any]]
    error: Optional[str] = None


@dataclass
class DeduplicationConfig:
    """Configuration for deduplication behavior."""
    exact_match_threshold: float = 1.0
    high_similarity_threshold: float = 0.95
    medium_similarity_threshold: float = 0.85
    low_similarity_threshold: float = 0.70
    enable_semantic_similarity: bool = True
    preserve_source_attribution: bool = True
    conservative_preservation: bool = True
    max_merge_group_size: int = 10
    content_overlap_threshold: float = 0.80


class ChunkDeduplicationService:
    """
    Intelligent chunk deduplication service that detects content similarity
    and merges chunks while preserving metadata and source attribution.
    """
    
    def __init__(self, db: Session, vector_service: VectorService = None):
        """
        Initialize chunk deduplication service.
        
        Args:
            db: Database session
            vector_service: Vector service instance
        """
        self.db = db
        self.vector_service = vector_service or VectorService()
        self.config = DeduplicationConfig()
        
    def _calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA-256 hash of normalized chunk content.
        
        Args:
            content: Chunk content
            
        Returns:
            Content hash string
        """
        # Normalize content by removing extra whitespace and converting to lowercase
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using sequence matching.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize texts
        norm_text1 = re.sub(r'\s+', ' ', text1.strip().lower())
        norm_text2 = re.sub(r'\s+', ' ', text2.strip().lower())
        
        # Calculate sequence similarity
        matcher = SequenceMatcher(None, norm_text1, norm_text2)
        return matcher.ratio()
    
    def _calculate_content_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate content overlap percentage between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Overlap percentage between 0.0 and 1.0
        """
        # Split into words and create sets
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _assess_metadata_compatibility(
        self, 
        metadata1: Dict[str, Any], 
        metadata2: Dict[str, Any]
    ) -> bool:
        """
        Assess whether two chunks' metadata are compatible for merging.
        
        Args:
            metadata1: First chunk metadata
            metadata2: Second chunk metadata
            
        Returns:
            True if metadata are compatible for merging
        """
        # Check for conflicting critical metadata
        critical_fields = ['page_number', 'section', 'document_type']
        
        for field in critical_fields:
            val1 = metadata1.get(field)
            val2 = metadata2.get(field)
            
            # If both have values and they're different, not compatible
            if val1 is not None and val2 is not None and val1 != val2:
                return False
        
        return True
    
    async def detect_chunk_similarities(
        self,
        bot_id: UUID,
        chunk_ids: Optional[List[UUID]] = None,
        similarity_threshold: float = None
    ) -> List[ChunkSimilarity]:
        """
        Detect similarities between chunks based on content analysis.
        
        Args:
            bot_id: Bot identifier
            chunk_ids: Optional list of specific chunk IDs to analyze
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of detected chunk similarities
        """
        try:
            threshold = similarity_threshold or self.config.low_similarity_threshold
            
            # Query chunks to analyze
            query = self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id)
            
            if chunk_ids:
                query = query.filter(DocumentChunk.id.in_(chunk_ids))
            
            chunks = query.all()
            
            if len(chunks) < 2:
                return []
            
            similarities = []
            
            # Compare each pair of chunks
            for i, chunk1 in enumerate(chunks):
                for chunk2 in chunks[i + 1:]:
                    similarity = await self._analyze_chunk_pair(chunk1, chunk2)
                    
                    if similarity.similarity_score >= threshold:
                        similarities.append(similarity)
            
            # Sort by similarity score (highest first)
            similarities.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(
                f"Detected {len(similarities)} chunk similarities for bot {bot_id} "
                f"above threshold {threshold}"
            )
            
            return similarities
            
        except Exception as e:
            logger.error(f"Error detecting chunk similarities for bot {bot_id}: {e}")
            return []
    
    async def _analyze_chunk_pair(
        self, 
        chunk1: DocumentChunk, 
        chunk2: DocumentChunk
    ) -> ChunkSimilarity:
        """
        Analyze similarity between a pair of chunks.
        
        Args:
            chunk1: First chunk
            chunk2: Second chunk
            
        Returns:
            ChunkSimilarity object with analysis results
        """
        # Calculate text similarity
        text_similarity = self._calculate_text_similarity(chunk1.content, chunk2.content)
        
        # Calculate content overlap
        content_overlap = self._calculate_content_overlap(chunk1.content, chunk2.content)
        
        # Assess metadata compatibility
        metadata1 = chunk1.chunk_metadata or {}
        metadata2 = chunk2.chunk_metadata or {}
        metadata_compatible = self._assess_metadata_compatibility(metadata1, metadata2)
        
        # Determine similarity type
        if text_similarity >= self.config.exact_match_threshold:
            similarity_type = 'exact'
        elif text_similarity >= self.config.high_similarity_threshold:
            similarity_type = 'high'
        elif text_similarity >= self.config.medium_similarity_threshold:
            similarity_type = 'medium'
        else:
            similarity_type = 'low'
        
        return ChunkSimilarity(
            chunk1_id=chunk1.id,
            chunk2_id=chunk2.id,
            similarity_score=text_similarity,
            similarity_type=similarity_type,
            content_overlap=content_overlap,
            metadata_compatibility=metadata_compatible
        )
    
    def _merge_chunk_metadata(
        self,
        primary_metadata: Dict[str, Any],
        duplicate_metadatas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge metadata from multiple chunks while preserving important information.
        
        Args:
            primary_metadata: Metadata from the primary chunk
            duplicate_metadatas: List of metadata from duplicate chunks
            
        Returns:
            Merged metadata dictionary
        """
        merged = primary_metadata.copy()
        
        # Collect all unique values for each field
        all_metadatas = [primary_metadata] + duplicate_metadatas
        
        for metadata in duplicate_metadatas:
            for key, value in metadata.items():
                if key not in merged:
                    merged[key] = value
                elif merged[key] != value:
                    # Handle conflicting values by creating lists
                    if not isinstance(merged[key], list):
                        merged[key] = [merged[key]]
                    if value not in merged[key]:
                        merged[key].append(value)
        
        # Add deduplication metadata
        merged['_deduplication'] = {
            'merged_at': datetime.utcnow().isoformat(),
            'source_count': len(all_metadatas),
            'original_sources': [
                {
                    'metadata': metadata,
                    'merged_fields': list(metadata.keys())
                }
                for metadata in all_metadatas
            ]
        }
        
        return merged
    
    def _create_source_attribution(
        self,
        primary_chunk: DocumentChunk,
        duplicate_chunks: List[DocumentChunk]
    ) -> List[Dict[str, Any]]:
        """
        Create source attribution for merged chunks.
        
        Args:
            primary_chunk: Primary chunk being preserved
            duplicate_chunks: List of duplicate chunks being merged
            
        Returns:
            List of source attribution records
        """
        all_chunks = [primary_chunk] + duplicate_chunks
        
        attribution = []
        for chunk in all_chunks:
            source_info = {
                'chunk_id': str(chunk.id),
                'document_id': str(chunk.document_id),
                'chunk_index': chunk.chunk_index,
                'created_at': chunk.created_at.isoformat(),
                'content_length': len(chunk.content),
                'is_primary': chunk.id == primary_chunk.id
            }
            
            # Add document information if available
            if chunk.document:
                source_info.update({
                    'document_filename': chunk.document.filename,
                    'document_created_at': chunk.document.created_at.isoformat()
                })
            
            attribution.append(source_info)
        
        return attribution
    
    async def deduplicate_chunks(
        self,
        bot_id: UUID,
        chunk_ids: Optional[List[UUID]] = None,
        config: Optional[DeduplicationConfig] = None
    ) -> DeduplicationResult:
        """
        Perform intelligent deduplication of chunks with metadata merging.
        
        Args:
            bot_id: Bot identifier
            chunk_ids: Optional list of specific chunk IDs to deduplicate
            config: Optional deduplication configuration
            
        Returns:
            DeduplicationResult with operation details
        """
        try:
            if config:
                self.config = config
            
            # Detect similarities
            similarities = await self.detect_chunk_similarities(
                bot_id=bot_id,
                chunk_ids=chunk_ids,
                similarity_threshold=self.config.high_similarity_threshold
            )
            
            if not similarities:
                return DeduplicationResult(
                    success=True,
                    processed_chunks=0,
                    merged_chunks=0,
                    removed_chunks=0,
                    preserved_chunks=0,
                    decisions=[],
                    audit_trail=[]
                )
            
            # Group similar chunks
            similarity_groups = self._group_similar_chunks(similarities)
            
            decisions = []
            audit_trail = []
            merged_count = 0
            removed_count = 0
            preserved_count = 0
            
            # Process each similarity group
            for group in similarity_groups:
                decision = await self._process_similarity_group(bot_id, group)
                decisions.append(decision)
                
                # Update counters
                if decision.action == 'merge':
                    merged_count += 1
                    removed_count += len(decision.duplicate_chunk_ids)
                elif decision.action == 'preserve':
                    preserved_count += len(decision.duplicate_chunk_ids) + 1
                
                # Add to audit trail
                audit_trail.append({
                    'decision_id': decision.decision_id,
                    'timestamp': decision.timestamp.isoformat(),
                    'action': decision.action,
                    'chunk_count': len(decision.duplicate_chunk_ids) + 1,
                    'similarity_score': decision.similarity_score,
                    'reason': decision.reason
                })
            
            # Commit all changes
            self.db.commit()
            
            result = DeduplicationResult(
                success=True,
                processed_chunks=len(set(
                    chunk_id for group in similarity_groups 
                    for chunk_id in group
                )),
                merged_chunks=merged_count,
                removed_chunks=removed_count,
                preserved_chunks=preserved_count,
                decisions=decisions,
                audit_trail=audit_trail
            )
            
            logger.info(
                f"Deduplication completed for bot {bot_id}: "
                f"merged {merged_count}, removed {removed_count}, "
                f"preserved {preserved_count} chunks"
            )
            
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during chunk deduplication for bot {bot_id}: {e}")
            return DeduplicationResult(
                success=False,
                processed_chunks=0,
                merged_chunks=0,
                removed_chunks=0,
                preserved_chunks=0,
                decisions=[],
                audit_trail=[],
                error=str(e)
            )
    
    def _group_similar_chunks(
        self, 
        similarities: List[ChunkSimilarity]
    ) -> List[List[UUID]]:
        """
        Group similar chunks into deduplication groups.
        
        Args:
            similarities: List of chunk similarities
            
        Returns:
            List of chunk ID groups for deduplication
        """
        # Build adjacency graph of similar chunks
        chunk_connections = {}
        
        for similarity in similarities:
            chunk1_id = similarity.chunk1_id
            chunk2_id = similarity.chunk2_id
            
            if chunk1_id not in chunk_connections:
                chunk_connections[chunk1_id] = set()
            if chunk2_id not in chunk_connections:
                chunk_connections[chunk2_id] = set()
            
            chunk_connections[chunk1_id].add(chunk2_id)
            chunk_connections[chunk2_id].add(chunk1_id)
        
        # Find connected components (groups of similar chunks)
        visited = set()
        groups = []
        
        for chunk_id in chunk_connections:
            if chunk_id not in visited:
                group = self._find_connected_group(chunk_id, chunk_connections, visited)
                if len(group) > 1:  # Only include groups with multiple chunks
                    groups.append(list(group))
        
        return groups
    
    def _find_connected_group(
        self,
        start_chunk: UUID,
        connections: Dict[UUID, Set[UUID]],
        visited: Set[UUID]
    ) -> Set[UUID]:
        """
        Find all chunks connected to the starting chunk.
        
        Args:
            start_chunk: Starting chunk ID
            connections: Adjacency graph of chunk connections
            visited: Set of already visited chunks
            
        Returns:
            Set of connected chunk IDs
        """
        group = set()
        stack = [start_chunk]
        
        while stack:
            chunk_id = stack.pop()
            if chunk_id in visited:
                continue
            
            visited.add(chunk_id)
            group.add(chunk_id)
            
            # Add connected chunks to stack
            for connected_chunk in connections.get(chunk_id, set()):
                if connected_chunk not in visited:
                    stack.append(connected_chunk)
        
        return group
    
    async def _process_similarity_group(
        self,
        bot_id: UUID,
        chunk_ids: List[UUID]
    ) -> DeduplicationDecision:
        """
        Process a group of similar chunks and make deduplication decision.
        
        Args:
            bot_id: Bot identifier
            chunk_ids: List of similar chunk IDs
            
        Returns:
            DeduplicationDecision with action taken
        """
        # Get chunk data
        chunks = self.db.query(DocumentChunk).filter(
            and_(
                DocumentChunk.bot_id == bot_id,
                DocumentChunk.id.in_(chunk_ids)
            )
        ).all()
        
        if len(chunks) < 2:
            return self._create_preserve_decision(chunks[0] if chunks else None, [])
        
        # Sort chunks by creation date (oldest first) to prefer original content
        chunks.sort(key=lambda x: x.created_at)
        
        # Select primary chunk (oldest, longest content, or best metadata)
        primary_chunk = self._select_primary_chunk(chunks)
        duplicate_chunks = [c for c in chunks if c.id != primary_chunk.id]
        
        # Check if we should merge or preserve based on conservative settings
        should_merge = await self._should_merge_chunks(primary_chunk, duplicate_chunks)
        
        if should_merge:
            return await self._merge_chunks(primary_chunk, duplicate_chunks)
        else:
            return self._create_preserve_decision(primary_chunk, duplicate_chunks)
    
    def _select_primary_chunk(self, chunks: List[DocumentChunk]) -> DocumentChunk:
        """
        Select the primary chunk from a group of similar chunks.
        
        Args:
            chunks: List of similar chunks
            
        Returns:
            Selected primary chunk
        """
        # Scoring criteria: creation date (older is better), content length, metadata richness
        def score_chunk(chunk):
            age_score = 1.0  # Older chunks get higher score
            length_score = len(chunk.content) / 1000.0  # Longer content gets higher score
            metadata_score = len(chunk.chunk_metadata or {}) / 10.0  # More metadata gets higher score
            
            return age_score + length_score + metadata_score
        
        return max(chunks, key=score_chunk)
    
    async def _should_merge_chunks(
        self,
        primary_chunk: DocumentChunk,
        duplicate_chunks: List[DocumentChunk]
    ) -> bool:
        """
        Determine whether chunks should be merged based on conservative criteria.
        
        Args:
            primary_chunk: Primary chunk
            duplicate_chunks: List of duplicate chunks
            
        Returns:
            True if chunks should be merged
        """
        # Conservative preservation approach - only merge if very confident
        if self.config.conservative_preservation:
            # Check if all chunks have very high similarity
            for duplicate in duplicate_chunks:
                similarity = self._calculate_text_similarity(
                    primary_chunk.content, 
                    duplicate.content
                )
                if similarity < self.config.high_similarity_threshold:
                    return False
            
            # Check metadata compatibility
            primary_metadata = primary_chunk.chunk_metadata or {}
            for duplicate in duplicate_chunks:
                duplicate_metadata = duplicate.chunk_metadata or {}
                if not self._assess_metadata_compatibility(primary_metadata, duplicate_metadata):
                    return False
        
        return True
    
    async def _merge_chunks(
        self,
        primary_chunk: DocumentChunk,
        duplicate_chunks: List[DocumentChunk]
    ) -> DeduplicationDecision:
        """
        Merge duplicate chunks into the primary chunk.
        
        Args:
            primary_chunk: Primary chunk to preserve
            duplicate_chunks: List of duplicate chunks to merge
            
        Returns:
            DeduplicationDecision with merge details
        """
        decision_id = str(uuid.uuid4())
        
        # Create source attribution
        source_attribution = self._create_source_attribution(primary_chunk, duplicate_chunks)
        
        # Merge metadata
        duplicate_metadatas = [chunk.chunk_metadata or {} for chunk in duplicate_chunks]
        merged_metadata = self._merge_chunk_metadata(
            primary_chunk.chunk_metadata or {},
            duplicate_metadatas
        )
        
        # Update primary chunk with merged metadata
        primary_chunk.chunk_metadata = merged_metadata
        
        # Remove duplicate chunks from database
        duplicate_ids = [chunk.id for chunk in duplicate_chunks]
        self.db.query(DocumentChunk).filter(
            DocumentChunk.id.in_(duplicate_ids)
        ).delete(synchronize_session=False)
        
        # Remove duplicate chunks from vector store
        if duplicate_chunks and self.vector_service:
            embedding_ids = [chunk.embedding_id for chunk in duplicate_chunks if chunk.embedding_id]
            if embedding_ids:
                await self.vector_service.delete_document_chunks(
                    str(primary_chunk.bot_id),
                    embedding_ids
                )
        
        # Calculate average similarity score
        avg_similarity = sum(
            self._calculate_text_similarity(primary_chunk.content, dup.content)
            for dup in duplicate_chunks
        ) / len(duplicate_chunks)
        
        decision = DeduplicationDecision(
            decision_id=decision_id,
            timestamp=datetime.utcnow(),
            action='merge',
            primary_chunk_id=primary_chunk.id,
            duplicate_chunk_ids=duplicate_ids,
            similarity_score=avg_similarity,
            reason=f"Merged {len(duplicate_chunks)} similar chunks with high confidence",
            preserved_metadata=merged_metadata,
            source_attribution=source_attribution
        )
        
        logger.info(
            f"Merged {len(duplicate_chunks)} chunks into primary chunk {primary_chunk.id}"
        )
        
        return decision
    
    def _create_preserve_decision(
        self,
        primary_chunk: Optional[DocumentChunk],
        other_chunks: List[DocumentChunk]
    ) -> DeduplicationDecision:
        """
        Create a preservation decision for ambiguous similarity cases.
        
        Args:
            primary_chunk: Primary chunk (if any)
            other_chunks: Other chunks in the group
            
        Returns:
            DeduplicationDecision with preserve action
        """
        decision_id = str(uuid.uuid4())
        
        if not primary_chunk:
            return DeduplicationDecision(
                decision_id=decision_id,
                timestamp=datetime.utcnow(),
                action='preserve',
                primary_chunk_id=UUID('00000000-0000-0000-0000-000000000000'),
                duplicate_chunk_ids=[],
                similarity_score=0.0,
                reason="No chunks to process",
                preserved_metadata={},
                source_attribution=[]
            )
        
        return DeduplicationDecision(
            decision_id=decision_id,
            timestamp=datetime.utcnow(),
            action='preserve',
            primary_chunk_id=primary_chunk.id,
            duplicate_chunk_ids=[chunk.id for chunk in other_chunks],
            similarity_score=0.0,
            reason="Conservative preservation due to ambiguous similarity",
            preserved_metadata=primary_chunk.chunk_metadata or {},
            source_attribution=self._create_source_attribution(primary_chunk, other_chunks)
        )
    
    async def get_deduplication_statistics(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Get deduplication statistics for a bot's chunks.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Statistics about potential and completed deduplication
        """
        try:
            # Get total chunk count
            total_chunks = self.db.query(func.count(DocumentChunk.id)).filter(
                DocumentChunk.bot_id == bot_id
            ).scalar()
            
            # Detect potential duplicates
            similarities = await self.detect_chunk_similarities(
                bot_id=bot_id,
                similarity_threshold=self.config.medium_similarity_threshold
            )
            
            # Group similarities
            similarity_groups = self._group_similar_chunks(similarities)
            
            # Count chunks with deduplication metadata
            deduplicated_chunks = self.db.query(func.count(DocumentChunk.id)).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    DocumentChunk.chunk_metadata.op('?')('_deduplication')
                )
            ).scalar()
            
            # Calculate statistics
            potential_duplicates = sum(len(group) - 1 for group in similarity_groups)
            
            return {
                'total_chunks': total_chunks or 0,
                'potential_duplicate_groups': len(similarity_groups),
                'potential_duplicate_chunks': potential_duplicates,
                'already_deduplicated_chunks': deduplicated_chunks or 0,
                'deduplication_potential': potential_duplicates / max(total_chunks or 1, 1),
                'similarity_distribution': {
                    'exact': len([s for s in similarities if s.similarity_type == 'exact']),
                    'high': len([s for s in similarities if s.similarity_type == 'high']),
                    'medium': len([s for s in similarities if s.similarity_type == 'medium']),
                    'low': len([s for s in similarities if s.similarity_type == 'low'])
                },
                'recommendations': self._generate_deduplication_recommendations(
                    total_chunks or 0, potential_duplicates, deduplicated_chunks or 0
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting deduplication statistics for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    def _generate_deduplication_recommendations(
        self,
        total_chunks: int,
        potential_duplicates: int,
        already_deduplicated: int
    ) -> List[str]:
        """
        Generate deduplication recommendations based on statistics.
        
        Args:
            total_chunks: Total number of chunks
            potential_duplicates: Number of potential duplicate chunks
            already_deduplicated: Number of already deduplicated chunks
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if potential_duplicates > 0:
            duplicate_percentage = (potential_duplicates / max(total_chunks, 1)) * 100
            
            if duplicate_percentage > 20:
                recommendations.append(
                    f"High duplication detected ({duplicate_percentage:.1f}%). "
                    "Consider running deduplication to improve storage efficiency."
                )
            elif duplicate_percentage > 10:
                recommendations.append(
                    f"Moderate duplication detected ({duplicate_percentage:.1f}%). "
                    "Deduplication may improve retrieval quality."
                )
            else:
                recommendations.append(
                    f"Low duplication detected ({duplicate_percentage:.1f}%). "
                    "Current duplication level is acceptable."
                )
        
        if already_deduplicated > 0:
            recommendations.append(
                f"{already_deduplicated} chunks have been previously deduplicated. "
                "Audit trails are preserved in chunk metadata."
            )
        
        if total_chunks > 1000 and potential_duplicates > 50:
            recommendations.append(
                "Large document collection detected. Consider enabling automatic "
                "deduplication during document processing."
            )
        
        return recommendations