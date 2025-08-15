"""
Multi-LLM provider service for API key validation and response generation.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, status

from ..core.config import settings
from .llm_factory import LLMClientFactory


logger = logging.getLogger(__name__)


class LLMProviderService:
    """Service for managing multiple LLM providers and API key validation."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """
        Initialize the LLM provider service.
        
        Args:
            client: Optional HTTP client to use. If None, creates a new one.
        """
        self.factory = LLMClientFactory(client)
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
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
    
    async def validate_api_key(self, provider: str, api_key: str) -> bool:
        """
        Validate API key for a specific provider with retry logic.
        
        Args:
            provider: Provider name (openai, anthropic, openrouter, gemini)
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
    
    async def generate_response(
        self,
        provider: str,
        model: str,
        prompt: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response using specified provider and model with retry logic.
        
        Args:
            provider: Provider name
            model: Model name
            prompt: Input prompt
            api_key: API key for the provider
            config: Optional configuration parameters
            
        Returns:
            Generated response text
            
        Raises:
            HTTPException: If provider not supported or API call fails
        """
        return await self._retry_operation(
            self.factory.generate_response,
            provider,
            model,
            prompt,
            api_key,
            config
        )
    
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
        try:
            provider_instance = self.factory.get_provider(provider)
            
            # Get model-specific max tokens
            model_max_tokens = {}
            for model in provider_instance.get_available_models():
                try:
                    model_max_tokens[model] = provider_instance.get_model_max_tokens(model)
                except Exception as e:
                    logger.warning(f"Failed to get max tokens for {provider} model {model}: {e}")
                    model_max_tokens[model] = provider_instance.get_default_config().get("max_tokens", 1000)
            
            return {
                "name": provider_instance.provider_name,
                "base_url": provider_instance.base_url,
                "available_models": provider_instance.get_available_models(),
                "model_max_tokens": model_max_tokens,
                "default_config": provider_instance.get_default_config()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get info for {provider}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get provider information: {str(e)}"
            )
    
    def get_all_providers_info(self) -> Dict[str, Dict[str, Any]]:
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
                logger.error(f"Failed to get info for {provider_name}: {e}")
                # Continue with other providers
                continue
        
        return providers_info
    
    async def close(self):
        """Close the HTTP client."""
        await self.factory.close()