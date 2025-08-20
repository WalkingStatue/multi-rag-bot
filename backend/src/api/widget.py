"""
Widget API endpoints for embeddable chat widgets.
"""
import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import uuid

from ..core.database import get_db
from ..core.dependencies import get_current_active_user
from ..models.user import User
from ..schemas.widget import (
    WidgetConfigCreate, WidgetConfigUpdate, WidgetConfigResponse,
    WidgetInitRequest, WidgetInitResponse, WidgetStatsResponse
)
from ..services.widget_service import WidgetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["widget"])


def get_widget_service(db: Session = Depends(get_db)) -> WidgetService:
    """Get widget service instance."""
    return WidgetService(db)


@router.post("/config", response_model=WidgetConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_widget_config(
    config_data: WidgetConfigCreate,
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Create a new widget configuration.
    
    Args:
        config_data: Widget configuration data
        current_user: Current authenticated user
        widget_service: Widget service instance
        
    Returns:
        Created widget configuration
    """
    widget_config = widget_service.create_widget_config(current_user.id, config_data)
    return WidgetConfigResponse.model_validate(widget_config)


@router.get("/config", response_model=List[WidgetConfigResponse])
async def get_widget_configs(
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Get all widget configurations for the current user.
    
    Args:
        current_user: Current authenticated user
        widget_service: Widget service instance
        
    Returns:
        List of widget configurations
    """
    configs = widget_service.get_widget_configs(current_user.id)
    return [WidgetConfigResponse.model_validate(config) for config in configs]


@router.get("/config/{config_id}", response_model=WidgetConfigResponse)
async def get_widget_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Get a specific widget configuration.
    
    Args:
        config_id: Widget configuration ID
        current_user: Current authenticated user
        widget_service: Widget service instance
        
    Returns:
        Widget configuration
    """
    config = widget_service.get_widget_config(current_user.id, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget configuration not found"
        )
    
    return WidgetConfigResponse.model_validate(config)


@router.put("/config/{config_id}", response_model=WidgetConfigResponse)
async def update_widget_config(
    config_id: uuid.UUID,
    update_data: WidgetConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Update a widget configuration.
    
    Args:
        config_id: Widget configuration ID
        update_data: Update data
        current_user: Current authenticated user
        widget_service: Widget service instance
        
    Returns:
        Updated widget configuration
    """
    config = widget_service.update_widget_config(current_user.id, config_id, update_data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget configuration not found"
        )
    
    return WidgetConfigResponse.model_validate(config)


@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Delete a widget configuration.
    
    Args:
        config_id: Widget configuration ID
        current_user: Current authenticated user
        widget_service: Widget service instance
    """
    success = widget_service.delete_widget_config(current_user.id, config_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget configuration not found"
        )


@router.post("/init")
async def initialize_widget(
    init_request: WidgetInitRequest,
    request: Request,
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Initialize a widget session (simplified version).
    
    Args:
        init_request: Widget initialization request
        request: FastAPI request object
        widget_service: Widget service instance
        
    Returns:
        Simple success response
    """
    try:
        # For now, just return a simple success response
        # In a full implementation, you'd create a proper session
        return {
            "success": True,
            "data": {
                "session_token": f"session_{init_request.visitor_id}_{int(datetime.now().timestamp())}",
                "message": "Widget initialized successfully"
            }
        }
    
    except Exception as e:
        logger.error(f"Error initializing widget session: {e}")
        return {
            "success": False,
            "error": "Failed to initialize widget session"
        }


@router.get("/config/{config_id}/stats", response_model=WidgetStatsResponse)
async def get_widget_stats(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Get statistics for a widget configuration.
    
    Args:
        config_id: Widget configuration ID
        current_user: Current authenticated user
        widget_service: Widget service instance
        
    Returns:
        Widget statistics
    """
    return widget_service.get_widget_stats(current_user.id, config_id)


@router.post("/chat/{bot_id}")
async def widget_chat(
    bot_id: uuid.UUID,
    message_data: dict,
    request: Request,
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Public chat endpoint for widgets (no authentication required).
    
    Args:
        bot_id: Bot ID to chat with
        message_data: Message data containing message, conversation_id, etc.
        request: FastAPI request object
        widget_service: Widget service instance
        
    Returns:
        Bot response
    """
    try:
        # Extract headers for validation
        widget_key = request.headers.get("x-widget-key")
        visitor_id = request.headers.get("x-visitor-id")
        domain = request.headers.get("x-domain")
        
        # Validate required fields
        if not message_data.get("message"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )
        
        # Process the chat message through widget service
        response = await widget_service.process_widget_chat(
            bot_id=bot_id,
            message=message_data["message"],
            conversation_id=message_data.get("conversation_id"),
            visitor_id=visitor_id,
            domain=domain,
            widget_key=widget_key
        )
        
        return {
            "success": True,
            "data": response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing widget chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.post("/cleanup")
async def cleanup_expired_sessions(
    current_user: User = Depends(get_current_active_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """
    Clean up expired widget sessions (admin endpoint).
    
    Args:
        current_user: Current authenticated user
        widget_service: Widget service instance
        
    Returns:
        Number of cleaned up sessions
    """
    # This could be restricted to admin users only
    cleaned_count = widget_service.cleanup_expired_sessions()
    return {"cleaned_sessions": cleaned_count}