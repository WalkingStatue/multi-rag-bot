"""
RAG Error Recovery System - Comprehensive error handling and fallback strategies.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
import uuid

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of RAG errors."""
    EMBEDDING_GENERATION = "embedding_generation"
    VECTOR_SEARCH = "vector_search"
    COLLECTION_MANAGEMENT = "collection_management"
    API_KEY_VALIDATION = "api_key_validation"
    CONFIGURATION_VALIDATION = "configuration_validation"
    NETWORK_CONNECTIVITY = "network_connectivity"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_CORRUPTION = "data_corruption"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_PROVIDER = "fallback_provider"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CACHE_FALLBACK = "cache_fallback"
    ALTERNATIVE_ENDPOINT = "alternative_endpoint"
    SKIP_OPERATION = "skip_operation"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    bot_id: uuid.UUID
    user_id: uuid.UUID
    operation: str
    error_category: ErrorCategory
    error_message: str
    severity: ErrorSeverity
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RecoveryAction:
    """Action to take for error recovery."""
    strategy: RecoveryStrategy
    action_data: Optional[Dict[str, Any]] = None
    fallback_enabled: bool = True
    retry_delay: float = 1.0
    max_attempts: int = 3
    success_callback: Optional[Callable] = None
    failure_callback: Optional[Callable] = None


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
    success: bool
    strategy_used: RecoveryStrategy
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    recovery_time: Optional[float] = None
    fallback_used: bool = False


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0
    success_count: int = 0


