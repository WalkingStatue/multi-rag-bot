"""
Embedding Compatibility Manager - Handles embedding provider transitions and dimension validation.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.document import Document, DocumentChunk
from .embedding_service import EmbeddingProviderService
from .vector_store import VectorService
from .user_service import UserService
from .dimension_validator import DimensionValidator
from .embedding_migration_system import EmbeddingMigrationSystem, MigrationConfig
from .embedding_configuration_validator import EmbeddingConfigurationValidator


logger = logging.getLogger(__name__)


@dataclass
class DimensionInfo:
    """Information about embedding dimensions."""
    provider: str
    model: str
    dimension: int
    compatible_providers: List[str] = None
    migration_required: bool = False


@dataclass
class CompatibilityResult:
    """Result of compatibility validation."""
    compatible: bool
    issues: List[str] = None
    recommendations: List[str] = None
    migration_required: bool = False
    current_config: Optional[Dict[str, Any]] = None
    target_config: Optional[Dict[str, Any]] = None


@dataclass
class MigrationResult:
    """Result of embedding migration."""
    success: bool
    migrated_chunks: int = 0
    total_chunks: int = 0
    error: Optional[str] = None
    rollback_available: bool = False
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class MigrationStatus(Enum):
    """Migration status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class EmbeddingCompatibilityManager:
    """
    Manages embedding provider transitions and ensures dimension compatibility.
    
    This manager handles:
    - Dimension validation between providers/models
    - Safe migration workflows with rollback capability
    - Compatibility checking before configuration changes
    - Migration progress tracking and status reporting
    """
    
    def __init__(self, db: Session):
        """
        Initialize Embedding Compatibility Manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = EmbeddingProviderService()
        self.vector_service = VectorService()
        self.user_service = UserService(db)
        self.dimension_validator = DimensionValidator(db)
        self.migration_system = EmbeddingMigrationSystem(db)
        self.configuration_validator = EmbeddingConfigurationValidator(db)
        
        # Migration configuration
        self.migration_batch_size = 50
        self.max_migration_retries = 3
        self.migration_timeout = 3600  # 1 hour
    
    async def validate_provider_change(
        self,
        bot_id: uuid.UUID,
        new_provider: str,
        new_model: str
    ) -> CompatibilityResult:
        """
        Validate embedding provider change and detect issues.
        
        Args:
            bot_id: Bot identifier
            new_provider: Target embedding provider
            new_model: Target embedding model
            
        Returns:
            CompatibilityResult with validation status and recommendations
        """
        try:
            logger.info(f"Validating provider change for bot {bot_id}: {new_provider}/{new_model}")
            
            # Use the enhanced configuration validator for comprehensive validation
            validation_report = await self.configuration_validator.validate_configuration_change(
                bot_id=bot_id,
                new_provider=new_provider,
                new_model=new_model,
                change_reason="Provider change validation"
            )
            
            # Convert ValidationReport to CompatibilityResult
            issues = [issue.message for issue in validation_report.issues]
            recommendations = validation_report.recommendations
            
            return CompatibilityResult(
                compatible=validation_report.is_valid,
                issues=issues,
                recommendations=recommendations,
                migration_required=validation_report.migration_required,
                current_config=validation_report.metadata.get("current_config") if validation_report.metadata else None,
                target_config=validation_report.metadata.get("target_config") if validation_report.metadata else None
            )
            
        except Exception as e:
            logger.error(f"Error validating provider change for bot {bot_id}: {e}")
            return CompatibilityResult(
                compatible=False,
                issues=[f"Validation error: {str(e)}"],
                recommendations=["Check bot configuration and try again"]
            )
    
    async def migrate_embeddings(
        self,
        bot_id: uuid.UUID,
        from_config: Dict[str, Any],
        to_config: Dict[str, Any]
    ) -> MigrationResult:
        """
        Migrate embeddings to new provider/model with rollback capability.
        
        This method now uses the enhanced EmbeddingMigrationSystem for improved
        safety, progress tracking, and rollback capabilities.
        
        Args:
            bot_id: Bot identifier
            from_config: Current embedding configuration
            to_config: Target embedding configuration
            
        Returns:
            MigrationResult with migration status and statistics
        """
        try:
            logger.info(f"Starting enhanced embedding migration for bot {bot_id}")
            
            # Create migration configuration
            migration_config = await self.migration_system.create_migration_config(
                bot_id=bot_id,
                to_provider=to_config["provider"],
                to_model=to_config["model"],
                batch_size=self.migration_batch_size,
                enable_rollback=True
            )
            
            # Start migration
            migration_id, initial_progress = await self.migration_system.start_migration(migration_config)
            
            # Wait for migration to complete (with timeout)
            start_time = time.time()
            while True:
                progress = await self.migration_system.get_migration_progress(migration_id)
                if not progress:
                    break
                
                # Check if completed or failed
                if progress.status in [MigrationStatus.COMPLETED, MigrationStatus.FAILED, 
                                     MigrationStatus.ROLLED_BACK, MigrationStatus.CANCELLED]:
                    break
                
                # Check timeout
                if time.time() - start_time > self.migration_timeout:
                    await self.migration_system.cancel_migration(migration_id)
                    return MigrationResult(
                        success=False,
                        migrated_chunks=progress.processed_chunks,
                        total_chunks=progress.total_chunks,
                        error="Migration timed out",
                        processing_time=time.time() - start_time
                    )
                
                # Wait before checking again
                await asyncio.sleep(5)
            
            # Get final progress
            final_progress = await self.migration_system.get_migration_progress(migration_id)
            if not final_progress:
                return MigrationResult(
                    success=False,
                    error="Migration progress lost"
                )
            
            # Convert to legacy MigrationResult format
            processing_time = (final_progress.last_update - final_progress.start_time).total_seconds()
            
            return MigrationResult(
                success=final_progress.status == MigrationStatus.COMPLETED,
                migrated_chunks=final_progress.processed_chunks,
                total_chunks=final_progress.total_chunks,
                error=final_progress.error_message,
                processing_time=processing_time,
                rollback_available=final_progress.rollback_available,
                metadata={
                    "migration_id": migration_id,
                    "from_config": from_config,
                    "to_config": to_config,
                    "status": final_progress.status.value,
                    "phase": final_progress.phase.value
                }
            )
            
        except Exception as e:
            logger.error(f"Enhanced migration failed for bot {bot_id}: {e}")
            return MigrationResult(
                success=False,
                error=f"Migration system error: {str(e)}"
            )
    
    async def get_dimension_info(
        self,
        provider: str,
        model: str
    ) -> DimensionInfo:
        """
        Get embedding dimensions and compatibility information.
        
        Args:
            provider: Embedding provider
            model: Embedding model
            
        Returns:
            DimensionInfo with dimension and compatibility details
        """
        try:
            # Validate provider and model
            if not self.embedding_service.validate_model_for_provider(provider, model):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model '{model}' not available for provider '{provider}'"
                )
            
            # Get dimension
            dimension = self.embedding_service.get_embedding_dimension(provider, model)
            
            # Find compatible providers (same dimension)
            compatible_providers = []
            all_providers = self.embedding_service.get_supported_providers()
            
            for other_provider in all_providers:
                if other_provider == provider:
                    continue
                
                try:
                    other_models = self.embedding_service.get_available_models(other_provider)
                    for other_model in other_models:
                        try:
                            other_dimension = self.embedding_service.get_embedding_dimension(
                                other_provider, other_model
                            )
                            if other_dimension == dimension:
                                compatible_providers.append(f"{other_provider}/{other_model}")
                        except:
                            continue
                except:
                    continue
            
            return DimensionInfo(
                provider=provider,
                model=model,
                dimension=dimension,
                compatible_providers=compatible_providers,
                migration_required=False
            )
            
        except Exception as e:
            logger.error(f"Error getting dimension info for {provider}/{model}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get dimension info: {str(e)}"
            )
    
    async def get_migration_status(self, bot_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get current migration status for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Migration status information or None if no active migration
        """
        try:
            progress = await self.migration_system.get_bot_migration_status(bot_id)
            if not progress:
                return None
            
            # Convert to legacy format for backward compatibility
            return {
                "migration_id": progress.migration_id,
                "status": progress.status.value,
                "phase": progress.phase.value,
                "progress": {
                    "processed": progress.processed_chunks,
                    "total": progress.total_chunks,
                    "failed": progress.failed_chunks,
                    "current_batch": progress.current_batch,
                    "total_batches": progress.total_batches
                },
                "start_time": progress.start_time.timestamp(),
                "last_update": progress.last_update.timestamp(),
                "error_message": progress.error_message,
                "rollback_available": progress.rollback_available
            }
        except Exception as e:
            logger.error(f"Error getting migration status for bot {bot_id}: {e}")
            return None
    
    async def get_all_migration_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get migration statuses for all active migrations."""
        try:
            active_migrations = await self.migration_system.get_all_active_migrations()
            result = {}
            
            for progress in active_migrations:
                result[str(progress.bot_id)] = {
                    "migration_id": progress.migration_id,
                    "status": progress.status.value,
                    "phase": progress.phase.value,
                    "progress": {
                        "processed": progress.processed_chunks,
                        "total": progress.total_chunks,
                        "failed": progress.failed_chunks
                    },
                    "start_time": progress.start_time.timestamp(),
                    "last_update": progress.last_update.timestamp(),
                    "error_message": progress.error_message,
                    "rollback_available": progress.rollback_available
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting all migration statuses: {e}")
            return {}
    
    async def cancel_migration(self, bot_id: uuid.UUID) -> bool:
        """
        Cancel an active migration.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            True if migration was cancelled successfully
        """
        try:
            # Get current migration
            progress = await self.migration_system.get_bot_migration_status(bot_id)
            if not progress:
                return False
            
            # Cancel using migration system
            return await self.migration_system.cancel_migration(progress.migration_id)
            
        except Exception as e:
            logger.error(f"Error cancelling migration for bot {bot_id}: {e}")
            return False
    
    async def detect_dimension_mismatches(
        self,
        bot_ids: Optional[List[uuid.UUID]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect dimension mismatches in existing collections.
        
        Args:
            bot_ids: Optional list of bot IDs to check. If None, checks all bots.
            
        Returns:
            List of dictionaries with mismatch information
        """
        try:
            logger.info("Detecting dimension mismatches across collections")
            
            mismatches = await self.dimension_validator.detect_dimension_mismatches(bot_ids)
            
            # Convert to dictionary format for API response
            result = []
            for mismatch in mismatches:
                result.append({
                    "bot_id": mismatch.bot_id,
                    "collection_name": mismatch.collection_name,
                    "stored_dimension": mismatch.stored_dimension,
                    "configured_dimension": mismatch.configured_dimension,
                    "points_count": mismatch.points_count,
                    "dimension_mismatch": mismatch.dimension_mismatch,
                    "last_validated": mismatch.last_validated.isoformat() if mismatch.last_validated else None,
                    "metadata": mismatch.metadata
                })
            
            logger.info(f"Found {len(result)} dimension mismatches")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting dimension mismatches: {e}")
            return []
    
    async def validate_embedding_configuration_change(
        self,
        bot_id: uuid.UUID,
        new_provider: str,
        new_model: str,
        change_reason: Optional[str] = None
    ) -> CompatibilityResult:
        """
        Validate embedding configuration change with history tracking.
        
        Args:
            bot_id: Bot identifier
            new_provider: New embedding provider
            new_model: New embedding model
            change_reason: Optional reason for the change
            
        Returns:
            CompatibilityResult with validation details
        """
        try:
            logger.info(f"Validating configuration change for bot {bot_id}")
            
            # Use dimension validator for comprehensive validation
            validation_result = await self.dimension_validator.validate_embedding_configuration_change(
                bot_id, new_provider, new_model, change_reason
            )
            
            # Convert to CompatibilityResult format
            return CompatibilityResult(
                compatible=validation_result.is_valid,
                issues=validation_result.issues or [],
                recommendations=validation_result.recommendations or [],
                migration_required=not validation_result.dimension_match,
                current_config=validation_result.metadata.get("current_config") if validation_result.metadata else None,
                target_config=validation_result.metadata.get("target_config") if validation_result.metadata else None
            )
            
        except Exception as e:
            logger.error(f"Error validating configuration change for bot {bot_id}: {e}")
            return CompatibilityResult(
                compatible=False,
                issues=[f"Configuration validation error: {str(e)}"],
                recommendations=["Check bot configuration and try again"]
            )
    
    async def store_collection_metadata(
        self,
        bot_id: uuid.UUID,
        provider: str,
        model: str,
        dimension: int,
        points_count: int = 0
    ) -> bool:
        """
        Store collection metadata for dimension tracking.
        
        Args:
            bot_id: Bot identifier
            provider: Embedding provider
            model: Embedding model
            dimension: Embedding dimension
            points_count: Number of points in collection
            
        Returns:
            True if metadata was stored successfully
        """
        try:
            return await self.dimension_validator.store_collection_metadata(
                bot_id, provider, model, dimension, points_count
            )
        except Exception as e:
            logger.error(f"Error storing collection metadata for bot {bot_id}: {e}")
            return False
    
    async def get_collection_metadata(
        self,
        bot_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get collection metadata for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Dictionary with collection metadata or None if not found
        """
        try:
            return await self.dimension_validator.get_collection_metadata(bot_id)
        except Exception as e:
            logger.error(f"Error getting collection metadata for bot {bot_id}: {e}")
            return None
    
    async def close(self):
        """Close the compatibility manager and clean up resources."""
        try:
            # Close migration system (this will cancel active migrations)
            await self.migration_system.close()
            
            # Close dimension validator
            await self.dimension_validator.close()
            
            # Close configuration validator
            await self.configuration_validator.close()
            
            logger.info("Embedding Compatibility Manager closed successfully")
        except Exception as e:
            logger.error(f"Error closing Embedding Compatibility Manager: {e}")
    
    # Additional methods for enhanced migration system integration
    
    async def start_migration_with_progress(
        self,
        bot_id: uuid.UUID,
        to_provider: str,
        to_model: str,
        batch_size: int = 50
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Start migration and return migration ID and initial progress.
        
        Args:
            bot_id: Bot identifier
            to_provider: Target embedding provider
            to_model: Target embedding model
            batch_size: Batch size for processing
            
        Returns:
            Tuple of (migration_id, progress_dict)
        """
        try:
            # Create migration configuration
            migration_config = await self.migration_system.create_migration_config(
                bot_id=bot_id,
                to_provider=to_provider,
                to_model=to_model,
                batch_size=batch_size,
                enable_rollback=True
            )
            
            # Start migration
            migration_id, progress = await self.migration_system.start_migration(migration_config)
            
            # Convert progress to dictionary
            from .embedding_migration_system import format_migration_progress
            progress_dict = format_migration_progress(progress)
            
            return migration_id, progress_dict
            
        except Exception as e:
            logger.error(f"Failed to start migration with progress for bot {bot_id}: {e}")
            raise
    
    async def get_migration_progress_detailed(
        self,
        migration_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed migration progress by migration ID.
        
        Args:
            migration_id: Migration identifier
            
        Returns:
            Detailed progress dictionary or None if not found
        """
        try:
            progress = await self.migration_system.get_migration_progress(migration_id)
            if not progress:
                return None
            
            from .embedding_migration_system import format_migration_progress
            return format_migration_progress(progress)
            
        except Exception as e:
            logger.error(f"Error getting detailed migration progress for {migration_id}: {e}")
            return None
    
    async def rollback_migration(
        self,
        migration_id: str
    ) -> bool:
        """
        Manually trigger rollback for a migration.
        
        Args:
            migration_id: Migration identifier
            
        Returns:
            True if rollback was successful
        """
        try:
            return await self.migration_system.rollback_migration(migration_id)
        except Exception as e:
            logger.error(f"Error rolling back migration {migration_id}: {e}")
            return False
    
    async def estimate_migration_time(
        self,
        bot_id: uuid.UUID,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Estimate migration time for a bot.
        
        Args:
            bot_id: Bot identifier
            batch_size: Batch size for processing
            
        Returns:
            Dictionary with time estimates
        """
        try:
            from .embedding_migration_system import estimate_migration_time
            return await estimate_migration_time(self.db, bot_id, batch_size)
        except Exception as e:
            logger.error(f"Error estimating migration time for bot {bot_id}: {e}")
            return {
                "total_chunks": 0,
                "estimated_time_seconds": 0,
                "estimated_time_human": "Unable to estimate",
                "error": str(e)
            }