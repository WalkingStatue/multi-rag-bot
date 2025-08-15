"""
Vector store abstraction and Qdrant implementation for embedding storage and retrieval.
Enhanced with truly asynchronous operations, connection pooling, and resource management.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import uuid
from contextlib import asynccontextmanager
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from enum import Enum

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException
from fastapi import HTTPException, status

from ..core.config import settings


logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Enumeration of operation statuses."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationState:
    """Atomic operation state with thread-safe updates."""
    id: str
    status: OperationStatus = OperationStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    failed_at: Optional[float] = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'failed_at': self.failed_at,
            'error': self.error,
            'progress': self.progress,
            'metadata': self.metadata,
            'duration': self._calculate_duration()
        }
    
    def _calculate_duration(self) -> Optional[float]:
        """Calculate operation duration."""
        if self.started_at is None:
            return None
        
        end_time = (
            self.completed_at or 
            self.failed_at or 
            time.time()
        )
        return end_time - self.started_at


class AtomicStatusManager:
    """Thread-safe status manager for vector operations."""
    
    def __init__(self):
        """Initialize status manager."""
        self._operations: Dict[str, OperationState] = {}
        self._lock = asyncio.Lock()
    
    async def create_operation(self, operation_id: str, metadata: Dict[str, Any] = None) -> OperationState:
        """Create a new operation with atomic status."""
        async with self._lock:
            operation = OperationState(
                id=operation_id,
                metadata=metadata or {}
            )
            self._operations[operation_id] = operation
            return operation
    
    async def update_status(
        self, 
        operation_id: str, 
        status: OperationStatus, 
        error: str = None,
        progress: float = None
    ) -> bool:
        """Atomically update operation status."""
        async with self._lock:
            if operation_id not in self._operations:
                return False
            
            operation = self._operations[operation_id]
            operation.status = status
            
            current_time = time.time()
            
            if status == OperationStatus.RUNNING and operation.started_at is None:
                operation.started_at = current_time
            elif status == OperationStatus.COMPLETED:
                operation.completed_at = current_time
            elif status == OperationStatus.FAILED:
                operation.failed_at = current_time
                operation.error = error
            
            if progress is not None:
                operation.progress = progress
            
            return True
    
    async def get_operation(self, operation_id: str) -> Optional[OperationState]:
        """Get operation state."""
        async with self._lock:
            return self._operations.get(operation_id)
    
    async def remove_operation(self, operation_id: str) -> bool:
        """Remove operation from tracking."""
        async with self._lock:
            if operation_id in self._operations:
                del self._operations[operation_id]
                return True
            return False
    
    async def get_all_operations(self) -> Dict[str, OperationState]:
        """Get all operations (copy)."""
        async with self._lock:
            return self._operations.copy()
    
    async def cleanup_completed_operations(self, max_age_seconds: int = 300):
        """Clean up old completed operations."""
        current_time = time.time()
        to_remove = []
        
        async with self._lock:
            for op_id, operation in self._operations.items():
                if operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
                    end_time = operation.completed_at or operation.failed_at
                    if end_time and (current_time - end_time) > max_age_seconds:
                        to_remove.append(op_id)
            
            for op_id in to_remove:
                del self._operations[op_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} completed operations")


class VectorOperationQueue:
    """Queue manager for vector operations with backpressure and concurrency control."""
    
    def __init__(self, max_concurrent_operations: int = 5, max_queue_size: int = 100):
        """
        Initialize operation queue with atomic status management.
        
        Args:
            max_concurrent_operations: Maximum number of concurrent operations
            max_queue_size: Maximum number of queued operations
        """
        self.max_concurrent_operations = max_concurrent_operations
        self.max_queue_size = max_queue_size
        self._semaphore = asyncio.Semaphore(max_concurrent_operations)
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self._status_manager = AtomicStatusManager()
        self._operation_counter = 0
        self._lock = asyncio.Lock()
        self._shutdown = False
        
        # Defer starting cleanup task until an event loop is available
        self._cleanup_task = None

    async def start_cleanup(self) -> None:
        """Start periodic cleanup when an event loop is running."""
        if self._cleanup_task is None:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
    
    async def enqueue_operation(
        self, 
        operation_id: str, 
        operation_func: callable, 
        *args, 
        **kwargs
    ) -> str:
        """
        Enqueue an operation for execution with atomic status tracking.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_func: The async function to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Operation ID for tracking
            
        Raises:
            HTTPException: If queue is full (backpressure)
        """
        if self._shutdown:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector operation queue is shutting down"
            )
        
        try:
            # Create atomic operation state
            await self._status_manager.create_operation(
                operation_id, 
                metadata={'function': operation_func.__name__ if hasattr(operation_func, '__name__') else 'unknown'}
            )
            
            operation_data = {
                'id': operation_id,
                'func': operation_func,
                'args': args,
                'kwargs': kwargs
            }
            
            # Try to add to queue (non-blocking)
            self._queue.put_nowait(operation_data)
            
            logger.info(f"Enqueued operation {operation_id}, queue size: {self._queue.qsize()}")
            return operation_id
            
        except asyncio.QueueFull:
            # Remove from status manager if queue is full
            await self._status_manager.remove_operation(operation_id)
            logger.warning(f"Operation queue full, rejecting operation {operation_id}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Vector operation queue is full ({self.max_queue_size} operations). Please try again later."
            )
    
    async def execute_operation(self, operation_data: Dict[str, Any]) -> Any:
        """
        Execute a single operation with semaphore control and atomic status updates.
        
        Args:
            operation_data: Operation data dictionary
            
        Returns:
            Operation result
        """
        operation_id = operation_data['id']
        
        async with self._semaphore:
            try:
                # Atomically update status to running
                await self._status_manager.update_status(operation_id, OperationStatus.RUNNING)
                logger.info(f"Executing operation {operation_id}")
                
                # Execute the operation
                result = await operation_data['func'](*operation_data['args'], **operation_data['kwargs'])
                
                # Atomically update status to completed
                await self._status_manager.update_status(operation_id, OperationStatus.COMPLETED, progress=1.0)
                logger.info(f"Completed operation {operation_id}")
                return result
                
            except asyncio.CancelledError:
                # Handle cancellation
                await self._status_manager.update_status(operation_id, OperationStatus.CANCELLED)
                logger.info(f"Operation {operation_id} was cancelled")
                raise
                
            except Exception as e:
                # Atomically update status to failed
                await self._status_manager.update_status(
                    operation_id, OperationStatus.FAILED, error=str(e)
                )
                logger.error(f"Operation {operation_id} failed: {e}")
                raise
    
    async def _periodic_cleanup(self):
        """Periodically clean up completed operations."""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # Clean up every minute
                await self._status_manager.cleanup_completed_operations(max_age_seconds=300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def process_queue(self):
        """Process operations from the queue continuously."""
        while not self._shutdown:
            try:
                # Get operation from queue with timeout
                operation_data = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                
                # Execute operation in background
                asyncio.create_task(self.execute_operation(operation_data))
                
            except asyncio.TimeoutError:
                # No operations in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                await asyncio.sleep(1)
    
    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific operation with atomic access."""
        operation = await self._status_manager.get_operation(operation_id)
        return operation.to_dict() if operation else None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        all_operations = await self._status_manager.get_all_operations()
        
        status_counts = {}
        for status in OperationStatus:
            status_counts[status.value] = 0
        
        for operation in all_operations.values():
            status_counts[operation.status.value] += 1
        
        return {
            'active_operations': status_counts[OperationStatus.RUNNING.value],
            'queued_operations': self._queue.qsize(),
            'completed_operations': status_counts[OperationStatus.COMPLETED.value],
            'failed_operations': status_counts[OperationStatus.FAILED.value],
            'cancelled_operations': status_counts[OperationStatus.CANCELLED.value],
            'total_operations': len(all_operations),
            'max_concurrent': self.max_concurrent_operations,
            'max_queue_size': self.max_queue_size,
            'available_slots': self.max_concurrent_operations - status_counts[OperationStatus.RUNNING.value],
            'status_breakdown': status_counts
        }
    
    async def shutdown(self):
        """Shutdown the queue and wait for active operations to complete."""
        self._shutdown = True
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active operations to complete
        max_wait_time = 30  # Maximum wait time in seconds
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait_time:
            all_operations = await self._status_manager.get_all_operations()
            active_ops = [op for op in all_operations.values() if op.status == OperationStatus.RUNNING]
            
            if not active_ops:
                break
            
            logger.info(f"Waiting for {len(active_ops)} active operations to complete...")
            await asyncio.sleep(1)
        
        # Cancel any remaining operations
        all_operations = await self._status_manager.get_all_operations()
        remaining_ops = [op for op in all_operations.values() if op.status == OperationStatus.RUNNING]
        
        if remaining_ops:
            logger.warning(f"Forcibly cancelling {len(remaining_ops)} remaining operations")
            for operation in remaining_ops:
                await self._status_manager.update_status(operation.id, OperationStatus.CANCELLED)
        
        logger.info("Vector operation queue shutdown complete")


