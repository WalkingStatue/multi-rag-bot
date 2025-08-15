"""
Analytics service for bot usage metrics and activity tracking.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.sql import text

from ..models.bot import Bot, BotPermission
from ..models.conversation import ConversationSession, Message
from ..models.activity import ActivityLog
from ..models.user import User
from ..models.document import Document


class AnalyticsService:
    """Service for analytics and reporting functionality."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_bot_usage_analytics(
        self, 
        bot_id: str, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive usage analytics for a specific bot."""
        # Check if user has access to this bot
        permission = self.db.query(BotPermission).filter(
            BotPermission.bot_id == bot_id,
            BotPermission.user_id == user_id
        ).first()
        
        if not permission:
            raise ValueError("User does not have access to this bot")
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Basic metrics
        total_conversations = self.db.query(ConversationSession).filter(
            ConversationSession.bot_id == bot_id,
            ConversationSession.created_at >= start_date
        ).count()
        
        total_messages = self.db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.created_at >= start_date
        ).count()
        
        user_messages = self.db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == "user",
            Message.created_at >= start_date
        ).count()
        
        assistant_messages = self.db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == "assistant",
            Message.created_at >= start_date
        ).count()
        
        # Unique users
        unique_users = self.db.query(func.count(func.distinct(Message.user_id))).filter(
            Message.bot_id == bot_id,
            Message.created_at >= start_date
        ).scalar()
        
        # Documents count
        documents_count = self.db.query(Document).filter(
            Document.bot_id == bot_id
        ).count()
        
        # Daily message counts for the last 30 days
        daily_messages = self.db.query(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('count')
        ).filter(
            Message.bot_id == bot_id,
            Message.created_at >= start_date
        ).group_by(func.date(Message.created_at)).order_by('date').all()
        
        # Top users by message count
        top_users = self.db.query(
            User.username,
            User.full_name,
            func.count(Message.id).label('message_count')
        ).join(Message, User.id == Message.user_id).filter(
            Message.bot_id == bot_id,
            Message.created_at >= start_date
        ).group_by(User.id, User.username, User.full_name).order_by(
            desc('message_count')
        ).limit(10).all()
        
        # Average response time (if metadata contains response_time)
        avg_response_time = self.db.query(
            func.avg(
                func.cast(
                    func.json_extract_path_text(Message.message_metadata, 'response_time'),
                    text('FLOAT')
                )
            )
        ).filter(
            Message.bot_id == bot_id,
            Message.role == "assistant",
            Message.created_at >= start_date,
            Message.message_metadata.op('?')('response_time')
        ).scalar()
        
        # Token usage (if metadata contains tokens_used)
        total_tokens = self.db.query(
            func.sum(
                func.cast(
                    func.json_extract_path_text(Message.message_metadata, 'tokens_used'),
                    text('INTEGER')
                )
            )
        ).filter(
            Message.bot_id == bot_id,
            Message.role == "assistant",
            Message.created_at >= start_date,
            Message.message_metadata.op('?')('tokens_used')
        ).scalar()
        
        return {
            "bot_id": bot_id,
            "period_days": days,
            "metrics": {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "unique_users": unique_users or 0,
                "documents_count": documents_count,
                "avg_response_time": float(avg_response_time) if avg_response_time else None,
                "total_tokens": int(total_tokens) if total_tokens else None
            },
            "daily_activity": [
                {
                    "date": str(day.date),
                    "message_count": day.count
                }
                for day in daily_messages
            ],
            "top_users": [
                {
                    "username": user.username,
                    "full_name": user.full_name,
                    "message_count": user.message_count
                }
                for user in top_users
            ]
        }
    
    def get_user_dashboard_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get dashboard analytics for a user across all their accessible bots."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all bots user has access to
        accessible_bots = self.db.query(Bot).join(BotPermission).filter(
            BotPermission.user_id == user_id
        ).all()
        
        bot_ids = [str(bot.id) for bot in accessible_bots]
        
        if not bot_ids:
            return {
                "user_id": user_id,
                "period_days": days,
                "metrics": {
                    "total_bots": 0,
                    "owned_bots": 0,
                    "total_conversations": 0,
                    "total_messages": 0,
                    "messages_sent": 0,
                    "messages_received": 0
                },
                "bot_activity": [],
                "recent_conversations": []
            }
        
        # Basic metrics
        total_bots = len(accessible_bots)
        owned_bots = len([bot for bot in accessible_bots if str(bot.owner_id) == user_id])
        
        total_conversations = self.db.query(ConversationSession).filter(
            ConversationSession.bot_id.in_(bot_ids),
            ConversationSession.user_id == user_id,
            ConversationSession.created_at >= start_date
        ).count()
        
        messages_sent = self.db.query(Message).filter(
            Message.bot_id.in_(bot_ids),
            Message.user_id == user_id,
            Message.role == "user",
            Message.created_at >= start_date
        ).count()
        
        messages_received = self.db.query(Message).filter(
            Message.bot_id.in_(bot_ids),
            Message.user_id == user_id,
            Message.role == "assistant",
            Message.created_at >= start_date
        ).count()
        
        total_messages = messages_sent + messages_received
        
        # Bot activity breakdown
        bot_activity = self.db.query(
            Bot.name,
            Bot.id,
            func.count(Message.id).label('message_count'),
            func.count(func.distinct(ConversationSession.id)).label('conversation_count')
        ).join(Message, Bot.id == Message.bot_id).join(
            ConversationSession, Message.session_id == ConversationSession.id
        ).filter(
            Bot.id.in_(bot_ids),
            Message.user_id == user_id,
            Message.created_at >= start_date
        ).group_by(Bot.id, Bot.name).order_by(desc('message_count')).all()
        
        # Recent conversations
        recent_conversations = self.db.query(
            ConversationSession.id,
            ConversationSession.title,
            ConversationSession.created_at,
            ConversationSession.updated_at,
            Bot.name.label('bot_name'),
            func.count(Message.id).label('message_count')
        ).join(Bot, ConversationSession.bot_id == Bot.id).outerjoin(
            Message, ConversationSession.id == Message.session_id
        ).filter(
            ConversationSession.bot_id.in_(bot_ids),
            ConversationSession.user_id == user_id
        ).group_by(
            ConversationSession.id,
            ConversationSession.title,
            ConversationSession.created_at,
            ConversationSession.updated_at,
            Bot.name
        ).order_by(desc(ConversationSession.updated_at)).limit(10).all()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "metrics": {
                "total_bots": total_bots,
                "owned_bots": owned_bots,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "messages_sent": messages_sent,
                "messages_received": messages_received
            },
            "bot_activity": [
                {
                    "bot_id": str(activity.id),
                    "bot_name": activity.name,
                    "message_count": activity.message_count,
                    "conversation_count": activity.conversation_count
                }
                for activity in bot_activity
            ],
            "recent_conversations": [
                {
                    "session_id": str(conv.id),
                    "title": conv.title,
                    "bot_name": conv.bot_name,
                    "message_count": conv.message_count,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                }
                for conv in recent_conversations
            ]
        }
    
    def get_bot_activity_logs(
        self, 
        bot_id: str, 
        user_id: str, 
        limit: int = 50,
        action_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get activity logs for a specific bot."""
        # Check if user has access to this bot
        permission = self.db.query(BotPermission).filter(
            BotPermission.bot_id == bot_id,
            BotPermission.user_id == user_id
        ).first()
        
        if not permission:
            raise ValueError("User does not have access to this bot")
        
        query = self.db.query(
            ActivityLog,
            User.username,
            User.full_name
        ).outerjoin(User, ActivityLog.user_id == User.id).filter(
            ActivityLog.bot_id == bot_id
        )
        
        if action_filter:
            query = query.filter(ActivityLog.action == action_filter)
        
        activities = query.order_by(desc(ActivityLog.created_at)).limit(limit).all()
        
        return [
            {
                "id": str(activity.ActivityLog.id),
                "action": activity.ActivityLog.action,
                "details": activity.ActivityLog.details,
                "created_at": activity.ActivityLog.created_at.isoformat(),
                "user": {
                    "username": activity.username,
                    "full_name": activity.full_name
                } if activity.username else None
            }
            for activity in activities
        ]
    
    def get_system_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get system-wide analytics (admin only)."""
        # Check if user is admin (for now, check if they own any bots - in real system, add admin role)
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # For now, allow any user to see system stats (in production, add proper admin check)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # System-wide metrics
        total_users = self.db.query(User).count()
        total_bots = self.db.query(Bot).count()
        total_conversations = self.db.query(ConversationSession).filter(
            ConversationSession.created_at >= start_date
        ).count()
        total_messages = self.db.query(Message).filter(
            Message.created_at >= start_date
        ).count()
        total_documents = self.db.query(Document).count()
        
        # Active users (users who sent messages in the period)
        active_users = self.db.query(func.count(func.distinct(Message.user_id))).filter(
            Message.created_at >= start_date,
            Message.role == "user"
        ).scalar()
        
        # Most active bots
        most_active_bots = self.db.query(
            Bot.name,
            Bot.id,
            func.count(Message.id).label('message_count')
        ).join(Message, Bot.id == Message.bot_id).filter(
            Message.created_at >= start_date
        ).group_by(Bot.id, Bot.name).order_by(desc('message_count')).limit(10).all()
        
        # Daily activity
        daily_activity = self.db.query(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('message_count'),
            func.count(func.distinct(Message.user_id)).label('active_users')
        ).filter(
            Message.created_at >= start_date
        ).group_by(func.date(Message.created_at)).order_by('date').all()
        
        return {
            "period_days": days,
            "metrics": {
                "total_users": total_users,
                "total_bots": total_bots,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_documents": total_documents,
                "active_users": active_users or 0
            },
            "most_active_bots": [
                {
                    "bot_id": str(bot.id),
                    "bot_name": bot.name,
                    "message_count": bot.message_count
                }
                for bot in most_active_bots
            ],
            "daily_activity": [
                {
                    "date": str(day.date),
                    "message_count": day.message_count,
                    "active_users": day.active_users
                }
                for day in daily_activity
            ]
        }
    
    def export_bot_data(
        self, 
        bot_id: str, 
        user_id: str, 
        format_type: str = "json",
        include_messages: bool = True,
        include_documents: bool = True,
        include_activity: bool = True
    ) -> Dict[str, Any]:
        """Export bot data for analytics and reporting."""
        # Check if user has access to this bot
        permission = self.db.query(BotPermission).filter(
            BotPermission.bot_id == bot_id,
            BotPermission.user_id == user_id
        ).first()
        
        if not permission:
            raise ValueError("User does not have access to this bot")
        
        # Get bot details
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise ValueError("Bot not found")
        
        export_data = {
            "bot": {
                "id": str(bot.id),
                "name": bot.name,
                "description": bot.description,
                "system_prompt": bot.system_prompt,
                "llm_provider": bot.llm_provider,
                "llm_model": bot.llm_model,
                "created_at": bot.created_at.isoformat(),
                "updated_at": bot.updated_at.isoformat()
            },
            "export_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "exported_by": user_id,
                "format": format_type
            }
        }
        
        if include_messages:
            conversations = self.db.query(ConversationSession).filter(
                ConversationSession.bot_id == bot_id
            ).all()
            
            export_data["conversations"] = []
            for conv in conversations:
                messages = self.db.query(Message).filter(
                    Message.session_id == conv.id
                ).order_by(Message.created_at).all()
                
                export_data["conversations"].append({
                    "session_id": str(conv.id),
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "messages": [
                        {
                            "id": str(msg.id),
                            "role": msg.role,
                            "content": msg.content,
                            "metadata": msg.message_metadata,
                            "created_at": msg.created_at.isoformat()
                        }
                        for msg in messages
                    ]
                })
        
        if include_documents:
            documents = self.db.query(Document).filter(
                Document.bot_id == bot_id
            ).all()
            
            export_data["documents"] = [
                {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                    "mime_type": doc.mime_type,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in documents
            ]
        
        if include_activity:
            activities = self.db.query(ActivityLog).filter(
                ActivityLog.bot_id == bot_id
            ).order_by(desc(ActivityLog.created_at)).all()
            
            export_data["activity_logs"] = [
                {
                    "id": str(activity.id),
                    "action": activity.action,
                    "details": activity.details,
                    "created_at": activity.created_at.isoformat()
                }
                for activity in activities
            ]
        
        return export_data