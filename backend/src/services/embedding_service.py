"""
Multi-provider embedding service for generating and managing embeddings.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import httpx
from fastapi import HTTPException, status

from ..core.config import settings
from .embedding_factory import EmbeddingClientFactory


logger = logging.getLogger(__name__)


class EmbeddingProviderService:
    """Service for managing multiple embedding providers and generating embeddings."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize the embedding provider service.
        
        Args:
            client: Optional HTTP client to use. If None, creates a new one.
        """
        self.factory = EmbeddingClientFactory(client)
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.max_batch_size = 100  # Maximum texts per batch
    
    async def _retry_operation(self, operation, *args, **kwargs):
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: The async operation to retry
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation
            
        Returns:
            Result of the operation
            
        Raises:
            The last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {operation.__name__}: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {operation.__name__}")
            except HTTPException:
                # Don't retry HTTP exceptions (auth errors, etc.)
                raise
            except Exception as e:
                # Don't retry other exceptions
                last_exception = e
                break
        
        if last_exception:
            raise last_exception
    
    async def validate_api_key(self, provider: str, api_key: Optional[str] = None) -> bool:
        """
        Validate API key for a specific provider with retry logic.
        
        Args:
            provider: Provider name (openai, gemini, anthropic)
            api_key: API key to validate
            
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            return await self._retry_operation(
                self.factory.validate_api_key,
                provider,
                api_key
            )
        except Exception as e:
            logger.error(f"API key validation failed for {provider}: {e}")
            return False
    
    def get_available_models(self, provider: str) -> List[str]:
        """
        Get list of available models for a provider (static fallback).
        
        Args:
            provider: Provider name
            
        Returns:
            List of available model names
        """
        try:
            return self.factory.get_available_models(provider)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get models for {provider}: {e}")
            return []
    
    async def get_available_models_dynamic(self, provider: str, api_key: str) -> List[str]:
        """
        Get list of available models for a provider dynamically from API.
        
        Args:
            provider: Provider name
            api_key: API key for the provider
            
        Returns:
            List of available model names
        """
        try:
            return await self.factory.get_available_models_dynamic(provider, api_key)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get dynamic models for {provider}: {e}")
            # Fall back to static models
            return self.get_available_models(provider)
    
    def get_all_available_models(self) -> Dict[str, List[str]]:
        """
        Get available models for all providers.
        
        Returns:
            Dictionary mapping provider names to their available models
        """
        return self.factory.get_all_available_models()
    
    def get_supported_providers(self) -> List[str]:
        """
        Get list of supported providers.
        
        Returns:
            List of supported provider names
        """
        return self.factory.get_supported_providers()
    
    def get_embedding_dimension(self, provider: str, model: str) -> int:
        """
        Get embedding dimension for a specific provider and model.
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            Embedding dimension
            
        Raises:
            HTTPException: If provider or model is not supported
        """
        return self.factory.get_embedding_dimension(provider, model)
    
    def validate_model_for_provider(self, provider: str, model: str) -> bool:
        """
        Validate that a model is available for a specific provider.
        
        Args:
            provider: Provider name
            model: Model name to validate
            
        Returns:
            True if model is available for the provider, False otherwise
        """
        try:
            available_models = self.get_available_models(provider)
            return model in available_models
        except Exception as e:
            logger.error(f"Failed to validate model {model} for {provider}: {e}")
            return False
    
    def _batch_texts(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[str]]:
        """
        Split texts into batches for processing.
        
        Args:
            texts: List of texts to batch
            batch_size: Maximum batch size (uses default if None)
            
        Returns:
            List of text batches
        """
        if batch_size is None:
            batch_size = self.max_batch_size
        
        batches = []
        for i in range(0, len(texts), batch_size):
            batches.append(texts[i:i + batch_size])
        
        return batches
    
    async def generate_embeddings(
        self,
        provider: str,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for texts using specified provider and model with retry logic.
        
        Args:
            provider: Provider name
            texts: List of texts to embed
            model: Model name
            api_key: API key for the provider
            config: Optional configuration parameters
            batch_size: Optional batch size for processing (uses default if None)
            
        Returns:
            List of embedding vectors
            
        Raises:
            HTTPException: If provider not supported or generation fails
        """
        if not texts:
            return []
        
        # Validate provider and model
        if not self.validate_model_for_provider(provider, model):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model}' is not available for provider '{provider}'"
            )
        
        try:
            # Process in batches if needed
            if len(texts) > (batch_size or self.max_batch_size):
                batches = self._batch_texts(texts, batch_size)
                all_embeddings = []
                
                for batch in batches:
                    batch_embeddings = await self._retry_operation(
                        self.factory.generate_embeddings,
                        provider,
                        batch,
                        model,
                        api_key,
                        config
                    )
                    all_embeddings.extend(batch_embeddings)
                
                return all_embeddings
            else:
                # Process all texts in one batch
                return await self._retry_operation(
                    self.factory.generate_embeddings,
                    provider,
                    texts,
                    model,
                    api_key,
                    config
                )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Embedding generation failed for {provider}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate embeddings: {str(e)}"
            )
    
    async def generate_single_embedding(
        self,
        provider: str,
        text: str,
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            provider: Provider name
            text: Text to embed
            model: Model name
            api_key: API key for the provider
            config: Optional configuration parameters
            
        Returns:
            Embedding vector
            
        Raises:
            HTTPException: If provider not supported or generation fails
        """
        embeddings = await self.generate_embeddings(
            provider, [text], model, api_key, config
        )
        
        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No embedding generated"
            )
        
        return embeddings[0]
    
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """
        Get information about a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary containing provider information
            
        Raises:
            HTTPException: If provider is not supported
        """
        return self.factory.get_provider_info(provider)
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all supported providers.
        
        Returns:
            Dictionary mapping provider names to their information
        """
        return self.factory.get_all_providers_info()
    
    async def get_fallback_provider(self) -> Tuple[str, str]:
        """
        Get the fallback provider and model (OpenAI provider).
        
        Returns:
            Tuple of (provider_name, model_name)
        """
        fallback_provider = "openai"
        fallback_models = self.get_available_models(fallback_provider)
        
        if not fallback_models:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No fallback embedding models available"
            )
        
        # Use the first available model as default
        fallback_model = fallback_models[0]
        
        return fallback_provider, fallback_model
    
    async def generate_embeddings_with_fallback(
        self,
        primary_provider: str,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        use_fallback: bool = False
    ) -> Tuple[List[List[float]], str, str]:
        """
        Generate embeddings with optional fallback (fallback disabled by default).
        
        Args:
            primary_provider: Primary provider to try first
            texts: List of texts to embed
            model: Model name for primary provider
            api_key: API key for primary provider
            config: Optional configuration parameters
            use_fallback: Whether to use fallback on failure (disabled by default)
            
        Returns:
            Tuple of (embeddings, used_provider, used_model)
            
        Raises:
            HTTPException: If primary provider fails and fallback is disabled or also fails
        """
        try:
            # Try primary provider first
            embeddings = await self.generate_embeddings(
                primary_provider, texts, model, api_key, config
            )
            return embeddings, primary_provider, model
            
        except Exception as e:
            logger.warning(f"Primary provider {primary_provider} failed: {e}")
            
            if not use_fallback:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Embedding generation failed for {primary_provider}: {str(e)}"
                )
            
            try:
                # Fall back to OpenAI provider (requires user's API key)
                fallback_provider, fallback_model = await self.get_fallback_provider()
                logger.info(f"Falling back to {fallback_provider} with model {fallback_model}")
                
                # Note: This would require the user to have an API key for the fallback provider
                embeddings = await self.generate_embeddings(
                    fallback_provider, texts, fallback_model, api_key
                )
                return embeddings, fallback_provider, fallback_model
                
            except Exception as fallback_error:
                logger.error(f"Fallback provider also failed: {fallback_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Both primary ({primary_provider}) and fallback providers failed"
                )
    
    async def close(self):
        """Close the factory and clean up resources."""
        await self.factory.close()