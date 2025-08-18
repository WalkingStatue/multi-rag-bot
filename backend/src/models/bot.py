"""
Bot-related database models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Float, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class Bot(Base):
    """Bot model for AI assistant configuration."""
    
    __tablename__ = "bots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # LLM Configuration
    llm_provider = Column(String(50), nullable=False, default="openai")  # 'openai', 'anthropic', 'openrouter', 'gemini'
    llm_model = Column(String(100), nullable=False, default="gpt-3.5-turbo")
    
    # Embedding Configuration
    embedding_provider = Column(String(50), default="openai")  # provider for embeddings
    embedding_model = Column(String(100), default="text-embedding-3-small")
    
    # Model Parameters
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    top_p = Column(Float, default=1.0)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    
    # Bot Settings
    is_public = Column(Boolean, default=False)
    allow_collaboration = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="owned_bots")
    permissions = relationship("BotPermission", back_populates="bot", cascade="all, delete-orphan")
    conversation_sessions = relationship("ConversationSession", back_populates="bot", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="bot", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="bot", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="bot", cascade="all, delete-orphan")
    collection_metadata = relationship("CollectionMetadata", back_populates="bot", uselist=False, cascade="all, delete-orphan")


class BotPermission(Base):
    """Bot permissions for role-based access control."""
    
    __tablename__ = "bot_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'owner', 'admin', 'editor', 'viewer'
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="permissions")
    user = relationship("User", back_populates="bot_permissions", foreign_keys=[user_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])
    
    # Unique constraint on bot_id and user_id
    __table_args__ = (
        UniqueConstraint('bot_id', 'user_id', name='uq_bot_user'),
    )