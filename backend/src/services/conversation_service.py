"""
Conversation and session management service.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
import uuid

from ..models.conversation import ConversationSession, Message
from ..models.bot import Bot
from ..schemas.conversation import (
    ConversationSessionCreate,
    ConversationSessionResponse,
    MessageCreate,
    MessageResponse
)

from .permission_service import PermissionService


class ConversationService:
    """Service for managing conversations and sessions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.permission_service = PermissionService(db)
    
    def create_session(
        self,
        user_id: uuid.UUID,
        session_data: ConversationSessionCreate
    ) -> ConversationSession:
        """Create a new conversation session."""
        # Check if user has permission to access the bot
        if not self.permission_service.check_bot_permission(
            user_id, session_data.bot_id, "view_conversations"
        ):
            raise ValueError("User does not have permission to access this bot")
        
        # Create the session
        session = ConversationSession(
            bot_id=session_data.bot_id,
            user_id=user_id,
            title=session_data.title,
            is_shared=session_data.is_shared or False
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ConversationSession]:
        """Get a conversation session by ID."""
        session = self.db.query(ConversationSession).filter(
            ConversationSession.id == session_id
        ).first()
        
        if not session:
            return None
        
        # Check if user has permission to access the bot
        if not self.permission_service.check_bot_permission(
            user_id, session.bot_id, "view_conversations"
        ):
            return None
        
        return session
    
    def list_user_sessions(
        self,
        user_id: uuid.UUID,
        bot_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationSession]:
        """List conversation sessions for a user."""
        # Get all bots the user has access to
        accessible_bot_ids = self.permission_service.get_user_accessible_bot_ids(user_id)
        
        if not accessible_bot_ids:
            return []
        
        query = self.db.query(ConversationSession).filter(
            ConversationSession.bot_id.in_(accessible_bot_ids)
        )
        
        if bot_id:
            # Check if user has access to this specific bot
            if bot_id not in accessible_bot_ids:
                return []
            query = query.filter(ConversationSession.bot_id == bot_id)
        
        sessions = query.order_by(desc(ConversationSession.updated_at))\
                        .offset(offset)\
                        .limit(limit)\
                        .all()
        
        return sessions
    
    def update_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        is_shared: Optional[bool] = None
    ) -> Optional[ConversationSession]:
        """Update a conversation session."""
        session = self.get_session(session_id, user_id)
        if not session:
            return None
        
        # Check if user has editor permission
        if not self.permission_service.check_bot_permission(
            user_id, session.bot_id, "edit_bot"
        ):
            raise ValueError("User does not have permission to edit this session")
        
        if title is not None:
            session.title = title
        if is_shared is not None:
            session.is_shared = is_shared
        
        session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def delete_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Delete a conversation session."""
        session = self.get_session(session_id, user_id)
        if not session:
            return False
        
        # Check if user has admin permission or is the session owner
        if not (session.user_id == user_id or 
                self.permission_service.check_bot_role(
                    user_id, session.bot_id, "admin"
                )):
            raise ValueError("User does not have permission to delete this session")
        
        self.db.delete(session)
        self.db.commit()
        return True
    
    def add_message(
        self,
        user_id: uuid.UUID,
        message_data: MessageCreate
    ) -> Message:
        """Add a message to a conversation session."""
        # Get the session and verify access
        session = self.get_session(message_data.session_id, user_id)
        if not session:
            raise ValueError("Session not found or access denied")
        
        # Create the message
        message = Message(
            session_id=message_data.session_id,
            bot_id=session.bot_id,
            user_id=user_id,
            role=message_data.role,
            content=message_data.content,
            message_metadata=message_data.message_metadata
        )
        
        self.db.add(message)
        
        # Update session timestamp
        session.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_session_messages(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """Get messages from a conversation session."""
        # Verify session access
        session = self.get_session(session_id, user_id)
        if not session:
            return []
        
        messages = self.db.query(Message)\
                          .filter(Message.session_id == session_id)\
                          .order_by(Message.created_at)\
                          .offset(offset)\
                          .limit(limit)\
                          .all()
        
        return messages
    
    def search_conversations(
        self,
        user_id: uuid.UUID,
        query: str,
        bot_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search conversations across user's accessible bots."""
        # Get all bots the user has access to
        accessible_bot_ids = self.permission_service.get_user_accessible_bot_ids(user_id)
        
        if not accessible_bot_ids:
            return []
        
        # Build the search query
        search_query = self.db.query(
            Message,
            ConversationSession.title,
            Bot.name.label('bot_name')
        ).join(
            ConversationSession, Message.session_id == ConversationSession.id
        ).join(
            Bot, Message.bot_id == Bot.id
        ).filter(
            Message.bot_id.in_(accessible_bot_ids),
            Message.content.ilike(f"%{query}%")
        )
        
        if bot_id and bot_id in accessible_bot_ids:
            search_query = search_query.filter(Message.bot_id == bot_id)
        
        results = search_query.order_by(desc(Message.created_at))\
                             .offset(offset)\
                             .limit(limit)\
                             .all()
        
        # Format results
        formatted_results = []
        for message, session_title, bot_name in results:
            formatted_results.append({
                "message_id": str(message.id),
                "session_id": str(message.session_id),
                "bot_id": str(message.bot_id),
                "bot_name": bot_name,
                "session_title": session_title,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
                "metadata": message.message_metadata
            })
        
        return formatted_results
    
    def export_conversations(
        self,
        user_id: uuid.UUID,
        bot_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        format_type: str = "json"
    ) -> Dict[str, Any]:
        """Export conversations for backup and analysis."""
        # Get accessible bots
        accessible_bot_ids = self.permission_service.get_user_accessible_bot_ids(user_id)
        
        if not accessible_bot_ids:
            return {"conversations": [], "metadata": {"total_sessions": 0, "total_messages": 0}}
        
        # Build query based on filters
        query = self.db.query(ConversationSession).filter(
            ConversationSession.bot_id.in_(accessible_bot_ids)
        )
        
        if bot_id and bot_id in accessible_bot_ids:
            query = query.filter(ConversationSession.bot_id == bot_id)
        
        if session_id:
            # Verify session access
            session = self.get_session(session_id, user_id)
            if not session:
                return {"conversations": [], "metadata": {"total_sessions": 0, "total_messages": 0}}
            query = query.filter(ConversationSession.id == session_id)
        
        sessions = query.order_by(desc(ConversationSession.created_at)).all()
        
        # Export data
        exported_conversations = []
        total_messages = 0
        
        for session in sessions:
            messages = self.db.query(Message)\
                             .filter(Message.session_id == session.id)\
                             .order_by(Message.created_at)\
                             .all()
            
            total_messages += len(messages)
            
            session_data = {
                "session_id": str(session.id),
                "bot_id": str(session.bot_id),
                "user_id": str(session.user_id),
                "title": session.title,
                "is_shared": session.is_shared,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "messages": [
                    {
                        "message_id": str(msg.id),
                        "role": msg.role,
                        "content": msg.content,
                        "metadata": msg.message_metadata,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
            
            exported_conversations.append(session_data)
        
        return {
            "conversations": exported_conversations,
            "metadata": {
                "total_sessions": len(sessions),
                "total_messages": total_messages,
                "export_timestamp": datetime.utcnow().isoformat(),
                "format": format_type
            }
        }
    
    def get_conversation_analytics(
        self,
        user_id: uuid.UUID,
        bot_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get conversation analytics for user's accessible bots."""
        # Get accessible bots
        accessible_bot_ids = self.permission_service.get_user_accessible_bot_ids(user_id)
        
        if not accessible_bot_ids:
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "recent_activity": [],
                "bot_usage": []
            }
        
        # Filter by specific bot if provided
        bot_filter = accessible_bot_ids
        if bot_id and bot_id in accessible_bot_ids:
            bot_filter = [bot_id]
        
        # Get session count
        total_sessions = self.db.query(ConversationSession)\
                               .filter(ConversationSession.bot_id.in_(bot_filter))\
                               .count()
        
        # Get message count
        total_messages = self.db.query(Message)\
                               .filter(Message.bot_id.in_(bot_filter))\
                               .count()
        
        # Get recent activity (last 10 sessions)
        recent_sessions = self.db.query(ConversationSession)\
                                .filter(ConversationSession.bot_id.in_(bot_filter))\
                                .order_by(desc(ConversationSession.updated_at))\
                                .limit(10)\
                                .all()
        
        recent_activity = [
            {
                "session_id": str(session.id),
                "bot_id": str(session.bot_id),
                "title": session.title,
                "updated_at": session.updated_at.isoformat()
            }
            for session in recent_sessions
        ]
        
        # Get bot usage statistics
        bot_usage_query = self.db.query(
            Bot.id,
            Bot.name,
            func.count(ConversationSession.id).label('session_count'),
            func.count(Message.id).label('message_count')
        ).outerjoin(
            ConversationSession, Bot.id == ConversationSession.bot_id
        ).outerjoin(
            Message, Bot.id == Message.bot_id
        ).filter(
            Bot.id.in_(bot_filter)
        ).group_by(Bot.id, Bot.name).all()
        
        bot_usage = [
            {
                "bot_id": str(bot_id),
                "bot_name": bot_name,
                "session_count": session_count or 0,
                "message_count": message_count or 0
            }
            for bot_id, bot_name, session_count, message_count in bot_usage_query
        ]
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "recent_activity": recent_activity,
            "bot_usage": bot_usage
        }