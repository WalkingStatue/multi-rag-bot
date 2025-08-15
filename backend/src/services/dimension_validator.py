"""
Dimension Validation Service - Handles embedding dimension compatibility checking and validation.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.collection_metadata import CollectionMetadata, EmbeddingConfigurationHistory, DimensionCompatibilityCache
from ..models.document import DocumentChunk
from .embedding_service import EmbeddingProviderService
from .vector_store import VectorService


logger = logging.getLogger(__name__)


@dataclass
class DimensionValidationResult:
    """Result of dimension validation."""
    is_valid: bool
    current_dimension: Optional[int] = None
    target_dimension: Optional[int] = None
    dimension_match: bool = False
    issues: List[str] = None
    recommendations: List[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CollectionDimensionInfo:
    """Information about collection dimensions."""
    bot_id: str
    collection_name: str
    stored_dimension: Optional[int] = None
    configured_dimension: Optional[int] = None
    points_count: int = 0
    dimension_mismatch: bool = False
    last_validated: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompatibilityMatrix:
    """Matrix of provider/model compatibility information."""
    provider_models: Dict[str, List[str]]
    dimension_map: Dict[Tuple[str, str], int]  # (provider, model) -> dimension
    compatible_groups: Dict[int, List[Tuple[str, str]]]  # dimension -> [(provider, model)]
    last_updated: datetime


class DimensionMismatchType(Enum):
    """Types of dimension mismatches."""
    NO_MISMATCH = "no_mismatch"
    CONFIG_VS_STORED = "config_vs_stored"
    MODEL_CHANGED = "model_changed"
    PROVIDER_CHANGED = "provider_changed"
    COLLECTION_CORRUPTED = "collection_corrupted"


class DimensionValidator:
    """
    Service for validating embedding dimensions and detecting compatibility issues.
    
    This service handles:
    - Dimension compatibility checking between providers/models
    - Automatic detection of dimension mismatches in existing collections
    - Validation of embedding configuration changes
    - Dimension metadata storage and retrieval
    """
    
    def __init__(self, db: Session):
        """
        Initialize Dimension Validator.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = EmbeddingProviderService()
        self.vector_service = VectorService()
        
        # Cache configuration
        self.cache_ttl = timedelta(hours=24)  # Cache dimension info for 24 hours
        self.validation_batch_size = 50
        
        # Compatibility matrix cache
        self._compatibility_matrix: Optional[CompatibilityMatrix] = None
        self._matrix_last_updated: Optional[datetime] = None
        self._matrix_cache_ttl = timedelta(hours=6)
    
    async def validate_dimension_compatibility(
        self,
        bot_id: uuid.UUID,
        target_provider: str,
        target_model: str
    ) -> DimensionValidationResult:
        """
        Validate dimension compatibility for a bot's embedding configuration change.
        
        Args:
            bot_id: Bot identifier
            target_provider: Target embedding provider
            target_model: Target embedding model
            
        Returns:
            DimensionValidationResult with validation details
        """
        try:
            logger.info(f"Validating dimension compatibility for bot {bot_id}: {target_provider}/{target_model}")
            
            # Get bot and current configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return DimensionValidationResult(
                    is_valid=False,
                    issues=["Bot not found"],
                    recommendations=[]
                )
            
            issues = []
            recommendations = []
            metadata = {}
            
            # Validate target provider and model
            if not self.embedding_service.validate_model_for_provider(target_provider, target_model):
                available_models = self.embedding_service.get_available_models(target_provider)
                issues.append(f"Model '{target_model}' is not available for provider '{target_provider}'")
                if available_models:
                    recommendations.append(f"Available models for {target_provider}: {', '.join(available_models[:5])}")
                return DimensionValidationResult(
                    is_valid=False,
                    issues=issues,
                    recommendations=recommendations
                )
            
            # Get dimensions
            try:
                current_dimension = self.embedding_service.get_embedding_dimension(
                    bot.embedding_provider, bot.embedding_model
                )
                target_dimension = self.embedding_service.get_embedding_dimension(
                    target_provider, target_model
                )
                
                metadata.update({
                    "current_config": {
                        "provider": bot.embedding_provider,
                        "model": bot.embedding_model,
                        "dimension": current_dimension
                    },
                    "target_config": {
                        "provider": target_provider,
                        "model": target_model,
                        "dimension": target_dimension
                    }
                })
                
            except Exception as e:
                issues.append(f"Failed to get dimension information: {str(e)}")
                return DimensionValidationResult(
                    is_valid=False,
                    issues=issues,
                    recommendations=["Check provider and model configuration"]
                )
            
            # Check dimension compatibility
            dimension_match = current_dimension == target_dimension
            
            if not dimension_match:
                issues.append(f"Dimension mismatch: current={current_dimension}, target={target_dimension}")
                recommendations.append("Migration will be required to change embedding dimensions")
                recommendations.append("All existing documents will need to be reprocessed")
            
            # Check collection status
            collection_info = await self._get_collection_dimension_info(bot_id)
            if collection_info:
                metadata["collection_info"] = {
                    "stored_dimension": collection_info.stored_dimension,
                    "points_count": collection_info.points_count,
                    "dimension_mismatch": collection_info.dimension_mismatch
                }
                
                if collection_info.dimension_mismatch:
                    issues.append("Existing collection has dimension mismatch with current configuration")
                    recommendations.append("Consider running collection validation and repair")
                
                if collection_info.points_count > 0 and not dimension_match:
                    recommendations.append(f"Migration will affect {collection_info.points_count} existing embeddings")
            
            # Find compatible alternatives if dimensions don't match
            if not dimension_match:
                compatible_models = await self._find_compatible_models(current_dimension)
                if compatible_models:
                    compatible_list = [f"{p}/{m}" for p, m in compatible_models[:3]]
                    recommendations.append(f"Compatible alternatives with same dimension: {', '.join(compatible_list)}")
            
            # Determine overall validation result
            is_valid = len([issue for issue in issues if "not available" in issue or "Failed to get" in issue]) == 0
            
            result = DimensionValidationResult(
                is_valid=is_valid,
                current_dimension=current_dimension,
                target_dimension=target_dimension,
                dimension_match=dimension_match,
                issues=issues,
                recommendations=recommendations,
                metadata=metadata
            )
            
            logger.info(f"Dimension validation for bot {bot_id}: valid={is_valid}, match={dimension_match}")
            return result
            
        except Exception as e:
            logger.error(f"Error validating dimension compatibility for bot {bot_id}: {e}")
            return DimensionValidationResult(
                is_valid=False,
                issues=[f"Validation error: {str(e)}"],
                recommendations=["Check bot configuration and try again"]
            )
    
    async def detect_dimension_mismatches(
        self,
        bot_ids: Optional[List[uuid.UUID]] = None
    ) -> List[CollectionDimensionInfo]:
        """
        Automatically detect dimension mismatches in existing collections.
        
        Args:
            bot_ids: Optional list of bot IDs to check. If None, checks all bots.
            
        Returns:
            List of CollectionDimensionInfo with mismatch details
        """
        try:
            logger.info(f"Detecting dimension mismatches for {len(bot_ids) if bot_ids else 'all'} bots")
            
            # Get bots to check
            if bot_ids:
                bots = self.db.query(Bot).filter(Bot.id.in_(bot_ids)).all()
            else:
                bots = self.db.query(Bot).all()
            
            mismatches = []
            
            # Process bots in batches
            for i in range(0, len(bots), self.validation_batch_size):
                batch = bots[i:i + self.validation_batch_size]
                batch_tasks = []
                
                for bot in batch:
                    task = self._check_bot_dimension_consistency(bot)
                    batch_tasks.append(task)
                
                # Process batch concurrently
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for bot, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Error checking bot {bot.id}: {result}")
                        continue
                    
                    if result and result.dimension_mismatch:
                        mismatches.append(result)
            
            logger.info(f"Found {len(mismatches)} dimension mismatches")
            return mismatches
            
        except Exception as e:
            logger.error(f"Error detecting dimension mismatches: {e}")
            return []
    
    async def _check_bot_dimension_consistency(self, bot: Bot) -> Optional[CollectionDimensionInfo]:
        """
        Check dimension consistency for a single bot.
        
        Args:
            bot: Bot instance to check
            
        Returns:
            CollectionDimensionInfo if mismatch found, None otherwise
        """
        try:
            collection_name = str(bot.id)
            
            # Get configured dimension
            try:
                configured_dimension = self.embedding_service.get_embedding_dimension(
                    bot.embedding_provider, bot.embedding_model
                )
            except Exception as e:
                logger.warning(f"Could not get configured dimension for bot {bot.id}: {e}")
                configured_dimension = None
            
            # Get stored dimension from vector collection
            stored_dimension = None
            points_count = 0
            
            try:
                if await self.vector_service.vector_store.collection_exists(collection_name):
                    collection_stats = await self.vector_service.get_bot_collection_stats(collection_name)
                    stored_dimension = collection_stats.get('config', {}).get('vector_size')
                    points_count = collection_stats.get('points_count', 0)
            except Exception as e:
                logger.warning(f"Could not get stored dimension for bot {bot.id}: {e}")
            
            # Check for mismatches
            dimension_mismatch = False
            mismatch_type = DimensionMismatchType.NO_MISMATCH
            
            if configured_dimension and stored_dimension:
                if configured_dimension != stored_dimension:
                    dimension_mismatch = True
                    mismatch_type = DimensionMismatchType.CONFIG_VS_STORED
            elif configured_dimension and not stored_dimension and points_count > 0:
                dimension_mismatch = True
                mismatch_type = DimensionMismatchType.COLLECTION_CORRUPTED
            
            # Get collection metadata
            collection_metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot.id
            ).first()
            
            metadata = {
                "mismatch_type": mismatch_type.value,
                "bot_config": {
                    "provider": bot.embedding_provider,
                    "model": bot.embedding_model
                },
                "has_metadata": collection_metadata is not None
            }
            
            if collection_metadata:
                metadata["metadata_dimension"] = collection_metadata.embedding_dimension
                metadata["metadata_updated"] = collection_metadata.last_updated.isoformat()
            
            return CollectionDimensionInfo(
                bot_id=str(bot.id),
                collection_name=collection_name,
                stored_dimension=stored_dimension,
                configured_dimension=configured_dimension,
                points_count=points_count,
                dimension_mismatch=dimension_mismatch,
                last_validated=datetime.utcnow(),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error checking dimension consistency for bot {bot.id}: {e}")
            return None
    
    async def validate_embedding_configuration_change(
        self,
        bot_id: uuid.UUID,
        new_provider: str,
        new_model: str,
        change_reason: Optional[str] = None
    ) -> DimensionValidationResult:
        """
        Validate embedding configuration change and record in history.
        
        Args:
            bot_id: Bot identifier
            new_provider: New embedding provider
            new_model: New embedding model
            change_reason: Optional reason for the change
            
        Returns:
            DimensionValidationResult with validation details
        """
        try:
            logger.info(f"Validating configuration change for bot {bot_id}: {new_provider}/{new_model}")
            
            # Perform dimension validation
            validation_result = await self.validate_dimension_compatibility(
                bot_id, new_provider, new_model
            )
            
            if not validation_result.is_valid:
                return validation_result
            
            # Get current configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return DimensionValidationResult(
                    is_valid=False,
                    issues=["Bot not found"]
                )
            
            # Record configuration change in history
            try:
                current_dimension = self.embedding_service.get_embedding_dimension(
                    bot.embedding_provider, bot.embedding_model
                )
                new_dimension = self.embedding_service.get_embedding_dimension(
                    new_provider, new_model
                )
                
                config_history = EmbeddingConfigurationHistory(
                    bot_id=bot_id,
                    previous_provider=bot.embedding_provider,
                    previous_model=bot.embedding_model,
                    previous_dimension=current_dimension,
                    new_provider=new_provider,
                    new_model=new_model,
                    new_dimension=new_dimension,
                    change_reason=change_reason,
                    migration_required=not validation_result.dimension_match,
                    metadata={
                        "validation_result": {
                            "dimension_match": validation_result.dimension_match,
                            "issues_count": len(validation_result.issues or []),
                            "recommendations_count": len(validation_result.recommendations or [])
                        }
                    }
                )
                
                self.db.add(config_history)
                self.db.commit()
                
                logger.info(f"Recorded configuration change history for bot {bot_id}")
                
            except Exception as e:
                logger.error(f"Failed to record configuration history for bot {bot_id}: {e}")
                # Don't fail validation due to history recording error
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating configuration change for bot {bot_id}: {e}")
            return DimensionValidationResult(
                is_valid=False,
                issues=[f"Configuration validation error: {str(e)}"]
            )
    
    async def store_collection_metadata(
        self,
        bot_id: uuid.UUID,
        provider: str,
        model: str,
        dimension: int,
        points_count: int = 0,
        status: str = "active"
    ) -> bool:
        """
        Store or update collection metadata.
        
        Args:
            bot_id: Bot identifier
            provider: Embedding provider
            model: Embedding model
            dimension: Embedding dimension
            points_count: Number of points in collection
            status: Collection status
            
        Returns:
            True if metadata was stored successfully
        """
        try:
            logger.debug(f"Storing collection metadata for bot {bot_id}")
            
            # Check if metadata already exists
            existing_metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot_id
            ).first()
            
            if existing_metadata:
                # Update existing metadata
                existing_metadata.embedding_provider = provider
                existing_metadata.embedding_model = model
                existing_metadata.embedding_dimension = dimension
                existing_metadata.points_count = points_count
                existing_metadata.status = status
                existing_metadata.last_updated = datetime.utcnow()
                
                # Update configuration history
                if existing_metadata.configuration_history is None:
                    existing_metadata.configuration_history = []
                
                existing_metadata.configuration_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "provider": provider,
                    "model": model,
                    "dimension": dimension,
                    "points_count": points_count,
                    "status": status
                })
                
            else:
                # Create new metadata
                new_metadata = CollectionMetadata(
                    bot_id=bot_id,
                    collection_name=str(bot_id),
                    embedding_provider=provider,
                    embedding_model=model,
                    embedding_dimension=dimension,
                    points_count=points_count,
                    status=status,
                    configuration_history=[{
                        "timestamp": datetime.utcnow().isoformat(),
                        "provider": provider,
                        "model": model,
                        "dimension": dimension,
                        "points_count": points_count,
                        "status": status,
                        "initial": True
                    }]
                )
                
                self.db.add(new_metadata)
            
            self.db.commit()
            logger.debug(f"Successfully stored collection metadata for bot {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing collection metadata for bot {bot_id}: {e}")
            self.db.rollback()
            return False
    
    async def get_collection_metadata(
        self,
        bot_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve collection metadata for a bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            Dictionary with collection metadata or None if not found
        """
        try:
            metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot_id
            ).first()
            
            if not metadata:
                return None
            
            return {
                "bot_id": str(metadata.bot_id),
                "collection_name": metadata.collection_name,
                "embedding_provider": metadata.embedding_provider,
                "embedding_model": metadata.embedding_model,
                "embedding_dimension": metadata.embedding_dimension,
                "status": metadata.status,
                "points_count": metadata.points_count,
                "last_updated": metadata.last_updated.isoformat(),
                "created_at": metadata.created_at.isoformat(),
                "configuration_history": metadata.configuration_history or [],
                "migration_info": metadata.migration_info or {}
            }
            
        except Exception as e:
            logger.error(f"Error retrieving collection metadata for bot {bot_id}: {e}")
            return None
    
    async def _get_collection_dimension_info(
        self,
        bot_id: uuid.UUID
    ) -> Optional[CollectionDimensionInfo]:
        """
        Get dimension information for a collection.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            CollectionDimensionInfo or None if collection doesn't exist
        """
        try:
            collection_name = str(bot_id)
            
            # Check if collection exists
            if not await self.vector_service.vector_store.collection_exists(collection_name):
                return None
            
            # Get collection stats
            collection_stats = await self.vector_service.get_bot_collection_stats(collection_name)
            stored_dimension = collection_stats.get('config', {}).get('vector_size')
            points_count = collection_stats.get('points_count', 0)
            
            # Get configured dimension
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            configured_dimension = None
            
            if bot:
                try:
                    configured_dimension = self.embedding_service.get_embedding_dimension(
                        bot.embedding_provider, bot.embedding_model
                    )
                except Exception:
                    pass
            
            # Check for mismatch
            dimension_mismatch = (
                stored_dimension is not None and 
                configured_dimension is not None and 
                stored_dimension != configured_dimension
            )
            
            return CollectionDimensionInfo(
                bot_id=str(bot_id),
                collection_name=collection_name,
                stored_dimension=stored_dimension,
                configured_dimension=configured_dimension,
                points_count=points_count,
                dimension_mismatch=dimension_mismatch,
                last_validated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting collection dimension info for bot {bot_id}: {e}")
            return None
    
    async def _find_compatible_models(
        self,
        target_dimension: int
    ) -> List[Tuple[str, str]]:
        """
        Find provider/model combinations with the specified dimension.
        
        Args:
            target_dimension: Target embedding dimension
            
        Returns:
            List of (provider, model) tuples with matching dimension
        """
        try:
            compatible_models = []
            
            # Get compatibility matrix
            matrix = await self._get_compatibility_matrix()
            
            # Find models with matching dimension
            if target_dimension in matrix.compatible_groups:
                compatible_models = matrix.compatible_groups[target_dimension]
            
            return compatible_models
            
        except Exception as e:
            logger.error(f"Error finding compatible models for dimension {target_dimension}: {e}")
            return []
    
    async def _get_compatibility_matrix(self) -> CompatibilityMatrix:
        """
        Get or build the provider/model compatibility matrix.
        
        Returns:
            CompatibilityMatrix with current compatibility information
        """
        try:
            current_time = datetime.utcnow()
            
            # Check if cached matrix is still valid
            if (self._compatibility_matrix and 
                self._matrix_last_updated and 
                current_time - self._matrix_last_updated < self._matrix_cache_ttl):
                return self._compatibility_matrix
            
            logger.info("Building compatibility matrix")
            
            # Build new matrix
            provider_models = {}
            dimension_map = {}
            compatible_groups = {}
            
            # Get all supported providers
            providers = self.embedding_service.get_supported_providers()
            
            for provider in providers:
                try:
                    models = self.embedding_service.get_available_models(provider)
                    provider_models[provider] = models
                    
                    for model in models:
                        try:
                            dimension = self.embedding_service.get_embedding_dimension(provider, model)
                            dimension_map[(provider, model)] = dimension
                            
                            # Group by dimension
                            if dimension not in compatible_groups:
                                compatible_groups[dimension] = []
                            compatible_groups[dimension].append((provider, model))
                            
                        except Exception as e:
                            logger.warning(f"Could not get dimension for {provider}/{model}: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Could not get models for provider {provider}: {e}")
                    continue
            
            # Create matrix
            matrix = CompatibilityMatrix(
                provider_models=provider_models,
                dimension_map=dimension_map,
                compatible_groups=compatible_groups,
                last_updated=current_time
            )
            
            # Cache matrix
            self._compatibility_matrix = matrix
            self._matrix_last_updated = current_time
            
            logger.info(f"Built compatibility matrix with {len(dimension_map)} provider/model combinations")
            return matrix
            
        except Exception as e:
            logger.error(f"Error building compatibility matrix: {e}")
            # Return empty matrix as fallback
            return CompatibilityMatrix(
                provider_models={},
                dimension_map={},
                compatible_groups={},
                last_updated=datetime.utcnow()
            )
    
    async def cache_dimension_info(
        self,
        provider: str,
        model: str,
        dimension: int,
        is_valid: bool = True,
        validation_error: Optional[str] = None
    ) -> bool:
        """
        Cache dimension information for a provider/model combination.
        
        Args:
            provider: Embedding provider
            model: Embedding model
            dimension: Embedding dimension
            is_valid: Whether the provider/model combination is valid
            validation_error: Optional validation error message
            
        Returns:
            True if cached successfully
        """
        try:
            # Check if cache entry exists
            existing_cache = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == provider,
                    DimensionCompatibilityCache.model == model
                )
            ).first()
            
            if existing_cache:
                # Update existing cache
                existing_cache.dimension = dimension
                existing_cache.is_valid = is_valid
                existing_cache.validation_error = validation_error
                existing_cache.last_validated = datetime.utcnow()
                existing_cache.updated_at = datetime.utcnow()
            else:
                # Create new cache entry
                new_cache = DimensionCompatibilityCache(
                    provider=provider,
                    model=model,
                    dimension=dimension,
                    is_valid=is_valid,
                    validation_error=validation_error
                )
                self.db.add(new_cache)
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error caching dimension info for {provider}/{model}: {e}")
            self.db.rollback()
            return False
    
    async def get_cached_dimension_info(
        self,
        provider: str,
        model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached dimension information for a provider/model combination.
        
        Args:
            provider: Embedding provider
            model: Embedding model
            
        Returns:
            Dictionary with cached dimension info or None if not found/expired
        """
        try:
            cache_entry = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == provider,
                    DimensionCompatibilityCache.model == model
                )
            ).first()
            
            if not cache_entry:
                return None
            
            # Check if cache is expired
            if datetime.utcnow() - cache_entry.last_validated > self.cache_ttl:
                return None
            
            return {
                "provider": cache_entry.provider,
                "model": cache_entry.model,
                "dimension": cache_entry.dimension,
                "is_valid": cache_entry.is_valid,
                "validation_error": cache_entry.validation_error,
                "last_validated": cache_entry.last_validated.isoformat(),
                "cached": True
            }
            
        except Exception as e:
            logger.error(f"Error getting cached dimension info for {provider}/{model}: {e}")
            return None
    
    async def cleanup_expired_cache(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            cutoff_time = datetime.utcnow() - self.cache_ttl
            
            expired_entries = self.db.query(DimensionCompatibilityCache).filter(
                DimensionCompatibilityCache.last_validated < cutoff_time
            )
            
            count = expired_entries.count()
            expired_entries.delete()
            self.db.commit()
            
            logger.info(f"Cleaned up {count} expired dimension cache entries")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            self.db.rollback()
            return 0
    
    async def close(self):
        """Close the dimension validator and clean up resources."""
        try:
            await self.embedding_service.close()
            logger.info("Dimension Validator closed successfully")
        except Exception as e:
            logger.error(f"Error closing Dimension Validator: {e}")