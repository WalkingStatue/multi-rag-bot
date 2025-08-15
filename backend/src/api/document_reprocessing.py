"""
Document Reprocessing API endpoints.

This module provides REST API endpoints for:
- Starting document reprocessing operations
- Monitoring reprocessing progress
- Managing reprocessing queue
- Data integrity verification and rollback
"""
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..models.bot import Bot
from ..services.document_reprocessing_service import (
    DocumentReprocessingService,
    ReprocessingStatus,
    ReprocessingProgress,
    ReprocessingReport
)
from ..services.data_integrity_service import (
    DataIntegrityService,
    IntegrityCheckType,
    IntegrityIssueLevel,
    DataSnapshot,
    RollbackResult
)
from ..services.reprocessing_queue_manager import (
    ReprocessingQueueManager,
    OperationPriority,
    QueueStatistics
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reprocessing", tags=["document-reprocessing"])


# Request/Response Models
class StartReprocessingRequest(BaseModel):
    """Request model for starting reprocessing operation."""
    batch_size: Optional[int] = Field(default=10, ge=1, le=100, description="Batch size for processing")
    force_recreate_collection: bool = Field(default=False, description="Whether to recreate vector collection")
    enable_rollback: bool = Field(default=True, description="Whether to enable rollback on failure")
    priority: Optional[str] = Field(default="normal", description="Operation priority (low, normal, high, urgent)")


class ReprocessingStatusResponse(BaseModel):
    """Response model for reprocessing status."""
    operation_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegrityCheckRequest(BaseModel):
    """Request model for integrity check."""
    check_types: Optional[List[str]] = Field(default=None, description="Specific checks to perform")
    detailed: bool = Field(default=True, description="Whether to perform detailed checks")


class CreateSnapshotRequest(BaseModel):
    """Request model for creating data snapshot."""
    snapshot_id: Optional[str] = Field(default=None, description="Optional snapshot identifier")


class RollbackRequest(BaseModel):
    """Request model for rollback operation."""
    snapshot_id: str = Field(description="Snapshot ID to rollback to")
    verify_after_rollback: bool = Field(default=True, description="Whether to verify integrity after rollback")


# Dependency injection
def get_reprocessing_service(db: Session = Depends(get_db)) -> DocumentReprocessingService:
    """Get document reprocessing service instance."""
    return DocumentReprocessingService(db)


def get_integrity_service(db: Session = Depends(get_db)) -> DataIntegrityService:
    """Get data integrity service instance."""
    return DataIntegrityService(db)


def get_queue_manager(db: Session = Depends(get_db)) -> ReprocessingQueueManager:
    """Get reprocessing queue manager instance."""
    return ReprocessingQueueManager(db)


@router.post("/bots/{bot_id}/start", response_model=Dict[str, str])
async def start_reprocessing(
    bot_id: UUID,
    request: StartReprocessingRequest,
    current_user: User = Depends(get_current_user),
    queue_manager: ReprocessingQueueManager = Depends(get_queue_manager)
):
    """
    Start reprocessing all documents for a bot.
    
    This endpoint queues a reprocessing operation that will:
    - Process documents in batches with error isolation
    - Generate new embeddings with current configuration
    - Store chunks in vector store with deduplication
    - Provide detailed progress tracking and completion reports
    """
    try:
        # Validate bot exists and user has permissions
        db = queue_manager.db
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions (user must be owner or admin)
        if bot.owner_id != current_user.id:
            # TODO: Add proper permission checking for admins
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to reprocess documents"
            )
        
        # Parse priority
        priority_map = {
            "low": OperationPriority.LOW,
            "normal": OperationPriority.NORMAL,
            "high": OperationPriority.HIGH,
            "urgent": OperationPriority.URGENT
        }
        
        priority = priority_map.get(request.priority.lower(), OperationPriority.NORMAL)
        
        # Queue the reprocessing operation
        operation_id = await queue_manager.queue_reprocessing_operation(
            bot_id=bot_id,
            user_id=current_user.id,
            batch_size=request.batch_size,
            force_recreate_collection=request.force_recreate_collection,
            enable_rollback=request.enable_rollback,
            priority=priority
        )
        
        logger.info(f"Queued reprocessing operation {operation_id} for bot {bot_id}")
        
        return {
            "operation_id": operation_id,
            "message": "Reprocessing operation queued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting reprocessing for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start reprocessing: {str(e)}"
        )


