"""
Anthropic embedding provider implementation.
Note: Anthropic doesn't currently offer embedding models, but this is prepared for future support.
"""
import logging
from typing import List, Optional, Dict, Any
import httpx
from fastapi import HTTPException, status

from .embedding_base import BaseEmbeddingProvider


logger = logging.getLogger(__name__)


class AnthropicEmbeddingProvider(BaseEmbeddingProvider):
    """Anthropic embedding provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def base_url(self) -> str:
        return "https://api.anthropic.com/v1"
    
    def get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get headers for Anthropic API requests."""
        headers = super().get_headers(api_key)
        if api_key:
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        return headers
    
    async def validate_api_key(self, api_key: Optional[str] = None) -> bool:
        """Validate Anthropic API key."""
        if not api_key:
            return False
        
        try:
            # Since Anthropic doesn't have embeddings yet, we'll validate by checking the messages endpoint
            headers = self.get_headers(api_key)
            response = await self.client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "test"}]
                }
            )
            return response.status_code in [200, 400]  # 400 is also valid (means API key works but request is malformed)
        except Exception as e:
            logger.error(f"Anthropic API key validation failed: {e}")
            return False
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings using Anthropic API."""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Anthropic does not currently offer embedding models. Please use OpenAI or Gemini for embeddings."
        )
    
    def get_available_models(self) -> List[str]:
        """Get list of available Anthropic embedding models."""
        # Anthropic doesn't currently offer embedding models
        return []
    
    async def get_available_models_dynamic(self, api_key: str) -> List[str]:
        """Get list of available Anthropic embedding models from API."""
        # Anthropic doesn't currently offer embedding models
        return []
    
    def get_embedding_dimension(self, model: str) -> int:
        """Get embedding dimension for Anthropic models."""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anthropic does not currently offer embedding models"
        )
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Anthropic embeddings."""
        return {}