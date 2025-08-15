"""
User Notification Service - Provides user-friendly notifications for RAG pipeline issues.
"""
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.orm import Session

from .rag_error_recovery import ErrorCategory, ErrorSeverity, RecoveryStrategy


logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of user notifications."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class UserNotification:
    """User-friendly notification message."""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    details: Optional[str] = None
    action_required: bool = False
    suggested_actions: Optional[List[str]] = None
    timestamp: float = None
    bot_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.id is None:
            self.id = f"notif_{int(self.timestamp)}_{hash(self.message) % 10000}"


class UserNotificationService:
    """
    Service for generating user-friendly notifications about RAG pipeline issues.
    
    This service provides:
    - User-friendly error messages with clear explanations
    - Specific troubleshooting guidance and suggested actions
    - Contextual notifications based on error category and severity
    - Integration with WebSocket service for real-time notifications
    """
    
    def __init__(self, db: Session):
        """
        Initialize user notification service.
        
        Args:
            db: Database session
        """
        self.db = db
        
        # Notification templates
        self._notification_templates = self._initialize_notification_templates()
        
        # Troubleshooting guides
        self._troubleshooting_guides = self._initialize_troubleshooting_guides()
        
        # Recent notifications cache (to avoid spam)
        self._recent_notifications: Dict[str, float] = {}
        self._notification_cooldown = 300  # 5 minutes
    
    def _initialize_notification_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize notification templates for different error scenarios."""
        return {
            # Embedding generation errors
            "embedding_api_key_missing": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.HIGH,
                "title": "API Key Required",
                "message": "Document context is unavailable because no API key is configured for the embedding provider.",
                "action_required": True,
                "suggested_actions": [
                    "Configure your API key in user settings",
                    "Contact the bot owner to configure their API key",
                    "Switch to a different embedding provider"
                ]
            },
            "embedding_api_key_invalid": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.HIGH,
                "title": "Invalid API Key",
                "message": "Document context is unavailable due to an invalid or expired API key.",
                "action_required": True,
                "suggested_actions": [
                    "Check and update your API key in user settings",
                    "Verify the API key has the correct permissions",
                    "Contact support if the issue persists"
                ]
            },
            "embedding_rate_limit": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Rate Limit Reached",
                "message": "Document context is temporarily unavailable due to API rate limits.",
                "action_required": False,
                "suggested_actions": [
                    "Wait a few minutes before trying again",
                    "Consider upgrading your API plan for higher limits",
                    "The conversation will continue without document context"
                ]
            },
            "embedding_model_unavailable": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Embedding Model Unavailable",
                "message": "Document context is unavailable because the configured embedding model is not accessible.",
                "action_required": True,
                "suggested_actions": [
                    "Contact the bot owner to update the embedding model",
                    "Check if the model name is correct",
                    "Try again later if this is a temporary service issue"
                ]
            },
            
            # Vector search errors
            "vector_collection_not_found": {
                "type": NotificationType.INFO,
                "priority": NotificationPriority.LOW,
                "title": "No Documents Available",
                "message": "This bot doesn't have any documents uploaded yet, so document context is not available.",
                "action_required": False,
                "suggested_actions": [
                    "Upload documents to enable document-based responses",
                    "The bot can still respond using its base knowledge"
                ]
            },
            "vector_search_failed": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Document Search Unavailable",
                "message": "Document context is temporarily unavailable due to a search service issue.",
                "action_required": False,
                "suggested_actions": [
                    "The conversation will continue without document context",
                    "Try again in a few minutes",
                    "Contact support if the issue persists"
                ]
            },
            "vector_dimension_mismatch": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.HIGH,
                "title": "Configuration Issue",
                "message": "Document context is unavailable due to a configuration mismatch. Documents need to be reprocessed.",
                "action_required": True,
                "suggested_actions": [
                    "Contact the bot owner to reprocess documents",
                    "The embedding model may have been changed recently",
                    "This requires administrator action to resolve"
                ]
            },
            
            # Collection management errors
            "collection_creation_failed": {
                "type": NotificationType.ERROR,
                "priority": NotificationPriority.HIGH,
                "title": "Setup Issue",
                "message": "Document context is unavailable due to a setup issue with the bot's knowledge base.",
                "action_required": True,
                "suggested_actions": [
                    "Contact the bot owner to resolve the setup issue",
                    "This may require re-uploading documents",
                    "Contact support if the issue persists"
                ]
            },
            
            # Network and connectivity errors
            "network_timeout": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Connection Issue",
                "message": "Document context is temporarily unavailable due to a connection timeout.",
                "action_required": False,
                "suggested_actions": [
                    "This is usually temporary - try again in a moment",
                    "The conversation will continue without document context",
                    "Check your internet connection if the issue persists"
                ]
            },
            
            # Generic fallback
            "generic_rag_failure": {
                "type": NotificationType.WARNING,
                "priority": NotificationPriority.MEDIUM,
                "title": "Document Context Unavailable",
                "message": "Document context is temporarily unavailable, but the conversation can continue.",
                "action_required": False,
                "suggested_actions": [
                    "The bot will respond using its base knowledge",
                    "Try again later for document-based responses",
                    "Contact support if this happens frequently"
                ]
            },
            
            # Recovery notifications
            "service_recovered": {
                "type": NotificationType.SUCCESS,
                "priority": NotificationPriority.LOW,
                "title": "Service Restored",
                "message": "Document context is now available again. The service has recovered from previous issues.",
                "action_required": False,
                "suggested_actions": [
                    "You can now ask questions about uploaded documents",
                    "Previous conversations will also have document context available"
                ]
            }
        }
    
    def _initialize_troubleshooting_guides(self) -> Dict[ErrorCategory, Dict[str, Any]]:
        """Initialize detailed troubleshooting guides for administrators."""
        return {
            ErrorCategory.API_KEY_VALIDATION: {
                "title": "API Key Issues",
                "description": "Problems with API key configuration or validation",
                "common_causes": [
                    "Missing API key for the embedding or LLM provider",
                    "Invalid or expired API key",
                    "API key lacks required permissions",
                    "Incorrect provider configuration"
                ],
                "diagnostic_steps": [
                    "Check if API key is configured in user settings",
                    "Verify API key format and validity",
                    "Test API key with provider's API directly",
                    "Check API key permissions and quotas"
                ],
                "resolution_steps": [
                    "Configure valid API key in user settings",
                    "Update expired or invalid API keys",
                    "Ensure API key has required permissions",
                    "Contact provider support for API key issues"
                ]
            },
            
            ErrorCategory.EMBEDDING_GENERATION: {
                "title": "Embedding Generation Issues",
                "description": "Problems with generating embeddings for text",
                "common_causes": [
                    "Embedding model not available or deprecated",
                    "Text too long for embedding model",
                    "Provider service outage",
                    "Rate limiting or quota exceeded"
                ],
                "diagnostic_steps": [
                    "Check if embedding model is still supported",
                    "Verify text length is within model limits",
                    "Test embedding generation with simple text",
                    "Check provider status page for outages"
                ],
                "resolution_steps": [
                    "Update to a supported embedding model",
                    "Implement text chunking for long content",
                    "Wait for provider service recovery",
                    "Upgrade API plan or wait for quota reset"
                ]
            },
            
            ErrorCategory.VECTOR_SEARCH: {
                "title": "Vector Search Problems",
                "description": "Issues with searching the vector database",
                "common_causes": [
                    "Vector collection doesn't exist",
                    "Dimension mismatch between query and stored vectors",
                    "Vector database connection issues",
                    "Corrupted vector index"
                ],
                "diagnostic_steps": [
                    "Check if vector collection exists for the bot",
                    "Verify embedding dimensions match stored vectors",
                    "Test vector database connectivity",
                    "Check vector database logs for errors"
                ],
                "resolution_steps": [
                    "Create vector collection if missing",
                    "Reprocess documents with correct embedding model",
                    "Restart vector database service",
                    "Rebuild vector index if corrupted"
                ]
            },
            
            ErrorCategory.COLLECTION_MANAGEMENT: {
                "title": "Collection Management Issues",
                "description": "Problems with vector collection lifecycle",
                "common_causes": [
                    "Failed collection creation",
                    "Collection configuration mismatch",
                    "Insufficient permissions",
                    "Storage space issues"
                ],
                "diagnostic_steps": [
                    "Check collection creation logs",
                    "Verify collection configuration parameters",
                    "Check database permissions",
                    "Monitor storage space usage"
                ],
                "resolution_steps": [
                    "Retry collection creation with correct parameters",
                    "Update collection configuration",
                    "Grant necessary database permissions",
                    "Free up storage space or increase limits"
                ]
            },
            
            ErrorCategory.NETWORK_CONNECTIVITY: {
                "title": "Network and Connectivity Issues",
                "description": "Problems with network connections to external services",
                "common_causes": [
                    "Internet connectivity issues",
                    "Provider API endpoint unavailable",
                    "Firewall or proxy blocking requests",
                    "DNS resolution problems"
                ],
                "diagnostic_steps": [
                    "Test internet connectivity",
                    "Check provider API status",
                    "Verify firewall and proxy settings",
                    "Test DNS resolution for provider domains"
                ],
                "resolution_steps": [
                    "Fix internet connectivity issues",
                    "Wait for provider service recovery",
                    "Update firewall/proxy configuration",
                    "Use alternative DNS servers"
                ]
            }
        }
    
    def create_rag_failure_notification(
        self,
        error_category: ErrorCategory,
        error_message: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        recovery_strategy: Optional[RecoveryStrategy] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> UserNotification:
        """
        Create a user-friendly notification for RAG failures.
        
        Args:
            error_category: Category of the error
            error_message: Original error message
            bot_id: Bot identifier
            user_id: User identifier
            recovery_strategy: Recovery strategy applied
            additional_context: Additional context information
            
        Returns:
            UserNotification with user-friendly message
        """
        # Determine notification template based on error details
        template_key = self._select_notification_template(error_category, error_message)
        template = self._notification_templates.get(template_key, self._notification_templates["generic_rag_failure"])
        
        # Create notification
        notification = UserNotification(
            id=None,  # Will be auto-generated
            type=template["type"],
            priority=template["priority"],
            title=template["title"],
            message=template["message"],
            details=self._generate_detailed_explanation(error_category, error_message, recovery_strategy),
            action_required=template["action_required"],
            suggested_actions=template["suggested_actions"].copy(),
            bot_id=bot_id,
            user_id=user_id,
            metadata={
                "error_category": error_category.value,
                "recovery_strategy": recovery_strategy.value if recovery_strategy else None,
                "original_error": error_message[:200],  # Truncate for metadata
                **(additional_context or {})
            }
        )
        
        # Add context-specific suggestions
        if additional_context:
            notification.suggested_actions.extend(
                self._generate_contextual_suggestions(error_category, additional_context)
            )
        
        return notification
    
    def create_service_recovery_notification(
        self,
        service_name: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        recovery_details: Optional[Dict[str, Any]] = None
    ) -> UserNotification:
        """Create notification for service recovery."""
        template = self._notification_templates["service_recovered"]
        
        return UserNotification(
            id=None,
            type=template["type"],
            priority=template["priority"],
            title=template["title"],
            message=f"The {service_name} has recovered and document context is now available again.",
            details=f"Service recovery detected at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            action_required=template["action_required"],
            suggested_actions=template["suggested_actions"].copy(),
            bot_id=bot_id,
            user_id=user_id,
            metadata={
                "service_name": service_name,
                "recovery_time": time.time(),
                **(recovery_details or {})
            }
        )
    
    def should_send_notification(self, notification: UserNotification) -> bool:
        """
        Check if notification should be sent (avoid spam).
        
        Args:
            notification: Notification to check
            
        Returns:
            True if notification should be sent
        """
        # Create a key for deduplication
        dedup_key = f"{notification.bot_id}_{notification.user_id}_{notification.type.value}_{hash(notification.message) % 1000}"
        
        current_time = time.time()
        last_sent = self._recent_notifications.get(dedup_key)
        
        if last_sent and (current_time - last_sent) < self._notification_cooldown:
            # Skip notification if sent recently
            return False
        
        # Update last sent time
        self._recent_notifications[dedup_key] = current_time
        
        # Clean up old entries
        self._cleanup_recent_notifications(current_time)
        
        return True
    
    def _select_notification_template(self, error_category: ErrorCategory, error_message: str) -> str:
        """Select appropriate notification template based on error details."""
        error_lower = error_message.lower()
        
        # API key related errors
        if error_category == ErrorCategory.API_KEY_VALIDATION:
            if "missing" in error_lower or "not found" in error_lower:
                return "embedding_api_key_missing"
            elif "invalid" in error_lower or "expired" in error_lower or "unauthorized" in error_lower:
                return "embedding_api_key_invalid"
        
        # Embedding generation errors
        elif error_category == ErrorCategory.EMBEDDING_GENERATION:
            if "rate limit" in error_lower or "quota" in error_lower:
                return "embedding_rate_limit"
            elif "model" in error_lower and ("not found" in error_lower or "unavailable" in error_lower):
                return "embedding_model_unavailable"
        
        # Vector search errors
        elif error_category == ErrorCategory.VECTOR_SEARCH:
            if "collection not found" in error_lower or "no documents" in error_lower:
                return "vector_collection_not_found"
            elif "dimension" in error_lower and "mismatch" in error_lower:
                return "vector_dimension_mismatch"
            else:
                return "vector_search_failed"
        
        # Collection management errors
        elif error_category == ErrorCategory.COLLECTION_MANAGEMENT:
            return "collection_creation_failed"
        
        # Network errors
        elif error_category == ErrorCategory.NETWORK_CONNECTIVITY:
            if "timeout" in error_lower:
                return "network_timeout"
        
        # Default fallback
        return "generic_rag_failure"
    
    def _generate_detailed_explanation(
        self,
        error_category: ErrorCategory,
        error_message: str,
        recovery_strategy: Optional[RecoveryStrategy]
    ) -> str:
        """Generate detailed explanation for the error."""
        explanations = []
        
        # Add category-specific explanation
        if error_category == ErrorCategory.API_KEY_VALIDATION:
            explanations.append("This happens when the API key for the embedding provider is missing, invalid, or expired.")
        elif error_category == ErrorCategory.EMBEDDING_GENERATION:
            explanations.append("This occurs when the system cannot generate embeddings for your text, usually due to provider issues.")
        elif error_category == ErrorCategory.VECTOR_SEARCH:
            explanations.append("This happens when the system cannot search through the bot's document knowledge base.")
        elif error_category == ErrorCategory.COLLECTION_MANAGEMENT:
            explanations.append("This occurs when there's an issue with the bot's document storage configuration.")
        elif error_category == ErrorCategory.NETWORK_CONNECTIVITY:
            explanations.append("This is usually a temporary connectivity issue with external services.")
        
        # Add recovery strategy explanation
        if recovery_strategy:
            if recovery_strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                explanations.append("The system has automatically switched to continue the conversation without document context.")
            elif recovery_strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                explanations.append("The system will automatically retry the operation after a brief delay.")
            elif recovery_strategy == RecoveryStrategy.CACHE_FALLBACK:
                explanations.append("The system is using cached information as a fallback.")
        
        return " ".join(explanations)
    
    def _generate_contextual_suggestions(
        self,
        error_category: ErrorCategory,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate context-specific suggestions."""
        suggestions = []
        
        # Provider-specific suggestions
        if "provider" in context:
            provider = context["provider"]
            suggestions.append(f"Check your {provider} API key configuration")
        
        # Model-specific suggestions
        if "model" in context:
            model = context["model"]
            suggestions.append(f"Verify that the {model} model is still available")
        
        # Bot-specific suggestions
        if "bot_name" in context:
            bot_name = context["bot_name"]
            suggestions.append(f"Contact the owner of '{bot_name}' bot for assistance")
        
        return suggestions
    
    def _cleanup_recent_notifications(self, current_time: float):
        """Clean up old notification entries."""
        cutoff_time = current_time - self._notification_cooldown * 2
        
        keys_to_remove = [
            key for key, timestamp in self._recent_notifications.items()
            if timestamp < cutoff_time
        ]
        
        for key in keys_to_remove:
            del self._recent_notifications[key]
    
    def get_troubleshooting_guide(self, error_category: ErrorCategory) -> Dict[str, Any]:
        """
        Get detailed troubleshooting guide for administrators.
        
        Args:
            error_category: Category of error
            
        Returns:
            Troubleshooting guide with diagnostic and resolution steps
        """
        return self._troubleshooting_guides.get(error_category, {
            "title": "Unknown Error Category",
            "description": "No specific troubleshooting guide available",
            "common_causes": ["Unknown error type"],
            "diagnostic_steps": ["Check system logs for more details"],
            "resolution_steps": ["Contact technical support"]
        })
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification statistics for monitoring."""
        try:
            current_time = time.time()
            
            return {
                "recent_notifications_count": len(self._recent_notifications),
                "notification_cooldown_seconds": self._notification_cooldown,
                "available_templates": list(self._notification_templates.keys()),
                "troubleshooting_categories": [cat.value for cat in self._troubleshooting_guides.keys()],
                "last_cleanup": current_time
            }
            
        except Exception as e:
            logger.error(f"Error generating notification statistics: {e}")
            return {"error": str(e)}