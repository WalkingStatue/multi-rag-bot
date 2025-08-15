"""
Base abstract class for embedding providers.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import httpx


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> Optional[str]:
        """Return the base URL for the provider API (None for local providers)."""
        pass
    
    @abstractmethod
    async def validate_api_key(self, api_key: Optional[str] = None) -> bool:
        """
        Validate API key for this provider.
        
        Args:
            api_key: API key to validate (None for local providers)
            
        Returns:
            True if API key is valid or not required, False otherwise
        """
        pass
    
    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for the given texts.
        
        Args:
            texts: List of texts to embed
            model: Model name to use
            api_key: API key for the provider (None for local providers)
            config: Optional configuration parameters
            
        Returns:
            List of embedding vectors (one per input text)
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
        Get list of available models for this provider from API (optional override).
        
        Args:
            api_key: API key for the provider
            
        Returns:
            List of available model names
        """
        # Default implementation returns static models
        return self.get_available_models()
    
    @abstractmethod
    def get_embedding_dimension(self, model: str) -> int:
        """
        Get the embedding dimension for a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Embedding dimension
        """
        pass
    
    def get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Args:
            api_key: API key (None for local providers)
            
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
        return {}
    
    @property
    def requires_api_key(self) -> bool:
        """
        Whether this provider requires an API key.
        
        Returns:
            True if API key is required, False otherwise
        """
        return self.base_url is not None