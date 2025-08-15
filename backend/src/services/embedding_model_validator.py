"""
Embedding Model Validation Service - Comprehensive model validation and compatibility system.

This service provides:
- Model availability validation for each embedding provider
- Model compatibility checking with existing bot configurations
- Model suggestion system when validation fails
- Model deprecation detection and migration notifications
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime, timedelta
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
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


class ModelValidationStatus(Enum):
    """Status of model validation."""
    VALID = "valid"
    INVALID = "invalid"
    DEPRECATED = "deprecated"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class MigrationImpact(Enum):
    """Impact level of model migration."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ModelValidationResult:
    """Result of model validation."""
    provider: str
    model: str
    status: ModelValidationStatus
    is_available: bool
    dimension: int
    validation_error: Optional[str] = None
    last_validated: Optional[datetime] = None
    deprecation_info: Optional[Dict[str, Any]] = None
    api_requirements: Optional[Dict[str, Any]] = None


@dataclass
class ModelCompatibilityResult:
    """Result of model compatibility check."""
    is_compatible: bool
    current_model: ModelValidationResult
    target_model: ModelValidationResult
    migration_required: bool
    migration_impact: MigrationImpact
    compatibility_issues: List[str]
    recommendations: List[str]
    estimated_migration_time: Optional[str] = None
    affected_documents: int = 0


@dataclass
class ModelSuggestion:
    """Model suggestion with compatibility information."""
    provider: str
    model: str
    dimension: int
    compatibility_score: float
    reason: str
    migration_required: bool
    estimated_cost: Optional[str] = None


