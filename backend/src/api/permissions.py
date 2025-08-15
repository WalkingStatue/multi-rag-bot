"""
Bot permissions and collaboration API endpoints.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import uuid

from ..core.database import get_db
from ..core.dependencies import get_current_active_user
from ..core.permissions import (
    get_permission_service,
    require_bot_view,
    require_admin_role
)
from ..models.user import User
from ..schemas.bot import (
    BotPermissionCreate, BotPermissionUpdate, BotPermissionResponse,
    CollaboratorInvite, BulkPermissionUpdate, PermissionHistoryResponse,
    ActivityLogResponse, CollaboratorInviteResponse
)
from ..services.permission_service import PermissionService
from ..services.user_service import UserService

router = APIRouter(prefix="/bots/{bot_id}/permissions", tags=["permissions"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_bot_collaborators(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    _: bool = Depends(require_bot_view)
):
    """
    List all collaborators for a bot.
    
    Requires viewer role or higher.
    """
    return permission_service.list_bot_collaborators(bot_id)


@router.post("/", response_model=BotPermissionResponse, status_code=status.HTTP_201_CREATED)
async def grant_bot_permission(
    bot_id: uuid.UUID,
    permission_data: BotPermissionCreate,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    _: bool = Depends(require_admin_role)
):
    """
    Grant permission to a user for a bot.
    
    Requires admin role or higher. Cannot grant owner role directly.
    """
    permission = permission_service.grant_permission(
        bot_id=bot_id,
        user_id=permission_data.user_id,
        role=permission_data.role,
        granted_by=current_user.id
    )
    
    return BotPermissionResponse.model_validate(permission)


@router.put("/{user_id}", response_model=BotPermissionResponse)
async def update_bot_permission(
    bot_id: uuid.UUID,
    user_id: uuid.UUID,
    permission_update: BotPermissionUpdate,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    _: bool = Depends(require_admin_role)
):
    """
    Update a user's role for a bot.
    
    Requires admin role or higher. Cannot update to owner role directly.
    """
    permission = permission_service.grant_permission(
        bot_id=bot_id,
        user_id=user_id,
        role=permission_update.role,
        granted_by=current_user.id
    )
    
    return BotPermissionResponse.model_validate(permission)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_bot_permission(
    bot_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    _: bool = Depends(require_admin_role)
):
    """
    Revoke a user's permission for a bot.
    
    Requires admin role or higher. Cannot revoke owner permission.
    """
    success = permission_service.revoke_permission(
        bot_id=bot_id,
        user_id=user_id,
        revoked_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )


@router.get("/my-role", response_model=Dict[str, Any])
async def get_my_bot_role(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    _: bool = Depends(require_bot_view)
):
    """
    Get current user's role for a bot.
    
    Requires viewer role or higher.
    """
    role = permission_service.get_user_bot_role(current_user.id, bot_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this bot"
        )
    
    return {
        "bot_id": bot_id,
        "user_id": current_user.id,
        "role": role,
        "permissions": permission_service.ROLE_PERMISSIONS.get(role, [])
    }


@router.post("/invite", response_model=CollaboratorInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_collaborator(
    bot_id: uuid.UUID,
    invite_data: CollaboratorInvite,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin_role)
):
    """
    Invite a collaborator by email or username.
    
    Requires admin role or higher.
    """
    # Create user service instance
    user_service = UserService(db)
    
    # Try to find user by email first, then by username
    target_user = None
    
    # Check if identifier looks like an email
    if "@" in invite_data.identifier:
        target_user = user_service.get_user_by_email(invite_data.identifier)
    else:
        target_user = user_service.get_user_by_username(invite_data.identifier)
    
    if not target_user:
        return CollaboratorInviteResponse(
            success=False,
            message=f"User not found with identifier: {invite_data.identifier}"
        )
    
    try:
        permission = permission_service.grant_permission(
            bot_id=bot_id,
            user_id=target_user.id,
            role=invite_data.role,
            granted_by=current_user.id
        )
        
        return CollaboratorInviteResponse(
            success=True,
            message=f"Successfully invited {target_user.username} as {invite_data.role}",
            user_id=target_user.id,
            permission=BotPermissionResponse.model_validate(permission)
        )
        
    except HTTPException as e:
        return CollaboratorInviteResponse(
            success=False,
            message=e.detail
        )


@router.post("/bulk-update", response_model=Dict[str, Any])
async def bulk_update_permissions(
    bot_id: uuid.UUID,
    bulk_update: BulkPermissionUpdate,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    _: bool = Depends(require_admin_role)
):
    """
    Bulk update permissions for multiple users.
    
    Requires admin role or higher.
    """
    results = {
        "successful": [],
        "failed": [],
        "total": len(bulk_update.user_permissions)
    }
    
    for user_perm in bulk_update.user_permissions:
        try:
            user_id = uuid.UUID(user_perm["user_id"])
            role = user_perm["role"]
            
            # Validate role
            if role not in permission_service.ROLE_HIERARCHY:
                results["failed"].append({
                    "user_id": str(user_id),
                    "error": f"Invalid role: {role}"
                })
                continue
            
            permission = permission_service.grant_permission(
                bot_id=bot_id,
                user_id=user_id,
                role=role,
                granted_by=current_user.id
            )
            
            results["successful"].append({
                "user_id": str(user_id),
                "role": role,
                "permission_id": str(permission.id)
            })
            
        except ValueError as e:
            results["failed"].append({
                "user_id": user_perm.get("user_id", "unknown"),
                "error": f"Invalid user ID format: {e}"
            })
        except HTTPException as e:
            results["failed"].append({
                "user_id": user_perm.get("user_id", "unknown"),
                "error": e.detail
            })
        except Exception as e:
            results["failed"].append({
                "user_id": user_perm.get("user_id", "unknown"),
                "error": f"Unexpected error: {str(e)}"
            })
    
    return results


@router.get("/history", response_model=List[PermissionHistoryResponse])
async def get_permission_history(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: bool = Depends(require_bot_view)
):
    """
    Get permission change history for a bot.
    
    Requires viewer role or higher.
    """
    return permission_service.get_permission_history(bot_id, limit=limit, offset=offset)


@router.get("/activity", response_model=List[ActivityLogResponse])
async def get_bot_activity_logs(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action_filter: Optional[str] = Query(None, description="Filter by action type"),
    _: bool = Depends(require_bot_view)
):
    """
    Get activity logs for a bot.
    
    Requires viewer role or higher.
    """
    return permission_service.get_bot_activity_logs(
        bot_id, 
        limit=limit, 
        offset=offset, 
        action_filter=action_filter
    )