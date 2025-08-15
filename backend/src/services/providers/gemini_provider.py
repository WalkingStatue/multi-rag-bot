"""
Gemini provider implementation.
"""
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, status

from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """Gemini provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    @property
    def base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """Get headers for Gemini API requests."""
        return {
            "Content-Type": "application/json"
        }
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Gemini API key by listing models."""
        try:
            url = f"{self.base_url}/models?key={api_key}"
            headers = self.get_headers(api_key)
            
            response = await self.client.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False
    
    async def generate_response(
        self,
        model: str,
        prompt: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response using Gemini API."""
        url = f"{self.base_url}/models/{model}:generateContent?key={api_key}"
        headers = self.get_headers(api_key)
        
        # Merge default config with provided config
        default_config = self.get_default_config()
        if config:
            default_config.update(config)
        
        # Parse the prompt to extract conversation context if available
        system_instruction, contents = self._parse_prompt_to_contents(prompt)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": default_config.get("temperature", 0.7),
                "maxOutputTokens": default_config.get("max_tokens", 1000),
                "topP": default_config.get("top_p", 1.0)
            }
        }
        
        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        # Add safety settings to prevent blocking
        payload["safetySettings"] = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if response was blocked by safety filters
            if "candidates" not in data or not data["candidates"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Response blocked by Gemini safety filters"
                )
            
            candidate = data["candidates"][0]
            if "content" not in candidate or "parts" not in candidate["content"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid response format from Gemini API"
                )
            
            return candidate["content"]["parts"][0]["text"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Try to get more specific error from response
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("error", {}).get("message", "Bad request")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Gemini API error: {error_message}"
                    )
                except:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request to Gemini API"
                    )
            elif e.response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Gemini API key or insufficient permissions"
                )
            elif e.response.status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Gemini API rate limit exceeded"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Gemini API error: {e.response.status_code}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Gemini response: {str(e)}"
            )
    
    def _parse_prompt_to_contents(self, prompt: str) -> tuple[str, List[Dict[str, Any]]]:
        """Parse a formatted prompt into Gemini contents format with system instruction."""
        system_instruction = ""
        contents = []
        
        # Split prompt into sections
        sections = prompt.split('\n\n')
        current_content = []
        
        for section in sections:
            if section.startswith('System:'):
                if current_content:
                    contents.append({"role": "user", "parts": [{"text": '\n\n'.join(current_content)}]})
                    current_content = []
                system_instruction = section[7:].strip()  # Remove 'System:' prefix
            elif section.startswith('Conversation History:'):
                if current_content:
                    contents.append({"role": "user", "parts": [{"text": '\n\n'.join(current_content)}]})
                    current_content = []
                # Parse conversation history
                history_content = section[21:].strip()  # Remove 'Conversation History:' prefix
                history_contents = self._parse_conversation_history(history_content)
                contents.extend(history_contents)
            elif section.startswith('User:'):
                if current_content:
                    contents.append({"role": "user", "parts": [{"text": '\n\n'.join(current_content)}]})
                    current_content = []
                user_content = section[5:].strip()  # Remove 'User:' prefix
                contents.append({"role": "user", "parts": [{"text": user_content}]})
            elif section.startswith('Assistant:'):
                # This is just a prompt continuation, ignore
                continue
            else:
                # Add to current content (context, etc.)
                current_content.append(section)
        
        # Add any remaining content as user message
        if current_content:
            contents.append({"role": "user", "parts": [{"text": '\n\n'.join(current_content)}]})
        
        # Ensure we have at least one content
        if not contents:
            contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        return system_instruction, contents
    
    def _parse_conversation_history(self, history_content: str) -> List[Dict[str, Any]]:
        """Parse conversation history into Gemini contents."""
        contents = []
        lines = history_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('User:'):
                contents.append({"role": "user", "parts": [{"text": line[5:].strip()}]})
            elif line.startswith('Assistant:'):
                contents.append({"role": "model", "parts": [{"text": line[10:].strip()}]})
        
        return contents
    
    def get_available_models(self) -> List[str]:
        """Get list of available Gemini models (static fallback)."""
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro"
        ]
    
    def get_model_max_tokens(self, model: str) -> int:
        """Get default max tokens for a specific model."""
        model_limits = {
            "gemini-pro": 2048,
            "gemini-pro-vision": 2048,
            "gemini-1.5-pro": 8192,
            "gemini-1.5-flash": 8192,
            "gemini-1.0-pro": 2048
        }
        return model_limits.get(model, 2048)  # Default to 2048 if model not found
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Gemini provider."""
        return {
            "temperature": 0.7,
            "max_tokens": 2048,  # Will be overridden by model-specific value
            "top_p": 1.0
        }
    
    async def _fetch_models_from_api(self, api_key: str) -> List[str]:
        """Fetch available models from Gemini API."""
        url = f"{self.base_url}/models?key={api_key}"
        headers = self.get_headers(api_key)
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        models = []
        
        # Extract model names from the response
        for model in data.get("models", []):
            model_name = model.get("name", "")
            # Remove the "models/" prefix if present
            if model_name.startswith("models/"):
                model_name = model_name[7:]
            
            # Filter for text generation models only
            supported_methods = model.get("supportedGenerationMethods", [])
            if "generateContent" in supported_methods:
                models.append(model_name)
        
        # Sort models with newer versions first
        models.sort(key=lambda x: (not x.startswith("gemini-1.5"), not x.startswith("gemini-pro"), x))
        
        return models if models else self.get_available_models()