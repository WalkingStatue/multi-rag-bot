"""
Permission service for bot ownership and role-based access control.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
import uuid
from datetime import datetime

from ..models.bot import Bot, BotPermission
from ..models.user import User
from ..models.activity import ActivityLog
from ..schemas.bot import BotPermissionCreate, BotPermissionUpdate


class PermissionService:
    """Service for managing bot permissions and role-based access control."""
    
    # Role hierarchy (higher number = more permissions)
    ROLE_HIERARCHY = {
        "viewer": 1,
        "editor": 2,
        "admin": 3,
        "owner": 4
    }
    
    # Permissions for each role
    ROLE_PERMISSIONS = {
        "viewer": ["view_bot", "view_conversations", "view_documents"],
        "editor": ["view_bot", "view_conversations", "view_documents", "chat", "upload_documents"],
        "admin": ["view_bot", "view_conversations", "view_documents", "chat", "upload_documents", 
                 "edit_bot", "delete_documents", "manage_collaborators"],
        "owner": ["view_bot", "view_conversations", "view_documents", "chat", "upload_documents",
                 "edit_bot", "delete_documents", "manage_collaborators", "delete_bot", "transfer_ownership"]
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_bot_permission(self, user_id: uuid.UUID, bot_id: uuid.UUID, required_permission: str) -> bool:
        """
        Check if user has required permission for a bot.
        
        Args:
            user_id: User ID to check
            bot_id: Bot ID to check permission for
            required_permission: Permission to check (e.g., 'edit_bot', 'chat')
            
        Returns:
            True if user has permission, False otherwise
        """
        user_role = self.get_user_bot_role(user_id, bot_id)
        if not user_role:
            return False
            
        return required_permission in self.ROLE_PERMISSIONS.get(user_role, [])
    
    def check_bot_role(self, user_id: uuid.UUID, bot_id: uuid.UUID, required_role: str) -> bool:
        """
        Check if user has required role or higher for a bot.
        
        Args:
            user_id: User ID to check
            bot_id: Bot ID to check role for
            required_role: Minimum role required
            
        Returns:
            True if user has required role or higher, False otherwise
        """
        user_role = self.get_user_bot_role(user_id, bot_id)
        if not user_role:
            return False
            
        user_level = self.ROLE_HIERARCHY.get(user_role, 0)
        required_level = self.ROLE_HIERARCHY.get(required_role, 0)
        
        return user_level >= required_level
    
    def get_user_bot_role(self, user_id: uuid.UUID, bot_id: uuid.UUID) -> Optional[str]:
        """
        Get user's role for a specific bot.
        
        Args:
            user_id: User ID
            bot_id: Bot ID
            
        Returns:
            User's role string or None if no permission
        """
        permission = self.db.query(BotPermission).filter(
            and_(
                BotPermission.user_id == user_id,
                BotPermission.bot_id == bot_id
            )
        ).first()
        
        return permission.role if permission else None
    
    def grant_permission(
        self, 
        bot_id: uuid.UUID, 
        user_id: uuid.UUID, 
        role: str, 
        granted_by: uuid.UUID
    ) -> BotPermission:
        """
        Grant permission to a user for a bot.
        
        Args:
            bot_id: Bot ID
            user_id: User ID to grant permission to
            role: Role to grant
            granted_by: User ID who is granting the permission
            
        Returns:
            Created BotPermission object
            
        Raises:
            HTTPException: If validation fails
        """
        # Validate role
        if role not in self.ROLE_HIERARCHY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )
        
        # Check if granter has permission to grant this role
        if not self.check_bot_role(granted_by, bot_id, "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to grant access"
            )
        
        # Prevent granting owner role (only transfer ownership can do this)
        if role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot grant owner role directly. Use transfer ownership instead."
            )
        
        # Check if user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if bot exists
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check if permission already exists
        existing_permission = self.db.query(BotPermission).filter(
            and_(
                BotPermission.user_id == user_id,
                BotPermission.bot_id == bot_id
            )
        ).first()
        
        if existing_permission:
            # Update existing permission
            old_role = existing_permission.role
            existing_permission.role = role
            existing_permission.granted_by = granted_by
            existing_permission.granted_at = datetime.utcnow()
            
            # Log activity
            self._log_activity(
                bot_id=bot_id,
                user_id=granted_by,
                action="permission_updated",
                details={
                    "target_user_id": str(user_id),
                    "target_username": user.username,
                    "old_role": old_role,
                    "new_role": role
                }
            )
            
            self.db.commit()
            self.db.refresh(existing_permission)
            
            # Send WebSocket notification
            self._send_permission_notification(
                bot_id, user_id, "updated", {
                    "old_role": old_role,
                    "new_role": role,
                    "granted_by": str(granted_by)
                }
            )
            
            return existing_permission
        else:
            # Create new permission
            permission = BotPermission(
                bot_id=bot_id,
                user_id=user_id,
                role=role,
                granted_by=granted_by
            )
            
            self.db.add(permission)
            
            # Log activity
            self._log_activity(
                bot_id=bot_id,
                user_id=granted_by,
                action="permission_granted",
                details={
                    "target_user_id": str(user_id),
                    "target_username": user.username,
                    "role": role
                }
            )
            
            self.db.commit()
            self.db.refresh(permission)
            
            # Send WebSocket notification
            self._send_permission_notification(
                bot_id, user_id, "granted", {
                    "role": role,
                    "granted_by": str(granted_by)
                }
            )
            
            return permission
    
    def revoke_permission(self, bot_id: uuid.UUID, user_id: uuid.UUID, revoked_by: uuid.UUID) -> bool:
        """
        Revoke permission from a user for a bot.
        
        Args:
            bot_id: Bot ID
            user_id: User ID to revoke permission from
            revoked_by: User ID who is revoking the permission
            
        Returns:
            True if permission was revoked, False if no permission existed
            
        Raises:
            HTTPException: If validation fails
        """
        # Check if revoker has permission
        if not self.check_bot_role(revoked_by, bot_id, "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to revoke access"
            )
        
        # Find the permission
        permission = self.db.query(BotPermission).filter(
            and_(
                BotPermission.user_id == user_id,
                BotPermission.bot_id == bot_id
            )
        ).first()
        
        if not permission:
            return False
        
        # Prevent revoking owner permission
        if permission.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revoke owner permission. Use transfer ownership instead."
            )
        
        # Get user info for logging
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # Log activity before deletion
        self._log_activity(
            bot_id=bot_id,
            user_id=revoked_by,
            action="permission_revoked",
            details={
                "target_user_id": str(user_id),
                "target_username": user.username if user else "Unknown",
                "revoked_role": permission.role
            }
        )
        
        # Delete permission
        self.db.delete(permission)
        self.db.commit()
        
        # Send WebSocket notification
        self._send_permission_notification(
            bot_id, user_id, "revoked", {
                "revoked_role": permission.role,
                "revoked_by": str(revoked_by)
            }
        )
        
        return True
    
    def list_bot_collaborators(self, bot_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        List all collaborators for a bot.
        
        Args:
            bot_id: Bot ID
            
        Returns:
            List of collaborator information
        """
        permissions = self.db.query(BotPermission).filter(
            BotPermission.bot_id == bot_id
        ).join(User, BotPermission.user_id == User.id).all()
        
        collaborators = []
        for permission in permissions:
            collaborators.append({
                "id": permission.id,
                "user_id": permission.user_id,
                "username": permission.user.username,
                "full_name": permission.user.full_name,
                "email": permission.user.email,
                "role": permission.role,
                "granted_by": permission.granted_by,
                "granted_at": permission.granted_at
            })
        
        return collaborators
    
    def transfer_ownership(
        self, 
        bot_id: uuid.UUID, 
        current_owner: uuid.UUID, 
        new_owner: uuid.UUID
    ) -> bool:
        """
        Transfer bot ownership to another user.
        
        Args:
            bot_id: Bot ID
            current_owner: Current owner user ID
            new_owner: New owner user ID
            
        Returns:
            True if ownership was transferred
            
        Raises:
            HTTPException: If validation fails
        """
        # Verify current owner
        if not self.check_bot_role(current_owner, bot_id, "owner"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can transfer ownership"
            )
        
        # Check if new owner user exists
        new_owner_user = self.db.query(User).filter(User.id == new_owner).first()
        if not new_owner_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New owner user not found"
            )
        
        # Get bot
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Update bot owner
        old_owner_user = self.db.query(User).filter(User.id == current_owner).first()
        bot.owner_id = new_owner
        
        # Update permissions
        # Remove old owner permission
        old_owner_permission = self.db.query(BotPermission).filter(
            and_(
                BotPermission.user_id == current_owner,
                BotPermission.bot_id == bot_id,
                BotPermission.role == "owner"
            )
        ).first()
        
        if old_owner_permission:
            self.db.delete(old_owner_permission)
        
        # Add new owner permission or update existing
        new_owner_permission = self.db.query(BotPermission).filter(
            and_(
                BotPermission.user_id == new_owner,
                BotPermission.bot_id == bot_id
            )
        ).first()
        
        if new_owner_permission:
            new_owner_permission.role = "owner"
            new_owner_permission.granted_by = current_owner
            new_owner_permission.granted_at = datetime.utcnow()
        else:
            new_owner_permission = BotPermission(
                bot_id=bot_id,
                user_id=new_owner,
                role="owner",
                granted_by=current_owner
            )
            self.db.add(new_owner_permission)
        
        # Log activity
        self._log_activity(
            bot_id=bot_id,
            user_id=current_owner,
            action="ownership_transferred",
            details={
                "old_owner_id": str(current_owner),
                "old_owner_username": old_owner_user.username if old_owner_user else "Unknown",
                "new_owner_id": str(new_owner),
                "new_owner_username": new_owner_user.username
            }
        )
        
        self.db.commit()
        return True
    
    def get_user_accessible_bots(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get all bots that a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            List of accessible bots with user's role
        """
        permissions = self.db.query(BotPermission).filter(
            BotPermission.user_id == user_id
        ).join(Bot, BotPermission.bot_id == Bot.id).all()
        
        accessible_bots = []
        for permission in permissions:
            accessible_bots.append({
                "bot": permission.bot,
                "role": permission.role,
                "granted_at": permission.granted_at
            })
        
        return accessible_bots
    
    def get_user_accessible_bot_ids(self, user_id: uuid.UUID) -> List[uuid.UUID]:
        """
        Get all bot IDs that a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            List of accessible bot IDs
        """
        permissions = self.db.query(BotPermission.bot_id).filter(
            BotPermission.user_id == user_id
        ).all()
        
        return [permission.bot_id for permission in permissions]
    
    def _log_activity(self, bot_id: uuid.UUID, user_id: uuid.UUID, action: str, details: Dict[str, Any]):
        """
        Log activity for audit trail.
        
        Args:
            bot_id: Bot ID
            user_id: User ID performing the action
            action: Action performed
            details: Additional details about the action
        """
        activity_log = ActivityLog(
            bot_id=bot_id,
            user_id=user_id,
            action=action,
            details=details
        )
        
        self.db.add(activity_log)
        # Note: commit is handled by the calling method
    
    def get_permission_history(self, bot_id: uuid.UUID, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get permission change history for a bot.
        
        Args:
            bot_id: Bot ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of permission history records
        """
        # Get permission-related activity logs
        permission_activities = self.db.query(ActivityLog).filter(
            and_(
                ActivityLog.bot_id == bot_id,
                ActivityLog.action.in_([
                    'permission_granted', 'permission_updated', 'permission_revoked',
                    'ownership_transferred'
                ])
            )
        ).join(
            User, ActivityLog.user_id == User.id, isouter=True
        ).order_by(
            ActivityLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        history = []
        for activity in permission_activities:
            # Extract information from activity details
            details = activity.details or {}
            
            # Determine action type and roles
            if activity.action == 'permission_granted':
                action = 'granted'
                old_role = None
                new_role = details.get('role')
            elif activity.action == 'permission_updated':
                action = 'updated'
                old_role = details.get('old_role')
                new_role = details.get('new_role')
            elif activity.action == 'permission_revoked':
                action = 'revoked'
                old_role = details.get('revoked_role')
                new_role = None
            elif activity.action == 'ownership_transferred':
                action = 'ownership_transferred'
                old_role = 'owner'
                new_role = 'owner'
            else:
                continue
            
            # Get target user info
            target_user_id = details.get('target_user_id')
            target_username = details.get('target_username', 'Unknown')
            
            if target_user_id:
                try:
                    target_user_uuid = uuid.UUID(target_user_id)
                except ValueError:
                    continue
                    
                history.append({
                    "id": activity.id,
                    "bot_id": bot_id,
                    "user_id": target_user_uuid,
                    "username": target_username,
                    "action": action,
                    "old_role": old_role,
                    "new_role": new_role,
                    "granted_by": activity.user_id,
                    "granted_by_username": activity.user.username if activity.user else None,
                    "created_at": activity.created_at
                })
        
        return history
    
    def get_bot_activity_logs(
        self, 
        bot_id: uuid.UUID, 
        limit: int = 50, 
        offset: int = 0, 
        action_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activity logs for a bot.
        
        Args:
            bot_id: Bot ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            action_filter: Optional filter by action type
            
        Returns:
            List of activity log records
        """
        query = self.db.query(ActivityLog).filter(
            ActivityLog.bot_id == bot_id
        ).join(
            User, ActivityLog.user_id == User.id, isouter=True
        )
        
        # Apply action filter if provided
        if action_filter:
            query = query.filter(ActivityLog.action == action_filter)
        
        activities = query.order_by(
            ActivityLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            {
                "id": activity.id,
                "bot_id": bot_id,
                "user_id": activity.user_id,
                "username": activity.user.username if activity.user else None,
                "action": activity.action,
                "details": activity.details,
                "created_at": activity.created_at
            }
            for activity in activities
        ]

    def _send_permission_notification(
        self, 
        bot_id: uuid.UUID, 
        target_user_id: uuid.UUID, 
        action: str, 
        details: Dict[str, Any]
    ):
        """
        Send WebSocket notification for permission changes.
        
        Args:
            bot_id: Bot ID
            target_user_id: User ID whose permissions changed
            action: Action performed (granted, revoked, updated)
            details: Additional details about the change
        """
        try:
            # Import here to avoid circular imports
            import asyncio
            from .websocket_service import connection_manager
            
            # Run async notification in background
            asyncio.create_task(
                connection_manager.send_notification(
                    user_id=str(target_user_id),
                    notification_type="permission_change",
                    data={
                        "bot_id": str(bot_id),
                        "action": action,
                        "details": details
                    }
                )
            )
            
            # Also broadcast to all bot collaborators
            asyncio.create_task(
                connection_manager.broadcast_to_bot_collaborators(
                    bot_id=str(bot_id),
                    message={
                        "type": "permission_change",
                        "bot_id": str(bot_id),
                        "data": {
                            "target_user_id": str(target_user_id),
                            "action": action,
                            "details": details
                        }
                    },
                    db=self.db
                )
            )
            
        except Exception as e:
            # Don't raise exception - WebSocket failure shouldn't break permission changes
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send permission WebSocket notification: {e}")