class AsyncQdrantConnectionPool:
    """Connection pool for async Qdrant operations with resource management."""
    
    def __init__(self, url: str, max_connections: int = 10, timeout: float = 30.0):
        """
        Initialize connection pool.
        
        Args:
            url: Qdrant server URL
            max_connections: Maximum number of concurrent connections
            timeout: Default timeout for operations in seconds
        """
        self.url = url
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = asyncio.Queue(maxsize=max_connections)
        self._executor = ThreadPoolExecutor(max_workers=max_connections)
        self._connections_created = 0
        self._lock = asyncio.Lock()
        self._closed = False
    
    async def _create_connection(self) -> QdrantClient:
        """Create a new Qdrant client connection."""
        return QdrantClient(url=self.url)
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        connection = None
        try:
            # Try to get existing connection from pool
            try:
                connection = self._pool.get_nowait()
            except asyncio.QueueEmpty:
                # Create new connection if pool is empty and under limit
                async with self._lock:
                    if self._connections_created < self.max_connections:
                        connection = await asyncio.get_event_loop().run_in_executor(
                            self._executor, self._create_connection
                        )
                        self._connections_created += 1
                    else:
                        # Wait for available connection
                        connection = await asyncio.wait_for(
                            self._pool.get(), timeout=self.timeout
                        )
            
            yield connection
            
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for connection from pool")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector store connection timeout"
            )
        finally:
            # Return connection to pool if it's still valid
            if connection and not self._closed:
                try:
                    self._pool.put_nowait(connection)
                except asyncio.QueueFull:
                    # Pool is full, close this connection
                    await asyncio.get_event_loop().run_in_executor(
                        self._executor, self._close_connection, connection
                    )
    
    def _close_connection(self, connection: QdrantClient):
        """Close a single connection."""
        try:
            if hasattr(connection, 'close'):
                connection.close()
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    async def execute_with_timeout(self, operation, *args, timeout: Optional[float] = None, **kwargs):
        """
        Execute an operation with timeout and proper async handling.
        
        Args:
            operation: The operation to execute
            *args: Positional arguments for the operation
            timeout: Operation timeout (uses default if None)
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Operation result
        """
        operation_timeout = timeout or self.timeout
        
        try:
            # Execute the synchronous operation in thread pool
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    self._executor, operation, *args, **kwargs
                ),
                timeout=operation_timeout
            )
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Operation timeout after {operation_timeout}s")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Vector operation timeout after {operation_timeout}s"
            )
        except FutureTimeoutError:
            logger.error(f"Future timeout after {operation_timeout}s")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Vector operation timeout after {operation_timeout}s"
            )
    
    async def close(self):
        """Close all connections in the pool."""
        if self._closed:
            return
        
        self._closed = True
        
        # Close all connections in pool
        connections_to_close = []
        while not self._pool.empty():
            try:
                connection = self._pool.get_nowait()
                connections_to_close.append(connection)
            except asyncio.QueueEmpty:
                break
        
        # Close connections in parallel
        if connections_to_close:
            await asyncio.gather(*[
                asyncio.get_event_loop().run_in_executor(
                    self._executor, self._close_connection, conn
                )
                for conn in connections_to_close
            ], return_exceptions=True)
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        logger.info(f"Closed connection pool with {len(connections_to_close)} connections")


