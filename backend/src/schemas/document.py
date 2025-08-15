"""
Document-related Pydantic schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class DocumentBase(BaseModel):
    """Base document schema."""
    filename: str = Field(..., max_length=255)


class DocumentUpload(BaseModel):
    """Schema for document upload."""
    bot_id: uuid.UUID


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: uuid.UUID
    bot_id: uuid.UUID
    uploaded_by: Optional[uuid.UUID]
    file_size: Optional[int]
    mime_type: Optional[str]
    chunk_count: int
    created_at: datetime
    processing_status: str

    model_config = {"from_attributes": True}


class DocumentChunkInfo(BaseModel):
    """Schema for document chunk information."""
    id: uuid.UUID
    chunk_index: int
    content_preview: str
    content_length: int
    metadata: Optional[Dict[str, Any]]
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """Schema for detailed document response."""
    chunks: List[DocumentChunkInfo]


class DocumentListResponse(BaseModel):
    """Schema for document list response."""
    documents: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int


class DocumentProcessingResponse(BaseModel):
    """Schema for document processing response."""
    document_id: str
    filename: str
    chunks_created: int
    embeddings_stored: int
    processing_stats: Dict[str, Any]
    document_metadata: Dict[str, Any]


class DocumentSearchResult(BaseModel):
    """Schema for document search result."""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]
    document_info: Optional[Dict[str, Any]] = None


class DocumentSearchResponse(BaseModel):
    """Schema for document search response."""
    query: str
    results: List[DocumentSearchResult]
    total_results: int


class DocumentStatsResponse(BaseModel):
    """Schema for document statistics response."""
    total_documents: int
    total_file_size: int
    total_chunks: int
    average_chunks_per_document: float
    file_type_distribution: Dict[str, int]
    vector_store_stats: Dict[str, Any]


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response."""
    id: uuid.UUID
    document_id: uuid.UUID
    bot_id: uuid.UUID
    chunk_index: int
    content: str
    embedding_id: Optional[str]
    chunk_metadata: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}