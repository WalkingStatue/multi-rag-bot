"""
Collection metadata database models for tracking embedding dimensions and configuration.
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class CollectionMetadata(Base):
    """Collection metadata model for tracking embedding configuration and dimensions."""
    
    __tablename__ = "collection_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, unique=True)
    collection_name = Column(String(255), nullable=False)
    
    # Current embedding configuration
    embedding_provider = Column(String(50), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    
    # Collection status
    status = Column(String(20), default="active")  # 'active', 'migrating', 'deprecated'
    points_count = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Additional metadata
    configuration_history = Column(JSONB)  # Track configuration changes
    migration_info = Column(JSONB)  # Track migration information
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="collection_metadata")


class EmbeddingConfigurationHistory(Base):
    """History of embedding configuration changes for audit and rollback purposes."""
    
    __tablename__ = "embedding_configuration_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    
    # Previous configuration
    previous_provider = Column(String(50))
    previous_model = Column(String(100))
    previous_dimension = Column(Integer)
    
    # New configuration
    new_provider = Column(String(50), nullable=False)
    new_model = Column(String(100), nullable=False)
    new_dimension = Column(Integer, nullable=False)
    
    # Change metadata
    change_reason = Column(Text)
    migration_required = Column(Boolean, default=False)
    migration_completed = Column(Boolean, default=False)
    migration_id = Column(String(100))  # Reference to migration process
    
    # Audit information
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metadata
    extra_metadata = Column(JSONB)
    
    # Relationships
    bot = relationship("Bot")
    changed_by_user = relationship("User")


class DimensionCompatibilityCache(Base):
    """Cache for dimension compatibility information to avoid repeated API calls."""
    
    __tablename__ = "dimension_compatibility_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Provider and model information
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    dimension = Column(Integer, nullable=False)
    
    # Validation status
    is_valid = Column(Boolean, default=True)
    last_validated = Column(DateTime(timezone=True), server_default=func.now())
    validation_error = Column(Text)
    
    # Cache metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Unique constraint on provider and model
    __table_args__ = (
        {"schema": None}  # Ensure it uses the default schema
    )