"""
Base abstract class for LLM providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import httpx


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for the provider API."""
        pass
    
    @abstractmethod
    async def validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key for this provider.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if API key is valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        model: str,
        prompt: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response using this provider.
        
        Args:
            model: Model name
            prompt: Input prompt
            api_key: API key for the provider
            config: Optional configuration parameters
            
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider (static fallback).
        
        Returns:
            List of available model names
        """
        pass
    
    async def get_available_models_dynamic(self, api_key: str) -> List[str]:
        """
        Get list of available models dynamically from the provider API.
        Falls back to static list if API call fails.
        
        Args:
            api_key: API key for the provider
            
        Returns:
            List of available model names
        """
        try:
            return await self._fetch_models_from_api(api_key)
        except Exception:
            # Fall back to static list if dynamic fetch fails
            return self.get_available_models()
    
    async def _fetch_models_from_api(self, api_key: str) -> List[str]:
        """
        Fetch models from the provider API. Override in subclasses.
        
        Args:
            api_key: API key for the provider
            
        Returns:
            List of available model names
            
        Raises:
            NotImplementedError: If not implemented in subclass
        """
        raise NotImplementedError("Subclasses should implement _fetch_models_from_api")
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Args:
            api_key: API key
            
        Returns:
            Dictionary of headers
        """
        return {"Content-Type": "application/json"}
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for this provider.
        
        Returns:
            Dictionary of default configuration values
        """
        return {
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
    
    def get_model_max_tokens(self, model: str) -> int:
        """
        Get default max tokens for a specific model.
        Override in subclasses for model-specific limits.
        
        Args:
            model: Model name
            
        Returns:
            Default max tokens for the model
        """
        return 1000  # Default fallback