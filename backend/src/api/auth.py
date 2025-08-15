"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_auth_service, get_current_active_user
from ..schemas.user import (
    UserCreate, UserLogin, UserResponse, Token, RefreshToken,
    PasswordReset, PasswordResetConfirm, PasswordChange
)
from ..services.auth_service import AuthService
from ..models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        auth_service: Authentication service
        
    Returns:
        Created user object
    """
    user = auth_service.register_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return JWT tokens.
    
    Args:
        credentials: User login credentials
        auth_service: Authentication service
        
    Returns:
        JWT access and refresh tokens
    """
    user, tokens = auth_service.authenticate_user(credentials)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshToken,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token data
        auth_service: Authentication service
        
    Returns:
        New JWT token pair
    """
    tokens = auth_service.refresh_token(refresh_data.refresh_token)
    return tokens


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    reset_request: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request password reset token.
    
    Args:
        reset_request: Password reset request
        auth_service: Authentication service
        
    Returns:
        Success message with reset token (in real app, this would be sent via email)
    """
    reset_token = auth_service.request_password_reset(reset_request.email)
    
    # In a real application, you would send this token via email
    # For development/testing, we return it in the response
    return {
        "message": "Password reset instructions sent to your email",
        "note": "In development mode, check the server logs for the reset token"
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Reset password using reset token.
    
    Args:
        reset_data: Password reset confirmation data
        auth_service: Authentication service
        
    Returns:
        Success message
    """
    success = auth_service.reset_password(reset_data)
    if success:
        return {"message": "Password reset successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change user password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        auth_service: Authentication service
        
    Returns:
        Success message
    """
    success = auth_service.change_password(
        current_user, 
        password_data.current_password, 
        password_data.new_password
    )
    if success:
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user (client-side token removal).
    
    Args:
        auth_service: Authentication service
        
    Returns:
        Success message
    """
    # In a JWT-based system, logout is typically handled client-side
    # by removing the tokens from storage. Server-side logout would
    # require token blacklisting, which is not implemented here.
    # For now, we'll just return a success message.
    return {"message": "Logged out successfully"}