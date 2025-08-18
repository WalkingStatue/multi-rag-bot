"""
User-related database models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class User(Base):
    """User model for authentication and profile management."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", cascade="all, delete-orphan", uselist=False)
    owned_bots = relationship("Bot", back_populates="owner", cascade="all, delete-orphan")
    bot_permissions = relationship("BotPermission", back_populates="user", cascade="all, delete-orphan", foreign_keys="BotPermission.user_id")
    conversation_sessions = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    uploaded_documents = relationship("Document", back_populates="uploaded_by_user")
    activity_logs = relationship("ActivityLog", back_populates="user")


class UserAPIKey(Base):
    """User API keys for different LLM providers."""
    
    __tablename__ = "user_api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'openai', 'anthropic', 'openrouter', 'gemini'
    api_key_encrypted = Column(Text, nullable=False)  # encrypted API key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Unique constraint on user_id and provider
    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )


class UserSettings(Base):
    """User settings and preferences."""
    
    __tablename__ = "user_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    theme = Column(String(20), default="light")  # 'light', 'dark', 'auto'
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    notifications_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    default_llm_provider = Column(String(50))  # 'openai', 'anthropic', 'openrouter', 'gemini'
    default_embedding_provider = Column(String(50))  # 'openai', 'gemini', 'local'
    max_conversation_history = Column(Integer, default=50)
    auto_save_conversations = Column(Boolean, default=True)
    custom_settings = Column(JSONB)  # For additional custom settings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")