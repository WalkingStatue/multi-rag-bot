"""
Widget-related database models for embeddable chat widgets.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class WidgetConfig(Base):
    """Widget configuration for embeddable chat widgets."""
    
    __tablename__ = "widget_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Widget identification
    widget_key = Column(String(64), unique=True, nullable=False, index=True)  # Public widget identifier
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Security settings
    allowed_domains = Column(JSON, default=list)  # List of allowed domains
    require_domain_validation = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=20)
    rate_limit_per_hour = Column(Integer, default=100)
    
    # Widget appearance and behavior
    widget_title = Column(String(255), default="Chat Assistant")
    welcome_message = Column(Text, default="Hello! How can I help you today?")
    placeholder_text = Column(String(255), default="Type your message...")
    theme_config = Column(JSON, default=dict)  # Custom CSS/theme configuration
    
    # Session settings
    session_timeout_minutes = Column(Integer, default=30)
    max_messages_per_session = Column(Integer, default=50)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", backref="widget_configs")
    owner = relationship("User", backref="widget_configs")
    sessions = relationship("WidgetSession", back_populates="widget_config", cascade="all, delete-orphan")


class WidgetSession(Base):
    """Widget session for tracking individual chat sessions."""
    
    __tablename__ = "widget_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    widget_config_id = Column(UUID(as_uuid=True), ForeignKey("widget_configs.id", ondelete="CASCADE"), nullable=False)
    
    # Session identification
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    visitor_id = Column(String(255), nullable=False)  # Anonymous visitor identifier
    
    # Request metadata
    domain = Column(String(255), nullable=False)
    user_agent = Column(Text)
    ip_address = Column(String(45))  # IPv6 compatible
    referrer = Column(Text)
    
    # Session state
    message_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    widget_config = relationship("WidgetConfig", back_populates="sessions")
    messages = relationship("WidgetMessage", back_populates="session", cascade="all, delete-orphan")


class WidgetMessage(Base):
    """Messages sent through widget sessions."""
    
    __tablename__ = "widget_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("widget_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("WidgetSession", back_populates="messages")