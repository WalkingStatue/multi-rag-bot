"""
WebSocket service for widget chat sessions.
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..core.security import verify_token
from ..services.widget_service import WidgetService
from ..services.chat_service import ChatService
from ..models.widget import WidgetSession

logger = logging.getLogger(__name__)


class WidgetWebSocketService:
    """Service for handling widget WebSocket connections."""
    
    def __init__(self, db: Session):
        self.db = db
        self.widget_service = WidgetService(db)
        self.chat_service = ChatService(db)
    
    async def authenticate_widget_session(self, websocket: WebSocket, session_token: str) -> Optional[WidgetSession]:
        """
        Authenticate widget session using JWT token.
        
        Args:
            websocket: WebSocket connection
            session_token: JWT session token
            
        Returns:
            Widget session if valid, None otherwise
        """
        try:
            # Verify JWT token
            payload = verify_token(session_token, "access")
            if not payload or payload.get("type") != "widget_session":
                await websocket.close(code=4001, reason="Invalid token")
                return None
            
            # Get session from database
            session_id = payload.get("sub")
            if not session_id:
                await websocket.close(code=4001, reason="Invalid token payload")
                return None
            
            session = self.db.query(WidgetSession).filter(
                WidgetSession.id == session_id
            ).first()
            
            if not session or not session.is_active or session.expires_at < datetime.utcnow():
                await websocket.close(code=4002, reason="Session expired or invalid")
                return None
            
            return session
        
        except Exception as e:
            logger.error(f"Widget authentication error: {e}")
            await websocket.close(code=4001, reason="Authentication failed")
            return None
    
    async def handle_widget_connection(self, websocket: WebSocket, session_token: str):
        """
        Handle widget WebSocket connection lifecycle.
        
        Args:
            websocket: WebSocket connection
            session_token: JWT session token
        """
        # Accept connection
        await websocket.accept()
        
        # Authenticate session
        session = await self.authenticate_widget_session(websocket, session_token)
        if not session:
            return
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "session_id": str(session.id),
                "visitor_id": session.visitor_id,
                "widget_title": session.widget_config.widget_title,
                "welcome_message": session.widget_config.welcome_message,
                "max_messages": session.widget_config.max_messages_per_session,
                "current_message_count": session.message_count
            }
        }))
        
        # Send chat history if any
        messages = self.widget_service.get_session_messages(session)
        if messages:
            await websocket.send_text(json.dumps({
                "type": "chat_history",
                "data": {
                    "messages": [
                        {
                            "id": str(msg.id),
                            "content": msg.content,
                            "role": msg.role,
                            "timestamp": msg.created_at.isoformat()
                        }
                        for msg in messages
                    ]
                }
            }))
        
        # Handle messages
        try:
            while True:
                data = await websocket.receive_text()
                await self.handle_widget_message(websocket, session, data)
        
        except WebSocketDisconnect:
            logger.info(f"Widget session {session.id} disconnected")
        
        except Exception as e:
            logger.error(f"Error in widget connection: {e}")
            await websocket.close(code=1011, reason="Internal server error")
    
    async def handle_widget_message(self, websocket: WebSocket, session: WidgetSession, data: str):
        """
        Handle incoming widget message.
        
        Args:
            websocket: WebSocket connection
            session: Widget session
            data: Raw message data
        """
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "chat_message":
                await self.handle_chat_message(websocket, session, message)
            
            elif message_type == "typing":
                # Echo typing indicator back (for multi-user scenarios)
                await websocket.send_text(json.dumps({
                    "type": "typing_echo",
                    "data": message.get("data", {})
                }))
            
            elif message_type == "ping":
                # Handle ping/pong for connection health
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                }))
            
            else:
                logger.warning(f"Unknown widget message type: {message_type}")
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from widget")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid message format"
            }))
        
        except Exception as e:
            logger.error(f"Error handling widget message: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Error processing message"
            }))
    
    async def handle_chat_message(self, websocket: WebSocket, session: WidgetSession, message: Dict[str, Any]):
        """
        Handle chat message from widget.
        
        Args:
            websocket: WebSocket connection
            session: Widget session
            message: Message data
        """
        try:
            content = message.get("data", {}).get("content", "").strip()
            if not content:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Message content cannot be empty"
                }))
                return
            
            # Check message limits
            if session.message_count >= session.widget_config.max_messages_per_session:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Message limit reached for this session"
                }))
                return
            
            # Save user message
            user_message = self.widget_service.add_message_to_session(session, content, "user")
            
            # Send user message confirmation
            await websocket.send_text(json.dumps({
                "type": "message_received",
                "data": {
                    "id": str(user_message.id),
                    "content": content,
                    "role": "user",
                    "timestamp": user_message.created_at.isoformat()
                }
            }))
            
            # Send typing indicator for bot
            await websocket.send_text(json.dumps({
                "type": "bot_typing",
                "data": {"is_typing": True}
            }))
            
            # Get bot response
            try:
                # Get conversation history for context
                messages = self.widget_service.get_session_messages(session)
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
                
                # Generate bot response using the chat service
                bot_response = await self.generate_bot_response(
                    session.widget_config.bot,
                    conversation_history,
                    session.widget_config.bot.system_prompt
                )
                
                # Save bot message
                bot_message = self.widget_service.add_message_to_session(
                    session, bot_response, "assistant"
                )
                
                # Send bot response
                await websocket.send_text(json.dumps({
                    "type": "bot_message",
                    "data": {
                        "id": str(bot_message.id),
                        "content": bot_response,
                        "role": "assistant",
                        "timestamp": bot_message.created_at.isoformat()
                    }
                }))
            
            except Exception as e:
                logger.error(f"Error generating bot response: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Sorry, I'm having trouble responding right now. Please try again."
                }))
            
            finally:
                # Stop typing indicator
                await websocket.send_text(json.dumps({
                    "type": "bot_typing",
                    "data": {"is_typing": False}
                }))
        
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Error processing your message"
            }))
    
    async def generate_bot_response(self, bot, conversation_history, system_prompt: str) -> str:
        """
        Generate bot response using the chat service.
        
        Args:
            bot: Bot configuration
            conversation_history: List of previous messages
            system_prompt: System prompt for the bot
            
        Returns:
            Generated response text
        """
        try:
            # Use the existing chat service to generate response
            # This maintains consistency with the main chat functionality
            response = await self.chat_service.generate_response(
                bot_id=bot.id,
                messages=conversation_history,
                system_prompt=system_prompt,
                user_id=bot.owner_id  # Use bot owner's credentials
            )
            
            return response.get("content", "I'm sorry, I couldn't generate a response.")
        
        except Exception as e:
            logger.error(f"Error in bot response generation: {e}")
            return "I'm sorry, I'm having trouble responding right now. Please try again later."