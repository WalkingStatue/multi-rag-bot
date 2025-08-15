"""
OpenAI embedding provider implementation.
"""
import logging
from typing import List, Optional, Dict, Any
import httpx
from fastapi import HTTPException, status

from .embedding_base import BaseEmbeddingProvider


logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    def get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get headers for OpenAI API requests."""
        headers = super().get_headers(api_key)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers
    
    async def validate_api_key(self, api_key: Optional[str] = None) -> bool:
        """Validate OpenAI API key by making a test request."""
        if not api_key:
            return False
        
        try:
            headers = self.get_headers(api_key)
            response = await self.client.get(
                f"{self.base_url}/models",
                headers=headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenAI API key validation failed: {e}")
            return False
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key is required for OpenAI embeddings"
            )
        
        if not texts:
            return []
        
        try:
            headers = self.get_headers(api_key)
            payload = {
                "input": texts,
                "model": model,
                "encoding_format": "float"
            }
            
            # Add any additional config parameters
            if config:
                payload.update(config)
            
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = f"OpenAI API error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"].get("message", error_detail)
                except:
                    pass
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
            
            result = response.json()
            embeddings = []
            
            # Sort by index to maintain order
            sorted_data = sorted(result["data"], key=lambda x: x["index"])
            for item in sorted_data:
                embeddings.append(item["embedding"])
            
            return embeddings
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate embeddings: {str(e)}"
            )
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI embedding models (static fallback)."""
        return [
            "text-embedding-3-small",
            "text-embedding-3-large", 
            "text-embedding-ada-002"
        ]
    
    async def get_available_models_dynamic(self, api_key: str) -> List[str]:
        """Get list of available OpenAI embedding models from API."""
        if not api_key:
            return self.get_available_models()
        
        try:
            headers = self.get_headers(api_key)
            response = await self.client.get(
                f"{self.base_url}/models",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch OpenAI models: {response.status_code}")
                return self.get_available_models()
            
            result = response.json()
            embedding_models = []
            
            for model in result.get("data", []):
                model_id = model.get("id", "")
                # Filter for embedding models
                if "embedding" in model_id.lower():
                    embedding_models.append(model_id)
            
            # Sort models with newer ones first
            embedding_models.sort(reverse=True)
            
            # Return dynamic models if found, otherwise fallback to static
            return embedding_models if embedding_models else self.get_available_models()
            
        except Exception as e:
            logger.error(f"Failed to fetch OpenAI embedding models: {e}")
            return self.get_available_models()
    
    def get_embedding_dimension(self, model: str) -> int:
        """Get embedding dimension for OpenAI models."""
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        
        if model not in dimensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown OpenAI embedding model: {model}"
            )
        
        return dimensions[model]
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for OpenAI embeddings."""
        return {
            "encoding_format": "float"
        }