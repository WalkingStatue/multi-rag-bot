"""
Document service for handling document upload, processing, and RAG operations.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import uuid

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..core.config import settings
from ..core.database import get_db
from ..models.document import Document, DocumentChunk
from ..models.bot import Bot
from ..services.permission_service import PermissionService
from ..services.embedding_service import EmbeddingProviderService
from ..services.vector_store import VectorService
from ..services.vector_collection_manager import VectorCollectionManager
from ..services.optimized_chunk_storage import OptimizedChunkStorage
from ..services.chunk_metadata_cache import ChunkMetadataCache
from ..models.collection_metadata import CollectionMetadata
from ..utils.text_processing import DocumentProcessor, TextChunk

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document management and processing with RAG integration."""
    
    def __init__(
        self,
        db: Session,
        permission_service: PermissionService = None,
        embedding_service: EmbeddingProviderService = None,
        vector_service: VectorService = None,
        collection_manager: VectorCollectionManager = None,
        optimized_storage: OptimizedChunkStorage = None,
        metadata_cache: ChunkMetadataCache = None
    ):
        """
        Initialize document service.
        
        Args:
            db: Database session
            permission_service: Permission service instance
            embedding_service: Embedding service instance
            vector_service: Vector service instance
            collection_manager: Vector collection manager instance
            optimized_storage: Optimized chunk storage service
            metadata_cache: Chunk metadata cache service
        """
        self.db = db
        self.permission_service = permission_service or PermissionService(db)
        self.embedding_service = embedding_service or EmbeddingProviderService()
        self.collection_manager = collection_manager or VectorCollectionManager(db)
        self.optimized_storage = optimized_storage or OptimizedChunkStorage(db)
        self.metadata_cache = metadata_cache or ChunkMetadataCache(db)
        
        # Initialize vector service
        self.vector_service = vector_service or VectorService()
        logger.info("Vector service initialized successfully")
        
        # Initialize document processor with configurable settings including OCR
        try:
            from ..core.ocr_config import ocr_settings
            
            self.processor = DocumentProcessor(
                chunk_size=getattr(settings, 'chunk_size', 1000),
                chunk_overlap=getattr(settings, 'chunk_overlap', 200),
                max_file_size=getattr(settings, 'max_file_size', 50 * 1024 * 1024),
                enable_ocr=ocr_settings.ocr_enabled,
                ocr_language=ocr_settings.ocr_default_language
            )
            logger.info(f"DocumentProcessor initialized successfully with OCR support (enabled: {ocr_settings.ocr_enabled})")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentProcessor: {e}")
            # Fallback to basic processor without OCR
            try:
                self.processor = DocumentProcessor(
                    chunk_size=getattr(settings, 'chunk_size', 1000),
                    chunk_overlap=getattr(settings, 'chunk_overlap', 200),
                    max_file_size=getattr(settings, 'max_file_size', 50 * 1024 * 1024),
                    enable_ocr=False
                )
                logger.warning("Initialized DocumentProcessor without OCR support as fallback")
            except Exception as fallback_error:
                logger.error(f"Failed to initialize fallback DocumentProcessor: {fallback_error}")
                self.processor = None
        
        # Ensure upload directory exists
        try:
            self.upload_dir = Path(getattr(settings, 'upload_dir', './uploads'))
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Upload directory created: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directory: {e}")
            self.upload_dir = Path('./uploads')
    
    async def upload_document(
        self,
        bot_id: UUID,
        user_id: UUID,
        file: UploadFile,
        process_immediately: bool = True
    ) -> Document:
        """
        Upload and optionally process a document for a bot.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            file: Uploaded file
            process_immediately: Whether to process the document immediately
            
        Returns:
            Document model instance
            
        Raises:
            HTTPException: If permission denied or processing fails
        """
        # Check permissions - user must be editor or higher
        if not self.permission_service.check_bot_permission(
            user_id, bot_id, "upload_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to upload documents"
            )
        
        # Get bot to ensure it exists
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        try:
            # Read file content
            file_content = await file.read()
            
            # Generate unique document ID and file path
            document_id = uuid.uuid4()
            file_extension = Path(file.filename).suffix
            safe_filename = f"{document_id}{file_extension}"
            file_path = self.upload_dir / str(bot_id) / safe_filename
            
            # Create bot directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file to disk
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Create document record
            document = Document(
                id=document_id,
                bot_id=bot_id,
                uploaded_by=user_id,
                filename=file.filename,
                file_path=str(file_path),
                file_size=len(file_content),
                mime_type=file.content_type
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Document {file.filename} uploaded for bot {bot_id}")
            
            # Process document if requested
            if process_immediately:
                await self.process_document(document_id, user_id)
            
            return document
            
        except Exception as e:
            self.db.rollback()
            # Clean up file if it was created
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
            
            logger.error(f"Error uploading document {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document upload failed: {str(e)}"
            )
    
    async def process_document(self, document_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Process a document: extract text, chunk, generate embeddings, and store.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
            
        Returns:
            Processing results and statistics
            
        Raises:
            HTTPException: If document not found or processing fails
        """
        # Get document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions
        if not self.permission_service.check_bot_permission(
            user_id, document.bot_id, "upload_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to process document"
            )
        
        try:
            # Read file content
            file_path = Path(document.file_path)
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document file not found on disk"
                )
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Process document through pipeline with retry logic
            chunks, doc_metadata = await self._process_document_with_retry(
                file_content=file_content,
                filename=document.filename,
                document_id=str(document_id),
                additional_metadata={
                    "bot_id": str(document.bot_id),
                    "uploaded_by": str(document.uploaded_by) if document.uploaded_by else None
                }
            )
            
            # Get bot's embedding configuration
            bot = self.db.query(Bot).filter(Bot.id == document.bot_id).first()
            embedding_provider = bot.embedding_provider
            embedding_model = bot.embedding_model
            
            # Generate embeddings for chunks
            chunk_texts = [chunk.content for chunk in chunks]
            
            # Get user's API key for the embedding provider
            from ..services.user_service import UserService
            user_service = UserService(self.db)
            api_key = user_service.get_user_api_key(document.uploaded_by, embedding_provider)
            
            embeddings = await self.embedding_service.generate_embeddings(
                provider=embedding_provider,
                texts=chunk_texts,
                model=embedding_model,
                api_key=api_key
            )
            
            # Prepare chunks for optimized storage
            chunk_data = []
            for chunk in chunks:
                chunk_info = {
                    'content': chunk.content,
                    'metadata': {
                        'chunk_index': chunk.chunk_index,
                        'start_char': chunk.start_char,
                        'end_char': chunk.end_char,
                        **chunk.metadata
                    }
                }
                chunk_data.append(chunk_info)
            
            # Ensure vector collection exists for this bot with proper validation
            if self.vector_service and vector_chunks:
                # Get embedding dimension from the first embedding
                embedding_dimension = len(embeddings[0]) if embeddings else 768
                
                # Prepare embedding configuration
                embedding_config = {
                    "provider": embedding_provider,
                    "model": embedding_model,
                    "dimension": embedding_dimension
                }
                
                # Ensure collection exists with proper configuration
                collection_result = await self.collection_manager.ensure_collection_exists(
                    document.bot_id, embedding_config
                )
                
                if not collection_result.success:
                    logger.error(f"Failed to ensure collection exists for bot {document.bot_id}: {collection_result.error}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to initialize vector collection: {collection_result.error}"
                    )
                
                # Update or create collection metadata if needed
                collection_metadata = self.db.query(CollectionMetadata).filter(
                    CollectionMetadata.bot_id == document.bot_id
                ).first()
                
                if not collection_metadata:
                    collection_metadata = CollectionMetadata(
                        bot_id=document.bot_id,
                        collection_name=str(document.bot_id),
                        embedding_provider=embedding_provider,
                        embedding_model=embedding_model,
                        embedding_dimension=embedding_dimension,
                        status="active",
                        points_count=0
                    )
                    self.db.add(collection_metadata)
                    logger.info(f"Created collection metadata for bot {document.bot_id}")
                else:
                    # Update points count (will be updated after successful storage)
                    logger.debug(f"Collection metadata already exists for bot {document.bot_id}")
            
            # Use optimized storage for efficient chunk storage with deduplication
            storage_result = await self.optimized_storage.store_chunks_efficiently(
                bot_id=document.bot_id,
                document_id=document_id,
                chunks=chunk_data,
                embeddings=embeddings,
                enable_deduplication=True,
                batch_size=100
            )
            
            if not storage_result.success:
                raise Exception(f"Failed to store chunks: {storage_result.error}")
            
            # Cache metadata for frequently accessed chunks
            await self.metadata_cache.cache_bot_chunks(document.bot_id)
            
            stored_ids = storage_result.vector_ids
            
            # Get processing statistics
            processing_stats = self.processor.get_processing_stats(chunks)
            
            result = {
                "document_id": str(document_id),
                "filename": document.filename,
                "chunks_created": storage_result.stored_chunks,
                "chunks_deduplicated": storage_result.deduplicated_chunks,
                "embeddings_stored": len(stored_ids),
                "processing_stats": processing_stats,
                "document_metadata": doc_metadata,
                "storage_optimized": True
            }
            
            logger.info(f"Document {document.filename} processed successfully: {len(chunks)} chunks")
            return result
            
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document processing failed: {str(e)}"
            )
    
    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        """
        Delete a document and all associated data.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
            
        Returns:
            True if deletion successful
            
        Raises:
            HTTPException: If document not found or permission denied
        """
        # Get document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions - user must be admin or higher
        if not self.permission_service.check_bot_permission(
            user_id, document.bot_id, "delete_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete document"
            )
        
        try:
            # Get chunk IDs for vector store deletion
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            chunk_ids = [chunk.embedding_id for chunk in chunks if chunk.embedding_id]
            
            # Delete from vector store
            if chunk_ids:
                await self.vector_service.delete_document_chunks(
                    str(document.bot_id), chunk_ids
                )
            
            # Delete file from disk
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Delete from database (chunks will be deleted by cascade)
            self.db.delete(document)
            self.db.commit()
            
            logger.info(f"Document {document.filename} deleted successfully")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document deletion failed: {str(e)}"
            )
    
    async def list_documents(
        self,
        bot_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List documents for a bot with metadata.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            
        Returns:
            List of document information
            
        Raises:
            HTTPException: If permission denied
        """
        # Check permissions - user must be viewer or higher
        if not self.permission_service.check_bot_permission(
            user_id, bot_id, "view_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view documents"
            )
        
        try:
            documents = self.db.query(Document).filter(
                Document.bot_id == bot_id
            ).offset(skip).limit(limit).all()
            
            result = []
            for doc in documents:
                doc_info = {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                    "mime_type": doc.mime_type,
                    "chunk_count": doc.chunk_count,
                    "uploaded_by": str(doc.uploaded_by) if doc.uploaded_by else None,
                    "created_at": doc.created_at.isoformat(),
                    "processing_status": "processed" if doc.chunk_count > 0 else "pending"
                }
                result.append(doc_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing documents for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list documents: {str(e)}"
            )
    
    async def get_document_info(
        self,
        document_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get detailed information about a document.
        
        Args:
            document_id: Document identifier
            user_id: User identifier
            
        Returns:
            Document information with processing details
            
        Raises:
            HTTPException: If document not found or permission denied
        """
        # Get document
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions
        if not self.permission_service.check_bot_permission(
            user_id, document.bot_id, "view_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view document"
            )
        
        try:
            # Get chunks information
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            chunk_info = []
            for chunk in chunks:
                chunk_data = {
                    "id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    "content_length": len(chunk.content),
                    "metadata": chunk.chunk_metadata,
                    "created_at": chunk.created_at.isoformat()
                }
                chunk_info.append(chunk_data)
            
            result = {
                "id": str(document.id),
                "bot_id": str(document.bot_id),
                "filename": document.filename,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "chunk_count": document.chunk_count,
                "uploaded_by": str(document.uploaded_by) if document.uploaded_by else None,
                "created_at": document.created_at.isoformat(),
                "chunks": chunk_info,
                "processing_status": "processed" if document.chunk_count > 0 else "pending"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting document info {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get document info: {str(e)}"
            )
    
    async def search_document_content(
        self,
        bot_id: UUID,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        document_filter: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks using semantic similarity.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            query: Search query
            top_k: Number of results to return
            document_filter: Optional document ID to filter results
            
        Returns:
            List of relevant chunks with similarity scores
            
        Raises:
            HTTPException: If permission denied or search fails
        """
        # Check permissions
        if not self.permission_service.check_bot_permission(
            user_id, bot_id, "view_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to search documents"
            )
        
        try:
            # Get bot's embedding configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            # Generate query embedding
            from ..services.user_service import UserService
            user_service = UserService(self.db)
            api_key = user_service.get_user_api_key(user_id, bot.embedding_provider)
            
            query_embeddings = await self.embedding_service.generate_embeddings(
                provider=bot.embedding_provider,
                texts=[query],
                model=bot.embedding_model,
                api_key=api_key
            )
            
            query_embedding = query_embeddings[0]
            
            # Search in vector store
            results = await self.vector_service.search_relevant_chunks(
                bot_id=str(bot_id),
                query_embedding=query_embedding,
                top_k=top_k,
                document_filter=str(document_filter) if document_filter else None
            )
            
            # Enrich results with document information
            enriched_results = []
            for result in results:
                document_id = result["metadata"].get("document_id")
                if document_id:
                    document = self.db.query(Document).filter(
                        Document.id == UUID(document_id)
                    ).first()
                    
                    if document:
                        enriched_result = {
                            **result,
                            "document_info": {
                                "id": str(document.id),
                                "filename": document.filename,
                                "mime_type": document.mime_type
                            }
                        }
                        enriched_results.append(enriched_result)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error searching documents for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document search failed: {str(e)}"
            )
    
    async def reprocess_bot_documents(
        self,
        bot_id: UUID,
        user_id: UUID,
        force_recreate_collection: bool = False
    ) -> Dict[str, Any]:
        """
        Reprocess all documents for a bot with current embedding configuration.
        
        This is useful when:
        - Embedding provider or model has changed
        - Vector collection has dimension mismatches
        - Documents were processed with different embedding settings
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            force_recreate_collection: Whether to delete and recreate the vector collection
            
        Returns:
            Processing results and statistics
            
        Raises:
            HTTPException: If permission denied or processing fails
        """
        # Check permissions - user must be admin or higher
        if not self.permission_service.check_bot_permission(
            user_id, bot_id, "delete_documents"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to reprocess documents"
            )
        
        try:
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            # Get all documents for this bot
            documents = self.db.query(Document).filter(Document.bot_id == bot_id).all()
            
            if not documents:
                return {
                    "message": "No documents to reprocess",
                    "documents_processed": 0,
                    "total_chunks": 0
                }
            
            logger.info(f"Starting reprocessing of {len(documents)} documents for bot {bot_id}")
            
            # Delete existing vector collection if requested
            if force_recreate_collection:
                logger.info(f"Deleting existing vector collection for bot {bot_id}")
                await self.vector_service.delete_bot_collection(str(bot_id))
            
            # Delete existing chunks from database
            self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).delete()
            
            # Reset chunk counts
            for doc in documents:
                doc.chunk_count = 0
            
            self.db.commit()
            
            # Process each document
            processed_count = 0
            total_chunks = 0
            errors = []
            
            for document in documents:
                try:
                    logger.info(f"Reprocessing document: {document.filename}")
                    result = await self.process_document(document.id, user_id)
                    processed_count += 1
                    total_chunks += result.get("chunks_created", 0)
                    logger.info(f"Successfully reprocessed {document.filename}: {result.get('chunks_created', 0)} chunks")
                    
                except Exception as e:
                    error_msg = f"Failed to reprocess {document.filename}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                "message": f"Reprocessed {processed_count} of {len(documents)} documents",
                "documents_processed": processed_count,
                "total_documents": len(documents),
                "total_chunks": total_chunks,
                "embedding_provider": bot.embedding_provider,
                "embedding_model": bot.embedding_model,
                "errors": errors
            }
            
            logger.info(f"Completed reprocessing for bot {bot_id}: {result}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reprocessing documents for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document reprocessing failed: {str(e)}"
            )
    
    async def get_bot_document_stats(self, bot_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about documents for a bot.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            
        Returns:
            Document statistics
            
        Raises:
            HTTPException: If permission denied
        """
        logger.info(f"Getting document stats for bot {bot_id}, user {user_id}")
        
        # Check permissions
        try:
            has_permission = self.permission_service.check_bot_permission(
                user_id, bot_id, "view_documents"
            )
            logger.info(f"Permission check result: {has_permission}")
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to view document statistics"
                )
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Permission check failed: {str(e)}"
            )
        
        try:
            logger.info("Querying documents from database")
            # Get document counts and sizes
            documents = self.db.query(Document).filter(Document.bot_id == bot_id).all()
            logger.info(f"Found {len(documents)} documents")
            
            total_documents = len(documents)
            total_size = sum(doc.file_size or 0 for doc in documents)
            total_chunks = sum(doc.chunk_count or 0 for doc in documents)
            
            # Get file type distribution
            mime_types = {}
            for doc in documents:
                mime_type = doc.mime_type or "unknown"
                mime_types[mime_type] = mime_types.get(mime_type, 0) + 1
            
            logger.info(f"Basic stats calculated: docs={total_documents}, size={total_size}, chunks={total_chunks}")
            
            # Simple stats without vector store
            stats = {
                "total_documents": total_documents,
                "total_file_size": total_size,
                "total_chunks": total_chunks,
                "average_chunks_per_document": total_chunks / total_documents if total_documents > 0 else 0,
                "file_type_distribution": mime_types,
                "vector_store_stats": {"status": "disabled_for_debugging"}
            }
            
            logger.info(f"Returning stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting document stats for bot {bot_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get document statistics: {str(e)}"
            )
    
    async def _process_document_with_retry(
        self,
        file_content: bytes,
        filename: str,
        document_id: str,
        additional_metadata: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Tuple[List, Dict[str, Any]]:
        """
        Process document with retry logic for better reliability.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            document_id: Unique document identifier
            additional_metadata: Additional metadata to include
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (chunks, document_metadata)
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Processing document {filename}, attempt {attempt + 1}/{max_retries}")
                
                # Try processing with current processor
                chunks, doc_metadata = self.processor.process_document(
                    file_content=file_content,
                    filename=filename,
                    document_id=document_id,
                    additional_metadata=additional_metadata
                )
                
                logger.info(f"Successfully processed {filename} on attempt {attempt + 1}")
                return chunks, doc_metadata
                
            except Exception as e:
                last_error = e
                logger.warning(f"Document processing attempt {attempt + 1} failed for {filename}: {e}")
                
                # If this is not the last attempt, try with different settings
                if attempt < max_retries - 1:
                    try:
                        # Try with OCR disabled for the retry
                        from ..utils.text_processing import DocumentProcessor
                        fallback_processor = DocumentProcessor(
                            chunk_size=getattr(settings, 'chunk_size', 1000),
                            chunk_overlap=getattr(settings, 'chunk_overlap', 200),
                            max_file_size=getattr(settings, 'max_file_size', 50 * 1024 * 1024),
                            enable_ocr=False  # Disable OCR for retry
                        )
                        
                        logger.info(f"Retrying {filename} with OCR disabled")
                        chunks, doc_metadata = fallback_processor.process_document(
                            file_content=file_content,
                            filename=filename,
                            document_id=document_id,
                            additional_metadata=additional_metadata
                        )
                        
                        logger.info(f"Successfully processed {filename} with fallback processor")
                        return chunks, doc_metadata
                        
                    except Exception as fallback_error:
                        logger.warning(f"Fallback processing also failed for {filename}: {fallback_error}")
                        continue
        
        # If all retries failed, raise the last error
        logger.error(f"All processing attempts failed for {filename}")
        raise last_error