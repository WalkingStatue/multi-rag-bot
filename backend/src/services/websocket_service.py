"""
WebSocket service for real-time updates and notifications.
"""
import json
import logging
from typing import Dict, Set, Optional, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from ..models.user import User
from ..models.bot import Bot
from ..services.permission_service import PermissionService
from ..core.security import verify_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Bot subscriptions: {bot_id: {user_id}}
        self.bot_subscriptions: Dict[str, Set[str]] = {}
        # Connection metadata: {connection_id: {user_id, bot_id, connected_at}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, bot_id: Optional[str] = None) -> str:
        """
        Connect a user to WebSocket.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
            bot_id: Optional bot ID for bot-specific subscriptions
            
        Returns:
            Connection ID
        """
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Store connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][connection_id] = websocket
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "bot_id": bot_id,
            "connected_at": datetime.utcnow().isoformat()
        }
        
        # Subscribe to bot if specified
        if bot_id:
            if bot_id not in self.bot_subscriptions:
                self.bot_subscriptions[bot_id] = set()
            self.bot_subscriptions[bot_id].add(user_id)
        
        logger.info(f"User {user_id} connected with connection {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect a WebSocket connection.
        
        Args:
            connection_id: Connection ID to disconnect
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        user_id = metadata["user_id"]
        bot_id = metadata.get("bot_id")
        
        # Close and remove from active connections
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id].get(connection_id)
            if websocket:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
            self.active_connections[user_id].pop(connection_id, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from bot subscriptions
        if bot_id and bot_id in self.bot_subscriptions:
            self.bot_subscriptions[bot_id].discard(user_id)
            if not self.bot_subscriptions[bot_id]:
                del self.bot_subscriptions[bot_id]
        
        # Remove metadata
        del self.connection_metadata[connection_id]
        
        logger.info(f"User {user_id} disconnected (connection {connection_id})")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to all connections of a specific user.
        
        Args:
            user_id: User ID to send message to
            message: Message to send
            
        Returns:
            True if message was sent to at least one connection
        """
        if user_id not in self.active_connections:
            return False
        
        message_str = json.dumps(message)
        sent_count = 0
        
        # Send to all user connections
        connections_to_remove = []
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_text(message_str)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}, connection {connection_id}: {e}")
                connections_to_remove.append(connection_id)
        
        # Clean up failed connections
        for connection_id in connections_to_remove:
            self.disconnect(connection_id)
        
        return sent_count > 0
    
    async def broadcast_to_bot_collaborators(
        self, 
        bot_id: str, 
        message: Dict[str, Any], 
        exclude_user: Optional[str] = None,
        db: Optional[Session] = None
    ) -> int:
        """
        Broadcast message to all collaborators of a bot.
        
        Args:
            bot_id: Bot ID
            message: Message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
            db: Database session for permission checking
            
        Returns:
            Number of users message was sent to
        """
        if bot_id not in self.bot_subscriptions:
            return 0
        
        sent_count = 0
        message_str = json.dumps(message)
        
        # Get all subscribed users for this bot
        subscribed_users = self.bot_subscriptions[bot_id].copy()
        
        # If we have a database session, verify permissions
        if db:
            permission_service = PermissionService(db)
            verified_users = []
            for user_id in subscribed_users:
                try:
                    user_uuid = uuid.UUID(user_id)
                    bot_uuid = uuid.UUID(bot_id)
                    if permission_service.check_bot_permission(user_uuid, bot_uuid, "view_bot"):
                        verified_users.append(user_id)
                    else:
                        # Remove user from subscription if they no longer have permission
                        self.bot_subscriptions[bot_id].discard(user_id)
                except (ValueError, Exception) as e:
                    logger.error(f"Error verifying permission for user {user_id} on bot {bot_id}: {e}")
            subscribed_users = verified_users
        
        # Send to all subscribed users (except excluded)
        for user_id in subscribed_users:
            if exclude_user and user_id == exclude_user:
                continue
            
            if user_id in self.active_connections:
                connections_to_remove = []
                for connection_id, websocket in self.active_connections[user_id].items():
                    try:
                        await websocket.send_text(message_str)
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Error broadcasting to user {user_id}, connection {connection_id}: {e}")
                        connections_to_remove.append(connection_id)
                
                # Clean up failed connections
                for connection_id in connections_to_remove:
                    self.disconnect(connection_id)
        
        return sent_count
    
    async def send_notification(self, user_id: str, notification_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a notification to a user.
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            data: Notification data
            
        Returns:
            True if notification was sent
        """
        message = {
            "type": "notification",
            "notification_type": notification_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_user(user_id, message)
    
    def get_connected_users(self) -> List[str]:
        """Get list of all connected user IDs."""
        return list(self.active_connections.keys())
    
    def get_bot_subscribers(self, bot_id: str) -> List[str]:
        """Get list of user IDs subscribed to a bot."""
        return list(self.bot_subscriptions.get(bot_id, set()))
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user."""
        return len(self.active_connections.get(user_id, {}))


class WebSocketService:
    """Service for managing WebSocket connections and real-time updates."""
    
    def __init__(self, db: Session):
        self.db = db
        self.permission_service = PermissionService(db)
    
    async def authenticate_websocket(self, websocket: WebSocket, token: Optional[str]) -> Optional[User]:
        """
        Authenticate WebSocket connection using JWT token.
        
        Args:
            websocket: WebSocket connection
            token: JWT token
            
        Returns:
            User object if authenticated, None otherwise
        """
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return None
        
        try:
            # Decode JWT token
            payload = verify_token(token, "access")
            if not payload:
                await websocket.close(code=4001, reason="Invalid token")
                return None
            
            username = payload.get("sub")
            if not username:
                await websocket.close(code=4001, reason="Invalid token payload")
                return None
            
            # Get user from database by username
            user = self.db.query(User).filter(User.username == username).first()
            if not user or not user.is_active:
                await websocket.close(code=4001, reason="User not found or inactive")
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await websocket.close(code=4001, reason="Authentication failed")
            return None
    
    async def verify_bot_access(self, user: User, bot_id: str) -> Optional[Bot]:
        """
        Verify user has access to a bot.
        
        Args:
            user: User object
            bot_id: Bot ID to check access for
            
        Returns:
            Bot object if user has access, None otherwise
        """
        try:
            bot_uuid = uuid.UUID(bot_id)
            
            # Check if user has at least viewer permission
            if not self.permission_service.check_bot_permission(user.id, bot_uuid, "view_bot"):
                return None
            
            # Get bot from database
            bot = self.db.query(Bot).filter(Bot.id == bot_uuid).first()
            return bot
            
        except (ValueError, Exception) as e:
            logger.error(f"Error verifying bot access: {e}")
            return None
    
    async def handle_chat_message(
        self, 
        bot_id: str, 
        message_data: Dict[str, Any], 
        sender_user_id: str
    ):
        """
        Handle real-time chat message broadcast.
        
        Args:
            bot_id: Bot ID
            message_data: Message data to broadcast
            sender_user_id: User ID of message sender
        """
        broadcast_message = {
            "type": "chat_message",
            "bot_id": bot_id,
            "data": message_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast_to_bot_collaborators(
            bot_id=bot_id,
            message=broadcast_message,
            exclude_user=sender_user_id,
            db=self.db
        )
    
    async def handle_typing_indicator(
        self, 
        bot_id: str, 
        user_id: str, 
        username: str, 
        is_typing: bool
    ):
        """
        Handle typing indicator broadcast.
        
        Args:
            bot_id: Bot ID
            user_id: User ID
            username: Username
            is_typing: Whether user is typing
        """
        broadcast_message = {
            "type": "typing_indicator",
            "bot_id": bot_id,
            "data": {
                "user_id": user_id,
                "username": username,
                "is_typing": is_typing
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast_to_bot_collaborators(
            bot_id=bot_id,
            message=broadcast_message,
            exclude_user=user_id,
            db=self.db
        )
    
    async def handle_permission_change(
        self, 
        bot_id: str, 
        target_user_id: str, 
        action: str, 
        details: Dict[str, Any]
    ):
        """
        Handle permission change notifications.
        
        Args:
            bot_id: Bot ID
            target_user_id: User ID whose permissions changed
            action: Action performed (granted, revoked, updated)
            details: Additional details about the change
        """
        # Notify the target user
        await connection_manager.send_notification(
            user_id=target_user_id,
            notification_type="permission_change",
            data={
                "bot_id": bot_id,
                "action": action,
                "details": details
            }
        )
        
        # Broadcast to all bot collaborators
        broadcast_message = {
            "type": "permission_change",
            "bot_id": bot_id,
            "data": {
                "target_user_id": target_user_id,
                "action": action,
                "details": details
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast_to_bot_collaborators(
            bot_id=bot_id,
            message=broadcast_message,
            db=self.db
        )
    
    async def handle_bot_update(
        self, 
        bot_id: str, 
        update_type: str, 
        details: Dict[str, Any],
        updated_by: str
    ):
        """
        Handle bot update notifications.
        
        Args:
            bot_id: Bot ID
            update_type: Type of update (config, name, etc.)
            details: Update details
            updated_by: User ID who made the update
        """
        broadcast_message = {
            "type": "bot_update",
            "bot_id": bot_id,
            "data": {
                "update_type": update_type,
                "details": details,
                "updated_by": updated_by
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast_to_bot_collaborators(
            bot_id=bot_id,
            message=broadcast_message,
            exclude_user=updated_by,
            db=self.db
        )
    
    async def handle_document_update(
        self, 
        bot_id: str, 
        action: str, 
        document_data: Dict[str, Any],
        user_id: str
    ):
        """
        Handle document update notifications.
        
        Args:
            bot_id: Bot ID
            action: Action performed (uploaded, deleted, processed)
            document_data: Document data
            user_id: User ID who performed the action
        """
        broadcast_message = {
            "type": "document_update",
            "bot_id": bot_id,
            "data": {
                "action": action,
                "document": document_data,
                "user_id": user_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast_to_bot_collaborators(
            bot_id=bot_id,
            message=broadcast_message,
            exclude_user=user_id,
            db=self.db
        )


# Global connection manager instance
connection_manager = ConnectionManager()