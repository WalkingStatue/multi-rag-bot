"""
Threshold performance tracking models.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class ThresholdPerformanceLog(Base):
    """Database model for tracking threshold performance."""
    
    __tablename__ = "threshold_performance_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Threshold information
    threshold_used = Column(Float, nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    
    # Query information
    query_length = Column(Integer, nullable=False)
    query_hash = Column(String(64))  # SHA-256 hash for privacy
    
    # Results information
    results_found = Column(Integer, nullable=False)
    avg_score = Column(Float)
    max_score = Column(Float)
    min_score = Column(Float)
    
    # Performance metrics
    processing_time = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False)
    adjustment_reason = Column(String(50))
    
    # Additional context
    additional_metadata = Column(JSONB)