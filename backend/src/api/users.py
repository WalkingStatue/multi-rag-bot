"""
User management API endpoints.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
import base64
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_active_user, get_user_service
from ..schemas.user import (
    UserResponse, UserUpdate, UserSearch, PasswordChange,
    APIKeyCreate, APIKeyUpdate, APIKeyResponse,
    UserSettingsUpdate, UserSettingsResponse, UserAnalytics
)
from ..services.user_service import UserService
from ..services.auth_service import AuthService
from ..services.llm_service import LLMProviderService
from ..services.embedding_service import EmbeddingProviderService
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user profile.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile data
    """
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update current user profile.
    
    Args:
        updates: Profile updates
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        Updated user profile
    """
    updated_user = user_service.update_user_profile(current_user, updates)
    return UserResponse.model_validate(updated_user)


@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Upload and save a user's avatar image.

    The image is stored in the database as a data URL (base64-encoded).
    This avoids managing a separate static file store and works well for small avatars.
    """
    # Validate content type
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Allowed: png, jpg, jpeg, webp",
        )

    # Read and size-check (max ~2MB)
    content = await file.read()
    max_bytes = 2 * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar image too large (max 2MB)",
        )

    # Encode as data URL and update profile
    data_url = f"data:{file.content_type};base64,{base64.b64encode(content).decode()}"
    updated = user_service.update_user_profile(current_user, UserUpdate(avatar_url=data_url))
    return UserResponse.model_validate(updated)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    auth_service = AuthService(db)
    try:
        auth_service.change_password(
            current_user,
            password_data.current_password,
            password_data.new_password
        )
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.get("/search", response_model=List[UserSearch])
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search users for collaboration.
    
    Args:
        q: Search query
        limit: Maximum number of results
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        List of matching users
    """
    return user_service.search_users(q, limit)


# API Key Management Endpoints

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all API keys for current user.
    
    Args:
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        List of user's API keys (without actual key values)
    """
    return user_service.get_user_api_keys(current_user)


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def add_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Add or update API key for a provider.
    
    Args:
        api_key_data: API key data
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        Created/updated API key info
    """
    return user_service.add_api_key(current_user, api_key_data)


@router.put("/api-keys/{provider}", response_model=APIKeyResponse)
async def update_api_key(
    provider: str,
    api_key_data: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update API key for a specific provider.
    
    Args:
        provider: Provider name (openai, anthropic, openrouter, gemini)
        api_key_data: Updated API key data
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        Updated API key info
    """
    return user_service.update_api_key(current_user, provider, api_key_data)


@router.delete("/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete API key for a specific provider.
    
    Args:
        provider: Provider name (openai, anthropic, openrouter, gemini)
        current_user: Current authenticated user
        user_service: User service
    """
    user_service.delete_api_key(current_user, provider)
    return None


@router.post("/api-keys/{provider}/validate", status_code=status.HTTP_200_OK)
async def validate_api_key(
    provider: str,
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate API key for a specific provider.
    
    Args:
        provider: Provider name (openai, anthropic, openrouter, gemini)
        api_key_data: API key data to validate
        current_user: Current authenticated user
        
    Returns:
        Validation result
    """
    if provider != api_key_data.provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider in URL must match provider in request body"
        )
    
    llm_service = LLMProviderService()
    try:
        is_valid = await llm_service.validate_api_key(provider, api_key_data.api_key)
        return {
            "valid": is_valid,
            "provider": provider,
            "message": "API key is valid" if is_valid else "API key is invalid"
        }
    finally:
        await llm_service.close()


