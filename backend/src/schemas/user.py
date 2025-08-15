"""
User-related Pydantic schemas for API validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import uuid


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user updates."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: uuid.UUID
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class Token(BaseModel):
    """Schema for authentication token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data."""
    username: Optional[str] = None


class RefreshToken(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserSearch(BaseModel):
    """Schema for user search results."""
    id: uuid.UUID
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


# API Key schemas
class APIKeyBase(BaseModel):
    """Base API key schema."""
    provider: str = Field(..., pattern="^(openai|anthropic|openrouter|gemini)$")


class APIKeyCreate(APIKeyBase):
    """Schema for API key creation."""
    api_key: str = Field(..., min_length=10)


class APIKeyUpdate(BaseModel):
    """Schema for API key updates."""
    api_key: str = Field(..., min_length=10)
    is_active: Optional[bool] = True


class APIKeyResponse(APIKeyBase):
    """Schema for API key response."""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Note: We don't return the actual API key for security

    model_config = {"from_attributes": True}


# User Settings and Preferences schemas
class UserSettings(BaseModel):
    """Schema for user settings and preferences."""
    theme: Optional[str] = Field("light", pattern="^(light|dark|auto)$")
    language: Optional[str] = Field("en", max_length=10)
    timezone: Optional[str] = Field("UTC", max_length=50)
    notifications_enabled: Optional[bool] = True
    email_notifications: Optional[bool] = True
    default_llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic|openrouter|gemini)$")
    default_embedding_provider: Optional[str] = Field(None, pattern="^(openai|gemini)$")
    max_conversation_history: Optional[int] = Field(50, ge=10, le=200)
    auto_save_conversations: Optional[bool] = True


class UserSettingsUpdate(BaseModel):
    """Schema for user settings updates."""
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    default_llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic|openrouter|gemini)$")
    default_embedding_provider: Optional[str] = Field(None, pattern="^(openai|gemini)$")
    max_conversation_history: Optional[int] = Field(None, ge=10, le=200)
    auto_save_conversations: Optional[bool] = None


class UserSettingsResponse(UserSettings):
    """Schema for user settings response."""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# User Activity and Analytics schemas
class UserActivitySummary(BaseModel):
    """Schema for user activity summary."""
    total_bots: int
    total_conversations: int
    total_messages: int
    total_documents_uploaded: int
    most_used_bot: Optional[str] = None
    most_used_provider: Optional[str] = None
    activity_last_30_days: int
    created_at: datetime


class BotUsageStats(BaseModel):
    """Schema for bot usage statistics."""
    bot_id: uuid.UUID
    bot_name: str
    message_count: int
    conversation_count: int
    document_count: int
    last_used: Optional[datetime] = None
    avg_response_time: Optional[float] = None


class ConversationAnalytics(BaseModel):
    """Schema for conversation analytics."""
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    most_active_bot: Optional[str] = None
    conversations_by_day: List[dict]  # [{date: str, count: int}]
    messages_by_day: List[dict]  # [{date: str, count: int}]


class UserAnalytics(BaseModel):
    """Schema for comprehensive user analytics."""
    activity_summary: UserActivitySummary
    bot_usage: List[BotUsageStats]
    conversation_analytics: ConversationAnalytics
    provider_usage: dict  # {provider: usage_count}
    recent_activity: List[dict]  # Recent activity logs