"""
User management service for profile operations and collaboration features.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, func, desc
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from ..models.user import User, UserAPIKey, UserSettings
from ..models.bot import Bot
from ..models.conversation import ConversationSession, Message
from ..models.document import Document
from ..models.activity import ActivityLog
from ..schemas.user import (
    UserUpdate, UserSearch, APIKeyCreate, APIKeyUpdate, APIKeyResponse,
    UserSettingsUpdate, UserSettingsResponse, UserActivitySummary,
    BotUsageStats, ConversationAnalytics, UserAnalytics
)
from ..utils.encryption import encrypt_api_key, decrypt_api_key


class UserService:
    """Service class for user management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_profile(self, user_id: str) -> User:
        """
        Get user profile by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object
            
        Raises:
            HTTPException: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    
    def update_user_profile(self, user: User, updates: UserUpdate) -> User:
        """
        Update user profile.
        
        Args:
            user: Current user object
            updates: Profile updates
            
        Returns:
            Updated user object
            
        Raises:
            HTTPException: If username/email already exists
        """
        # Check for username/email conflicts
        if updates.username and updates.username != user.username:
            existing_user = self.db.query(User).filter(
                and_(User.username == updates.username, User.id != user.id)
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        if updates.email and updates.email != user.email:
            existing_user = self.db.query(User).filter(
                and_(User.email == updates.email, User.id != user.id)
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update profile"
            )
    
    def search_users(self, query: str, limit: int = 20) -> List[UserSearch]:
        """
        Search users by username or full name for collaboration.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of user search results
        """
        if not query or len(query.strip()) < 2:
            return []
        
        search_term = f"%{query.strip()}%"
        users = self.db.query(User).filter(
            and_(
                User.is_active == True,
                or_(
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        ).limit(limit).all()
        
        return [
            UserSearch(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                avatar_url=user.avatar_url
            )
            for user in users
        ]
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()
    
    # API Key Management Methods
    
    def add_api_key(self, user: User, api_key_data: APIKeyCreate) -> APIKeyResponse:
        """
        Add or update API key for a provider.
        
        Args:
            user: User object
            api_key_data: API key data
            
        Returns:
            API key response object
            
        Raises:
            HTTPException: If encryption fails
        """
        try:
            # Encrypt the API key
            encrypted_key = encrypt_api_key(api_key_data.api_key)
            
            # Check if API key already exists for this provider
            existing_key = self.db.query(UserAPIKey).filter(
                and_(
                    UserAPIKey.user_id == user.id,
                    UserAPIKey.provider == api_key_data.provider
                )
            ).first()
            
            if existing_key:
                # Update existing key
                existing_key.api_key_encrypted = encrypted_key
                existing_key.is_active = True
                self.db.commit()
                self.db.refresh(existing_key)
                return APIKeyResponse.model_validate(existing_key)
            else:
                # Create new key
                db_api_key = UserAPIKey(
                    user_id=user.id,
                    provider=api_key_data.provider,
                    api_key_encrypted=encrypted_key,
                    is_active=True
                )
                self.db.add(db_api_key)
                self.db.commit()
                self.db.refresh(db_api_key)
                return APIKeyResponse.model_validate(db_api_key)
                
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save API key"
            )
    
    def get_user_api_keys(self, user: User) -> List[APIKeyResponse]:
        """
        Get all API keys for a user.
        
        Args:
            user: User object
            
        Returns:
            List of API key response objects
        """
        api_keys = self.db.query(UserAPIKey).filter(
            UserAPIKey.user_id == user.id
        ).all()
        
        return [APIKeyResponse.model_validate(key) for key in api_keys]
    
    def get_user_api_key(self, user_id: uuid.UUID, provider: str) -> Optional[str]:
        """
        Get decrypted API key for a provider by user ID.
        
        Args:
            user_id: User ID
            provider: Provider name
            
        Returns:
            Decrypted API key or None if not found
        """
        api_key = self.db.query(UserAPIKey).filter(
            and_(
                UserAPIKey.user_id == user_id,
                UserAPIKey.provider == provider,
                UserAPIKey.is_active == True
            )
        ).first()
        
        if not api_key:
            return None
        
        try:
            return decrypt_api_key(api_key.api_key_encrypted)
        except Exception:
            return None
    
    def get_api_key(self, user: User, provider: str) -> Optional[str]:
        """
        Get decrypted API key for a provider.
        
        Args:
            user: User object
            provider: Provider name
            
        Returns:
            Decrypted API key or None if not found
        """
        api_key = self.db.query(UserAPIKey).filter(
            and_(
                UserAPIKey.user_id == user.id,
                UserAPIKey.provider == provider,
                UserAPIKey.is_active == True
            )
        ).first()
        
        if not api_key:
            return None
        
        try:
            return decrypt_api_key(api_key.api_key_encrypted)
        except Exception:
            return None
    
    def update_api_key(self, user: User, provider: str, api_key_data: APIKeyUpdate) -> APIKeyResponse:
        """
        Update API key for a provider.
        
        Args:
            user: User object
            provider: Provider name
            api_key_data: Updated API key data
            
        Returns:
            Updated API key response object
            
        Raises:
            HTTPException: If API key not found or update fails
        """
        api_key = self.db.query(UserAPIKey).filter(
            and_(
                UserAPIKey.user_id == user.id,
                UserAPIKey.provider == provider
            )
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found for this provider"
            )
        
        try:
            # Encrypt new API key
            encrypted_key = encrypt_api_key(api_key_data.api_key)
            
            # Update fields
            api_key.api_key_encrypted = encrypted_key
            if api_key_data.is_active is not None:
                api_key.is_active = api_key_data.is_active
            # updated_at will be automatically set by the database due to onupdate=func.now()
            
            self.db.commit()
            self.db.refresh(api_key)
            return APIKeyResponse.model_validate(api_key)
            
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update API key"
            )
    
    def delete_api_key(self, user: User, provider: str) -> bool:
        """
        Delete API key for a provider.
        
        Args:
            user: User object
            provider: Provider name
            
        Returns:
            True if deleted successfully
            
        Raises:
            HTTPException: If API key not found
        """
        api_key = self.db.query(UserAPIKey).filter(
            and_(
                UserAPIKey.user_id == user.id,
                UserAPIKey.provider == provider
            )
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found for this provider"
            )
        
        try:
            self.db.delete(api_key)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete API key"
            )
    
    # User Settings Methods
    
    def get_user_settings(self, user: User) -> UserSettingsResponse:
        """
        Get user settings and preferences.
        
        Args:
            user: User object
            
        Returns:
            User settings response object
        """
        settings = self.db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        if not settings:
            # Create default settings if none exist
            try:
                settings = UserSettings(
                    user_id=user.id,
                    theme="light",
                    language="en",
                    timezone="UTC",
                    notifications_enabled=True,
                    email_notifications=True,
                    max_conversation_history=50,
                    auto_save_conversations=True
                )
                self.db.add(settings)
                self.db.commit()
                self.db.refresh(settings)
            except IntegrityError:
                self.db.rollback()
                # Try to get settings again in case another process created them
                settings = self.db.query(UserSettings).filter(
                    UserSettings.user_id == user.id
                ).first()
                if not settings:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user settings"
                    )
        
        return UserSettingsResponse.model_validate(settings)
    
    def update_user_settings(self, user: User, updates: UserSettingsUpdate) -> UserSettingsResponse:
        """
        Update user settings and preferences.
        
        Args:
            user: User object
            updates: Settings updates
            
        Returns:
            Updated user settings response object
            
        Raises:
            HTTPException: If update fails
        """
        settings = self.db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        if not settings:
            # Create new settings if none exist
            try:
                settings = UserSettings(user_id=user.id)
                self.db.add(settings)
            except IntegrityError:
                self.db.rollback()
                # Try to get settings again in case another process created them
                settings = self.db.query(UserSettings).filter(
                    UserSettings.user_id == user.id
                ).first()
                if not settings:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create user settings"
                    )
        
        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(settings)
            return UserSettingsResponse.model_validate(settings)
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user settings"
            )
    
    # User Analytics Methods
    
    def get_user_activity_summary(self, user: User) -> UserActivitySummary:
        """
        Get user activity summary.
        
        Args:
            user: User object
            
        Returns:
            User activity summary
        """
        # Get basic counts
        total_bots = self.db.query(Bot).filter(Bot.owner_id == user.id).count()
        
        total_conversations = self.db.query(ConversationSession).filter(
            ConversationSession.user_id == user.id
        ).count()
        
        total_messages = self.db.query(Message).filter(
            Message.user_id == user.id
        ).count()
        
        total_documents = self.db.query(Document).filter(
            Document.uploaded_by == user.id
        ).count()
        
        # Get most used bot
        most_used_bot_query = self.db.query(
            Bot.name,
            func.count(Message.id).label('message_count')
        ).join(
            Message, Bot.id == Message.bot_id
        ).filter(
            Message.user_id == user.id
        ).group_by(Bot.id, Bot.name).order_by(desc('message_count')).first()
        
        most_used_bot = most_used_bot_query.name if most_used_bot_query else None
        
        # Get most used provider (from bot configurations)
        most_used_provider_query = self.db.query(
            Bot.llm_provider,
            func.count(Message.id).label('usage_count')
        ).join(
            Message, Bot.id == Message.bot_id
        ).filter(
            Message.user_id == user.id
        ).group_by(Bot.llm_provider).order_by(desc('usage_count')).first()
        
        most_used_provider = most_used_provider_query.llm_provider if most_used_provider_query else None
        
        # Get activity in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        activity_last_30_days = self.db.query(Message).filter(
            and_(
                Message.user_id == user.id,
                Message.created_at >= thirty_days_ago
            )
        ).count()
        
        return UserActivitySummary(
            total_bots=total_bots,
            total_conversations=total_conversations,
            total_messages=total_messages,
            total_documents_uploaded=total_documents,
            most_used_bot=most_used_bot,
            most_used_provider=most_used_provider,
            activity_last_30_days=activity_last_30_days,
            created_at=user.created_at
        )
    
    def get_bot_usage_stats(self, user: User) -> List[BotUsageStats]:
        """
        Get bot usage statistics for user.
        
        Args:
            user: User object
            
        Returns:
            List of bot usage statistics
        """
        # Get bots with usage stats
        bot_stats = self.db.query(
            Bot.id,
            Bot.name,
            func.count(Message.id).label('message_count'),
            func.count(func.distinct(ConversationSession.id)).label('conversation_count'),
            func.count(func.distinct(Document.id)).label('document_count'),
            func.max(Message.created_at).label('last_used')
        ).outerjoin(
            Message, Bot.id == Message.bot_id
        ).outerjoin(
            ConversationSession, Bot.id == ConversationSession.bot_id
        ).outerjoin(
            Document, Bot.id == Document.bot_id
        ).filter(
            Bot.owner_id == user.id
        ).group_by(Bot.id, Bot.name).all()
        
        return [
            BotUsageStats(
                bot_id=stat.id,
                bot_name=stat.name,
                message_count=stat.message_count or 0,
                conversation_count=stat.conversation_count or 0,
                document_count=stat.document_count or 0,
                last_used=stat.last_used,
                avg_response_time=None  # Could be calculated from message metadata
            )
            for stat in bot_stats
        ]
    
    def get_conversation_analytics(self, user: User) -> ConversationAnalytics:
        """
        Get conversation analytics for user.
        
        Args:
            user: User object
            
        Returns:
            Conversation analytics
        """
        # Basic conversation stats
        total_conversations = self.db.query(ConversationSession).filter(
            ConversationSession.user_id == user.id
        ).count()
        
        total_messages = self.db.query(Message).filter(
            Message.user_id == user.id
        ).count()
        
        avg_messages_per_conversation = (
            total_messages / total_conversations if total_conversations > 0 else 0
        )
        
        # Most active bot
        most_active_bot_query = self.db.query(
            Bot.name,
            func.count(ConversationSession.id).label('conversation_count')
        ).join(
            ConversationSession, Bot.id == ConversationSession.bot_id
        ).filter(
            ConversationSession.user_id == user.id
        ).group_by(Bot.id, Bot.name).order_by(desc('conversation_count')).first()
        
        most_active_bot = most_active_bot_query.name if most_active_bot_query else None
        
        # Conversations by day (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        conversations_by_day = self.db.query(
            func.date(ConversationSession.created_at).label('date'),
            func.count(ConversationSession.id).label('count')
        ).filter(
            and_(
                ConversationSession.user_id == user.id,
                ConversationSession.created_at >= thirty_days_ago
            )
        ).group_by(func.date(ConversationSession.created_at)).all()
        
        # Messages by day (last 30 days)
        messages_by_day = self.db.query(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('count')
        ).filter(
            and_(
                Message.user_id == user.id,
                Message.created_at >= thirty_days_ago
            )
        ).group_by(func.date(Message.created_at)).all()
        
        return ConversationAnalytics(
            total_conversations=total_conversations,
            total_messages=total_messages,
            avg_messages_per_conversation=avg_messages_per_conversation,
            most_active_bot=most_active_bot,
            conversations_by_day=[
                {"date": str(row.date), "count": row.count}
                for row in conversations_by_day
            ],
            messages_by_day=[
                {"date": str(row.date), "count": row.count}
                for row in messages_by_day
            ]
        )
    
    def get_user_analytics(self, user: User) -> UserAnalytics:
        """
        Get comprehensive user analytics.
        
        Args:
            user: User object
            
        Returns:
            Comprehensive user analytics
        """
        activity_summary = self.get_user_activity_summary(user)
        bot_usage = self.get_bot_usage_stats(user)
        conversation_analytics = self.get_conversation_analytics(user)
        
        # Provider usage stats
        provider_usage = {}
        provider_stats = self.db.query(
            Bot.llm_provider,
            func.count(Message.id).label('usage_count')
        ).join(
            Message, Bot.id == Message.bot_id
        ).filter(
            Message.user_id == user.id
        ).group_by(Bot.llm_provider).all()
        
        for stat in provider_stats:
            provider_usage[stat.llm_provider] = stat.usage_count
        
        # Recent activity (last 10 activities)
        recent_activity = self.db.query(ActivityLog).filter(
            ActivityLog.user_id == user.id
        ).order_by(desc(ActivityLog.created_at)).limit(10).all()
        
        recent_activity_list = [
            {
                "action": activity.action,
                "details": activity.details,
                "created_at": activity.created_at.isoformat(),
                "bot_id": str(activity.bot_id) if activity.bot_id else None
            }
            for activity in recent_activity
        ]
        
        return UserAnalytics(
            activity_summary=activity_summary,
            bot_usage=bot_usage,
            conversation_analytics=conversation_analytics,
            provider_usage=provider_usage,
            recent_activity=recent_activity_list
        )