@router.get("/api-keys/providers", status_code=status.HTTP_200_OK)
async def get_supported_providers(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of supported LLM providers with static model lists.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of supported providers with their available models
    """
    llm_service = LLMProviderService()
    try:
        providers = llm_service.get_supported_providers()
        provider_info = {}
        
        for provider in providers:
            provider_info[provider] = {
                "name": provider,
                "models": llm_service.get_available_models(provider)
            }
        
        return {
            "providers": provider_info,
            "total": len(providers)
        }
    finally:
        await llm_service.close()


@router.get("/api-keys/providers/{provider}/models", status_code=status.HTTP_200_OK)
async def get_provider_models_dynamic(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get list of available models for a specific provider using user's API key.
    
    Args:
        provider: Provider name (openai, anthropic, gemini, openrouter)
        current_user: Current authenticated user
        user_service: User service dependency
        
    Returns:
        List of available models from the provider API
    """
    # Get user's API key for this provider
    api_key = user_service.get_user_api_key(current_user.id, provider)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No API key configured for provider '{provider}'. Please add your API key first."
        )
    
    llm_service = LLMProviderService()
    try:
        models = await llm_service.get_available_models_dynamic(provider, api_key)
        return {
            "provider": provider,
            "models": models,
            "total": len(models),
            "source": "api"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch models for {provider}: {e}")
        # Fall back to static models
        static_models = llm_service.get_available_models(provider)
        return {
            "provider": provider,
            "models": static_models,
            "total": len(static_models),
            "source": "static"
        }
    finally:
        await llm_service.close()


# Embedding Provider Endpoints

@router.get("/embedding-providers", status_code=status.HTTP_200_OK)
async def get_supported_embedding_providers(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of supported embedding providers with static model lists.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of supported embedding providers with their available models
    """
    embedding_service = EmbeddingProviderService()
    try:
        providers = embedding_service.get_supported_providers()
        provider_info = {}
        
        for provider in providers:
            provider_info[provider] = {
                "name": provider,
                "models": embedding_service.get_available_models(provider),
                "requires_api_key": True  # All embedding providers require API keys now
            }
        
        return {
            "providers": provider_info,
            "total": len(providers)
        }
    finally:
        await embedding_service.close()


@router.get("/embedding-providers/{provider}/models", status_code=status.HTTP_200_OK)
async def get_embedding_provider_models_dynamic(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get list of available embedding models for a specific provider using user's API key.
    
    Args:
        provider: Provider name (openai, gemini, anthropic)
        current_user: Current authenticated user
        user_service: User service dependency
        
    Returns:
        List of available embedding models from the provider API
    """
    # Get user's API key for this provider
    api_key = user_service.get_user_api_key(current_user.id, provider)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No API key configured for provider '{provider}'. Please add your API key first."
        )
    
    embedding_service = EmbeddingProviderService()
    try:
        models = await embedding_service.get_available_models_dynamic(provider, api_key)
        return {
            "provider": provider,
            "models": models,
            "total": len(models),
            "source": "api"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch embedding models for {provider}: {e}")
        # Fall back to static models
        static_models = embedding_service.get_available_models(provider)
        return {
            "provider": provider,
            "models": static_models,
            "total": len(static_models),
            "source": "static"
        }
    finally:
        await embedding_service.close()


@router.post("/embedding-providers/{provider}/validate", status_code=status.HTTP_200_OK)
async def validate_embedding_api_key(
    provider: str,
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate API key for a specific embedding provider.
    
    Args:
        provider: Provider name (openai, gemini, anthropic)
        api_key_data: API key data to validate
        current_user: Current authenticated user
        
    Returns:
        Validation result
    """
    if provider != api_key_data.provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider in URL must match provider in request body"
        )
    
    embedding_service = EmbeddingProviderService()
    try:
        is_valid = await embedding_service.validate_api_key(provider, api_key_data.api_key)
        return {
            "valid": is_valid,
            "provider": provider,
            "message": "API key is valid" if is_valid else "API key is invalid"
        }
    finally:
        await embedding_service.close()


# User Settings Endpoints

@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get current user settings and preferences.
    
    Args:
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        User settings and preferences
    """
    return user_service.get_user_settings(current_user)


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user settings and preferences.
    
    Args:
        settings_update: Settings updates
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        Updated user settings
    """
    return user_service.update_user_settings(current_user, settings_update)


# User Analytics Endpoints

@router.get("/analytics", response_model=UserAnalytics)
async def get_user_analytics(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get comprehensive user analytics and activity data.
    
    Args:
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        Comprehensive user analytics including activity summary,
        bot usage statistics, conversation analytics, and recent activity
    """
    return user_service.get_user_analytics(current_user)


@router.get("/activity", status_code=status.HTTP_200_OK)
async def get_user_activity(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of activity records"),
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user activity summary.
    
    Args:
        limit: Maximum number of activity records to return
        current_user: Current authenticated user
        user_service: User service
        
    Returns:
        User activity summary with recent actions
    """
    activity_summary = user_service.get_user_activity_summary(current_user)
    return {
        "activity_summary": activity_summary,
        "message": f"Retrieved activity summary for user {current_user.username}"
    }