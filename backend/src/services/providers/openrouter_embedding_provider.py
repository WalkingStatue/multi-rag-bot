"""
OpenRouter embedding provider implementation.
Note: OpenRouter doesn't have dedicated embedding models, so this provider
uses OpenAI-compatible embedding models available through OpenRouter.
"""
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, status

from .embedding_base import BaseEmbeddingProvider


class OpenRouterEmbeddingProvider(BaseEmbeddingProvider):
    """OpenRouter embedding provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "openrouter"
    
    @property
    def base_url(self) -> str:
        return "https://openrouter.ai/api/v1"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """Get headers for OpenRouter API requests."""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://multi-bot-rag-platform.com",
            "X-Title": "Multi-Bot RAG Platform"
        }
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenRouter API key by listing models."""
        try:
            url = f"{self.base_url}/models"
            headers = self.get_headers(api_key)
            
            response = await self.client.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings using OpenRouter API."""
        url = f"{self.base_url}/embeddings"
        headers = self.get_headers(api_key)
        
        # Merge default config with provided config
        default_config = self.get_default_config()
        if config:
            default_config.update(config)
        
        payload = {
            "model": model,
            "input": texts
        }
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OpenRouter API key"
                )
            elif e.response.status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="OpenRouter API rate limit exceeded"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OpenRouter API error: {e.response.status_code}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate OpenRouter embeddings: {str(e)}"
            )
    
    def get_available_models(self) -> List[str]:
        """Get list of available embedding models through OpenRouter."""
        return [
            "openai/text-embedding-3-large",
            "openai/text-embedding-3-small",
            "openai/text-embedding-ada-002"
        ]
    
    def get_embedding_dimension(self, model: str) -> int:
        """Get embedding dimension for a specific model."""
        model_dimensions = {
            "openai/text-embedding-3-large": 3072,
            "openai/text-embedding-3-small": 1536,
            "openai/text-embedding-ada-002": 1536
        }
        return model_dimensions.get(model, 1536)  # Default to 1536 if model not found
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for OpenRouter embedding provider."""
        return {}
    
    async def _fetch_models_from_api(self, api_key: str) -> List[str]:
        """Fetch available embedding models from OpenRouter API."""
        url = f"{self.base_url}/models"
        headers = self.get_headers(api_key)
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        models = []
        
        # Filter for embedding models
        for model in data.get("data", []):
            model_id = model.get("id", "")
            # Look for embedding models
            if "embedding" in model_id.lower():
                models.append(model_id)
        
        # If no embedding models found, return the static list
        return models if models else self.get_available_models()