"""
API Key Error Handler for RAG Pipeline.

This module provides comprehensive error handling and recovery strategies
for API key related issues across the RAG pipeline.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .enhanced_api_key_service import (
    EnhancedAPIKeyService, 
    APIKeyErrorType, 
    APIKeyError,
    FallbackResult
)


logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for API key failures."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    USE_FALLBACK_PROVIDER = "use_fallback_provider"
    SKIP_VALIDATION = "skip_validation"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"


@dataclass
class RecoveryAction:
    """Action to take for API key error recovery."""
    strategy: RecoveryStrategy
    delay_seconds: Optional[float] = None
    alternative_provider: Optional[str] = None
    skip_operation: bool = False
    user_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ErrorContext:
    """Context information for error handling."""
    bot_id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    operation: str
    attempt_count: int = 1
    max_attempts: int = 3
    metadata: Optional[Dict[str, Any]] = None


class APIKeyErrorHandler:
    """
    Comprehensive API key error handler with recovery strategies.
    
    This handler provides intelligent error recovery, user-friendly error messages,
    and specific remediation guidance for API key related issues.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the API key error handler.
        
        Args:
            db: Database session
        """
        self.db = db
        self.api_key_service = EnhancedAPIKeyService(db)
        
        # Recovery configuration
        self.max_retry_attempts = 3
        self.base_retry_delay = 1.0
        self.max_retry_delay = 8.0
        
        # Provider fallback mappings
        self.provider_fallbacks = {
            "openai": ["gemini"],
            "gemini": ["openai"],
            "anthropic": ["openai", "gemini"]
        }
    
    async def handle_api_key_error(
        self,
        error: Exception,
        context: ErrorContext,
        operation_func: Optional[Callable[..., Awaitable[Any]]] = None,
        **operation_kwargs
    ) -> Any:
        """
        Handle API key error with appropriate recovery strategy.
        
        Args:
            error: The original error that occurred
            context: Context information about the error
            operation_func: Optional function to retry with recovered API key
            **operation_kwargs: Arguments for the operation function
            
        Returns:
            Result of recovery operation or raises appropriate exception
        """
        logger.warning(f"Handling API key error for {context.provider}: {str(error)}")
        
        # Categorize the error
        api_key_error = self._categorize_error(error, context)
        
        # Determine recovery strategy
        recovery_action = self._determine_recovery_strategy(api_key_error, context)
        
        # Execute recovery strategy
        return await self._execute_recovery_strategy(
            recovery_action, context, operation_func, **operation_kwargs
        )
    
    def _categorize_error(self, error: Exception, context: ErrorContext) -> APIKeyError:
        """
        Categorize the error and determine its type.
        
        Args:
            error: The original error
            context: Error context
            
        Returns:
            Categorized APIKeyError
        """
        error_message = str(error).lower()
        
        # Determine error type based on error message
        if "api key" in error_message and ("not found" in error_message or "missing" in error_message):
            error_type = APIKeyErrorType.NOT_FOUND
        elif "invalid" in error_message or "unauthorized" in error_message or "401" in error_message:
            error_type = APIKeyErrorType.INVALID
        elif "expired" in error_message or "403" in error_message:
            error_type = APIKeyErrorType.EXPIRED
        elif "rate limit" in error_message or "quota" in error_message or "429" in error_message:
            error_type = APIKeyErrorType.RATE_LIMITED
        elif "timeout" in error_message or "timed out" in error_message:
            error_type = APIKeyErrorType.VALIDATION_TIMEOUT
        else:
            error_type = APIKeyErrorType.NETWORK_ERROR
        
        # Generate remediation steps
        remediation_steps = self._generate_remediation_steps(error_type, context.provider)
        
        return APIKeyError(
            error_type=error_type,
            provider=context.provider,
            message=str(error),
            remediation_steps=remediation_steps
        )
    
    def _generate_remediation_steps(self, error_type: APIKeyErrorType, provider: str) -> List[str]:
        """Generate specific remediation steps for the error type."""
        provider_urls = {
            "openai": "https://platform.openai.com/api-keys",
            "anthropic": "https://console.anthropic.com/",
            "gemini": "https://makersuite.google.com/app/apikey",
            "openrouter": "https://openrouter.ai/keys"
        }
        
        provider_name = provider.title()
        setup_url = provider_urls.get(provider, f"{provider} provider website")
        
        base_steps = {
            APIKeyErrorType.NOT_FOUND: [
                f"Configure {provider_name} API key in your profile settings",
                f"Get an API key from: {setup_url}",
                "Ensure the API key is properly saved"
            ],
            APIKeyErrorType.INVALID: [
                f"Verify your {provider_name} API key is correct",
                f"Check API key permissions at: {setup_url}",
                "Generate a new API key if needed"
            ],
            APIKeyErrorType.EXPIRED: [
                f"Generate a new {provider_name} API key",
                f"Update your profile with the new key",
                "Set up API key rotation to prevent future expiration"
            ],
            APIKeyErrorType.RATE_LIMITED: [
                f"Wait for {provider_name} rate limits to reset",
                f"Consider upgrading your {provider_name} plan",
                "Implement request throttling"
            ],
            APIKeyErrorType.VALIDATION_TIMEOUT: [
                f"Check network connectivity to {provider_name}",
                "Retry the operation after a brief delay",
                f"Contact {provider_name} support if timeouts persist"
            ],
            APIKeyErrorType.NETWORK_ERROR: [
                "Check network connectivity",
                f"Verify {provider_name} service status",
                "Retry the operation"
            ]
        }
        
        return base_steps.get(error_type, ["Contact support for assistance"])
    
    def _determine_recovery_strategy(
        self, 
        api_key_error: APIKeyError, 
        context: ErrorContext
    ) -> RecoveryAction:
        """
        Determine the appropriate recovery strategy based on error type and context.
        
        Args:
            api_key_error: Categorized API key error
            context: Error context
            
        Returns:
            Recovery action to take
        """
        # Check if we've exceeded retry attempts
        if context.attempt_count >= context.max_attempts:
            return RecoveryAction(
                strategy=RecoveryStrategy.FAIL_FAST,
                user_message=self._generate_final_error_message(api_key_error, context)
            )
        
        # Strategy based on error type
        if api_key_error.error_type == APIKeyErrorType.RATE_LIMITED:
            # For rate limiting, wait and retry
            delay = min(
                self.base_retry_delay * (2 ** (context.attempt_count - 1)),
                self.max_retry_delay
            )
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                delay_seconds=delay,
                user_message=f"Rate limit exceeded for {context.provider}. Retrying in {delay:.1f} seconds..."
            )
        
        elif api_key_error.error_type == APIKeyErrorType.VALIDATION_TIMEOUT:
            # For timeouts, retry with backoff
            delay = self.base_retry_delay * context.attempt_count
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                delay_seconds=delay,
                user_message=f"Validation timeout for {context.provider}. Retrying..."
            )
        
        elif api_key_error.error_type in [APIKeyErrorType.NOT_FOUND, APIKeyErrorType.INVALID]:
            # For missing/invalid keys, try fallback provider
            fallback_providers = self.provider_fallbacks.get(context.provider, [])
            if fallback_providers and context.attempt_count == 1:
                return RecoveryAction(
                    strategy=RecoveryStrategy.USE_FALLBACK_PROVIDER,
                    alternative_provider=fallback_providers[0],
                    user_message=f"Trying alternative provider due to {context.provider} API key issue..."
                )
            else:
                # No fallback available, try without validation
                return RecoveryAction(
                    strategy=RecoveryStrategy.SKIP_VALIDATION,
                    user_message=f"Attempting to use {context.provider} API key without validation..."
                )
        
        elif api_key_error.error_type == APIKeyErrorType.EXPIRED:
            # For expired keys, fail fast with clear message
            return RecoveryAction(
                strategy=RecoveryStrategy.FAIL_FAST,
                user_message=f"{context.provider} API key has expired. Please update your API key."
            )
        
        else:
            # For network errors, retry with backoff
            delay = self.base_retry_delay * context.attempt_count
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                delay_seconds=delay,
                user_message=f"Network error with {context.provider}. Retrying..."
            )
    
    async def _execute_recovery_strategy(
        self,
        recovery_action: RecoveryAction,
        context: ErrorContext,
        operation_func: Optional[Callable[..., Awaitable[Any]]] = None,
        **operation_kwargs
    ) -> Any:
        """
        Execute the determined recovery strategy.
        
        Args:
            recovery_action: Recovery action to execute
            context: Error context
            operation_func: Function to retry
            **operation_kwargs: Arguments for operation function
            
        Returns:
            Result of recovery operation
        """
        logger.info(f"Executing recovery strategy: {recovery_action.strategy.value}")
        
        if recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            if recovery_action.delay_seconds:
                logger.info(f"Waiting {recovery_action.delay_seconds}s before retry...")
                await asyncio.sleep(recovery_action.delay_seconds)
            
            # Increment attempt count and retry
            context.attempt_count += 1
            
            if operation_func:
                try:
                    return await operation_func(**operation_kwargs)
                except Exception as retry_error:
                    # Recursive call to handle the retry error
                    return await self.handle_api_key_error(
                        retry_error, context, operation_func, **operation_kwargs
                    )
            else:
                # Just return success if no operation to retry
                return {"success": True, "message": "Retry completed"}
        
        elif recovery_action.strategy == RecoveryStrategy.USE_FALLBACK_PROVIDER:
            # Try with alternative provider
            if recovery_action.alternative_provider and operation_func:
                logger.info(f"Trying fallback provider: {recovery_action.alternative_provider}")
                
                # Update context for fallback provider
                fallback_context = ErrorContext(
                    bot_id=context.bot_id,
                    user_id=context.user_id,
                    provider=recovery_action.alternative_provider,
                    operation=context.operation,
                    attempt_count=1,
                    max_attempts=context.max_attempts
                )
                
                # Update operation kwargs to use fallback provider
                operation_kwargs["provider"] = recovery_action.alternative_provider
                
                try:
                    return await operation_func(**operation_kwargs)
                except Exception as fallback_error:
                    # If fallback also fails, handle that error
                    return await self.handle_api_key_error(
                        fallback_error, fallback_context, operation_func, **operation_kwargs
                    )
        
        elif recovery_action.strategy == RecoveryStrategy.SKIP_VALIDATION:
            # Try operation without API key validation
            if operation_func:
                logger.info("Attempting operation without API key validation")
                
                # Add flag to skip validation
                operation_kwargs["validate_key"] = False
                
                try:
                    return await operation_func(**operation_kwargs)
                except Exception as no_validation_error:
                    # If this also fails, fail fast
                    context.attempt_count = context.max_attempts  # Force fail fast
                    return await self.handle_api_key_error(
                        no_validation_error, context, operation_func, **operation_kwargs
                    )
        
        elif recovery_action.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            # Return a degraded response
            logger.info("Using graceful degradation for API key error")
            return {
                "success": False,
                "degraded": True,
                "message": recovery_action.user_message or "Service temporarily unavailable",
                "error_type": "api_key_unavailable"
            }
        
        else:  # FAIL_FAST
            # Generate comprehensive error message
            error_message = recovery_action.user_message or self._generate_final_error_message(
                None, context
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
    
    def _generate_final_error_message(
        self, 
        api_key_error: Optional[APIKeyError], 
        context: ErrorContext
    ) -> str:
        """
        Generate comprehensive final error message with remediation steps.
        
        Args:
            api_key_error: The API key error (if available)
            context: Error context
            
        Returns:
            Comprehensive error message
        """
        provider_name = context.provider.title()
        
        base_message = f"Unable to resolve API key for {provider_name} after {context.attempt_count} attempts."
        
        if api_key_error and api_key_error.remediation_steps:
            remediation_text = "\n".join(f"• {step}" for step in api_key_error.remediation_steps[:3])
            base_message += f"\n\nRecommended actions:\n{remediation_text}"
        
        # Add configuration suggestions
        suggestions = self.api_key_service.unified_manager.get_api_key_configuration_suggestions(
            context.bot_id, context.user_id, context.provider
        )
        
        if suggestions:
            suggestion_text = "\n".join(f"• {suggestion}" for suggestion in suggestions[:2])
            base_message += f"\n\nConfiguration suggestions:\n{suggestion_text}"
        
        return base_message
    
    async def test_api_key_recovery(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str
    ) -> Dict[str, Any]:
        """
        Test API key error recovery mechanisms.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            provider: Provider name
            
        Returns:
            Test results with recovery scenarios
        """
        test_results = {
            "provider": provider,
            "bot_id": str(bot_id),
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_tests": {}
        }
        
        # Test 1: Normal API key resolution
        try:
            fallback_result = await self.api_key_service.get_api_key_with_fallback(
                bot_id, user_id, provider, validate_key=True, enable_fallback=True
            )
            
            test_results["recovery_tests"]["normal_resolution"] = {
                "success": fallback_result.success,
                "source": fallback_result.source.value if fallback_result.source else None,
                "fallback_chain": [s.value for s in (fallback_result.fallback_chain or [])],
                "errors": len(fallback_result.errors or [])
            }
            
        except Exception as e:
            test_results["recovery_tests"]["normal_resolution"] = {
                "success": False,
                "error": str(e)
            }
        
        # Test 2: Recovery with simulated errors
        error_scenarios = [
            ("rate_limit", "Rate limit exceeded"),
            ("invalid_key", "Invalid API key"),
            ("timeout", "Request timed out"),
            ("not_found", "API key not found")
        ]
        
        for scenario_name, error_message in error_scenarios:
            try:
                # Create mock error context
                context = ErrorContext(
                    bot_id=bot_id,
                    user_id=user_id,
                    provider=provider,
                    operation="test_recovery",
                    attempt_count=1,
                    max_attempts=2
                )
                
                # Simulate error
                mock_error = Exception(error_message)
                api_key_error = self._categorize_error(mock_error, context)
                recovery_action = self._determine_recovery_strategy(api_key_error, context)
                
                test_results["recovery_tests"][scenario_name] = {
                    "error_type": api_key_error.error_type.value,
                    "recovery_strategy": recovery_action.strategy.value,
                    "delay_seconds": recovery_action.delay_seconds,
                    "alternative_provider": recovery_action.alternative_provider,
                    "user_message": recovery_action.user_message
                }
                
            except Exception as e:
                test_results["recovery_tests"][scenario_name] = {
                    "error": str(e)
                }
        
        return test_results
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about API key errors and recovery attempts.
        
        Returns:
            Dictionary with error statistics
        """
        # This would typically be implemented with persistent storage
        # For now, return basic information
        return {
            "supported_providers": list(self.provider_fallbacks.keys()),
            "recovery_strategies": [strategy.value for strategy in RecoveryStrategy],
            "max_retry_attempts": self.max_retry_attempts,
            "base_retry_delay": self.base_retry_delay,
            "max_retry_delay": self.max_retry_delay,
            "provider_fallbacks": self.provider_fallbacks
        }