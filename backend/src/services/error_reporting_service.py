"""
Error Reporting Service - Detailed error logging and reporting for administrators.
"""
import logging
import time
import json
import traceback
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import text

from .rag_error_recovery import ErrorCategory, ErrorSeverity, RecoveryStrategy


logger = logging.getLogger(__name__)


class ReportSeverity(Enum):
    """Severity levels for error reports."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorReport:
    """Detailed error report for administrators."""
    id: str
    timestamp: float
    severity: ReportSeverity
    category: ErrorCategory
    operation: str
    bot_id: uuid.UUID
    user_id: uuid.UUID
    error_message: str
    error_type: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    recovery_applied: bool
    recovery_strategy: Optional[RecoveryStrategy]
    recovery_success: bool
    system_state: Dict[str, Any]
    troubleshooting_steps: List[str]
    resolution_status: str = "unresolved"  # unresolved, investigating, resolved
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = f"err_{int(self.timestamp)}_{str(uuid.uuid4())[:8]}"


@dataclass
class ErrorPattern:
    """Pattern analysis for recurring errors."""
    pattern_id: str
    error_signature: str
    occurrences: int
    first_seen: float
    last_seen: float
    affected_bots: List[str]
    affected_users: List[str]
    common_context: Dict[str, Any]
    suggested_resolution: str


@dataclass
class SystemHealthReport:
    """System health report for monitoring."""
    timestamp: float
    overall_health: str  # healthy, degraded, unhealthy
    service_status: Dict[str, str]
    error_rates: Dict[str, float]
    recovery_rates: Dict[str, float]
    active_issues: List[str]
    recommendations: List[str]


class ErrorReportingService:
    """
    Service for detailed error logging and reporting for administrators.
    
    This service provides:
    - Comprehensive error logging with full context
    - Error pattern analysis and trend detection
    - System health monitoring and reporting
    - Troubleshooting guidance and resolution tracking
    - Integration with monitoring and alerting systems
    """
    
    def __init__(self, db: Session):
        """
        Initialize error reporting service.
        
        Args:
            db: Database session
        """
        self.db = db
        
        # Error storage (in production, this would be a proper database or logging system)
        self._error_reports: List[ErrorReport] = []
        self._error_patterns: Dict[str, ErrorPattern] = {}
        
        # Configuration
        self.max_stored_reports = 10000
        self.pattern_detection_threshold = 3
        self.health_check_interval = 300  # 5 minutes
        
        # System state tracking
        self._last_health_check = 0
        self._system_metrics: Dict[str, Any] = {}
        
        # Initialize troubleshooting database
        self._troubleshooting_database = self._initialize_troubleshooting_database()
    
    def _initialize_troubleshooting_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize comprehensive troubleshooting database."""
        return {
            # API Key Issues
            "api_key_missing": {
                "title": "Missing API Key",
                "description": "No API key configured for the required provider",
                "diagnostic_queries": [
                    "SELECT * FROM user_api_keys WHERE user_id = ? AND provider = ?",
                    "SELECT embedding_provider, llm_provider FROM bots WHERE id = ?"
                ],
                "diagnostic_steps": [
                    "Check if user has API key configured for the provider",
                    "Verify bot's provider configuration",
                    "Check if API key was recently deleted or expired"
                ],
                "resolution_steps": [
                    "Guide user to configure API key in settings",
                    "Verify API key format and validity",
                    "Test API key with provider's validation endpoint"
                ],
                "prevention_tips": [
                    "Implement API key validation during bot creation",
                    "Add API key expiration monitoring",
                    "Provide clear setup instructions for users"
                ]
            },
            
            "api_key_invalid": {
                "title": "Invalid or Expired API Key",
                "description": "API key exists but is not valid or has expired",
                "diagnostic_queries": [
                    "SELECT created_at, last_used FROM user_api_keys WHERE user_id = ? AND provider = ?",
                    "SELECT COUNT(*) FROM activity_logs WHERE user_id = ? AND operation LIKE '%api_key%'"
                ],
                "diagnostic_steps": [
                    "Check when API key was last successfully used",
                    "Verify API key format matches provider requirements",
                    "Test API key directly with provider API",
                    "Check for recent provider API changes"
                ],
                "resolution_steps": [
                    "Ask user to regenerate API key from provider",
                    "Update API key in user settings",
                    "Clear any cached validation results",
                    "Test with a simple API call"
                ],
                "prevention_tips": [
                    "Implement periodic API key validation",
                    "Monitor provider API changes and deprecations",
                    "Add API key health checks to monitoring"
                ]
            },
            
            # Embedding Issues
            "embedding_dimension_mismatch": {
                "title": "Embedding Dimension Mismatch",
                "description": "Stored embeddings have different dimensions than current model",
                "diagnostic_queries": [
                    "SELECT embedding_provider, embedding_model FROM bots WHERE id = ?",
                    "SELECT COUNT(*) FROM document_chunks WHERE bot_id = ?",
                    "SELECT config FROM vector_collections WHERE bot_id = ?"
                ],
                "diagnostic_steps": [
                    "Check current bot embedding configuration",
                    "Verify vector collection configuration",
                    "Compare expected vs actual embedding dimensions",
                    "Check when embedding model was last changed"
                ],
                "resolution_steps": [
                    "Backup existing vector collection",
                    "Create new collection with correct dimensions",
                    "Reprocess all documents with new embedding model",
                    "Update bot configuration if needed"
                ],
                "prevention_tips": [
                    "Validate embedding dimensions before model changes",
                    "Implement migration workflows for model updates",
                    "Add dimension compatibility checks"
                ]
            },
            
            "embedding_rate_limit": {
                "title": "Embedding API Rate Limit",
                "description": "Provider API rate limit exceeded",
                "diagnostic_queries": [
                    "SELECT COUNT(*) FROM activity_logs WHERE operation = 'embedding_generation' AND created_at > ?",
                    "SELECT api_usage_stats FROM user_api_keys WHERE user_id = ? AND provider = ?"
                ],
                "diagnostic_steps": [
                    "Check recent embedding API usage",
                    "Verify current rate limits for user's API plan",
                    "Check if multiple bots are using same API key",
                    "Monitor API usage patterns"
                ],
                "resolution_steps": [
                    "Implement exponential backoff retry logic",
                    "Suggest API plan upgrade if needed",
                    "Add request queuing and throttling",
                    "Consider embedding caching"
                ],
                "prevention_tips": [
                    "Implement proactive rate limit monitoring",
                    "Add embedding caching to reduce API calls",
                    "Distribute load across multiple API keys"
                ]
            },
            
            # Vector Search Issues
            "vector_collection_missing": {
                "title": "Vector Collection Not Found",
                "description": "Bot's vector collection doesn't exist in the vector database",
                "diagnostic_queries": [
                    "SELECT * FROM bots WHERE id = ?",
                    "SELECT COUNT(*) FROM documents WHERE bot_id = ?",
                    "SELECT * FROM vector_collections WHERE bot_id = ?"
                ],
                "diagnostic_steps": [
                    "Check if bot exists and is properly configured",
                    "Verify if documents have been uploaded",
                    "Check vector database connection",
                    "Look for collection creation errors in logs"
                ],
                "resolution_steps": [
                    "Create vector collection with correct configuration",
                    "Process existing documents to populate collection",
                    "Update collection metadata in database",
                    "Test collection accessibility"
                ],
                "prevention_tips": [
                    "Implement automatic collection creation",
                    "Add collection health checks",
                    "Monitor collection creation success rates"
                ]
            },
            
            "vector_search_timeout": {
                "title": "Vector Search Timeout",
                "description": "Vector database search operation timed out",
                "diagnostic_queries": [
                    "SELECT COUNT(*) FROM document_chunks WHERE bot_id = ?",
                    "SELECT AVG(search_time) FROM search_metrics WHERE bot_id = ? AND created_at > ?"
                ],
                "diagnostic_steps": [
                    "Check vector collection size and complexity",
                    "Monitor vector database performance metrics",
                    "Check network connectivity to vector database",
                    "Analyze search query complexity"
                ],
                "resolution_steps": [
                    "Optimize vector collection configuration",
                    "Implement search result caching",
                    "Add connection pooling and retry logic",
                    "Consider collection partitioning for large datasets"
                ],
                "prevention_tips": [
                    "Monitor search performance metrics",
                    "Implement search timeout handling",
                    "Add vector database performance monitoring"
                ]
            }
        }
    
    async def create_error_report(
        self,
        error: Exception,
        operation: str,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        error_category: ErrorCategory,
        error_severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        recovery_applied: bool = False,
        recovery_strategy: Optional[RecoveryStrategy] = None,
        recovery_success: bool = False
    ) -> ErrorReport:
        """
        Create comprehensive error report for administrators.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            bot_id: Bot identifier
            user_id: User identifier
            error_category: Category of the error
            error_severity: Severity of the error
            context: Additional context information
            recovery_applied: Whether error recovery was applied
            recovery_strategy: Recovery strategy used
            recovery_success: Whether recovery was successful
            
        Returns:
            ErrorReport with comprehensive details
        """
        current_time = time.time()
        
        # Generate error signature for pattern detection
        error_signature = self._generate_error_signature(error, operation, error_category)
        
        # Collect system state
        system_state = await self._collect_system_state(bot_id, user_id)
        
        # Generate troubleshooting steps
        troubleshooting_steps = self._generate_troubleshooting_steps(
            error, error_category, context or {}
        )
        
        # Create error report
        report = ErrorReport(
            id="",  # Will be auto-generated
            timestamp=current_time,
            severity=self._map_severity(error_severity),
            category=error_category,
            operation=operation,
            bot_id=bot_id,
            user_id=user_id,
            error_message=str(error),
            error_type=type(error).__name__,
            stack_trace=traceback.format_exc(),
            context=context or {},
            recovery_applied=recovery_applied,
            recovery_strategy=recovery_strategy,
            recovery_success=recovery_success,
            system_state=system_state,
            troubleshooting_steps=troubleshooting_steps
        )
        
        # Store report
        self._store_error_report(report)
        
        # Update error patterns
        self._update_error_patterns(error_signature, report)
        
        # Log to system logger
        self._log_error_report(report)
        
        logger.info(f"Created error report {report.id} for {operation} failure")
        
        return report
    
    def _generate_error_signature(
        self,
        error: Exception,
        operation: str,
        error_category: ErrorCategory
    ) -> str:
        """Generate unique signature for error pattern detection."""
        # Create signature based on error type, operation, and key message parts
        error_message = str(error).lower()
        
        # Extract key terms from error message
        key_terms = []
        for term in ["api key", "timeout", "connection", "not found", "invalid", "rate limit"]:
            if term in error_message:
                key_terms.append(term.replace(" ", "_"))
        
        signature_parts = [
            type(error).__name__,
            operation,
            error_category.value,
            "_".join(key_terms)
        ]
        
        return "_".join(filter(None, signature_parts))
    
    async def _collect_system_state(self, bot_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Collect current system state for debugging."""
        try:
            state = {
                "timestamp": time.time(),
                "bot_info": {},
                "user_info": {},
                "system_metrics": {},
                "database_stats": {}
            }
            
            # Collect bot information
            try:
                bot_query = text("SELECT * FROM bots WHERE id = :bot_id")
                bot_result = self.db.execute(bot_query, {"bot_id": str(bot_id)}).fetchone()
                if bot_result:
                    state["bot_info"] = dict(bot_result._mapping)
            except Exception as e:
                state["bot_info"] = {"error": str(e)}
            
            # Collect user information (non-sensitive)
            try:
                user_query = text("SELECT id, email, created_at FROM users WHERE id = :user_id")
                user_result = self.db.execute(user_query, {"user_id": str(user_id)}).fetchone()
                if user_result:
                    state["user_info"] = dict(user_result._mapping)
            except Exception as e:
                state["user_info"] = {"error": str(e)}
            
            # Collect system metrics
            state["system_metrics"] = {
                "active_connections": "unknown",  # Would integrate with connection pool
                "memory_usage": "unknown",        # Would integrate with system monitoring
                "cpu_usage": "unknown",           # Would integrate with system monitoring
                "disk_usage": "unknown"           # Would integrate with system monitoring
            }
            
            # Collect database statistics
            try:
                # Count documents for bot
                doc_count_query = text("SELECT COUNT(*) as count FROM documents WHERE bot_id = :bot_id")
                doc_count = self.db.execute(doc_count_query, {"bot_id": str(bot_id)}).fetchone()
                state["database_stats"]["document_count"] = doc_count.count if doc_count else 0
                
                # Count chunks for bot
                chunk_count_query = text("SELECT COUNT(*) as count FROM document_chunks WHERE document_id IN (SELECT id FROM documents WHERE bot_id = :bot_id)")
                chunk_count = self.db.execute(chunk_count_query, {"bot_id": str(bot_id)}).fetchone()
                state["database_stats"]["chunk_count"] = chunk_count.count if chunk_count else 0
                
            except Exception as e:
                state["database_stats"] = {"error": str(e)}
            
            return state
            
        except Exception as e:
            logger.error(f"Error collecting system state: {e}")
            return {"error": str(e), "timestamp": time.time()}
    
    def _generate_troubleshooting_steps(
        self,
        error: Exception,
        error_category: ErrorCategory,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate specific troubleshooting steps based on error details."""
        steps = []
        
        # Get error-specific troubleshooting info
        error_signature = self._generate_error_signature(error, context.get("operation", "unknown"), error_category)
        
        # Look for specific troubleshooting guide
        for key, guide in self._troubleshooting_database.items():
            if key in error_signature.lower() or key in str(error).lower():
                steps.extend(guide.get("diagnostic_steps", []))
                steps.extend(guide.get("resolution_steps", []))
                break
        
        # Add general troubleshooting steps if no specific guide found
        if not steps:
            steps = [
                "Check system logs for additional error details",
                "Verify all required services are running",
                "Test basic connectivity to external services",
                "Check configuration settings for correctness",
                "Monitor system resources (CPU, memory, disk)",
                "Contact technical support if issue persists"
            ]
        
        # Add context-specific steps
        if "bot_id" in context:
            steps.append(f"Review bot configuration for bot ID: {context['bot_id']}")
        
        if "provider" in context:
            steps.append(f"Check {context['provider']} service status and API limits")
        
        return steps[:10]  # Limit to top 10 steps
    
    def _map_severity(self, error_severity: ErrorSeverity) -> ReportSeverity:
        """Map error severity to report severity."""
        mapping = {
            ErrorSeverity.LOW: ReportSeverity.INFO,
            ErrorSeverity.MEDIUM: ReportSeverity.WARNING,
            ErrorSeverity.HIGH: ReportSeverity.ERROR,
            ErrorSeverity.CRITICAL: ReportSeverity.CRITICAL
        }
        return mapping.get(error_severity, ReportSeverity.ERROR)
    
    def _store_error_report(self, report: ErrorReport):
        """Store error report in memory (in production, would use proper storage)."""
        self._error_reports.append(report)
        
        # Maintain size limit
        if len(self._error_reports) > self.max_stored_reports:
            self._error_reports = self._error_reports[-self.max_stored_reports:]
    
    def _update_error_patterns(self, error_signature: str, report: ErrorReport):
        """Update error pattern analysis."""
        if error_signature in self._error_patterns:
            pattern = self._error_patterns[error_signature]
            pattern.occurrences += 1
            pattern.last_seen = report.timestamp
            pattern.affected_bots.append(str(report.bot_id))
            pattern.affected_users.append(str(report.user_id))
            
            # Remove duplicates
            pattern.affected_bots = list(set(pattern.affected_bots))
            pattern.affected_users = list(set(pattern.affected_users))
        else:
            # Create new pattern
            self._error_patterns[error_signature] = ErrorPattern(
                pattern_id=f"pattern_{len(self._error_patterns)}_{int(time.time())}",
                error_signature=error_signature,
                occurrences=1,
                first_seen=report.timestamp,
                last_seen=report.timestamp,
                affected_bots=[str(report.bot_id)],
                affected_users=[str(report.user_id)],
                common_context=report.context,
                suggested_resolution=self._generate_pattern_resolution(error_signature)
            )
    
    def _generate_pattern_resolution(self, error_signature: str) -> str:
        """Generate suggested resolution for error pattern."""
        # Look for known patterns
        for key, guide in self._troubleshooting_database.items():
            if key in error_signature.lower():
                resolution_steps = guide.get("resolution_steps", [])
                if resolution_steps:
                    return "; ".join(resolution_steps[:3])  # Top 3 steps
        
        return "Review error details and follow standard troubleshooting procedures"
    
    def _log_error_report(self, report: ErrorReport):
        """Log error report to system logger."""
        log_data = {
            "report_id": report.id,
            "severity": report.severity.value,
            "category": report.category.value,
            "operation": report.operation,
            "bot_id": str(report.bot_id),
            "user_id": str(report.user_id),
            "error_type": report.error_type,
            "recovery_applied": report.recovery_applied,
            "recovery_success": report.recovery_success
        }
        
        if report.severity == ReportSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR REPORT: {json.dumps(log_data)}")
        elif report.severity == ReportSeverity.ERROR:
            logger.error(f"ERROR REPORT: {json.dumps(log_data)}")
        elif report.severity == ReportSeverity.WARNING:
            logger.warning(f"WARNING REPORT: {json.dumps(log_data)}")
        else:
            logger.info(f"INFO REPORT: {json.dumps(log_data)}")
    
    def get_error_reports(
        self,
        limit: int = 100,
        severity: Optional[ReportSeverity] = None,
        category: Optional[ErrorCategory] = None,
        bot_id: Optional[uuid.UUID] = None,
        since: Optional[float] = None
    ) -> List[ErrorReport]:
        """Get error reports with filtering."""
        reports = self._error_reports.copy()
        
        # Apply filters
        if severity:
            reports = [r for r in reports if r.severity == severity]
        
        if category:
            reports = [r for r in reports if r.category == category]
        
        if bot_id:
            reports = [r for r in reports if r.bot_id == bot_id]
        
        if since:
            reports = [r for r in reports if r.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        reports.sort(key=lambda r: r.timestamp, reverse=True)
        return reports[:limit]
    
    def get_error_patterns(self, min_occurrences: int = 3) -> List[ErrorPattern]:
        """Get error patterns that occur frequently."""
        patterns = [
            pattern for pattern in self._error_patterns.values()
            if pattern.occurrences >= min_occurrences
        ]
        
        # Sort by occurrences (most frequent first)
        patterns.sort(key=lambda p: p.occurrences, reverse=True)
        return patterns
    
    def generate_system_health_report(self) -> SystemHealthReport:
        """Generate comprehensive system health report."""
        current_time = time.time()
        
        # Calculate error rates for last hour
        one_hour_ago = current_time - 3600
        recent_reports = [r for r in self._error_reports if r.timestamp >= one_hour_ago]
        
        # Calculate service status
        service_status = {}
        error_rates = {}
        recovery_rates = {}
        
        for category in ErrorCategory:
            category_reports = [r for r in recent_reports if r.category == category]
            total_reports = len(category_reports)
            successful_recoveries = len([r for r in category_reports if r.recovery_success])
            
            if total_reports > 0:
                error_rates[category.value] = total_reports / 60  # errors per minute
                recovery_rates[category.value] = successful_recoveries / total_reports
                
                # Determine service status
                if error_rates[category.value] > 5:  # More than 5 errors per minute
                    service_status[category.value] = "unhealthy"
                elif error_rates[category.value] > 1:  # More than 1 error per minute
                    service_status[category.value] = "degraded"
                else:
                    service_status[category.value] = "healthy"
            else:
                error_rates[category.value] = 0
                recovery_rates[category.value] = 1.0
                service_status[category.value] = "healthy"
        
        # Determine overall health
        unhealthy_services = [s for s in service_status.values() if s == "unhealthy"]
        degraded_services = [s for s in service_status.values() if s == "degraded"]
        
        if unhealthy_services:
            overall_health = "unhealthy"
        elif degraded_services:
            overall_health = "degraded"
        else:
            overall_health = "healthy"
        
        # Generate active issues
        active_issues = []
        for pattern in self.get_error_patterns(min_occurrences=2):
            if pattern.last_seen >= one_hour_ago:
                active_issues.append(f"Recurring issue: {pattern.error_signature} ({pattern.occurrences} occurrences)")
        
        # Generate recommendations
        recommendations = []
        if overall_health != "healthy":
            recommendations.append("Review recent error reports and address recurring issues")
        
        if any(rate > 0.5 for rate in error_rates.values()):
            recommendations.append("High error rates detected - investigate system performance")
        
        if any(rate < 0.8 for rate in recovery_rates.values() if rate > 0):
            recommendations.append("Low recovery success rates - review error handling strategies")
        
        return SystemHealthReport(
            timestamp=current_time,
            overall_health=overall_health,
            service_status=service_status,
            error_rates=error_rates,
            recovery_rates=recovery_rates,
            active_issues=active_issues[:10],  # Top 10 issues
            recommendations=recommendations
        )
    
    def get_troubleshooting_guide(self, error_signature: str) -> Optional[Dict[str, Any]]:
        """Get troubleshooting guide for specific error signature."""
        for key, guide in self._troubleshooting_database.items():
            if key in error_signature.lower():
                return guide
        return None
    
    def get_reporting_statistics(self) -> Dict[str, Any]:
        """Get error reporting statistics."""
        try:
            current_time = time.time()
            
            # Calculate statistics
            total_reports = len(self._error_reports)
            recent_reports = [r for r in self._error_reports if r.timestamp >= current_time - 3600]
            
            severity_counts = {}
            category_counts = {}
            
            for report in self._error_reports:
                severity_counts[report.severity.value] = severity_counts.get(report.severity.value, 0) + 1
                category_counts[report.category.value] = category_counts.get(report.category.value, 0) + 1
            
            return {
                "total_reports": total_reports,
                "recent_reports_1h": len(recent_reports),
                "severity_distribution": severity_counts,
                "category_distribution": category_counts,
                "error_patterns_detected": len(self._error_patterns),
                "troubleshooting_guides_available": len(self._troubleshooting_database),
                "last_report_time": max([r.timestamp for r in self._error_reports]) if self._error_reports else None
            }
            
        except Exception as e:
            logger.error(f"Error generating reporting statistics: {e}")
            return {"error": str(e)}