class EmbeddingModelValidator:
    """
    Comprehensive embedding model validator.
    
    Provides model availability validation, compatibility checking,
    and migration impact analysis.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the model validator.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = EmbeddingProviderService()
        self.user_service = UserService(db)
        
        # Cache settings
        self.cache_ttl = timedelta(hours=6)  # Cache validation results for 6 hours
        self.validation_timeout = 30  # seconds
        
        # Known deprecated models (can be updated from external sources)
        self.deprecated_models = {
            "openai": {
                "text-embedding-ada-002": {
                    "deprecated_date": "2024-01-01",
                    "replacement": "text-embedding-3-small",
                    "reason": "Replaced by more efficient model"
                }
            }
        }
        
        # Model preference scoring
        self.provider_preferences = {
            "openai": 1.0,
            "gemini": 0.9,
            "anthropic": 0.8,
            "openrouter": 0.7
        }
    
    async def validate_model_availability(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        use_cache: bool = True
    ) -> ModelValidationResult:
        """
        Validate model availability for a specific provider.
        
        Args:
            provider: Embedding provider name
            model: Model name to validate
            api_key: Optional API key for validation
            use_cache: Whether to use cached validation results
            
        Returns:
            ModelValidationResult with validation details
        """
        try:
            logger.info(f"Validating model availability: {provider}/{model}")
            
            # Check cache first
            if use_cache:
                cached_result = await self._get_cached_validation(provider, model)
                if cached_result:
                    logger.debug(f"Using cached validation for {provider}/{model}")
                    return cached_result
            
            # Validate provider is supported
            supported_providers = self.embedding_service.get_supported_providers()
            if provider not in supported_providers:
                return ModelValidationResult(
                    provider=provider,
                    model=model,
                    status=ModelValidationStatus.INVALID,
                    is_available=False,
                    dimension=0,
                    validation_error=f"Provider '{provider}' is not supported",
                    last_validated=datetime.utcnow()
                )
            
            # Get available models
            try:
                if api_key:
                    available_models = await asyncio.wait_for(
                        self.embedding_service.get_available_models_dynamic(provider, api_key),
                        timeout=self.validation_timeout
                    )
                else:
                    available_models = self.embedding_service.get_available_models(provider)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting models for {provider}")
                available_models = self.embedding_service.get_available_models(provider)
            except Exception as e:
                logger.warning(f"Error getting models for {provider}: {e}")
                available_models = self.embedding_service.get_available_models(provider)
            
            # Check if model is available
            is_available = model in available_models
            status = ModelValidationStatus.VALID if is_available else ModelValidationStatus.UNAVAILABLE
            
            # Get dimension information
            dimension = 0
            validation_error = None
            if is_available:
                try:
                    dimension = self.embedding_service.get_embedding_dimension(provider, model)
                except Exception as e:
                    validation_error = f"Could not determine dimension: {str(e)}"
                    status = ModelValidationStatus.UNKNOWN
            else:
                validation_error = f"Model '{model}' not found in available models for {provider}"
            
            # Check for deprecation
            deprecation_info = None
            if is_available and provider in self.deprecated_models:
                if model in self.deprecated_models[provider]:
                    status = ModelValidationStatus.DEPRECATED
                    deprecation_info = self.deprecated_models[provider][model]
            
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
            
            result = ModelValidationResult(
                provider=provider,
                model=model,
                status=status,
                is_available=is_available,
                dimension=dimension,
                validation_error=validation_error,
                last_validated=datetime.utcnow(),
                deprecation_info=deprecation_info,
                api_requirements=api_requirements
            )
            
            # Cache the result
            if use_cache:
                await self._cache_validation_result(result)
            
            logger.info(f"Model validation complete for {provider}/{model}: available={is_available}, status={status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error validating model {provider}/{model}: {e}")
            return ModelValidationResult(
                provider=provider,
                model=model,
                status=ModelValidationStatus.INVALID,
                is_available=False,
                dimension=0,
                validation_error=str(e),
                last_validated=datetime.utcnow()
            )
    
    async def check_model_compatibility(
        self,
        bot_id: uuid.UUID,
        target_provider: str,
        target_model: str,
        api_key: Optional[str] = None
    ) -> ModelCompatibilityResult:
        """
        Check compatibility between current and target model configurations.
        
        Args:
            bot_id: Bot identifier
            target_provider: Target embedding provider
            target_model: Target embedding model
            api_key: Optional API key for validation
            
        Returns:
            ModelCompatibilityResult with compatibility analysis
        """
        try:
            logger.info(f"Checking model compatibility for bot {bot_id}: {target_provider}/{target_model}")
            
            # Get bot and current configuration
            bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bot not found"
                )
            
            current_provider = bot.embedding_provider or "openai"
            current_model = bot.embedding_model or "text-embedding-3-small"
            
            # Validate both models
            current_validation = await self.validate_model_availability(
                current_provider, current_model, api_key
            )
            target_validation = await self.validate_model_availability(
                target_provider, target_model, api_key
            )
            
            # Check basic compatibility
            is_compatible = target_validation.is_available
            compatibility_issues = []
            recommendations = []
            migration_required = False
            migration_impact = MigrationImpact.NONE
            
            # Check if target model is valid
            if not target_validation.is_available:
                compatibility_issues.append(f"Target model {target_provider}/{target_model} is not available")
                is_compatible = False
            
            # Check for deprecation
            if target_validation.status == ModelValidationStatus.DEPRECATED:
                compatibility_issues.append(f"Target model {target_provider}/{target_model} is deprecated")
                if target_validation.deprecation_info:
                    replacement = target_validation.deprecation_info.get("replacement")
                    if replacement:
                        recommendations.append(f"Consider using {replacement} instead")
            
            # Check dimension compatibility
            if current_validation.is_available and target_validation.is_available:
                if current_validation.dimension != target_validation.dimension:
                    migration_required = True
                    compatibility_issues.append(
                        f"Dimension mismatch: current={current_validation.dimension}, "
                        f"target={target_validation.dimension}"
                    )
                    
                    # Assess migration impact
                    affected_documents = self.db.query(DocumentChunk).filter(
                        DocumentChunk.bot_id == bot_id
                    ).count()
                    
                    if affected_documents == 0:
                        migration_impact = MigrationImpact.NONE
                        recommendations.append("No documents to migrate")
                    elif affected_documents < 100:
                        migration_impact = MigrationImpact.LOW
                        recommendations.append("Small document collection - migration should be quick")
                    elif affected_documents < 1000:
                        migration_impact = MigrationImpact.MEDIUM
                        recommendations.append("Medium document collection - plan for migration downtime")
                    elif affected_documents < 10000:
                        migration_impact = MigrationImpact.HIGH
                        recommendations.append("Large document collection - schedule migration carefully")
                    else:
                        migration_impact = MigrationImpact.CRITICAL
                        recommendations.append("Very large document collection - consider phased migration")
                else:
                    recommendations.append("Dimensions match - no migration required")
            
            # Estimate migration time
            estimated_migration_time = None
            if migration_required:
                estimated_migration_time = self._estimate_migration_time(
                    self.db.query(DocumentChunk).filter(DocumentChunk.bot_id == bot_id).count()
                )
            
            # Add general recommendations
            if is_compatible:
                if current_provider == target_provider and current_model == target_model:
                    recommendations.append("Configuration is already set to target values")
                else:
                    recommendations.append("Target configuration is compatible")
            
            result = ModelCompatibilityResult(
                is_compatible=is_compatible,
                current_model=current_validation,
                target_model=target_validation,
                migration_required=migration_required,
                migration_impact=migration_impact,
                compatibility_issues=compatibility_issues,
                recommendations=recommendations,
                estimated_migration_time=estimated_migration_time,
                affected_documents=self.db.query(DocumentChunk).filter(
                    DocumentChunk.bot_id == bot_id
                ).count()
            )
            
            logger.info(f"Compatibility check complete for bot {bot_id}: compatible={is_compatible}, migration_required={migration_required}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking model compatibility for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compatibility check failed: {str(e)}"
            )
    
    async def suggest_compatible_models(
        self,
        target_dimension: Optional[int] = None,
        exclude_provider: Optional[str] = None,
        exclude_model: Optional[str] = None,
        max_suggestions: int = 5
    ) -> List[ModelSuggestion]:
        """
        Suggest compatible models based on criteria.
        
        Args:
            target_dimension: Target embedding dimension (None for all)
            exclude_provider: Provider to exclude from suggestions
            exclude_model: Model to exclude from suggestions
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of ModelSuggestion objects sorted by compatibility score
        """
        try:
            logger.info(f"Generating model suggestions for dimension {target_dimension}")
            
            suggestions = []
            all_providers = self.embedding_service.get_all_providers_info()
            
            for provider_name, provider_info in all_providers.items():
                if exclude_provider and provider_name == exclude_provider:
                    continue
                
                model_dimensions = provider_info.get("model_dimensions", {})
                for model_name, dimension in model_dimensions.items():
                    if exclude_model and model_name == exclude_model:
                        continue
                    
                    # Filter by dimension if specified
                    if target_dimension is not None and dimension != target_dimension:
                        continue
                    
                    # Validate the model
                    validation = await self.validate_model_availability(provider_name, model_name)
                    if not validation.is_available:
                        continue
                    
                    # Calculate compatibility score
                    compatibility_score = self._calculate_compatibility_score(
                        provider_name, model_name, validation
                    )
                    
                    # Determine migration requirement
                    migration_required = target_dimension is not None and dimension != target_dimension
                    
                    # Estimate cost (placeholder - could be enhanced with actual pricing)
                    estimated_cost = self._estimate_model_cost(provider_name, model_name)
                    
                    # Generate reason
                    reason = self._generate_suggestion_reason(
                        provider_name, model_name, validation, compatibility_score
                    )
                    
                    suggestions.append(ModelSuggestion(
                        provider=provider_name,
                        model=model_name,
                        dimension=dimension,
                        compatibility_score=compatibility_score,
                        reason=reason,
                        migration_required=migration_required,
                        estimated_cost=estimated_cost
                    ))
            
            # Sort by compatibility score (descending)
            suggestions.sort(key=lambda x: x.compatibility_score, reverse=True)
            
            # Return top suggestions
            result = suggestions[:max_suggestions]
            logger.info(f"Generated {len(result)} model suggestions")
            return result
            
        except Exception as e:
            logger.error(f"Error generating model suggestions: {e}")
            return []
    
    async def detect_deprecated_models(
        self,
        check_all_bots: bool = False,
        bot_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect deprecated models in use and suggest migrations.
        
        Args:
            check_all_bots: Whether to check all bots or specific bot
            bot_id: Specific bot ID to check (if check_all_bots is False)
            
        Returns:
            List of deprecation notifications with migration suggestions
        """
        try:
            logger.info(f"Detecting deprecated models (all_bots={check_all_bots}, bot_id={bot_id})")
            
            notifications = []
            
            # Build query
            query = self.db.query(Bot)
            if not check_all_bots and bot_id:
                query = query.filter(Bot.id == bot_id)
            
            bots = query.all()
            
            for bot in bots:
                provider = bot.embedding_provider or "openai"
                model = bot.embedding_model or "text-embedding-3-small"
                
                # Validate current model
                validation = await self.validate_model_availability(provider, model)
                
                if validation.status == ModelValidationStatus.DEPRECATED:
                    # Get suggested replacement
                    suggestions = await self.suggest_compatible_models(
                        target_dimension=validation.dimension,
                        exclude_provider=provider,
                        exclude_model=model,
                        max_suggestions=3
                    )
                    
                    notification = {
                        "bot_id": str(bot.id),
                        "bot_name": bot.name,
                        "current_provider": provider,
                        "current_model": model,
                        "deprecation_info": validation.deprecation_info,
                        "suggested_replacements": [
                            {
                                "provider": s.provider,
                                "model": s.model,
                                "reason": s.reason,
                                "migration_required": s.migration_required
                            }
                            for s in suggestions
                        ],
                        "detected_at": datetime.utcnow().isoformat()
                    }
                    
                    notifications.append(notification)
            
            logger.info(f"Found {len(notifications)} deprecated model notifications")
            return notifications
            
        except Exception as e:
            logger.error(f"Error detecting deprecated models: {e}")
            return []
    
    async def validate_all_models(
        self,
        refresh_cache: bool = False
    ) -> Dict[str, List[ModelValidationResult]]:
        """
        Validate all available models across all providers.
        
        Args:
            refresh_cache: Whether to refresh cached validation results
            
        Returns:
            Dictionary mapping providers to lists of validation results
        """
        try:
            logger.info("Validating all available models")
            
            results = {}
            supported_providers = self.embedding_service.get_supported_providers()
            
            for provider in supported_providers:
                try:
                    available_models = self.embedding_service.get_available_models(provider)
                    provider_results = []
                    
                    for model in available_models:
                        validation = await self.validate_model_availability(
                            provider, model, use_cache=not refresh_cache
                        )
                        provider_results.append(validation)
                    
                    results[provider] = provider_results
                    
                except Exception as e:
                    logger.error(f"Error validating models for provider {provider}: {e}")
                    results[provider] = []
            
            logger.info(f"Validated models for {len(results)} providers")
            return results
            
        except Exception as e:
            logger.error(f"Error validating all models: {e}")
            return {}
    
    # Private helper methods
    
    async def _get_cached_validation(
        self,
        provider: str,
        model: str
    ) -> Optional[ModelValidationResult]:
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
                return ModelValidationResult(
                    provider=provider,
                    model=model,
                    status=ModelValidationStatus.VALID if cache_entry.is_valid else ModelValidationStatus.INVALID,
                    is_available=cache_entry.is_valid,
                    dimension=cache_entry.dimension,
                    validation_error=cache_entry.validation_error,
                    last_validated=cache_entry.last_validated
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached validation for {provider}/{model}: {e}")
            return None
    
    async def _cache_validation_result(self, result: ModelValidationResult) -> None:
        """Cache validation result for future use."""
        try:
            # Update or create cache entry
            cache_entry = self.db.query(DimensionCompatibilityCache).filter(
                and_(
                    DimensionCompatibilityCache.provider == result.provider,
                    DimensionCompatibilityCache.model == result.model
                )
            ).first()
            
            if cache_entry:
                cache_entry.dimension = result.dimension
                cache_entry.is_valid = result.is_available
                cache_entry.last_validated = result.last_validated or datetime.utcnow()
                cache_entry.validation_error = result.validation_error
                cache_entry.updated_at = datetime.utcnow()
            else:
                cache_entry = DimensionCompatibilityCache(
                    provider=result.provider,
                    model=result.model,
                    dimension=result.dimension,
                    is_valid=result.is_available,
                    last_validated=result.last_validated or datetime.utcnow(),
                    validation_error=result.validation_error
                )
                self.db.add(cache_entry)
            
            self.db.commit()
            
        except Exception as e:
            logger.warning(f"Error caching validation result for {result.provider}/{result.model}: {e}")
            self.db.rollback()
    
    def _calculate_compatibility_score(
        self,
        provider: str,
        model: str,
        validation: ModelValidationResult
    ) -> float:
        """Calculate compatibility score for a model."""
        score = 0.0
        
        # Base score from provider preference
        score += self.provider_preferences.get(provider, 0.5)
        
        # Availability bonus
        if validation.is_available:
            score += 0.3
        
        # Deprecation penalty
        if validation.status == ModelValidationStatus.DEPRECATED:
            score -= 0.2
        
        # Model name preferences (newer models typically better)
        if "3" in model:  # e.g., text-embedding-3-small
            score += 0.1
        elif "2" in model:  # e.g., text-embedding-ada-002
            score -= 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def _estimate_model_cost(self, provider: str, model: str) -> str:
        """Estimate relative cost for a model (placeholder implementation)."""
        # This could be enhanced with actual pricing data
        cost_estimates = {
            "openai": {
                "text-embedding-3-small": "Low",
                "text-embedding-3-large": "Medium",
                "text-embedding-ada-002": "Low"
            },
            "gemini": {
                "embedding-001": "Low"
            }
        }
        
        return cost_estimates.get(provider, {}).get(model, "Unknown")
    
    def _generate_suggestion_reason(
        self,
        provider: str,
        model: str,
        validation: ModelValidationResult,
        compatibility_score: float
    ) -> str:
        """Generate human-readable reason for model suggestion."""
        reasons = []
        
        if compatibility_score > 0.8:
            reasons.append("Highly compatible")
        elif compatibility_score > 0.6:
            reasons.append("Good compatibility")
        else:
            reasons.append("Basic compatibility")
        
        if validation.status == ModelValidationStatus.DEPRECATED:
            reasons.append("deprecated model")
        elif "3" in model:
            reasons.append("latest generation model")
        
        if provider == "openai":
            reasons.append("reliable provider")
        
        return ", ".join(reasons)
    
    def _estimate_migration_time(self, document_count: int) -> str:
        """Estimate migration time based on document count."""
        if document_count == 0:
            return "Immediate"
        elif document_count < 100:
            return "1-5 minutes"
        elif document_count < 1000:
            return "5-30 minutes"
        elif document_count < 10000:
            return "30 minutes - 2 hours"
        else:
            return "2+ hours"
    
    def _calculate_compatibility_score(
        self,
        provider: str,
        model: str,
        validation: ModelValidationResult
    ) -> float:
        """Calculate compatibility score for a model."""
        score = 0.0
        
        # Base score from provider preference
        score += self.provider_preferences.get(provider, 0.5)
        
        # Availability bonus
        if validation.is_available:
            score += 0.3
        
        # Deprecation penalty
        if validation.status == ModelValidationStatus.DEPRECATED:
            score -= 0.2
        
        # Model name preferences (newer models typically better)
        if "3" in model:  # e.g., text-embedding-3-small
            score += 0.1
        elif "2" in model:  # e.g., text-embedding-ada-002
            score -= 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))