"""
WebSocket message schemas for type safety and validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime
import uuid


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""
    type: str
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConnectionEstablishedMessage(WebSocketMessage):
    """Connection established message."""
    type: Literal["connection_established"] = "connection_established"
    data: Dict[str, Any]


class ChatMessage(WebSocketMessage):
    """Chat message for real-time updates."""
    type: Literal["chat_message"] = "chat_message"
    bot_id: str
    data: Dict[str, Any]


class TypingIndicatorMessage(WebSocketMessage):
    """Typing indicator message."""
    type: Literal["typing_indicator"] = "typing_indicator"
    bot_id: str
    data: Dict[str, Any]


class PermissionChangeMessage(WebSocketMessage):
    """Permission change notification."""
    type: Literal["permission_change"] = "permission_change"
    bot_id: str
    data: Dict[str, Any]


class BotUpdateMessage(WebSocketMessage):
    """Bot update notification."""
    type: Literal["bot_update"] = "bot_update"
    bot_id: str
    data: Dict[str, Any]


class DocumentUpdateMessage(WebSocketMessage):
    """Document update notification."""
    type: Literal["document_update"] = "document_update"
    bot_id: str
    data: Dict[str, Any]


class NotificationMessage(WebSocketMessage):
    """General notification message."""
    type: Literal["notification"] = "notification"
    notification_type: str
    data: Dict[str, Any]


class ErrorMessage(WebSocketMessage):
    """Error message."""
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None


class PingMessage(WebSocketMessage):
    """Ping message for connection health."""
    type: Literal["ping"] = "ping"


class PongMessage(WebSocketMessage):
    """Pong response message."""
    type: Literal["pong"] = "pong"


# Client-to-server message schemas
class ClientTypingMessage(BaseModel):
    """Client typing indicator message."""
    type: Literal["typing"] = "typing"
    data: Dict[str, Any]


class ClientPingMessage(BaseModel):
    """Client ping message."""
    type: Literal["ping"] = "ping"
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())


# WebSocket connection info schemas
class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    connection_id: str
    user_id: str
    bot_id: Optional[str] = None
    connected_at: str


class WebSocketStats(BaseModel):
    """WebSocket connection statistics."""
    total_connections: int
    connected_users: int
    bot_subscriptions: int


class WebSocketConnectionDetails(BaseModel):
    """Detailed WebSocket connection information."""
    connected_users: list[str]
    bot_subscriptions: Dict[str, list[str]]
    connection_metadata: Dict[str, Dict[str, Any]]


# Real-time event data schemas
class ChatMessageData(BaseModel):
    """Chat message data for real-time updates."""
    message_id: str
    session_id: str
    user_id: str
    username: str
    content: str
    role: Literal["user", "assistant"]
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class TypingIndicatorData(BaseModel):
    """Typing indicator data."""
    user_id: str
    username: str
    is_typing: bool


class PermissionChangeData(BaseModel):
    """Permission change data."""
    target_user_id: str
    action: Literal["granted", "revoked", "updated"]
    role: Optional[str] = None
    old_role: Optional[str] = None
    new_role: Optional[str] = None
    granted_by: Optional[str] = None


class BotUpdateData(BaseModel):
    """Bot update data."""
    update_type: str
    details: Dict[str, Any]
    updated_by: str


class DocumentUpdateData(BaseModel):
    """Document update data."""
    action: Literal["uploaded", "deleted", "processed"]
    document: Dict[str, Any]
    user_id: str


class NotificationData(BaseModel):
    """General notification data."""
    title: str
    message: str
    level: Literal["info", "success", "warning", "error"] = "info"
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None