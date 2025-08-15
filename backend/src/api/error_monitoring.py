"""
Error Monitoring API - Endpoints for administrators to monitor RAG pipeline errors and recovery.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.comprehensive_error_handler import ComprehensiveErrorHandler, ErrorHandlingConfig
from ..services.error_reporting_service import ErrorReportingService, ReportSeverity
from ..services.error_recovery_status_service import ErrorRecoveryStatusService, RecoveryStatus
from ..services.user_notification_service import UserNotificationService
from ..services.rag_error_recovery import ErrorCategory, ErrorSeverity


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/error-monitoring", tags=["Error Monitoring"])


def get_error_handler(db: Session = Depends(get_db)) -> ComprehensiveErrorHandler:
    """Get comprehensive error handler instance."""
    return ComprehensiveErrorHandler(db)


def get_error_reporting_service(db: Session = Depends(get_db)) -> ErrorReportingService:
    """Get error reporting service instance."""
    return ErrorReportingService(db)


def get_recovery_status_service(db: Session = Depends(get_db)) -> ErrorRecoveryStatusService:
    """Get recovery status service instance."""
    return ErrorRecoveryStatusService(db)


def get_notification_service(db: Session = Depends(get_db)) -> UserNotificationService:
    """Get user notification service instance."""
    return UserNotificationService(db)


@router.get("/health")
async def get_system_health(
    error_handler: ComprehensiveErrorHandler = Depends(get_error_handler),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall system health status.
    
    Requires administrator privileges.
    """
    # TODO: Add admin permission check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get comprehensive statistics
        stats = error_handler.get_comprehensive_statistics()
        
        # Get recovery metrics
        recovery_metrics = error_handler.recovery_status_service.calculate_recovery_metrics()
        
        # Get system health report
        health_report = error_handler.error_reporting_service.generate_system_health_report()
        
        return {
            "status": "success",
            "data": {
                "system_health": health_report,
                "recovery_metrics": recovery_metrics,
                "comprehensive_stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/error-reports")
async def get_error_reports(
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    bot_id: Optional[str] = Query(None),
    since_hours: Optional[int] = Query(24, ge=1, le=168),  # Last 24 hours by default, max 1 week
    error_reporting: ErrorReportingService = Depends(get_error_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get error reports with filtering options.
    
    Requires administrator privileges.
    """
    try:
        # Parse filters
        severity_filter = None
        if severity:
            try:
                severity_filter = ReportSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        category_filter = None
        if category:
            try:
                category_filter = ErrorCategory(category.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        bot_id_filter = None
        if bot_id:
            try:
                bot_id_filter = uuid.UUID(bot_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid bot_id format: {bot_id}")
        
        since_timestamp = None
        if since_hours:
            since_timestamp = (datetime.utcnow() - timedelta(hours=since_hours)).timestamp()
        
        # Get error reports
        reports = error_reporting.get_error_reports(
            limit=limit,
            severity=severity_filter,
            category=category_filter,
            bot_id=bot_id_filter,
            since=since_timestamp
        )
        
        # Convert to serializable format
        serialized_reports = []
        for report in reports:
            serialized_reports.append({
                "id": report.id,
                "timestamp": report.timestamp,
                "severity": report.severity.value,
                "category": report.category.value,
                "operation": report.operation,
                "bot_id": str(report.bot_id),
                "user_id": str(report.user_id),
                "error_message": report.error_message,
                "error_type": report.error_type,
                "recovery_applied": report.recovery_applied,
                "recovery_strategy": report.recovery_strategy.value if report.recovery_strategy else None,
                "recovery_success": report.recovery_success,
                "resolution_status": report.resolution_status,
                "troubleshooting_steps": report.troubleshooting_steps[:5],  # Limit to first 5 steps
                "context": report.context
            })
        
        return {
            "status": "success",
            "data": {
                "reports": serialized_reports,
                "total_count": len(serialized_reports),
                "filters_applied": {
                    "severity": severity,
                    "category": category,
                    "bot_id": bot_id,
                    "since_hours": since_hours,
                    "limit": limit
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting error reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error reports: {str(e)}"
        )


@router.get("/error-patterns")
async def get_error_patterns(
    min_occurrences: int = Query(3, ge=2, le=100),
    error_reporting: ErrorReportingService = Depends(get_error_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get recurring error patterns.
    
    Requires administrator privileges.
    """
    try:
        patterns = error_reporting.get_error_patterns(min_occurrences=min_occurrences)
        
        # Convert to serializable format
        serialized_patterns = []
        for pattern in patterns:
            serialized_patterns.append({
                "pattern_id": pattern.pattern_id,
                "error_signature": pattern.error_signature,
                "occurrences": pattern.occurrences,
                "first_seen": pattern.first_seen,
                "last_seen": pattern.last_seen,
                "affected_bots_count": len(pattern.affected_bots),
                "affected_users_count": len(pattern.affected_users),
                "suggested_resolution": pattern.suggested_resolution,
                "common_context": pattern.common_context
            })
        
        return {
            "status": "success",
            "data": {
                "patterns": serialized_patterns,
                "total_patterns": len(serialized_patterns),
                "min_occurrences": min_occurrences
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting error patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error patterns: {str(e)}"
        )


@router.get("/recovery-status")
async def get_recovery_status(
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    bot_id: Optional[str] = Query(None),
    since_hours: Optional[int] = Query(24, ge=1, le=168),
    recovery_service: ErrorRecoveryStatusService = Depends(get_recovery_status_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get recovery attempt status with filtering.
    
    Requires administrator privileges.
    """
    try:
        # Parse filters
        status_filter_enum = None
        if status_filter:
            try:
                status_filter_enum = RecoveryStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        
        category_filter = None
        if category:
            try:
                category_filter = ErrorCategory(category.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        bot_id_filter = None
        if bot_id:
            try:
                bot_id_filter = uuid.UUID(bot_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid bot_id format: {bot_id}")
        
        since_timestamp = None
        if since_hours:
            since_timestamp = (datetime.utcnow() - timedelta(hours=since_hours)).timestamp()
        
        # Get recovery attempts
        attempts = recovery_service.get_recent_recovery_attempts(
            limit=limit,
            status=status_filter_enum,
            category=category_filter,
            bot_id=bot_id_filter,
            since=since_timestamp
        )
        
        # Convert to serializable format
        serialized_attempts = []
        for attempt in attempts:
            serialized_attempts.append({
                "id": attempt.id,
                "timestamp": attempt.timestamp,
                "bot_id": str(attempt.bot_id),
                "user_id": str(attempt.user_id),
                "error_category": attempt.error_category.value,
                "error_severity": attempt.error_severity.value,
                "recovery_strategy": attempt.recovery_strategy.value,
                "status": attempt.status.value,
                "duration": attempt.duration,
                "success_rate": attempt.success_rate,
                "notes": attempt.notes,
                "metadata": attempt.metadata
            })
        
        return {
            "status": "success",
            "data": {
                "recovery_attempts": serialized_attempts,
                "total_count": len(serialized_attempts),
                "filters_applied": {
                    "status": status_filter,
                    "category": category,
                    "bot_id": bot_id,
                    "since_hours": since_hours,
                    "limit": limit
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recovery status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recovery status: {str(e)}"
        )


@router.get("/service-status")
async def get_service_status(
    service_name: Optional[str] = Query(None),
    recovery_service: ErrorRecoveryStatusService = Depends(get_recovery_status_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get status of individual services or all services.
    
    Requires administrator privileges.
    """
    try:
        service_status = recovery_service.get_service_status(service_name)
        
        # Convert to serializable format
        if service_name:
            # Single service
            if service_status:
                serialized_status = {
                    "service_name": service_status.service_name,
                    "current_status": service_status.current_status.value,
                    "last_incident": service_status.last_incident,
                    "recovery_time": service_status.recovery_time,
                    "uptime_percentage": service_status.uptime_percentage,
                    "recent_failures": service_status.recent_failures,
                    "recovery_success_rate": service_status.recovery_success_rate,
                    "average_recovery_time": service_status.average_recovery_time,
                    "last_successful_recovery": service_status.last_successful_recovery,
                    "ongoing_issues": service_status.ongoing_issues
                }
            else:
                raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        else:
            # All services
            serialized_status = {}
            for name, status in service_status.items():
                serialized_status[name] = {
                    "service_name": status.service_name,
                    "current_status": status.current_status.value,
                    "last_incident": status.last_incident,
                    "recovery_time": status.recovery_time,
                    "uptime_percentage": status.uptime_percentage,
                    "recent_failures": status.recent_failures,
                    "recovery_success_rate": status.recovery_success_rate,
                    "average_recovery_time": status.average_recovery_time,
                    "last_successful_recovery": status.last_successful_recovery,
                    "ongoing_issues": status.ongoing_issues
                }
        
        return {
            "status": "success",
            "data": {
                "service_status": serialized_status,
                "requested_service": service_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )


@router.get("/recovery-report")
async def get_recovery_report(
    hours: int = Query(24, ge=1, le=168),  # Default 24 hours, max 1 week
    recovery_service: ErrorRecoveryStatusService = Depends(get_recovery_status_service),
    current_user: User = Depends(get_current_user)
):
    """
    Generate comprehensive recovery report for specified time range.
    
    Requires administrator privileges.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow().timestamp()
        start_time = end_time - (hours * 3600)
        
        # Generate report
        report = recovery_service.generate_recovery_report(
            time_range=(start_time, end_time)
        )
        
        return {
            "status": "success",
            "data": report
        }
        
    except Exception as e:
        logger.error(f"Error generating recovery report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recovery report: {str(e)}"
        )


@router.get("/troubleshooting-guide/{error_category}")
async def get_troubleshooting_guide(
    error_category: str,
    error_reporting: ErrorReportingService = Depends(get_error_reporting_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get troubleshooting guide for specific error category.
    
    Requires administrator privileges.
    """
    try:
        # Validate error category
        try:
            category_enum = ErrorCategory(error_category.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid error category: {error_category}")
        
        # Get troubleshooting guide
        guide = error_reporting.get_troubleshooting_guide(error_category.lower())
        
        if not guide:
            raise HTTPException(status_code=404, detail=f"No troubleshooting guide found for {error_category}")
        
        return {
            "status": "success",
            "data": {
                "error_category": error_category,
                "troubleshooting_guide": guide
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting troubleshooting guide: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get troubleshooting guide: {str(e)}"
        )


@router.get("/notification-stats")
async def get_notification_statistics(
    notification_service: UserNotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get user notification statistics.
    
    Requires administrator privileges.
    """
    try:
        stats = notification_service.get_notification_statistics()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting notification statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification statistics: {str(e)}"
        )


@router.post("/reset-statistics")
async def reset_error_statistics(
    error_handler: ComprehensiveErrorHandler = Depends(get_error_handler),
    current_user: User = Depends(get_current_user)
):
    """
    Reset error and recovery statistics.
    
    Requires administrator privileges.
    """
    try:
        # Reset statistics in all services
        error_handler.reset_statistics()
        
        return {
            "status": "success",
            "message": "Error and recovery statistics have been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset statistics: {str(e)}"
        )