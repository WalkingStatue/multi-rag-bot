"""
API endpoints for embedding configuration validation.
"""
import logging
from typing import List, Optional, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.embedding_configuration_validator import EmbeddingConfigurationValidator
from ..schemas.embedding_validation import (
    ValidationReportResponse,
    ProviderModelInfoResponse,
    ConfigurationChangeRequest,
    ValidationStatisticsResponse,
    CompatibilityMatrixResponse,
    BotValidationResponse
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/embedding-validation", tags=["embedding-validation"])


@router.post("/validate-provider-model", response_model=ValidationReportResponse)
async def validate_provider_model(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    use_cache: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate a provider/model combination comprehensively.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        report = await validator.validate_provider_model_combination(
            provider=provider,
            model=model,
            api_key=api_key,
            use_cache=use_cache
        )
        
        return ValidationReportResponse(
            is_valid=report.is_valid,
            provider=report.provider,
            model=report.model,
            dimension=report.dimension,
            issues=[{
                "severity": issue.severity.value,
                "code": issue.code,
                "message": issue.message,
                "remediation": issue.remediation,
                "metadata": issue.metadata
            } for issue in report.issues],
            recommendations=report.recommendations,
            compatibility_score=report.compatibility_score,
            migration_required=report.migration_required,
            estimated_migration_time=report.estimated_migration_time,
            metadata=report.metadata
        )
        
    except Exception as e:
        logger.error(f"Error validating provider/model {provider}/{model}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/validate-configuration-change/{bot_id}", response_model=ValidationReportResponse)
async def validate_configuration_change(
    bot_id: uuid.UUID,
    request: ConfigurationChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate embedding configuration change for a bot.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        report = await validator.validate_configuration_change(
            bot_id=bot_id,
            new_provider=request.new_provider,
            new_model=request.new_model,
            change_reason=request.change_reason
        )
        
        return ValidationReportResponse(
            is_valid=report.is_valid,
            provider=report.provider,
            model=report.model,
            dimension=report.dimension,
            issues=[{
                "severity": issue.severity.value,
                "code": issue.code,
                "message": issue.message,
                "remediation": issue.remediation,
                "metadata": issue.metadata
            } for issue in report.issues],
            recommendations=report.recommendations,
            compatibility_score=report.compatibility_score,
            migration_required=report.migration_required,
            estimated_migration_time=report.estimated_migration_time,
            metadata=report.metadata
        )
        
    except Exception as e:
        logger.error(f"Error validating configuration change for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration change validation failed: {str(e)}"
        )


@router.get("/provider-model-info/{provider}/{model}", response_model=ProviderModelInfoResponse)
async def get_provider_model_info(
    provider: str,
    model: str,
    refresh_cache: bool = Query(False, description="Whether to refresh cached information"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive information about a provider/model combination.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        info = await validator.get_provider_model_info(
            provider=provider,
            model=model,
            refresh_cache=refresh_cache
        )
        
        return ProviderModelInfoResponse(
            provider=info.provider,
            model=info.model,
            dimension=info.dimension,
            is_available=info.is_available,
            last_validated=info.last_validated,
            validation_error=info.validation_error,
            api_requirements=info.api_requirements
        )
        
    except Exception as e:
        logger.error(f"Error getting provider/model info for {provider}/{model}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider/model info: {str(e)}"
        )


@router.get("/compatible-alternatives/{dimension}", response_model=List[ProviderModelInfoResponse])
async def get_compatible_alternatives(
    dimension: int,
    exclude_provider: Optional[str] = Query(None, description="Provider to exclude from results"),
    exclude_model: Optional[str] = Query(None, description="Model to exclude from results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get compatible provider/model alternatives with the same dimension.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        alternatives = await validator.get_compatible_alternatives(
            target_dimension=dimension,
            exclude_provider=exclude_provider,
            exclude_model=exclude_model
        )
        
        return [
            ProviderModelInfoResponse(
                provider=info.provider,
                model=info.model,
                dimension=info.dimension,
                is_available=info.is_available,
                last_validated=info.last_validated,
                validation_error=info.validation_error,
                api_requirements=info.api_requirements
            )
            for info in alternatives
        ]
        
    except Exception as e:
        logger.error(f"Error getting compatible alternatives for dimension {dimension}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compatible alternatives: {str(e)}"
        )


@router.get("/collection-metadata/{bot_id}")
async def get_collection_metadata(
    bot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get collection metadata for a bot.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        metadata = await validator.get_collection_metadata(bot_id)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection metadata not found"
            )
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection metadata for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection metadata: {str(e)}"
        )


@router.get("/configuration-history/{bot_id}")
async def get_configuration_history(
    bot_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of history entries"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get configuration change history for a bot.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        history = await validator.get_configuration_history(bot_id, limit)
        
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Error getting configuration history for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration history: {str(e)}"
        )


@router.get("/statistics", response_model=ValidationStatisticsResponse)
async def get_validation_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get validation statistics and cache performance metrics.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        stats = await validator.get_validation_statistics()
        
        return ValidationStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting validation statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation statistics: {str(e)}"
        )


@router.get("/compatibility-matrix", response_model=CompatibilityMatrixResponse)
async def get_compatibility_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a compatibility matrix showing dimension compatibility between providers.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        matrix = await validator.generate_compatibility_matrix()
        
        return CompatibilityMatrixResponse(**matrix)
        
    except Exception as e:
        logger.error(f"Error generating compatibility matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate compatibility matrix: {str(e)}"
        )


@router.get("/validate-all-providers")
async def validate_all_providers(
    refresh_cache: bool = Query(False, description="Whether to refresh cached validation results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate all available provider/model combinations.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        results = await validator.validate_all_provider_models(refresh_cache)
        
        # Convert to response format
        response = {}
        for provider, models in results.items():
            response[provider] = [
                {
                    "provider": info.provider,
                    "model": info.model,
                    "dimension": info.dimension,
                    "is_available": info.is_available,
                    "last_validated": info.last_validated.isoformat() if info.last_validated else None,
                    "validation_error": info.validation_error,
                    "api_requirements": info.api_requirements
                }
                for info in models
            ]
        
        return {"providers": response}
        
    except Exception as e:
        logger.error(f"Error validating all providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate all providers: {str(e)}"
        )


@router.get("/validate-bot-configurations", response_model=List[BotValidationResponse])
async def validate_bot_configurations(
    bot_ids: Optional[str] = Query(None, description="Comma-separated list of bot IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate embedding configurations for multiple bots.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        # Parse bot IDs if provided
        parsed_bot_ids = None
        if bot_ids:
            try:
                parsed_bot_ids = [uuid.UUID(bot_id.strip()) for bot_id in bot_ids.split(",")]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid bot ID format: {str(e)}"
                )
        
        results = await validator.validate_bot_configurations(parsed_bot_ids)
        
        return [BotValidationResponse(**result) for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating bot configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate bot configurations: {str(e)}"
        )


@router.post("/cleanup-cache")
async def cleanup_expired_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clean up expired cache entries.
    """
    try:
        validator = EmbeddingConfigurationValidator(db)
        
        result = await validator.cleanup_expired_cache()
        
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up expired cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup expired cache: {str(e)}"
        )