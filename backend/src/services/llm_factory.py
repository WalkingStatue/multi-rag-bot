"""
LLM client factory for dynamic provider selection.
"""
from typing import Dict, Optional
import httpx
from fastapi import HTTPException, status

from .providers import (
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    OpenRouterProvider,
    GeminiProvider
)


class LLMClientFactory:
    """Factory for creating LLM provider clients."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize the factory.
        
        Args:
            client: Optional HTTP client to use. If None, creates a new one.
        """
        self.client = client or httpx.AsyncClient(timeout=30.0)
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all supported providers."""
        self._providers = {
            "openai": OpenAIProvider(self.client),
            "anthropic": AnthropicProvider(self.client),
            "openrouter": OpenRouterProvider(self.client),
            "gemini": GeminiProvider(self.client)
        }
    
    def get_provider(self, provider_name: str) -> BaseLLMProvider:
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
                detail=f"Provider '{provider_name}' is not supported. "
                       f"Supported providers: {list(self._providers.keys())}"
            )
        
        return self._providers[provider_name]
    
    def get_supported_providers(self) -> list[str]:
        """
        Get list of supported provider names.
        
        Returns:
            List of supported provider names
        """
        return list(self._providers.keys())
    
    def get_all_providers(self) -> Dict[str, BaseLLMProvider]:
        """
        Get all provider instances.
        
        Returns:
            Dictionary mapping provider names to provider instances
        """
        return self._providers.copy()
    
    async def validate_api_key(self, provider_name: str, api_key: str) -> bool:
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
    
    async def generate_response(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        api_key: str,
        config: Optional[Dict] = None
    ) -> str:
        """
        Generate response using specified provider.
        
        Args:
            provider_name: Name of the provider
            model: Model name
            prompt: Input prompt
            api_key: API key for the provider
            config: Optional configuration parameters
            
        Returns:
            Generated response text
            
        Raises:
            HTTPException: If provider is not supported or generation fails
        """
        provider = self.get_provider(provider_name)
        return await provider.generate_response(model, prompt, api_key, config)
    
    def get_available_models(self, provider_name: str) -> list[str]:
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
    
    async def get_available_models_dynamic(self, provider_name: str, api_key: str) -> list[str]:
        """
        Get available models for a specific provider dynamically from API.
        
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
    
    def get_all_available_models(self) -> Dict[str, list[str]]:
        """
        Get available models for all providers.
        
        Returns:
            Dictionary mapping provider names to their available models
        """
        return {
            provider_name: provider.get_available_models()
            for provider_name, provider in self._providers.items()
        }
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()