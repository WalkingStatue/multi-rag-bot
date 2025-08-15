"""
OpenAI provider implementation.
"""
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, status

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def base_url(self) -> str:
        return "https://api.openai.com/v1"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """Get headers for OpenAI API requests."""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key by listing models."""
        try:
            url = f"{self.base_url}/models"
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
        """Generate response using OpenAI API."""
        url = f"{self.base_url}/chat/completions"
        headers = self.get_headers(api_key)
        
        # Merge default config with provided config
        default_config = self.get_default_config()
        if config:
            default_config.update(config)
        
        # Parse the prompt to extract conversation context if available
        messages = self._parse_prompt_to_messages(prompt)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": default_config.get("temperature", 0.7),
            "max_tokens": default_config.get("max_tokens", 1000),
            "top_p": default_config.get("top_p", 1.0),
            "frequency_penalty": default_config.get("frequency_penalty", 0.0),
            "presence_penalty": default_config.get("presence_penalty", 0.0)
        }
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OpenAI API key"
                )
            elif e.response.status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="OpenAI API rate limit exceeded"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OpenAI API error: {e.response.status_code}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate OpenAI response: {str(e)}"
            )
    
    def _parse_prompt_to_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Parse a formatted prompt into OpenAI messages format."""
        messages = []
        
        # Split prompt into sections
        sections = prompt.split('\n\n')
        current_content = []
        
        for section in sections:
            if section.startswith('System:'):
                if current_content:
                    messages.append({"role": "user", "content": '\n\n'.join(current_content)})
                    current_content = []
                system_content = section[7:].strip()  # Remove 'System:' prefix
                messages.append({"role": "system", "content": system_content})
            elif section.startswith('Conversation History:'):
                if current_content:
                    messages.append({"role": "user", "content": '\n\n'.join(current_content)})
                    current_content = []
                # Parse conversation history
                history_content = section[21:].strip()  # Remove 'Conversation History:' prefix
                history_messages = self._parse_conversation_history(history_content)
                messages.extend(history_messages)
            elif section.startswith('User:'):
                if current_content:
                    messages.append({"role": "user", "content": '\n\n'.join(current_content)})
                    current_content = []
                user_content = section[5:].strip()  # Remove 'User:' prefix
                messages.append({"role": "user", "content": user_content})
            elif section.startswith('Assistant:'):
                # This is just a prompt continuation, ignore
                continue
            else:
                # Add to current content (context, etc.)
                current_content.append(section)
        
        # Add any remaining content as user message
        if current_content:
            messages.append({"role": "user", "content": '\n\n'.join(current_content)})
        
        # Ensure we have at least one message
        if not messages:
            messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def _parse_conversation_history(self, history_content: str) -> List[Dict[str, str]]:
        """Parse conversation history into messages."""
        messages = []
        lines = history_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('User:'):
                messages.append({"role": "user", "content": line[5:].strip()})
            elif line.startswith('Assistant:'):
                messages.append({"role": "assistant", "content": line[10:].strip()})
        
        return messages
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models (static fallback)."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-1106"
        ]
    
    def get_model_max_tokens(self, model: str) -> int:
        """Get default max tokens for a specific model."""
        model_limits = {
            "gpt-4o": 4096,
            "gpt-4o-mini": 16384,
            "gpt-4-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4-0125-preview": 4096,
            "gpt-4-1106-preview": 4096,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-0125": 4096,
            "gpt-3.5-turbo-1106": 4096
        }
        return model_limits.get(model, 4096)  # Default to 4096 if model not found
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for OpenAI provider."""
        return {
            "temperature": 0.7,
            "max_tokens": 4096,  # Will be overridden by model-specific value
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
    
    async def _fetch_models_from_api(self, api_key: str) -> List[str]:
        """Fetch available models from OpenAI API."""
        url = f"{self.base_url}/models"
        headers = self.get_headers(api_key)
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        models = []
        
        # Filter for chat completion models only
        for model in data.get("data", []):
            model_id = model.get("id", "")
            # Include GPT models that support chat completions
            if any(prefix in model_id for prefix in ["gpt-4", "gpt-3.5-turbo"]):
                models.append(model_id)
        
        # Sort models with GPT-4 first, then GPT-3.5
        models.sort(key=lambda x: (not x.startswith("gpt-4"), x))
        
        return models if models else self.get_available_models()