@router.get("/operations/{operation_id}/status", response_model=ReprocessingStatusResponse)
async def get_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    queue_manager: ReprocessingQueueManager = Depends(get_queue_manager)
):
    """Get the status and progress of a reprocessing operation."""
    try:
        status_info = queue_manager.get_operation_status(operation_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found"
            )
        
        return ReprocessingStatusResponse(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting operation status {operation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get operation status: {str(e)}"
        )


@router.delete("/operations/{operation_id}")
async def cancel_operation(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    queue_manager: ReprocessingQueueManager = Depends(get_queue_manager)
):
    """Cancel a queued or running reprocessing operation."""
    try:
        cancelled = await queue_manager.cancel_operation(operation_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found or cannot be cancelled"
            )
        
        return {"message": "Operation cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling operation {operation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel operation: {str(e)}"
        )


@router.get("/queue/status")
async def get_queue_status(
    current_user: User = Depends(get_current_user),
    queue_manager: ReprocessingQueueManager = Depends(get_queue_manager)
):
    """Get detailed status of the reprocessing queue."""
    try:
        return queue_manager.get_queue_status()
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.get("/queue/statistics", response_model=Dict[str, Any])
async def get_queue_statistics(
    current_user: User = Depends(get_current_user),
    queue_manager: ReprocessingQueueManager = Depends(get_queue_manager)
):
    """Get queue statistics and performance metrics."""
    try:
        statistics = queue_manager.get_queue_statistics()
        return {
            "total_operations": statistics.total_operations,
            "queued_operations": statistics.queued_operations,
            "running_operations": statistics.running_operations,
            "completed_operations": statistics.completed_operations,
            "failed_operations": statistics.failed_operations,
            "cancelled_operations": statistics.cancelled_operations,
            "average_processing_time": statistics.average_processing_time,
            "queue_wait_time": statistics.queue_wait_time,
            "resource_utilization": statistics.resource_utilization
        }
        
    except Exception as e:
        logger.error(f"Error getting queue statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue statistics: {str(e)}"
        )


@router.post("/bots/{bot_id}/integrity/check")
async def check_data_integrity(
    bot_id: UUID,
    request: IntegrityCheckRequest,
    current_user: User = Depends(get_current_user),
    integrity_service: DataIntegrityService = Depends(get_integrity_service)
):
    """Perform comprehensive data integrity verification for a bot."""
    try:
        # Validate bot exists and user has permissions
        db = integrity_service.db
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions
        if bot.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to check data integrity"
            )
        
        # Parse check types
        check_types = None
        if request.check_types:
            try:
                check_types = [IntegrityCheckType(check_type) for check_type in request.check_types]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid check type: {str(e)}"
                )
        
        # Perform integrity checks
        results = await integrity_service.verify_data_integrity(
            bot_id=bot_id,
            check_types=check_types,
            detailed=request.detailed
        )
        
        # Convert results to serializable format
        serialized_results = {}
        for check_type, result in results.items():
            serialized_results[check_type] = {
                "check_type": result.check_type.value,
                "passed": result.passed,
                "check_duration": result.check_duration,
                "issues": [
                    {
                        "check_type": issue.check_type.value,
                        "level": issue.level.value,
                        "description": issue.description,
                        "affected_entities": issue.affected_entities,
                        "suggested_fix": issue.suggested_fix,
                        "metadata": issue.metadata
                    }
                    for issue in result.issues
                ],
                "metadata": result.metadata
            }
        
        return {
            "bot_id": str(bot_id),
            "check_results": serialized_results,
            "summary": {
                "total_checks": len(results),
                "passed_checks": sum(1 for r in results.values() if r.passed),
                "total_issues": sum(len(r.issues) for r in results.values()),
                "critical_issues": sum(
                    len([i for i in r.issues if i.level == IntegrityIssueLevel.CRITICAL])
                    for r in results.values()
                )
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking data integrity for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check data integrity: {str(e)}"
        )


@router.post("/bots/{bot_id}/snapshots/create")
async def create_data_snapshot(
    bot_id: UUID,
    request: CreateSnapshotRequest,
    current_user: User = Depends(get_current_user),
    integrity_service: DataIntegrityService = Depends(get_integrity_service)
):
    """Create a data snapshot for rollback purposes."""
    try:
        # Validate bot exists and user has permissions
        db = integrity_service.db
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions
        if bot.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create data snapshot"
            )
        
        # Create snapshot
        snapshot = await integrity_service.create_data_snapshot(
            bot_id=bot_id,
            snapshot_id=request.snapshot_id
        )
        
        return {
            "snapshot_id": snapshot.snapshot_id,
            "bot_id": str(snapshot.bot_id),
            "created_at": snapshot.created_at,
            "document_count": snapshot.document_count,
            "chunk_count": snapshot.chunk_count,
            "vector_count": snapshot.vector_count,
            "collection_config": snapshot.collection_config,
            "metadata": snapshot.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data snapshot for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create data snapshot: {str(e)}"
        )