class RAGErrorRecovery:
    """
    Comprehensive error recovery system with fallback strategies.
    
    This system provides:
    - Intelligent error categorization and severity assessment
    - Multiple recovery strategies with automatic selection
    - Circuit breaker pattern for preventing cascading failures
    - Performance monitoring and adaptive behavior
    - Graceful degradation for non-critical operations
    """
    
    def __init__(self):
        """Initialize RAG Error Recovery system."""
        # Configuration
        self.default_max_retries = 3
        self.default_retry_delay = 1.0
        self.circuit_breaker_enabled = True
        self.fallback_enabled = True
        
        # Circuit breakers for different services
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Error tracking and analytics
        self._error_history: List[ErrorContext] = []
        self._recovery_statistics: Dict[str, Dict[str, int]] = {}
        
        # Recovery strategy mappings
        self._strategy_mappings = self._initialize_strategy_mappings()
        
        # Performance metrics
        self._recovery_metrics: Dict[str, List[float]] = {}
    
    def _initialize_strategy_mappings(self) -> Dict[ErrorCategory, List[RecoveryStrategy]]:
        """Initialize error category to recovery strategy mappings."""
        return {
            ErrorCategory.EMBEDDING_GENERATION: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.FALLBACK_PROVIDER,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ],
            ErrorCategory.VECTOR_SEARCH: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.CACHE_FALLBACK,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ],
            ErrorCategory.COLLECTION_MANAGEMENT: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.ALTERNATIVE_ENDPOINT,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.API_KEY_VALIDATION: [
                RecoveryStrategy.FALLBACK_PROVIDER,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.CONFIGURATION_VALIDATION: [
                RecoveryStrategy.GRACEFUL_DEGRADATION,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.NETWORK_CONNECTIVITY: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.ALTERNATIVE_ENDPOINT,
                RecoveryStrategy.CACHE_FALLBACK
            ],
            ErrorCategory.RESOURCE_EXHAUSTION: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.GRACEFUL_DEGRADATION,
                RecoveryStrategy.SKIP_OPERATION
            ],
            ErrorCategory.DATA_CORRUPTION: [
                RecoveryStrategy.MANUAL_INTERVENTION,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ],
            ErrorCategory.UNKNOWN: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ]
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext
    ) -> RecoveryResult:
        """
        Handle error with appropriate recovery strategy.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            RecoveryResult with recovery outcome
        """
        start_time = time.time()
        
        try:
            logger.info(f"Handling error for bot {context.bot_id}: {context.error_category.value}")
            
            # Add to error history
            self._error_history.append(context)
            
            # Keep only last 1000 errors
            if len(self._error_history) > 1000:
                self._error_history = self._error_history[-1000:]
            
            # Check circuit breaker
            circuit_breaker_key = f"{context.bot_id}_{context.operation}"
            if self.circuit_breaker_enabled:
                circuit_breaker = self._get_or_create_circuit_breaker(circuit_breaker_key)
                
                if circuit_breaker.state == CircuitBreakerState.OPEN:
                    if time.time() - circuit_breaker.last_failure_time < circuit_breaker.recovery_timeout:
                        logger.warning(f"Circuit breaker open for {circuit_breaker_key}, skipping operation")
                        return RecoveryResult(
                            success=False,
                            strategy_used=RecoveryStrategy.SKIP_OPERATION,
                            error="Circuit breaker is open",
                            metadata={"circuit_breaker_state": "open"}
                        )
                    else:
                        # Try to transition to half-open
                        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
                        circuit_breaker.success_count = 0
            
            # Select recovery strategy
            recovery_action = self._select_recovery_strategy(error, context)
            
            # Execute recovery strategy
            recovery_result = await self._execute_recovery_strategy(
                error, context, recovery_action
            )
            
            # Update circuit breaker based on result
            if self.circuit_breaker_enabled:
                await self._update_circuit_breaker(circuit_breaker_key, recovery_result.success)
            
            # Track recovery metrics
            recovery_time = time.time() - start_time
            recovery_result.recovery_time = recovery_time
            
            await self._track_recovery_metrics(
                context.error_category, recovery_action.strategy, recovery_time, recovery_result.success
            )
            
            logger.info(f"Error recovery completed for bot {context.bot_id}: success={recovery_result.success}")
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"Error in error recovery system: {e}")
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
                error=f"Recovery system error: {str(e)}",
                recovery_time=time.time() - start_time
            )
    
    def _categorize_error(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """
        Categorize error based on exception type and context.
        
        Args:
            error: The exception
            context: Error context
            
        Returns:
            ErrorCategory for the error
        """
        error_message = str(error).lower()
        
        # API key related errors
        if any(keyword in error_message for keyword in ["api key", "authentication", "unauthorized", "invalid key"]):
            return ErrorCategory.API_KEY_VALIDATION
        
        # Network related errors
        if any(keyword in error_message for keyword in ["connection", "timeout", "network", "dns", "unreachable"]):
            return ErrorCategory.NETWORK_CONNECTIVITY
        
        # Embedding generation errors
        if any(keyword in error_message for keyword in ["embedding", "model not found", "provider", "dimension"]):
            return ErrorCategory.EMBEDDING_GENERATION
        
        # Vector search errors
        if any(keyword in error_message for keyword in ["vector", "search", "similarity", "collection not found"]):
            return ErrorCategory.VECTOR_SEARCH
        
        # Collection management errors
        if any(keyword in error_message for keyword in ["collection", "index", "qdrant", "vector store"]):
            return ErrorCategory.COLLECTION_MANAGEMENT
        
        # Resource exhaustion
        if any(keyword in error_message for keyword in ["memory", "quota", "rate limit", "resource", "capacity"]):
            return ErrorCategory.RESOURCE_EXHAUSTION
        
        # Configuration errors
        if any(keyword in error_message for keyword in ["configuration", "config", "invalid", "missing"]):
            return ErrorCategory.CONFIGURATION_VALIDATION
        
        # Data corruption
        if any(keyword in error_message for keyword in ["corrupt", "invalid data", "malformed", "parse error"]):
            return ErrorCategory.DATA_CORRUPTION
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """
        Assess error severity based on error type and context.
        
        Args:
            error: The exception
            context: Error context
            
        Returns:
            ErrorSeverity level
        """
        error_message = str(error).lower()
        
        # Critical errors that prevent core functionality
        if any(keyword in error_message for keyword in ["corrupt", "data loss", "security", "breach"]):
            return ErrorSeverity.CRITICAL
        
        # High severity errors that significantly impact functionality
        if any(keyword in error_message for keyword in ["authentication", "authorization", "collection not found"]):
            return ErrorSeverity.HIGH
        
        # Medium severity errors that impact some functionality
        if any(keyword in error_message for keyword in ["timeout", "rate limit", "quota", "network"]):
            return ErrorSeverity.MEDIUM
        
        # Low severity errors that have minimal impact
        return ErrorSeverity.LOW
    
    def _select_recovery_strategy(
        self,
        error: Exception,
        context: ErrorContext
    ) -> RecoveryAction:
        """
        Select appropriate recovery strategy based on error and context.
        
        Args:
            error: The exception
            context: Error context
            
        Returns:
            RecoveryAction to execute
        """
        # Get available strategies for this error category
        available_strategies = self._strategy_mappings.get(
            context.error_category, [RecoveryStrategy.GRACEFUL_DEGRADATION]
        )
        
        # Select strategy based on retry count and severity
        if context.retry_count == 0:
            # First attempt - try the primary strategy
            strategy = available_strategies[0]
        elif context.retry_count < len(available_strategies):
            # Use next available strategy
            strategy = available_strategies[context.retry_count]
        else:
            # Exhausted strategies - use graceful degradation
            strategy = RecoveryStrategy.GRACEFUL_DEGRADATION
        
        # Configure recovery action based on strategy
        action_data = {}
        retry_delay = self.default_retry_delay * (2 ** context.retry_count)  # Exponential backoff
        max_attempts = context.max_retries
        
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            action_data = {
                "delay": retry_delay,
                "max_attempts": max_attempts
            }
        elif strategy == RecoveryStrategy.FALLBACK_PROVIDER:
            action_data = {
                "fallback_enabled": self.fallback_enabled
            }
        elif strategy == RecoveryStrategy.CACHE_FALLBACK:
            action_data = {
                "cache_timeout": 300  # 5 minutes
            }
        elif strategy == RecoveryStrategy.ALTERNATIVE_ENDPOINT:
            action_data = {
                "endpoint_rotation": True
            }
        
        return RecoveryAction(
            strategy=strategy,
            action_data=action_data,
            fallback_enabled=self.fallback_enabled,
            retry_delay=retry_delay,
            max_attempts=max_attempts
        )
    
    async def _execute_recovery_strategy(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """
        Execute the selected recovery strategy.
        
        Args:
            error: The original exception
            context: Error context
            recovery_action: Recovery action to execute
            
        Returns:
            RecoveryResult with outcome
        """
        try:
            strategy = recovery_action.strategy
            
            if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                return await self._execute_retry_with_backoff(error, context, recovery_action)
            
            elif strategy == RecoveryStrategy.FALLBACK_PROVIDER:
                return await self._execute_fallback_provider(error, context, recovery_action)
            
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return await self._execute_graceful_degradation(error, context, recovery_action)
            
            elif strategy == RecoveryStrategy.CACHE_FALLBACK:
                return await self._execute_cache_fallback(error, context, recovery_action)
            
            elif strategy == RecoveryStrategy.ALTERNATIVE_ENDPOINT:
                return await self._execute_alternative_endpoint(error, context, recovery_action)
            
            elif strategy == RecoveryStrategy.SKIP_OPERATION:
                return await self._execute_skip_operation(error, context, recovery_action)
            
            elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                return await self._execute_manual_intervention(error, context, recovery_action)
            
            else:
                return RecoveryResult(
                    success=False,
                    strategy_used=strategy,
                    error=f"Unknown recovery strategy: {strategy}"
                )
                
        except Exception as e:
            logger.error(f"Error executing recovery strategy {recovery_action.strategy}: {e}")
            return RecoveryResult(
                success=False,
                strategy_used=recovery_action.strategy,
                error=f"Recovery execution error: {str(e)}"
            )
    
    async def _execute_retry_with_backoff(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute retry with exponential backoff strategy."""
        delay = recovery_action.action_data.get("delay", self.default_retry_delay)
        
        logger.info(f"Retrying operation after {delay}s delay (attempt {context.retry_count + 1})")
        
        await asyncio.sleep(delay)
        
        # The actual retry would be handled by the calling code
        # This method just provides the delay and signals that retry should be attempted
        return RecoveryResult(
            success=True,  # Success means the recovery strategy was executed, not that the operation succeeded
            strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF,
            data={"retry_delay": delay, "should_retry": True},
            metadata={"delay_applied": delay}
        )
    
    async def _execute_fallback_provider(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute fallback provider strategy."""
        if not recovery_action.fallback_enabled:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_PROVIDER,
                error="Fallback provider disabled"
            )
        
        logger.info(f"Attempting fallback provider for bot {context.bot_id}")
        
        # The actual fallback logic would be implemented by the calling service
        # This method signals that fallback should be attempted
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.FALLBACK_PROVIDER,
            data={"use_fallback": True},
            fallback_used=True,
            metadata={"fallback_enabled": True}
        )
    
    async def _execute_graceful_degradation(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute graceful degradation strategy."""
        logger.info(f"Applying graceful degradation for bot {context.bot_id}")
        
        # Determine what functionality to disable based on error category
        degradation_actions = []
        
        if context.error_category == ErrorCategory.EMBEDDING_GENERATION:
            degradation_actions.append("disable_rag")
        elif context.error_category == ErrorCategory.VECTOR_SEARCH:
            degradation_actions.append("disable_context_retrieval")
        elif context.error_category == ErrorCategory.COLLECTION_MANAGEMENT:
            degradation_actions.append("disable_document_processing")
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
            data={
                "degradation_actions": degradation_actions,
                "continue_without_feature": True
            },
            fallback_used=True,
            metadata={"degraded_features": degradation_actions}
        )
    
    async def _execute_cache_fallback(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute cache fallback strategy."""
        logger.info(f"Attempting cache fallback for bot {context.bot_id}")
        
        cache_timeout = recovery_action.action_data.get("cache_timeout", 300)
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.CACHE_FALLBACK,
            data={
                "use_cache": True,
                "cache_timeout": cache_timeout
            },
            fallback_used=True,
            metadata={"cache_fallback_enabled": True}
        )
    
    async def _execute_alternative_endpoint(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute alternative endpoint strategy."""
        logger.info(f"Attempting alternative endpoint for bot {context.bot_id}")
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.ALTERNATIVE_ENDPOINT,
            data={"use_alternative_endpoint": True},
            metadata={"endpoint_rotation": True}
        )
    
    async def _execute_skip_operation(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute skip operation strategy."""
        logger.info(f"Skipping operation for bot {context.bot_id} due to error")
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.SKIP_OPERATION,
            data={"operation_skipped": True},
            metadata={"skip_reason": str(error)}
        )
    
    async def _execute_manual_intervention(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_action: RecoveryAction
    ) -> RecoveryResult:
        """Execute manual intervention strategy."""
        logger.error(f"Manual intervention required for bot {context.bot_id}: {error}")
        
        # In a production system, this might trigger alerts or notifications
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            error="Manual intervention required",
            metadata={
                "requires_manual_intervention": True,
                "error_details": str(error),
                "context": {
                    "bot_id": str(context.bot_id),
                    "operation": context.operation,
                    "error_category": context.error_category.value
                }
            }
        )
    
    def _get_or_create_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create circuit breaker for a key."""
        if key not in self._circuit_breakers:
            self._circuit_breakers[key] = CircuitBreaker(name=key)
        return self._circuit_breakers[key]
    
    async def _update_circuit_breaker(self, key: str, success: bool):
        """Update circuit breaker state based on operation result."""
        circuit_breaker = self._get_or_create_circuit_breaker(key)
        
        if success:
            circuit_breaker.failure_count = 0
            if circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
                circuit_breaker.success_count += 1
                if circuit_breaker.success_count >= 3:  # Require 3 successes to close
                    circuit_breaker.state = CircuitBreakerState.CLOSED
        else:
            circuit_breaker.failure_count += 1
            circuit_breaker.last_failure_time = time.time()
            
            if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
                circuit_breaker.state = CircuitBreakerState.OPEN
    
    async def _track_recovery_metrics(
        self,
        error_category: ErrorCategory,
        strategy: RecoveryStrategy,
        recovery_time: float,
        success: bool
    ):
        """Track recovery metrics for analysis."""
        metric_key = f"{error_category.value}_{strategy.value}"
        
        if metric_key not in self._recovery_metrics:
            self._recovery_metrics[metric_key] = []
        
        self._recovery_metrics[metric_key].append(recovery_time)
        
        # Keep only last 100 measurements
        if len(self._recovery_metrics[metric_key]) > 100:
            self._recovery_metrics[metric_key] = self._recovery_metrics[metric_key][-100:]
        
        # Update recovery statistics
        if error_category.value not in self._recovery_statistics:
            self._recovery_statistics[error_category.value] = {}
        
        if strategy.value not in self._recovery_statistics[error_category.value]:
            self._recovery_statistics[error_category.value][strategy.value] = {"success": 0, "failure": 0}
        
        if success:
            self._recovery_statistics[error_category.value][strategy.value]["success"] += 1
        else:
            self._recovery_statistics[error_category.value][strategy.value]["failure"] += 1
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error and recovery statistics."""
        try:
            total_errors = len(self._error_history)
            
            if total_errors == 0:
                return {
                    "total_errors": 0,
                    "error_categories": {},
                    "recovery_statistics": {},
                    "circuit_breaker_status": {}
                }
            
            # Count errors by category
            category_counts = {}
            for error_context in self._error_history:
                category = error_context.error_category.value
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Circuit breaker status
            circuit_breaker_status = {}
            for key, cb in self._circuit_breakers.items():
                circuit_breaker_status[key] = {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time
                }
            
            return {
                "total_errors": total_errors,
                "error_categories": category_counts,
                "recovery_statistics": self._recovery_statistics,
                "circuit_breaker_status": circuit_breaker_status,
                "recovery_metrics": {
                    key: {
                        "avg_time": sum(times) / len(times),
                        "min_time": min(times),
                        "max_time": max(times),
                        "total_recoveries": len(times)
                    }
                    for key, times in self._recovery_metrics.items()
                    if times
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating error statistics: {e}")
            return {"error": str(e)}
    
    def reset_circuit_breaker(self, key: str) -> bool:
        """
        Reset a circuit breaker to closed state.
        
        Args:
            key: Circuit breaker key
            
        Returns:
            True if reset successfully
        """
        try:
            if key in self._circuit_breakers:
                self._circuit_breakers[key].state = CircuitBreakerState.CLOSED
                self._circuit_breakers[key].failure_count = 0
                self._circuit_breakers[key].success_count = 0
                logger.info(f"Reset circuit breaker: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resetting circuit breaker {key}: {e}")
            return False
    
    def clear_error_history(self):
        """Clear error history and reset statistics."""
        try:
            self._error_history.clear()
            self._recovery_statistics.clear()
            self._recovery_metrics.clear()
            logger.info("Cleared error history and statistics")
        except Exception as e:
            logger.error(f"Error clearing error history: {e}")