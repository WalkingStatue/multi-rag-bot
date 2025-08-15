"""
API endpoints for cache management operations.
"""
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field

from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.cache_management_service import get_cache_management_service, CacheManagementService
from ..services.enhanced_embedding_service import get_enhanced_embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache-management"])


class CacheInvalidationRequest(BaseModel):
    """Request model for cache invalidation."""
    provider: Optional[str] = Field(None, description="Provider to invalidate (optional)")
    model: Optional[str] = Field(None, description="Model to invalidate (optional)")
    reason: str = Field(..., description="Reason for invalidation")


class CacheWarmingRequest(BaseModel):
    """Request model for cache warming."""
    texts: List[str] = Field(..., description="Texts to warm in cache")
    provider: str = Field(..., description="Embedding provider")
    model: str = Field(..., description="Embedding model")
    priority: int = Field(5, ge=1, le=10, description="Priority level (1-10)")


class CacheWarmingResponse(BaseModel):
    """Response model for cache warming."""
    task_id: str = Field(..., description="Task ID for tracking")
    message: str = Field(..., description="Success message")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    cache_performance: Dict[str, Any]
    hit_rate_analysis: Dict[str, Any]
    provider_breakdown: Dict[str, Any]
    warming_statistics: Dict[str, Any]
    maintenance: Dict[str, Any]


class MaintenanceResponse(BaseModel):
    """Response model for maintenance operations."""
    timestamp: float
    expired_entries_cleaned: int
    invalid_entries_cleaned: int
    memory_freed_mb: float
    maintenance_duration_seconds: float
    errors: List[str]


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive cache statistics and analytics.
    
    Returns cache performance metrics, hit rate analysis, provider breakdown,
    and warming task statistics.
    """
    try:
        cache_mgmt = await get_cache_management_service()
        stats = await cache_mgmt.get_cache_statistics()
        
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.post("/invalidate")
async def invalidate_cache(
    request: CacheInvalidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Invalidate cache entries based on provider/model filters.
    
    Can invalidate all cache entries or filter by specific provider and/or model.
    """
    try:
        enhanced_service = await get_enhanced_embedding_service()
        
        # Clear cache with optional filters
        await enhanced_service.clear_cache(request.provider, request.model)
        
        # Log the invalidation
        cache_mgmt = await get_cache_management_service()
        await cache_mgmt._log_cache_invalidation(
            "manual_invalidation",
            {
                "provider": request.provider,
                "model": request.model,
                "reason": request.reason,
                "user_id": str(current_user.id)
            }
        )
        
        filter_desc = ""
        if request.provider:
            filter_desc += f" for provider '{request.provider}'"
        if request.model:
            filter_desc += f" for model '{request.model}'"
        
        return {
            "message": f"Cache invalidated{filter_desc}",
            "reason": request.reason
        }
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post("/warm", response_model=CacheWarmingResponse)
async def schedule_cache_warming(
    request: CacheWarmingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Schedule cache warming for frequently accessed content.
    
    Queues texts for embedding generation and caching to improve future performance.
    """
    try:
        if not request.texts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No texts provided for warming"
            )
        
        if len(request.texts) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many texts for warming (maximum 1000)"
            )
        
        # Validate provider and model
        enhanced_service = await get_enhanced_embedding_service()
        if not enhanced_service.validate_model_for_provider(request.provider, request.model):
            available_models = enhanced_service.get_available_models(request.provider)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{request.model}' not available for provider '{request.provider}'. "
                       f"Available models: {', '.join(available_models)}"
            )
        
        # Schedule warming
        cache_mgmt = await get_cache_management_service()
        task_id = await cache_mgmt.schedule_cache_warming(
            texts=request.texts,
            provider=request.provider,
            model=request.model,
            priority=request.priority
        )
        
        return CacheWarmingResponse(
            task_id=task_id,
            message=f"Cache warming scheduled for {len(request.texts)} texts"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling cache warming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule cache warming: {str(e)}"
        )


@router.get("/warming/{task_id}")
async def get_warming_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a cache warming task.
    
    Returns task progress, status, and any error messages.
    """
    try:
        cache_mgmt = await get_cache_management_service()
        task = await cache_mgmt.get_warming_task_status(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warming task '{task_id}' not found"
            )
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "texts_count": len(task.texts),
            "provider": task.provider,
            "model": task.model,
            "priority": task.priority,
            "created_at": task.created_at,
            "error_message": task.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warming task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get warming task status: {str(e)}"
        )


