"""
Error Recovery Status Service - Tracks and reports on error recovery status and effectiveness.
"""
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .rag_error_recovery import ErrorCategory, ErrorSeverity, RecoveryStrategy


logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """Status of error recovery attempts."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    PARTIAL = "partial"
    ABANDONED = "abandoned"


class ServiceStatus(Enum):
    """Status of individual services."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAttempt:
    """Individual recovery attempt record."""
    id: str
    timestamp: float
    bot_id: uuid.UUID
    user_id: uuid.UUID
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    status: RecoveryStatus
    duration: Optional[float] = None
    success_rate: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = f"recovery_{int(self.timestamp)}_{str(uuid.uuid4())[:8]}"


@dataclass
class ServiceRecoveryStatus:
    """Recovery status for a specific service."""
    service_name: str
    current_status: ServiceStatus
    last_incident: Optional[float]
    recovery_time: Optional[float]
    uptime_percentage: float
    recent_failures: int
    recovery_success_rate: float
    average_recovery_time: float
    last_successful_recovery: Optional[float]
    ongoing_issues: List[str]


@dataclass
class RecoveryMetrics:
    """Comprehensive recovery metrics."""
    timestamp: float
    total_recovery_attempts: int
    successful_recoveries: int
    failed_recoveries: int
    average_recovery_time: float
    recovery_success_rate: float
    strategy_effectiveness: Dict[str, float]
    category_recovery_rates: Dict[str, float]
    service_availability: Dict[str, float]
    trending_issues: List[str]


