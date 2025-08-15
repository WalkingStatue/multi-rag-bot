"""
Chunk storage optimization and cleanup procedures.
Completes requirements 6.3, 6.5 for task 7.2.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, delete

from ..models.document import Document, DocumentChunk
from ..services.optimized_chunk_storage import OptimizedChunkStorage
from ..services.chunk_metadata_cache import ChunkMetadataCache
from ..services.vector_store import VectorService

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of storage optimization operation."""
    success: bool
    actions_performed: List[str]
    space_saved_bytes: int
    chunks_removed: int
    chunks_optimized: int
    error: Optional[str] = None


@dataclass
class CleanupStats:
    """Statistics from cleanup operations."""
    orphaned_chunks_removed: int
    duplicate_chunks_removed: int
    empty_documents_removed: int
    vector_inconsistencies_fixed: int
    cache_entries_cleaned: int
    total_space_freed_bytes: int


class ChunkStorageOptimizer:
    """
    Service for optimizing chunk storage, performing cleanup, and maintaining data consistency.
    """
    
    def __init__(
        self,
        db: Session,
        storage_service: OptimizedChunkStorage = None,
        cache_service: ChunkMetadataCache = None,
        vector_service: VectorService = None
    ):
        """
        Initialize chunk storage optimizer.
        
        Args:
            db: Database session
            storage_service: Optimized chunk storage service
            cache_service: Chunk metadata cache service
            vector_service: Vector service instance
        """
        self.db = db
        self.storage_service = storage_service or OptimizedChunkStorage(db)
        self.cache_service = cache_service or ChunkMetadataCache(db)
        self.vector_service = vector_service or VectorService()
    
    async def optimize_bot_storage(
        self,
        bot_id: UUID,
        remove_duplicates: bool = True,
        cleanup_orphans: bool = True,
        optimize_cache: bool = True
    ) -> OptimizationResult:
        """
        Perform comprehensive storage optimization for a bot.
        
        Args:
            bot_id: Bot identifier
            remove_duplicates: Whether to remove duplicate chunks
            cleanup_orphans: Whether to clean up orphaned data
            optimize_cache: Whether to optimize cache configuration
            
        Returns:
            OptimizationResult with optimization statistics
        """
        try:
            actions_performed = []
            space_saved = 0
            chunks_removed = 0
            chunks_optimized = 0
            
            logger.info(f"Starting storage optimization for bot {bot_id}")
            
            # 1. Remove duplicate chunks
            if remove_duplicates:
                dedup_result = await self._remove_duplicate_chunks(bot_id)
                if dedup_result['removed_count'] > 0:
                    actions_performed.append(
                        f"Removed {dedup_result['removed_count']} duplicate chunks"
                    )
                    space_saved += dedup_result['space_saved']
                    chunks_removed += dedup_result['removed_count']
            
            # 2. Clean up orphaned data
            if cleanup_orphans:
                orphan_result = await self._cleanup_orphaned_data(bot_id)
                if orphan_result['cleaned_count'] > 0:
                    actions_performed.append(
                        f"Cleaned up {orphan_result['cleaned_count']} orphaned entries"
                    )
                    space_saved += orphan_result['space_saved']
                    chunks_removed += orphan_result['cleaned_count']
            
            # 3. Optimize chunk metadata storage
            metadata_result = await self._optimize_chunk_metadata(bot_id)
            if metadata_result['optimized_count'] > 0:
                actions_performed.append(
                    f"Optimized metadata for {metadata_result['optimized_count']} chunks"
                )
                chunks_optimized += metadata_result['optimized_count']
            
            # 4. Maintain referential integrity
            integrity_result = await self.storage_service.maintain_referential_integrity(bot_id)
            if integrity_result.get('repair_actions'):
                actions_performed.extend(integrity_result['repair_actions'])
            
            # 5. Optimize cache if requested
            if optimize_cache:
                cache_result = await self.cache_service.optimize_cache_for_bot(bot_id)
                if cache_result.get('actions_taken'):
                    actions_performed.extend(cache_result['actions_taken'])
            
            logger.info(
                f"Storage optimization completed for bot {bot_id}: "
                f"{len(actions_performed)} actions, {space_saved} bytes saved"
            )
            
            return OptimizationResult(
                success=True,
                actions_performed=actions_performed,
                space_saved_bytes=space_saved,
                chunks_removed=chunks_removed,
                chunks_optimized=chunks_optimized
            )
            
        except Exception as e:
            logger.error(f"Error optimizing storage for bot {bot_id}: {e}")
            return OptimizationResult(
                success=False,
                actions_performed=[],
                space_saved_bytes=0,
                chunks_removed=0,
                chunks_optimized=0,
                error=str(e)
            )
    
    async def perform_system_cleanup(
        self,
        max_age_days: int = 30,
        cleanup_empty_documents: bool = True,
        cleanup_cache: bool = True
    ) -> CleanupStats:
        """
        Perform system-wide cleanup of old and unused data.
        
        Args:
            max_age_days: Maximum age for cleanup consideration
            cleanup_empty_documents: Whether to remove empty documents
            cleanup_cache: Whether to clean up cache
            
        Returns:
            CleanupStats with cleanup statistics
        """
        try:
            stats = CleanupStats(
                orphaned_chunks_removed=0,
                duplicate_chunks_removed=0,
                empty_documents_removed=0,
                vector_inconsistencies_fixed=0,
                cache_entries_cleaned=0,
                total_space_freed_bytes=0
            )
            
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            # 1. Remove orphaned chunks (chunks without documents)
            orphaned_chunks = self.db.query(DocumentChunk).filter(
                ~DocumentChunk.document_id.in_(
                    self.db.query(Document.id)
                )
            ).all()
            
            for chunk in orphaned_chunks:
                # Remove from vector store
                if chunk.embedding_id:
                    try:
                        await self.vector_service.delete_document_chunks(
                            str(chunk.bot_id), [chunk.embedding_id]
                        )
                    except Exception as e:
                        logger.warning(f"Failed to remove orphaned vector chunk {chunk.embedding_id}: {e}")
                
                # Calculate space saved
                stats.total_space_freed_bytes += len(chunk.content) if chunk.content else 0
                stats.orphaned_chunks_removed += 1
            
            # Delete orphaned chunks from database
            if orphaned_chunks:
                orphaned_ids = [chunk.id for chunk in orphaned_chunks]
                self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(orphaned_ids)
                ).delete(synchronize_session=False)
            
            # 2. Remove empty documents
            if cleanup_empty_documents:
                empty_docs = self.db.query(Document).filter(
                    Document.chunk_count == 0,
                    Document.created_at < cutoff_date
                ).all()
                
                for doc in empty_docs:
                    # Remove file if it exists
                    try:
                        import os
                        if os.path.exists(doc.file_path):
                            os.remove(doc.file_path)
                            stats.total_space_freed_bytes += doc.file_size or 0
                    except Exception as e:
                        logger.warning(f"Failed to remove file {doc.file_path}: {e}")
                    
                    stats.empty_documents_removed += 1
                
                # Delete empty documents
                if empty_docs:
                    empty_doc_ids = [doc.id for doc in empty_docs]
                    self.db.query(Document).filter(
                        Document.id.in_(empty_doc_ids)
                    ).delete(synchronize_session=False)
            
            # 3. Clean up cache
            if cleanup_cache:
                cache_cleaned = await self.cache_service.cleanup_expired_cache()
                stats.cache_entries_cleaned = cache_cleaned
            
            # 4. Fix vector store inconsistencies for all bots
            bots_with_chunks = self.db.query(DocumentChunk.bot_id).distinct().all()
            for (bot_id,) in bots_with_chunks:
                try:
                    integrity_result = await self.storage_service.maintain_referential_integrity(bot_id)
                    if integrity_result.get('repair_actions'):
                        stats.vector_inconsistencies_fixed += len(integrity_result['repair_actions'])
                except Exception as e:
                    logger.warning(f"Failed to fix vector inconsistencies for bot {bot_id}: {e}")
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"System cleanup completed: "
                f"{stats.orphaned_chunks_removed} orphaned chunks, "
                f"{stats.empty_documents_removed} empty documents, "
                f"{stats.cache_entries_cleaned} cache entries cleaned, "
                f"{stats.total_space_freed_bytes} bytes freed"
            )
            
            return stats
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during system cleanup: {e}")
            return CleanupStats(0, 0, 0, 0, 0, 0)
    
    async def analyze_storage_efficiency(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Analyze storage efficiency and provide optimization recommendations.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Storage efficiency analysis and recommendations
        """
        try:
            # Get basic storage statistics
            storage_stats = await self.storage_service.get_storage_statistics(bot_id)
            
            # Get cache statistics
            cache_stats = await self.cache_service.get_cache_statistics()
            
            # Analyze chunk size distribution
            chunk_sizes = self.db.query(
                func.length(DocumentChunk.content).label('size')
            ).filter(DocumentChunk.bot_id == bot_id).all()
            
            sizes = [size[0] for size in chunk_sizes if size[0]]
            
            size_analysis = {
                'min_size': min(sizes) if sizes else 0,
                'max_size': max(sizes) if sizes else 0,
                'avg_size': sum(sizes) / len(sizes) if sizes else 0,
                'median_size': sorted(sizes)[len(sizes) // 2] if sizes else 0
            }
            
            # Check for potential optimizations
            recommendations = []
            
            # Size-based recommendations
            if size_analysis['max_size'] > 5000:
                recommendations.append(
                    "Some chunks are very large (>5KB). Consider reducing chunk size for better retrieval."
                )
            
            if size_analysis['min_size'] < 100:
                recommendations.append(
                    "Some chunks are very small (<100 chars). Consider increasing chunk size or merging small chunks."
                )
            
            # Duplication recommendations
            if storage_stats.get('duplicate_chunks', 0) > 0:
                recommendations.append(
                    f"Found {storage_stats['duplicate_chunks']} duplicate chunks. Run deduplication to save space."
                )
            
            # Cache recommendations
            if cache_stats.hit_rate < 0.7:
                recommendations.append(
                    f"Cache hit rate is low ({cache_stats.hit_rate:.2%}). Consider cache optimization."
                )
            
            # Vector store recommendations
            vector_stats = await self._analyze_vector_storage(bot_id)
            if vector_stats.get('inconsistencies', 0) > 0:
                recommendations.append(
                    f"Found {vector_stats['inconsistencies']} vector store inconsistencies. Run integrity check."
                )
            
            return {
                'bot_id': str(bot_id),
                'storage_stats': storage_stats,
                'cache_stats': asdict(cache_stats) if hasattr(cache_stats, '__dict__') else cache_stats._asdict(),
                'size_analysis': size_analysis,
                'vector_stats': vector_stats,
                'recommendations': recommendations,
                'efficiency_score': self._calculate_efficiency_score(storage_stats, cache_stats, size_analysis),
                'optimization_priority': self._get_optimization_priority(recommendations)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing storage efficiency for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    async def schedule_maintenance_tasks(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Schedule and execute routine maintenance tasks for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Maintenance task results
        """
        try:
            maintenance_results = {
                'tasks_completed': [],
                'tasks_failed': [],
                'next_maintenance': None
            }
            
            # Task 1: Cache optimization
            try:
                cache_result = await self.cache_service.optimize_cache_for_bot(bot_id)
                if cache_result.get('optimization_completed'):
                    maintenance_results['tasks_completed'].append('cache_optimization')
            except Exception as e:
                maintenance_results['tasks_failed'].append(f'cache_optimization: {str(e)}')
            
            # Task 2: Referential integrity check
            try:
                integrity_result = await self.storage_service.maintain_referential_integrity(bot_id)
                if integrity_result.get('integrity_status') in ['clean', 'repaired']:
                    maintenance_results['tasks_completed'].append('integrity_check')
            except Exception as e:
                maintenance_results['tasks_failed'].append(f'integrity_check: {str(e)}')
            
            # Task 3: Storage statistics update
            try:
                stats = await self.storage_service.get_storage_statistics(bot_id)
                if not stats.get('error'):
                    maintenance_results['tasks_completed'].append('statistics_update')
                    maintenance_results['storage_stats'] = stats
            except Exception as e:
                maintenance_results['tasks_failed'].append(f'statistics_update: {str(e)}')
            
            # Task 4: Cache warming for frequently accessed bots
            try:
                cached_count = await self.cache_service.cache_bot_chunks(bot_id)
                if cached_count > 0:
                    maintenance_results['tasks_completed'].append('cache_warming')
                    maintenance_results['cached_chunks'] = cached_count
            except Exception as e:
                maintenance_results['tasks_failed'].append(f'cache_warming: {str(e)}')
            
            # Schedule next maintenance (24 hours from now)
            next_maintenance = datetime.now() + timedelta(hours=24)
            maintenance_results['next_maintenance'] = next_maintenance.isoformat()
            
            logger.info(
                f"Maintenance completed for bot {bot_id}: "
                f"{len(maintenance_results['tasks_completed'])} tasks completed, "
                f"{len(maintenance_results['tasks_failed'])} tasks failed"
            )
            
            return maintenance_results
            
        except Exception as e:
            logger.error(f"Error during maintenance for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    # Private helper methods
    
    async def _remove_duplicate_chunks(self, bot_id: UUID) -> Dict[str, Any]:
        """Remove duplicate chunks based on content hash."""
        try:
            # Find duplicate chunks by content hash
            duplicate_query = text("""
                SELECT 
                    encode(digest(content, 'sha256'), 'hex') as content_hash,
                    array_agg(id ORDER BY created_at) as chunk_ids,
                    count(*) as count,
                    sum(length(content)) as total_size
                FROM document_chunks 
                WHERE bot_id = :bot_id
                GROUP BY encode(digest(content, 'sha256'), 'hex')
                HAVING count(*) > 1
            """)
            
            duplicates = self.db.execute(duplicate_query, {'bot_id': str(bot_id)}).fetchall()
            
            removed_count = 0
            space_saved = 0
            
            for dup in duplicates:
                chunk_ids = dup.chunk_ids[1:]  # Keep the first one, remove the rest
                chunk_size = dup.total_size // dup.count  # Average size per chunk
                
                # Remove from vector store
                for chunk_id in chunk_ids:
                    chunk = self.db.query(DocumentChunk).filter(
                        DocumentChunk.id == chunk_id
                    ).first()
                    
                    if chunk and chunk.embedding_id:
                        try:
                            await self.vector_service.delete_document_chunks(
                                str(bot_id), [chunk.embedding_id]
                            )
                        except Exception as e:
                            logger.warning(f"Failed to remove duplicate vector chunk {chunk.embedding_id}: {e}")
                
                # Remove from database
                deleted = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(chunk_ids)
                ).delete(synchronize_session=False)
                
                removed_count += deleted
                space_saved += chunk_size * deleted
            
            return {
                'removed_count': removed_count,
                'space_saved': space_saved,
                'duplicate_groups': len(duplicates)
            }
            
        except Exception as e:
            logger.error(f"Error removing duplicate chunks for bot {bot_id}: {e}")
            return {'removed_count': 0, 'space_saved': 0, 'error': str(e)}
    
    async def _cleanup_orphaned_data(self, bot_id: UUID) -> Dict[str, Any]:
        """Clean up orphaned data for a bot."""
        try:
            cleaned_count = 0
            space_saved = 0
            
            # Find chunks without valid documents
            orphaned_chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    ~DocumentChunk.document_id.in_(
                        self.db.query(Document.id).filter(Document.bot_id == bot_id)
                    )
                )
            ).all()
            
            for chunk in orphaned_chunks:
                # Remove from vector store
                if chunk.embedding_id:
                    try:
                        await self.vector_service.delete_document_chunks(
                            str(bot_id), [chunk.embedding_id]
                        )
                    except Exception as e:
                        logger.warning(f"Failed to remove orphaned vector chunk {chunk.embedding_id}: {e}")
                
                space_saved += len(chunk.content) if chunk.content else 0
                cleaned_count += 1
            
            # Delete orphaned chunks
            if orphaned_chunks:
                orphaned_ids = [chunk.id for chunk in orphaned_chunks]
                self.db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(orphaned_ids)
                ).delete(synchronize_session=False)
            
            return {
                'cleaned_count': cleaned_count,
                'space_saved': space_saved
            }
            
        except Exception as e:
            logger.error(f"Error cleaning orphaned data for bot {bot_id}: {e}")
            return {'cleaned_count': 0, 'space_saved': 0, 'error': str(e)}
    
    async def _optimize_chunk_metadata(self, bot_id: UUID) -> Dict[str, Any]:
        """Optimize chunk metadata storage."""
        try:
            optimized_count = 0
            
            # Find chunks with large or redundant metadata
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == bot_id
            ).all()
            
            for chunk in chunks:
                if chunk.chunk_metadata:
                    original_metadata = chunk.chunk_metadata
                    optimized_metadata = self._optimize_metadata_dict(original_metadata)
                    
                    if len(str(optimized_metadata)) < len(str(original_metadata)):
                        chunk.chunk_metadata = optimized_metadata
                        optimized_count += 1
            
            if optimized_count > 0:
                self.db.flush()
            
            return {'optimized_count': optimized_count}
            
        except Exception as e:
            logger.error(f"Error optimizing chunk metadata for bot {bot_id}: {e}")
            return {'optimized_count': 0, 'error': str(e)}
    
    def _optimize_metadata_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize metadata dictionary by removing redundant or large values."""
        optimized = {}
        
        for key, value in metadata.items():
            # Skip very large values
            if isinstance(value, str) and len(value) > 1000:
                continue
            
            # Skip redundant keys
            if key in ['full_content', 'raw_text', 'original_document']:
                continue
            
            # Keep useful metadata
            if key in ['page_number', 'section', 'title', 'source', 'chunk_type']:
                optimized[key] = value
            elif isinstance(value, (int, float, bool)):
                optimized[key] = value
            elif isinstance(value, str) and len(value) <= 200:
                optimized[key] = value
        
        return optimized
    
    async def _analyze_vector_storage(self, bot_id: UUID) -> Dict[str, Any]:
        """Analyze vector storage for inconsistencies."""
        try:
            # Get database chunk count
            db_count = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == bot_id
            ).count()
            
            # Get vector store count
            try:
                vector_ids = await self.vector_service.get_collection_point_ids(str(bot_id))
                vector_count = len(vector_ids) if vector_ids else 0
            except:
                vector_count = 0
            
            inconsistencies = abs(db_count - vector_count)
            
            return {
                'database_chunks': db_count,
                'vector_chunks': vector_count,
                'inconsistencies': inconsistencies,
                'consistency_ratio': min(db_count, vector_count) / max(db_count, vector_count, 1)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing vector storage for bot {bot_id}: {e}")
            return {'error': str(e)}
    
    def _calculate_efficiency_score(
        self,
        storage_stats: Dict[str, Any],
        cache_stats: Any,
        size_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall storage efficiency score (0-100)."""
        try:
            score = 100.0
            
            # Deduct for duplicates
            duplicate_ratio = storage_stats.get('duplicate_chunks', 0) / max(storage_stats.get('total_chunks', 1), 1)
            score -= duplicate_ratio * 30
            
            # Deduct for poor cache performance
            hit_rate = getattr(cache_stats, 'hit_rate', 0) if hasattr(cache_stats, 'hit_rate') else cache_stats.get('hit_rate', 0)
            score -= (1 - hit_rate) * 20
            
            # Deduct for poor chunk size distribution
            avg_size = size_analysis.get('avg_size', 1000)
            if avg_size < 200 or avg_size > 3000:
                score -= 15
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating efficiency score: {e}")
            return 50.0  # Default middle score
    
    def _get_optimization_priority(self, recommendations: List[str]) -> str:
        """Determine optimization priority based on recommendations."""
        if not recommendations:
            return 'low'
        
        high_priority_keywords = ['duplicate', 'inconsistencies', 'large']
        medium_priority_keywords = ['cache', 'size', 'small']
        
        for rec in recommendations:
            rec_lower = rec.lower()
            if any(keyword in rec_lower for keyword in high_priority_keywords):
                return 'high'
            elif any(keyword in rec_lower for keyword in medium_priority_keywords):
                return 'medium'
        
        return 'low'