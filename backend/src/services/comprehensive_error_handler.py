"""
Comprehensive Error Handler - Centralized error handling and fallback system for RAG operations.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .rag_error_recovery import (
    RAGErrorRecovery, ErrorContext, ErrorCategory, ErrorSeverity, 
    RecoveryResult, RecoveryStrategy
)
from .user_notification_service import UserNotificationService, UserNotification
from .error_reporting_service import ErrorReportingService, ErrorReport
from .error_recovery_status_service import ErrorRecoveryStatusService, RecoveryStatus


logger = logging.getLogger(__name__)


@dataclass
class ErrorHandlingConfig:
    """Configuration for error handling behavior."""
    enable_graceful_degradation: bool = True
    enable_service_recovery_detection: bool = True
    enable_fallback_responses: bool = True
    max_retry_attempts: int = 3
    retry_delay_base: float = 1.0
    circuit_breaker_enabled: bool = True
    error_context_in_response: bool = True


@dataclass
class FallbackResponse:
    """Fallback response when RAG operations fail."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    fallback_used: bool = True


class ComprehensiveErrorHandler:
    """
    Centralized error handling system that provides:
    - Graceful degradation for RAG pipeline failures
    - Automatic service recovery detection and resumption
    - Comprehensive error context inclusion for debugging
    - Fallback response generation when operations fail
    """
    
    def __init__(self, db: Session, config: Optional[ErrorHandlingConfig] = None):
        """
        Initialize comprehensive error handler.
        
        Args:
            db: Database session
            config: Error handling configuration
        """
        self.db = db
        self.config = config or ErrorHandlingConfig()
        self.error_recovery = RAGErrorRecovery()
        
        # Initialize integrated services
        self.notification_service = UserNotificationService(db)
        self.error_reporting_service = ErrorReportingService(db)
        self.recovery_status_service = ErrorRecoveryStatusService(db)
        
        # Service health tracking
        self._service_health: Dict[str, Dict[str, Any]] = {}
        self._initialize_service_health_tracking()
        
        # Error statistics
        self._error_statistics: Dict[str, int] = {}
        self._recovery_statistics: Dict[str, int] = {}
    
    def _initialize_service_health_tracking(self):
        """Initialize service health tracking."""
        services = [
            "embedding_generation",
            "vector_search", 
            "collection_management",
            "api_key_validation",
            "llm_generation"
        ]
        
        for service in services:
            self._service_health[service] = {
                "status": "unknown",
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "recovery_detected": False,
                "total_operations": 0,
                "success_rate": 0.0
            }
    
    async def handle_rag_operation_error(
        self,
        operation_name: str,
        error: Exception,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        operation_context: Optional[Dict[str, Any]] = None,
        fallback_data: Optional[Any] = None
    ) -> Tuple[bool, Any, Dict[str, Any]]:
        """
        Handle RAG operation errors with comprehensive recovery.
        
        Args:
            operation_name: Name of the operation that failed
            error: The exception that occurred
            bot_id: Bot identifier
            user_id: User identifier
            operation_context: Additional context about the operation
            fallback_data: Data to return if graceful degradation is applied
            
        Returns:
            Tuple of (success, data, metadata)
        """
        start_time = time.time()
        
        try:
            # Create error context
            error_context = ErrorContext(
                bot_id=bot_id,
                user_id=user_id,
                operation=operation_name,
                error_category=self._categorize_operation_error(operation_name, error),
                error_message=str(error),
                severity=self._assess_operation_error_severity(operation_name, error),
                timestamp=start_time,
                metadata=operation_context or {}
            )
            
            # Update error statistics
            self._update_error_statistics(operation_name, error_context.error_category)
            
            # Update service health
            await self._update_service_health(operation_name, False, str(error))
            
            # Apply error recovery
            recovery_result = await self.error_recovery.handle_error(error, error_context)
            
            # Update recovery statistics
            self._update_recovery_statistics(recovery_result.strategy_used)
            
            # Record recovery attempt
            recovery_id = self.recovery_status_service.record_recovery_attempt(
                bot_id=bot_id,
                user_id=user_id,
                error_category=error_context.error_category,
                error_severity=error_context.severity,
                recovery_strategy=recovery_result.strategy_used,
                initial_status=RecoveryStatus.IN_PROGRESS,
                metadata={"operation": operation_name, "error_message": str(error)}
            )
            
            # Process recovery result
            success, data, metadata = await self._process_recovery_result(
                recovery_result, operation_name, fallback_data, error_context
            )
            
            # Update recovery status
            final_status = RecoveryStatus.SUCCESSFUL if success else RecoveryStatus.FAILED
            self.recovery_status_service.update_recovery_status(
                recovery_id=recovery_id,
                status=final_status,
                duration=time.time() - start_time,
                success_rate=1.0 if success else 0.0
            )
            
            # Create error report for administrators
            await self.error_reporting_service.create_error_report(
                error=error,
                operation=operation_name,
                bot_id=bot_id,
                user_id=user_id,
                error_category=error_context.error_category,
                error_severity=error_context.severity,
                context=operation_context,
                recovery_applied=True,
                recovery_strategy=recovery_result.strategy_used,
                recovery_success=success
            )
            
            # Create user notification if appropriate
            if self.config.enable_fallback_responses and not success:
                notification = self.notification_service.create_rag_failure_notification(
                    error_category=error_context.error_category,
                    error_message=str(error),
                    bot_id=bot_id,
                    user_id=user_id,
                    recovery_strategy=recovery_result.strategy_used,
                    additional_context=operation_context
                )
                
                if self.notification_service.should_send_notification(notification):
                    # In a real implementation, this would send the notification via WebSocket
                    metadata["user_notification"] = {
                        "id": notification.id,
                        "type": notification.type.value,
                        "title": notification.title,
                        "message": notification.message,
                        "suggested_actions": notification.suggested_actions
                    }
            
            # Include error context in metadata if enabled
            if self.config.error_context_in_response:
                metadata.update({
                    "error_context": {
                        "operation": operation_name,
                        "error_category": error_context.error_category.value,
                        "error_severity": error_context.severity.value,
                        "recovery_strategy": recovery_result.strategy_used.value,
                        "recovery_time": time.time() - start_time,
                        "service_health": self._get_service_health_summary(operation_name)
                    }
                })
            
            # Check for service recovery
            if success:
                await self._check_and_handle_service_recovery(operation_name, bot_id)
            
            logger.info(f"Error handling completed for {operation_name}: success={success}, strategy={recovery_result.strategy_used.value}")
            
            return success, data, metadata
            
        except Exception as handler_error:
            logger.error(f"Error in comprehensive error handler: {handler_error}")
            return False, None, {
                "error": "Error handler failure",
                "original_error": str(error),
                "handler_error": str(handler_error)
            }
    
    async def handle_embedding_failure(
        self,
        error: Exception,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        query: Optional[str] = None
    ) -> FallbackResponse:
        """Handle embedding generation failures with graceful degradation."""
        success, data, metadata = await self.handle_rag_operation_error(
            operation_name="embedding_generation",
            error=error,
            bot_id=bot_id,
            user_id=user_id,
            operation_context={"query": query[:100] if query else None},
            fallback_data=[]  # Empty chunks for graceful degradation
        )
        
        if success and self.config.enable_graceful_degradation:
            return FallbackResponse(
                success=True,
                data=data,
                message="Continuing conversation without document context due to embedding service issues",
                metadata=metadata,
                fallback_used=True
            )
        
        return FallbackResponse(
            success=False,
            message=f"Embedding generation failed: {str(error)}",
            metadata=metadata,
            fallback_used=False
        )
    
    async def handle_vector_search_failure(
        self,
        error: Exception,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        query_embedding: Optional[List[float]] = None
    ) -> FallbackResponse:
        """Handle vector search failures with fallback strategies."""
        success, data, metadata = await self.handle_rag_operation_error(
            operation_name="vector_search",
            error=error,
            bot_id=bot_id,
            user_id=user_id,
            operation_context={
                "embedding_dimension": len(query_embedding) if query_embedding else None
            },
            fallback_data=[]  # Empty search results
        )
        
        if success and self.config.enable_graceful_degradation:
            return FallbackResponse(
                success=True,
                data=data,
                message="Continuing conversation without retrieved context due to search service issues",
                metadata=metadata,
                fallback_used=True
            )
        
        return FallbackResponse(
            success=False,
            message=f"Vector search failed: {str(error)}",
            metadata=metadata,
            fallback_used=False
        )
    
    async def handle_collection_management_failure(
        self,
        error: Exception,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        operation_type: str = "collection_access"
    ) -> FallbackResponse:
        """Handle collection management failures."""
        success, data, metadata = await self.handle_rag_operation_error(
            operation_name="collection_management",
            error=error,
            bot_id=bot_id,
            user_id=user_id,
            operation_context={"operation_type": operation_type},
            fallback_data=None
        )
        
        return FallbackResponse(
            success=success,
            data=data,
            message=f"Collection management operation failed: {str(error)}" if not success else None,
            metadata=metadata,
            fallback_used=success and metadata.get("fallback_used", False)
        )
    
    def _categorize_operation_error(self, operation_name: str, error: Exception) -> ErrorCategory:
        """Categorize errors based on operation and error details."""
        error_message = str(error).lower()
        
        # Operation-specific categorization
        if operation_name == "embedding_generation":
            if any(keyword in error_message for keyword in ["api key", "authentication"]):
                return ErrorCategory.API_KEY_VALIDATION
            elif any(keyword in error_message for keyword in ["model", "provider"]):
                return ErrorCategory.EMBEDDING_GENERATION
            elif any(keyword in error_message for keyword in ["rate limit", "quota"]):
                return ErrorCategory.RESOURCE_EXHAUSTION
        
        elif operation_name == "vector_search":
            if any(keyword in error_message for keyword in ["collection", "index"]):
                return ErrorCategory.COLLECTION_MANAGEMENT
            elif any(keyword in error_message for keyword in ["dimension", "vector"]):
                return ErrorCategory.VECTOR_SEARCH
        
        elif operation_name == "collection_management":
            return ErrorCategory.COLLECTION_MANAGEMENT
        
        # General categorization
        if any(keyword in error_message for keyword in ["network", "timeout", "connection"]):
            return ErrorCategory.NETWORK_CONNECTIVITY
        elif any(keyword in error_message for keyword in ["config", "invalid"]):
            return ErrorCategory.CONFIGURATION_VALIDATION
        
        return ErrorCategory.UNKNOWN
    
    def _assess_operation_error_severity(self, operation_name: str, error: Exception) -> ErrorSeverity:
        """Assess error severity based on operation and error details."""
        error_message = str(error).lower()
        
        # Critical errors that prevent core functionality
        if any(keyword in error_message for keyword in ["corrupt", "data loss", "security"]):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if any(keyword in error_message for keyword in ["authentication", "collection not found"]):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if any(keyword in error_message for keyword in ["timeout", "rate limit", "network"]):
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    async def _process_recovery_result(
        self,
        recovery_result: RecoveryResult,
        operation_name: str,
        fallback_data: Optional[Any],
        error_context: ErrorContext
    ) -> Tuple[bool, Any, Dict[str, Any]]:
        """Process recovery result and determine response."""
        metadata = {
            "recovery_strategy": recovery_result.strategy_used.value,
            "recovery_success": recovery_result.success,
            "recovery_time": recovery_result.recovery_time,
            "fallback_used": recovery_result.fallback_used
        }
        
        if recovery_result.success:
            # Check recovery strategy
            if recovery_result.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION:
                if recovery_result.data and recovery_result.data.get("continue_without_feature"):
                    return True, fallback_data, {**metadata, "degradation_applied": True}
            
            elif recovery_result.strategy_used == RecoveryStrategy.CACHE_FALLBACK:
                if recovery_result.data and recovery_result.data.get("use_cache"):
                    # Implement cache fallback logic here
                    cached_data = await self._get_cached_data(operation_name, error_context.bot_id)
                    return True, cached_data or fallback_data, {**metadata, "cache_used": True}
            
            elif recovery_result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF:
                if recovery_result.data and recovery_result.data.get("should_retry"):
                    return False, None, {**metadata, "should_retry": True}
            
            # Default success case
            return True, recovery_result.data or fallback_data, metadata
        
        # Recovery failed
        return False, None, {**metadata, "recovery_failed": True}
    
    async def _get_cached_data(self, operation_name: str, bot_id: uuid.UUID) -> Optional[Any]:
        """Get cached data for fallback (placeholder implementation)."""
        # This would integrate with a caching system
        # For now, return None to indicate no cached data available
        return None
    
    async def _update_service_health(self, service_name: str, success: bool, error: Optional[str] = None):
        """Update service health tracking."""
        if service_name not in self._service_health:
            return
        
        current_time = time.time()
        health = self._service_health[service_name]
        
        health["total_operations"] += 1
        
        if success:
            # Check for recovery
            if health["consecutive_failures"] > 0:
                health["recovery_detected"] = True
                logger.info(f"Service recovery detected for {service_name}")
            
            health.update({
                "status": "healthy",
                "last_success": current_time,
                "consecutive_failures": 0
            })
        else:
            health.update({
                "status": "unhealthy",
                "last_failure": current_time,
                "consecutive_failures": health["consecutive_failures"] + 1,
                "recovery_detected": False
            })
        
        # Calculate success rate
        if health["total_operations"] > 0:
            success_count = health["total_operations"] - health["consecutive_failures"]
            health["success_rate"] = success_count / health["total_operations"]
    
    async def _check_and_handle_service_recovery(self, service_name: str, bot_id: uuid.UUID):
        """Check for service recovery and handle resumption."""
        if not self.config.enable_service_recovery_detection:
            return
        
        if service_name in self._service_health:
            health = self._service_health[service_name]
            
            if health["recovery_detected"]:
                logger.info(f"Handling service recovery for {service_name}, bot {bot_id}")
                
                # Reset recovery flag
                health["recovery_detected"] = False
                
                # Log recovery event
                await self._log_service_recovery(service_name, bot_id)
    
    async def _log_service_recovery(self, service_name: str, bot_id: uuid.UUID):
        """Log service recovery event."""
        try:
            recovery_event = {
                "service_name": service_name,
                "bot_id": str(bot_id),
                "timestamp": time.time(),
                "event_type": "service_recovery"
            }
            
            logger.info(f"Service recovery logged: {recovery_event}")
            # In production, this could trigger notifications or dashboard updates
            
        except Exception as e:
            logger.error(f"Failed to log service recovery: {e}")
    
    def _update_error_statistics(self, operation_name: str, error_category: ErrorCategory):
        """Update error statistics."""
        key = f"{operation_name}_{error_category.value}"
        self._error_statistics[key] = self._error_statistics.get(key, 0) + 1
    
    def _update_recovery_statistics(self, strategy: RecoveryStrategy):
        """Update recovery statistics."""
        key = strategy.value
        self._recovery_statistics[key] = self._recovery_statistics.get(key, 0) + 1
    
    def _get_service_health_summary(self, service_name: str) -> Dict[str, Any]:
        """Get service health summary."""
        if service_name not in self._service_health:
            return {"status": "unknown"}
        
        health = self._service_health[service_name]
        current_time = time.time()
        
        return {
            "status": health["status"],
            "consecutive_failures": health["consecutive_failures"],
            "success_rate": health["success_rate"],
            "last_success_ago": current_time - health["last_success"] if health["last_success"] else None,
            "total_operations": health["total_operations"]
        }
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error handling and recovery statistics."""
        try:
            current_time = time.time()
            
            # Service health summary
            service_health_summary = {}
            for service_name, health in self._service_health.items():
                service_health_summary[service_name] = self._get_service_health_summary(service_name)
            
            return {
                "service_health": service_health_summary,
                "error_statistics": self._error_statistics,
                "recovery_statistics": self._recovery_statistics,
                "error_recovery_stats": self.error_recovery.get_error_statistics(),
                "configuration": {
                    "graceful_degradation_enabled": self.config.enable_graceful_degradation,
                    "service_recovery_detection_enabled": self.config.enable_service_recovery_detection,
                    "fallback_responses_enabled": self.config.enable_fallback_responses,
                    "circuit_breaker_enabled": self.config.circuit_breaker_enabled
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive statistics: {e}")
            return {"error": str(e)}
    
    def reset_statistics(self):
        """Reset all statistics and health tracking."""
        try:
            self._error_statistics.clear()
            self._recovery_statistics.clear()
            self._initialize_service_health_tracking()
            self.error_recovery.clear_error_history()
            logger.info("Reset comprehensive error handler statistics")
        except Exception as e:
            logger.error(f"Error resetting statistics: {e}")