class ErrorRecoveryStatusService:
    """
    Service for tracking and reporting error recovery status and effectiveness.
    
    This service provides:
    - Real-time tracking of recovery attempts and outcomes
    - Service availability and uptime monitoring
    - Recovery strategy effectiveness analysis
    - Trending issue identification and alerting
    - Comprehensive recovery metrics and reporting
    """
    
    def __init__(self, db: Session):
        """
        Initialize error recovery status service.
        
        Args:
            db: Database session
        """
        self.db = db
        
        # Recovery tracking
        self._recovery_attempts: List[RecoveryAttempt] = []
        self._service_status: Dict[str, ServiceRecoveryStatus] = {}
        
        # Configuration
        self.max_stored_attempts = 5000
        self.metrics_calculation_interval = 300  # 5 minutes
        self.uptime_calculation_window = 86400  # 24 hours
        
        # Initialize service tracking
        self._initialize_service_tracking()
        
        # Metrics cache
        self._cached_metrics: Optional[RecoveryMetrics] = None
        self._last_metrics_calculation = 0
    
    def _initialize_service_tracking(self):
        """Initialize service status tracking."""
        services = [
            "embedding_service",
            "vector_search_service",
            "collection_management_service",
            "api_key_service",
            "llm_service"
        ]
        
        current_time = time.time()
        
        for service in services:
            self._service_status[service] = ServiceRecoveryStatus(
                service_name=service,
                current_status=ServiceStatus.UNKNOWN,
                last_incident=None,
                recovery_time=None,
                uptime_percentage=100.0,
                recent_failures=0,
                recovery_success_rate=1.0,
                average_recovery_time=0.0,
                last_successful_recovery=None,
                ongoing_issues=[]
            )
    
    def record_recovery_attempt(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        error_category: ErrorCategory,
        error_severity: ErrorSeverity,
        recovery_strategy: RecoveryStrategy,
        initial_status: RecoveryStatus = RecoveryStatus.PENDING,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a new recovery attempt.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            error_category: Category of the error being recovered from
            error_severity: Severity of the error
            recovery_strategy: Strategy being used for recovery
            initial_status: Initial status of the recovery attempt
            metadata: Additional metadata about the recovery attempt
            
        Returns:
            Recovery attempt ID
        """
        attempt = RecoveryAttempt(
            id="",  # Will be auto-generated
            timestamp=time.time(),
            bot_id=bot_id,
            user_id=user_id,
            error_category=error_category,
            error_severity=error_severity,
            recovery_strategy=recovery_strategy,
            status=initial_status,
            metadata=metadata or {}
        )
        
        self._recovery_attempts.append(attempt)
        
        # Maintain size limit
        if len(self._recovery_attempts) > self.max_stored_attempts:
            self._recovery_attempts = self._recovery_attempts[-self.max_stored_attempts:]
        
        # Update service status
        service_name = self._map_category_to_service(error_category)
        if service_name:
            self._update_service_incident(service_name, attempt.timestamp)
        
        logger.info(f"Recorded recovery attempt {attempt.id} for {error_category.value}")
        
        return attempt.id
    
    def update_recovery_status(
        self,
        recovery_id: str,
        status: RecoveryStatus,
        duration: Optional[float] = None,
        success_rate: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update the status of a recovery attempt.
        
        Args:
            recovery_id: ID of the recovery attempt
            status: New status
            duration: Duration of the recovery attempt
            success_rate: Success rate if applicable
            notes: Additional notes about the recovery
            
        Returns:
            True if update was successful
        """
        try:
            # Find the recovery attempt
            attempt = None
            for a in self._recovery_attempts:
                if a.id == recovery_id:
                    attempt = a
                    break
            
            if not attempt:
                logger.warning(f"Recovery attempt {recovery_id} not found")
                return False
            
            # Update status
            old_status = attempt.status
            attempt.status = status
            
            if duration is not None:
                attempt.duration = duration
            
            if success_rate is not None:
                attempt.success_rate = success_rate
            
            if notes:
                attempt.notes = notes
            
            # Update service status based on recovery outcome
            service_name = self._map_category_to_service(attempt.error_category)
            if service_name:
                self._update_service_recovery(service_name, attempt, old_status, status)
            
            logger.info(f"Updated recovery attempt {recovery_id}: {old_status.value} -> {status.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating recovery status {recovery_id}: {e}")
            return False
    
    def _map_category_to_service(self, error_category: ErrorCategory) -> Optional[str]:
        """Map error category to service name."""
        mapping = {
            ErrorCategory.EMBEDDING_GENERATION: "embedding_service",
            ErrorCategory.VECTOR_SEARCH: "vector_search_service",
            ErrorCategory.COLLECTION_MANAGEMENT: "collection_management_service",
            ErrorCategory.API_KEY_VALIDATION: "api_key_service",
            ErrorCategory.CONFIGURATION_VALIDATION: "api_key_service",
            ErrorCategory.NETWORK_CONNECTIVITY: "embedding_service",  # Could affect multiple services
            ErrorCategory.RESOURCE_EXHAUSTION: "embedding_service",
            ErrorCategory.DATA_CORRUPTION: "collection_management_service"
        }
        return mapping.get(error_category)
    
    def _update_service_incident(self, service_name: str, incident_time: float):
        """Update service status when an incident occurs."""
        if service_name not in self._service_status:
            return
        
        service = self._service_status[service_name]
        service.last_incident = incident_time
        service.recent_failures += 1
        
        # Update service status based on recent failures
        if service.recent_failures >= 5:
            service.current_status = ServiceStatus.OUTAGE
        elif service.recent_failures >= 2:
            service.current_status = ServiceStatus.DEGRADED
        else:
            service.current_status = ServiceStatus.OPERATIONAL
        
        # Calculate uptime
        self._calculate_service_uptime(service_name)
    
    def _update_service_recovery(
        self,
        service_name: str,
        attempt: RecoveryAttempt,
        old_status: RecoveryStatus,
        new_status: RecoveryStatus
    ):
        """Update service status based on recovery outcome."""
        if service_name not in self._service_status:
            return
        
        service = self._service_status[service_name]
        
        if new_status == RecoveryStatus.SUCCESSFUL:
            # Successful recovery
            service.last_successful_recovery = time.time()
            service.recovery_time = attempt.duration
            
            # Reset failure count and improve status
            service.recent_failures = max(0, service.recent_failures - 1)
            
            if service.recent_failures == 0:
                service.current_status = ServiceStatus.OPERATIONAL
            elif service.recent_failures < 2:
                service.current_status = ServiceStatus.DEGRADED
            
            # Update recovery success rate
            self._update_recovery_success_rate(service_name)
            
        elif new_status == RecoveryStatus.FAILED:
            # Failed recovery
            if service.current_status != ServiceStatus.OUTAGE:
                service.current_status = ServiceStatus.DEGRADED
        
        # Calculate uptime
        self._calculate_service_uptime(service_name)
    
    def _calculate_service_uptime(self, service_name: str):
        """Calculate service uptime percentage."""
        if service_name not in self._service_status:
            return
        
        service = self._service_status[service_name]
        current_time = time.time()
        window_start = current_time - self.uptime_calculation_window
        
        # Count incidents in the time window
        incidents_in_window = 0
        total_downtime = 0
        
        for attempt in self._recovery_attempts:
            if (attempt.timestamp >= window_start and 
                self._map_category_to_service(attempt.error_category) == service_name):
                
                incidents_in_window += 1
                
                # Estimate downtime based on recovery duration
                if attempt.duration:
                    total_downtime += attempt.duration
                else:
                    # Estimate based on error severity
                    if attempt.error_severity == ErrorSeverity.CRITICAL:
                        total_downtime += 300  # 5 minutes
                    elif attempt.error_severity == ErrorSeverity.HIGH:
                        total_downtime += 120  # 2 minutes
                    else:
                        total_downtime += 30   # 30 seconds
        
        # Calculate uptime percentage
        uptime_seconds = self.uptime_calculation_window - total_downtime
        service.uptime_percentage = max(0, (uptime_seconds / self.uptime_calculation_window) * 100)
    
    def _update_recovery_success_rate(self, service_name: str):
        """Update recovery success rate for a service."""
        if service_name not in self._service_status:
            return
        
        # Count successful vs failed recoveries for this service
        successful = 0
        total = 0
        
        for attempt in self._recovery_attempts:
            if self._map_category_to_service(attempt.error_category) == service_name:
                total += 1
                if attempt.status == RecoveryStatus.SUCCESSFUL:
                    successful += 1
        
        if total > 0:
            self._service_status[service_name].recovery_success_rate = successful / total
        else:
            self._service_status[service_name].recovery_success_rate = 1.0
    
    def get_recovery_status(self, recovery_id: str) -> Optional[RecoveryAttempt]:
        """Get status of a specific recovery attempt."""
        for attempt in self._recovery_attempts:
            if attempt.id == recovery_id:
                return attempt
        return None
    
    def get_service_status(self, service_name: Optional[str] = None) -> Union[ServiceRecoveryStatus, Dict[str, ServiceRecoveryStatus]]:
        """Get status of services."""
        if service_name:
            return self._service_status.get(service_name)
        else:
            return self._service_status.copy()
    
    def get_recent_recovery_attempts(
        self,
        limit: int = 100,
        status: Optional[RecoveryStatus] = None,
        category: Optional[ErrorCategory] = None,
        bot_id: Optional[uuid.UUID] = None,
        since: Optional[float] = None
    ) -> List[RecoveryAttempt]:
        """Get recent recovery attempts with filtering."""
        attempts = self._recovery_attempts.copy()
        
        # Apply filters
        if status:
            attempts = [a for a in attempts if a.status == status]
        
        if category:
            attempts = [a for a in attempts if a.error_category == category]
        
        if bot_id:
            attempts = [a for a in attempts if a.bot_id == bot_id]
        
        if since:
            attempts = [a for a in attempts if a.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        attempts.sort(key=lambda a: a.timestamp, reverse=True)
        return attempts[:limit]
    
    def calculate_recovery_metrics(self, force_recalculate: bool = False) -> RecoveryMetrics:
        """Calculate comprehensive recovery metrics."""
        current_time = time.time()
        
        # Use cached metrics if recent enough
        if (not force_recalculate and 
            self._cached_metrics and 
            current_time - self._last_metrics_calculation < self.metrics_calculation_interval):
            return self._cached_metrics
        
        # Calculate metrics
        total_attempts = len(self._recovery_attempts)
        successful_recoveries = len([a for a in self._recovery_attempts if a.status == RecoveryStatus.SUCCESSFUL])
        failed_recoveries = len([a for a in self._recovery_attempts if a.status == RecoveryStatus.FAILED])
        
        # Calculate average recovery time
        recovery_times = [a.duration for a in self._recovery_attempts if a.duration and a.status == RecoveryStatus.SUCCESSFUL]
        average_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0
        
        # Calculate overall success rate
        recovery_success_rate = successful_recoveries / total_attempts if total_attempts > 0 else 1.0
        
        # Calculate strategy effectiveness
        strategy_effectiveness = {}
        for strategy in RecoveryStrategy:
            strategy_attempts = [a for a in self._recovery_attempts if a.recovery_strategy == strategy]
            strategy_successes = [a for a in strategy_attempts if a.status == RecoveryStatus.SUCCESSFUL]
            
            if strategy_attempts:
                strategy_effectiveness[strategy.value] = len(strategy_successes) / len(strategy_attempts)
            else:
                strategy_effectiveness[strategy.value] = 0.0
        
        # Calculate category recovery rates
        category_recovery_rates = {}
        for category in ErrorCategory:
            category_attempts = [a for a in self._recovery_attempts if a.error_category == category]
            category_successes = [a for a in category_attempts if a.status == RecoveryStatus.SUCCESSFUL]
            
            if category_attempts:
                category_recovery_rates[category.value] = len(category_successes) / len(category_attempts)
            else:
                category_recovery_rates[category.value] = 1.0
        
        # Calculate service availability
        service_availability = {}
        for service_name, service_status in self._service_status.items():
            service_availability[service_name] = service_status.uptime_percentage
        
        # Identify trending issues
        trending_issues = self._identify_trending_issues()
        
        # Create metrics object
        metrics = RecoveryMetrics(
            timestamp=current_time,
            total_recovery_attempts=total_attempts,
            successful_recoveries=successful_recoveries,
            failed_recoveries=failed_recoveries,
            average_recovery_time=average_recovery_time,
            recovery_success_rate=recovery_success_rate,
            strategy_effectiveness=strategy_effectiveness,
            category_recovery_rates=category_recovery_rates,
            service_availability=service_availability,
            trending_issues=trending_issues
        )
        
        # Cache metrics
        self._cached_metrics = metrics
        self._last_metrics_calculation = current_time
        
        return metrics
    
    def _identify_trending_issues(self) -> List[str]:
        """Identify trending issues based on recent recovery attempts."""
        current_time = time.time()
        recent_window = current_time - 3600  # Last hour
        
        recent_attempts = [a for a in self._recovery_attempts if a.timestamp >= recent_window]
        
        # Count issues by category and strategy
        issue_counts = {}
        
        for attempt in recent_attempts:
            if attempt.status in [RecoveryStatus.FAILED, RecoveryStatus.PARTIAL]:
                key = f"{attempt.error_category.value}_{attempt.recovery_strategy.value}"
                issue_counts[key] = issue_counts.get(key, 0) + 1
        
        # Sort by frequency and return top issues
        trending = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [f"{issue} ({count} occurrences)" for issue, count in trending[:5]]
    
    def generate_recovery_report(
        self,
        time_range: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive recovery status report."""
        try:
            current_time = time.time()
            
            # Default to last 24 hours if no time range specified
            if not time_range:
                time_range = (current_time - 86400, current_time)
            
            start_time, end_time = time_range
            
            # Filter attempts by time range
            filtered_attempts = [
                a for a in self._recovery_attempts 
                if start_time <= a.timestamp <= end_time
            ]
            
            # Calculate metrics for the time range
            total_attempts = len(filtered_attempts)
            successful = len([a for a in filtered_attempts if a.status == RecoveryStatus.SUCCESSFUL])
            failed = len([a for a in filtered_attempts if a.status == RecoveryStatus.FAILED])
            in_progress = len([a for a in filtered_attempts if a.status == RecoveryStatus.IN_PROGRESS])
            
            # Group by category
            category_stats = {}
            for category in ErrorCategory:
                category_attempts = [a for a in filtered_attempts if a.error_category == category]
                category_stats[category.value] = {
                    "total": len(category_attempts),
                    "successful": len([a for a in category_attempts if a.status == RecoveryStatus.SUCCESSFUL]),
                    "failed": len([a for a in category_attempts if a.status == RecoveryStatus.FAILED]),
                    "success_rate": len([a for a in category_attempts if a.status == RecoveryStatus.SUCCESSFUL]) / len(category_attempts) if category_attempts else 1.0
                }
            
            # Group by strategy
            strategy_stats = {}
            for strategy in RecoveryStrategy:
                strategy_attempts = [a for a in filtered_attempts if a.recovery_strategy == strategy]
                strategy_stats[strategy.value] = {
                    "total": len(strategy_attempts),
                    "successful": len([a for a in strategy_attempts if a.status == RecoveryStatus.SUCCESSFUL]),
                    "failed": len([a for a in strategy_attempts if a.status == RecoveryStatus.FAILED]),
                    "success_rate": len([a for a in strategy_attempts if a.status == RecoveryStatus.SUCCESSFUL]) / len(strategy_attempts) if strategy_attempts else 1.0
                }
            
            return {
                "report_timestamp": current_time,
                "time_range": {
                    "start": start_time,
                    "end": end_time,
                    "duration_hours": (end_time - start_time) / 3600
                },
                "summary": {
                    "total_attempts": total_attempts,
                    "successful": successful,
                    "failed": failed,
                    "in_progress": in_progress,
                    "overall_success_rate": successful / total_attempts if total_attempts > 0 else 1.0
                },
                "category_breakdown": category_stats,
                "strategy_breakdown": strategy_stats,
                "service_status": {name: asdict(status) for name, status in self._service_status.items()},
                "current_metrics": asdict(self.calculate_recovery_metrics())
            }
            
        except Exception as e:
            logger.error(f"Error generating recovery report: {e}")
            return {"error": str(e), "timestamp": time.time()}
    
    def get_status_statistics(self) -> Dict[str, Any]:
        """Get recovery status tracking statistics."""
        try:
            current_time = time.time()
            
            return {
                "total_recovery_attempts": len(self._recovery_attempts),
                "services_tracked": len(self._service_status),
                "last_metrics_calculation": self._last_metrics_calculation,
                "metrics_cache_age": current_time - self._last_metrics_calculation,
                "uptime_calculation_window_hours": self.uptime_calculation_window / 3600,
                "recent_attempts_1h": len([a for a in self._recovery_attempts if a.timestamp >= current_time - 3600]),
                "active_recoveries": len([a for a in self._recovery_attempts if a.status == RecoveryStatus.IN_PROGRESS])
            }
            
        except Exception as e:
            logger.error(f"Error generating status statistics: {e}")
            return {"error": str(e)}