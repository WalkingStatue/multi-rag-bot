"""
Activity-related Pydantic schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class ActivityLogResponse(BaseModel):
    """Schema for activity log response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    action: str = Field(..., max_length=100)
    details: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}