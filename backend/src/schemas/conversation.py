"""
Conversation-related Pydantic schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class ConversationSessionBase(BaseModel):
    """Base conversation session schema."""
    title: Optional[str] = Field(None, max_length=255)
    is_shared: Optional[bool] = False


class ConversationSessionCreate(ConversationSessionBase):
    """Schema for conversation session creation."""
    bot_id: uuid.UUID


class ConversationSessionResponse(ConversationSessionBase):
    """Schema for conversation session response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Message schemas
class MessageBase(BaseModel):
    """Base message schema."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    """Schema for message creation."""
    session_id: uuid.UUID
    message_metadata: Optional[Dict[str, Any]] = None


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: uuid.UUID
    session_id: uuid.UUID
    bot_id: uuid.UUID
    user_id: uuid.UUID
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Chat schemas
class ChatRequest(BaseModel):
    """Schema for chat request."""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[uuid.UUID] = None  # If None, creates new session


class ChatResponse(BaseModel):
    """Schema for chat response."""
    message: str
    session_id: uuid.UUID
    chunks_used: List[str] = []
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None