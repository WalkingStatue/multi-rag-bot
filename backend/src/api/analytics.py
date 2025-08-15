"""
Analytics API endpoints for bot usage metrics and activity tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.analytics_service import AnalyticsService
from ..schemas.analytics import (
    BotAnalytics, UserDashboardAnalytics, ActivityLogsResponse,
    SystemAnalytics, BotExportData, AnalyticsSummary
)

router = APIRouter(tags=["analytics"])


@router.get("/bots/{bot_id}/analytics", response_model=BotAnalytics)
async def get_bot_analytics(
    bot_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive usage analytics for a specific bot.
    
    Returns metrics including:
    - Total conversations and messages
    - Unique users and activity patterns
    - Daily activity breakdown
    - Top users by activity
    - Response times and token usage
    """
    try:
        analytics_service = AnalyticsService(db)
        analytics = analytics_service.get_bot_usage_analytics(
            bot_id=bot_id,
            user_id=str(current_user.id),
            days=days
        )
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bot analytics: {str(e)}")


@router.get("/dashboard/analytics", response_model=UserDashboardAnalytics)
async def get_dashboard_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard analytics for the current user across all accessible bots.
    
    Returns:
    - Overview metrics (total bots, conversations, messages)
    - Bot activity breakdown
    - Recent conversations
    - Usage patterns
    """
    try:
        analytics_service = AnalyticsService(db)
        analytics = analytics_service.get_user_dashboard_analytics(
            user_id=str(current_user.id),
            days=days
        )
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard analytics: {str(e)}")


@router.get("/bots/{bot_id}/activity", response_model=ActivityLogsResponse)
async def get_bot_activity_logs(
    bot_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of activity logs to return"),
    action: Optional[str] = Query(None, description="Filter by specific action type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get activity logs for a specific bot.
    
    Returns chronological list of bot modifications, permission changes,
    and other significant events.
    """
    try:
        analytics_service = AnalyticsService(db)
        activity_logs = analytics_service.get_bot_activity_logs(
            bot_id=bot_id,
            user_id=str(current_user.id),
            limit=limit,
            action_filter=action
        )
        return {"activity_logs": activity_logs}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity logs: {str(e)}")


@router.get("/system/analytics", response_model=SystemAnalytics)
async def get_system_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get system-wide analytics (admin functionality).
    
    Returns:
    - Platform-wide usage statistics
    - Most active bots and users
    - Growth metrics
    - Daily activity patterns
    
    Note: In production, this should be restricted to admin users only.
    """
    try:
        analytics_service = AnalyticsService(db)
        analytics = analytics_service.get_system_analytics(
            user_id=str(current_user.id),
            days=days
        )
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system analytics: {str(e)}")


@router.get("/bots/{bot_id}/export", response_model=BotExportData)
async def export_bot_data(
    bot_id: str,
    format_type: str = Query("json", pattern="^(json|csv)$", description="Export format"),
    include_messages: bool = Query(True, description="Include conversation messages"),
    include_documents: bool = Query(True, description="Include document metadata"),
    include_activity: bool = Query(True, description="Include activity logs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export bot data for analytics and reporting.
    
    Supports multiple formats and allows selective data inclusion.
    Useful for backup, analysis, and compliance reporting.
    """
    try:
        analytics_service = AnalyticsService(db)
        export_data = analytics_service.export_bot_data(
            bot_id=bot_id,
            user_id=str(current_user.id),
            format_type=format_type,
            include_messages=include_messages,
            include_documents=include_documents,
            include_activity=include_activity
        )
        return export_data
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export bot data: {str(e)}")


@router.get("/users/{user_id}/analytics", response_model=UserDashboardAnalytics)
async def get_user_analytics(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics for a specific user (admin functionality).
    
    Returns user activity across all their accessible bots.
    In production, this should be restricted to admin users or the user themselves.
    """
    # For now, allow users to view their own analytics or any user's analytics
    # In production, add proper authorization checks
    if str(current_user.id) != user_id:
        # In production, check if current_user is admin
        pass
    
    try:
        analytics_service = AnalyticsService(db)
        analytics = analytics_service.get_user_dashboard_analytics(
            user_id=user_id,
            days=days
        )
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user analytics: {str(e)}")


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a quick analytics summary for the current user.
    
    Returns high-level metrics for dashboard widgets and overview displays.
    """
    try:
        analytics_service = AnalyticsService(db)
        
        # Get 7-day and 30-day analytics for comparison
        analytics_7d = analytics_service.get_user_dashboard_analytics(
            user_id=str(current_user.id),
            days=7
        )
        analytics_30d = analytics_service.get_user_dashboard_analytics(
            user_id=str(current_user.id),
            days=30
        )
        
        return {
            "summary": {
                "total_bots": analytics_30d["metrics"]["total_bots"],
                "owned_bots": analytics_30d["metrics"]["owned_bots"],
                "messages_this_week": analytics_7d["metrics"]["total_messages"],
                "messages_this_month": analytics_30d["metrics"]["total_messages"],
                "conversations_this_week": analytics_7d["metrics"]["total_conversations"],
                "conversations_this_month": analytics_30d["metrics"]["total_conversations"]
            },
            "recent_activity": analytics_30d["recent_conversations"][:5]  # Last 5 conversations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics summary: {str(e)}")