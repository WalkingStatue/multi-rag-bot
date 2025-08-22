"""
Bot API Key schemas for request/response validation.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class BotAPIKeyCreate(BaseModel):
    """Schema for creating a new bot API key."""
    name: str = Field(..., min_length=1, max_length=255, description="User-friendly name for the API key")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the API key")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")


class BotAPIKeyUpdate(BaseModel):
    """Schema for updating an existing bot API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated name")
    description: Optional[str] = Field(None, max_length=1000, description="Updated description")
    is_active: Optional[bool] = Field(None, description="Whether the key is active")


class BotAPIKeyResponse(BaseModel):
    """Schema for bot API key responses."""
    id: uuid.UUID
    bot_id: uuid.UUID
    name: str
    description: Optional[str] = None
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_by: uuid.UUID

    class Config:
        from_attributes = True


class BotAPIKeyCreateResponse(BotAPIKeyResponse):
    """Schema for API key creation response with the plain key."""
    api_key: str = Field(..., description="The full API key - only shown once")


class BotAPIKeyListResponse(BaseModel):
    """Schema for listing bot API keys."""
    api_keys: List[BotAPIKeyResponse]
    total_count: int


class BotAPIKeyUsageResponse(BaseModel):
    """Schema for API key usage statistics."""
    key_id: uuid.UUID
    total_requests: int
    requests_last_24h: int
    requests_last_7d: int
    requests_last_30d: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
