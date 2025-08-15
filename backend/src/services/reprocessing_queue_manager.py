"""
Reprocessing Queue Manager - Manages multiple concurrent reprocessing operations.

This service provides:
- Queue management for multiple concurrent reprocessing operations
- Priority-based scheduling
- Resource allocation and throttling
- Progress tracking and status reporting
- Operation cancellation and cleanup
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import UUID
import uuid
from collections import deque

from sqlalchemy.orm import Session

from .document_reprocessing_service import (
    DocumentReprocessingService, 
    ReprocessingStatus, 
    ReprocessingProgress,
    ReprocessingReport
)


logger = logging.getLogger(__name__)


class OperationPriority(Enum):
    """Priority levels for reprocessing operations."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class QueueStatus(Enum):
    """Status of the reprocessing queue."""
    IDLE = "idle"
    PROCESSING = "processing"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class QueuedOperation:
    """Represents a queued reprocessing operation."""
    operation_id: str
    bot_id: UUID
    user_id: UUID
    priority: OperationPriority
    batch_size: int
    force_recreate_collection: bool
    enable_rollback: bool
    queued_at: float
    started_at: Optional[float] = None
    estimated_duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class QueueStatistics:
    """Statistics about the reprocessing queue."""
    total_operations: int
    queued_operations: int
    running_operations: int
    completed_operations: int
    failed_operations: int
    cancelled_operations: int
    average_processing_time: float
    queue_wait_time: float
    resource_utilization: float


