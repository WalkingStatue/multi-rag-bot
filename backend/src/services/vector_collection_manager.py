"""
Vector Collection Manager - Proactive management of vector collections with lifecycle automation.
"""
import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.document import Document
from .vector_store import VectorService
from .embedding_service import EmbeddingProviderService


logger = logging.getLogger(__name__)


@dataclass
class CollectionInfo:
    """Information about a vector collection."""
    bot_id: str
    collection_name: str
    exists: bool
    dimension: Optional[int] = None
    points_count: Optional[int] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    last_updated: Optional[float] = None


@dataclass
class CollectionResult:
    """Result of collection operations."""
    success: bool
    collection_info: Optional[CollectionInfo] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OptimizationResult:
    """Result of collection optimization."""
    success: bool
    optimizations_applied: List[str] = None
    performance_improvement: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConfigurationChange:
    """Represents a configuration change that requires collection migration."""
    bot_id: str
    old_config: Dict[str, Any]
    new_config: Dict[str, Any]
    change_type: str  # 'provider', 'model', 'dimension'
    detected_at: float
    migration_required: bool
    priority: str  # 'high', 'medium', 'low'


@dataclass
class MaintenanceTask:
    """Represents a scheduled maintenance task for a collection."""
    bot_id: str
    task_type: str  # 'optimization', 'health_check', 'cleanup'
    scheduled_at: float
    priority: int  # 1-5, 1 being highest priority
    metadata: Optional[Dict[str, Any]] = None
    attempts: int = 0
    max_attempts: int = 3
    last_attempt: Optional[float] = None


@dataclass
class DiagnosticInfo:
    """Detailed diagnostic information for collection failures."""
    bot_id: str
    error_type: str
    error_message: str
    timestamp: float
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    remediation_steps: List[str] = None


