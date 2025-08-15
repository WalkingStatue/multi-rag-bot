"""
Enhanced embedding service with intelligent caching and unified API key management.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import httpx
from fastapi import HTTPException, status

from ..core.config import settings
from .embedding_service import EmbeddingProviderService
from .embedding_cache_service import get_embedding_cache_service, EmbeddingCacheService
from .unified_api_key_manager import UnifiedAPIKeyManager

logger = logging.getLogger(__name__)


class EnhancedEmbeddingService:
    """
    Enhanced embedding service with intelligent caching, validation, and error handling.
    """
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize the enhanced embedding service.
        
        Args:
            client: Optional HTTP client to use. If None, creates a new one.
        """
        self.embedding_service = EmbeddingProviderService(client)
        self.api_key_manager = UnifiedAPIKeyManager()
        self.cache_service: Optional[EmbeddingCacheService] = None
        
        # Configuration
        self.enable_caching = True
        self.cache_ttl = 86400 * 7  # 7 days
        self.batch_cache_threshold = 5  # Use batch caching for 5+ texts
        
    async def initialize(self):
        """Initialize the enhanced embedding service."""
        try:
            # Initialize cache service
            if self.enable_caching:
                self.cache_service = await get_embedding_cache_service()
                logger.info("Enhanced embedding service initialized with caching")
            else:
                logger.info("Enhanced embedding service initialized without caching")
                
        except Exception as e:
            logger.warning(f"Failed to initialize cache service: {e}")
            self.cache_service = None
    
    async def close(self):
        """Close the enhanced embedding service."""
        await self.embedding_service.close()
        if self.cache_service:
            await self.cache_service.close()
    
    async def get_unified_api_key(
        self, 
        bot_id: str, 
        user_id: str, 
        provider: str
    ) -> str:
        """
        Get API key using unified strategy with fallbacks.
        
        Args:
            bot_id: Bot ID for bot owner's API key
            user_id: User ID for user's API key fallback
            provider: Provider name
            
        Returns:
            API key string
            
        Raises:
            HTTPException: If no valid API key is found
        """
        return await self.api_key_manager.get_api_key_with_fallback(
            bot_id, user_id, provider
        )
    
    async def validate_embedding_config(
        self, 
        provider: str, 
        model: str, 
        api_key: str
    ) -> Dict[str, Any]:
        """
        Validate embedding configuration comprehensively.
        
        Args:
            provider: Provider name
            model: Model name
            api_key: API key for the provider
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': False,
            'provider_supported': False,
            'model_available': False,
            'api_key_valid': False,
            'dimension': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if provider is supported
            supported_providers = self.embedding_service.get_supported_providers()
            if provider not in supported_providers:
                result['errors'].append(f"Provider '{provider}' is not supported")
                return result
            
            result['provider_supported'] = True
            
            # Check if model is available for provider
            if not self.embedding_service.validate_model_for_provider(provider, model):
                available_models = self.embedding_service.get_available_models(provider)
                result['errors'].append(
                    f"Model '{model}' is not available for provider '{provider}'. "
                    f"Available models: {', '.join(available_models)}"
                )
                return result
            
            result['model_available'] = True
            
            # Get embedding dimension
            try:
                dimension = self.embedding_service.get_embedding_dimension(provider, model)
                result['dimension'] = dimension
            except Exception as e:
                result['warnings'].append(f"Could not determine embedding dimension: {e}")
            
            # Validate API key
            api_key_valid = await self.embedding_service.validate_api_key(provider, api_key)
            if not api_key_valid:
                result['errors'].append(f"Invalid API key for provider '{provider}'")
                return result
            
            result['api_key_valid'] = True
            result['valid'] = True
            
        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")
        
        return result
    
    async def generate_embeddings_with_cache(
        self,
        texts: List[str],
        provider: str,
        model: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings with intelligent caching.
        
        Args:
            texts: List of texts to embed
            provider: Provider name
            model: Model name
            api_key: API key for the provider
            config: Optional configuration parameters
            use_cache: Whether to use caching (default: True)
            
        Returns:
            List of embedding vectors
            
        Raises:
            HTTPException: If embedding generation fails
        """
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = [text for text in texts if text.strip()]
        if not valid_texts:
            return []
        
        try:
            # Use batch caching for multiple texts
            if use_cache and self.cache_service and len(valid_texts) >= self.batch_cache_threshold:
                return await self._generate_embeddings_batch_cached(
                    valid_texts, provider, model, api_key, config
                )
            
            # Use individual caching for smaller batches
            elif use_cache and self.cache_service:
                return await self._generate_embeddings_individual_cached(
                    valid_texts, provider, model, api_key, config
                )
            
            # Generate without caching
            else:
                return await self.embedding_service.generate_embeddings(
                    provider, valid_texts, model, api_key, config
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Enhanced embedding generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate embeddings: {str(e)}"
            )
    
    async def _generate_embeddings_batch_cached(
        self,
        texts: List[str],
        provider: str,
        model: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings using batch caching strategy."""
        # Check cache for all texts
        cached_embeddings, missing_indices = await self.cache_service.get_cached_embeddings_batch(
            texts, provider, model
        )
        
        # If all embeddings are cached, return them
        if not missing_indices:
            logger.debug(f"All {len(texts)} embeddings found in cache")
            return [emb for emb in cached_embeddings if emb is not None]
        
        # Generate embeddings for missing texts
        missing_texts = [texts[i] for i in missing_indices]
        logger.debug(f"Generating {len(missing_texts)} missing embeddings, {len(texts) - len(missing_texts)} from cache")
        
        new_embeddings = await self.embedding_service.generate_embeddings(
            provider, missing_texts, model, api_key, config
        )
        
        # Cache the new embeddings
        await self.cache_service.cache_embeddings_batch(
            missing_texts, provider, model, new_embeddings, self.cache_ttl
        )
        
        # Combine cached and new embeddings
        result_embeddings = []
        missing_iter = iter(new_embeddings)
        
        for i, cached_emb in enumerate(cached_embeddings):
            if cached_emb is not None:
                result_embeddings.append(cached_emb)
            else:
                result_embeddings.append(next(missing_iter))
        
        return result_embeddings
    
    async def _generate_embeddings_individual_cached(
        self,
        texts: List[str],
        provider: str,
        model: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings using individual caching strategy."""
        embeddings = []
        texts_to_generate = []
        text_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cached_embedding = await self.cache_service.get_cached_embedding(
                text, provider, model
            )
            
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
            else:
                embeddings.append(None)  # Placeholder
                texts_to_generate.append(text)
                text_indices.append(i)
        
        # Generate missing embeddings
        if texts_to_generate:
            logger.debug(f"Generating {len(texts_to_generate)} missing embeddings, {len(texts) - len(texts_to_generate)} from cache")
            
            new_embeddings = await self.embedding_service.generate_embeddings(
                provider, texts_to_generate, model, api_key, config
            )
            
            # Cache and insert new embeddings
            for text, embedding, idx in zip(texts_to_generate, new_embeddings, text_indices):
                await self.cache_service.cache_embedding(
                    text, provider, model, embedding, self.cache_ttl
                )
                embeddings[idx] = embedding
        else:
            logger.debug(f"All {len(texts)} embeddings found in cache")
        
        return embeddings
    
    async def generate_single_embedding_with_cache(
        self,
        text: str,
        provider: str,
        model: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[float]:
        """
        Generate embedding for a single text with caching.
        
        Args:
            text: Text to embed
            provider: Provider name
            model: Model name
            api_key: API key for the provider
            config: Optional configuration parameters
            use_cache: Whether to use caching (default: True)
            
        Returns:
            Embedding vector
            
        Raises:
            HTTPException: If embedding generation fails
        """
        embeddings = await self.generate_embeddings_with_cache(
            [text], provider, model, api_key, config, use_cache
        )
        
        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No embedding generated"
            )
        
        return embeddings[0]
    
    async def generate_embeddings_with_unified_keys(
        self,
        texts: List[str],
        provider: str,
        model: str,
        bot_id: str,
        user_id: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings using unified API key strategy with caching.
        
        Args:
            texts: List of texts to embed
            provider: Provider name
            model: Model name
            bot_id: Bot ID for bot owner's API key
            user_id: User ID for user's API key fallback
            config: Optional configuration parameters
            use_cache: Whether to use caching (default: True)
            
        Returns:
            List of embedding vectors
            
        Raises:
            HTTPException: If embedding generation fails
        """
        # Get API key using unified strategy
        api_key = await self.get_unified_api_key(bot_id, user_id, provider)
        
        # Generate embeddings with caching
        return await self.generate_embeddings_with_cache(
            texts, provider, model, api_key, config, use_cache
        )
    
    async def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get cache performance statistics.
        
        Returns:
            Cache statistics dictionary or None if caching is disabled
        """
        if not self.cache_service:
            return None
        
        stats = await self.cache_service.get_cache_stats()
        
        return {
            'total_requests': stats.total_requests,
            'cache_hits': stats.cache_hits,
            'cache_misses': stats.cache_misses,
            'hit_rate': stats.hit_rate,
            'total_entries': stats.total_entries,
            'memory_usage_mb': stats.memory_usage_mb,
            'evictions': stats.evictions
        }
    
    async def clear_cache(
        self, 
        provider: Optional[str] = None, 
        model: Optional[str] = None
    ):
        """
        Clear embedding cache.
        
        Args:
            provider: Optional provider filter
            model: Optional model filter
        """
        if self.cache_service:
            await self.cache_service.clear_cache(provider, model)
    
    async def invalidate_cache_for_model_change(
        self, 
        provider: str, 
        old_model: str, 
        new_model: str
    ):
        """
        Invalidate cache entries when embedding model changes.
        
        Args:
            provider: Provider name
            old_model: Old model name
            new_model: New model name
        """
        if self.cache_service:
            # Clear cache for the old model
            await self.cache_service.clear_cache(provider, old_model)
            logger.info(f"Invalidated cache for {provider}/{old_model} due to model change to {new_model}")
    
    # Delegate methods to underlying embedding service
    async def validate_api_key(self, provider: str, api_key: Optional[str] = None) -> bool:
        """Validate API key for a specific provider."""
        return await self.embedding_service.validate_api_key(provider, api_key)
    
    def get_available_models(self, provider: str) -> List[str]:
        """Get list of available models for a provider."""
        return self.embedding_service.get_available_models(provider)
    
    async def get_available_models_dynamic(self, provider: str, api_key: str) -> List[str]:
        """Get list of available models for a provider dynamically from API."""
        return await self.embedding_service.get_available_models_dynamic(provider, api_key)
    
    def get_all_available_models(self) -> Dict[str, List[str]]:
        """Get available models for all providers."""
        return self.embedding_service.get_all_available_models()
    
    def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return self.embedding_service.get_supported_providers()
    
    def get_embedding_dimension(self, provider: str, model: str) -> int:
        """Get embedding dimension for a specific provider and model."""
        return self.embedding_service.get_embedding_dimension(provider, model)
    
    def validate_model_for_provider(self, provider: str, model: str) -> bool:
        """Validate that a model is available for a specific provider."""
        return self.embedding_service.validate_model_for_provider(provider, model)
    
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """Get information about a specific provider."""
        return self.embedding_service.get_provider_info(provider)
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all supported providers."""
        return self.embedding_service.get_all_providers_info()


# Global enhanced embedding service instance
_enhanced_service: Optional[EnhancedEmbeddingService] = None


async def get_enhanced_embedding_service() -> EnhancedEmbeddingService:
    """
    Get the global enhanced embedding service instance.
    
    Returns:
        Initialized enhanced embedding service
    """
    global _enhanced_service
    
    if _enhanced_service is None:
        _enhanced_service = EnhancedEmbeddingService()
        await _enhanced_service.initialize()
    
    return _enhanced_service


async def close_enhanced_embedding_service():
    """Close the global enhanced embedding service."""
    global _enhanced_service
    
    if _enhanced_service:
        await _enhanced_service.close()
        _enhanced_service = None