class VectorStoreInterface(ABC):
    """Abstract interface for vector store implementations."""
    
    @abstractmethod
    async def create_collection(self, bot_id: str, dimension: int, **kwargs) -> bool:
        """
        Create a collection/namespace for a bot.
        
        Args:
            bot_id: Bot identifier
            dimension: Embedding dimension
            **kwargs: Additional configuration parameters
            
        Returns:
            True if collection created successfully
        """
        pass
    
    @abstractmethod
    async def delete_collection(self, bot_id: str) -> bool:
        """
        Delete a collection/namespace for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            True if collection deleted successfully
        """
        pass
    
    @abstractmethod
    async def collection_exists(self, bot_id: str) -> bool:
        """
        Check if a collection/namespace exists for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            True if collection exists
        """
        pass
    
    @abstractmethod
    async def store_embeddings(
        self,
        bot_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Store embeddings with associated texts and metadata.
        
        Args:
            bot_id: Bot identifier
            embeddings: List of embedding vectors
            texts: List of original texts
            metadata: List of metadata dictionaries
            ids: Optional list of custom IDs (generated if None)
            
        Returns:
            List of stored embedding IDs
        """
        pass
    
    @abstractmethod
    async def search_similar(
        self,
        bot_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings.
        
        Args:
            bot_id: Bot identifier
            query_embedding: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            metadata_filter: Optional metadata filter
            
        Returns:
            List of search results with id, score, text, and metadata
        """
        pass
    
    @abstractmethod
    async def delete_embeddings(self, bot_id: str, ids: List[str]) -> bool:
        """
        Delete specific embeddings by ID.
        
        Args:
            bot_id: Bot identifier
            ids: List of embedding IDs to delete
            
        Returns:
            True if embeddings deleted successfully
        """
        pass
    
    @abstractmethod
    async def get_collection_info(self, bot_id: str) -> Dict[str, Any]:
        """
        Get information about a collection.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Dictionary with collection information
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Close the vector store connection and clean up resources."""
        pass


class QdrantVectorStore(VectorStoreInterface):
    """Qdrant vector store implementation with bot-specific namespace isolation and async operations."""
    
    def __init__(
        self, 
        url: str = None, 
        max_connections: int = 10, 
        timeout: float = 30.0,
        max_concurrent_operations: int = 5,
        max_queue_size: int = 100
    ):
        """
        Initialize Qdrant vector store with connection pooling and operation queue.
        
        Args:
            url: Qdrant server URL (uses settings default if None)
            max_connections: Maximum number of concurrent connections
            timeout: Default timeout for operations in seconds
            max_concurrent_operations: Maximum number of concurrent operations
            max_queue_size: Maximum number of queued operations
        """
        self.url = url or settings.qdrant_url
        self.max_connections = max_connections
        self.timeout = timeout
        self._connection_pool = AsyncQdrantConnectionPool(
            self.url, max_connections, timeout
        )
        self._operation_queue = VectorOperationQueue(
            max_concurrent_operations, max_queue_size
        )
        self._collection_prefix = "bot_"
        self._queue_processor_task = None
        self._start_queue_processor()
    
    def _get_collection_name(self, bot_id: str) -> str:
        """Get collection name for a bot."""
        return f"{self._collection_prefix}{bot_id}"
    
    def _start_queue_processor(self):
        """Start the background queue processor."""
        try:
            # Only start if we're in an async context
            loop = asyncio.get_running_loop()
            if self._queue_processor_task is None or self._queue_processor_task.done():
                self._queue_processor_task = asyncio.create_task(
                    self._operation_queue.process_queue()
                )
        except RuntimeError:
            # No event loop running, defer initialization
            self._queue_processor_task = None
    
    async def _ensure_queue_processor_started(self):
        """Ensure the queue processor is started in an async context."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(
                self._operation_queue.process_queue()
            )

    async def _execute_with_queue(
        self, 
        operation_name: str, 
        operation_func: callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute an operation through the queue system.
        
        Args:
            operation_name: Name of the operation for tracking
            operation_func: The async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Operation result
        """
        # Ensure queue processor is started
        await self._ensure_queue_processor_started()
        
        operation_id = f"{operation_name}_{uuid.uuid4().hex[:8]}"
        
        # For critical operations, execute directly
        critical_operations = ['collection_exists', 'get_collection_info']
        if operation_name in critical_operations:
            return await operation_func(*args, **kwargs)
        
        # Queue non-critical operations
        await self._operation_queue.enqueue_operation(
            operation_id, operation_func, *args, **kwargs
        )
        
        # Execute the operation
        operation_data = {
            'id': operation_id,
            'func': operation_func,
            'args': args,
            'kwargs': kwargs,
            'created_at': time.time(),
            'status': 'queued'
        }
        
        return await self._operation_queue.execute_operation(operation_data)
    
    async def create_collection(self, bot_id: str, dimension: int, **kwargs) -> bool:
        """Create a collection for a bot with proper configuration."""
        collection_name = self._get_collection_name(bot_id)
        
        try:
            # Check if collection already exists
            if await self.collection_exists(bot_id):
                logger.info(f"Collection {collection_name} already exists")
                return True
            
            # Create collection with vector configuration using synchronous client
            client = QdrantClient(url=self.url)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE
                )
            )
            
            logger.info(f"Created collection {collection_name} with dimension {dimension}")
            return True
            
        except HTTPException:
            # Re-raise HTTP exceptions (timeouts, etc.)
            raise
        except ResponseHandlingException as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating collection {collection_name}: {e}")
            return False
    
    async def delete_collection(self, bot_id: str) -> bool:
        """Delete a collection for a bot."""
        collection_name = self._get_collection_name(bot_id)
        
        try:
            if not await self.collection_exists(bot_id):
                logger.info(f"Collection {collection_name} does not exist")
                return True
            
            # Use synchronous client for now
            client = QdrantClient(url=self.url)
            client.delete_collection(collection_name)
            
            logger.info(f"Deleted collection {collection_name}")
            return True
            
        except HTTPException:
            # Re-raise HTTP exceptions (timeouts, etc.)
            raise
        except ResponseHandlingException as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting collection {collection_name}: {e}")
            return False
    
    async def collection_exists(self, bot_id: str) -> bool:
        """Check if a collection exists for a bot."""
        collection_name = self._get_collection_name(bot_id)
        
        try:
            # Use synchronous client for now until async connection pool is properly implemented
            client = QdrantClient(url=self.url)
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]
            exists = collection_name in collection_names
            logger.info(f"Collection {collection_name} exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking collection existence {collection_name}: {e}")
            return False
    
    async def store_embeddings(
        self,
        bot_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        metadata: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Store embeddings in Qdrant with bot isolation and async batch processing."""
        collection_name = self._get_collection_name(bot_id)
        
        if not await self.collection_exists(bot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection for bot {bot_id} does not exist"
            )
        
        if len(embeddings) != len(texts) or len(embeddings) != len(metadata):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Embeddings, texts, and metadata must have the same length"
            )
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in embeddings]
        elif len(ids) != len(embeddings):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IDs must have the same length as embeddings"
            )
        
        try:
            # Prepare points for insertion
            points = []
            for i, (embedding, text, meta, point_id) in enumerate(zip(embeddings, texts, metadata, ids)):
                # Add text to metadata for retrieval
                full_metadata = {**meta, "text": text, "bot_id": bot_id}
                
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=full_metadata
                    )
                )
            
            # Insert points in batches with queue management
            batch_size = 100
            batch_operations = []
            
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                
                # Create operation function for this batch
                async def batch_upsert(batch_points=batch):
                    async with self._connection_pool.get_connection() as client:
                        return await self._connection_pool.execute_with_timeout(
                            client.upsert,
                            collection_name=collection_name,
                            points=batch_points
                        )
                
                batch_operations.append(batch_upsert)
            
            # Execute batches through queue system with concurrency control
            results = await asyncio.gather(*[
                self._execute_with_queue(f"store_batch_{i}", op)
                for i, op in enumerate(batch_operations)
            ])
            
            logger.info(f"Stored {len(embeddings)} embeddings in collection {collection_name}")
            return ids
            
        except HTTPException:
            # Re-raise HTTP exceptions (timeouts, etc.)
            raise
        except ResponseHandlingException as e:
            logger.error(f"Failed to store embeddings in {collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store embeddings: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error storing embeddings in {collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store embeddings: {str(e)}"
            )
    
    async def search_similar(
        self,
        bot_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings in Qdrant with async operations."""
        collection_name = self._get_collection_name(bot_id)
        
        if not await self.collection_exists(bot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection for bot {bot_id} does not exist"
            )
        
        try:
            # Build filter conditions
            filter_conditions = [
                models.FieldCondition(
                    key="bot_id",
                    match=models.MatchValue(value=bot_id)
                )
            ]
            
            # Add metadata filters if provided
            if metadata_filter:
                for key, value in metadata_filter.items():
                    filter_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
            
            # Perform search using synchronous client
            client = QdrantClient(url=self.url)
            search_result = client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=models.Filter(
                    must=filter_conditions
                ) if filter_conditions else None
            )
            
            # Format results
            results = []
            for hit in search_result:
                result = {
                    "id": str(hit.id),
                    "score": hit.score,
                    "text": hit.payload.get("text", ""),
                    "metadata": {k: v for k, v in hit.payload.items() if k not in ["text", "bot_id"]}
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar embeddings in collection {collection_name}")
            return results
            
        except HTTPException:
            # Re-raise HTTP exceptions (timeouts, etc.)
            raise
        except ResponseHandlingException as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to search embeddings: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error searching in {collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to search embeddings: {str(e)}"
            )
    
    async def delete_embeddings(self, bot_id: str, ids: List[str]) -> bool:
        """Delete specific embeddings by ID with async operations."""
        collection_name = self._get_collection_name(bot_id)
        
        if not await self.collection_exists(bot_id):
            logger.warning(f"Collection {collection_name} does not exist")
            return True
        
        try:
            # Use synchronous client for now
            client = QdrantClient(url=self.url)
            client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=ids)
            )
            
            logger.info(f"Deleted {len(ids)} embeddings from collection {collection_name}")
            return True
            
        except HTTPException:
            # Re-raise HTTP exceptions (timeouts, etc.)
            raise
        except ResponseHandlingException as e:
            logger.error(f"Failed to delete embeddings from {collection_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting embeddings from {collection_name}: {e}")
            return False
    
    async def get_collection_info(self, bot_id: str) -> Dict[str, Any]:
        """Get information about a collection with async operations."""
        collection_name = self._get_collection_name(bot_id)
        
        if not await self.collection_exists(bot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection for bot {bot_id} does not exist"
            )
        
        try:
            # Use synchronous client for now
            client = QdrantClient(url=self.url)
            info = client.get_collection(collection_name)
            
            return {
                "name": collection_name,
                "bot_id": bot_id,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance
                }
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions (timeouts, etc.)
            raise
        except ResponseHandlingException as e:
            logger.error(f"Failed to get collection info for {collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get collection info: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error getting collection info for {collection_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get collection info: {str(e)}"
            )
    
    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific operation."""
        return await self._operation_queue.get_operation_status(operation_id)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics for monitoring."""
        return await self._operation_queue.get_queue_stats()
    
    async def close(self):
        """Close the connection pool and operation queue."""
        try:
            # Shutdown operation queue first
            if self._queue_processor_task and not self._queue_processor_task.done():
                self._queue_processor_task.cancel()
                try:
                    await self._queue_processor_task
                except asyncio.CancelledError:
                    pass
            
            await self._operation_queue.shutdown()
            await self._connection_pool.close()
            logger.info("Closed Qdrant connection pool and operation queue")
        except Exception as e:
            logger.error(f"Error closing Qdrant resources: {e}")


