"""
RAG Pipeline Manager - Central orchestrator for all RAG operations with error recovery.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.document import Document, DocumentChunk
from ..models.user import User
from .embedding_compatibility_manager import EmbeddingCompatibilityManager
from .vector_collection_manager import VectorCollectionManager
from .embedding_service import EmbeddingProviderService
from .vector_store import VectorService
from .user_service import UserService
from .enhanced_api_key_service import EnhancedAPIKeyService
from .adaptive_retrieval_engine import AdaptiveRetrievalEngine, RetrievalContext
from .rag_error_recovery import RAGErrorRecovery, ErrorContext, ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)


class RAGOperationType(Enum):
    """Types of RAG operations."""
    CHAT_QUERY = "chat_query"
    DOCUMENT_PROCESSING = "document_processing"
    COLLECTION_MIGRATION = "collection_migration"
    CONFIGURATION_VALIDATION = "configuration_validation"


@dataclass
class RAGContext:
    """Context information for RAG operations."""
    bot_id: uuid.UUID
    user_id: uuid.UUID
    operation_type: RAGOperationType
    session_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RAGResult:
    """Result of a RAG operation."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    fallback_used: bool = False


@dataclass
class DocumentProcessingResult:
    """Result of document processing operation."""
    success: bool
    document_id: uuid.UUID
    chunks_processed: int = 0
    chunks_stored: int = 0
    error: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation."""
    valid: bool
    issues: List[str] = None
    recommendations: List[str] = None
    migration_required: bool = False
    metadata: Optional[Dict[str, Any]] = None


class RAGPipelineManager:
    """
    Central orchestrator for all RAG operations with comprehensive error handling and recovery.
    
    This manager coordinates between embedding compatibility, vector collection management,
    and provides graceful error recovery with fallback strategies.
    """
    
    def __init__(self, db: Session):
        """
        Initialize RAG Pipeline Manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_compatibility_manager = EmbeddingCompatibilityManager(db)
        self.vector_collection_manager = VectorCollectionManager(db)
        self.embedding_service = EmbeddingProviderService()
        self.vector_service = VectorService()
        self.user_service = UserService(db)
        self.api_key_service = EnhancedAPIKeyService(db)
        self.adaptive_retrieval_engine = AdaptiveRetrievalEngine(db, self.vector_service)
        self.error_recovery = RAGErrorRecovery()
        
        # Configuration
        self.max_retries = 3
        self.retry_delay = 1.0
        self.fallback_enabled = True
        self.performance_tracking = True
        self.enable_graceful_degradation = True
        self.enable_service_recovery_detection = True
        
        # Performance metrics
        self._operation_metrics: Dict[str, List[float]] = {}
        
        # Service health tracking
        self._service_health: Dict[str, Dict[str, Any]] = {}
        
        # Initialize service health monitoring
        self._initialize_service_health_monitoring()
    
    async def process_chat_query(
        self,
        bot_id: uuid.UUID,
        query: str,
        user_id: uuid.UUID,
        session_context: Optional[Dict] = None
    ) -> RAGResult:
        """
        Process chat query through complete RAG pipeline with error recovery.
        
        Args:
            bot_id: Bot identifier
            query: User query text
            user_id: User identifier
            session_context: Optional session context
            
        Returns:
            RAGResult with retrieved chunks and metadata
        """
        start_time = time.time()
        context = RAGContext(
            bot_id=bot_id,
            user_id=user_id,
            operation_type=RAGOperationType.CHAT_QUERY,
            metadata={
                **(session_context or {}),
                "query_text": query
            }
        )
        
        try:
            logger.info(f"Starting RAG chat query processing for bot {bot_id}")
            
            # Step 1: Validate bot configuration
            validation_result = await self.validate_bot_configuration(bot_id)
            if not validation_result.valid:
                if validation_result.migration_required:
                    logger.warning(f"Bot {bot_id} requires migration: {validation_result.issues}")
                    return RAGResult(
                        success=False,
                        error="Bot configuration requires migration. Please update embedding settings.",
                        metadata={"validation_issues": validation_result.issues}
                    )
                else:
                    logger.warning(f"Bot {bot_id} configuration issues: {validation_result.issues}")
            
            # Step 2: Ensure vector collection exists and is properly configured
            collection_ready = await self.vector_collection_manager.ensure_collection_exists(
                bot_id, await self._get_bot_embedding_config(bot_id)
            )
            
            if not collection_ready.success:
                logger.error(f"Failed to ensure collection for bot {bot_id}: {collection_ready.error}")
                return await self._handle_collection_failure(context, collection_ready.error)
            
            # Step 3: Check if bot has documents
            if not await self._bot_has_documents(bot_id):
                logger.info(f"Bot {bot_id} has no documents, returning empty result")
                return RAGResult(
                    success=True,
                    data=[],
                    metadata={"reason": "no_documents", "processing_time": time.time() - start_time}
                )
            
            # Step 4: Generate query embedding with error recovery
            embedding_result = await self._generate_query_embedding_with_recovery(
                bot_id, query, user_id
            )
            
            # Update service health based on embedding result
            await self._update_service_health(
                "embedding_service", 
                embedding_result.success, 
                embedding_result.error
            )
            
            if not embedding_result.success:
                logger.error(f"Failed to generate embedding for bot {bot_id}: {embedding_result.error}")
                return await self._handle_embedding_failure(context, embedding_result.error)
            
            # Check for service recovery
            await self._handle_service_recovery_resumption("embedding_service", context)
            
            # Step 5: Search for relevant chunks with adaptive thresholds
            search_result = await self._search_relevant_chunks_adaptive(
                bot_id, embedding_result.data, context
            )
            
            # Update service health based on search result
            await self._update_service_health(
                "vector_service", 
                search_result.success, 
                search_result.error
            )
            
            if not search_result.success:
                logger.error(f"Failed to search chunks for bot {bot_id}: {search_result.error}")
                return await self._handle_search_failure(context, search_result.error)
            
            # Check for service recovery
            await self._handle_service_recovery_resumption("vector_service", context)
            
            processing_time = time.time() - start_time
            
            # Track performance metrics
            if self.performance_tracking:
                await self._track_operation_performance(
                    RAGOperationType.CHAT_QUERY, processing_time
                )
            
            logger.info(f"Successfully processed RAG query for bot {bot_id} in {processing_time:.2f}s")
            
            return RAGResult(
                success=True,
                data=search_result.data,
                processing_time=processing_time,
                metadata={
                    "chunks_found": len(search_result.data) if search_result.data else 0,
                    "embedding_provider": embedding_result.metadata.get("provider"),
                    "embedding_model": embedding_result.metadata.get("model"),
                    "fallback_used": embedding_result.fallback_used or search_result.fallback_used
                }
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in RAG chat query for bot {bot_id}: {e}")
            return await self._handle_unexpected_error(context, str(e))
    
    async def process_document(
        self,
        bot_id: uuid.UUID,
        document: Document,
        user_id: uuid.UUID
    ) -> DocumentProcessingResult:
        """
        Process document through embedding and storage pipeline.
        
        Args:
            bot_id: Bot identifier
            document: Document to process
            user_id: User identifier
            
        Returns:
            DocumentProcessingResult with processing statistics
        """
        start_time = time.time()
        context = RAGContext(
            bot_id=bot_id,
            user_id=user_id,
            operation_type=RAGOperationType.DOCUMENT_PROCESSING,
            document_id=document.id
        )
        
        try:
            logger.info(f"Starting document processing for document {document.id} in bot {bot_id}")
            
            # Step 1: Validate bot configuration
            validation_result = await self.validate_bot_configuration(bot_id)
            if not validation_result.valid and validation_result.migration_required:
                return DocumentProcessingResult(
                    success=False,
                    document_id=document.id,
                    error="Bot configuration requires migration before document processing"
                )
            
            # Step 2: Ensure vector collection exists
            embedding_config = await self._get_bot_embedding_config(bot_id)
            collection_result = await self.vector_collection_manager.ensure_collection_exists(
                bot_id, embedding_config
            )
            
            if not collection_result.success:
                return DocumentProcessingResult(
                    success=False,
                    document_id=document.id,
                    error=f"Failed to prepare vector collection: {collection_result.error}"
                )
            
            # Step 3: Process document chunks (this would integrate with existing document service)
            # For now, we'll assume chunks are already created and focus on embedding generation
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document.id
            ).all()
            
            if not chunks:
                return DocumentProcessingResult(
                    success=False,
                    document_id=document.id,
                    error="No chunks found for document"
                )
            
            # Step 4: Generate embeddings for chunks with error recovery
            embedding_results = await self._process_document_chunks_with_recovery(
                bot_id, chunks, user_id
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"Completed document processing for {document.id} in {processing_time:.2f}s")
            
            return DocumentProcessingResult(
                success=embedding_results["success"],
                document_id=document.id,
                chunks_processed=len(chunks),
                chunks_stored=embedding_results["stored_count"],
                processing_time=processing_time,
                error=embedding_results.get("error"),
                metadata=embedding_results.get("metadata")
            )
            
        except Exception as e:
            logger.error(f"Unexpected error processing document {document.id}: {e}")
            return DocumentProcessingResult(
                success=False,
                document_id=document.id,
                error=f"Unexpected error: {str(e)}"
            )
    
    def _initialize_service_health_monitoring(self):
        """Initialize service health monitoring for automatic recovery detection."""
        self._service_health = {
            "embedding_service": {
                "status": "unknown",
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "recovery_detected": False
            },
            "vector_service": {
                "status": "unknown",
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "recovery_detected": False
            },
            "collection_manager": {
                "status": "unknown",
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "recovery_detected": False
            }
        }
    
    async def _update_service_health(self, service_name: str, success: bool, error: Optional[str] = None):
        """Update service health status and detect recovery."""
        if service_name not in self._service_health:
            return
        
        current_time = time.time()
        service_health = self._service_health[service_name]
        
        if success:
            # Check if this is a recovery from previous failures
            if service_health["consecutive_failures"] > 0:
                logger.info(f"Service recovery detected for {service_name} after {service_health['consecutive_failures']} failures")
                service_health["recovery_detected"] = True
                
                # Reset circuit breaker if applicable
                circuit_breaker_key = f"service_{service_name}"
                self.error_recovery.reset_circuit_breaker(circuit_breaker_key)
            
            service_health.update({
                "status": "healthy",
                "last_success": current_time,
                "consecutive_failures": 0
            })
        else:
            service_health.update({
                "status": "unhealthy",
                "last_failure": current_time,
                "consecutive_failures": service_health["consecutive_failures"] + 1,
                "recovery_detected": False
            })
            
            logger.warning(f"Service {service_name} failure #{service_health['consecutive_failures']}: {error}")
    
    async def _check_service_recovery(self, service_name: str) -> bool:
        """Check if a service has recovered from previous failures."""
        if service_name not in self._service_health:
            return False
        
        service_health = self._service_health[service_name]
        
        # Service is considered recovered if:
        # 1. It was previously failing (consecutive_failures > 0)
        # 2. Recent operations have been successful
        # 3. Recovery was detected
        
        if service_health["recovery_detected"] and service_health["status"] == "healthy":
            # Reset recovery flag after acknowledging
            service_health["recovery_detected"] = False
            return True
        
        return False
    
    async def _handle_service_recovery_resumption(self, service_name: str, context: RAGContext):
        """Handle automatic resumption when service recovery is detected."""
        if not self.enable_service_recovery_detection:
            return
        
        recovery_detected = await self._check_service_recovery(service_name)
        
        if recovery_detected:
            logger.info(f"Service recovery detected for {service_name}, resuming normal operations for bot {context.bot_id}")
            
            # Log recovery event
            recovery_metadata = {
                "service_name": service_name,
                "bot_id": str(context.bot_id),
                "recovery_time": time.time(),
                "operation_type": context.operation_type.value
            }
            
            # This could trigger notifications or dashboard updates
            await self._log_service_recovery_event(recovery_metadata)
    
    async def _log_service_recovery_event(self, metadata: Dict[str, Any]):
        """Log service recovery events for monitoring and alerting."""
        try:
            logger.info(f"Service recovery event logged: {metadata}")
            # In a production system, this could:
            # - Send notifications to administrators
            # - Update monitoring dashboards
            # - Trigger automated health checks
            # - Reset alerting systems
        except Exception as e:
            logger.error(f"Failed to log service recovery event: {e}")
    
    def get_service_health_status(self) -> Dict[str, Any]:
        """Get current service health status for monitoring."""
        try:
            current_time = time.time()
            health_summary = {}
            
            for service_name, health_data in self._service_health.items():
                health_summary[service_name] = {
                    "status": health_data["status"],
                    "consecutive_failures": health_data["consecutive_failures"],
                    "last_success_ago": current_time - health_data["last_success"] if health_data["last_success"] else None,
                    "last_failure_ago": current_time - health_data["last_failure"] if health_data["last_failure"] else None,
                    "recovery_detected": health_data["recovery_detected"]
                }
            
            # Add error recovery statistics
            health_summary["error_recovery"] = self.error_recovery.get_error_statistics()
            
            return health_summary
            
        except Exception as e:
            logger.error(f"Error getting service health status: {e}")
            return {"error": str(e)}
    
    async def validate_bot_configuration(
        self,
        bot_id: uuid.UUID
    ) -> ConfigurationValidationResult:
        """
        Validate bot's RAG configuration and suggest fixes.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            ConfigurationValidationResult with validation status and recommendations
        """
        try:
            logger.info(f"Validating configuration for bot {bot_id}")
            
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return ConfigurationValidationResult(
                    valid=False,
                    issues=["Bot not found"],
                    recommendations=[]
                )
            
            issues = []
            recommendations = []
            migration_required = False
            
            # Validate embedding provider and model
            embedding_validation = await self.embedding_compatibility_manager.validate_provider_change(
                bot_id, bot.embedding_provider, bot.embedding_model
            )
            
            if not embedding_validation.compatible:
                issues.extend(embedding_validation.issues)
                recommendations.extend(embedding_validation.recommendations)
                if embedding_validation.migration_required:
                    migration_required = True
            
            # Validate API key availability
            try:
                api_key = self.user_service.get_user_api_key(bot.owner_id, bot.embedding_provider)
                if not api_key:
                    issues.append(f"No API key configured for embedding provider: {bot.embedding_provider}")
                    recommendations.append(f"Configure API key for {bot.embedding_provider} in user settings")
            except Exception as e:
                issues.append(f"Failed to validate API key: {str(e)}")
            
            # Validate vector collection status
            collection_exists = await self.vector_service.vector_store.collection_exists(str(bot_id))
            if not collection_exists:
                issues.append("Vector collection does not exist")
                recommendations.append("Collection will be created automatically on first use")
            else:
                # Check for dimension compatibility
                try:
                    collection_info = await self.vector_service.get_bot_collection_stats(str(bot_id))
                    expected_dimension = self.embedding_service.get_embedding_dimension(
                        bot.embedding_provider, bot.embedding_model
                    )
                    stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
                    
                    if stored_dimension != expected_dimension:
                        issues.append(f"Dimension mismatch: stored={stored_dimension}, expected={expected_dimension}")
                        recommendations.append("Reprocess documents with current embedding model")
                        migration_required = True
                        
                except Exception as e:
                    issues.append(f"Failed to validate collection dimensions: {str(e)}")
            
            is_valid = len(issues) == 0 or (len(issues) > 0 and not migration_required)
            
            logger.info(f"Configuration validation for bot {bot_id}: valid={is_valid}, issues={len(issues)}")
            
            return ConfigurationValidationResult(
                valid=is_valid,
                issues=issues,
                recommendations=recommendations,
                migration_required=migration_required,
                metadata={
                    "bot_id": str(bot_id),
                    "embedding_provider": bot.embedding_provider,
                    "embedding_model": bot.embedding_model
                }
            )
            
        except Exception as e:
            logger.error(f"Error validating bot configuration {bot_id}: {e}")
            return ConfigurationValidationResult(
                valid=False,
                issues=[f"Validation error: {str(e)}"],
                recommendations=["Check bot configuration and try again"]
            )
    
    async def _get_bot_embedding_config(self, bot_id: uuid.UUID) -> Dict[str, Any]:
        """Get bot's embedding configuration."""
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return {
            "provider": bot.embedding_provider,
            "model": bot.embedding_model,
            "dimension": self.embedding_service.get_embedding_dimension(
                bot.embedding_provider, bot.embedding_model
            )
        }
    
    async def _bot_has_documents(self, bot_id: uuid.UUID) -> bool:
        """Check if bot has any documents uploaded."""
        try:
            document_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            return document_count > 0
        except Exception as e:
            logger.error(f"Failed to check documents for bot {bot_id}: {e}")
            return False
    
    async def _generate_query_embedding_with_recovery(
        self,
        bot_id: uuid.UUID,
        query: str,
        user_id: uuid.UUID
    ) -> RAGResult:
        """Generate query embedding with error recovery and fallback strategies."""
        try:
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return RAGResult(success=False, error="Bot not found")
            
            # Get user's API key
            api_key = self.user_service.get_user_api_key(bot.owner_id, bot.embedding_provider)
            if not api_key:
                return RAGResult(
                    success=False,
                    error=f"No API key configured for embedding provider: {bot.embedding_provider}"
                )
            
            # Generate embedding with retry logic
            for attempt in range(self.max_retries):
                try:
                    embedding = await self.embedding_service.generate_single_embedding(
                        provider=bot.embedding_provider,
                        text=query,
                        model=bot.embedding_model,
                        api_key=api_key
                    )
                    
                    return RAGResult(
                        success=True,
                        data=embedding,
                        metadata={
                            "provider": bot.embedding_provider,
                            "model": bot.embedding_model,
                            "dimension": len(embedding),
                            "attempts": attempt + 1
                        }
                    )
                    
                except Exception as e:
                    logger.warning(f"Embedding generation attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        return RAGResult(
                            success=False,
                            error=f"Failed to generate embedding after {self.max_retries} attempts: {str(e)}"
                        )
            
        except Exception as e:
            logger.error(f"Unexpected error generating embedding for bot {bot_id}: {e}")
            return RAGResult(success=False, error=f"Unexpected error: {str(e)}")
    
    async def _search_relevant_chunks_adaptive(
        self,
        bot_id: uuid.UUID,
        query_embedding: List[float],
        context: RAGContext
    ) -> RAGResult:
        """Search for relevant chunks with adaptive similarity thresholds using the new engine."""
        try:
            # Create retrieval context
            retrieval_context = RetrievalContext(
                bot_id=bot_id,
                query_text=context.metadata.get("query_text", "") if context.metadata else "",
                content_type=context.metadata.get("content_type") if context.metadata else None,
                document_count=await self._get_document_count(bot_id),
                session_id=context.session_id,
                user_id=context.user_id
            )
            
            # Use the adaptive retrieval engine
            retrieval_result = await self.adaptive_retrieval_engine.retrieve_relevant_chunks(
                bot_id=bot_id,
                query_embedding=query_embedding,
                context=retrieval_context,
                max_chunks=5
            )
            
            if retrieval_result.success:
                return RAGResult(
                    success=True,
                    data=retrieval_result.chunks,
                    metadata={
                        "threshold_used": retrieval_result.threshold_used,
                        "chunks_found": len(retrieval_result.chunks),
                        "total_attempts": retrieval_result.total_attempts,
                        "processing_time": retrieval_result.processing_time,
                        "fallback_used": retrieval_result.fallback_used,
                        **retrieval_result.metadata
                    },
                    fallback_used=retrieval_result.fallback_used
                )
            else:
                return RAGResult(
                    success=False,
                    error=retrieval_result.error,
                    metadata=retrieval_result.metadata
                )
            
        except Exception as e:
            logger.error(f"Error in adaptive search for bot {bot_id}: {e}")
            return RAGResult(success=False, error=f"Search error: {str(e)}")
    
    async def _get_document_count(self, bot_id: uuid.UUID) -> int:
        """Get the number of documents for a bot."""
        try:
            return self.db.query(Document).filter(Document.bot_id == bot_id).count()
        except Exception as e:
            logger.error(f"Error getting document count for bot {bot_id}: {e}")
            return 0
    
    async def _process_document_chunks_with_recovery(
        self,
        bot_id: uuid.UUID,
        chunks: List[DocumentChunk],
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Process document chunks with error recovery and batch processing."""
        try:
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return {"success": False, "error": "Bot not found", "stored_count": 0}
            
            api_key = self.user_service.get_user_api_key(bot.owner_id, bot.embedding_provider)
            if not api_key:
                return {
                    "success": False,
                    "error": f"No API key for provider: {bot.embedding_provider}",
                    "stored_count": 0
                }
            
            # Process chunks in batches
            batch_size = 10
            total_stored = 0
            errors = []
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_texts = [chunk.content for chunk in batch]
                
                try:
                    # Generate embeddings for batch
                    embeddings = await self.embedding_service.generate_embeddings(
                        provider=bot.embedding_provider,
                        texts=batch_texts,
                        model=bot.embedding_model,
                        api_key=api_key
                    )
                    
                    # Prepare data for vector store
                    chunk_data = []
                    for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                        chunk_data.append({
                            "embedding": embedding,
                            "text": chunk.content,
                            "metadata": {
                                "document_id": str(chunk.document_id),
                                "chunk_id": str(chunk.id),
                                "chunk_index": chunk.chunk_index,
                                **(chunk.chunk_metadata or {})
                            },
                            "id": str(chunk.id)
                        })
                    
                    # Store in vector database
                    stored_ids = await self.vector_service.store_document_chunks(
                        str(bot_id), chunk_data
                    )
                    
                    total_stored += len(stored_ids)
                    logger.info(f"Stored batch {i//batch_size + 1}: {len(stored_ids)} chunks")
                    
                except Exception as e:
                    error_msg = f"Batch {i//batch_size + 1} failed: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            success = total_stored > 0
            return {
                "success": success,
                "stored_count": total_stored,
                "error": "; ".join(errors) if errors else None,
                "metadata": {
                    "total_chunks": len(chunks),
                    "batches_processed": (len(chunks) + batch_size - 1) // batch_size,
                    "errors": len(errors)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing document chunks for bot {bot_id}: {e}")
            return {"success": False, "error": f"Processing error: {str(e)}", "stored_count": 0}
    
    async def _handle_collection_failure(self, context: RAGContext, error: str) -> RAGResult:
        """Handle vector collection failures with fallback strategies."""
        logger.warning(f"Collection failure for bot {context.bot_id}: {error}")
        
        if self.fallback_enabled:
            # Try to recreate collection
            try:
                embedding_config = await self._get_bot_embedding_config(context.bot_id)
                recreation_result = await self.vector_collection_manager.ensure_collection_exists(
                    context.bot_id, embedding_config, force_recreate=True
                )
                
                if recreation_result.success:
                    logger.info(f"Successfully recreated collection for bot {context.bot_id}")
                    return RAGResult(
                        success=True,
                        data=[],
                        fallback_used=True,
                        metadata={"recovery_action": "collection_recreated"}
                    )
            except Exception as e:
                logger.error(f"Failed to recreate collection: {e}")
        
        return RAGResult(
            success=False,
            error=f"Collection failure: {error}",
            metadata={"recovery_attempted": self.fallback_enabled}
        )
    
    async def _handle_embedding_failure(self, context: RAGContext, error: str) -> RAGResult:
        """Handle embedding generation failures with comprehensive error recovery."""
        logger.warning(f"Embedding failure for bot {context.bot_id}: {error}")
        
        # Create error context for recovery system
        error_context = ErrorContext(
            bot_id=context.bot_id,
            user_id=context.user_id,
            operation="embedding_generation",
            error_category=ErrorCategory.EMBEDDING_GENERATION,
            error_message=error,
            severity=self._assess_embedding_error_severity(error),
            timestamp=time.time(),
            metadata=context.metadata
        )
        
        # Apply comprehensive error recovery
        recovery_result = await self.error_recovery.handle_error(
            Exception(error), error_context
        )
        
        if recovery_result.success:
            # Check if graceful degradation was applied
            if recovery_result.data and recovery_result.data.get("continue_without_feature"):
                logger.info(f"Applying graceful degradation for bot {context.bot_id}: continuing without RAG")
                return RAGResult(
                    success=True,
                    data=[],
                    fallback_used=True,
                    metadata={
                        "recovery_strategy": recovery_result.strategy_used.value,
                        "recovery_action": "continue_without_rag",
                        "original_error": error,
                        "error_context_included": True,
                        "service_recovery_enabled": self.enable_service_recovery_detection
                    }
                )
            
            # Check if retry should be attempted
            elif recovery_result.data and recovery_result.data.get("should_retry"):
                logger.info(f"Recovery suggests retry for bot {context.bot_id}")
                return RAGResult(
                    success=False,
                    error=f"Embedding failure (retry suggested): {error}",
                    metadata={
                        "recovery_strategy": recovery_result.strategy_used.value,
                        "should_retry": True,
                        "retry_delay": recovery_result.data.get("retry_delay", self.retry_delay)
                    }
                )
        
        # Recovery failed or not applicable
        return RAGResult(
            success=False,
            error=f"Embedding failure: {error}",
            metadata={
                "recovery_attempted": True,
                "recovery_strategy": recovery_result.strategy_used.value if recovery_result else None,
                "recovery_success": recovery_result.success if recovery_result else False,
                "error_context_included": True
            }
        )
    
    def _assess_embedding_error_severity(self, error: str) -> ErrorSeverity:
        """Assess the severity of embedding errors."""
        error_lower = error.lower()
        
        if any(keyword in error_lower for keyword in ["api key", "authentication", "unauthorized"]):
            return ErrorSeverity.HIGH
        elif any(keyword in error_lower for keyword in ["rate limit", "quota exceeded"]):
            return ErrorSeverity.MEDIUM
        elif any(keyword in error_lower for keyword in ["timeout", "network"]):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    async def _handle_search_failure(self, context: RAGContext, error: str) -> RAGResult:
        """Handle vector search failures with comprehensive error recovery."""
        logger.warning(f"Search failure for bot {context.bot_id}: {error}")
        
        # Create error context for recovery system
        error_context = ErrorContext(
            bot_id=context.bot_id,
            user_id=context.user_id,
            operation="vector_search",
            error_category=ErrorCategory.VECTOR_SEARCH,
            error_message=error,
            severity=self._assess_search_error_severity(error),
            timestamp=time.time(),
            metadata=context.metadata
        )
        
        # Apply comprehensive error recovery
        recovery_result = await self.error_recovery.handle_error(
            Exception(error), error_context
        )
        
        if recovery_result.success:
            # Check if graceful degradation was applied
            if recovery_result.data and recovery_result.data.get("continue_without_feature"):
                logger.info(f"Applying graceful degradation for bot {context.bot_id}: continuing without context retrieval")
                return RAGResult(
                    success=True,
                    data=[],
                    fallback_used=True,
                    metadata={
                        "recovery_strategy": recovery_result.strategy_used.value,
                        "recovery_action": "continue_without_context",
                        "original_error": error,
                        "error_context_included": True,
                        "service_recovery_enabled": self.enable_service_recovery_detection
                    }
                )
            
            # Check if cache fallback is available
            elif recovery_result.data and recovery_result.data.get("use_cache"):
                logger.info(f"Attempting cache fallback for bot {context.bot_id}")
                # This would integrate with a caching system if available
                return RAGResult(
                    success=True,
                    data=[],
                    fallback_used=True,
                    metadata={
                        "recovery_strategy": recovery_result.strategy_used.value,
                        "recovery_action": "cache_fallback",
                        "cache_used": True
                    }
                )
        
        # Recovery failed or not applicable
        return RAGResult(
            success=False,
            error=f"Search failure: {error}",
            metadata={
                "recovery_attempted": True,
                "recovery_strategy": recovery_result.strategy_used.value if recovery_result else None,
                "recovery_success": recovery_result.success if recovery_result else False,
                "error_context_included": True
            }
        )
    
    def _assess_search_error_severity(self, error: str) -> ErrorSeverity:
        """Assess the severity of search errors."""
        error_lower = error.lower()
        
        if any(keyword in error_lower for keyword in ["collection not found", "index missing"]):
            return ErrorSeverity.HIGH
        elif any(keyword in error_lower for keyword in ["timeout", "connection"]):
            return ErrorSeverity.MEDIUM
        elif any(keyword in error_lower for keyword in ["dimension mismatch", "invalid query"]):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    async def _handle_unexpected_error(self, context: RAGContext, error: str) -> RAGResult:
        """Handle unexpected errors with graceful degradation."""
        logger.error(f"Unexpected error for bot {context.bot_id}: {error}")
        
        if self.fallback_enabled and context.operation_type == RAGOperationType.CHAT_QUERY:
            return RAGResult(
                success=True,
                data=[],
                fallback_used=True,
                metadata={
                    "recovery_action": "graceful_degradation",
                    "original_error": error
                }
            )
        
        return RAGResult(
            success=False,
            error=f"Unexpected error: {error}",
            metadata={"recovery_attempted": self.fallback_enabled}
        )
    
    async def _track_operation_performance(
        self,
        operation_type: RAGOperationType,
        processing_time: float
    ):
        """Track performance metrics for operations."""
        if operation_type.value not in self._operation_metrics:
            self._operation_metrics[operation_type.value] = []
        
        self._operation_metrics[operation_type.value].append(processing_time)
        
        # Keep only last 100 measurements
        if len(self._operation_metrics[operation_type.value]) > 100:
            self._operation_metrics[operation_type.value] = self._operation_metrics[operation_type.value][-100:]
    
    def get_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for all operation types."""
        metrics = {}
        
        for operation_type, times in self._operation_metrics.items():
            if times:
                metrics[operation_type] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_operations": len(times)
                }
        
        return metrics
    
    async def close(self):
        """Close all services and clean up resources."""
        try:
            await self.embedding_service.close()
            await self.vector_service.close()
            await self.embedding_compatibility_manager.close()
            await self.vector_collection_manager.close()
            logger.info("RAG Pipeline Manager closed successfully")
        except Exception as e:
            logger.error(f"Error closing RAG Pipeline Manager: {e}")