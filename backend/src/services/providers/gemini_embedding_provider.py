"""
Google Gemini embedding provider implementation.
"""
import logging
from typing import List, Optional, Dict, Any
import httpx
from fastapi import HTTPException, status

from .embedding_base import BaseEmbeddingProvider


logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    @property
    def base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta"
    
    async def validate_api_key(self, api_key: Optional[str] = None) -> bool:
        """Validate Gemini API key by making a test request."""
        if not api_key:
            return False
        
        try:
            # Test with a simple embedding request
            response = await self.client.post(
                f"{self.base_url}/models/embedding-001:embedContent",
                params={"key": api_key},
                json={
                    "model": "models/embedding-001",
                    "content": {
                        "parts": [{"text": "test"}]
                    }
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Gemini API key validation failed: {e}")
            return False
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> List[List[float]]:
        """Generate embeddings using Gemini API."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key is required for Gemini embeddings"
            )
        
        if not texts:
            return []
        
        try:
            embeddings = []
            
            # Gemini API processes one text at a time
            for text in texts:
                payload = {
                    "model": f"models/{model}",
                    "content": {
                        "parts": [{"text": text}]
                    }
                }
                
                # Add any additional config parameters
                if config:
                    payload.update(config)
                
                response = await self.client.post(
                    f"{self.base_url}/models/{model}:embedContent",
                    params={"key": api_key},
                    json=payload
                )
                
                if response.status_code != 200:
                    error_detail = f"Gemini API error: {response.status_code}"
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
                if "embedding" in result and "values" in result["embedding"]:
                    embeddings.append(result["embedding"]["values"])
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invalid response format from Gemini API"
                    )
            
            return embeddings
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gemini embedding generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate embeddings: {str(e)}"
            )
    
    def get_available_models(self) -> List[str]:
        """Get list of available Gemini embedding models (static fallback)."""
        return [
            "embedding-001",
            "text-embedding-004"
        ]
    
    async def get_available_models_dynamic(self, api_key: str) -> List[str]:
        """Get list of available Gemini embedding models from API."""
        if not api_key:
            return self.get_available_models()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/models",
                params={"key": api_key}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch Gemini models: {response.status_code}")
                return self.get_available_models()
            
            result = response.json()
            embedding_models = []
            
            for model in result.get("models", []):
                model_name = model.get("name", "")
                # Extract model ID from full name (e.g., "models/embedding-001" -> "embedding-001")
                if "embedding" in model_name.lower():
                    model_id = model_name.split("/")[-1] if "/" in model_name else model_name
                    embedding_models.append(model_id)
            
            # Sort models
            embedding_models.sort()
            
            # Return dynamic models if found, otherwise fallback to static
            return embedding_models if embedding_models else self.get_available_models()
            
        except Exception as e:
            logger.error(f"Failed to fetch Gemini embedding models: {e}")
            return self.get_available_models()
    
    def get_embedding_dimension(self, model: str) -> int:
        """Get embedding dimension for Gemini models."""
        dimensions = {
            "embedding-001": 768,
            "text-embedding-004": 768
        }
        
        if model not in dimensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown Gemini embedding model: {model}"
            )
        
        return dimensions[model]
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Gemini embeddings."""
        return {}