class VectorStoreFactory:
    """Factory for creating vector store instances."""
    
    @staticmethod
    def create_vector_store(
        url: str = None, 
        max_connections: int = 10, 
        timeout: float = 30.0,
        max_concurrent_operations: int = 5,
        max_queue_size: int = 100
    ) -> VectorStoreInterface:
        """
        Create a Qdrant vector store instance with async connection pooling and operation queue.
        
        Args:
            url: Qdrant server URL (uses settings default if None)
            max_connections: Maximum number of concurrent connections
            timeout: Default timeout for operations in seconds
            max_concurrent_operations: Maximum number of concurrent operations
            max_queue_size: Maximum number of queued operations
            
        Returns:
            QdrantVectorStore instance with async capabilities and backpressure
        """
        return QdrantVectorStore(
            url=url, 
            max_connections=max_connections, 
            timeout=timeout,
            max_concurrent_operations=max_concurrent_operations,
            max_queue_size=max_queue_size
        )
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """Get list of supported vector store types."""
        return ["qdrant"]


# Service class for high-level vector operations
class VectorService:
    """High-level service for vector store operations with bot isolation and async capabilities."""
    
    def __init__(
        self, 
        vector_store: VectorStoreInterface = None,
        max_connections: int = 10,
        timeout: float = 30.0,
        max_concurrent_operations: int = 5,
        max_queue_size: int = 100
    ):
        """
        Initialize vector service with async capabilities and backpressure.
        
        Args:
            vector_store: Vector store instance (creates default if None)
            max_connections: Maximum number of concurrent connections
            timeout: Default timeout for operations in seconds
            max_concurrent_operations: Maximum number of concurrent operations
            max_queue_size: Maximum number of queued operations
        """
        self.vector_store = vector_store or VectorStoreFactory.create_vector_store(
            max_connections=max_connections, 
            timeout=timeout,
            max_concurrent_operations=max_concurrent_operations,
            max_queue_size=max_queue_size
        )
        self.max_connections = max_connections
        self.timeout = timeout
        self.max_concurrent_operations = max_concurrent_operations
        self.max_queue_size = max_queue_size
    
    async def initialize_bot_collection(self, bot_id: str, dimension: int) -> bool:
        """
        Initialize a collection for a bot.
        
        Args:
            bot_id: Bot identifier
            dimension: Embedding dimension
            
        Returns:
            True if collection initialized successfully
        """
        return await self.vector_store.create_collection(bot_id, dimension)
    
    async def delete_bot_collection(self, bot_id: str) -> bool:
        """
        Delete a bot's collection and all its data.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            True if collection deleted successfully
        """
        return await self.vector_store.delete_collection(bot_id)
    
    async def store_document_chunks(
        self,
        bot_id: str,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store document chunks with embeddings.
        
        Args:
            bot_id: Bot identifier
            chunks: List of chunk dictionaries with 'embedding', 'text', and 'metadata'
            
        Returns:
            List of stored chunk IDs
        """
        if not chunks:
            return []
        
        embeddings = [chunk["embedding"] for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadata = [chunk["metadata"] for chunk in chunks]
        ids = [chunk.get("id") for chunk in chunks]
        
        # Filter out None IDs
        if any(id is None for id in ids):
            ids = None
        
        return await self.vector_store.store_embeddings(
            bot_id, embeddings, texts, metadata, ids
        )
    
    async def search_relevant_chunks(
        self,
        bot_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        document_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks.
        
        Args:
            bot_id: Bot identifier
            query_embedding: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            document_filter: Optional document ID filter
            
        Returns:
            List of relevant chunks with scores
        """
        metadata_filter = {}
        if document_filter:
            metadata_filter["document_id"] = document_filter
        
        return await self.vector_store.search_similar(
            bot_id, query_embedding, top_k, score_threshold, metadata_filter
        )
    
    async def delete_document_chunks(self, bot_id: str, chunk_ids: List[str]) -> bool:
        """
        Delete specific document chunks.
        
        Args:
            bot_id: Bot identifier
            chunk_ids: List of chunk IDs to delete
            
        Returns:
            True if chunks deleted successfully
        """
        return await self.vector_store.delete_embeddings(bot_id, chunk_ids)
    
    async def get_bot_collection_stats(self, bot_id: str) -> Dict[str, Any]:
        """
        Get statistics about a bot's collection.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Dictionary with collection statistics
        """
        return await self.vector_store.get_collection_info(bot_id)
    
    async def store_document_chunks_with_progress(
        self,
        bot_id: str,
        chunks: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """
        Store document chunks with progress tracking and cancellation support.
        
        Args:
            bot_id: Bot identifier
            chunks: List of chunk dictionaries with 'embedding', 'text', and 'metadata'
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of stored chunk IDs
        """
        if not chunks:
            return []
        
        total_chunks = len(chunks)
        batch_size = 100
        stored_ids = []
        
        try:
            for i in range(0, total_chunks, batch_size):
                batch = chunks[i:i + batch_size]
                
                # Store batch
                batch_ids = await self.store_document_chunks(bot_id, batch)
                stored_ids.extend(batch_ids)
                
                # Report progress
                if progress_callback:
                    progress = min((i + batch_size) / total_chunks, 1.0)
                    await progress_callback(progress, f"Stored {len(stored_ids)}/{total_chunks} chunks")
                
                # Allow for cancellation between batches
                await asyncio.sleep(0)  # Yield control to event loop
            
            return stored_ids
            
        except asyncio.CancelledError:
            logger.info(f"Document chunk storage cancelled for bot {bot_id}")
            raise
        except Exception as e:
            logger.error(f"Error storing document chunks for bot {bot_id}: {e}")
            raise
    
    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific vector operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Operation status dictionary or None if not found
        """
        if hasattr(self.vector_store, 'get_operation_status'):
            return await self.vector_store.get_operation_status(operation_id)
        return None
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        stats = {
            'service_config': {
                'max_connections': self.max_connections,
                'timeout': self.timeout,
                'max_concurrent_operations': self.max_concurrent_operations,
                'max_queue_size': self.max_queue_size
            }
        }
        
        # Add queue stats if available
        if hasattr(self.vector_store, 'get_queue_stats'):
            queue_stats = await self.vector_store.get_queue_stats()
            stats['queue_stats'] = queue_stats
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the vector service.
        
        Returns:
            Health status dictionary
        """
        try:
            # Test basic connectivity
            test_bot_id = f"health_check_{uuid.uuid4().hex[:8]}"
            
            # Try to create and delete a test collection
            await self.initialize_bot_collection(test_bot_id, 128)
            await self.delete_bot_collection(test_bot_id)
            
            # Get service stats
            stats = await self.get_service_stats()
            
            return {
                'status': 'healthy',
                'timestamp': time.time(),
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return {
                'status': 'unhealthy',
                'timestamp': time.time(),
                'error': str(e)
            }
    
    async def close(self):
        """Close the vector service and clean up resources."""
        await self.vector_store.close()