"""
Chat service with RAG integration for processing messages and generating responses.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid

from ..models.bot import Bot
from ..models.conversation import ConversationSession, Message
from ..models.user import User
from ..schemas.conversation import ChatRequest, ChatResponse
from .conversation_service import ConversationService
from .permission_service import PermissionService
from .llm_service import LLMProviderService
from .embedding_service import EmbeddingProviderService
from .vector_store import VectorService
from .user_service import UserService
from .enhanced_api_key_service import EnhancedAPIKeyService
from .rag_error_recovery import RAGErrorRecovery, ErrorContext, ErrorCategory, ErrorSeverity
from .comprehensive_error_handler import ComprehensiveErrorHandler, ErrorHandlingConfig


logger = logging.getLogger(__name__)

# Import WebSocket service (avoid circular import by importing at module level)
def get_websocket_service():
    """Get WebSocket service instance to avoid circular imports."""
    from .websocket_service import WebSocketService
    return WebSocketService


class ChatService:
    """Service for processing chat messages with RAG integration."""
    
    def __init__(self, db: Session):
        """
        Initialize chat service with required dependencies.
        
        Args:
            db: Database session
        """
        self.db = db
        self.conversation_service = ConversationService(db)
        self.permission_service = PermissionService(db)
        self.llm_service = LLMProviderService()
        self.embedding_service = EmbeddingProviderService()
        self.vector_service = VectorService()
        self.user_service = UserService(db)
        self.api_key_service = EnhancedAPIKeyService(db)
        self.error_recovery = RAGErrorRecovery()
        
        # Initialize comprehensive error handler
        error_config = ErrorHandlingConfig(
            enable_graceful_degradation=True,
            enable_service_recovery_detection=True,
            enable_fallback_responses=True,
            error_context_in_response=True
        )
        self.comprehensive_error_handler = ComprehensiveErrorHandler(db, error_config)
        
        # Configuration
        self.max_history_messages = 10
        self.max_retrieved_chunks = 5
        # Model/provider-specific similarity thresholds with sane defaults
        self.similarity_thresholds = {
            "openai": {"text-embedding-ada-002": 0.3, "text-embedding-3-small": 0.25},
            "gemini": {"embedding-001": 0.2, "text-embedding-004": 0.15},
            "anthropic": {"claude-3-haiku": 0.25},
        }
        self.default_similarity_threshold = 0.3
        self.max_prompt_length = 8000
        self.enable_graceful_degradation = True
    
    async def process_message(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        chat_request: ChatRequest
    ) -> ChatResponse:
        """
        Process a chat message through the complete RAG pipeline.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            chat_request: Chat request with message and optional session_id
            
        Returns:
            ChatResponse with generated response and metadata
            
        Raises:
            HTTPException: If permission denied or processing fails
        """
        start_time = time.time()
        
        try:
            # Step 1: Permission validation
            if not self.permission_service.check_bot_permission(
                user_id, bot_id, "view_conversations"
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not have permission to chat with this bot"
                )
            
            # Step 2: Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            # Step 3: Get or create conversation session
            session = await self._get_or_create_session(
                bot_id, user_id, chat_request.session_id
            )
            
            # Step 4: Store user message
            user_message = await self._store_user_message(
                session.id, bot_id, user_id, chat_request.message
            )
            
            # Step 5: Retrieve relevant document chunks using RAG with error recovery
            relevant_chunks, rag_metadata = await self._retrieve_relevant_chunks_with_recovery(
                bot, chat_request.message, user_id
            )
            
            # Step 6: Get conversation history (excluding current message)
            conversation_history = await self._get_conversation_history(
                session.id, user_id, exclude_current_message=chat_request.message
            )
            
            # Step 7: Build prompt with context
            prompt = await self._build_prompt(
                bot, conversation_history, relevant_chunks, chat_request.message
            )
            
            # Step 8: Generate response using configured LLM
            response_text, response_metadata = await self._generate_response(
                bot, user_id, prompt
            )
            
            # Step 9: Store assistant response
            assistant_message = await self._store_assistant_message(
                session.id, bot_id, user_id, response_text, {
                    **response_metadata,
                    "chunks_used": [chunk["id"] for chunk in relevant_chunks],
                    "chunks_count": len(relevant_chunks),
                    "prompt_length": len(prompt),
                    **rag_metadata  # Include RAG error recovery metadata
                }
            )
            
            processing_time = time.time() - start_time
            
            # Step 10: Log conversation metadata
            await self._log_conversation_metadata(
                bot_id, user_id, session.id, user_message.id, assistant_message.id,
                processing_time, relevant_chunks, response_metadata
            )
            
            # Step 11: Send real-time WebSocket notifications
            await self._send_chat_notifications(
                bot_id, user_id, user_message, assistant_message, session.id
            )
            
            # Step 12: Send user notification if RAG fallback was used
            if rag_metadata.get("fallback_used") and rag_metadata.get("fallback_message"):
                await self._send_rag_fallback_notification(
                    bot_id, user_id, session.id, rag_metadata
                )
            
            return ChatResponse(
                message=response_text,
                session_id=session.id,
                chunks_used=[chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"] for chunk in relevant_chunks],
                processing_time=processing_time,
                metadata={
                    "user_message_id": str(user_message.id),
                    "assistant_message_id": str(assistant_message.id),
                    "chunks_count": len(relevant_chunks),
                    "llm_provider": bot.llm_provider,
                    "llm_model": bot.llm_model,
                    **response_metadata,
                    **rag_metadata  # Include RAG error recovery metadata
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat processing failed for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process chat message: {str(e)}"
            )
    
    async def _send_rag_fallback_notification(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        rag_metadata: Dict[str, Any]
    ):
        """Send user notification when RAG fallback is used."""
        try:
            # Get WebSocket service
            websocket_service = get_websocket_service()
            
            # Create notification data
            notification_data = {
                "type": "rag_fallback",
                "bot_id": str(bot_id),
                "session_id": str(session_id),
                "message": rag_metadata.get("fallback_message", "Document context is temporarily unavailable"),
                "degradation_reason": rag_metadata.get("degradation_reason"),
                "recovery_strategy": rag_metadata.get("recovery_strategy"),
                "timestamp": time.time()
            }
            
            # Add user notification details if available
            if "user_notification" in rag_metadata:
                notification_data.update(rag_metadata["user_notification"])
            
            # Send notification via WebSocket
            await websocket_service.send_notification_to_user(
                user_id=user_id,
                notification_type="rag_status",
                data=notification_data
            )
            
            logger.info(f"Sent RAG fallback notification to user {user_id} for bot {bot_id}")
            
        except Exception as e:
            logger.error(f"Failed to send RAG fallback notification: {e}")
    
    async def _send_service_recovery_notification(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        service_name: str,
        recovery_details: Optional[Dict[str, Any]] = None
    ):
        """Send notification when a service recovers."""
        try:
            # Create service recovery notification
            notification = self.comprehensive_error_handler.notification_service.create_service_recovery_notification(
                service_name=service_name,
                bot_id=bot_id,
                user_id=user_id,
                recovery_details=recovery_details
            )
            
            if self.comprehensive_error_handler.notification_service.should_send_notification(notification):
                # Get WebSocket service
                websocket_service = get_websocket_service()
                
                # Send notification via WebSocket
                await websocket_service.send_notification_to_user(
                    user_id=user_id,
                    notification_type="service_recovery",
                    data={
                        "type": notification.type.value,
                        "title": notification.title,
                        "message": notification.message,
                        "service_name": service_name,
                        "bot_id": str(bot_id),
                        "timestamp": notification.timestamp
                    }
                )
                
                logger.info(f"Sent service recovery notification to user {user_id} for {service_name}")
            
        except Exception as e:
            logger.error(f"Failed to send service recovery notification: {e}")
    
    async def _get_or_create_session(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID]
    ) -> ConversationSession:
        """Get existing session or create a new one."""
        if session_id:
            session = self.conversation_service.get_session(session_id, user_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or access denied"
                )
            return session
        else:
            # Create new session
            from ..schemas.conversation import ConversationSessionCreate
            session_data = ConversationSessionCreate(
                bot_id=bot_id,
                title="New Conversation"
            )
            return self.conversation_service.create_session(user_id, session_data)
    
    async def _store_user_message(
        self,
        session_id: uuid.UUID,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str
    ) -> Message:
        """Store user message in the database."""
        from ..schemas.conversation import MessageCreate
        
        message_data = MessageCreate(
            session_id=session_id,
            role="user",
            content=content,
            message_metadata={"timestamp": time.time()}
        )
        
        return self.conversation_service.add_message(user_id, message_data)
    
    async def _store_assistant_message(
        self,
        session_id: uuid.UUID,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        metadata: Dict[str, Any]
    ) -> Message:
        """Store assistant message in the database."""
        from ..schemas.conversation import MessageCreate
        
        message_data = MessageCreate(
            session_id=session_id,
            role="assistant",
            content=content,
            message_metadata=metadata
        )
        
        return self.conversation_service.add_message(user_id, message_data)
    
    async def _retrieve_relevant_chunks_with_recovery(
        self,
        bot: Bot,
        query: str,
        user_id: uuid.UUID
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieve relevant document chunks with comprehensive error recovery.
        
        Returns:
            Tuple of (chunks, metadata) where metadata includes error recovery information
        """
        recovery_metadata = {
            "rag_enabled": True,
            "fallback_used": False,
            "error_recovery_applied": False,
            "degradation_reason": None
        }
        
        try:
            chunks = await self._retrieve_relevant_chunks(bot, query)
            return chunks, recovery_metadata
            
        except Exception as e:
            logger.error(f"RAG retrieval failed for bot {bot.id}: {e}")
            
            # Use comprehensive error handler for embedding failures
            if any(keyword in str(e).lower() for keyword in ["embedding", "api key", "authentication", "model"]):
                fallback_response = await self.comprehensive_error_handler.handle_embedding_failure(
                    error=e,
                    bot_id=bot.id,
                    user_id=user_id,
                    query=query
                )
                
                if fallback_response.success:
                    recovery_metadata.update({
                        "rag_enabled": False,
                        "fallback_used": True,
                        "degradation_reason": "embedding_failure",
                        "fallback_message": fallback_response.message,
                        **fallback_response.metadata
                    })
                    logger.info(f"Applied embedding failure fallback for bot {bot.id}: {fallback_response.message}")
                    return fallback_response.data or [], recovery_metadata
            
            # Use comprehensive error handler for vector search failures
            elif any(keyword in str(e).lower() for keyword in ["vector", "search", "collection", "qdrant"]):
                fallback_response = await self.comprehensive_error_handler.handle_vector_search_failure(
                    error=e,
                    bot_id=bot.id,
                    user_id=user_id
                )
                
                if fallback_response.success:
                    recovery_metadata.update({
                        "rag_enabled": False,
                        "fallback_used": True,
                        "degradation_reason": "vector_search_failure",
                        "fallback_message": fallback_response.message,
                        **fallback_response.metadata
                    })
                    logger.info(f"Applied vector search failure fallback for bot {bot.id}: {fallback_response.message}")
                    return fallback_response.data or [], recovery_metadata
            
            # Generic error handling with comprehensive handler
            else:
                success, data, metadata = await self.comprehensive_error_handler.handle_rag_operation_error(
                    operation_name="rag_retrieval",
                    error=e,
                    bot_id=bot.id,
                    user_id=user_id,
                    operation_context={"query": query[:100]},
                    fallback_data=[]
                )
                
                if success:
                    recovery_metadata.update({
                        "rag_enabled": False,
                        "fallback_used": True,
                        "degradation_reason": "generic_rag_failure",
                        **metadata
                    })
                    logger.info(f"Applied generic RAG failure fallback for bot {bot.id}")
                    return data or [], recovery_metadata
            
            # If all recovery attempts fail, update metadata and re-raise
            recovery_metadata.update({
                "rag_enabled": False,
                "error_recovery_applied": True,
                "recovery_success": False,
                "degradation_reason": "all_recovery_failed",
                "original_error": str(e)
            })
            
            # In graceful degradation mode, return empty chunks instead of raising
            if self.enable_graceful_degradation:
                logger.warning(f"All recovery attempts failed for bot {bot.id}, continuing without RAG")
                return [], recovery_metadata
            
            raise
    
    def _categorize_rag_error(self, error: Exception) -> ErrorCategory:
        """Categorize RAG-specific errors."""
        error_message = str(error).lower()
        
        if any(keyword in error_message for keyword in ["api key", "authentication", "unauthorized"]):
            return ErrorCategory.API_KEY_VALIDATION
        elif any(keyword in error_message for keyword in ["embedding", "model not found", "provider"]):
            return ErrorCategory.EMBEDDING_GENERATION
        elif any(keyword in error_message for keyword in ["vector", "search", "similarity", "collection"]):
            return ErrorCategory.VECTOR_SEARCH
        elif any(keyword in error_message for keyword in ["network", "timeout", "connection"]):
            return ErrorCategory.NETWORK_CONNECTIVITY
        elif any(keyword in error_message for keyword in ["rate limit", "quota", "resource"]):
            return ErrorCategory.RESOURCE_EXHAUSTION
        else:
            return ErrorCategory.UNKNOWN
    
    def _assess_rag_error_severity(self, error: Exception) -> ErrorSeverity:
        """Assess severity of RAG errors."""
        error_message = str(error).lower()
        
        if any(keyword in error_message for keyword in ["corrupt", "data loss"]):
            return ErrorSeverity.CRITICAL
        elif any(keyword in error_message for keyword in ["authentication", "collection not found"]):
            return ErrorSeverity.HIGH
        elif any(keyword in error_message for keyword in ["timeout", "rate limit"]):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    async def _retrieve_relevant_chunks(
        self,
        bot: Bot,
        query: str
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks using semantic search."""
        try:
            logger.info(f"Starting RAG retrieval for bot {bot.id} with query: '{query[:50]}...' using embedding provider {bot.embedding_provider}")
            
            # Check if bot has documents uploaded
            if not await self._bot_has_documents(bot.id):
                logger.info(f"Bot {bot.id} has no documents uploaded, skipping RAG retrieval")
                return []
            
            # Check if vector collection exists first
            if not await self.vector_service.vector_store.collection_exists(str(bot.id)):
                logger.warning(f"Vector collection for bot {bot.id} does not exist, skipping RAG retrieval")
                return []
            
            # Generate query embedding with comprehensive error handling
            try:
                # Get API key from bot owner
                user_api_key = self.user_service.get_user_api_key(bot.owner_id, bot.embedding_provider)
                logger.info(f"Retrieved API key for embedding provider {bot.embedding_provider} from bot owner")
                
                # FIXED: Validate embedding model compatibility and dimensions
                embedding_model = bot.embedding_model
                if not self.embedding_service.validate_model_for_provider(bot.embedding_provider, embedding_model):
                    logger.warning(f"Model {embedding_model} not valid for provider {bot.embedding_provider}, using default")
                    # Get default model for provider
                    available_models = self.embedding_service.get_available_models(bot.embedding_provider)
                    if available_models:
                        embedding_model = available_models[0]
                        logger.info(f"Using default model {embedding_model} for provider {bot.embedding_provider}")
                        
                        # Update bot's embedding model in database for future use
                        bot.embedding_model = embedding_model
                        self.db.commit()
                    else:
                        logger.error(f"No available models for provider {bot.embedding_provider}")
                        return []
                
                # FIXED: Verify embedding dimensions match stored embeddings
                expected_dimension = self.embedding_service.get_embedding_dimension(bot.embedding_provider, embedding_model)
                logger.info(f"Expected embedding dimension: {expected_dimension}")
                
                # Get collection info to verify dimensions match
                try:
                    collection_info = await self.vector_service.get_bot_collection_stats(str(bot.id))
                    stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
                    
                    if stored_dimension != expected_dimension:
                        logger.error(
                            f"Dimension mismatch: stored={stored_dimension}, expected={expected_dimension}"
                        )
                        error_msg = (
                            "Embedding dimension mismatch detected. Documents were processed with "
                            f"{stored_dimension}D embeddings, but current model expects {expected_dimension}D. "
                            "Please reprocess documents or change embedding model."
                        )
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail={
                                "error": "dimension_mismatch",
                                "message": error_msg,
                                "stored_dimension": stored_dimension,
                                "expected_dimension": expected_dimension,
                                "remediation": [
                                    "Reprocess all documents with current embedding model",
                                    "Or change bot's embedding model to match stored embeddings",
                                ],
                            },
                        )
                    
                    logger.info(f"Embedding dimensions match: {expected_dimension}")
                    
                except Exception as dim_error:
                    logger.warning(f"Could not verify embedding dimensions: {dim_error}")
                    # Continue anyway, but log the issue
                
                # Generate embedding with retry logic
                logger.info(f"Generating embedding for query using {bot.embedding_provider}/{embedding_model}")
                query_embedding = await self.embedding_service.generate_single_embedding(
                    provider=bot.embedding_provider,
                    text=query,
                    model=embedding_model,
                    api_key=user_api_key
                )
                
                if not query_embedding:
                    logger.error(f"Empty embedding generated for bot {bot.id}")
                    return []
                
                logger.info(f"Generated query embedding with {len(query_embedding)} dimensions using {bot.embedding_provider}/{embedding_model}")
                
                # FIXED: Verify query embedding dimension matches expected
                if len(query_embedding) != expected_dimension:
                    logger.error(f"Query embedding dimension mismatch: got {len(query_embedding)}, expected {expected_dimension}")
                    return []
                
            except HTTPException as http_error:
                logger.error(f"HTTP error generating embedding for bot {bot.id}: {http_error.detail}")
                # FIXED: Provide more specific error information
                if "API key" in str(http_error.detail):
                    logger.error(f"Bot owner needs to configure API key for embedding provider: {bot.embedding_provider}")
                return []
            except Exception as embedding_error:
                logger.error(f"Failed to generate embedding for bot {bot.id}: {embedding_error}")
                import traceback
                logger.error(f"Embedding error traceback: {traceback.format_exc()}")
                return []
            
            # Search for relevant chunks with improved error handling
            try:
                logger.info(f"Searching vector store for bot {bot.id} with {len(query_embedding)} dimensional embedding")
                # Determine threshold for current provider/model
                provider_thresholds = self.similarity_thresholds.get(bot.embedding_provider, {})
                score_threshold = provider_thresholds.get(
                    embedding_model,
                    self.default_similarity_threshold,
                )

                relevant_chunks = await self.vector_service.search_relevant_chunks(
                    bot_id=str(bot.id),
                    query_embedding=query_embedding,
                    top_k=self.max_retrieved_chunks,
                    score_threshold=score_threshold
                )
                
                logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for bot {bot.id}")
                if relevant_chunks:
                    logger.info(f"Top chunk score: {relevant_chunks[0].get('score', 'N/A')}")
                    # Log chunk preview for debugging
                    for i, chunk in enumerate(relevant_chunks[:2]):  # Log first 2 chunks
                        preview = chunk.get('text', '')[:100] + '...' if len(chunk.get('text', '')) > 100 else chunk.get('text', '')
                        logger.info(f"Chunk {i+1} (score: {chunk.get('score', 'N/A')}): {preview}")
                else:
                    logger.info(f"No relevant chunks found for bot {bot.id} with similarity threshold {score_threshold}")
                    # FIXED: Lower similarity threshold temporarily to see if there are any matches
                    logger.info(f"Trying with lower similarity threshold (0.5) to debug...")
                    debug_chunks = await self.vector_service.search_relevant_chunks(
                        bot_id=str(bot.id),
                        query_embedding=query_embedding,
                        top_k=self.max_retrieved_chunks,
                        score_threshold=0.5
                    )
                    if debug_chunks:
                        logger.info(f"Found {len(debug_chunks)} chunks with lower threshold. Top score: {debug_chunks[0].get('score', 'N/A')}")
                    else:
                        logger.info("No chunks found even with lower threshold - trying without threshold...")
                        # Try without any threshold to see if there are ANY chunks
                        no_threshold_chunks = await self.vector_service.search_relevant_chunks(
                            bot_id=str(bot.id),
                            query_embedding=query_embedding,
                            top_k=self.max_retrieved_chunks,
                            score_threshold=None
                        )
                        if no_threshold_chunks:
                            logger.info(f"Found {len(no_threshold_chunks)} chunks without threshold. Top score: {no_threshold_chunks[0].get('score', 'N/A')}")
                            logger.warning(f"Similarity scores are very low. Consider lowering similarity_threshold from {self.similarity_threshold}")
                        else:
                            logger.error("No chunks found at all - possible embedding/indexing issue or empty collection")
                
                return relevant_chunks
                
            except HTTPException as http_error:
                logger.error(f"HTTP error searching vector store for bot {bot.id}: {http_error.detail}")
                return []
            except Exception as search_error:
                logger.error(f"Failed to search vector store for bot {bot.id}: {search_error}")
                import traceback
                logger.error(f"Search error traceback: {traceback.format_exc()}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for bot {bot.id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return empty list if retrieval fails - bot can still respond without RAG
            return []
    
    async def _bot_has_documents(self, bot_id: uuid.UUID) -> bool:
        """Check if bot has any documents uploaded."""
        try:
            from ..models.document import Document
            document_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            return document_count > 0
        except Exception as e:
            logger.error(f"Failed to check documents for bot {bot_id}: {e}")
            return False
    
    async def _get_conversation_history(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        exclude_current_message: Optional[str] = None
    ) -> List[Message]:
        """Get recent conversation history for context."""
        try:
            # Get more messages than needed to account for filtering
            messages = self.conversation_service.get_session_messages(
                session_id, user_id, limit=self.max_history_messages * 2
            )
            
            # Filter out the current user message if provided
            if exclude_current_message:
                messages = [msg for msg in messages if msg.content != exclude_current_message or msg.role != "user"]
            
            # Sort messages in chronological order (oldest first)
            sorted_messages = sorted(messages, key=lambda m: m.created_at)
            
            # Take the most recent messages up to the limit (excluding the very last one which might be the current message)
            recent_messages = sorted_messages[-self.max_history_messages:] if len(sorted_messages) > self.max_history_messages else sorted_messages
            
            logger.info(f"Retrieved {len(recent_messages)} messages from conversation history for session {session_id}")
            
            return recent_messages
            
        except Exception as e:
            logger.error(f"Failed to get conversation history for session {session_id}: {e}")
            return []
    
    async def _build_prompt(
        self,
        bot: Bot,
        history: List[Message],
        chunks: List[Dict[str, Any]],
        user_input: str
    ) -> str:
        """Build the complete prompt with system prompt, context, history, and user input."""
        prompt_parts = []
        
        # System prompt
        prompt_parts.append(f"System: {bot.system_prompt}")
        
        # Add retrieved document context if available
        if chunks:
            context_text = "\n\n".join([
                f"Document Context {i+1}:\n{chunk['text']}"
                for i, chunk in enumerate(chunks)
            ])
            prompt_parts.append(f"\nRelevant Context:\n{context_text}")
        
        # Add conversation history - FIXED: Ensure we get the full history excluding current message
        if history:
            # Filter out the current user message if it's already in history
            filtered_history = [msg for msg in history if msg.content != user_input or msg.role != "user"]
            
            # Take the most recent messages for context
            recent_history = filtered_history[-self.max_history_messages:] if len(filtered_history) > self.max_history_messages else filtered_history
            
            if recent_history:
                history_text = "\n".join([
                    f"{msg.role.title()}: {msg.content}"
                    for msg in recent_history
                ])
                prompt_parts.append(f"\nConversation History:\n{history_text}")
        
        # Add current user input
        prompt_parts.append(f"\nUser: {user_input}")
        prompt_parts.append("\nAssistant:")
        
        # Join and truncate if necessary
        full_prompt = "\n".join(prompt_parts)
        
        # Improved prompt length management
        if len(full_prompt) > self.max_prompt_length:
            logger.warning(f"Prompt length {len(full_prompt)} exceeds maximum {self.max_prompt_length}, truncating...")
            
            # Priority order: System prompt > Current user input > Document context > History
            system_part = prompt_parts[0]
            user_part = f"\nUser: {user_input}\nAssistant:"
            
            # Calculate base length
            base_length = len(system_part) + len(user_part) + 50  # Extra buffer
            remaining_length = self.max_prompt_length - base_length
            
            context_part = ""
            history_part = ""
            
            # Add context if there's space
            if chunks and remaining_length > 200:
                context_text = "\n\n".join([
                    f"Document Context {i+1}:\n{chunk['text']}"
                    for i, chunk in enumerate(chunks)
                ])
                full_context = f"\nRelevant Context:\n{context_text}"
                
                if len(full_context) <= remaining_length // 2:  # Use up to half remaining space for context
                    context_part = full_context
                    remaining_length -= len(context_part)
                else:
                    # Truncate context to fit
                    available_context = remaining_length // 2
                    truncated_context = context_text[:available_context-50] + "...\n[Context truncated]"
                    context_part = f"\nRelevant Context:\n{truncated_context}"
                    remaining_length -= len(context_part)
            
            # Add history if there's remaining space
            if history and remaining_length > 100:
                filtered_history = [msg for msg in history if msg.content != user_input or msg.role != "user"]
                recent_history = filtered_history[-self.max_history_messages:] if len(filtered_history) > self.max_history_messages else filtered_history
                
                if recent_history:
                    history_text = "\n".join([
                        f"{msg.role.title()}: {msg.content}"
                        for msg in recent_history
                    ])
                    full_history = f"\nConversation History:\n{history_text}"
                    
                    if len(full_history) <= remaining_length:
                        history_part = full_history
                    else:
                        # Truncate history to fit, keeping most recent messages
                        available_history = remaining_length - 50
                        truncated_history = history_text[:available_history] + "...\n[History truncated]"
                        history_part = f"\nConversation History:\n{truncated_history}"
            
            # Rebuild prompt with available parts
            full_prompt = system_part + context_part + history_part + user_part
            
            logger.info(f"Truncated prompt to length {len(full_prompt)} (context: {len(context_part)}, history: {len(history_part)})")
        
        return full_prompt
    
    async def _generate_response(
        self,
        bot: Bot,
        user_id: uuid.UUID,
        prompt: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response using the configured LLM provider."""
        # Get API key using unified strategy with fallback
        user_api_key = await self._get_unified_api_key(bot.id, user_id, bot.llm_provider)
        
        # Get model-specific max tokens if bot's max_tokens is default
        max_tokens = bot.max_tokens
        if max_tokens == 1000:  # Default value, use model-specific
            try:
                provider_instance = self.llm_service.factory.get_provider(bot.llm_provider)
                max_tokens = provider_instance.get_model_max_tokens(bot.llm_model)
            except Exception as e:
                logger.warning(f"Failed to get model-specific max tokens: {e}")
                max_tokens = bot.max_tokens  # Fall back to bot setting
        
        # Prepare LLM configuration
        llm_config = {
            "temperature": bot.temperature,
            "max_tokens": max_tokens,
            "top_p": bot.top_p,
            "frequency_penalty": bot.frequency_penalty,
            "presence_penalty": bot.presence_penalty
        }
        
        # Generate response
        response_text = await self.llm_service.generate_response(
            provider=bot.llm_provider,
            model=bot.llm_model,
            prompt=prompt,
            api_key=user_api_key,
            config=llm_config
        )
        
        # Prepare metadata
        metadata = {
            "llm_provider": bot.llm_provider,
            "llm_model": bot.llm_model,
            "llm_config": llm_config,
            "response_length": len(response_text)
        }
        
        return response_text, metadata
    
    async def _get_unified_api_key(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str
    ) -> str:
        """Get API key using unified strategy with fallback and error handling."""
        try:
            # Use enhanced API key service with fallback
            fallback_result = await self.api_key_service.get_api_key_with_fallback(
                bot_id=bot_id,
                user_id=user_id,
                provider=provider,
                validate_key=True,
                enable_fallback=True
            )
            
            if fallback_result.success:
                logger.info(f"Successfully resolved API key for {provider} from {fallback_result.source.value}")
                return fallback_result.api_key
            
            # Generate specific error message with remediation steps
            error_message = fallback_result.final_error or f"No valid API key found for {provider}"
            
            # Add specific remediation suggestions
            suggestions = self.api_key_service.unified_manager.get_api_key_configuration_suggestions(
                bot_id, user_id, provider
            )
            
            if suggestions:
                error_message += f"\n\nSuggested actions:\n" + "\n".join(f"• {suggestion}" for suggestion in suggestions[:3])
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in unified API key resolution: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resolve API key for {provider}: {str(e)}"
            )
    
    def _get_user_api_key_sync(
        self,
        user_id: uuid.UUID,
        provider: str
    ) -> Optional[str]:
        """
        Legacy synchronous API key method - deprecated.
        Use _get_unified_api_key instead for new implementations.
        """
        logger.warning("Using deprecated _get_user_api_key_sync method. Consider migrating to _get_unified_api_key.")
        try:
            api_key = self.user_service.get_user_api_key(user_id, provider)
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No API key configured for provider '{provider}'. Please add your API key in settings."
                )
            return api_key
        except Exception as e:
            logger.error(f"Failed to get API key for user {user_id}, provider {provider}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve API key"
            )
    
    async def _get_user_api_key(
        self,
        user_id: uuid.UUID,
        provider: str
    ) -> Optional[str]:
        """
        Legacy async API key method - deprecated.
        Use _get_unified_api_key instead for new implementations.
        """
        logger.warning("Using deprecated _get_user_api_key method. Consider migrating to _get_unified_api_key.")
        return self._get_user_api_key_sync(user_id, provider)
    
    async def _log_conversation_metadata(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        user_message_id: uuid.UUID,
        assistant_message_id: uuid.UUID,
        processing_time: float,
        chunks: List[Dict[str, Any]],
        response_metadata: Dict[str, Any]
    ):
        """Log comprehensive conversation metadata for analytics."""
        try:
            # Create activity log entry
            from ..models.activity import ActivityLog
            
            activity_log = ActivityLog(
                bot_id=bot_id,
                user_id=user_id,
                action="chat_interaction",
                details={
                    "session_id": str(session_id),
                    "user_message_id": str(user_message_id),
                    "assistant_message_id": str(assistant_message_id),
                    "processing_time": processing_time,
                    "chunks_used": len(chunks),
                    "chunk_ids": [chunk["id"] for chunk in chunks],
                    "llm_metadata": response_metadata
                }
            )
            
            self.db.add(activity_log)
            self.db.commit()
            
            logger.info(f"Logged chat interaction for bot {bot_id}, session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to log conversation metadata: {e}")
            # Don't raise exception - logging failure shouldn't break chat
    
    async def create_session(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None
    ) -> ConversationSession:
        """Create a new conversation session."""
        # Check permission
        if not self.permission_service.check_bot_permission(
            user_id, bot_id, "view_conversations"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have permission to create sessions for this bot"
            )
        
        from ..schemas.conversation import ConversationSessionCreate
        session_data = ConversationSessionCreate(
            bot_id=bot_id,
            title=title or "New Conversation"
        )
        
        return self.conversation_service.create_session(user_id, session_data)
    
    async def get_session_messages(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """Get messages from a conversation session."""
        return self.conversation_service.get_session_messages(
            session_id, user_id, limit, offset
        )
    
    async def search_conversations(
        self,
        user_id: uuid.UUID,
        query: str,
        bot_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search conversations across user's accessible bots."""
        return self.conversation_service.search_conversations(
            user_id, query, bot_id, limit, offset
        )
    
    async def _send_chat_notifications(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        user_message: Message,
        assistant_message: Message,
        session_id: uuid.UUID
    ):
        """Send real-time WebSocket notifications for chat messages."""
        try:
            # Import WebSocket service to avoid circular imports
            from .websocket_service import connection_manager
            
            # Get user info
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return
            
            # FIXED: Only send assistant message notification to avoid duplicates
            # The user message is already displayed in the frontend when sent
            assistant_message_data = {
                "message_id": str(assistant_message.id),
                "session_id": str(session_id),
                "user_id": str(user_id),
                "username": "Assistant",
                "content": assistant_message.content,
                "role": "assistant",
                "timestamp": assistant_message.created_at.isoformat(),
                "metadata": assistant_message.message_metadata if hasattr(assistant_message, 'message_metadata') else {}
            }
            
            # Send to all collaborators including the user who sent the message
            await connection_manager.broadcast_to_bot_collaborators(
                bot_id=str(bot_id),
                message={
                    "type": "chat_response",  # Changed type to distinguish from user messages
                    "bot_id": str(bot_id),
                    "data": assistant_message_data
                },
                db=self.db
            )
            
            logger.info(f"Sent assistant response WebSocket notification for bot {bot_id}")
            
        except Exception as e:
            logger.error(f"Failed to send chat WebSocket notifications: {e}")
            # Don't raise exception - WebSocket failure shouldn't break chat
    
    async def diagnose_embedding_issues(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Diagnose embedding and RAG retrieval issues for a bot.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            
        Returns:
            Dictionary with diagnostic information
        """
        try:
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return {"error": "Bot not found"}
            
            diagnosis = {
                "bot_id": str(bot_id),
                "embedding_provider": bot.embedding_provider,
                "embedding_model": bot.embedding_model,
                "llm_provider": bot.llm_provider,
                "llm_model": bot.llm_model,
                "issues": [],
                "recommendations": []
            }
            
            # Check if bot has documents
            has_docs = await self._bot_has_documents(bot_id)
            diagnosis["has_documents"] = has_docs
            
            if not has_docs:
                diagnosis["issues"].append("No documents uploaded")
                diagnosis["recommendations"].append("Upload documents to enable RAG retrieval")
                return diagnosis
            
            # Check vector collection exists
            collection_exists = await self.vector_service.vector_store.collection_exists(str(bot_id))
            diagnosis["vector_collection_exists"] = collection_exists
            
            if not collection_exists:
                diagnosis["issues"].append("Vector collection does not exist")
                diagnosis["recommendations"].append("Reprocess documents to create vector collection")
                return diagnosis
            
            # Check API key availability using unified strategy
            try:
                availability_check = await self.api_key_service.unified_manager.check_api_key_availability(
                    bot.id, bot.owner_id, bot.embedding_provider
                )
                diagnosis["api_key_available"] = availability_check.available
                diagnosis["api_key_sources"] = [source.value for source in availability_check.valid_sources]
                
                if not availability_check.available:
                    diagnosis["issues"].append(f"No valid API key available for {bot.embedding_provider}")
                    if availability_check.recommendations:
                        diagnosis["recommendations"].extend(availability_check.recommendations)
                    
            except Exception as e:
                diagnosis["api_key_available"] = False
                diagnosis["issues"].append(f"API key check failed for {bot.embedding_provider}: {str(e)}")
                diagnosis["recommendations"].append(f"Configure API key for {bot.embedding_provider}")
            
            # Check model validity
            model_valid = self.embedding_service.validate_model_for_provider(bot.embedding_provider, bot.embedding_model)
            diagnosis["model_valid"] = model_valid
            
            if not model_valid:
                diagnosis["issues"].append(f"Model {bot.embedding_model} not valid for provider {bot.embedding_provider}")
                available_models = self.embedding_service.get_available_models(bot.embedding_provider)
                diagnosis["available_models"] = available_models
                diagnosis["recommendations"].append(f"Use one of the available models: {available_models}")
            
            # Check embedding dimensions
            try:
                expected_dimension = self.embedding_service.get_embedding_dimension(bot.embedding_provider, bot.embedding_model)
                diagnosis["expected_dimension"] = expected_dimension
                
                collection_info = await self.vector_service.get_bot_collection_stats(str(bot_id))
                stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
                diagnosis["stored_dimension"] = stored_dimension
                
                if stored_dimension != expected_dimension:
                    diagnosis["issues"].append(f"Dimension mismatch: stored={stored_dimension}, expected={expected_dimension}")
                    diagnosis["recommendations"].append("Reprocess documents with current embedding model")
                
            except Exception as e:
                diagnosis["issues"].append(f"Could not verify embedding dimensions: {str(e)}")
            
            # Test embedding generation
            if diagnosis["api_key_available"] and diagnosis["model_valid"]:
                try:
                    # Use unified API key strategy for testing
                    api_key = await self._get_unified_api_key(
                        bot.id, bot.owner_id, bot.embedding_provider
                    )
                    test_embedding = await self.embedding_service.generate_single_embedding(
                        provider=bot.embedding_provider,
                        text="test query",
                        model=bot.embedding_model,
                        api_key=api_key
                    )
                    diagnosis["embedding_generation_works"] = True
                    diagnosis["test_embedding_dimension"] = len(test_embedding)
                except Exception as e:
                    diagnosis["embedding_generation_works"] = False
                    diagnosis["embedding_error"] = str(e)
                    diagnosis["issues"].append(f"Embedding generation failed: {str(e)}")
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"Error diagnosing embedding issues for bot {bot_id}: {e}")
            return {"error": f"Diagnosis failed: {str(e)}"}
    
    async def close(self):
        """Close all service connections and clean up resources."""
        try:
            await self.llm_service.close()
            await self.embedding_service.close()
            await self.vector_service.close()
            logger.info("Closed chat service connections")
        except Exception as e:
            logger.error(f"Error closing chat service: {e}")