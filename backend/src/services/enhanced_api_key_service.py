"""
Enhanced API Key Service with fallback logic and comprehensive error handling.

This service extends the unified API key manager with additional fallback strategies,
error handling, and remediation suggestions for API key configuration issues.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.user import User
from .unified_api_key_manager import (
    UnifiedAPIKeyManager, 
    APIKeyResolutionResult, 
    APIKeySource,
    APIKeyAvailabilityCheck
)
from .user_service import UserService
from .embedding_service import EmbeddingProviderService


logger = logging.getLogger(__name__)


class APIKeyErrorType(Enum):
    """Types of API key errors."""
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"
    VALIDATION_TIMEOUT = "validation_timeout"


@dataclass
class APIKeyError:
    """Detailed API key error information."""
    error_type: APIKeyErrorType
    provider: str
    source: Optional[APIKeySource] = None
    message: str = ""
    remediation_steps: List[str] = None
    retry_after: Optional[int] = None  # seconds


@dataclass
class FallbackResult:
    """Result of fallback API key resolution."""
    success: bool
    api_key: Optional[str] = None
    source: Optional[APIKeySource] = None
    provider: str = ""
    fallback_chain: List[APIKeySource] = None
    errors: List[APIKeyError] = None
    final_error: Optional[str] = None


class EnhancedAPIKeyService:
    """
    Enhanced API Key Service with comprehensive fallback logic and error handling.
    
    This service provides multiple API key sources with intelligent fallback,
    detailed error categorization, and specific remediation guidance.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the enhanced API key service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.unified_manager = UnifiedAPIKeyManager(db)
        self.user_service = UserService(db)
        self.embedding_service = EmbeddingProviderService()
        
        # Configuration
        self.max_fallback_attempts = 3
        self.retry_delays = [1.0, 2.0, 4.0]  # Progressive retry delays
    
    async def get_api_key_with_fallback(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        validate_key: bool = True,
        enable_fallback: bool = True
    ) -> FallbackResult:
        """
        Get API key with comprehensive fallback logic.
        
        Args:
            bot_id: Bot identifier
            user_id: Requesting user identifier
            provider: Provider name
            validate_key: Whether to validate API keys
            enable_fallback: Whether to enable fallback strategies
            
        Returns:
            FallbackResult with resolved API key and detailed error information
        """
        fallback_chain = []
        errors = []
        
        try:
            # Primary attempt: Use unified manager
            primary_result = await self.unified_manager.get_unified_api_key(
                bot_id, user_id, provider, validate_key
            )
            
            if primary_result.success:
                fallback_chain.append(primary_result.source)
                return FallbackResult(
                    success=True,
                    api_key=primary_result.api_key,
                    source=primary_result.source,
                    provider=provider,
                    fallback_chain=fallback_chain
                )
            
            # Primary attempt failed, categorize error
            primary_error = self._categorize_api_key_error(
                provider, primary_result.error, None
            )
            errors.append(primary_error)
            
            if not enable_fallback:
                return FallbackResult(
                    success=False,
                    provider=provider,
                    fallback_chain=fallback_chain,
                    errors=errors,
                    final_error=primary_result.error
                )
            
            # Fallback strategies
            fallback_result = await self._attempt_fallback_strategies(
                bot_id, user_id, provider, validate_key, errors, fallback_chain
            )
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"Unexpected error in API key resolution: {e}")
            
            error = APIKeyError(
                error_type=APIKeyErrorType.NETWORK_ERROR,
                provider=provider,
                message=f"Unexpected error during API key resolution: {str(e)}",
                remediation_steps=["Check system logs", "Retry the operation"]
            )
            errors.append(error)
            
            return FallbackResult(
                success=False,
                provider=provider,
                fallback_chain=fallback_chain,
                errors=errors,
                final_error=str(e)
            )
    
    async def _attempt_fallback_strategies(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        validate_key: bool,
        errors: List[APIKeyError],
        fallback_chain: List[APIKeySource]
    ) -> FallbackResult:
        """
        Attempt various fallback strategies for API key resolution.
        
        Args:
            bot_id: Bot identifier
            user_id: Requesting user identifier
            provider: Provider name
            validate_key: Whether to validate API keys
            errors: List of accumulated errors
            fallback_chain: List of attempted sources
            
        Returns:
            FallbackResult with final resolution status
        """
        # Strategy 1: Try without validation (if validation was enabled)
        if validate_key:
            logger.info(f"Attempting fallback: Skip validation for {provider}")
            
            no_validation_result = await self.unified_manager.get_unified_api_key(
                bot_id, user_id, provider, validate_key=False
            )
            
            if no_validation_result.success:
                fallback_chain.append(no_validation_result.source)
                logger.warning(f"Using unvalidated API key for {provider}")
                
                return FallbackResult(
                    success=True,
                    api_key=no_validation_result.api_key,
                    source=no_validation_result.source,
                    provider=provider,
                    fallback_chain=fallback_chain,
                    errors=errors
                )
        
        # Strategy 2: Try alternative providers (if applicable)
        alternative_result = await self._try_alternative_providers(
            bot_id, user_id, provider, validate_key
        )
        
        if alternative_result.success:
            fallback_chain.append(alternative_result.source)
            return FallbackResult(
                success=True,
                api_key=alternative_result.api_key,
                source=alternative_result.source,
                provider=alternative_result.provider,
                fallback_chain=fallback_chain,
                errors=errors
            )
        
        # Strategy 3: Retry with exponential backoff
        retry_result = await self._retry_with_backoff(
            bot_id, user_id, provider, validate_key
        )
        
        if retry_result.success:
            fallback_chain.append(retry_result.source)
            return FallbackResult(
                success=True,
                api_key=retry_result.api_key,
                source=retry_result.source,
                provider=provider,
                fallback_chain=fallback_chain,
                errors=errors
            )
        
        # All fallback strategies failed
        final_error = self._generate_comprehensive_error_message(errors, provider)
        
        return FallbackResult(
            success=False,
            provider=provider,
            fallback_chain=fallback_chain,
            errors=errors,
            final_error=final_error
        )
    
    async def _try_alternative_providers(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        original_provider: str,
        validate_key: bool
    ) -> APIKeyResolutionResult:
        """
        Try alternative providers that might be compatible.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            original_provider: Original provider that failed
            validate_key: Whether to validate keys
            
        Returns:
            APIKeyResolutionResult for alternative provider
        """
        # Define provider alternatives (for embedding providers)
        provider_alternatives = {
            "openai": ["gemini"],  # If OpenAI fails, try Gemini
            "gemini": ["openai"],  # If Gemini fails, try OpenAI
            "anthropic": ["openai", "gemini"],  # Anthropic alternatives
        }
        
        alternatives = provider_alternatives.get(original_provider, [])
        
        for alternative_provider in alternatives:
            logger.info(f"Trying alternative provider: {alternative_provider}")
            
            try:
                result = await self.unified_manager.get_unified_api_key(
                    bot_id, user_id, alternative_provider, validate_key
                )
                
                if result.success:
                    logger.info(f"Successfully using alternative provider: {alternative_provider}")
                    # Update the provider in the result
                    result.provider = alternative_provider
                    return result
                    
            except Exception as e:
                logger.warning(f"Alternative provider {alternative_provider} also failed: {e}")
                continue
        
        # No alternatives worked
        return APIKeyResolutionResult(
            success=False,
            error=f"No alternative providers available for {original_provider}",
            provider=original_provider
        )
    
    async def _retry_with_backoff(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        validate_key: bool
    ) -> APIKeyResolutionResult:
        """
        Retry API key resolution with exponential backoff.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            provider: Provider name
            validate_key: Whether to validate keys
            
        Returns:
            APIKeyResolutionResult from retry attempts
        """
        for attempt in range(self.max_fallback_attempts):
            try:
                logger.info(f"Retry attempt {attempt + 1} for {provider}")
                
                # Clear cache to force fresh validation
                self.unified_manager.clear_validation_cache(provider)
                
                result = await self.unified_manager.get_unified_api_key(
                    bot_id, user_id, provider, validate_key
                )
                
                if result.success:
                    logger.info(f"Retry successful on attempt {attempt + 1}")
                    return result
                
                # Wait before next retry
                if attempt < self.max_fallback_attempts - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.info(f"Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_fallback_attempts - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    await asyncio.sleep(delay)
        
        return APIKeyResolutionResult(
            success=False,
            error=f"All retry attempts failed for {provider}",
            provider=provider
        )
    
    def _categorize_api_key_error(
        self,
        provider: str,
        error_message: Optional[str],
        source: Optional[APIKeySource]
    ) -> APIKeyError:
        """
        Categorize API key error and provide remediation steps.
        
        Args:
            provider: Provider name
            error_message: Error message from API key resolution
            source: Source that failed
            
        Returns:
            Categorized APIKeyError with remediation steps
        """
        if not error_message:
            error_message = "Unknown API key error"
        
        error_lower = error_message.lower()
        
        # Categorize error type
        if "not found" in error_lower or "no api key" in error_lower:
            error_type = APIKeyErrorType.NOT_FOUND
            remediation_steps = [
                f"Configure {provider} API key in your profile settings",
                f"Ensure the API key is active and not expired",
                f"Check {provider} provider documentation for setup instructions"
            ]
        
        elif "invalid" in error_lower or "unauthorized" in error_lower:
            error_type = APIKeyErrorType.INVALID
            remediation_steps = [
                f"Verify your {provider} API key is correct",
                f"Check if the API key has required permissions",
                f"Generate a new API key if the current one is compromised"
            ]
        
        elif "expired" in error_lower:
            error_type = APIKeyErrorType.EXPIRED
            remediation_steps = [
                f"Generate a new {provider} API key",
                f"Update your profile with the new API key",
                f"Set up API key rotation to prevent future expiration"
            ]
        
        elif "rate limit" in error_lower or "quota" in error_lower:
            error_type = APIKeyErrorType.RATE_LIMITED
            remediation_steps = [
                f"Wait for {provider} rate limits to reset",
                f"Consider upgrading your {provider} plan",
                f"Implement request throttling in your application"
            ]
        
        elif "timeout" in error_lower:
            error_type = APIKeyErrorType.VALIDATION_TIMEOUT
            remediation_steps = [
                f"Check network connectivity to {provider}",
                f"Retry the operation after a brief delay",
                f"Contact {provider} support if timeouts persist"
            ]
        
        else:
            error_type = APIKeyErrorType.NETWORK_ERROR
            remediation_steps = [
                f"Check network connectivity",
                f"Verify {provider} service status",
                f"Retry the operation",
                f"Contact support if the issue persists"
            ]
        
        return APIKeyError(
            error_type=error_type,
            provider=provider,
            source=source,
            message=error_message,
            remediation_steps=remediation_steps
        )
    
    def _generate_comprehensive_error_message(
        self,
        errors: List[APIKeyError],
        provider: str
    ) -> str:
        """
        Generate comprehensive error message with all remediation steps.
        
        Args:
            errors: List of accumulated errors
            provider: Provider name
            
        Returns:
            Comprehensive error message
        """
        if not errors:
            return f"Failed to resolve API key for {provider}"
        
        # Get unique remediation steps
        all_steps = []
        for error in errors:
            if error.remediation_steps:
                all_steps.extend(error.remediation_steps)
        
        unique_steps = list(dict.fromkeys(all_steps))  # Preserve order, remove duplicates
        
        error_summary = f"Failed to resolve API key for {provider} after trying multiple sources."
        
        if unique_steps:
            steps_text = "\n".join(f"• {step}" for step in unique_steps[:5])  # Limit to 5 steps
            error_summary += f"\n\nRecommended actions:\n{steps_text}"
        
        return error_summary
    
    async def validate_multiple_api_keys(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        providers: List[str]
    ) -> Dict[str, APIKeyAvailabilityCheck]:
        """
        Validate API key availability for multiple providers.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            providers: List of provider names
            
        Returns:
            Dictionary mapping providers to availability check results
        """
        # Run availability checks concurrently
        tasks = [
            self.unified_manager.check_api_key_availability(bot_id, user_id, provider)
            for provider in providers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        availability_results = {}
        for provider, result in zip(providers, results):
            if isinstance(result, Exception):
                # Create error result
                availability_results[provider] = APIKeyAvailabilityCheck(
                    available=False,
                    sources_checked=[],
                    valid_sources=[],
                    provider=provider,
                    error=f"Validation failed: {str(result)}",
                    recommendations=[f"Check {provider} configuration and try again"]
                )
            else:
                availability_results[provider] = result
        
        return availability_results
    
    def get_provider_specific_error_messages(
        self,
        provider: str,
        error_type: APIKeyErrorType
    ) -> Dict[str, str]:
        """
        Get provider-specific error messages and guidance.
        
        Args:
            provider: Provider name
            error_type: Type of error
            
        Returns:
            Dictionary with error message and guidance
        """
        provider_info = {
            "openai": {
                "name": "OpenAI",
                "url": "https://platform.openai.com/api-keys",
                "docs": "https://platform.openai.com/docs/quickstart"
            },
            "anthropic": {
                "name": "Anthropic",
                "url": "https://console.anthropic.com/",
                "docs": "https://docs.anthropic.com/claude/docs"
            },
            "gemini": {
                "name": "Google Gemini",
                "url": "https://makersuite.google.com/app/apikey",
                "docs": "https://ai.google.dev/docs"
            },
            "openrouter": {
                "name": "OpenRouter",
                "url": "https://openrouter.ai/keys",
                "docs": "https://openrouter.ai/docs"
            }
        }
        
        info = provider_info.get(provider, {
            "name": provider.title(),
            "url": f"{provider} provider website",
            "docs": f"{provider} documentation"
        })
        
        error_messages = {
            APIKeyErrorType.NOT_FOUND: {
                "message": f"No {info['name']} API key found",
                "guidance": f"Get an API key from {info['url']} and add it to your profile settings"
            },
            APIKeyErrorType.INVALID: {
                "message": f"{info['name']} API key is invalid",
                "guidance": f"Verify your API key at {info['url']} and update it in your settings"
            },
            APIKeyErrorType.EXPIRED: {
                "message": f"{info['name']} API key has expired",
                "guidance": f"Generate a new API key at {info['url']} and update your settings"
            },
            APIKeyErrorType.RATE_LIMITED: {
                "message": f"{info['name']} rate limit exceeded",
                "guidance": f"Wait for rate limits to reset or upgrade your {info['name']} plan"
            },
            APIKeyErrorType.NETWORK_ERROR: {
                "message": f"Network error connecting to {info['name']}",
                "guidance": f"Check connectivity and {info['name']} service status"
            }
        }
        
        return error_messages.get(error_type, {
            "message": f"Unknown error with {info['name']} API key",
            "guidance": f"Check {info['docs']} for troubleshooting guidance"
        })
    
    async def test_api_key_configuration(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str
    ) -> Dict[str, Any]:
        """
        Test API key configuration and provide detailed diagnostics.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            provider: Provider name
            
        Returns:
            Dictionary with test results and diagnostics
        """
        test_results = {
            "provider": provider,
            "bot_id": str(bot_id),
            "user_id": str(user_id),
            "timestamp": asyncio.get_event_loop().time(),
            "tests": {}
        }
        
        try:
            # Test 1: API key availability
            availability_check = await self.unified_manager.check_api_key_availability(
                bot_id, user_id, provider
            )
            
            test_results["tests"]["availability"] = {
                "passed": availability_check.available,
                "sources_checked": [source.value for source in availability_check.sources_checked],
                "valid_sources": [source.value for source in availability_check.valid_sources],
                "recommendations": availability_check.recommendations
            }
            
            # Test 2: API key resolution
            resolution_result = await self.get_api_key_with_fallback(
                bot_id, user_id, provider, validate_key=True, enable_fallback=True
            )
            
            test_results["tests"]["resolution"] = {
                "passed": resolution_result.success,
                "source": resolution_result.source.value if resolution_result.source else None,
                "fallback_chain": [source.value for source in (resolution_result.fallback_chain or [])],
                "errors": [
                    {
                        "type": error.error_type.value,
                        "message": error.message,
                        "remediation_steps": error.remediation_steps
                    }
                    for error in (resolution_result.errors or [])
                ]
            }
            
            # Test 3: Actual API call (if resolution succeeded)
            if resolution_result.success and resolution_result.api_key:
                try:
                    # Test with a simple embedding generation
                    test_embedding = await self.embedding_service.generate_single_embedding(
                        provider=provider,
                        text="test",
                        model=self._get_default_model_for_provider(provider),
                        api_key=resolution_result.api_key
                    )
                    
                    test_results["tests"]["api_call"] = {
                        "passed": True,
                        "embedding_dimension": len(test_embedding),
                        "response_time": None  # Could be measured
                    }
                    
                except Exception as e:
                    test_results["tests"]["api_call"] = {
                        "passed": False,
                        "error": str(e)
                    }
            
            # Overall test result
            all_tests_passed = all(
                test.get("passed", False) 
                for test in test_results["tests"].values()
            )
            
            test_results["overall_result"] = {
                "passed": all_tests_passed,
                "summary": "All tests passed" if all_tests_passed else "Some tests failed"
            }
            
        except Exception as e:
            test_results["error"] = str(e)
            test_results["overall_result"] = {
                "passed": False,
                "summary": f"Test execution failed: {str(e)}"
            }
        
        return test_results
    
    def _get_default_model_for_provider(self, provider: str) -> str:
        """Get default model for testing purposes."""
        default_models = {
            "openai": "text-embedding-ada-002",
            "gemini": "embedding-001",
            "anthropic": "claude-3-haiku-20240307"  # Not for embeddings, but for testing
        }
        
        return default_models.get(provider, "default-model")