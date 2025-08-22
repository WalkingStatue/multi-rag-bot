"""
Bot API Key database model for programmatic access to bots.
"""
import uuid
import secrets
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class BotAPIKey(Base):
    """Bot API Key model for programmatic access to bots."""
    
    __tablename__ = "bot_api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # User-friendly name for the API key
    description = Column(Text)  # Optional description
    
    # The actual API key (hashed)
    key_hash = Column(String(128), nullable=False, unique=True)
    # Key prefix for display (first 8 characters)
    key_prefix = Column(String(12), nullable=False)
    
    # Permissions and settings
    is_active = Column(Boolean, default=True)
    
    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))  # Optional expiration
    
    # Relationships
    bot = relationship("Bot", back_populates="api_keys")
    created_by_user = relationship("User", back_populates="created_bot_api_keys")
    
    def __init__(self, **kwargs):
        """Initialize with auto-generated API key if not provided."""
        if 'key_hash' not in kwargs and 'key_prefix' not in kwargs:
            # Generate a secure API key
            api_key = self._generate_api_key()
            kwargs['key_hash'] = self._hash_key(api_key)
            kwargs['key_prefix'] = api_key[:8] + "..."
            # Store the plain key temporarily for return to user
            self._plain_key = api_key
        super().__init__(**kwargs)
    
    @staticmethod
    def _generate_api_key() -> str:
        """Generate a secure API key."""
        # Generate a 32-byte random key and encode as hex
        return f"mbr_{secrets.token_hex(24)}"  # mbr = multi-bot-rag
    
    @staticmethod
    def _hash_key(api_key: str) -> str:
        """Hash an API key for secure storage."""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_key(self, api_key: str) -> bool:
        """Verify if the provided API key matches this record."""
        return self.key_hash == self._hash_key(api_key)
    
    def get_plain_key(self) -> str:
        """Get the plain API key if available (only during creation)."""
        return getattr(self, '_plain_key', None)
