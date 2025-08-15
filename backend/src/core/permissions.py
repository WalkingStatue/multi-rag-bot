"""
Permission checking middleware and decorators for API endpoints.
"""
from typing import Callable, Any
from functools import wraps
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from .database import get_db
from .dependencies import get_current_active_user
from ..models.user import User
from ..services.permission_service import PermissionService


def require_bot_permission(permission: str):
    """
    Decorator to require specific bot permission for an endpoint.
    
    Args:
        permission: Required permission (e.g., 'edit_bot', 'chat', 'view_bot')
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract bot_id from path parameters
            bot_id = kwargs.get('bot_id')
            if not bot_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bot ID is required"
                )
            
            # Get current user and db from dependencies
            current_user = None
            db = None
            
            # Find current_user and db in function arguments
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif hasattr(arg, 'query'):  # Session object
                    db = arg
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication or database session not found"
                )
            
            # Check permission
            permission_service = PermissionService(db)
            if not permission_service.check_bot_permission(current_user.id, bot_id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission} required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_bot_role(role: str):
    """
    Decorator to require specific bot role for an endpoint.
    
    Args:
        role: Required role (e.g., 'owner', 'admin', 'editor', 'viewer')
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract bot_id from path parameters
            bot_id = kwargs.get('bot_id')
            if not bot_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bot ID is required"
                )
            
            # Get current user and db from dependencies
            current_user = None
            db = None
            
            # Find current_user and db in function arguments
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif hasattr(arg, 'query'):  # Session object
                    db = arg
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication or database session not found"
                )
            
            # Check role
            permission_service = PermissionService(db)
            if not permission_service.check_bot_role(current_user.id, bot_id, role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role: {role} or higher required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class BotPermissionChecker:
    """Dependency class for checking bot permissions in FastAPI endpoints."""
    
    def __init__(self, required_permission: str):
        self.required_permission = required_permission
    
    def __call__(
        self,
        bot_id: uuid.UUID,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> bool:
        """
        Check if current user has required permission for bot.
        
        Args:
            bot_id: Bot ID from path parameter
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            True if user has permission
            
        Raises:
            HTTPException: If permission denied
        """
        permission_service = PermissionService(db)
        
        if not permission_service.check_bot_permission(current_user.id, bot_id, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {self.required_permission} required"
            )
        
        return True


class BotRoleChecker:
    """Dependency class for checking bot roles in FastAPI endpoints."""
    
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    def __call__(
        self,
        bot_id: uuid.UUID,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> bool:
        """
        Check if current user has required role for bot.
        
        Args:
            bot_id: Bot ID from path parameter
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            True if user has role
            
        Raises:
            HTTPException: If role insufficient
        """
        permission_service = PermissionService(db)
        
        if not permission_service.check_bot_role(current_user.id, bot_id, self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role: {self.required_role} or higher required"
            )
        
        return True


# Common permission checkers
require_bot_view = BotPermissionChecker("view_bot")
require_bot_chat = BotPermissionChecker("chat")
require_bot_edit = BotPermissionChecker("edit_bot")
require_bot_delete = BotPermissionChecker("delete_bot")
require_bot_upload = BotPermissionChecker("upload_documents")
require_bot_manage_collaborators = BotPermissionChecker("manage_collaborators")

# Common role checkers
require_viewer_role = BotRoleChecker("viewer")
require_editor_role = BotRoleChecker("editor")
require_admin_role = BotRoleChecker("admin")
require_owner_role = BotRoleChecker("owner")


def get_permission_service(db: Session = Depends(get_db)) -> PermissionService:
    """
    Dependency to get permission service.
    
    Args:
        db: Database session
        
    Returns:
        PermissionService instance
    """
    return PermissionService(db)


def get_bot_service(db: Session = Depends(get_db)):
    """
    Dependency to get bot service.
    
    Args:
        db: Database session
        
    Returns:
        BotService instance
    """
    from ..services.bot_service import BotService
    return BotService(db)