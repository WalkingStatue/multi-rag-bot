"""
Optimized chunk storage service with minimal duplication and efficient retrieval.
Implements requirements 6.1, 6.2, 6.4 for task 7.1.
"""
import asyncio
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from uuid import UUID
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, func, text
from sqlalchemy.dialects.postgresql import insert

from ..core.database import get_db
from ..models.document import Document, DocumentChunk
from ..models.bot import Bot
from ..services.vector_store import VectorService

logger = logging.getLogger(__name__)


@dataclass
class ChunkStorageResult:
    """Result of chunk storage operation."""
    success: bool
    stored_chunks: int
    deduplicated_chunks: int
    vector_ids: List[str]
    error: Optional[str] = None


@dataclass
class ChunkRetrievalResult:
    """Result of chunk retrieval operation."""
    chunks: List[Dict[str, Any]]
    total_count: int
    has_more: bool


@dataclass
class StreamingChunk:
    """Streaming chunk data structure."""
    id: UUID
    content: str
    metadata: Dict[str, Any]
    embedding_id: Optional[str]
    content_hash: str


class OptimizedChunkStorage:
    """
    Optimized chunk storage service that minimizes metadata duplication
    and provides efficient retrieval with streaming support.
    """
    
    def __init__(self, db: Session, vector_service: VectorService = None):
        """
        Initialize optimized chunk storage.
        
        Args:
            db: Database session
            vector_service: Vector service instance
        """
        self.db = db
        self.vector_service = vector_service or VectorService()
        
    def _calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA-256 hash of chunk content for deduplication.
        
        Args:
            content: Chunk content
            
        Returns:
            Content hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def store_chunks_efficiently(
        self,
        bot_id: UUID,
        document_id: UUID,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        enable_deduplication: bool = True,
        batch_size: int = 100
    ) -> ChunkStorageResult:
        """
        Store document chunks with minimal duplication and efficient batch processing.
        
        Args:
            bot_id: Bot identifier
            document_id: Document identifier
            chunks: List of chunk data with content and metadata
            embeddings: List of embedding vectors
            enable_deduplication: Whether to enable content-based deduplication
            batch_size: Batch size for processing large documents
            
        Returns:
            ChunkStorageResult with storage statistics
        """
        try:
            if len(chunks) != len(embeddings):
                raise ValueError("Number of chunks must match number of embeddings")
            
            stored_count = 0
            deduplicated_count = 0
            vector_ids = []
            
            # Process chunks in batches to avoid memory issues
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                
                batch_result = await self._store_chunk_batch(
                    bot_id=bot_id,
                    document_id=document_id,
                    chunks=batch_chunks,
                    embeddings=batch_embeddings,
                    enable_deduplication=enable_deduplication,
                    batch_offset=i
                )
                
                stored_count += batch_result.stored_chunks
                deduplicated_count += batch_result.deduplicated_chunks
                vector_ids.extend(batch_result.vector_ids)
            
            # Update document chunk count
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.chunk_count = stored_count
                self.db.commit()
            
            logger.info(
                f"Stored {stored_count} chunks for document {document_id}, "
                f"deduplicated {deduplicated_count} chunks"
            )
            
            return ChunkStorageResult(
                success=True,
                stored_chunks=stored_count,
                deduplicated_chunks=deduplicated_count,
                vector_ids=vector_ids
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing chunks for document {document_id}: {e}")
            return ChunkStorageResult(
                success=False,
                stored_chunks=0,
                deduplicated_chunks=0,
                vector_ids=[],
                error=str(e)
            )
    
    async def _store_chunk_batch(
        self,
        bot_id: UUID,
        document_id: UUID,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        enable_deduplication: bool,
        batch_offset: int
    ) -> ChunkStorageResult:
        """
        Store a batch of chunks with deduplication and referential integrity.
        
        Args:
            bot_id: Bot identifier
            document_id: Document identifier
            chunks: Batch of chunk data
            embeddings: Batch of embedding vectors
            enable_deduplication: Whether to enable deduplication
            batch_offset: Offset for chunk indexing
            
        Returns:
            ChunkStorageResult for this batch
        """
        stored_count = 0
        deduplicated_count = 0
        vector_ids = []
        
        # Prepare chunk data with content hashes
        chunk_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            content = chunk.get('content', '')
            content_hash = self._calculate_content_hash(content)
            
            chunk_info = {
                'content': content,
                'content_hash': content_hash,
                'metadata': chunk.get('metadata', {}),
                'chunk_index': batch_offset + i,
                'embedding': embedding
            }
            chunk_data.append(chunk_info)
        
        # Check for existing chunks if deduplication is enabled
        existing_hashes = set()
        if enable_deduplication:
            content_hashes = [chunk['content_hash'] for chunk in chunk_data]
            
            # Query existing chunks by content hash within the same bot
            existing_chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.bot_id == bot_id,
                    func.encode(func.digest(DocumentChunk.content, 'sha256'), 'hex').in_(content_hashes)
                )
            ).all()
            
            existing_hashes = {
                hashlib.sha256(chunk.content.encode('utf-8')).hexdigest()
                for chunk in existing_chunks
            }
        
        # Prepare database chunks and vector chunks
        db_chunks = []
        vector_chunks = []
        
        for chunk_info in chunk_data:
            content_hash = chunk_info['content_hash']
            
            # Skip if duplicate and deduplication is enabled
            if enable_deduplication and content_hash in existing_hashes:
                deduplicated_count += 1
                logger.debug(f"Skipping duplicate chunk with hash {content_hash[:8]}...")
                continue
            
            chunk_id = str(uuid.uuid4())
            
            # Prepare database chunk with minimal metadata duplication
            db_chunk = DocumentChunk(
                id=UUID(chunk_id),
                document_id=document_id,
                bot_id=bot_id,
                chunk_index=chunk_info['chunk_index'],
                content=chunk_info['content'],
                embedding_id=chunk_id,
                chunk_metadata=chunk_info['metadata']
            )
            db_chunks.append(db_chunk)
            
            # Prepare vector chunk with optimized metadata
            vector_chunk = {
                'id': chunk_id,
                'embedding': chunk_info['embedding'],
                'text': chunk_info['content'],
                'metadata': {
                    'document_id': str(document_id),
                    'bot_id': str(bot_id),
                    'chunk_index': chunk_info['chunk_index'],
                    'content_hash': content_hash,
                    **chunk_info['metadata']
                }
            }
            vector_chunks.append(vector_chunk)
            vector_ids.append(chunk_id)
            stored_count += 1
        
        # Bulk insert database chunks for efficiency
        if db_chunks:
            self.db.add_all(db_chunks)
            self.db.flush()  # Flush to ensure referential integrity
        
        # Store embeddings in vector store
        if vector_chunks:
            await self.vector_service.store_document_chunks(str(bot_id), vector_chunks)
        
        return ChunkStorageResult(
            success=True,
            stored_chunks=stored_count,
            deduplicated_chunks=deduplicated_count,
            vector_ids=vector_ids
        )
    
    async def retrieve_chunks_efficiently(
        self,
        chunk_ids: List[str],
        include_content: bool = True,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks with efficient queries that fetch only necessary data.
        
        Args:
            chunk_ids: List of chunk IDs to retrieve
            include_content: Whether to include chunk content
            include_metadata: Whether to include chunk metadata
            
        Returns:
            List of chunk data with requested fields
        """
        try:
            # Build query with selective field loading
            query = self.db.query(DocumentChunk)
            
            # Filter by chunk IDs
            uuid_ids = [UUID(chunk_id) for chunk_id in chunk_ids]
            query = query.filter(DocumentChunk.id.in_(uuid_ids))
            
            # Execute query
            chunks = query.all()
            
            # Build result with only requested fields
            result = []
            for chunk in chunks:
                chunk_data = {
                    'id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'bot_id': str(chunk.bot_id),
                    'chunk_index': chunk.chunk_index,
                    'embedding_id': chunk.embedding_id,
                    'created_at': chunk.created_at.isoformat()
                }
                
                if include_content:
                    chunk_data['content'] = chunk.content
                
                if include_metadata:
                    chunk_data['metadata'] = chunk.chunk_metadata or {}
                
                result.append(chunk_data)
            
            logger.debug(f"Retrieved {len(result)} chunks efficiently")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving chunks {chunk_ids}: {e}")
            return []
    
    async def stream_document_chunks(
        self,
        document_id: UUID,
        batch_size: int = 100
    ) -> AsyncGenerator[List[StreamingChunk], None]:
        """
        Stream document chunks in batches to avoid memory issues with large documents.
        
        Args:
            document_id: Document identifier
            batch_size: Number of chunks per batch
            
        Yields:
            Batches of StreamingChunk objects
        """
        try:
            offset = 0
            
            while True:
                # Query batch of chunks
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).order_by(DocumentChunk.chunk_index).offset(offset).limit(batch_size).all()
                
                if not chunks:
                    break
                
                # Convert to streaming chunks
                streaming_chunks = []
                for chunk in chunks:
                    streaming_chunk = StreamingChunk(
                        id=chunk.id,
                        content=chunk.content,
                        metadata=chunk.chunk_metadata or {},
                        embedding_id=chunk.embedding_id,
                        content_hash=self._calculate_content_hash(chunk.content)
                    )
                    streaming_chunks.append(streaming_chunk)
                
                yield streaming_chunks
                
                # Move to next batch
                offset += batch_size
                
                # Break if we got fewer chunks than requested (end of data)
                if len(chunks) < batch_size:
                    break
                    
        except Exception as e:
            logger.error(f"Error streaming chunks for document {document_id}: {e}")
            return
    
    async def maintain_referential_integrity(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Maintain referential integrity between database and vector store.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Integrity check results and repair actions
        """
        try:
            # Get all chunk IDs from database
            db_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.bot_id == bot_id
            ).all()
            
            db_chunk_ids = {chunk.embedding_id for chunk in db_chunks if chunk.embedding_id}
            
            # Get all chunk IDs from vector store
            vector_chunk_ids = await self.vector_service.get_collection_point_ids(str(bot_id))
            vector_chunk_ids = set(vector_chunk_ids) if vector_chunk_ids else set()
            
            # Find inconsistencies
            orphaned_db_chunks = db_chunk_ids - vector_chunk_ids
            orphaned_vector_chunks = vector_chunk_ids - db_chunk_ids
            
            repair_actions = []
            
            # Remove orphaned database chunks
            if orphaned_db_chunks:
                orphaned_count = self.db.query(DocumentChunk).filter(
                    and_(
                        DocumentChunk.bot_id == bot_id,
                        DocumentChunk.embedding_id.in_(list(orphaned_db_chunks))
                    )
                ).delete(synchronize_session=False)
                
                repair_actions.append(f"Removed {orphaned_count} orphaned database chunks")
            
            # Remove orphaned vector chunks
            if orphaned_vector_chunks:
                await self.vector_service.delete_document_chunks(
                    str(bot_id), list(orphaned_vector_chunks)
                )
                repair_actions.append(f"Removed {len(orphaned_vector_chunks)} orphaned vector chunks")
            
            if repair_actions:
                self.db.commit()
            
            result = {
                'total_db_chunks': len(db_chunk_ids),
                'total_vector_chunks': len(vector_chunk_ids),
                'orphaned_db_chunks': len(orphaned_db_chunks),
                'orphaned_vector_chunks': len(orphaned_vector_chunks),
                'repair_actions': repair_actions,
                'integrity_status': 'clean' if not repair_actions else 'repaired'
            }
            
            logger.info(f"Integrity check for bot {bot_id}: {result}")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error maintaining referential integrity for bot {bot_id}: {e}")
            return {
                'error': str(e),
                'integrity_status': 'error'
            }
    
    async def get_storage_statistics(self, bot_id: UUID) -> Dict[str, Any]:
        """
        Get storage statistics for a bot's chunks.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Storage statistics and optimization recommendations
        """
        try:
            # Query chunk statistics
            stats_query = self.db.query(
                func.count(DocumentChunk.id).label('total_chunks'),
                func.sum(func.length(DocumentChunk.content)).label('total_content_size'),
                func.avg(func.length(DocumentChunk.content)).label('avg_chunk_size'),
                func.count(func.distinct(DocumentChunk.document_id)).label('total_documents')
            ).filter(DocumentChunk.bot_id == bot_id)
            
            stats = stats_query.first()
            
            # Calculate potential duplicates by content hash
            duplicate_query = self.db.query(
                func.encode(func.digest(DocumentChunk.content, 'sha256'), 'hex').label('content_hash'),
                func.count().label('count')
            ).filter(DocumentChunk.bot_id == bot_id).group_by(
                func.encode(func.digest(DocumentChunk.content, 'sha256'), 'hex')
            ).having(func.count() > 1)
            
            duplicates = duplicate_query.all()
            duplicate_chunks = sum(dup.count - 1 for dup in duplicates)  # Subtract 1 to keep one copy
            
            result = {
                'total_chunks': stats.total_chunks or 0,
                'total_documents': stats.total_documents or 0,
                'total_content_size': stats.total_content_size or 0,
                'avg_chunk_size': float(stats.avg_chunk_size or 0),
                'duplicate_chunks': duplicate_chunks,
                'duplicate_groups': len(duplicates),
                'storage_efficiency': 1.0 - (duplicate_chunks / max(stats.total_chunks or 1, 1)),
                'recommendations': []
            }
            
            # Add optimization recommendations
            if duplicate_chunks > 0:
                result['recommendations'].append(
                    f"Consider running deduplication to remove {duplicate_chunks} duplicate chunks"
                )
            
            if stats.avg_chunk_size and stats.avg_chunk_size > 2000:
                result['recommendations'].append(
                    "Average chunk size is large, consider reducing chunk size for better retrieval"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting storage statistics for bot {bot_id}: {e}")
            return {'error': str(e)}