"""
Activity logging database models.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class ActivityLog(Base):
    """Activity log model for tracking bot operations and changes."""
    
    __tablename__ = "activity_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)  # 'created', 'updated', 'deleted', 'permission_granted', etc.
    details = Column(JSONB)  # additional details about the action
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="activity_logs")
    user = relationship("User", back_populates="activity_logs")