"""
Embedding client factory for dynamic provider selection.
"""
import logging
from typing import Dict, Optional, List
import httpx
from fastapi import HTTPException, status

from .providers.embedding_base import BaseEmbeddingProvider
from .providers.openai_embedding_provider import OpenAIEmbeddingProvider
from .providers.gemini_embedding_provider import GeminiEmbeddingProvider
from .providers.anthropic_embedding_provider import AnthropicEmbeddingProvider
from .providers.openrouter_embedding_provider import OpenRouterEmbeddingProvider


logger = logging.getLogger(__name__)


class EmbeddingClientFactory:
    """Factory for creating embedding provider clients."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize the factory.
        
        Args:
            client: Optional HTTP client to use. If None, creates a new one for providers that need it.
        """
        self.client = client or httpx.AsyncClient(timeout=60.0)  # Longer timeout for embeddings
        self._providers: Dict[str, BaseEmbeddingProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all supported embedding providers."""
        self._providers = {
            "openai": OpenAIEmbeddingProvider(self.client),
            "gemini": GeminiEmbeddingProvider(self.client),
            "anthropic": AnthropicEmbeddingProvider(self.client),
            "openrouter": OpenRouterEmbeddingProvider(self.client)
        }
    
    def get_provider(self, provider_name: str) -> BaseEmbeddingProvider:
        """
        Get a provider instance by name.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider instance
            
        Raises:
            HTTPException: If provider is not supported
        """
        if provider_name not in self._providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Embedding provider '{provider_name}' is not supported. "
                       f"Supported providers: {list(self._providers.keys())}"
            )
        
        return self._providers[provider_name]
    
    def get_supported_providers(self) -> List[str]:
        """
        Get list of supported provider names.
        
        Returns:
            List of supported provider names
        """
        return list(self._providers.keys())
    
    def get_all_providers(self) -> Dict[str, BaseEmbeddingProvider]:
        """
        Get all provider instances.
        
        Returns:
            Dictionary mapping provider names to provider instances
        """
        return self._providers.copy()
    
    async def validate_api_key(self, provider_name: str, api_key: Optional[str] = None) -> bool:
        """
        Validate API key for a specific provider.
        
        Args:
            provider_name: Name of the provider
            api_key: API key to validate
            
        Returns:
            True if API key is valid, False otherwise
            
        Raises:
            HTTPException: If provider is not supported
        """
        provider = self.get_provider(provider_name)
        return await provider.validate_api_key(api_key)
    
    async def generate_embeddings(
        self,
        provider_name: str,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> List[List[float]]:
        """
        Generate embeddings using specified provider.
        
        Args:
            provider_name: Name of the provider
            texts: List of texts to embed
            model: Model name
            api_key: API key for the provider
            config: Optional configuration parameters
            
        Returns:
            List of embedding vectors
            
        Raises:
            HTTPException: If provider is not supported or generation fails
        """
        provider = self.get_provider(provider_name)
        return await provider.generate_embeddings(texts, model, api_key, config)
    
    def get_available_models(self, provider_name: str) -> List[str]:
        """
        Get available models for a specific provider (static fallback).
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            List of available model names
            
        Raises:
            HTTPException: If provider is not supported
        """
        provider = self.get_provider(provider_name)
        return provider.get_available_models()
    
    async def get_available_models_dynamic(self, provider_name: str, api_key: str) -> List[str]:
        """
        Get available models for a specific provider from API.
        
        Args:
            provider_name: Name of the provider
            api_key: API key for the provider
            
        Returns:
            List of available model names
            
        Raises:
            HTTPException: If provider is not supported
        """
        provider = self.get_provider(provider_name)
        return await provider.get_available_models_dynamic(api_key)
    
    def get_all_available_models(self) -> Dict[str, List[str]]:
        """
        Get available models for all providers.
        
        Returns:
            Dictionary mapping provider names to their available models
        """
        return {
            provider_name: provider.get_available_models()
            for provider_name, provider in self._providers.items()
        }
    
    def get_embedding_dimension(self, provider_name: str, model: str) -> int:
        """
        Get embedding dimension for a specific provider and model.
        
        Args:
            provider_name: Name of the provider
            model: Model name
            
        Returns:
            Embedding dimension
            
        Raises:
            HTTPException: If provider is not supported or model is unknown
        """
        provider = self.get_provider(provider_name)
        return provider.get_embedding_dimension(model)
    
    def get_provider_info(self, provider_name: str) -> Dict[str, any]:
        """
        Get information about a specific provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Dictionary containing provider information
            
        Raises:
            HTTPException: If provider is not supported
        """
        provider = self.get_provider(provider_name)
        
        # Get dimensions for all models
        model_dimensions = {}
        for model in provider.get_available_models():
            try:
                model_dimensions[model] = provider.get_embedding_dimension(model)
            except Exception as e:
                logger.warning(f"Failed to get dimension for {provider_name} model {model}: {e}")
                model_dimensions[model] = None
        
        return {
            "name": provider.provider_name,
            "base_url": provider.base_url,
            "requires_api_key": provider.requires_api_key,
            "available_models": provider.get_available_models(),
            "model_dimensions": model_dimensions,
            "default_config": provider.get_default_config()
        }
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about all supported providers.
        
        Returns:
            Dictionary mapping provider names to their information
        """
        providers_info = {}
        for provider_name in self.get_supported_providers():
            try:
                providers_info[provider_name] = self.get_provider_info(provider_name)
            except Exception as e:
                logger.error(f"Failed to get info for embedding provider {provider_name}: {e}")
                # Continue with other providers
                continue
        
        return providers_info
    
    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self.client:
            await self.client.aclose()