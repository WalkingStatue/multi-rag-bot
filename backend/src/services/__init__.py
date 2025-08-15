"""
Services package for business logic.
"""
from .auth_service import AuthService
from .user_service import UserService
from .llm_service import LLMProviderService
from .embedding_service import EmbeddingProviderService
from .permission_service import PermissionService
from .bot_service import BotService
from .vector_store import (
    VectorStoreInterface,
    QdrantVectorStore,
    VectorStoreFactory,
    VectorService
)
from .rag_pipeline_manager import RAGPipelineManager
from .embedding_compatibility_manager import EmbeddingCompatibilityManager
from .vector_collection_manager import VectorCollectionManager
from .rag_error_recovery import RAGErrorRecovery

__all__ = [
    "AuthService",
    "UserService", 
    "LLMProviderService",
    "EmbeddingProviderService",
    "PermissionService",
    "BotService",
    "VectorStoreInterface",
    "QdrantVectorStore",
    "VectorStoreFactory",
    "VectorService",
    "RAGPipelineManager",
    "EmbeddingCompatibilityManager",
    "VectorCollectionManager",
    "RAGErrorRecovery",
]