@router.get("/bots/{bot_id}/snapshots")
async def list_data_snapshots(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    integrity_service: DataIntegrityService = Depends(get_integrity_service)
):
    """List available data snapshots for a bot."""
    try:
        # Validate bot exists and user has permissions
        db = integrity_service.db
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions
        if bot.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to list data snapshots"
            )
        
        # Get snapshots
        snapshots = integrity_service.list_snapshots(bot_id=bot_id)
        
        return {
            "bot_id": str(bot_id),
            "snapshots": [
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "created_at": snapshot.created_at,
                    "document_count": snapshot.document_count,
                    "chunk_count": snapshot.chunk_count,
                    "vector_count": snapshot.vector_count,
                    "metadata": snapshot.metadata
                }
                for snapshot in snapshots
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing data snapshots for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list data snapshots: {str(e)}"
        )


@router.post("/bots/{bot_id}/rollback")
async def rollback_to_snapshot(
    bot_id: UUID,
    request: RollbackRequest,
    current_user: User = Depends(get_current_user),
    integrity_service: DataIntegrityService = Depends(get_integrity_service)
):
    """Rollback bot data to a previous snapshot."""
    try:
        # Validate bot exists and user has permissions
        db = integrity_service.db
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions (only owner can perform rollback)
        if bot.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to perform rollback"
            )
        
        # Execute rollback
        rollback_result = await integrity_service.execute_rollback(
            snapshot_id=request.snapshot_id,
            bot_id=bot_id,
            verify_after_rollback=request.verify_after_rollback
        )
        
        return {
            "success": rollback_result.success,
            "snapshot_id": rollback_result.snapshot_id,
            "bot_id": str(rollback_result.bot_id),
            "steps_completed": rollback_result.steps_completed,
            "total_steps": rollback_result.total_steps,
            "duration": rollback_result.duration,
            "error": rollback_result.error,
            "metadata": rollback_result.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing rollback for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform rollback: {str(e)}"
        )


@router.get("/bots/{bot_id}/integrity/summary")
async def get_integrity_summary(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    integrity_service: DataIntegrityService = Depends(get_integrity_service)
):
    """Get a quick integrity summary for a bot."""
    try:
        # Validate bot exists and user has permissions
        db = integrity_service.db
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions
        if bot.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view integrity summary"
            )
        
        # Get integrity summary
        summary = integrity_service.get_integrity_summary(bot_id)
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integrity summary for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integrity summary: {str(e)}"
        )