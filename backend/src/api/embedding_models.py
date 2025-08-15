"""
API endpoints for embedding model validation and migration.
"""
import logging
from typing import List, Optional, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.embedding_model_validator import (
    EmbeddingModelValidator,
    ModelValidationResult,
    ModelCompatibilityResult,
    ModelSuggestion
)
from ..services.embedding_model_migration import (
    EmbeddingModelMigration,
    DimensionCompatibilityCheck,
    ModelChangeImpact,
    MigrationPlan,
    MigrationResult
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embedding-models", tags=["embedding-models"])


# Request/Response Models

class ModelValidationRequest(BaseModel):
    provider: str = Field(..., description="Embedding provider name")
    model: str = Field(..., description="Embedding model name")
    api_key: Optional[str] = Field(None, description="Optional API key for validation")


class ModelCompatibilityRequest(BaseModel):
    bot_id: uuid.UUID = Field(..., description="Bot identifier")
    target_provider: str = Field(..., description="Target embedding provider")
    target_model: str = Field(..., description="Target embedding model")


class ModelSuggestionRequest(BaseModel):
    target_dimension: Optional[int] = Field(None, description="Target embedding dimension")
    exclude_provider: Optional[str] = Field(None, description="Provider to exclude")
    exclude_model: Optional[str] = Field(None, description="Model to exclude")
    max_suggestions: int = Field(5, description="Maximum suggestions to return")


class MigrationPlanRequest(BaseModel):
    bot_id: uuid.UUID = Field(..., description="Bot identifier")
    target_provider: str = Field(..., description="Target embedding provider")
    target_model: str = Field(..., description="Target embedding model")
    migration_reason: Optional[str] = Field(None, description="Reason for migration")


class MigrationExecutionRequest(BaseModel):
    migration_plan_id: str = Field(..., description="Migration plan identifier")
    dry_run: bool = Field(False, description="Whether to perform a dry run")


class ModelValidationResponse(BaseModel):
    provider: str
    model: str
    status: str
    is_available: bool
    dimension: int
    validation_error: Optional[str] = None
    last_validated: Optional[str] = None
    deprecation_info: Optional[Dict[str, Any]] = None
    api_requirements: Optional[Dict[str, Any]] = None


class ModelCompatibilityResponse(BaseModel):
    is_compatible: bool
    current_model: ModelValidationResponse
    target_model: ModelValidationResponse
    migration_required: bool
    migration_impact: str
    compatibility_issues: List[str]
    recommendations: List[str]
    estimated_migration_time: Optional[str] = None
    affected_documents: int


class ModelSuggestionResponse(BaseModel):
    provider: str
    model: str
    dimension: int
    compatibility_score: float
    reason: str
    migration_required: bool
    estimated_cost: Optional[str] = None


class DimensionCompatibilityResponse(BaseModel):
    is_compatible: bool
    current_dimension: int
    target_dimension: int
    dimension_change: int
    compatibility_percentage: float
    migration_required: bool
    impact_assessment: str


class MigrationImpactResponse(BaseModel):
    impact_level: str
    affected_documents: int
    affected_chunks: int
    estimated_migration_time: str
    estimated_cost: Optional[str]
    data_loss_risk: str
    performance_impact: str
    compatibility_issues: List[str]
    recommendations: List[str]
    rollback_complexity: str


class MigrationPlanResponse(BaseModel):
    migration_id: str
    bot_id: str
    current_config: Dict[str, Any]
    target_config: Dict[str, Any]
    compatibility_check: DimensionCompatibilityResponse
    impact_analysis: MigrationImpactResponse
    migration_steps: List[Dict[str, Any]]
    rollback_plan: List[Dict[str, Any]]
    validation_checkpoints: List[str]
    estimated_duration: str
    created_at: str


class MigrationResultResponse(BaseModel):
    migration_id: str
    status: str
    success: bool
    completed_steps: int
    total_steps: int
    error_message: Optional[str]
    rollback_available: bool
    performance_metrics: Dict[str, Any]
    validation_results: Dict[str, Any]
    completed_at: Optional[str]


# API Endpoints

@router.post("/validate", response_model=ModelValidationResponse)
async def validate_model(
    request: ModelValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate model availability for a specific provider.
    
    Validates that the specified embedding model is available for the provider
    and returns detailed validation information including dimensions and requirements.
    """
    try:
        validator = EmbeddingModelValidator(db)
        
        result = await validator.validate_model_availability(
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
            use_cache=True
        )
        
        return ModelValidationResponse(
            provider=result.provider,
            model=result.model,
            status=result.status.value,
            is_available=result.is_available,
            dimension=result.dimension,
            validation_error=result.validation_error,
            last_validated=result.last_validated.isoformat() if result.last_validated else None,
            deprecation_info=result.deprecation_info,
            api_requirements=result.api_requirements
        )
        
    except Exception as e:
        logger.error(f"Error validating model {request.provider}/{request.model}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model validation failed: {str(e)}"
        )


@router.post("/compatibility", response_model=ModelCompatibilityResponse)
async def check_model_compatibility(
    request: ModelCompatibilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check compatibility between current and target model configurations.
    
    Analyzes the compatibility between a bot's current embedding configuration
    and a target configuration, including migration requirements and impact assessment.
    """
    try:
        validator = EmbeddingModelValidator(db)
        
        # Get user's API key for the target provider
        api_key = None
        try:
            from ..services.user_service import UserService
            user_service = UserService(db)
            api_key = user_service.get_user_api_key(current_user.id, request.target_provider)
        except Exception as e:
            logger.warning(f"Could not get API key for {request.target_provider}: {e}")
        
        result = await validator.check_model_compatibility(
            bot_id=request.bot_id,
            target_provider=request.target_provider,
            target_model=request.target_model,
            api_key=api_key
        )
        
        return ModelCompatibilityResponse(
            is_compatible=result.is_compatible,
            current_model=ModelValidationResponse(
                provider=result.current_model.provider,
                model=result.current_model.model,
                status=result.current_model.status.value,
                is_available=result.current_model.is_available,
                dimension=result.current_model.dimension,
                validation_error=result.current_model.validation_error,
                last_validated=result.current_model.last_validated.isoformat() if result.current_model.last_validated else None,
                deprecation_info=result.current_model.deprecation_info,
                api_requirements=result.current_model.api_requirements
            ),
            target_model=ModelValidationResponse(
                provider=result.target_model.provider,
                model=result.target_model.model,
                status=result.target_model.status.value,
                is_available=result.target_model.is_available,
                dimension=result.target_model.dimension,
                validation_error=result.target_model.validation_error,
                last_validated=result.target_model.last_validated.isoformat() if result.target_model.last_validated else None,
                deprecation_info=result.target_model.deprecation_info,
                api_requirements=result.target_model.api_requirements
            ),
            migration_required=result.migration_required,
            migration_impact=result.migration_impact.value,
            compatibility_issues=result.compatibility_issues,
            recommendations=result.recommendations,
            estimated_migration_time=result.estimated_migration_time,
            affected_documents=result.affected_documents
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking model compatibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compatibility check failed: {str(e)}"
        )


@router.post("/suggestions", response_model=List[ModelSuggestionResponse])
async def get_model_suggestions(
    request: ModelSuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get compatible model suggestions based on criteria.
    
    Returns a list of embedding models that are compatible with the specified
    criteria, sorted by compatibility score.
    """
    try:
        validator = EmbeddingModelValidator(db)
        
        suggestions = await validator.suggest_compatible_models(
            target_dimension=request.target_dimension,
            exclude_provider=request.exclude_provider,
            exclude_model=request.exclude_model,
            max_suggestions=request.max_suggestions
        )
        
        return [
            ModelSuggestionResponse(
                provider=suggestion.provider,
                model=suggestion.model,
                dimension=suggestion.dimension,
                compatibility_score=suggestion.compatibility_score,
                reason=suggestion.reason,
                migration_required=suggestion.migration_required,
                estimated_cost=suggestion.estimated_cost
            )
            for suggestion in suggestions
        ]
        
    except Exception as e:
        logger.error(f"Error getting model suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model suggestions failed: {str(e)}"
        )


@router.get("/deprecated", response_model=List[Dict[str, Any]])
async def detect_deprecated_models(
    check_all_bots: bool = Query(False, description="Check all bots or just user's bots"),
    bot_id: Optional[uuid.UUID] = Query(None, description="Specific bot ID to check"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Detect deprecated models in use and suggest migrations.
    
    Scans bots for deprecated embedding models and provides migration suggestions.
    """
    try:
        validator = EmbeddingModelValidator(db)
        
        notifications = await validator.detect_deprecated_models(
            check_all_bots=check_all_bots,
            bot_id=bot_id
        )
        
        return notifications
        
    except Exception as e:
        logger.error(f"Error detecting deprecated models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deprecated model detection failed: {str(e)}"
        )


@router.get("/validate-all", response_model=Dict[str, List[ModelValidationResponse]])
async def validate_all_models(
    refresh_cache: bool = Query(False, description="Refresh cached validation results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate all available models across all providers.
    
    Performs comprehensive validation of all embedding models and returns
    detailed validation results organized by provider.
    """
    try:
        validator = EmbeddingModelValidator(db)
        
        results = await validator.validate_all_models(refresh_cache=refresh_cache)
        
        # Convert results to response format
        response = {}
        for provider, validations in results.items():
            response[provider] = [
                ModelValidationResponse(
                    provider=validation.provider,
                    model=validation.model,
                    status=validation.status.value,
                    is_available=validation.is_available,
                    dimension=validation.dimension,
                    validation_error=validation.validation_error,
                    last_validated=validation.last_validated.isoformat() if validation.last_validated else None,
                    deprecation_info=validation.deprecation_info,
                    api_requirements=validation.api_requirements
                )
                for validation in validations
            ]
        
        return response
        
    except Exception as e:
        logger.error(f"Error validating all models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model validation failed: {str(e)}"
        )


# Migration endpoints

@router.post("/migration/compatibility", response_model=DimensionCompatibilityResponse)
async def check_dimension_compatibility(
    current_provider: str = Query(..., description="Current embedding provider"),
    current_model: str = Query(..., description="Current embedding model"),
    target_provider: str = Query(..., description="Target embedding provider"),
    target_model: str = Query(..., description="Target embedding model"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check dimension compatibility between old and new models.
    
    Analyzes the dimensional compatibility between current and target embedding
    models to determine migration requirements.
    """
    try:
        migration_service = EmbeddingModelMigration(db)
        
        result = await migration_service.check_dimension_compatibility(
            current_provider=current_provider,
            current_model=current_model,
            target_provider=target_provider,
            target_model=target_model
        )
        
        return DimensionCompatibilityResponse(
            is_compatible=result.is_compatible,
            current_dimension=result.current_dimension,
            target_dimension=result.target_dimension,
            dimension_change=result.dimension_change,
            compatibility_percentage=result.compatibility_percentage,
            migration_required=result.migration_required,
            impact_assessment=result.impact_assessment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking dimension compatibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dimension compatibility check failed: {str(e)}"
        )


@router.post("/migration/impact", response_model=MigrationImpactResponse)
async def analyze_migration_impact(
    bot_id: uuid.UUID = Query(..., description="Bot identifier"),
    target_provider: str = Query(..., description="Target embedding provider"),
    target_model: str = Query(..., description="Target embedding model"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze the impact of model changes with clear explanations.
    
    Provides detailed analysis of the impact of changing embedding models,
    including affected data, estimated time, and recommendations.
    """
    try:
        migration_service = EmbeddingModelMigration(db)
        
        # First check dimension compatibility
        from ..models.bot import Bot
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        current_provider = bot.embedding_provider or "openai"
        current_model = bot.embedding_model or "text-embedding-3-small"
        
        compatibility_check = await migration_service.check_dimension_compatibility(
            current_provider=current_provider,
            current_model=current_model,
            target_provider=target_provider,
            target_model=target_model
        )
        
        result = await migration_service.analyze_migration_impact(
            bot_id=bot_id,
            target_provider=target_provider,
            target_model=target_model,
            compatibility_check=compatibility_check
        )
        
        return MigrationImpactResponse(
            impact_level=result.impact_level.value,
            affected_documents=result.affected_documents,
            affected_chunks=result.affected_chunks,
            estimated_migration_time=result.estimated_migration_time,
            estimated_cost=result.estimated_cost,
            data_loss_risk=result.data_loss_risk,
            performance_impact=result.performance_impact,
            compatibility_issues=result.compatibility_issues,
            recommendations=result.recommendations,
            rollback_complexity=result.rollback_complexity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing migration impact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration impact analysis failed: {str(e)}"
        )


@router.post("/migration/plan", response_model=MigrationPlanResponse)
async def create_migration_plan(
    request: MigrationPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a comprehensive migration plan with validation and rollback.
    
    Generates a detailed migration plan including steps, validation checkpoints,
    and rollback procedures for changing embedding models.
    """
    try:
        migration_service = EmbeddingModelMigration(db)
        
        plan = await migration_service.create_migration_plan(
            bot_id=request.bot_id,
            target_provider=request.target_provider,
            target_model=request.target_model,
            migration_reason=request.migration_reason
        )
        
        return MigrationPlanResponse(
            migration_id=plan.migration_id,
            bot_id=str(plan.bot_id),
            current_config=plan.current_config,
            target_config=plan.target_config,
            compatibility_check=DimensionCompatibilityResponse(
                is_compatible=plan.compatibility_check.is_compatible,
                current_dimension=plan.compatibility_check.current_dimension,
                target_dimension=plan.compatibility_check.target_dimension,
                dimension_change=plan.compatibility_check.dimension_change,
                compatibility_percentage=plan.compatibility_check.compatibility_percentage,
                migration_required=plan.compatibility_check.migration_required,
                impact_assessment=plan.compatibility_check.impact_assessment
            ),
            impact_analysis=MigrationImpactResponse(
                impact_level=plan.impact_analysis.impact_level.value,
                affected_documents=plan.impact_analysis.affected_documents,
                affected_chunks=plan.impact_analysis.affected_chunks,
                estimated_migration_time=plan.impact_analysis.estimated_migration_time,
                estimated_cost=plan.impact_analysis.estimated_cost,
                data_loss_risk=plan.impact_analysis.data_loss_risk,
                performance_impact=plan.impact_analysis.performance_impact,
                compatibility_issues=plan.impact_analysis.compatibility_issues,
                recommendations=plan.impact_analysis.recommendations,
                rollback_complexity=plan.impact_analysis.rollback_complexity
            ),
            migration_steps=plan.migration_steps,
            rollback_plan=plan.rollback_plan,
            validation_checkpoints=plan.validation_checkpoints,
            estimated_duration=plan.estimated_duration,
            created_at=plan.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating migration plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration plan creation failed: {str(e)}"
        )


@router.post("/migration/update-lists", response_model=Dict[str, Any])
async def update_model_lists(
    provider: Optional[str] = Query(None, description="Specific provider to update"),
    force_refresh: bool = Query(False, description="Force refresh even if recently updated"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update model lists when providers add new models.
    
    Refreshes the list of available models from embedding providers and
    validates any newly discovered models.
    """
    try:
        migration_service = EmbeddingModelMigration(db)
        
        result = await migration_service.update_model_lists(
            provider=provider,
            force_refresh=force_refresh
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating model lists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model list update failed: {str(e)}"
        )