"""
Bot-related Pydantic schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class BotBase(BaseModel):
    """Base bot schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)


class BotCreate(BotBase):
    """Schema for bot creation."""
    llm_provider: str = Field("openai", pattern="^(openai|anthropic|openrouter|gemini)$")
    llm_model: str = Field("gpt-3.5-turbo", max_length=100)
    embedding_provider: Optional[str] = Field("openai", pattern="^(openai|gemini|local)$")
    embedding_model: Optional[str] = Field("text-embedding-3-small", max_length=100)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(1000, ge=1, le=8000)
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0)
    is_public: Optional[bool] = False
    allow_collaboration: Optional[bool] = True


class BotUpdate(BaseModel):
    """Schema for bot updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic|openrouter|gemini)$")
    llm_model: Optional[str] = Field(None, max_length=100)
    embedding_provider: Optional[str] = Field(None, pattern="^(openai|gemini|local)$")
    embedding_model: Optional[str] = Field(None, max_length=100)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8000)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    is_public: Optional[bool] = None
    allow_collaboration: Optional[bool] = None


class BotResponse(BotBase):
    """Schema for bot response."""
    id: uuid.UUID
    owner_id: uuid.UUID
    llm_provider: str
    llm_model: str
    embedding_provider: Optional[str]
    embedding_model: Optional[str]
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    is_public: bool
    allow_collaboration: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Bot Permission schemas
class BotPermissionBase(BaseModel):
    """Base bot permission schema."""
    role: str = Field(..., pattern="^(owner|admin|editor|viewer)$")


class BotPermissionCreate(BotPermissionBase):
    """Schema for bot permission creation."""
    user_id: uuid.UUID


class BotPermissionUpdate(BaseModel):
    """Schema for bot permission updates."""
    role: str = Field(..., pattern="^(owner|admin|editor|viewer)$")


class BotPermissionResponse(BotPermissionBase):
    """Schema for bot permission response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    user_id: uuid.UUID
    granted_by: Optional[uuid.UUID]
    granted_at: datetime

    model_config = {"from_attributes": True}


class BotTransferRequest(BaseModel):
    """Schema for bot ownership transfer request."""
    new_owner_id: uuid.UUID


# Collaboration and invitation schemas
class CollaboratorInvite(BaseModel):
    """Schema for inviting collaborators by email or username."""
    identifier: str = Field(..., min_length=1, max_length=255)  # email or username
    role: str = Field(..., pattern="^(admin|editor|viewer)$")
    message: Optional[str] = Field(None, max_length=500)  # optional invitation message


class BulkPermissionUpdate(BaseModel):
    """Schema for bulk permission updates."""
    user_permissions: List[Dict[str, Any]] = Field(..., min_items=1, max_items=50)
    # Each item should have: {"user_id": "uuid", "role": "role_name"}


class PermissionHistoryResponse(BaseModel):
    """Schema for permission history response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    action: str  # 'granted', 'updated', 'revoked'
    old_role: Optional[str]
    new_role: Optional[str]
    granted_by: Optional[uuid.UUID]
    granted_by_username: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityLogResponse(BaseModel):
    """Schema for activity log response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    username: Optional[str]
    action: str
    details: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class CollaboratorInviteResponse(BaseModel):
    """Schema for collaborator invitation response."""
    success: bool
    message: str
    user_id: Optional[uuid.UUID] = None
    permission: Optional[BotPermissionResponse] = None


# Embedding Migration schemas
class EmbeddingValidationRequest(BaseModel):
    """Schema for embedding validation request."""
    provider: str = Field(..., pattern="^(openai|gemini|anthropic|local)$")
    model: str = Field(..., max_length=100)


class EmbeddingValidationResponse(BaseModel):
    """Schema for embedding validation response."""
    compatible: bool
    issues: List[str] = []
    recommendations: List[str] = []
    migration_required: bool
    current_config: Optional[Dict[str, Any]] = None
    target_config: Optional[Dict[str, Any]] = None


class MigrationEstimateRequest(BaseModel):
    """Schema for migration time estimation request."""
    batch_size: int = Field(50, ge=1, le=500)


class MigrationEstimateResponse(BaseModel):
    """Schema for migration time estimation response."""
    total_chunks: int
    total_batches: int
    estimated_time_seconds: int
    estimated_time_human: str
    batch_size: int
    error: Optional[str] = None


class MigrationStartRequest(BaseModel):
    """Schema for starting migration."""
    provider: str = Field(..., pattern="^(openai|gemini|anthropic|local)$")
    model: str = Field(..., max_length=100)
    batch_size: int = Field(50, ge=1, le=500)


class MigrationProgressResponse(BaseModel):
    """Schema for migration progress response."""
    migration_id: str
    bot_id: str
    status: str
    phase: str
    progress: Dict[str, Any]
    timing: Dict[str, Any]
    rollback_available: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MigrationStatusResponse(BaseModel):
    """Schema for migration status response."""
    migration_id: Optional[str] = None
    status: str
    phase: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    start_time: Optional[float] = None
    last_update: Optional[float] = None
    error_message: Optional[str] = None
    rollback_available: bool = False


class DimensionInfoResponse(BaseModel):
    """Schema for dimension information response."""
    provider: str
    model: str
    dimension: int
    compatible_providers: List[str] = []
    migration_required: bool


class ActiveMigrationsResponse(BaseModel):
    """Schema for active migrations response."""
    active_migrations: Dict[str, Dict[str, Any]]
    total_count: int


class MigrationActionResponse(BaseModel):
    """Schema for migration action responses (cancel, rollback)."""
    message: str
    success: bool = True