@router.delete("/warming/{task_id}")
async def cancel_warming_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending cache warming task.
    
    Can only cancel tasks that are in 'pending' status.
    """
    try:
        cache_mgmt = await get_cache_management_service()
        cancelled = await cache_mgmt.cancel_warming_task(task_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel warming task '{task_id}'. Task may not exist, be already running, or completed."
            )
        
        return {
            "message": f"Warming task '{task_id}' cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling warming task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel warming task: {str(e)}"
        )


@router.post("/maintenance", response_model=MaintenanceResponse)
async def run_cache_maintenance(
    force: bool = Query(False, description="Force maintenance even if recently run"),
    current_user: User = Depends(get_current_user)
):
    """
    Run cache maintenance operations.
    
    Cleans up expired entries, invalid data, and optimizes cache performance.
    """
    try:
        cache_mgmt = await get_cache_management_service()
        report = await cache_mgmt.run_cache_maintenance(force=force)
        
        return MaintenanceResponse(
            timestamp=report.timestamp,
            expired_entries_cleaned=report.expired_entries_cleaned,
            invalid_entries_cleaned=report.invalid_entries_cleaned,
            memory_freed_mb=report.memory_freed_mb,
            maintenance_duration_seconds=report.maintenance_duration_seconds,
            errors=report.errors
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error running cache maintenance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run cache maintenance: {str(e)}"
        )


@router.get("/performance/history")
async def get_cache_performance_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (1-168)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get cache performance history for analysis.
    
    Returns historical cache performance metrics for the specified time period.
    """
    try:
        from ..services.cache_performance_monitor import get_cache_performance_monitor
        
        monitor = await get_cache_performance_monitor()
        history = await monitor.get_performance_history(hours)
        
        # Convert to serializable format
        history_data = []
        for metrics in history:
            history_data.append({
                "timestamp": metrics.timestamp,
                "total_requests": metrics.total_requests,
                "cache_hits": metrics.cache_hits,
                "cache_misses": metrics.cache_misses,
                "hit_rate": metrics.hit_rate,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "total_entries": metrics.total_entries,
                "memory_usage_mb": metrics.memory_usage_mb,
                "evictions": metrics.evictions,
                "provider_stats": metrics.provider_stats
            })
        
        return {
            "history": history_data,
            "period_hours": hours,
            "total_snapshots": len(history_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting cache performance history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache performance history: {str(e)}"
        )


@router.get("/providers/performance")
async def get_provider_performance_breakdown(
    current_user: User = Depends(get_current_user)
):
    """
    Get cache performance breakdown by provider and model.
    
    Returns detailed performance statistics for each provider/model combination.
    """
    try:
        from ..services.cache_performance_monitor import get_cache_performance_monitor
        
        monitor = await get_cache_performance_monitor()
        breakdown = await monitor.get_provider_performance_breakdown()
        
        return {
            "provider_performance": breakdown,
            "total_providers": len(breakdown)
        }
        
    except Exception as e:
        logger.error(f"Error getting provider performance breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider performance breakdown: {str(e)}"
        )


@router.get("/health")
async def get_cache_health():
    """
    Get cache system health status.
    
    Returns basic health information about the cache system.
    """
    try:
        from ..services.embedding_cache_service import get_embedding_cache_service
        
        cache_service = await get_embedding_cache_service()
        
        # Test Redis connection
        if cache_service.redis_client:
            await cache_service.redis_client.ping()
            redis_status = "healthy"
        else:
            redis_status = "disconnected"
        
        # Get basic stats
        stats = await cache_service.get_cache_stats()
        
        return {
            "status": "healthy" if redis_status == "healthy" else "degraded",
            "redis_connection": redis_status,
            "total_entries": stats.total_entries,
            "memory_usage_mb": stats.memory_usage_mb,
            "hit_rate": stats.hit_rate,
            "last_check": stats.total_requests > 0
        }
        
    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }