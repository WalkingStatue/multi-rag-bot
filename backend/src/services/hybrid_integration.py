"""
Integration Module for Hybrid Retrieval System with Existing Chat Service

This module provides the integration layer between the new hybrid retrieval system
and your existing chat service, ensuring backward compatibility.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from .hybrid_retrieval_orchestrator import (
    HybridRetrievalOrchestrator,
    HybridResponse,
    RetrievalMode,
    InformationDensity
)
from .context_aware_cache_manager import ContextAwareCacheManager, CacheStrategy
from .hybrid_performance_monitor import HybridPerformanceMonitor, HybridRetrievalConfig
from .chat_service import ChatService
from .llm_service import LLMProviderService
from .embedding_service import EmbeddingProviderService
from .vector_store import VectorService

logger = logging.getLogger(__name__)


class HybridChatService(ChatService):
    """
    Enhanced chat service with hybrid retrieval capabilities.
    Extends the existing ChatService with backward compatibility.
    """
    
    def __init__(self, db: Session, enable_hybrid: bool = True):
        """
        Initialize hybrid chat service.
        
        Args:
            db: Database session
            enable_hybrid: Whether to enable hybrid retrieval (default: True)
        """
        super().__init__(db)
        
        self.enable_hybrid = enable_hybrid
        
        if enable_hybrid:
            # Initialize hybrid components
            self.config = HybridRetrievalConfig()
            self.hybrid_orchestrator = HybridRetrievalOrchestrator(
                db=db,
                vector_service=self.vector_service,
                llm_service=self.llm_service,
                embedding_service=self.embedding_service
            )
            
            # Initialize cache manager with Redis if available
            try:
                import redis.asyncio as redis
                redis_client = redis.from_url(
                    "redis://localhost:6379",
                    encoding="utf-8",
                    decode_responses=False
                )
                self.cache_manager = ContextAwareCacheManager(
                    redis_client=redis_client,
                    strategy=CacheStrategy.ADAPTIVE
                )
            except Exception as e:
                logger.warning(f"Redis not available, using local cache only: {e}")
                self.cache_manager = ContextAwareCacheManager(
                    strategy=CacheStrategy.ADAPTIVE
                )
            
            # Initialize performance monitor
            self.performance_monitor = HybridPerformanceMonitor(
                db_session=db,
                config=self.config
            )
            
            logger.info("Hybrid retrieval system initialized")
    
    async def initialize(self):
        """Initialize all hybrid components."""
        if self.enable_hybrid:
            await self.cache_manager.initialize()
            await self.performance_monitor.initialize()
            logger.info("Hybrid components initialized")
    
    async def _retrieve_relevant_chunks_with_recovery(
        self,
        bot: Any,
        query: str,
        user_id: uuid.UUID
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Override parent method to use hybrid retrieval when enabled.
        
        This method maintains backward compatibility while adding hybrid capabilities.
        """
        if not self.enable_hybrid:
            # Fall back to original implementation
            return await super()._retrieve_relevant_chunks_with_recovery(bot, query, user_id)
        
        try:
            # Check cache first
            cache_key_context = {
                "bot_id": str(bot.id),
                "intent": "unknown",  # Will be determined by analyzer
                "domain": "general"
            }
            
            cached_response = await self.cache_manager.get(
                query=query,
                bot_id=str(bot.id),
                user_id=str(user_id),
                context=cache_key_context
            )
            
            if cached_response:
                logger.info(f"Cache hit for query in bot {bot.id}")
                # Convert cached response back to chunks format
                chunks = cached_response.metadata.get("chunks", [])
                metadata = {
                    "cache_hit": True,
                    "cached_mode": cached_response.mode_used,
                    "cached_confidence": cached_response.confidence_score
                }
                return chunks, metadata
            
            # Use hybrid orchestrator for retrieval
            response = await self.hybrid_orchestrator.process_query(
                query=query,
                bot_id=bot.id,
                user_id=user_id,
                conversation_history=await self._get_conversation_history_for_hybrid(
                    session_id=self.current_session_id if hasattr(self, 'current_session_id') else None,
                    user_id=user_id
                )
            )
            
            # Convert hybrid response to chunks format for compatibility
            chunks = self._convert_hybrid_response_to_chunks(response)
            
            # Build metadata
            metadata = {
                "hybrid_mode": response.mode_used.value,
                "hybrid_confidence": response.confidence_score,
                "document_contribution": response.document_contribution,
                "llm_contribution": response.llm_contribution,
                "information_density": response.information_density.name,
                "processing_time": response.processing_time,
                "cache_hit": False
            }
            
            # Cache the response
            await self._cache_hybrid_response(
                query, bot.id, user_id, response, chunks
            )
            
            # Record performance metrics
            await self.performance_monitor.record_query_performance(
                query_id=str(uuid.uuid4()),
                bot_id=str(bot.id),
                user_id=str(user_id),
                mode_used=response.mode_used.value,
                response_time=response.processing_time,
                confidence_score=response.confidence_score,
                cache_hit=False,
                document_count=len(chunks)
            )
            
            return chunks, metadata
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed, falling back to original: {e}")
            # Fall back to original implementation
            return await super()._retrieve_relevant_chunks_with_recovery(bot, query, user_id)
    
    def _convert_hybrid_response_to_chunks(self, response: HybridResponse) -> List[Dict[str, Any]]:
        """Convert hybrid response to chunks format for backward compatibility."""
        chunks = []
        
        # Extract chunks from response metadata if available
        if response.metadata and "chunks" in response.metadata:
            return response.metadata["chunks"]
        
        # Create synthetic chunks from response content
        if response.sources_used:
            for i, source in enumerate(response.sources_used):
                if source != "LLM":
                    chunks.append({
                        "id": source,
                        "text": response.content[i*200:(i+1)*200] if len(response.content) > i*200 else response.content,
                        "score": 0.8 - (i * 0.1),  # Decreasing score
                        "metadata": {
                            "source": source,
                            "mode": response.mode_used.value
                        }
                    })
        
        return chunks
    
    async def _get_conversation_history_for_hybrid(
        self,
        session_id: Optional[uuid.UUID],
        user_id: uuid.UUID
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for hybrid system."""
        if not session_id:
            return []
        
        try:
            messages = await self._get_conversation_history(
                session_id, user_id
            )
            
            # Format for hybrid system
            formatted = []
            for msg in messages[-10:]:  # Last 10 messages
                formatted.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Failed to get conversation history for hybrid: {e}")
            return []
    
    async def _cache_hybrid_response(
        self,
        query: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        response: HybridResponse,
        chunks: List[Dict[str, Any]]
    ):
        """Cache hybrid response for future use."""
        try:
            # Prepare query characteristics
            query_characteristics = {
                "mode": response.mode_used.value,
                "confidence": response.confidence_score,
                "information_density": response.information_density.value,
                "temporal_relevance": 0.2  # Default, would be computed from query analysis
            }
            
            # Add chunks to response metadata for caching
            response.metadata["chunks"] = chunks
            
            await self.cache_manager.set(
                query=query,
                bot_id=str(bot_id),
                user_id=str(user_id),
                response=response,
                context={
                    "bot_id": str(bot_id),
                    "mode": response.mode_used.value
                },
                query_characteristics=query_characteristics
            )
            
        except Exception as e:
            logger.error(f"Failed to cache hybrid response: {e}")
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get performance dashboard for monitoring."""
        if not self.enable_hybrid:
            return {"status": "hybrid_disabled"}
        
        return self.performance_monitor.get_dashboard_metrics()
    
    async def optimize_system(self):
        """Manually trigger system optimization."""
        if not self.enable_hybrid:
            return {"status": "hybrid_disabled"}
        
        return await self.performance_monitor.optimize_system_parameters()
    
    async def invalidate_bot_cache(self, bot_id: uuid.UUID):
        """Invalidate cache when bot configuration changes."""
        if self.enable_hybrid:
            await self.cache_manager.invalidate_bot_cache(str(bot_id))
    
    async def invalidate_document_cache(self, bot_id: uuid.UUID, document_id: str):
        """Invalidate cache when document is updated."""
        if self.enable_hybrid:
            await self.cache_manager.invalidate_document_cache(str(bot_id), document_id)
    
    async def close(self):
        """Close all services and clean up resources."""
        try:
            # Close hybrid components
            if self.enable_hybrid:
                await self.cache_manager.close()
                await self.performance_monitor.close()
            
            # Close parent services
            await super().close()
            
            logger.info("Hybrid chat service closed")
        except Exception as e:
            logger.error(f"Error closing hybrid chat service: {e}")


def create_hybrid_chat_service(db: Session, enable_hybrid: bool = True) -> HybridChatService:
    """
    Factory function to create hybrid chat service.
    
    Args:
        db: Database session
        enable_hybrid: Whether to enable hybrid features (default: True)
        
    Returns:
        HybridChatService instance
    """
    service = HybridChatService(db, enable_hybrid)
    return service


# Migration helper for existing code
async def migrate_to_hybrid_service(existing_service: ChatService, db: Session) -> HybridChatService:
    """
    Migrate from existing ChatService to HybridChatService.
    
    Args:
        existing_service: Existing ChatService instance
        db: Database session
        
    Returns:
        New HybridChatService instance with migrated state
    """
    # Create new hybrid service
    hybrid_service = HybridChatService(db, enable_hybrid=True)
    
    # Initialize components
    await hybrid_service.initialize()
    
    # Copy relevant state from existing service
    hybrid_service.max_history_messages = existing_service.max_history_messages
    hybrid_service.max_retrieved_chunks = existing_service.max_retrieved_chunks
    hybrid_service.similarity_thresholds = existing_service.similarity_thresholds
    hybrid_service.default_similarity_threshold = existing_service.default_similarity_threshold
    hybrid_service.max_prompt_length = existing_service.max_prompt_length
    hybrid_service.enable_graceful_degradation = existing_service.enable_graceful_degradation
    
    logger.info("Successfully migrated to hybrid chat service")
    
    return hybrid_service
