"""
Pydantic schemas package for API request/response validation.
"""
from .user import (
    UserCreate, UserUpdate, UserResponse, UserLogin, 
    APIKeyCreate, APIKeyResponse, APIKeyUpdate
)
from .bot import (
    BotCreate, BotUpdate, BotResponse, BotPermissionCreate,
    BotPermissionUpdate, BotPermissionResponse
)
from .conversation import (
    ConversationSessionCreate, ConversationSessionResponse,
    MessageCreate, MessageResponse, ChatRequest, ChatResponse
)
from .document import (
    DocumentResponse, DocumentUpload, DocumentChunkResponse
)
from .activity import ActivityLogResponse

__all__ = [
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin",
    "APIKeyCreate", "APIKeyResponse", "APIKeyUpdate",
    
    # Bot schemas
    "BotCreate", "BotUpdate", "BotResponse", 
    "BotPermissionCreate", "BotPermissionUpdate", "BotPermissionResponse",
    
    # Conversation schemas
    "ConversationSessionCreate", "ConversationSessionResponse",
    "MessageCreate", "MessageResponse", "ChatRequest", "ChatResponse",
    
    # Document schemas
    "DocumentResponse", "DocumentUpload", "DocumentChunkResponse",
    
    # Activity schemas
    "ActivityLogResponse",
]