"""
Pydantic schemas for embedding validation API responses.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ValidationIssueResponse(BaseModel):
    """Response model for validation issues."""
    severity: str = Field(..., description="Issue severity level")
    code: str = Field(..., description="Issue code")
    message: str = Field(..., description="Issue message")
    remediation: str = Field(..., description="Remediation steps")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ValidationReportResponse(BaseModel):
    """Response model for validation reports."""
    is_valid: bool = Field(..., description="Whether the configuration is valid")
    provider: str = Field(..., description="Embedding provider")
    model: str = Field(..., description="Embedding model")
    dimension: int = Field(..., description="Embedding dimension")
    issues: List[ValidationIssueResponse] = Field(default_factory=list, description="Validation issues")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    compatibility_score: float = Field(..., description="Compatibility score (0.0 to 1.0)")
    migration_required: bool = Field(..., description="Whether migration is required")
    estimated_migration_time: Optional[str] = Field(None, description="Estimated migration time")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ProviderModelInfoResponse(BaseModel):
    """Response model for provider/model information."""
    provider: str = Field(..., description="Embedding provider")
    model: str = Field(..., description="Embedding model")
    dimension: int = Field(..., description="Embedding dimension")
    is_available: bool = Field(..., description="Whether the model is available")
    last_validated: Optional[datetime] = Field(None, description="Last validation timestamp")
    validation_error: Optional[str] = Field(None, description="Validation error message")
    api_requirements: Optional[Dict[str, Any]] = Field(None, description="API requirements")


class ConfigurationChangeRequest(BaseModel):
    """Request model for configuration changes."""
    new_provider: str = Field(..., description="New embedding provider")
    new_model: str = Field(..., description="New embedding model")
    change_reason: Optional[str] = Field(None, description="Reason for the change")


class CacheStatistics(BaseModel):
    """Cache statistics model."""
    total_cached_validations: int = Field(..., description="Total cached validations")
    valid_configurations: int = Field(..., description="Number of valid configurations")
    invalid_configurations: int = Field(..., description="Number of invalid configurations")
    recent_validations_24h: int = Field(..., description="Recent validations in last 24 hours")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")


class ConfigurationHistoryStatistics(BaseModel):
    """Configuration history statistics model."""
    total_configuration_changes: int = Field(..., description="Total configuration changes")
    migrations_required: int = Field(..., description="Number of migrations required")
    migrations_completed: int = Field(..., description="Number of migrations completed")


class ValidationStatisticsResponse(BaseModel):
    """Response model for validation statistics."""
    cache_statistics: CacheStatistics = Field(..., description="Cache performance statistics")
    configuration_history: ConfigurationHistoryStatistics = Field(..., description="Configuration history statistics")
    last_updated: str = Field(..., description="Last updated timestamp")


class CompatibilityRecommendation(BaseModel):
    """Compatibility recommendation model."""
    dimension: int = Field(..., description="Embedding dimension")
    compatible_providers: List[str] = Field(..., description="Compatible providers")
    model_count: int = Field(..., description="Number of compatible models")
    models: List[Dict[str, Any]] = Field(..., description="Compatible models")


class CompatibilityMatrixResponse(BaseModel):
    """Response model for compatibility matrix."""
    dimension_groups: Dict[str, List[Dict[str, Any]]] = Field(..., description="Models grouped by dimension")
    provider_models: Dict[str, List[Dict[str, Any]]] = Field(..., description="Models grouped by provider")
    compatibility_recommendations: List[CompatibilityRecommendation] = Field(..., description="Compatibility recommendations")
    total_dimensions: int = Field(..., description="Total number of dimensions")
    total_compatible_groups: int = Field(..., description="Total number of compatible groups")
    generated_at: str = Field(..., description="Generation timestamp")


class BotValidationInfo(BaseModel):
    """Bot validation information model."""
    is_valid: bool = Field(..., description="Whether the bot configuration is valid")
    compatibility_score: float = Field(..., description="Compatibility score")
    issues_count: int = Field(..., description="Number of validation issues")
    critical_issues: int = Field(..., description="Number of critical issues")
    migration_required: bool = Field(..., description="Whether migration is required")
    error: Optional[str] = Field(None, description="Validation error message")


class BotValidationResponse(BaseModel):
    """Response model for bot validation."""
    bot_id: str = Field(..., description="Bot identifier")
    bot_name: str = Field(..., description="Bot name")
    provider: Optional[str] = Field(None, description="Embedding provider")
    model: Optional[str] = Field(None, description="Embedding model")
    validation: BotValidationInfo = Field(..., description="Validation information")
    collection_metadata: Optional[Dict[str, Any]] = Field(None, description="Collection metadata")
    last_validated: str = Field(..., description="Last validation timestamp")


class CollectionMetadataResponse(BaseModel):
    """Response model for collection metadata."""
    bot_id: str = Field(..., description="Bot identifier")
    collection_name: str = Field(..., description="Collection name")
    embedding_provider: str = Field(..., description="Embedding provider")
    embedding_model: str = Field(..., description="Embedding model")
    embedding_dimension: int = Field(..., description="Embedding dimension")
    status: str = Field(..., description="Collection status")
    points_count: int = Field(..., description="Number of points in collection")
    last_updated: str = Field(..., description="Last updated timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    configuration_history: Optional[Dict[str, Any]] = Field(None, description="Configuration history")
    migration_info: Optional[Dict[str, Any]] = Field(None, description="Migration information")


class ConfigurationHistoryEntry(BaseModel):
    """Configuration history entry model."""
    id: str = Field(..., description="History entry identifier")
    bot_id: str = Field(..., description="Bot identifier")
    previous_provider: Optional[str] = Field(None, description="Previous embedding provider")
    previous_model: Optional[str] = Field(None, description="Previous embedding model")
    previous_dimension: Optional[int] = Field(None, description="Previous embedding dimension")
    new_provider: str = Field(..., description="New embedding provider")
    new_model: str = Field(..., description="New embedding model")
    new_dimension: int = Field(..., description="New embedding dimension")
    change_reason: Optional[str] = Field(None, description="Reason for the change")
    migration_required: bool = Field(..., description="Whether migration was required")
    migration_completed: bool = Field(..., description="Whether migration was completed")
    migration_id: Optional[str] = Field(None, description="Migration identifier")
    changed_by: Optional[str] = Field(None, description="User who made the change")
    changed_at: str = Field(..., description="Change timestamp")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ConfigurationHistoryResponse(BaseModel):
    """Response model for configuration history."""
    history: List[ConfigurationHistoryEntry] = Field(..., description="Configuration history entries")


class CacheCleanupResponse(BaseModel):
    """Response model for cache cleanup."""
    expired_entries_removed: int = Field(..., description="Number of expired entries removed")
    cleanup_timestamp: str = Field(..., description="Cleanup timestamp")
    error: Optional[str] = Field(None, description="Error message if cleanup failed")


class AllProvidersValidationResponse(BaseModel):
    """Response model for all providers validation."""
    providers: Dict[str, List[ProviderModelInfoResponse]] = Field(..., description="Validation results by provider")