"""
Unified API Key Management System for RAG Pipeline.

This module provides a centralized approach to API key resolution with fallback strategies,
caching, and comprehensive error handling for all RAG operations.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.user import User
from .user_service import UserService
from .embedding_service import EmbeddingProviderService


logger = logging.getLogger(__name__)


class APIKeySource(Enum):
    """Sources for API key resolution."""
    BOT_OWNER = "bot_owner"
    REQUESTING_USER = "requesting_user"
    FALLBACK = "fallback"


@dataclass
class APIKeyValidationResult:
    """Result of API key validation."""
    valid: bool
    source: Optional[APIKeySource] = None
    provider: Optional[str] = None
    error: Optional[str] = None
    cached: bool = False
    validation_time: Optional[float] = None


@dataclass
class APIKeyResolutionResult:
    """Result of API key resolution process."""
    api_key: Optional[str] = None
    source: Optional[APIKeySource] = None
    provider: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    fallback_attempted: bool = False
    cached: bool = False


@dataclass
class APIKeyAvailabilityCheck:
    """Result of API key availability check."""
    available: bool
    sources_checked: List[APIKeySource]
    valid_sources: List[APIKeySource]
    provider: str
    error: Optional[str] = None
    recommendations: List[str] = None


class UnifiedAPIKeyManager:
    """
    Unified API Key Management System.
    
    Implements consistent API key strategy that tries bot owner first, then user fallback,
    with validation caching and comprehensive error handling.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the unified API key manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.user_service = UserService(db)
        self.embedding_service = EmbeddingProviderService()
        
        # Validation cache with TTL
        self._validation_cache: Dict[str, Tuple[bool, datetime]] = {}
        self._cache_ttl = timedelta(minutes=15)  # Cache validation results for 15 minutes
        
        # Configuration
        self.max_validation_retries = 2
        self.validation_timeout = 10.0  # seconds
    
    def _get_cache_key(self, provider: str, api_key_hash: str) -> str:
        """Generate cache key for API key validation."""
        return f"{provider}:{api_key_hash[:8]}"  # Use first 8 chars of hash for privacy
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached validation result is still valid."""
        if cache_key not in self._validation_cache:
            return False
        
        _, cached_time = self._validation_cache[cache_key]
        return datetime.utcnow() - cached_time < self._cache_ttl
    
    def _cache_validation_result(self, cache_key: str, is_valid: bool) -> None:
        """Cache validation result with timestamp."""
        self._validation_cache[cache_key] = (is_valid, datetime.utcnow())
    
    def _clear_expired_cache(self) -> None:
        """Clear expired cache entries."""
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, (_, cached_time) in self._validation_cache.items()
            if current_time - cached_time >= self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._validation_cache[key]
    
    async def validate_api_key_with_cache(
        self, 
        provider: str, 
        api_key: str
    ) -> APIKeyValidationResult:
        """
        Validate API key with caching to avoid repeated validation calls.
        
        Args:
            provider: Provider name (openai, anthropic, gemini, etc.)
            api_key: API key to validate
            
        Returns:
            APIKeyValidationResult with validation status and metadata
        """
        start_time = time.time()
        
        # Generate cache key (use hash for privacy)
        import hashlib
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        cache_key = self._get_cache_key(provider, api_key_hash)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            cached_result, _ = self._validation_cache[cache_key]
            logger.debug(f"Using cached validation result for {provider}: {cached_result}")
            
            return APIKeyValidationResult(
                valid=cached_result,
                provider=provider,
                cached=True,
                validation_time=time.time() - start_time
            )
        
        # Perform validation with retry logic
        validation_error = None
        for attempt in range(self.max_validation_retries):
            try:
                # Use asyncio.wait_for to implement timeout
                is_valid = await asyncio.wait_for(
                    self.embedding_service.validate_api_key(provider, api_key),
                    timeout=self.validation_timeout
                )
                
                # Cache the result
                self._cache_validation_result(cache_key, is_valid)
                
                return APIKeyValidationResult(
                    valid=is_valid,
                    provider=provider,
                    cached=False,
                    validation_time=time.time() - start_time
                )
                
            except asyncio.TimeoutError:
                validation_error = f"API key validation timed out for {provider}"
                logger.warning(f"Attempt {attempt + 1}: {validation_error}")
                
            except Exception as e:
                validation_error = f"API key validation failed for {provider}: {str(e)}"
                logger.warning(f"Attempt {attempt + 1}: {validation_error}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_validation_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))  # Progressive delay
        
        # All attempts failed
        logger.error(f"API key validation failed after {self.max_validation_retries} attempts: {validation_error}")
        
        return APIKeyValidationResult(
            valid=False,
            provider=provider,
            error=validation_error,
            cached=False,
            validation_time=time.time() - start_time
        )
    
    async def get_unified_api_key(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        validate_key: bool = True
    ) -> APIKeyResolutionResult:
        """
        Get API key using unified strategy: bot owner first, then user fallback.
        
        Args:
            bot_id: Bot identifier
            user_id: Requesting user identifier
            provider: Provider name (openai, anthropic, gemini, etc.)
            validate_key: Whether to validate the API key before returning
            
        Returns:
            APIKeyResolutionResult with resolved API key and metadata
        """
        # Clear expired cache entries periodically
        self._clear_expired_cache()
        
        # Get bot information
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return APIKeyResolutionResult(
                success=False,
                error=f"Bot {bot_id} not found",
                provider=provider
            )
        
        # Strategy 1: Try bot owner's API key first
        logger.debug(f"Trying bot owner's API key for {provider}")
        owner_api_key = self.user_service.get_user_api_key(bot.owner_id, provider)
        
        if owner_api_key:
            if validate_key:
                validation_result = await self.validate_api_key_with_cache(provider, owner_api_key)
                if validation_result.valid:
                    logger.info(f"Using bot owner's API key for {provider}")
                    return APIKeyResolutionResult(
                        api_key=owner_api_key,
                        source=APIKeySource.BOT_OWNER,
                        provider=provider,
                        success=True,
                        cached=validation_result.cached
                    )
                else:
                    logger.warning(f"Bot owner's API key invalid for {provider}: {validation_result.error}")
            else:
                # Skip validation, return owner's key
                return APIKeyResolutionResult(
                    api_key=owner_api_key,
                    source=APIKeySource.BOT_OWNER,
                    provider=provider,
                    success=True
                )
        
        # Strategy 2: Fall back to requesting user's API key
        logger.debug(f"Trying requesting user's API key for {provider}")
        user_api_key = self.user_service.get_user_api_key(user_id, provider)
        
        if user_api_key:
            if validate_key:
                validation_result = await self.validate_api_key_with_cache(provider, user_api_key)
                if validation_result.valid:
                    logger.info(f"Using requesting user's API key for {provider}")
                    return APIKeyResolutionResult(
                        api_key=user_api_key,
                        source=APIKeySource.REQUESTING_USER,
                        provider=provider,
                        success=True,
                        fallback_attempted=True,
                        cached=validation_result.cached
                    )
                else:
                    logger.warning(f"Requesting user's API key invalid for {provider}: {validation_result.error}")
            else:
                # Skip validation, return user's key
                return APIKeyResolutionResult(
                    api_key=user_api_key,
                    source=APIKeySource.REQUESTING_USER,
                    provider=provider,
                    success=True,
                    fallback_attempted=True
                )
        
        # No valid API key found
        error_msg = self._generate_api_key_error_message(provider, bot.owner_id, user_id)
        
        return APIKeyResolutionResult(
            success=False,
            error=error_msg,
            provider=provider,
            fallback_attempted=True
        )
    
    def _generate_api_key_error_message(
        self,
        provider: str,
        bot_owner_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> str:
        """
        Generate specific error message indicating which provider needs configuration.
        
        Args:
            provider: Provider name
            bot_owner_id: Bot owner user ID
            user_id: Requesting user ID
            
        Returns:
            Detailed error message with remediation steps
        """
        provider_urls = {
            "openai": "https://platform.openai.com/api-keys",
            "anthropic": "https://console.anthropic.com/",
            "gemini": "https://makersuite.google.com/app/apikey",
            "openrouter": "https://openrouter.ai/keys"
        }
        
        provider_name = provider.title()
        setup_url = provider_urls.get(provider, f"{provider} provider website")
        
        if bot_owner_id == user_id:
            # User is the bot owner
            return (
                f"No valid API key configured for {provider_name}. "
                f"Please add your {provider_name} API key in your profile settings. "
                f"You can get an API key from: {setup_url}"
            )
        else:
            # User is not the bot owner
            return (
                f"No valid API key available for {provider_name}. "
                f"Either the bot owner needs to configure their {provider_name} API key, "
                f"or you can add your own {provider_name} API key in your profile settings. "
                f"Get an API key from: {setup_url}"
            )
    
    async def check_api_key_availability(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str
    ) -> APIKeyAvailabilityCheck:
        """
        Check API key availability before operations without retrieving the actual key.
        
        Args:
            bot_id: Bot identifier
            user_id: Requesting user identifier
            provider: Provider name
            
        Returns:
            APIKeyAvailabilityCheck with availability status and recommendations
        """
        # Get bot information
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return APIKeyAvailabilityCheck(
                available=False,
                sources_checked=[],
                valid_sources=[],
                provider=provider,
                error=f"Bot {bot_id} not found"
            )
        
        sources_checked = []
        valid_sources = []
        recommendations = []
        
        # Check bot owner's API key
        sources_checked.append(APIKeySource.BOT_OWNER)
        owner_api_key = self.user_service.get_user_api_key(bot.owner_id, provider)
        
        if owner_api_key:
            # Validate owner's key
            validation_result = await self.validate_api_key_with_cache(provider, owner_api_key)
            if validation_result.valid:
                valid_sources.append(APIKeySource.BOT_OWNER)
            else:
                recommendations.append(f"Bot owner's {provider} API key is invalid and needs to be updated")
        else:
            recommendations.append(f"Bot owner should configure {provider} API key for optimal performance")
        
        # Check requesting user's API key (if different from owner)
        if user_id != bot.owner_id:
            sources_checked.append(APIKeySource.REQUESTING_USER)
            user_api_key = self.user_service.get_user_api_key(user_id, provider)
            
            if user_api_key:
                # Validate user's key
                validation_result = await self.validate_api_key_with_cache(provider, user_api_key)
                if validation_result.valid:
                    valid_sources.append(APIKeySource.REQUESTING_USER)
                else:
                    recommendations.append(f"Your {provider} API key is invalid and needs to be updated")
            else:
                recommendations.append(f"You can add your own {provider} API key as a fallback option")
        
        # Determine availability
        available = len(valid_sources) > 0
        
        if not available and not recommendations:
            recommendations.append(f"Configure a valid {provider} API key to use this bot")
        
        return APIKeyAvailabilityCheck(
            available=available,
            sources_checked=sources_checked,
            valid_sources=valid_sources,
            provider=provider,
            recommendations=recommendations
        )
    
    async def get_fallback_api_keys(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        providers: List[str]
    ) -> Dict[str, APIKeyResolutionResult]:
        """
        Get API keys for multiple providers with fallback logic.
        
        Args:
            bot_id: Bot identifier
            user_id: Requesting user identifier
            providers: List of provider names
            
        Returns:
            Dictionary mapping provider names to resolution results
        """
        results = {}
        
        # Process providers concurrently
        tasks = [
            self.get_unified_api_key(bot_id, user_id, provider)
            for provider in providers
        ]
        
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, result in zip(providers, provider_results):
            if isinstance(result, Exception):
                results[provider] = APIKeyResolutionResult(
                    success=False,
                    error=f"Failed to resolve API key for {provider}: {str(result)}",
                    provider=provider
                )
            else:
                results[provider] = result
        
        return results
    
    def get_api_key_configuration_suggestions(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str
    ) -> List[str]:
        """
        Get specific remediation suggestions for API key configuration issues.
        
        Args:
            bot_id: Bot identifier
            user_id: Requesting user identifier
            provider: Provider name
            
        Returns:
            List of specific remediation steps
        """
        suggestions = []
        
        # Get bot information
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            return [f"Bot {bot_id} not found"]
        
        # Check current API key status
        owner_api_key = self.user_service.get_user_api_key(bot.owner_id, provider)
        user_api_key = self.user_service.get_user_api_key(user_id, provider)
        
        provider_urls = {
            "openai": "https://platform.openai.com/api-keys",
            "anthropic": "https://console.anthropic.com/",
            "gemini": "https://makersuite.google.com/app/apikey",
            "openrouter": "https://openrouter.ai/keys"
        }
        
        provider_name = provider.title()
        setup_url = provider_urls.get(provider, f"{provider} provider website")
        
        if not owner_api_key and not user_api_key:
            # No API keys configured
            if bot.owner_id == user_id:
                suggestions.append(f"Configure your {provider_name} API key in profile settings")
            else:
                suggestions.append(f"Ask the bot owner to configure their {provider_name} API key")
                suggestions.append(f"Or configure your own {provider_name} API key as a fallback")
            
            suggestions.append(f"Get an API key from: {setup_url}")
        
        elif not owner_api_key and user_api_key:
            # Only user has API key
            suggestions.append(f"Bot owner should configure {provider_name} API key for better performance")
            suggestions.append("Your API key will be used as fallback")
        
        elif owner_api_key and not user_api_key:
            # Only owner has API key
            if bot.owner_id != user_id:
                suggestions.append(f"Consider adding your own {provider_name} API key as backup")
        
        else:
            # Both have API keys
            suggestions.append(f"Both bot owner and user have {provider_name} API keys configured")
            suggestions.append("Bot owner's key will be used first, with user's key as fallback")
        
        return suggestions
    
    def clear_validation_cache(self, provider: Optional[str] = None) -> int:
        """
        Clear validation cache entries.
        
        Args:
            provider: Optional provider to clear cache for (clears all if None)
            
        Returns:
            Number of cache entries cleared
        """
        if provider is None:
            # Clear all cache entries
            cleared_count = len(self._validation_cache)
            self._validation_cache.clear()
            logger.info(f"Cleared all {cleared_count} validation cache entries")
            return cleared_count
        
        # Clear cache entries for specific provider
        keys_to_remove = [
            key for key in self._validation_cache.keys()
            if key.startswith(f"{provider}:")
        ]
        
        for key in keys_to_remove:
            del self._validation_cache[key]
        
        logger.info(f"Cleared {len(keys_to_remove)} validation cache entries for {provider}")
        return len(keys_to_remove)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get validation cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        current_time = datetime.utcnow()
        
        total_entries = len(self._validation_cache)
        expired_entries = sum(
            1 for _, cached_time in self._validation_cache.values()
            if current_time - cached_time >= self._cache_ttl
        )
        
        valid_entries = total_entries - expired_entries
        
        # Count by provider
        provider_counts = {}
        for key in self._validation_cache.keys():
            provider = key.split(':')[0]
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_minutes": self._cache_ttl.total_seconds() / 60,
            "provider_counts": provider_counts
        }