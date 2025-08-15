"""
OpenRouter provider implementation.
"""
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, status

from .base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider implementation."""
    
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
            "HTTP-Referer": "https://multi-bot-rag-platform.com",  # Required by OpenRouter
            "X-Title": "Multi-Bot RAG Platform"  # Optional but recommended
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
    
    async def generate_response(
        self,
        model: str,
        prompt: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response using OpenRouter API."""
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
            "top_p": default_config.get("top_p", 1.0)
        }
        
        # Add frequency and presence penalty if supported by the model
        if "frequency_penalty" in default_config:
            payload["frequency_penalty"] = default_config["frequency_penalty"]
        if "presence_penalty" in default_config:
            payload["presence_penalty"] = default_config["presence_penalty"]
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
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
                detail=f"Failed to generate OpenRouter response: {str(e)}"
            )
    
    def _parse_prompt_to_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Parse a formatted prompt into OpenRouter messages format."""
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
        """Get list of available OpenRouter models (static fallback)."""
        return [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/gpt-4-turbo",
            "openai/gpt-4",
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet",
            "anthropic/claude-3-haiku",
            "anthropic/claude-2",
            "anthropic/claude-instant-1",
            "meta-llama/llama-2-70b-chat",
            "meta-llama/llama-2-13b-chat",
            "mistralai/mixtral-8x7b-instruct",
            "mistralai/mistral-7b-instruct",
            "google/gemini-pro",
            "google/palm-2-chat-bison",
            "cohere/command",
            "cohere/command-light"
        ]
    
    def get_model_max_tokens(self, model: str) -> int:
        """Get default max tokens for a specific model."""
        model_limits = {
            "openai/gpt-4o": 4096,
            "openai/gpt-4o-mini": 16384,
            "openai/gpt-4-turbo": 4096,
            "openai/gpt-4": 8192,
            "openai/gpt-3.5-turbo": 4096,
            "anthropic/claude-3-opus": 4096,
            "anthropic/claude-3-sonnet": 4096,
            "anthropic/claude-3-haiku": 4096,
            "anthropic/claude-2": 4096,
            "anthropic/claude-instant-1": 4096,
            "meta-llama/llama-2-70b-chat": 4096,
            "meta-llama/llama-2-13b-chat": 4096,
            "mistralai/mixtral-8x7b-instruct": 4096,
            "mistralai/mistral-7b-instruct": 4096,
            "google/gemini-pro": 2048,
            "google/palm-2-chat-bison": 1024,
            "cohere/command": 4096,
            "cohere/command-light": 4096
        }
        return model_limits.get(model, 2048)  # Default to 2048 if model not found
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for OpenRouter provider."""
        return {
            "temperature": 0.7,
            "max_tokens": 2048,  # Will be overridden by model-specific value
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
    
    async def _fetch_models_from_api(self, api_key: str) -> List[str]:
        """Fetch available models from OpenRouter API."""
        url = f"{self.base_url}/models"
        headers = self.get_headers(api_key)
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        models = []
        
        # Extract model IDs from the response
        for model in data.get("data", []):
            model_id = model.get("id", "")
            if model_id:
                models.append(model_id)
        
        # Sort models by popularity/preference
        priority_prefixes = ["openai/gpt-4", "anthropic/claude-3", "openai/gpt-3.5", "anthropic/claude-2"]
        
        def sort_key(model):
            for i, prefix in enumerate(priority_prefixes):
                if model.startswith(prefix):
                    return (i, model)
            return (len(priority_prefixes), model)
        
        models.sort(key=sort_key)
        
        return models if models else self.get_available_models()