class ReprocessingQueueManager:
    """
    Manager for reprocessing operation queues with priority scheduling and resource management.
    
    Features:
    - Priority-based operation scheduling
    - Configurable concurrency limits
    - Resource allocation and throttling
    - Progress tracking and status reporting
    - Operation cancellation and cleanup
    - Queue persistence and recovery
    """
    
    def __init__(
        self,
        db: Session,
        reprocessing_service: Optional[DocumentReprocessingService] = None,
        max_concurrent_operations: int = 3,
        max_queue_size: int = 100
    ):
        """
        Initialize reprocessing queue manager.
        
        Args:
            db: Database session
            reprocessing_service: Document reprocessing service instance
            max_concurrent_operations: Maximum concurrent operations
            max_queue_size: Maximum queue size
        """
        self.db = db
        self.reprocessing_service = reprocessing_service or DocumentReprocessingService(db)
        
        # Configuration
        self.max_concurrent_operations = max_concurrent_operations
        self.max_queue_size = max_queue_size
        self.default_priority = OperationPriority.NORMAL
        self.queue_check_interval = 1.0  # seconds
        self.operation_timeout = 3600.0  # 1 hour
        
        # Queue management
        self.operation_queues: Dict[OperationPriority, deque] = {
            priority: deque() for priority in OperationPriority
        }
        self.running_operations: Dict[str, asyncio.Task] = {}
        self.completed_operations: Dict[str, ReprocessingReport] = {}
        self.operation_metadata: Dict[str, QueuedOperation] = {}
        
        # Queue status and statistics
        self.queue_status = QueueStatus.IDLE
        self.statistics = QueueStatistics(
            total_operations=0,
            queued_operations=0,
            running_operations=0,
            completed_operations=0,
            failed_operations=0,
            cancelled_operations=0,
            average_processing_time=0.0,
            queue_wait_time=0.0,
            resource_utilization=0.0
        )
        
        # Resource management
        self.operation_semaphore = asyncio.Semaphore(max_concurrent_operations)
        self.resource_monitor_task: Optional[asyncio.Task] = None
        self.queue_processor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.processing_times: List[float] = []
        self.wait_times: List[float] = []
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for queue processing and monitoring."""
        try:
            # Start queue processor
            self.queue_processor_task = asyncio.create_task(self._process_queue())
            
            # Start resource monitor
            self.resource_monitor_task = asyncio.create_task(self._monitor_resources())
            
            logger.info("Reprocessing queue manager background tasks started")
            
        except Exception as e:
            logger.error(f"Error starting background tasks: {e}")
    
    async def queue_reprocessing_operation(
        self,
        bot_id: UUID,
        user_id: UUID,
        batch_size: Optional[int] = None,
        force_recreate_collection: bool = False,
        enable_rollback: bool = True,
        priority: Optional[OperationPriority] = None,
        operation_id: Optional[str] = None
    ) -> str:
        """
        Queue a reprocessing operation with priority scheduling.
        
        Args:
            bot_id: Bot identifier
            user_id: User identifier
            batch_size: Batch size for processing
            force_recreate_collection: Whether to recreate vector collection
            enable_rollback: Whether to enable rollback on failure
            priority: Operation priority
            operation_id: Optional operation identifier
            
        Returns:
            Operation ID for tracking
            
        Raises:
            ValueError: If queue is full or invalid parameters
        """
        try:
            # Check queue capacity
            total_queued = sum(len(queue) for queue in self.operation_queues.values())
            if total_queued >= self.max_queue_size:
                raise ValueError("Reprocessing queue is full")
            
            # Generate operation ID if not provided
            if not operation_id:
                operation_id = f"reprocess_{bot_id}_{int(time.time())}"
            
            # Check if operation already exists
            if operation_id in self.operation_metadata:
                raise ValueError(f"Operation {operation_id} already exists")
            
            # Set default values
            priority = priority or self.default_priority
            batch_size = batch_size or 10
            
            # Estimate operation duration based on historical data
            estimated_duration = self._estimate_operation_duration(bot_id, batch_size)
            
            # Create queued operation
            queued_operation = QueuedOperation(
                operation_id=operation_id,
                bot_id=bot_id,
                user_id=user_id,
                priority=priority,
                batch_size=batch_size,
                force_recreate_collection=force_recreate_collection,
                enable_rollback=enable_rollback,
                queued_at=time.time(),
                estimated_duration=estimated_duration,
                metadata={
                    "queue_position": total_queued + 1,
                    "estimated_wait_time": self._estimate_wait_time(priority)
                }
            )
            
            # Add to appropriate priority queue
            self.operation_queues[priority].append(queued_operation)
            self.operation_metadata[operation_id] = queued_operation
            
            # Update statistics
            self.statistics.total_operations += 1
            self.statistics.queued_operations += 1
            
            logger.info(f"Queued reprocessing operation {operation_id} for bot {bot_id} "
                       f"with priority {priority.name}")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Error queuing reprocessing operation: {e}")
            raise
    
    async def _process_queue(self):
        """Background task to process the operation queue."""
        logger.info("Queue processor started")
        
        while True:
            try:
                # Check if we can start new operations
                if (len(self.running_operations) < self.max_concurrent_operations and
                    self.queue_status in [QueueStatus.IDLE, QueueStatus.PROCESSING]):
                    
                    # Get next operation from highest priority queue
                    next_operation = self._get_next_operation()
                    
                    if next_operation:
                        # Start the operation
                        await self._start_operation(next_operation)
                    else:
                        # No operations in queue
                        if len(self.running_operations) == 0:
                            self.queue_status = QueueStatus.IDLE
                        
                        # Wait before checking again
                        await asyncio.sleep(self.queue_check_interval)
                else:
                    # Wait for running operations to complete
                    await asyncio.sleep(self.queue_check_interval)
                
                # Clean up completed operations
                await self._cleanup_completed_operations()
                
                # Update statistics
                self._update_statistics()
                
            except asyncio.CancelledError:
                logger.info("Queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(self.queue_check_interval)
    
    def _get_next_operation(self) -> Optional[QueuedOperation]:
        """Get the next operation from the highest priority queue."""
        # Check queues in priority order (highest first)
        for priority in sorted(OperationPriority, key=lambda p: p.value, reverse=True):
            queue = self.operation_queues[priority]
            if queue:
                return queue.popleft()
        
        return None
    
    async def _start_operation(self, operation: QueuedOperation):
        """Start a reprocessing operation."""
        try:
            operation.started_at = time.time()
            
            # Calculate wait time
            wait_time = operation.started_at - operation.queued_at
            self.wait_times.append(wait_time)
            
            # Update statistics
            self.statistics.queued_operations -= 1
            self.statistics.running_operations += 1
            self.queue_status = QueueStatus.PROCESSING
            
            logger.info(f"Starting reprocessing operation {operation.operation_id} "
                       f"(waited {wait_time:.1f}s)")
            
            # Create and start the operation task
            task = asyncio.create_task(
                self._execute_operation_with_timeout(operation)
            )
            
            self.running_operations[operation.operation_id] = task
            
        except Exception as e:
            logger.error(f"Error starting operation {operation.operation_id}: {e}")
            
            # Move operation back to queue or mark as failed
            await self._handle_operation_start_failure(operation, str(e))
    
    async def _execute_operation_with_timeout(self, operation: QueuedOperation) -> ReprocessingReport:
        """Execute operation with timeout handling."""
        try:
            # Execute the actual reprocessing operation
            report = await asyncio.wait_for(
                self.reprocessing_service._execute_reprocessing_operation(
                    operation_id=operation.operation_id,
                    bot_id=operation.bot_id,
                    user_id=operation.user_id,
                    batch_size=operation.batch_size,
                    force_recreate_collection=operation.force_recreate_collection,
                    enable_rollback=operation.enable_rollback
                ),
                timeout=self.operation_timeout
            )
            
            # Track processing time
            if operation.started_at:
                processing_time = time.time() - operation.started_at
                self.processing_times.append(processing_time)
            
            return report
            
        except asyncio.TimeoutError:
            logger.error(f"Operation {operation.operation_id} timed out after {self.operation_timeout}s")
            
            # Create timeout report
            return ReprocessingReport(
                operation_id=operation.operation_id,
                bot_id=operation.bot_id,
                status=ReprocessingStatus.FAILED,
                total_documents=0,
                successful_documents=0,
                failed_documents=0,
                total_chunks_processed=0,
                total_chunks_stored=0,
                processing_time=self.operation_timeout,
                start_time=operation.started_at or time.time(),
                end_time=time.time(),
                errors=[{"error": "Operation timed out", "context": "timeout"}],
                document_results=[],
                integrity_verified=False,
                rollback_performed=False,
                metadata={"timeout": True}
            )
            
        except Exception as e:
            logger.error(f"Error executing operation {operation.operation_id}: {e}")
            
            # Create error report
            return ReprocessingReport(
                operation_id=operation.operation_id,
                bot_id=operation.bot_id,
                status=ReprocessingStatus.FAILED,
                total_documents=0,
                successful_documents=0,
                failed_documents=0,
                total_chunks_processed=0,
                total_chunks_stored=0,
                processing_time=0.0,
                start_time=operation.started_at or time.time(),
                end_time=time.time(),
                errors=[{"error": str(e), "context": "execution_error"}],
                document_results=[],
                integrity_verified=False,
                rollback_performed=False,
                metadata={"execution_error": True}
            )
    
    async def _cleanup_completed_operations(self):
        """Clean up completed operations."""
        completed_operation_ids = []
        
        for operation_id, task in self.running_operations.items():
            if task.done():
                completed_operation_ids.append(operation_id)
                
                try:
                    # Get the result
                    report = await task
                    
                    # Store the report
                    self.completed_operations[operation_id] = report
                    
                    # Update statistics based on result
                    if report.status == ReprocessingStatus.COMPLETED:
                        self.statistics.completed_operations += 1
                    elif report.status == ReprocessingStatus.FAILED:
                        self.statistics.failed_operations += 1
                    elif report.status == ReprocessingStatus.CANCELLED:
                        self.statistics.cancelled_operations += 1
                    
                    logger.info(f"Operation {operation_id} completed with status {report.status.value}")
                    
                except Exception as e:
                    logger.error(f"Error getting result for operation {operation_id}: {e}")
                    self.statistics.failed_operations += 1
        
        # Remove completed operations from running list
        for operation_id in completed_operation_ids:
            del self.running_operations[operation_id]
            self.statistics.running_operations -= 1
    
    async def _handle_operation_start_failure(self, operation: QueuedOperation, error: str):
        """Handle failure to start an operation."""
        logger.error(f"Failed to start operation {operation.operation_id}: {error}")
        
        # Create failure report
        failure_report = ReprocessingReport(
            operation_id=operation.operation_id,
            bot_id=operation.bot_id,
            status=ReprocessingStatus.FAILED,
            total_documents=0,
            successful_documents=0,
            failed_documents=0,
            total_chunks_processed=0,
            total_chunks_stored=0,
            processing_time=0.0,
            start_time=time.time(),
            end_time=time.time(),
            errors=[{"error": error, "context": "start_failure"}],
            document_results=[],
            integrity_verified=False,
            rollback_performed=False,
            metadata={"start_failure": True}
        )
        
        self.completed_operations[operation.operation_id] = failure_report
        self.statistics.failed_operations += 1
    
    async def _monitor_resources(self):
        """Background task to monitor resource usage."""
        logger.info("Resource monitor started")
        
        while True:
            try:
                # Calculate resource utilization
                utilization = len(self.running_operations) / self.max_concurrent_operations
                self.statistics.resource_utilization = utilization
                
                # Log resource status periodically
                if len(self.running_operations) > 0:
                    logger.debug(f"Resource utilization: {utilization:.1%} "
                               f"({len(self.running_operations)}/{self.max_concurrent_operations})")
                
                # Check for stuck operations (running too long)
                current_time = time.time()
                for operation_id, task in self.running_operations.items():
                    operation = self.operation_metadata.get(operation_id)
                    if operation and operation.started_at:
                        running_time = current_time - operation.started_at
                        if running_time > self.operation_timeout:
                            logger.warning(f"Operation {operation_id} has been running for {running_time:.1f}s")
                
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("Resource monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(30.0)
    
    def _estimate_operation_duration(self, bot_id: UUID, batch_size: int) -> float:
        """Estimate operation duration based on historical data and bot size."""
        try:
            # Get document count for the bot
            from ..models.document import Document
            document_count = self.db.query(Document).filter(Document.bot_id == bot_id).count()
            
            # Base estimate: 2 seconds per document + overhead
            base_estimate = (document_count * 2.0) + 30.0
            
            # Adjust based on batch size (smaller batches take longer due to overhead)
            batch_factor = max(0.5, min(2.0, batch_size / 10.0))
            base_estimate *= (2.0 - batch_factor)
            
            # Use historical data if available
            if self.processing_times:
                avg_processing_time = sum(self.processing_times[-10:]) / len(self.processing_times[-10:])
                # Blend historical average with base estimate
                estimated_duration = (base_estimate + avg_processing_time) / 2.0
            else:
                estimated_duration = base_estimate
            
            return max(60.0, estimated_duration)  # Minimum 1 minute
            
        except Exception as e:
            logger.warning(f"Error estimating operation duration: {e}")
            return 300.0  # Default 5 minutes
    
    def _estimate_wait_time(self, priority: OperationPriority) -> float:
        """Estimate wait time for an operation based on queue state."""
        try:
            # Count operations ahead in queue with higher or equal priority
            operations_ahead = 0
            
            for p in OperationPriority:
                if p.value >= priority.value:
                    operations_ahead += len(self.operation_queues[p])
            
            # Estimate based on current processing rate
            if self.processing_times:
                avg_processing_time = sum(self.processing_times[-5:]) / len(self.processing_times[-5:])
            else:
                avg_processing_time = 300.0  # Default 5 minutes
            
            # Account for concurrent processing
            concurrent_factor = min(operations_ahead, self.max_concurrent_operations)
            if concurrent_factor > 0:
                estimated_wait = (operations_ahead * avg_processing_time) / concurrent_factor
            else:
                estimated_wait = 0.0
            
            return estimated_wait
            
        except Exception as e:
            logger.warning(f"Error estimating wait time: {e}")
            return 0.0
    
    def _update_statistics(self):
        """Update queue statistics."""
        try:
            # Update queue counts
            self.statistics.queued_operations = sum(
                len(queue) for queue in self.operation_queues.values()
            )
            self.statistics.running_operations = len(self.running_operations)
            
            # Update average processing time
            if self.processing_times:
                self.statistics.average_processing_time = (
                    sum(self.processing_times) / len(self.processing_times)
                )
            
            # Update average wait time
            if self.wait_times:
                self.statistics.queue_wait_time = (
                    sum(self.wait_times) / len(self.wait_times)
                )
            
        except Exception as e:
            logger.warning(f"Error updating statistics: {e}")
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status of a specific operation."""
        try:
            # Check if operation is queued
            operation = self.operation_metadata.get(operation_id)
            if not operation:
                return None
            
            # Check if operation is running
            if operation_id in self.running_operations:
                task = self.running_operations[operation_id]
                
                # Get detailed progress from reprocessing service
                detailed_status = self.reprocessing_service.get_detailed_operation_status(operation_id)
                
                return {
                    "operation_id": operation_id,
                    "queue_status": "running",
                    "started_at": operation.started_at,
                    "estimated_duration": operation.estimated_duration,
                    "queue_metadata": operation.metadata,
                    "detailed_status": detailed_status,
                    "task_done": task.done(),
                    "task_cancelled": task.cancelled()
                }
            
            # Check if operation is completed
            if operation_id in self.completed_operations:
                report = self.completed_operations[operation_id]
                
                # Get integrity status if available
                integrity_status = None
                try:
                    integrity_status = asyncio.create_task(
                        self.reprocessing_service.get_operation_integrity_status(
                            operation_id, operation.bot_id
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to get integrity status: {e}")
                
                return {
                    "operation_id": operation_id,
                    "queue_status": "completed",
                    "report": asdict(report),
                    "queue_metadata": operation.metadata,
                    "integrity_status": integrity_status,
                    "completion_time": report.end_time,
                    "total_duration": report.processing_time
                }
            
            # Operation is still queued
            queue_position = self._get_queue_position(operation_id)
            estimated_wait = self._estimate_wait_time(operation.priority)
            
            return {
                "operation_id": operation_id,
                "queue_status": "queued",
                "priority": operation.priority.name,
                "queue_position": queue_position,
                "estimated_wait_time": estimated_wait,
                "queued_at": operation.queued_at,
                "queue_metadata": operation.metadata,
                "can_cancel": True
            }
            
        except Exception as e:
            logger.error(f"Error getting operation status for {operation_id}: {e}")
            return {"operation_id": operation_id, "queue_status": "error", "error": str(e)}
    
    def _get_queue_position(self, operation_id: str) -> int:
        """Get the position of an operation in the queue."""
        position = 1
        
        # Check all priority queues in order
        for priority in sorted(OperationPriority, key=lambda p: p.value, reverse=True):
            queue = self.operation_queues[priority]
            
            for i, op in enumerate(queue):
                if op.operation_id == operation_id:
                    return position + i
            
            position += len(queue)
        
        return -1  # Not found
    
    async def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a queued or running operation."""
        try:
            # Check if operation is running
            if operation_id in self.running_operations:
                task = self.running_operations[operation_id]
                task.cancel()
                
                # Try to cancel through reprocessing service
                cancelled = await self.reprocessing_service.cancel_operation(operation_id)
                
                logger.info(f"Cancelled running operation {operation_id}")
                return cancelled
            
            # Check if operation is queued
            for priority, queue in self.operation_queues.items():
                for i, operation in enumerate(queue):
                    if operation.operation_id == operation_id:
                        # Remove from queue
                        del queue[i]
                        
                        # Update statistics
                        self.statistics.queued_operations -= 1
                        self.statistics.cancelled_operations += 1
                        
                        logger.info(f"Cancelled queued operation {operation_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling operation {operation_id}: {e}")
            return False
    
    def get_queue_statistics(self) -> QueueStatistics:
        """Get current queue statistics."""
        self._update_statistics()
        return self.statistics
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get detailed queue status."""
        try:
            queue_details = {}
            
            for priority in OperationPriority:
                queue = self.operation_queues[priority]
                queue_details[priority.name] = {
                    "count": len(queue),
                    "operations": [
                        {
                            "operation_id": op.operation_id,
                            "bot_id": str(op.bot_id),
                            "queued_at": op.queued_at,
                            "estimated_duration": op.estimated_duration
                        }
                        for op in list(queue)[:5]  # Show first 5 operations
                    ]
                }
            
            running_details = {}
            for operation_id, task in self.running_operations.items():
                operation = self.operation_metadata.get(operation_id)
                if operation:
                    running_details[operation_id] = {
                        "bot_id": str(operation.bot_id),
                        "started_at": operation.started_at,
                        "estimated_duration": operation.estimated_duration,
                        "running_time": time.time() - (operation.started_at or time.time())
                    }
            
            return {
                "queue_status": self.queue_status.value,
                "statistics": asdict(self.statistics),
                "queue_details": queue_details,
                "running_operations": running_details,
                "max_concurrent_operations": self.max_concurrent_operations,
                "max_queue_size": self.max_queue_size
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {"error": str(e)}
    
    async def pause_queue(self):
        """Pause the processing queue."""
        self.queue_status = QueueStatus.PAUSED
        logger.info("Reprocessing queue paused")
    
    async def get_operation_integrity_results(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get integrity verification results for a completed operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Integrity verification results or None if not available
        """
        try:
            operation = self.operation_metadata.get(operation_id)
            if not operation:
                return None
            
            # Check if operation is completed
            if operation_id not in self.completed_operations:
                return {"status": "not_completed", "message": "Operation has not completed yet"}
            
            # Get integrity status from reprocessing service
            integrity_status = await self.reprocessing_service.get_operation_integrity_status(
                operation_id, operation.bot_id
            )
            
            return integrity_status
            
        except Exception as e:
            logger.error(f"Error getting integrity results for operation {operation_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def trigger_rollback(self, operation_id: str) -> Dict[str, Any]:
        """
        Trigger rollback for a completed operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Rollback result
        """
        try:
            operation = self.operation_metadata.get(operation_id)
            if not operation:
                return {"success": False, "error": "Operation not found"}
            
            # Check if operation is completed
            if operation_id not in self.completed_operations:
                return {"success": False, "error": "Can only rollback completed operations"}
            
            # Check if rollback is possible (backup exists)
            backup_file = Path(f"/tmp/backup_{operation_id}.json")
            if not backup_file.exists():
                return {"success": False, "error": "No backup available for rollback"}
            
            logger.info(f"Triggering rollback for operation {operation_id}")
            
            # Perform rollback using reprocessing service
            rollback_result = await self.reprocessing_service._perform_rollback(
                operation_id, operation.bot_id
            )
            
            if rollback_result["success"]:
                logger.info(f"Rollback completed successfully for operation {operation_id}")
                
                # Update operation metadata to indicate rollback
                operation.metadata = operation.metadata or {}
                operation.metadata["rollback_performed"] = True
                operation.metadata["rollback_time"] = time.time()
                operation.metadata["rollback_type"] = rollback_result.get("rollback_type", "unknown")
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "rollback_type": rollback_result.get("rollback_type"),
                    "rollback_details": rollback_result
                }
            else:
                logger.error(f"Rollback failed for operation {operation_id}: {rollback_result.get('error')}")
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": rollback_result.get("error"),
                    "rollback_details": rollback_result
                }
            
        except Exception as e:
            logger.error(f"Error triggering rollback for operation {operation_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_rollback_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Get rollback status and capabilities for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Rollback status information
        """
        try:
            operation = self.operation_metadata.get(operation_id)
            if not operation:
                return {"status": "operation_not_found"}
            
            # Check if backup exists
            backup_file = Path(f"/tmp/backup_{operation_id}.json")
            backup_exists = backup_file.exists()
            
            backup_info = {}
            if backup_exists:
                try:
                    with open(backup_file, 'r') as f:
                        backup_metadata = json.load(f)
                    backup_info = {
                        "backup_type": backup_metadata.get("backup_type", "unknown"),
                        "backup_time": backup_metadata.get("backup_time"),
                        "document_count": backup_metadata.get("document_count", 0),
                        "chunk_count": backup_metadata.get("chunk_count", 0),
                        "vector_count": backup_metadata.get("vector_count", 0)
                    }
                except Exception as e:
                    backup_info = {"error": f"Failed to read backup metadata: {str(e)}"}
            
            # Check if rollback was already performed
            rollback_performed = operation.metadata and operation.metadata.get("rollback_performed", False)
            
            return {
                "operation_id": operation_id,
                "can_rollback": backup_exists and not rollback_performed,
                "backup_exists": backup_exists,
                "backup_info": backup_info,
                "rollback_performed": rollback_performed,
                "rollback_time": operation.metadata.get("rollback_time") if operation.metadata else None,
                "rollback_type": operation.metadata.get("rollback_type") if operation.metadata else None,
                "operation_status": "completed" if operation_id in self.completed_operations else "not_completed"
            }
            
        except Exception as e:
            logger.error(f"Error getting rollback status for operation {operation_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def resume_queue(self):
        """Resume the processing queue."""
        if self.queue_status == QueueStatus.PAUSED:
            self.queue_status = QueueStatus.IDLE
            logger.info("Reprocessing queue resumed")
    
    async def shutdown(self):
        """Shutdown the queue manager gracefully."""
        try:
            logger.info("Shutting down reprocessing queue manager")
            self.queue_status = QueueStatus.SHUTTING_DOWN
            
            # Cancel background tasks
            if self.queue_processor_task:
                self.queue_processor_task.cancel()
            
            if self.resource_monitor_task:
                self.resource_monitor_task.cancel()
            
            # Cancel all running operations
            for operation_id, task in self.running_operations.items():
                task.cancel()
                logger.info(f"Cancelled operation {operation_id} during shutdown")
            
            # Wait for tasks to complete
            if self.queue_processor_task:
                try:
                    await self.queue_processor_task
                except asyncio.CancelledError:
                    pass
            
            if self.resource_monitor_task:
                try:
                    await self.resource_monitor_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Reprocessing queue manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during queue manager shutdown: {e}")