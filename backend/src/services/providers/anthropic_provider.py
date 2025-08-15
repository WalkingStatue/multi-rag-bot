"""
Anthropic provider implementation.
"""
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException, status

from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider implementation."""
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def base_url(self) -> str:
        return "https://api.anthropic.com"
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """Get headers for Anthropic API requests."""
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Anthropic API key by making a minimal test request."""
        try:
            url = f"{self.base_url}/v1/messages"
            headers = self.get_headers(api_key)
            
            # Make a minimal test request
            test_payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            response = await self.client.post(url, headers=headers, json=test_payload)
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
        """Generate response using Anthropic API."""
        url = f"{self.base_url}/v1/messages"
        headers = self.get_headers(api_key)
        
        # Merge default config with provided config
        default_config = self.get_default_config()
        if config:
            default_config.update(config)
        
        # Parse the prompt to extract system message and conversation context
        system_message, messages = self._parse_prompt_to_messages(prompt)
        
        payload = {
            "model": model,
            "max_tokens": default_config.get("max_tokens", 1000),
            "temperature": default_config.get("temperature", 0.7),
            "messages": messages
        }
        
        # Add system message if present
        if system_message:
            payload["system"] = system_message
        
        # Add top_p if specified
        if "top_p" in default_config:
            payload["top_p"] = default_config["top_p"]
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Anthropic API key"
                )
            elif e.response.status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Anthropic API rate limit exceeded"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Anthropic API error: {e.response.status_code}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Anthropic response: {str(e)}"
            )
    
    def _parse_prompt_to_messages(self, prompt: str) -> tuple[str, List[Dict[str, str]]]:
        """Parse a formatted prompt into Anthropic messages format with system message."""
        system_message = ""
        messages = []
        
        # Split prompt into sections
        sections = prompt.split('\n\n')
        current_content = []
        
        for section in sections:
            if section.startswith('System:'):
                if current_content:
                    messages.append({"role": "user", "content": '\n\n'.join(current_content)})
                    current_content = []
                system_message = section[7:].strip()  # Remove 'System:' prefix
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
        
        return system_message, messages
    
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
        """Get list of available Anthropic models (static fallback)."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    def get_model_max_tokens(self, model: str) -> int:
        """Get default max tokens for a specific model."""
        model_limits = {
            "claude-3-opus-20240229": 4096,
            "claude-3-sonnet-20240229": 4096,
            "claude-3-haiku-20240307": 4096,
            "claude-2.1": 4096,
            "claude-2.0": 4096,
            "claude-instant-1.2": 4096
        }
        return model_limits.get(model, 4096)  # Default to 4096 if model not found
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Anthropic provider."""
        return {
            "temperature": 0.7,
            "max_tokens": 4096,  # Will be overridden by model-specific value
            "top_p": 1.0
        }
    
    async def _fetch_models_from_api(self, api_key: str) -> List[str]:
        """
        Fetch available models from Anthropic API.
        Note: Anthropic doesn't have a models endpoint, so we use the static list.
        """
        # Anthropic doesn't provide a models endpoint, so we return the static list
        # but we could potentially test each model to see which ones work
        return self.get_available_models()