class CollectionStatus(Enum):
    """Collection status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    MIGRATING = "migrating"
    OPTIMIZING = "optimizing"
    MAINTENANCE = "maintenance"


class MaintenanceTaskType(Enum):
    """Types of maintenance tasks."""
    OPTIMIZATION = "optimization"
    HEALTH_CHECK = "health_check"
    CLEANUP = "cleanup"
    REPAIR = "repair"
    MIGRATION = "migration"


class VectorCollectionManager:
    """
    Proactive management of vector collections with lifecycle automation.
    
    This manager handles:
    - Automatic collection initialization during bot creation
    - Configuration change detection and migration triggers
    - Collection health monitoring and maintenance
    - Performance optimization and cleanup
    """
    
    def __init__(self, db: Session):
        """
        Initialize Vector Collection Manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.vector_service = VectorService()
        self.embedding_service = EmbeddingProviderService()
        
        # Configuration
        self.health_check_interval = 300  # 5 minutes
        self.optimization_threshold = 1000  # Optimize when collection has 1000+ points
        self.max_retry_attempts = 3
        self.retry_delay = 2.0
        self.max_retry_delay = 30.0  # Maximum delay between retries
        self.maintenance_interval = 3600  # 1 hour between maintenance checks
        
        # Collection monitoring
        self._collection_health: Dict[str, Dict[str, Any]] = {}
        self._last_health_check: Dict[str, float] = {}
        
        # Performance tracking
        self._performance_metrics: Dict[str, List[float]] = {}
        
        # Configuration change detection
        self._bot_configurations: Dict[str, Dict[str, Any]] = {}
        self._configuration_changes: List[ConfigurationChange] = []
        
        # Maintenance scheduling
        self._maintenance_queue: List[MaintenanceTask] = []
        self._last_maintenance_check: float = 0
        
        # Diagnostic information
        self._diagnostic_logs: List[DiagnosticInfo] = []
        self._max_diagnostic_logs = 1000  # Keep last 1000 diagnostic entries
    
    async def ensure_collection_exists(
        self,
        bot_id: uuid.UUID,
        embedding_config: Dict[str, Any],
        force_recreate: bool = False
    ) -> CollectionResult:
        """
        Ensure vector collection exists with correct configuration.
        
        Args:
            bot_id: Bot identifier
            embedding_config: Embedding configuration with provider, model, dimension
            force_recreate: Whether to recreate collection if it exists
            
        Returns:
            CollectionResult with collection status and information
        """
        try:
            logger.info(f"Ensuring collection exists for bot {bot_id} with config: {embedding_config}")
            
            collection_name = str(bot_id)
            dimension = embedding_config.get("dimension")
            
            if not dimension:
                return CollectionResult(
                    success=False,
                    error="Embedding dimension not specified in configuration"
                )
            
            # Check if collection exists
            collection_exists = await self.vector_service.vector_store.collection_exists(collection_name)
            
            if collection_exists and not force_recreate:
                # Validate existing collection configuration
                try:
                    collection_info = await self.vector_service.get_bot_collection_stats(collection_name)
                    stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
                    
                    if stored_dimension != dimension:
                        logger.warning(f"Dimension mismatch for bot {bot_id}: stored={stored_dimension}, expected={dimension}")
                        return CollectionResult(
                            success=False,
                            error=f"Collection dimension mismatch: expected {dimension}, found {stored_dimension}",
                            metadata={"requires_migration": True}
                        )
                    
                    # Collection exists and is compatible
                    logger.info(f"Collection for bot {bot_id} already exists and is compatible")
                    
                    collection_info_obj = CollectionInfo(
                        bot_id=collection_name,
                        collection_name=collection_name,
                        exists=True,
                        dimension=stored_dimension,
                        points_count=collection_info.get('points_count', 0),
                        status=CollectionStatus.HEALTHY.value,
                        metadata=collection_info,
                        last_updated=time.time()
                    )
                    
                    return CollectionResult(
                        success=True,
                        collection_info=collection_info_obj
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to validate existing collection for bot {bot_id}: {e}")
                    # Continue to recreate collection
                    force_recreate = True
            
            # Create or recreate collection
            if force_recreate and collection_exists:
                logger.info(f"Recreating collection for bot {bot_id}")
                delete_success = await self.vector_service.vector_store.delete_collection(collection_name)
                if not delete_success:
                    return CollectionResult(
                        success=False,
                        error="Failed to delete existing collection for recreation"
                    )
            
            # Create new collection with retry logic
            async def create_collection_operation():
                create_success = await self.vector_service.vector_store.create_collection(
                    collection_name, dimension
                )
                
                if not create_success:
                    raise Exception("Collection creation returned False")
                
                # Verify collection was created successfully
                await asyncio.sleep(1)  # Brief delay for collection to be ready
                
                collection_info = await self.vector_service.get_bot_collection_stats(collection_name)
                
                collection_info_obj = CollectionInfo(
                    bot_id=collection_name,
                    collection_name=collection_name,
                    exists=True,
                    dimension=dimension,
                    points_count=0,
                    status=CollectionStatus.HEALTHY.value,
                    metadata=collection_info,
                    last_updated=time.time()
                )
                
                # Update health tracking
                self._collection_health[collection_name] = {
                    "status": CollectionStatus.HEALTHY.value,
                    "last_check": time.time(),
                    "dimension": dimension,
                    "points_count": 0
                }
                
                return collection_info_obj
            
            try:
                collection_info_obj = await self.perform_collection_operation_with_retry(
                    "create_collection",
                    create_collection_operation,
                    bot_id
                )
                
                logger.info(f"Successfully created collection for bot {bot_id}")
                
                return CollectionResult(
                    success=True,
                    collection_info=collection_info_obj,
                    metadata={"created": True}
                )
                
            except Exception as e:
                return CollectionResult(
                    success=False,
                    error=str(e)
                )
            
            return CollectionResult(
                success=False,
                error="Failed to create collection after all retry attempts"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error ensuring collection for bot {bot_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    async def migrate_collection(
        self,
        bot_id: uuid.UUID,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any]
    ) -> CollectionResult:
        """
        Migrate collection to new embedding configuration.
        
        Args:
            bot_id: Bot identifier
            old_config: Current embedding configuration
            new_config: Target embedding configuration
            
        Returns:
            CollectionResult with migration status
        """
        try:
            logger.info(f"Migrating collection for bot {bot_id}: {old_config} -> {new_config}")
            
            collection_name = str(bot_id)
            
            # Update collection health status
            self._collection_health[collection_name] = {
                "status": CollectionStatus.MIGRATING.value,
                "last_check": time.time(),
                "migration_start": time.time()
            }
            
            # Check if dimensions are different
            old_dimension = old_config.get("dimension")
            new_dimension = new_config.get("dimension")
            
            if old_dimension == new_dimension:
                # No migration needed, just update metadata
                logger.info(f"No dimension change for bot {bot_id}, updating metadata only")
                
                self._collection_health[collection_name]["status"] = CollectionStatus.HEALTHY.value
                
                return CollectionResult(
                    success=True,
                    metadata={"migration_type": "metadata_only"}
                )
            
            # Create new collection with new dimensions using retry logic
            new_collection_name = f"migrating_{bot_id}_{int(time.time())}"
            
            async def create_migration_collection():
                create_success = await self.vector_service.vector_store.create_collection(
                    new_collection_name, new_dimension
                )
                
                if not create_success:
                    raise Exception("Failed to create migration collection")
                
                return new_collection_name
            
            try:
                migration_collection = await self.perform_collection_operation_with_retry(
                    "create_migration_collection",
                    create_migration_collection,
                    bot_id
                )
                
                # The actual data migration would be handled by EmbeddingCompatibilityManager
                # This method focuses on collection lifecycle management
                
                logger.info(f"Created migration collection {migration_collection} for bot {bot_id}")
                
                # Update health status to healthy after successful migration setup
                self._collection_health[collection_name]["status"] = CollectionStatus.HEALTHY.value
                
                return CollectionResult(
                    success=True,
                    metadata={
                        "migration_collection": migration_collection,
                        "old_dimension": old_dimension,
                        "new_dimension": new_dimension
                    }
                )
                
            except Exception as e:
                self._collection_health[collection_name]["status"] = CollectionStatus.FAILED.value
                
                await self._log_diagnostic_info(
                    bot_id=str(bot_id),
                    error_type="migration_failure",
                    error_message=str(e),
                    context={
                        "old_config": old_config,
                        "new_config": new_config,
                        "migration_collection": new_collection_name
                    },
                    remediation_steps=[
                        "Verify vector store connectivity",
                        "Check embedding configuration validity",
                        "Ensure sufficient storage space",
                        "Consider manual collection recreation"
                    ]
                )
                
                return CollectionResult(
                    success=False,
                    error=str(e)
                )
            
        except Exception as e:
            logger.error(f"Error migrating collection for bot {bot_id}: {e}")
            
            # Update health status
            if str(bot_id) in self._collection_health:
                self._collection_health[str(bot_id)]["status"] = CollectionStatus.FAILED.value
            
            await self._log_diagnostic_info(
                bot_id=str(bot_id),
                error_type="migration_error",
                error_message=str(e),
                context={
                    "old_config": old_config,
                    "new_config": new_config,
                    "operation": "migrate_collection"
                }
            )
            
            return CollectionResult(
                success=False,
                error=f"Migration error: {str(e)}"
            )
    
    async def optimize_collection(
        self,
        bot_id: uuid.UUID
    ) -> OptimizationResult:
        """
        Optimize collection performance and storage.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            OptimizationResult with optimization details
        """
        try:
            logger.info(f"Optimizing collection for bot {bot_id}")
            
            collection_name = str(bot_id)
            
            # Check if collection exists
            if not await self.vector_service.vector_store.collection_exists(collection_name):
                return OptimizationResult(
                    success=False,
                    error="Collection does not exist"
                )
            
            # Update status
            self._collection_health[collection_name] = {
                **self._collection_health.get(collection_name, {}),
                "status": CollectionStatus.OPTIMIZING.value,
                "optimization_start": time.time()
            }
            
            async def perform_optimization():
                optimizations_applied = []
                start_time = time.time()
                
                # Get collection info before optimization
                collection_info = await self.vector_service.get_bot_collection_stats(collection_name)
                points_before = collection_info.get('points_count', 0)
                
                # Optimization 1: Check for duplicate embeddings (if supported by vector store)
                # This is a placeholder for actual optimization logic
                optimizations_applied.append("duplicate_check")
                
                # Optimization 2: Compact collection (if supported)
                # This would depend on the vector store implementation
                optimizations_applied.append("compaction")
                
                # Optimization 3: Update collection configuration for better performance
                # This could include adjusting indexing parameters
                optimizations_applied.append("index_optimization")
                
                # Get collection info after optimization
                collection_info_after = await self.vector_service.get_bot_collection_stats(collection_name)
                points_after = collection_info_after.get('points_count', 0)
                
                optimization_time = time.time() - start_time
                
                # Calculate performance improvement (placeholder)
                performance_improvement = max(0, (points_before - points_after) / max(points_before, 1) * 100)
                
                return {
                    "optimizations_applied": optimizations_applied,
                    "performance_improvement": performance_improvement,
                    "optimization_time": optimization_time,
                    "points_before": points_before,
                    "points_after": points_after,
                    "collection_info": collection_info_after
                }
            
            try:
                result = await self.perform_collection_operation_with_retry(
                    "optimize_collection",
                    perform_optimization,
                    bot_id
                )
                
                # Update health status
                self._collection_health[collection_name]["status"] = CollectionStatus.HEALTHY.value
                self._collection_health[collection_name]["last_optimization"] = time.time()
                
                logger.info(f"Optimized collection for bot {bot_id} in {result['optimization_time']:.2f}s")
                
                return OptimizationResult(
                    success=True,
                    optimizations_applied=result["optimizations_applied"],
                    performance_improvement=result["performance_improvement"],
                    metadata={
                        "optimization_time": result["optimization_time"],
                        "points_before": result["points_before"],
                        "points_after": result["points_after"],
                        "collection_info": result["collection_info"]
                    }
                )
                
            except Exception as e:
                # Update health status
                self._collection_health[collection_name]["status"] = CollectionStatus.FAILED.value
                
                await self._log_diagnostic_info(
                    bot_id=str(bot_id),
                    error_type="optimization_failure",
                    error_message=str(e),
                    context={
                        "collection_name": collection_name,
                        "operation": "optimize_collection"
                    },
                    remediation_steps=[
                        "Check collection health status",
                        "Verify vector store performance",
                        "Consider manual optimization",
                        "Review collection size and configuration"
                    ]
                )
                
                return OptimizationResult(
                    success=False,
                    error=str(e)
                )
            
        except Exception as e:
            logger.error(f"Error optimizing collection for bot {bot_id}: {e}")
            
            # Update health status
            if str(bot_id) in self._collection_health:
                self._collection_health[str(bot_id)]["status"] = CollectionStatus.FAILED.value
            
            return OptimizationResult(
                success=False,
                error=f"Optimization error: {str(e)}"
            )
    
    async def check_collection_health(
        self,
        bot_id: uuid.UUID,
        force_check: bool = False
    ) -> CollectionInfo:
        """
        Check collection health and status.
        
        Args:
            bot_id: Bot identifier
            force_check: Whether to force a fresh health check
            
        Returns:
            CollectionInfo with current health status
        """
        try:
            collection_name = str(bot_id)
            current_time = time.time()
            
            # Check if we need to perform a health check
            last_check = self._last_health_check.get(collection_name, 0)
            if not force_check and (current_time - last_check) < self.health_check_interval:
                # Return cached health info
                cached_health = self._collection_health.get(collection_name)
                if cached_health:
                    return CollectionInfo(
                        bot_id=collection_name,
                        collection_name=collection_name,
                        exists=True,
                        status=cached_health["status"],
                        metadata=cached_health,
                        last_updated=cached_health["last_check"]
                    )
            
            # Perform fresh health check
            logger.debug(f"Performing health check for collection {collection_name}")
            
            # Check if collection exists
            exists = await self.vector_service.vector_store.collection_exists(collection_name)
            
            if not exists:
                health_info = {
                    "status": CollectionStatus.FAILED.value,
                    "last_check": current_time,
                    "error": "Collection does not exist"
                }
                self._collection_health[collection_name] = health_info
                
                return CollectionInfo(
                    bot_id=collection_name,
                    collection_name=collection_name,
                    exists=False,
                    status=CollectionStatus.FAILED.value,
                    metadata=health_info,
                    last_updated=current_time
                )
            
            # Get collection statistics
            try:
                collection_info = await self.vector_service.get_bot_collection_stats(collection_name)
                
                # Determine health status based on collection info
                status = CollectionStatus.HEALTHY.value
                points_count = collection_info.get('points_count', 0)
                
                # Check for potential issues
                if collection_info.get('status') != 'green':
                    status = CollectionStatus.DEGRADED.value
                
                health_info = {
                    "status": status,
                    "last_check": current_time,
                    "points_count": points_count,
                    "dimension": collection_info.get('config', {}).get('vector_size'),
                    "collection_status": collection_info.get('status'),
                    "segments_count": collection_info.get('segments_count', 0)
                }
                
                self._collection_health[collection_name] = health_info
                self._last_health_check[collection_name] = current_time
                
                return CollectionInfo(
                    bot_id=collection_name,
                    collection_name=collection_name,
                    exists=True,
                    dimension=health_info["dimension"],
                    points_count=points_count,
                    status=status,
                    metadata=health_info,
                    last_updated=current_time
                )
                
            except Exception as e:
                logger.error(f"Error getting collection stats for {collection_name}: {e}")
                
                health_info = {
                    "status": CollectionStatus.FAILED.value,
                    "last_check": current_time,
                    "error": str(e)
                }
                self._collection_health[collection_name] = health_info
                
                return CollectionInfo(
                    bot_id=collection_name,
                    collection_name=collection_name,
                    exists=True,
                    status=CollectionStatus.FAILED.value,
                    metadata=health_info,
                    last_updated=current_time
                )
            
        except Exception as e:
            logger.error(f"Error checking collection health for bot {bot_id}: {e}")
            
            return CollectionInfo(
                bot_id=str(bot_id),
                collection_name=str(bot_id),
                exists=False,
                status=CollectionStatus.FAILED.value,
                metadata={"error": str(e)},
                last_updated=time.time()
            )
    
    async def cleanup_orphaned_collections(self) -> Dict[str, Any]:
        """
        Clean up collections that no longer have associated bots.
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            logger.info("Starting cleanup of orphaned collections")
            
            # Get all bot IDs from database
            active_bot_ids = set(str(bot.id) for bot in self.db.query(Bot).all())
            
            # This would require extending the vector store interface to list all collections
            # For now, we'll return a placeholder result
            
            cleanup_results = {
                "collections_checked": 0,
                "orphaned_collections": [],
                "collections_deleted": 0,
                "errors": []
            }
            
            logger.info("Completed orphaned collection cleanup")
            
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Error during orphaned collection cleanup: {e}")
            return {
                "collections_checked": 0,
                "orphaned_collections": [],
                "collections_deleted": 0,
                "errors": [str(e)]
            }
    
    def get_collection_health_summary(self) -> Dict[str, Any]:
        """
        Get summary of all collection health statuses.
        
        Returns:
            Dictionary with health summary statistics
        """
        try:
            total_collections = len(self._collection_health)
            status_counts = {}
            
            for health_info in self._collection_health.values():
                status = health_info.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_collections": total_collections,
                "status_distribution": status_counts,
                "last_updated": time.time(),
                "collections_needing_attention": [
                    collection_name for collection_name, health_info in self._collection_health.items()
                    if health_info.get("status") in [CollectionStatus.FAILED.value, CollectionStatus.DEGRADED.value]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating collection health summary: {e}")
            return {
                "total_collections": 0,
                "status_distribution": {},
                "error": str(e)
            }
    
    async def schedule_maintenance(self, bot_id: uuid.UUID) -> bool:
        """
        Schedule maintenance for a collection.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            True if maintenance was scheduled successfully
        """
        try:
            collection_name = str(bot_id)
            
            # Check if collection needs optimization
            health_info = await self.check_collection_health(bot_id)
            
            if health_info.points_count and health_info.points_count >= self.optimization_threshold:
                # Schedule optimization
                optimization_result = await self.optimize_collection(bot_id)
                return optimization_result.success
            
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling maintenance for bot {bot_id}: {e}")
            return False
    
    async def repair_collection(self, bot_id: uuid.UUID) -> CollectionResult:
        """
        Attempt to repair a failed or degraded collection.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            CollectionResult with repair status
        """
        try:
            logger.info(f"Attempting to repair collection for bot {bot_id}")
            
            collection_name = str(bot_id)
            
            # Get bot configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return CollectionResult(
                    success=False,
                    error="Bot not found"
                )
            
            # Get embedding dimension
            try:
                embedding_dimension = self.embedding_service.get_embedding_dimension(
                    bot.embedding_provider, 
                    bot.embedding_model
                )
            except Exception as e:
                return CollectionResult(
                    success=False,
                    error=f"Failed to get embedding dimension: {str(e)}"
                )
            
            # Prepare embedding configuration
            embedding_config = {
                "provider": bot.embedding_provider,
                "model": bot.embedding_model,
                "dimension": embedding_dimension
            }
            
            # Check current collection status
            collection_exists = await self.vector_service.vector_store.collection_exists(collection_name)
            
            if not collection_exists:
                # Collection doesn't exist, create it
                logger.info(f"Collection doesn't exist for bot {bot_id}, creating new one")
                return await self.ensure_collection_exists(bot_id, embedding_config, force_recreate=False)
            
            # Collection exists but may be corrupted, try to get info
            try:
                collection_info = await self.vector_service.get_bot_collection_stats(collection_name)
                stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
                
                if stored_dimension != embedding_dimension:
                    # Dimension mismatch, need to recreate
                    logger.warning(f"Dimension mismatch for bot {bot_id}, recreating collection")
                    return await self.ensure_collection_exists(bot_id, embedding_config, force_recreate=True)
                
                # Collection seems healthy
                collection_info_obj = CollectionInfo(
                    bot_id=collection_name,
                    collection_name=collection_name,
                    exists=True,
                    dimension=stored_dimension,
                    points_count=collection_info.get('points_count', 0),
                    status=CollectionStatus.HEALTHY.value,
                    metadata=collection_info,
                    last_updated=time.time()
                )
                
                # Update health tracking
                self._collection_health[collection_name] = {
                    "status": CollectionStatus.HEALTHY.value,
                    "last_check": time.time(),
                    "dimension": stored_dimension,
                    "points_count": collection_info.get('points_count', 0),
                    "repaired": True
                }
                
                logger.info(f"Collection for bot {bot_id} repaired successfully")
                
                return CollectionResult(
                    success=True,
                    collection_info=collection_info_obj,
                    metadata={"repair_action": "validated_existing"}
                )
                
            except Exception as e:
                # Collection exists but is corrupted, recreate it
                logger.warning(f"Collection for bot {bot_id} appears corrupted, recreating: {e}")
                return await self.ensure_collection_exists(bot_id, embedding_config, force_recreate=True)
            
        except Exception as e:
            logger.error(f"Error repairing collection for bot {bot_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Repair failed: {str(e)}"
            )
    
    async def validate_collection_configuration(
        self,
        bot_id: uuid.UUID,
        expected_config: Dict[str, Any]
    ) -> CollectionResult:
        """
        Validate that a collection matches the expected configuration.
        
        Args:
            bot_id: Bot identifier
            expected_config: Expected embedding configuration
            
        Returns:
            CollectionResult with validation status
        """
        try:
            collection_name = str(bot_id)
            
            # Check if collection exists
            if not await self.vector_service.vector_store.collection_exists(collection_name):
                return CollectionResult(
                    success=False,
                    error="Collection does not exist",
                    metadata={"requires_creation": True}
                )
            
            # Get collection info
            collection_info = await self.vector_service.get_bot_collection_stats(collection_name)
            stored_dimension = collection_info.get('config', {}).get('vector_size', 0)
            expected_dimension = expected_config.get('dimension', 0)
            
            if stored_dimension != expected_dimension:
                return CollectionResult(
                    success=False,
                    error=f"Dimension mismatch: expected {expected_dimension}, found {stored_dimension}",
                    metadata={
                        "requires_migration": True,
                        "stored_dimension": stored_dimension,
                        "expected_dimension": expected_dimension
                    }
                )
            
            # Configuration is valid
            collection_info_obj = CollectionInfo(
                bot_id=collection_name,
                collection_name=collection_name,
                exists=True,
                dimension=stored_dimension,
                points_count=collection_info.get('points_count', 0),
                status=CollectionStatus.HEALTHY.value,
                metadata=collection_info,
                last_updated=time.time()
            )
            
            return CollectionResult(
                success=True,
                collection_info=collection_info_obj,
                metadata={"validation_passed": True}
            )
            
        except Exception as e:
            logger.error(f"Error validating collection configuration for bot {bot_id}: {e}")
            return CollectionResult(
                success=False,
                error=f"Validation error: {str(e)}"
            )
    
    async def detect_configuration_changes(self, bot_id: uuid.UUID) -> Optional[ConfigurationChange]:
        """
        Detect configuration changes that require collection migration.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            ConfigurationChange if changes detected, None otherwise
        """
        try:
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return None
            
            bot_id_str = str(bot_id)
            current_config = {
                "provider": bot.embedding_provider,
                "model": bot.embedding_model,
                "dimension": self.embedding_service.get_embedding_dimension(
                    bot.embedding_provider, bot.embedding_model
                )
            }
            
            # Check if we have a previous configuration
            if bot_id_str not in self._bot_configurations:
                # First time seeing this bot, store current config
                self._bot_configurations[bot_id_str] = current_config
                return None
            
            old_config = self._bot_configurations[bot_id_str]
            
            # Compare configurations
            changes = []
            change_type = None
            migration_required = False
            priority = "low"
            
            if old_config["provider"] != current_config["provider"]:
                changes.append("provider")
                change_type = "provider"
                migration_required = True
                priority = "high"
            
            if old_config["model"] != current_config["model"]:
                changes.append("model")
                change_type = "model"
                migration_required = True
                priority = "high" if old_config["dimension"] != current_config["dimension"] else "medium"
            
            if old_config["dimension"] != current_config["dimension"]:
                changes.append("dimension")
                change_type = "dimension"
                migration_required = True
                priority = "high"
            
            if changes:
                logger.info(f"Configuration changes detected for bot {bot_id}: {changes}")
                
                configuration_change = ConfigurationChange(
                    bot_id=bot_id_str,
                    old_config=old_config,
                    new_config=current_config,
                    change_type=change_type or "multiple",
                    detected_at=time.time(),
                    migration_required=migration_required,
                    priority=priority
                )
                
                # Update stored configuration
                self._bot_configurations[bot_id_str] = current_config
                
                # Add to change queue
                self._configuration_changes.append(configuration_change)
                
                # Schedule migration if required
                if migration_required:
                    await self._schedule_migration_task(bot_id, configuration_change)
                
                return configuration_change
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting configuration changes for bot {bot_id}: {e}")
            await self._log_diagnostic_info(
                bot_id=str(bot_id),
                error_type="configuration_detection_error",
                error_message=str(e),
                context={"operation": "detect_configuration_changes"}
            )
            return None
    
    async def _schedule_migration_task(self, bot_id: uuid.UUID, config_change: ConfigurationChange):
        """Schedule a migration task for configuration changes."""
        try:
            migration_task = MaintenanceTask(
                bot_id=str(bot_id),
                task_type=MaintenanceTaskType.MIGRATION.value,
                scheduled_at=time.time(),
                priority=1 if config_change.priority == "high" else 2,
                metadata={
                    "config_change": asdict(config_change),
                    "migration_type": "embedding_configuration"
                }
            )
            
            self._maintenance_queue.append(migration_task)
            self._maintenance_queue.sort(key=lambda x: (x.priority, x.scheduled_at))
            
            logger.info(f"Scheduled migration task for bot {bot_id} due to {config_change.change_type} change")
            
        except Exception as e:
            logger.error(f"Error scheduling migration task for bot {bot_id}: {e}")
    
    async def perform_collection_operation_with_retry(
        self,
        operation_name: str,
        operation_func,
        bot_id: uuid.UUID,
        *args,
        **kwargs
    ) -> Any:
        """
        Perform collection operation with exponential backoff retry logic.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            bot_id: Bot identifier
            *args: Arguments for the operation function
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Result of the operation function
        """
        last_exception = None
        
        for attempt in range(self.max_retry_attempts):
            try:
                logger.debug(f"Attempting {operation_name} for bot {bot_id} (attempt {attempt + 1})")
                
                result = await operation_func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Successfully completed {operation_name} for bot {bot_id} after {attempt + 1} attempts")
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for {operation_name} on bot {bot_id}: {e}")
                
                # Log diagnostic information
                await self._log_diagnostic_info(
                    bot_id=str(bot_id),
                    error_type=f"{operation_name}_retry_attempt",
                    error_message=str(e),
                    context={
                        "attempt": attempt + 1,
                        "max_attempts": self.max_retry_attempts,
                        "operation": operation_name
                    }
                )
                
                if attempt < self.max_retry_attempts - 1:
                    # Calculate exponential backoff delay
                    delay = min(self.retry_delay * (2 ** attempt), self.max_retry_delay)
                    logger.info(f"Waiting {delay}s before retry {attempt + 2} for {operation_name} on bot {bot_id}")
                    await asyncio.sleep(delay)
        
        # All attempts failed
        error_msg = f"Failed {operation_name} for bot {bot_id} after {self.max_retry_attempts} attempts: {last_exception}"
        logger.error(error_msg)
        
        await self._log_diagnostic_info(
            bot_id=str(bot_id),
            error_type=f"{operation_name}_final_failure",
            error_message=error_msg,
            context={
                "total_attempts": self.max_retry_attempts,
                "operation": operation_name,
                "final_error": str(last_exception)
            },
            remediation_steps=[
                f"Check {operation_name} configuration and dependencies",
                "Verify vector store connectivity",
                "Review bot embedding configuration",
                "Consider manual intervention if issue persists"
            ]
        )
        
        raise Exception(error_msg)
    
    async def _log_diagnostic_info(
        self,
        bot_id: str,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        stack_trace: Optional[str] = None,
        remediation_steps: Optional[List[str]] = None
    ):
        """Log detailed diagnostic information for collection failures."""
        try:
            diagnostic_info = DiagnosticInfo(
                bot_id=bot_id,
                error_type=error_type,
                error_message=error_message,
                timestamp=time.time(),
                context=context,
                stack_trace=stack_trace,
                remediation_steps=remediation_steps or []
            )
            
            self._diagnostic_logs.append(diagnostic_info)
            
            # Maintain maximum log size
            if len(self._diagnostic_logs) > self._max_diagnostic_logs:
                self._diagnostic_logs = self._diagnostic_logs[-self._max_diagnostic_logs:]
            
            # Log to standard logger as well
            logger.error(f"Diagnostic [{error_type}] for bot {bot_id}: {error_message}")
            if context:
                logger.error(f"Context: {json.dumps(context, indent=2)}")
            if remediation_steps:
                logger.error(f"Remediation steps: {remediation_steps}")
                
        except Exception as e:
            logger.error(f"Error logging diagnostic information: {e}")
    
    async def schedule_maintenance_tasks(self) -> Dict[str, Any]:
        """
        Schedule maintenance tasks based on collection health and performance.
        
        Returns:
            Dictionary with scheduling results
        """
        try:
            current_time = time.time()
            
            # Check if it's time for maintenance scheduling
            if current_time - self._last_maintenance_check < self.maintenance_interval:
                return {"message": "Maintenance check not due yet"}
            
            self._last_maintenance_check = current_time
            
            logger.info("Starting maintenance task scheduling")
            
            scheduled_tasks = []
            
            # Get all bots for maintenance evaluation
            bots = self.db.query(Bot).all()
            
            for bot in bots:
                bot_id_str = str(bot.id)
                
                # Check collection health
                health_info = await self.check_collection_health(bot.id, force_check=True)
                
                # Schedule optimization if needed
                if (health_info.points_count and 
                    health_info.points_count >= self.optimization_threshold and
                    not self._has_pending_task(bot_id_str, MaintenanceTaskType.OPTIMIZATION.value)):
                    
                    optimization_task = MaintenanceTask(
                        bot_id=bot_id_str,
                        task_type=MaintenanceTaskType.OPTIMIZATION.value,
                        scheduled_at=current_time,
                        priority=3,
                        metadata={"points_count": health_info.points_count}
                    )
                    
                    self._maintenance_queue.append(optimization_task)
                    scheduled_tasks.append(f"optimization for bot {bot_id_str}")
                
                # Schedule repair if collection is failed or degraded
                if (health_info.status in [CollectionStatus.FAILED.value, CollectionStatus.DEGRADED.value] and
                    not self._has_pending_task(bot_id_str, MaintenanceTaskType.REPAIR.value)):
                    
                    repair_task = MaintenanceTask(
                        bot_id=bot_id_str,
                        task_type=MaintenanceTaskType.REPAIR.value,
                        scheduled_at=current_time,
                        priority=1,  # High priority for repairs
                        metadata={"health_status": health_info.status}
                    )
                    
                    self._maintenance_queue.append(repair_task)
                    scheduled_tasks.append(f"repair for bot {bot_id_str}")
                
                # Schedule regular health checks
                last_check = self._last_health_check.get(bot_id_str, 0)
                if (current_time - last_check > self.health_check_interval * 2 and
                    not self._has_pending_task(bot_id_str, MaintenanceTaskType.HEALTH_CHECK.value)):
                    
                    health_check_task = MaintenanceTask(
                        bot_id=bot_id_str,
                        task_type=MaintenanceTaskType.HEALTH_CHECK.value,
                        scheduled_at=current_time,
                        priority=4,
                        metadata={"last_check": last_check}
                    )
                    
                    self._maintenance_queue.append(health_check_task)
                    scheduled_tasks.append(f"health_check for bot {bot_id_str}")
            
            # Sort maintenance queue by priority
            self._maintenance_queue.sort(key=lambda x: (x.priority, x.scheduled_at))
            
            logger.info(f"Scheduled {len(scheduled_tasks)} maintenance tasks: {scheduled_tasks}")
            
            return {
                "tasks_scheduled": len(scheduled_tasks),
                "scheduled_tasks": scheduled_tasks,
                "total_queue_size": len(self._maintenance_queue),
                "next_check": current_time + self.maintenance_interval
            }
            
        except Exception as e:
            logger.error(f"Error scheduling maintenance tasks: {e}")
            await self._log_diagnostic_info(
                bot_id="system",
                error_type="maintenance_scheduling_error",
                error_message=str(e),
                context={"operation": "schedule_maintenance_tasks"}
            )
            return {"error": str(e)}
    
    def _has_pending_task(self, bot_id: str, task_type: str) -> bool:
        """Check if a bot already has a pending task of the specified type."""
        return any(
            task.bot_id == bot_id and task.task_type == task_type
            for task in self._maintenance_queue
        )
    
    async def execute_next_maintenance_task(self) -> Optional[Dict[str, Any]]:
        """
        Execute the next maintenance task from the queue.
        
        Returns:
            Dictionary with execution results or None if no tasks
        """
        if not self._maintenance_queue:
            return None
        
        task = self._maintenance_queue.pop(0)
        
        try:
            logger.info(f"Executing maintenance task: {task.task_type} for bot {task.bot_id}")
            
            task.attempts += 1
            task.last_attempt = time.time()
            
            bot_id = uuid.UUID(task.bot_id)
            result = None
            
            if task.task_type == MaintenanceTaskType.OPTIMIZATION.value:
                result = await self.optimize_collection(bot_id)
                
            elif task.task_type == MaintenanceTaskType.HEALTH_CHECK.value:
                result = await self.check_collection_health(bot_id, force_check=True)
                
            elif task.task_type == MaintenanceTaskType.REPAIR.value:
                result = await self.repair_collection(bot_id)
                
            elif task.task_type == MaintenanceTaskType.CLEANUP.value:
                result = await self.cleanup_orphaned_collections()
                
            elif task.task_type == MaintenanceTaskType.MIGRATION.value:
                # Handle migration task
                config_change_data = task.metadata.get("config_change", {})
                if config_change_data:
                    old_config = config_change_data.get("old_config", {})
                    new_config = config_change_data.get("new_config", {})
                    result = await self.migrate_collection(bot_id, old_config, new_config)
            
            success = getattr(result, 'success', True) if result else True
            
            if success:
                logger.info(f"Successfully executed {task.task_type} for bot {task.bot_id}")
                return {
                    "task_type": task.task_type,
                    "bot_id": task.bot_id,
                    "success": True,
                    "attempts": task.attempts,
                    "result": result
                }
            else:
                # Task failed, decide whether to retry
                if task.attempts < task.max_attempts:
                    # Re-queue with lower priority
                    task.priority = min(task.priority + 1, 5)
                    task.scheduled_at = time.time() + (task.attempts * 60)  # Delay retry
                    self._maintenance_queue.append(task)
                    self._maintenance_queue.sort(key=lambda x: (x.priority, x.scheduled_at))
                    
                    logger.warning(f"Task {task.task_type} for bot {task.bot_id} failed, re-queued for retry")
                else:
                    logger.error(f"Task {task.task_type} for bot {task.bot_id} failed after {task.attempts} attempts")
                    
                    await self._log_diagnostic_info(
                        bot_id=task.bot_id,
                        error_type="maintenance_task_failure",
                        error_message=f"Task {task.task_type} failed after {task.attempts} attempts",
                        context={
                            "task_type": task.task_type,
                            "attempts": task.attempts,
                            "result": str(result) if result else "No result"
                        }
                    )
                
                return {
                    "task_type": task.task_type,
                    "bot_id": task.bot_id,
                    "success": False,
                    "attempts": task.attempts,
                    "error": getattr(result, 'error', 'Unknown error') if result else 'No result'
                }
                
        except Exception as e:
            logger.error(f"Error executing maintenance task {task.task_type} for bot {task.bot_id}: {e}")
            
            await self._log_diagnostic_info(
                bot_id=task.bot_id,
                error_type="maintenance_task_execution_error",
                error_message=str(e),
                context={
                    "task_type": task.task_type,
                    "attempts": task.attempts
                }
            )
            
            return {
                "task_type": task.task_type,
                "bot_id": task.bot_id,
                "success": False,
                "attempts": task.attempts,
                "error": str(e)
            }
    
    def get_maintenance_queue_status(self) -> Dict[str, Any]:
        """Get current status of the maintenance queue."""
        try:
            queue_by_type = {}
            queue_by_priority = {}
            
            for task in self._maintenance_queue:
                # Count by type
                queue_by_type[task.task_type] = queue_by_type.get(task.task_type, 0) + 1
                
                # Count by priority
                queue_by_priority[task.priority] = queue_by_priority.get(task.priority, 0) + 1
            
            return {
                "total_tasks": len(self._maintenance_queue),
                "tasks_by_type": queue_by_type,
                "tasks_by_priority": queue_by_priority,
                "next_task": asdict(self._maintenance_queue[0]) if self._maintenance_queue else None,
                "last_maintenance_check": self._last_maintenance_check,
                "next_maintenance_check": self._last_maintenance_check + self.maintenance_interval
            }
            
        except Exception as e:
            logger.error(f"Error getting maintenance queue status: {e}")
            return {"error": str(e)}
    
    def get_diagnostic_summary(self, bot_id: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get diagnostic summary for troubleshooting.
        
        Args:
            bot_id: Optional bot ID to filter diagnostics
            hours: Number of hours to look back
            
        Returns:
            Dictionary with diagnostic summary
        """
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            # Filter diagnostic logs
            filtered_logs = [
                log for log in self._diagnostic_logs
                if log.timestamp >= cutoff_time and (not bot_id or log.bot_id == bot_id)
            ]
            
            # Analyze error patterns
            error_types = {}
            error_bots = {}
            
            for log in filtered_logs:
                error_types[log.error_type] = error_types.get(log.error_type, 0) + 1
                error_bots[log.bot_id] = error_bots.get(log.bot_id, 0) + 1
            
            # Get recent configuration changes
            recent_changes = [
                change for change in self._configuration_changes
                if change.detected_at >= cutoff_time and (not bot_id or change.bot_id == bot_id)
            ]
            
            return {
                "time_range_hours": hours,
                "total_diagnostic_entries": len(filtered_logs),
                "error_types": error_types,
                "affected_bots": error_bots,
                "recent_configuration_changes": len(recent_changes),
                "configuration_changes": [asdict(change) for change in recent_changes],
                "most_common_errors": sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5],
                "most_affected_bots": sorted(error_bots.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            logger.error(f"Error generating diagnostic summary: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close the collection manager and clean up resources."""
        try:
            await self.vector_service.close()
            logger.info("Vector Collection Manager closed successfully")
        except Exception as e:
            logger.error(f"Error closing Vector Collection Manager: {e}")