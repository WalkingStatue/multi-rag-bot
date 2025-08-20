"""
Widget-related Pydantic schemas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid


class WidgetConfigBase(BaseModel):
    """Base widget configuration schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    allowed_domains: List[str] = Field(default_factory=list)
    require_domain_validation: bool = True
    rate_limit_per_minute: int = Field(default=20, ge=1, le=100)
    rate_limit_per_hour: int = Field(default=100, ge=1, le=1000)
    widget_title: str = Field(default="Chat Assistant", max_length=255)
    welcome_message: str = Field(default="Hello! How can I help you today?", max_length=1000)
    placeholder_text: str = Field(default="Type your message...", max_length=255)
    theme_config: Dict[str, Any] = Field(default_factory=dict)
    session_timeout_minutes: int = Field(default=30, ge=5, le=120)
    max_messages_per_session: int = Field(default=50, ge=10, le=200)
    is_active: bool = True

    @validator('allowed_domains')
    def validate_domains(cls, v):
        """Validate domain format."""
        for domain in v:
            if not domain or len(domain) > 255:
                raise ValueError("Invalid domain format")
        return v


class WidgetConfigCreate(WidgetConfigBase):
    """Schema for creating widget configuration."""
    bot_id: uuid.UUID


class WidgetConfigUpdate(BaseModel):
    """Schema for updating widget configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    allowed_domains: Optional[List[str]] = None
    require_domain_validation: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=100)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=1000)
    widget_title: Optional[str] = Field(None, max_length=255)
    welcome_message: Optional[str] = Field(None, max_length=1000)
    placeholder_text: Optional[str] = Field(None, max_length=255)
    theme_config: Optional[Dict[str, Any]] = None
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=120)
    max_messages_per_session: Optional[int] = Field(None, ge=10, le=200)
    is_active: Optional[bool] = None


class WidgetConfigResponse(WidgetConfigBase):
    """Schema for widget configuration response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    owner_id: uuid.UUID
    widget_key: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WidgetInitRequest(BaseModel):
    """Schema for widget initialization request."""
    widget_key: str = Field(..., min_length=1, max_length=64)
    domain: str = Field(..., min_length=1, max_length=255)
    visitor_id: Optional[str] = Field(None, max_length=255)
    user_agent: Optional[str] = None
    referrer: Optional[str] = None


class WidgetInitResponse(BaseModel):
    """Schema for widget initialization response."""
    session_token: str
    widget_config: Dict[str, Any]
    websocket_url: str
    expires_at: datetime


class WidgetSessionInfo(BaseModel):
    """Schema for widget session information."""
    id: uuid.UUID
    visitor_id: str
    domain: str
    message_count: int
    is_active: bool
    created_at: datetime
    last_activity: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class WidgetMessageCreate(BaseModel):
    """Schema for creating widget message."""
    content: str = Field(..., min_length=1, max_length=4000)
    role: str = Field(..., pattern="^(user|assistant)$")


class WidgetMessageResponse(BaseModel):
    """Schema for widget message response."""
    id: uuid.UUID
    content: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class WidgetStatsResponse(BaseModel):
    """Schema for widget statistics response."""
    total_sessions: int
    active_sessions: int
    total_messages: int
    messages_today: int
    average_session_duration: Optional[float]
    top_domains: List[Dict[str, Any]]