"""
Widget service for managing embeddable chat widgets.
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from fastapi import HTTPException, status
import uuid

from ..models.widget import WidgetConfig, WidgetSession, WidgetMessage
from ..models.bot import Bot
from ..models.user import User
from ..schemas.widget import (
    WidgetConfigCreate, WidgetConfigUpdate, WidgetInitRequest,
    WidgetStatsResponse
)
from ..core.security import create_access_token


class WidgetService:
    """Service for managing widget configurations and sessions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_widget_key(self) -> str:
        """Generate a unique widget key."""
        while True:
            # Generate a 32-character alphanumeric key
            key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            # Check if key already exists
            existing = self.db.query(WidgetConfig).filter(WidgetConfig.widget_key == key).first()
            if not existing:
                return key
    
    def create_widget_config(self, user_id: uuid.UUID, config_data: WidgetConfigCreate) -> WidgetConfig:
        """Create a new widget configuration."""
        # Verify bot ownership
        bot = self.db.query(Bot).filter(
            and_(Bot.id == config_data.bot_id, Bot.owner_id == user_id)
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found or access denied"
            )
        
        # Create widget config
        widget_config = WidgetConfig(
            bot_id=config_data.bot_id,
            owner_id=user_id,
            widget_key=self.generate_widget_key(),
            **config_data.model_dump(exclude={'bot_id'})
        )
        
        self.db.add(widget_config)
        self.db.commit()
        self.db.refresh(widget_config)
        
        return widget_config
    
    def get_widget_configs(self, user_id: uuid.UUID) -> List[WidgetConfig]:
        """Get all widget configurations for a user."""
        return self.db.query(WidgetConfig).filter(
            WidgetConfig.owner_id == user_id
        ).order_by(desc(WidgetConfig.created_at)).all()
    
    def get_widget_config(self, user_id: uuid.UUID, config_id: uuid.UUID) -> Optional[WidgetConfig]:
        """Get a specific widget configuration."""
        return self.db.query(WidgetConfig).filter(
            and_(
                WidgetConfig.id == config_id,
                WidgetConfig.owner_id == user_id
            )
        ).first()
    
    def get_widget_config_by_key(self, widget_key: str) -> Optional[WidgetConfig]:
        """Get widget configuration by widget key."""
        return self.db.query(WidgetConfig).filter(
            and_(
                WidgetConfig.widget_key == widget_key,
                WidgetConfig.is_active == True
            )
        ).first()
    
    def update_widget_config(
        self, 
        user_id: uuid.UUID, 
        config_id: uuid.UUID, 
        update_data: WidgetConfigUpdate
    ) -> Optional[WidgetConfig]:
        """Update a widget configuration."""
        widget_config = self.get_widget_config(user_id, config_id)
        if not widget_config:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(widget_config, field, value)
        
        widget_config.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(widget_config)
        
        return widget_config
    
    def delete_widget_config(self, user_id: uuid.UUID, config_id: uuid.UUID) -> bool:
        """Delete a widget configuration."""
        widget_config = self.get_widget_config(user_id, config_id)
        if not widget_config:
            return False
        
        self.db.delete(widget_config)
        self.db.commit()
        return True
    
    def validate_domain(self, widget_config: WidgetConfig, domain: str) -> bool:
        """Validate if domain is allowed for the widget."""
        if not widget_config.require_domain_validation:
            return True
        
        if not widget_config.allowed_domains:
            return False
        
        # Check exact match or wildcard match
        for allowed_domain in widget_config.allowed_domains:
            if allowed_domain == domain:
                return True
            
            # Check wildcard domains (e.g., *.example.com)
            if allowed_domain.startswith('*.'):
                base_domain = allowed_domain[2:]
                if domain.endswith('.' + base_domain) or domain == base_domain:
                    return True
        
        return False
    
    def generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    def initialize_widget_session(
        self, 
        init_request: WidgetInitRequest,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a new widget session."""
        # Get widget configuration
        widget_config = self.get_widget_config_by_key(init_request.widget_key)
        if not widget_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found or inactive"
            )
        
        # Validate domain
        if not self.validate_domain(widget_config, init_request.domain):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Domain not allowed for this widget"
            )
        
        # Generate visitor ID if not provided
        visitor_id = init_request.visitor_id or f"visitor_{secrets.token_hex(8)}"
        
        # Create session
        session_token = self.generate_session_token()
        expires_at = datetime.utcnow() + timedelta(minutes=widget_config.session_timeout_minutes)
        
        widget_session = WidgetSession(
            widget_config_id=widget_config.id,
            session_token=session_token,
            visitor_id=visitor_id,
            domain=init_request.domain,
            user_agent=user_agent or init_request.user_agent,
            ip_address=ip_address,
            referrer=init_request.referrer,
            expires_at=expires_at
        )
        
        self.db.add(widget_session)
        self.db.commit()
        self.db.refresh(widget_session)
        
        # Create JWT token for WebSocket authentication
        jwt_token = create_access_token(
            data={
                "sub": str(widget_session.id),
                "type": "widget_session",
                "widget_key": init_request.widget_key,
                "visitor_id": visitor_id
            },
            expires_delta=timedelta(minutes=widget_config.session_timeout_minutes)
        )
        
        return {
            "session_token": session_token,
            "jwt_token": jwt_token,
            "widget_config": {
                "title": widget_config.widget_title,
                "welcome_message": widget_config.welcome_message,
                "placeholder_text": widget_config.placeholder_text,
                "theme_config": widget_config.theme_config,
                "max_messages": widget_config.max_messages_per_session
            },
            "websocket_url": f"/api/ws/widget/{session_token}",
            "expires_at": expires_at
        }
    
    def get_session_by_token(self, session_token: str) -> Optional[WidgetSession]:
        """Get widget session by token."""
        return self.db.query(WidgetSession).filter(
            and_(
                WidgetSession.session_token == session_token,
                WidgetSession.is_active == True,
                WidgetSession.expires_at > datetime.utcnow()
            )
        ).first()
    
    def update_session_activity(self, session: WidgetSession):
        """Update session last activity timestamp."""
        session.last_activity = datetime.utcnow()
        self.db.commit()
    
    def add_message_to_session(
        self, 
        session: WidgetSession, 
        content: str, 
        role: str
    ) -> WidgetMessage:
        """Add a message to widget session."""
        # Check message limit
        if session.message_count >= session.widget_config.max_messages_per_session:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Message limit reached for this session"
            )
        
        message = WidgetMessage(
            session_id=session.id,
            content=content,
            role=role
        )
        
        self.db.add(message)
        session.message_count += 1
        self.update_session_activity(session)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_session_messages(self, session: WidgetSession) -> List[WidgetMessage]:
        """Get all messages for a session."""
        return self.db.query(WidgetMessage).filter(
            WidgetMessage.session_id == session.id
        ).order_by(WidgetMessage.created_at).all()
    
    def get_widget_stats(self, user_id: uuid.UUID, config_id: uuid.UUID) -> WidgetStatsResponse:
        """Get statistics for a widget configuration."""
        widget_config = self.get_widget_config(user_id, config_id)
        if not widget_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget configuration not found"
            )
        
        # Total sessions
        total_sessions = self.db.query(func.count(WidgetSession.id)).filter(
            WidgetSession.widget_config_id == config_id
        ).scalar()
        
        # Active sessions
        active_sessions = self.db.query(func.count(WidgetSession.id)).filter(
            and_(
                WidgetSession.widget_config_id == config_id,
                WidgetSession.is_active == True,
                WidgetSession.expires_at > datetime.utcnow()
            )
        ).scalar()
        
        # Total messages
        total_messages = self.db.query(func.count(WidgetMessage.id)).join(
            WidgetSession
        ).filter(
            WidgetSession.widget_config_id == config_id
        ).scalar()
        
        # Messages today
        today = datetime.utcnow().date()
        messages_today = self.db.query(func.count(WidgetMessage.id)).join(
            WidgetSession
        ).filter(
            and_(
                WidgetSession.widget_config_id == config_id,
                func.date(WidgetMessage.created_at) == today
            )
        ).scalar()
        
        # Top domains
        top_domains = self.db.query(
            WidgetSession.domain,
            func.count(WidgetSession.id).label('session_count')
        ).filter(
            WidgetSession.widget_config_id == config_id
        ).group_by(
            WidgetSession.domain
        ).order_by(
            desc('session_count')
        ).limit(10).all()
        
        return WidgetStatsResponse(
            total_sessions=total_sessions or 0,
            active_sessions=active_sessions or 0,
            total_messages=total_messages or 0,
            messages_today=messages_today or 0,
            average_session_duration=None,  # Could be calculated if needed
            top_domains=[
                {"domain": domain, "sessions": count} 
                for domain, count in top_domains
            ]
        )
    
    async def process_widget_chat(
        self,
        bot_id: uuid.UUID,
        message: str,
        conversation_id: Optional[str] = None,
        visitor_id: Optional[str] = None,
        domain: Optional[str] = None,
        widget_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a chat message from a widget."""
        
        # Find the bot
        print(f"Looking for bot with ID: {bot_id}")
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            print(f"Bot not found with ID: {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        print(f"Found bot: {bot.name} (ID: {bot.id}, Owner: {bot.owner_id})")
        
        try:
            # Try to use the full chat service
            from ..services.chat_service import ChatService
            from ..schemas.conversation import ChatRequest
            
            # Create chat service and process message
            chat_service = ChatService(self.db)
            
            # Handle session continuity
            session_uuid = None
            if conversation_id:
                try:
                    # Try to parse the conversation_id as UUID
                    session_uuid = uuid.UUID(conversation_id)
                    print(f"Using existing session: {session_uuid}")
                except (ValueError, TypeError):
                    print(f"Invalid conversation_id format: {conversation_id}, creating new session")
                    session_uuid = None
            else:
                print("No conversation_id provided, creating new session")
            
            # Create chat request with session continuity
            chat_request = ChatRequest(
                message=message,
                session_id=session_uuid  # Use existing session or create new one
            )
            
            print(f"Processing widget chat with ChatService:")
            print(f"  Bot ID: {bot_id}")
            print(f"  Bot owner ID: {bot.owner_id}")
            print(f"  Message: {message}")
            
            # Process message using the bot owner's permissions
            response = await chat_service.process_message(
                bot_id=bot_id,
                user_id=bot.owner_id,  # Use bot owner's ID for permissions
                chat_request=chat_request
            )
            
            print(f"Chat response received: {response}")
            
            return {
                "message": response.message,
                "conversation_id": str(response.session_id),
                "message_id": str(uuid.uuid4()),  # Generate a message ID
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            # Log the full error for debugging
            import traceback
            print(f"ChatService failed: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            
            # Fallback to simple response
            print("Falling back to simple response")
            
            # Generate a simple conversation ID
            fallback_conversation_id = str(uuid.uuid4())
            
            # Create a simple response based on the bot's system prompt or a default
            fallback_message = f"Hello! I'm {bot.name}. I received your message: '{message}'. This is a fallback response while the full chat system is being set up."
            
            return {
                "message": fallback_message,
                "conversation_id": fallback_conversation_id,
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat()
            }

    def cleanup_expired_sessions(self):
        """Clean up expired widget sessions."""
        expired_sessions = self.db.query(WidgetSession).filter(
            WidgetSession.expires_at < datetime.utcnow()
        ).all()
        
        for session in expired_sessions:
            session.is_active = False
        
        self.db.commit()
        return len(expired_sessions)