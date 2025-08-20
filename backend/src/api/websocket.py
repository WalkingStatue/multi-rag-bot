"""
WebSocket API endpoints for real-time updates.
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.websocket_service import WebSocketService, connection_manager
from ..services.widget_websocket_service import WidgetWebSocketService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat/{bot_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    bot_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat updates for a specific bot.
    
    Args:
        websocket: WebSocket connection
        bot_id: Bot ID to subscribe to
        token: JWT authentication token
        db: Database session
    """
    websocket_service = WebSocketService(db)
    connection_id = None
    
    try:
        # Authenticate user
        user = await websocket_service.authenticate_websocket(websocket, token)
        if not user:
            return
        
        # Verify bot access
        bot = await websocket_service.verify_bot_access(user, bot_id)
        if not bot:
            await websocket.close(code=4003, reason="Bot not found or access denied")
            return
        
        # Connect user to WebSocket
        connection_id = await connection_manager.connect(
            websocket=websocket,
            user_id=str(user.id),
            bot_id=bot_id
        )
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "bot_id": bot_id,
                "bot_name": bot.name,
                "user_id": str(user.id),
                "connection_id": connection_id
            }
        }))
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "typing":
                    # Handle typing indicator
                    is_typing = message.get("data", {}).get("is_typing", False)
                    await websocket_service.handle_typing_indicator(
                        bot_id=bot_id,
                        user_id=str(user.id),
                        username=user.username,
                        is_typing=is_typing
                    )
                
                elif message_type == "ping":
                    # Handle ping/pong for connection health
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }))
                
                elif message_type == "session_sync":
                    # Handle session synchronization
                    session_id = message.get("data", {}).get("session_id")
                    if session_id:
                        logger.info(f"User {user.id} synced to session {session_id} for bot {bot_id}")
                        await websocket.send_text(json.dumps({
                            "type": "session_synced",
                            "data": {
                                "session_id": session_id,
                                "bot_id": bot_id,
                                "timestamp": message.get("timestamp")
                            }
                        }))
                    else:
                        logger.warning("Session sync message missing session_id")
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from WebSocket")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except:
                    # If we can't send error message, connection is likely broken
                    break
            
            except WebSocketDisconnect:
                # Re-raise WebSocketDisconnect to be handled by outer try-catch
                raise
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Error processing message"
                    }))
                except:
                    # If we can't send error message, connection is likely broken
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id if user else 'unknown'}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id)


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for general user notifications.
    
    Args:
        websocket: WebSocket connection
        token: JWT authentication token
        db: Database session
    """
    websocket_service = WebSocketService(db)
    connection_id = None
    
    try:
        # Authenticate user
        user = await websocket_service.authenticate_websocket(websocket, token)
        if not user:
            return
        
        # Connect user to WebSocket (no specific bot)
        connection_id = await connection_manager.connect(
            websocket=websocket,
            user_id=str(user.id)
        )
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "user_id": str(user.id),
                "connection_id": connection_id,
                "connection_type": "notifications"
            }
        }))
        
        # Listen for messages (mainly ping/pong for health checks)
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Handle ping/pong for connection health
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }))
                
                else:
                    logger.warning(f"Unknown notification message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from notifications WebSocket")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except:
                    # If we can't send error message, connection is likely broken
                    break
            
            except WebSocketDisconnect:
                # Re-raise WebSocketDisconnect to be handled by outer try-catch
                raise
            
            except Exception as e:
                logger.error(f"Error processing notifications WebSocket message: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Error processing message"
                    }))
                except:
                    # If we can't send error message, connection is likely broken
                    break
    
    except WebSocketDisconnect:
        logger.info(f"Notifications WebSocket disconnected for user {user.id if user else 'unknown'}")
    
    except Exception as e:
        logger.error(f"Notifications WebSocket error: {e}")
    
    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Returns:
        Connection statistics
    """
    return {
        "total_connections": connection_manager.get_connection_count(),
        "connected_users": len(connection_manager.get_connected_users()),
        "bot_subscriptions": len(connection_manager.bot_subscriptions)
    }


@router.get("/ws/connections")
async def get_websocket_connections():
    """
    Get detailed WebSocket connection information (for debugging).
    
    Returns:
        Detailed connection information
    """
    return {
        "connected_users": connection_manager.get_connected_users(),
        "bot_subscriptions": {
            bot_id: list(users) 
            for bot_id, users in connection_manager.bot_subscriptions.items()
        },
        "connection_metadata": connection_manager.connection_metadata
    }


@router.websocket("/ws/widget/{session_token}")
async def websocket_widget_endpoint(
    websocket: WebSocket,
    session_token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for widget chat sessions.
    
    Args:
        websocket: WebSocket connection
        session_token: Widget session token
        db: Database session
    """
    widget_ws_service = WidgetWebSocketService(db)
    
    try:
        # Authenticate and handle widget session
        await widget_ws_service.handle_widget_connection(websocket, session_token)
    
    except WebSocketDisconnect:
        logger.info(f"Widget WebSocket disconnected for session {session_token}")
    
    except Exception as e:
        logger.error(f"Widget WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass