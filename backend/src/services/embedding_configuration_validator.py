"""
Embedding Configuration Validator - Comprehensive validation for provider/model combinations.

This service provides:
- Comprehensive validation for provider/model combinations
- Metadata storage for collection dimensions and configuration history
- Compatibility checking before allowing configuration changes
- Validation reports with specific remediation steps
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.collection_metadata import (
    CollectionMetadata, 
    EmbeddingConfigurationHistory, 
    DimensionCompatibilityCache
)
from ..models.document import DocumentChunk
from .embedding_service import EmbeddingProviderService
from .user_service import UserService


logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue with severity and remediation."""
    severity: ValidationSeverity
    code: str
    message: str
    remediation: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report with issues and recommendations."""
    is_valid: bool
    provider: str
    model: str
    dimension: int
    issues: List[ValidationIssue]
    recommendations: List[str]
    compatibility_score: float  # 0.0 to 1.0
    migration_required: bool
    estimated_migration_time: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProviderModelInfo:
    """Information about a provider/model combination."""
    provider: str
    model: str
    dimension: int
    is_available: bool
    last_validated: Optional[datetime]
    validation_error: Optional[str] = None
    api_requirements: Optional[Dict[str, Any]] = None


class EmbeddingConfigurationValidator:
    """
    Comprehensive embedding configuration validator.
    
    Provides validation for provider/model combinations, metadata management,
    and compatibility checking with detailed remediation guidance.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the configuration validator.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = EmbeddingProviderService()
        self.user_service = UserService(db)
        
        # Cache settings
        self.cache_ttl = timedelta(hours=24)  # Cache validation results for 24 hours
        self.validation_timeout = 30  # seconds
        
        # Validation thresholds
        self.min_compatibility_score = 0.7
        self.max_dimension_difference = 0.1  # 10% difference threshold 
   
    async def validate_provider_model_combination(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        use_cache: bool = True
    ) -> ValidationReport:
        """
        Validate a provider/model combination comprehensively.
        
        Args:
            provider: Embedding provider name
            model: Embedding model name
            api_key: Optional API key for validation
            use_cache: Whether to use cached validation results
            
        Returns:
            ValidationReport with comprehensive validation results
        """
        try:
            logger.info(f"Validating provider/model combination: {provider}/{model}")
            
            issues = []
            recommendations = []
            compatibility_score = 1.0
            
            # Check if provider is supported
            supported_providers = self.embedding_service.get_supported_providers()
            if provider not in supported_providers:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="UNSUPPORTED_PROVIDER",
                    message=f"Provider '{provider}' is not supported",
                    remediation=f"Use one of the supported providers: {', '.join(supported_providers)}"
                ))
                compatibility_score = 0.0
            
            # Check cached validation if requested
            if use_cache and compatibility_score > 0:
                cached_result = await self._get_cached_validation(provider, model)
                if cached_result:
                    logger.debug(f"Using cached validation for {provider}/{model}")
                    return cached_result
            
            # Validate model availability
            if compatibility_score > 0:
                available_models = self.embedding_service.get_available_models(provider)
                if model not in available_models:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="UNSUPPORTED_MODEL",
                        message=f"Model '{model}' is not available for provider '{provider}'",
                        remediation=f"Use one of the available models: {', '.join(available_models[:5])}{'...' if len(available_models) > 5 else ''}"
                    ))
                    compatibility_score *= 0.5
            
            # Get dimension information
            dimension = 0
            if compatibility_score > 0:
                try:
                    dimension = self.embedding_service.get_embedding_dimension(provider, model)
                    logger.debug(f"Dimension for {provider}/{model}: {dimension}")
                except Exception as e:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="DIMENSION_UNKNOWN",
                        message=f"Could not determine embedding dimension: {str(e)}",
                        remediation="Verify model name and provider configuration"
                    ))
                    compatibility_score *= 0.8
            
            # Validate API key if provided
            if api_key and compatibility_score > 0:
                try:
                    key_valid = await asyncio.wait_for(
                        self.embedding_service.validate_api_key(provider, api_key),
                        timeout=self.validation_timeout
                    )
                    if not key_valid:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_API_KEY",
                            message=f"API key is invalid for provider '{provider}'",
                            remediation=f"Update your API key for {provider} in user settings"
                        ))
                        compatibility_score *= 0.3
                except asyncio.TimeoutError:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="API_KEY_TIMEOUT",
                        message="API key validation timed out",
                        remediation="Check network connectivity and try again"
                    ))
                    compatibility_score *= 0.9
                except Exception as e:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="API_KEY_ERROR",
                        message=f"Could not validate API key: {str(e)}",
                        remediation="Verify API key format and provider configuration"
                    ))
                    compatibility_score *= 0.8
            
            # Generate recommendations based on issues
            if not issues:
                recommendations.append(f"Configuration {provider}/{model} is fully compatible")
            else:
                error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
                warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)
                
                if error_count > 0:
                    recommendations.append(f"Fix {error_count} critical error(s) before using this configuration")
                if warning_count > 0:
                    recommendations.append(f"Consider addressing {warning_count} warning(s) for optimal performance")
            
            # Create validation report
            report = ValidationReport(
                is_valid=compatibility_score >= self.min_compatibility_score and not any(
                    issue.severity == ValidationSeverity.ERROR for issue in issues
                ),
                provider=provider,
                model=model,
                dimension=dimension,
                issues=issues,
                recommendations=recommendations,
                compatibility_score=compatibility_score,
                migration_required=False,  # Will be determined by caller
                metadata={
                    "validation_timestamp": datetime.utcnow().isoformat(),
                    "cache_used": False,
                    "timeout_seconds": self.validation_timeout
                }
            )
            
            # Cache the validation result
            if use_cache:
                await self._cache_validation_result(report)
            
            logger.info(f"Validation complete for {provider}/{model}: valid={report.is_valid}, score={compatibility_score:.2f}")
            return report
            
        except Exception as e:
            logger.error(f"Error validating provider/model {provider}/{model}: {e}")
            return ValidationReport(
                is_valid=False,
                provider=provider,
                model=model,
                dimension=0,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VALIDATION_ERROR",
                    message=f"Validation failed: {str(e)}",
                    remediation="Check configuration and try again"
                )],
                recommendations=["Resolve validation error and retry"],
                compatibility_score=0.0,
                migration_required=False
            )
    
    async def validate_configuration_change(
        self,
        bot_id: uuid.UUID,
        new_provider: str,
        new_model: str,
        change_reason: Optional[str] = None
    ) -> ValidationReport:
        """
        Validate embedding configuration change for a bot.
        
        Args:
            bot_id: Bot identifier
            new_provider: New embedding provider
            new_model: New embedding model
            change_reason: Optional reason for the change
            
        Returns:
            ValidationReport with change-specific validation
        """
        try:
            logger.info(f"Validating configuration change for bot {bot_id}: {new_provider}/{new_model}")
            
            # Get bot and current configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                return ValidationReport(
                    is_valid=False,
                    provider=new_provider,
                    model=new_model,
                    dimension=0,
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="BOT_NOT_FOUND",
                        message="Bot not found",
                        remediation="Verify bot ID and permissions"
                    )],
                    recommendations=["Check bot exists and you have access"],
                    compatibility_score=0.0,
                    migration_required=False
                )
            
            # Get API key for validation
            api_key = None
            try:
                api_key = self.user_service.get_user_api_key(bot.owner_id, new_provider)
            except Exception as e:
                logger.warning(f"Could not get API key for {new_provider}: {e}")
            
            # Validate the new configuration
            report = await self.validate_provider_model_combination(
                new_provider, new_model, api_key
            )
            
            # Add change-specific validation
            current_provider = bot.embedding_provider or "openai"
            current_model = bot.embedding_model or "text-embedding-3-small"
            
            # Check if change is necessary
            if current_provider == new_provider and current_model == new_model:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="NO_CHANGE_NEEDED",
                    message="Configuration is already set to the specified values",
                    remediation="No action needed unless you want to refresh the configuration"
                ))
            
            # Check dimension compatibility
            if report.is_valid and report.dimension > 0:
                try:
                    current_dimension = self.embedding_service.get_embedding_dimension(
                        current_provider, current_model
                    )
                    
                    if current_dimension != report.dimension:
                        report.migration_required = True
                        
                        # Estimate migration impact
                        chunk_count = self.db.query(DocumentChunk).filter(
                            DocumentChunk.bot_id == bot_id
                        ).count()
                        
                        if chunk_count > 0:
                            estimated_time = self._estimate_migration_time(chunk_count)
                            report.estimated_migration_time = estimated_time
                            
                            report.issues.append(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                code="MIGRATION_REQUIRED",
                                message=f"Dimension change from {current_dimension} to {report.dimension} requires migration of {chunk_count} chunks",
                                remediation=f"Plan for migration downtime (estimated: {estimated_time})",
                                metadata={
                                    "chunk_count": chunk_count,
                                    "current_dimension": current_dimension,
                                    "new_dimension": report.dimension
                                }
                            ))
                            
                            report.recommendations.append(
                                f"Schedule migration during low-usage period (estimated time: {estimated_time})"
                            )
                        else:
                            report.recommendations.append("No existing data to migrate")
                    
                except Exception as e:
                    logger.warning(f"Could not check dimension compatibility: {e}")
                    report.issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="DIMENSION_CHECK_FAILED",
                        message="Could not verify dimension compatibility with current configuration",
                        remediation="Proceed with caution and monitor for issues"
                    ))
            
            # Store configuration change history
            if report.is_valid:
                await self._store_configuration_history(
                    bot_id, current_provider, current_model, 
                    new_provider, new_model, change_reason, report.migration_required
                )
            
            # Update metadata
            report.metadata.update({
                "bot_id": str(bot_id),
                "current_config": {
                    "provider": current_provider,
                    "model": current_model
                },
                "target_config": {
                    "provider": new_provider,
                    "model": new_model
                },
                "change_reason": change_reason
            })
            
            logger.info(f"Configuration change validation complete for bot {bot_id}: valid={report.is_valid}, migration_required={report.migration_required}")
            return report
            
        except Exception as e:
            logger.error(f"Error validating configuration change for bot {bot_id}: {e}")
            return ValidationReport(
                is_valid=False,
                provider=new_provider,
                model=new_model,
                dimension=0,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CHANGE_VALIDATION_ERROR",
                    message=f"Configuration change validation failed: {str(e)}",
                    remediation="Check bot configuration and try again"
                )],
                recommendations=["Resolve validation error and retry"],
                compatibility_score=0.0,
                migration_required=False
            )    

    async def get_provider_model_info(
        self,
        provider: str,
        model: str,
        refresh_cache: bool = False
    ) -> ProviderModelInfo:
        """
        Get comprehensive information about a provider/model combination.
        
        Args:
            provider: Embedding provider name
            model: Embedding model name
            refresh_cache: Whether to refresh cached information
            
        Returns:
            ProviderModelInfo with detailed information
        """
        try:
            # Check cache first
            if not refresh_cache:
                cached_info = await self._get_cached_provider_info(provider, model)
                if cached_info:
                    return cached_info
            
            # Validate and get fresh information
            report = await self.validate_provider_model_combination(
                provider, model, use_cache=False
            )
            
            # Get API requirements
            api_requirements = None
            try:
                provider_info = self.embedding_service.get_provider_info(provider)
                api_requirements = {
                    "requires_api_key": provider_info.get("requires_api_key", True),
                    "base_url": provider_info.get("base_url"),
                    "default_config": provider_info.get("default_config", {})
                }
            except Exception as e:
                logger.warning(f"Could not get API requirements for {provider}: {e}")
            
            info = ProviderModelInfo(
                provider=provider,
                model=model,
                dimension=report.dimension,
                is_available=report.is_valid,
                last_validated=datetime.utcnow(),
                validation_error=report.issues[0].message if report.issues else None,
                api_requirements=api_requirements
            )
            
            # Cache the information
            await self._cache_provider_info(info)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting provider/model info for {provider}/{model}: {e}")
            return ProviderModelInfo(
                provider=provider,
                model=model,
                dimension=0,
                is_available=False,
                last_validated=datetime.utcnow(),
                validation_error=str(e)
            )
    
    async def get_compatible_alternatives(
        self,
        target_dimension: int,
        exclude_provider: Optional[str] = None,
        exclude_model: Optional[str] = None
    ) -> List[ProviderModelInfo]:
        """
        Get compatible provider/model alternatives with the same dimension.
        
        Args:
            target_dimension: Target embedding dimension
            exclude_provider: Provider to exclude from results
            exclude_model: Model to exclude from results
            
        Returns:
            List of compatible ProviderModelInfo objects
        """
        try:
            logger.info(f"Finding compatible alternatives for dimension {target_dimension}")
            
            alternatives = []
            all_providers = self.embedding_service.get_all_providers_info()
            
            for provider_name, provider_info in all_providers.items():
                if exclude_provider and provider_name == exclude_provider:
                    continue
                
                model_dimensions = provider_info.get("model_dimensions", {})
                for model_name, dimension in model_dimensions.items():
                    if exclude_model and model_name == exclude_model:
                        continue
                    
                    if dimension == target_dimension:
                        info = await self.get_provider_model_info(provider_name, model_name)
                        if info.is_available:
                            alternatives.append(info)
            
            # Sort by provider preference (OpenAI first, then others)
            alternatives.sort(key=lambda x: (
                0 if x.provider == "openai" else 1,
                x.provider,
                x.model
            ))
            
            logger.info(f"Found {len(alternatives)} compatible alternatives for dimension {target_dimension}")
            return alternatives
            
        except Exception as e:
            logger.error(f"Error finding compatible alternatives for dimension {target_dimension}: {e}")
            return []   
 
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
        Store or update collection metadata for a bot.
        
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
            logger.info(f"Storing collection metadata for bot {bot_id}: {provider}/{model} (dim: {dimension})")
            
            # Get or create collection metadata
            metadata = self.db.query(CollectionMetadata).filter(
                CollectionMetadata.bot_id == bot_id
            ).first()
            
            if metadata:
                # Update existing metadata
                metadata.embedding_provider = provider
                metadata.embedding_model = model
                metadata.embedding_dimension = dimension
                metadata.points_count = points_count
                metadata.status = status
                metadata.last_updated = datetime.utcnow()
            else:
                # Create new metadata
                metadata = CollectionMetadata(
                    bot_id=bot_id,
                    collection_name=f"bot_{bot_id}",
                    embedding_provider=provider,
                    embedding_model=model,
                    embedding_dimension=dimension,
                    points_count=points_count,
                    status=status
                )
                self.db.add(metadata)
            
            self.db.commit()
            logger.info(f"Collection metadata stored successfully for bot {bot_id}")
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
        Get collection metadata for a bot.
        
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
                "configuration_history": metadata.configuration_history,
                "migration_info": metadata.migration_info
            }
            
        except Exception as e:
            logger.error(f"Error getting collection metadata for bot {bot_id}: {e}")
            return None
    
    async def get_configuration_history(
        self,
        bot_id: uuid.UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get configuration change history for a bot.
        
        Args:
            bot_id: Bot identifier
            limit: Maximum number of history entries to return
            
        Returns:
            List of configuration history entries
        """
        try:
            history = self.db.query(EmbeddingConfigurationHistory).filter(
                EmbeddingConfigurationHistory.bot_id == bot_id
            ).order_by(desc(EmbeddingConfigurationHistory.changed_at)).limit(limit).all()
            
            result = []
            for entry in history:
                result.append({
                    "id": str(entry.id),
                    "bot_id": str(entry.bot_id),
                    "previous_provider": entry.previous_provider,
                    "previous_model": entry.previous_model,
                    "previous_dimension": entry.previous_dimension,
                    "new_provider": entry.new_provider,
                    "new_model": entry.new_model,
                    "new_dimension": entry.new_dimension,
                    "change_reason": entry.change_reason,
                    "migration_required": entry.migration_required,
                    "migration_completed": entry.migration_completed,
                    "migration_id": entry.migration_id,
                    "changed_by": str(entry.changed_by) if entry.changed_by else None,
                    "changed_at": entry.changed_at.isoformat(),
                    "extra_metadata": entry.extra_metadata
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting configuration history for bot {bot_id}: {e}")
            return []    

    async def validate_all_provider_models(
        self,
        refresh_cache: bool = False
    ) -> Dict[str, List[ProviderModelInfo]]:
        """
        Validate all available provider/model combinations.
        
        Args:
            refresh_cache: Whether to refresh cached validation results
            
        Returns:
            Dictionary mapping providers to lists of validated model info
        """
        try:
            logger.info("Validating all provider/model combinations")
            
            results = {}
            all_providers = self.embedding_service.get_supported_providers()
            
            for provider in all_providers:
                try:
                    available_models = self.embedding_service.get_available_models(provider)
                    provider_results = []
                    
                    for model in available_models:
                        try:
                            model_info = await self.get_provider_model_info(
                                provider, model, refresh_cache
                            )
                            provider_results.append(model_info)
                        except Exception as e:
                            logger.warning(f"Failed to validate {provider}/{model}: {e}")
                            provider_results.append(ProviderModelInfo(
                                provider=provider,
                                model=model,
                                dimension=0,
                                is_available=False,
                                last_validated=datetime.utcnow(),
                                validation_error=str(e)
                            ))
                    
                    results[provider] = provider_results
                    
                except Exception as e:
                    logger.error(f"Failed to get models for provider {provider}: {e}")
                    results[provider] = []
            
            logger.info(f"Validated {sum(len(models) for models in results.values())} provider/model combinations")
            return results
            
        except Exception as e:
            logger.error(f"Error validating all provider/model combinations: {e}")
            return {}
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics and cache performance metrics.
        
        Returns:
            Dictionary with validation statistics
        """
        try:
            # Get cache statistics
            total_cached = self.db.query(DimensionCompatibilityCache).count()
            valid_cached = self.db.query(DimensionCompatibilityCache).filter(
                DimensionCompatibilityCache.is_valid == True
            ).count()
            
            # Get recent validations (last 24 hours)
            recent_validations = self.db.query(DimensionCompatibilityCache).filter(
                DimensionCompatibilityCache.last_validated > datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            # Get configuration history statistics
            total_config_changes = self.db.query(EmbeddingConfigurationHistory).count()
            migrations_required = self.db.query(EmbeddingConfigurationHistory).filter(
                EmbeddingConfigurationHistory.migration_required == True
            ).count()
            
            return {
                "cache_statistics": {
                    "total_cached_validations": total_cached,
                    "valid_configurations": valid_cached,
                    "invalid_configurations": total_cached - valid_cached,
                    "recent_validations_24h": recent_validations,
                    "cache_hit_rate": valid_cached / max(total_cached, 1) * 100
                },
                "configuration_history": {
                    "total_configuration_changes": total_config_changes,
                    "migrations_required": migrations_required,
                    "migrations_completed": self.db.query(EmbeddingConfigurationHistory).filter(
                        EmbeddingConfigurationHistory.migration_completed == True
                    ).count()
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting validation statistics: {e}")
            return {
                "cache_statistics": {},
                "configuration_history": {},
                "error": str(e)
            } 
   
    async def generate_compatibility_matrix(self) -> Dict[str, Any]:
        """
        Generate a compatibility matrix showing dimension compatibility between providers.
        
        Returns:
            Dictionary with compatibility matrix and analysis
        """
        try:
            logger.info("Generating embedding compatibility matrix")
            
            # Get all validated provider/model combinations
            all_validations = await self.validate_all_provider_models()
            
            # Group by dimension
            dimension_groups = {}
            provider_models = {}
            
            for provider, models in all_validations.items():
                provider_models[provider] = []
                
                for model_info in models:
                    if model_info.is_available and model_info.dimension > 0:
                        dimension = model_info.dimension
                        
                        if dimension not in dimension_groups:
                            dimension_groups[dimension] = []
                        
                        dimension_groups[dimension].append({
                            "provider": provider,
                            "model": model_info.model,
                            "dimension": dimension
                        })
                        
                        provider_models[provider].append({
                            "model": model_info.model,
                            "dimension": dimension,
                            "available": model_info.is_available
                        })
            
            # Generate compatibility recommendations
            compatibility_recommendations = []
            
            for dimension, compatible_models in dimension_groups.items():
                if len(compatible_models) > 1:
                    providers = list(set(model["provider"] for model in compatible_models))
                    compatibility_recommendations.append({
                        "dimension": dimension,
                        "compatible_providers": providers,
                        "model_count": len(compatible_models),
                        "models": compatible_models
                    })
            
            return {
                "dimension_groups": dimension_groups,
                "provider_models": provider_models,
                "compatibility_recommendations": compatibility_recommendations,
                "total_dimensions": len(dimension_groups),
                "total_compatible_groups": len(compatibility_recommendations),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating compatibility matrix: {e}")
            return {
                "dimension_groups": {},
                "provider_models": {},
                "compatibility_recommendations": [],
                "error": str(e)
            }
    
    async def validate_bot_configurations(
        self,
        bot_ids: Optional[List[uuid.UUID]] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate embedding configurations for multiple bots.
        
        Args:
            bot_ids: Optional list of bot IDs to validate. If None, validates all bots.
            
        Returns:
            List of validation results for each bot
        """
        try:
            logger.info("Validating bot embedding configurations")
            
            # Get bots to validate
            query = self.db.query(Bot)
            if bot_ids:
                query = query.filter(Bot.id.in_(bot_ids))
            
            bots = query.all()
            results = []
            
            for bot in bots:
                try:
                    provider = bot.embedding_provider or "openai"
                    model = bot.embedding_model or "text-embedding-3-small"
                    
                    # Get API key for validation
                    api_key = None
                    try:
                        api_key = self.user_service.get_user_api_key(bot.owner_id, provider)
                    except Exception as e:
                        logger.warning(f"Could not get API key for bot {bot.id}: {e}")
                    
                    # Validate configuration
                    validation_report = await self.validate_provider_model_combination(
                        provider, model, api_key
                    )
                    
                    # Get collection metadata
                    collection_metadata = await self.get_collection_metadata(bot.id)
                    
                    results.append({
                        "bot_id": str(bot.id),
                        "bot_name": bot.name,
                        "provider": provider,
                        "model": model,
                        "validation": {
                            "is_valid": validation_report.is_valid,
                            "compatibility_score": validation_report.compatibility_score,
                            "issues_count": len(validation_report.issues),
                            "critical_issues": len([
                                issue for issue in validation_report.issues 
                                if issue.severity == ValidationSeverity.ERROR
                            ]),
                            "migration_required": validation_report.migration_required
                        },
                        "collection_metadata": collection_metadata,
                        "last_validated": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error validating bot {bot.id}: {e}")
                    results.append({
                        "bot_id": str(bot.id),
                        "bot_name": bot.name,
                        "validation": {
                            "is_valid": False,
                            "error": str(e)
                        },
                        "last_validated": datetime.utcnow().isoformat()
                    })
            
            logger.info(f"Validated {len(results)} bot configurations")
            return results
            
        except Exception as e:
            logger.error(f"Error validating bot configurations: {e}")
            return []    
   
 # Private helper methods
    
    def _estimate_migration_time(self, chunk_count: int) -> str:
        """
        Estimate migration time based on chunk count.
        
        Args:
            chunk_count: Number of chunks to migrate
            
        Returns:
            Human-readable time estimate
        """
        # Rough estimates based on typical embedding generation times
        # Assume ~100ms per chunk for embedding generation + processing
        seconds_per_chunk = 0.1
        total_seconds = chunk_count * seconds_per_chunk
        
        if total_seconds < 60:
            return f"{int(total_seconds)} seconds"
        elif total_seconds < 3600:
            return f"{int(total_seconds / 60)} minutes"
        else:
            hours = int(total_seconds / 3600)
            minutes = int((total_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    async def _get_cached_validation(
        self,
        provider: str,
        model: str
    ) -> Optional[ValidationReport]:
        """Get cached validation result if available and not expired."""
        try:
            cache_entry = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == provider,
                    DimensionCompatibilityCache.model == model,
                    DimensionCompatibilityCache.last_validated > datetime.utcnow() - self.cache_ttl
                )
            ).first()
            
            if cache_entry:
                return ValidationReport(
                    is_valid=cache_entry.is_valid,
                    provider=provider,
                    model=model,
                    dimension=cache_entry.dimension,
                    issues=[ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CACHED_ERROR",
                        message=cache_entry.validation_error,
                        remediation="Check configuration and try again"
                    )] if cache_entry.validation_error else [],
                    recommendations=["Cached validation result"],
                    compatibility_score=1.0 if cache_entry.is_valid else 0.0,
                    migration_required=False,
                    metadata={
                        "cached": True,
                        "cache_timestamp": cache_entry.last_validated.isoformat()
                    }
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached validation for {provider}/{model}: {e}")
            return None
    
    async def _cache_validation_result(self, report: ValidationReport) -> None:
        """Cache validation result for future use."""
        try:
            # Update or create cache entry
            cache_entry = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == report.provider,
                    DimensionCompatibilityCache.model == report.model
                )
            ).first()
            
            if cache_entry:
                cache_entry.dimension = report.dimension
                cache_entry.is_valid = report.is_valid
                cache_entry.last_validated = datetime.utcnow()
                cache_entry.validation_error = report.issues[0].message if report.issues else None
            else:
                cache_entry = DimensionCompatibilityCache(
                    provider=report.provider,
                    model=report.model,
                    dimension=report.dimension,
                    is_valid=report.is_valid,
                    validation_error=report.issues[0].message if report.issues else None
                )
                self.db.add(cache_entry)
            
            self.db.commit()
            
        except Exception as e:
            logger.warning(f"Error caching validation result for {report.provider}/{report.model}: {e}")
            self.db.rollback()
    
    async def _get_cached_provider_info(
        self,
        provider: str,
        model: str
    ) -> Optional[ProviderModelInfo]:
        """Get cached provider info if available."""
        try:
            cache_entry = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == provider,
                    DimensionCompatibilityCache.model == model,
                    DimensionCompatibilityCache.last_validated > datetime.utcnow() - self.cache_ttl
                )
            ).first()
            
            if cache_entry:
                return ProviderModelInfo(
                    provider=provider,
                    model=model,
                    dimension=cache_entry.dimension,
                    is_available=cache_entry.is_valid,
                    last_validated=cache_entry.last_validated,
                    validation_error=cache_entry.validation_error
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached provider info for {provider}/{model}: {e}")
            return None
    
    async def _cache_provider_info(self, info: ProviderModelInfo) -> None:
        """Cache provider info for future use."""
        try:
            # This reuses the same cache table as validation results
            cache_entry = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == info.provider,
                    DimensionCompatibilityCache.model == info.model
                )
            ).first()
            
            if cache_entry:
                cache_entry.dimension = info.dimension
                cache_entry.is_valid = info.is_available
                cache_entry.last_validated = info.last_validated or datetime.utcnow()
                cache_entry.validation_error = info.validation_error
            else:
                cache_entry = DimensionCompatibilityCache(
                    provider=info.provider,
                    model=info.model,
                    dimension=info.dimension,
                    is_valid=info.is_available,
                    validation_error=info.validation_error,
                    last_validated=info.last_validated or datetime.utcnow()
                )
                self.db.add(cache_entry)
            
            self.db.commit()
            
        except Exception as e:
            logger.warning(f"Error caching provider info for {info.provider}/{info.model}: {e}")
            self.db.rollback()
    
    async def _store_configuration_history(
        self,
        bot_id: uuid.UUID,
        previous_provider: str,
        previous_model: str,
        new_provider: str,
        new_model: str,
        change_reason: Optional[str],
        migration_required: bool
    ) -> None:
        """Store configuration change in history."""
        try:
            # Get dimensions
            previous_dimension = 0
            new_dimension = 0
            
            try:
                previous_dimension = self.embedding_service.get_embedding_dimension(
                    previous_provider, previous_model
                )
                new_dimension = self.embedding_service.get_embedding_dimension(
                    new_provider, new_model
                )
            except Exception as e:
                logger.warning(f"Could not get dimensions for history: {e}")
            
            history_entry = EmbeddingConfigurationHistory(
                bot_id=bot_id,
                previous_provider=previous_provider,
                previous_model=previous_model,
                previous_dimension=previous_dimension,
                new_provider=new_provider,
                new_model=new_model,
                new_dimension=new_dimension,
                change_reason=change_reason,
                migration_required=migration_required,
                migration_completed=False,
                extra_metadata={
                    "validation_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            self.db.add(history_entry)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing configuration history for bot {bot_id}: {e}")
            self.db.rollback()
    
    async def cleanup_expired_cache(self) -> Dict[str, Any]:
        """
        Clean up expired cache entries.
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            logger.info("Cleaning up expired validation cache entries")
            
            # Find expired entries
            expired_threshold = datetime.utcnow() - self.cache_ttl
            expired_entries = self.db.query(DimensionCompatibilityCache).filter(
                DimensionCompatibilityCache.last_validated < expired_threshold
            )
            
            expired_count = expired_entries.count()
            
            # Delete expired entries
            expired_entries.delete()
            self.db.commit()
            
            logger.info(f"Cleaned up {expired_count} expired cache entries")
            
            return {
                "expired_entries_removed": expired_count,
                "cleanup_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            self.db.rollback()
            return {
                "expired_entries_removed": 0,
                "error": str(e)
            }
    
    async def close(self):
        """Close the validator and clean up resources."""
        try:
            await self.embedding_service.close()
            logger.info("Embedding Configuration Validator closed successfully")
        except Exception as e:
            logger.error(f"Error closing Embedding Configuration Validator: {e}")