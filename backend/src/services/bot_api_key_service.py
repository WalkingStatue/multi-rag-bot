"""
Bot API Key Management Service.

Handles creation, validation, and management of API keys for bots.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException, status

from ..models.bot import Bot
from ..models.bot_api_key import BotAPIKey
from ..models.user import User
from ..schemas.bot_api_key import (
    BotAPIKeyCreate,
    BotAPIKeyUpdate,
    BotAPIKeyResponse,
    BotAPIKeyCreateResponse,
    BotAPIKeyUsageResponse
)


logger = logging.getLogger(__name__)


class BotAPIKeyService:
    """Service for managing bot API keys."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_api_key(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID,
        api_key_data: BotAPIKeyCreate
    ) -> BotAPIKeyCreateResponse:
        """
        Create a new API key for a bot.
        
        Args:
            bot_id: Bot identifier
            user_id: User creating the API key
            api_key_data: API key creation data
            
        Returns:
            BotAPIKeyCreateResponse with the new API key
            
        Raises:
            HTTPException: If bot not found or user doesn't have permission
        """
        # Verify bot exists and user has access
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # For now, only allow bot owners to create API keys
        # You might want to extend this to allow admins as well
        if bot.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the bot owner can create API keys"
            )
        
        # Create new API key
        try:
            api_key = BotAPIKey(
                bot_id=bot_id,
                name=api_key_data.name,
                description=api_key_data.description,
                created_by=user_id,
                expires_at=api_key_data.expires_at
            )
            
            self.db.add(api_key)
            self.db.commit()
            self.db.refresh(api_key)
            
            # Get the plain key for response (only available during creation)
            plain_key = api_key.get_plain_key()
            
            logger.info(f"Created API key {api_key.id} for bot {bot_id}")
            
            # Return response with plain key
            response_data = BotAPIKeyResponse.model_validate(api_key)
            return BotAPIKeyCreateResponse(
                **response_data.model_dump(),
                api_key=plain_key
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create API key for bot {bot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )
    
    def list_api_keys(
        self,
        bot_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[BotAPIKeyResponse]:
        """
        List all API keys for a bot.
        
        Args:
            bot_id: Bot identifier
            user_id: User requesting the list
            
        Returns:
            List of BotAPIKeyResponse objects
            
        Raises:
            HTTPException: If bot not found or user doesn't have permission
        """
        # Verify bot exists and user has access
        bot = self.db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check if user has permission to view API keys
        if bot.owner_id != user_id:
            # Could extend this to check for admin permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        api_keys = (
            self.db.query(BotAPIKey)
            .filter(BotAPIKey.bot_id == bot_id)
            .order_by(BotAPIKey.created_at.desc())
            .all()
        )
        
        return [BotAPIKeyResponse.model_validate(key) for key in api_keys]
    
    def get_api_key(
        self,
        bot_id: uuid.UUID,
        key_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> BotAPIKeyResponse:
        """
        Get a specific API key.
        
        Args:
            bot_id: Bot identifier
            key_id: API key identifier
            user_id: User requesting the key
            
        Returns:
            BotAPIKeyResponse object
            
        Raises:
            HTTPException: If not found or no permission
        """
        api_key = (
            self.db.query(BotAPIKey)
            .join(Bot)
            .filter(
                and_(
                    BotAPIKey.id == key_id,
                    BotAPIKey.bot_id == bot_id,
                    Bot.owner_id == user_id  # Only owner can access
                )
            )
            .first()
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return BotAPIKeyResponse.model_validate(api_key)
    
    def update_api_key(
        self,
        bot_id: uuid.UUID,
        key_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: BotAPIKeyUpdate
    ) -> BotAPIKeyResponse:
        """
        Update an API key.
        
        Args:
            bot_id: Bot identifier
            key_id: API key identifier
            user_id: User updating the key
            update_data: Update data
            
        Returns:
            Updated BotAPIKeyResponse object
            
        Raises:
            HTTPException: If not found or no permission
        """
        api_key = (
            self.db.query(BotAPIKey)
            .join(Bot)
            .filter(
                and_(
                    BotAPIKey.id == key_id,
                    BotAPIKey.bot_id == bot_id,
                    Bot.owner_id == user_id
                )
            )
            .first()
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(api_key, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(api_key)
            
            logger.info(f"Updated API key {key_id} for bot {bot_id}")
            return BotAPIKeyResponse.model_validate(api_key)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update API key {key_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update API key"
            )
    
    def delete_api_key(
        self,
        bot_id: uuid.UUID,
        key_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> None:
        """
        Delete an API key.
        
        Args:
            bot_id: Bot identifier
            key_id: API key identifier
            user_id: User deleting the key
            
        Raises:
            HTTPException: If not found or no permission
        """
        api_key = (
            self.db.query(BotAPIKey)
            .join(Bot)
            .filter(
                and_(
                    BotAPIKey.id == key_id,
                    BotAPIKey.bot_id == bot_id,
                    Bot.owner_id == user_id
                )
            )
            .first()
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        try:
            self.db.delete(api_key)
            self.db.commit()
            
            logger.info(f"Deleted API key {key_id} for bot {bot_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete API key {key_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete API key"
            )
    
    def verify_api_key(self, api_key: str) -> Optional[BotAPIKey]:
        """
        Verify an API key and return the associated bot API key record.
        
        Args:
            api_key: The API key to verify
            
        Returns:
            BotAPIKey object if valid, None otherwise
        """
        if not api_key or not api_key.startswith('mbr_'):
            return None
        
        key_hash = BotAPIKey._hash_key(api_key)
        
        api_key_record = (
            self.db.query(BotAPIKey)
            .filter(
                and_(
                    BotAPIKey.key_hash == key_hash,
                    BotAPIKey.is_active == True,
                    # Check expiration
                    (BotAPIKey.expires_at.is_(None) | (BotAPIKey.expires_at > datetime.utcnow()))
                )
            )
            .first()
        )
        
        if api_key_record:
            # Update last used timestamp
            api_key_record.last_used_at = datetime.utcnow()
            try:
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to update last_used_at for API key: {e}")
                self.db.rollback()
        
        return api_key_record
    
    def get_bot_by_api_key(self, api_key: str) -> Optional[Bot]:
        """
        Get the bot associated with an API key.
        
        Args:
            api_key: The API key
            
        Returns:
            Bot object if API key is valid, None otherwise
        """
        api_key_record = self.verify_api_key(api_key)
        if not api_key_record:
            return None
        
        return (
            self.db.query(Bot)
            .filter(Bot.id == api_key_record.bot_id)
            .first()
        )
