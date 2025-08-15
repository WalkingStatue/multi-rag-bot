"""
Application configuration settings.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/multi_bot_rag"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Vector Store
    qdrant_url: str = "http://localhost:6333"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # File Storage
    upload_dir: str = "./uploads"
    max_file_size: int = 10485760  # 10MB
    
    # CORS
    frontend_url: str = "http://localhost:3000"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY environment variable is required")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


# Global settings instance
settings = Settings()