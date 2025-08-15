"""
Document management API endpoints.
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..services.document_service import DocumentService
from ..schemas.document import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentStatsResponse,
    DocumentSearchResponse,
    DocumentProcessingResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bots/{bot_id}/documents", tags=["documents"])


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """Get document service instance."""
    try:
        return DocumentService(db)
    except Exception as e:
        logger.error(f"Failed to create DocumentService: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service initialization failed: {str(e)}"
        )


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    bot_id: UUID,
    file: UploadFile = File(...),
    process_immediately: bool = Query(True, description="Process document immediately after upload"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Upload a document to a bot.
    
    Requires editor permissions or higher.
    """
    try:
        document = await document_service.upload_document(
            bot_id=bot_id,
            user_id=current_user.id,
            file=file,
            process_immediately=process_immediately
        )
        
        return DocumentResponse(
            id=document.id,
            bot_id=document.bot_id,
            filename=document.filename,
            file_size=document.file_size,
            mime_type=document.mime_type,
            chunk_count=document.chunk_count,
            uploaded_by=document.uploaded_by,
            created_at=document.created_at,
            processing_status="processed" if document.chunk_count > 0 else "pending"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document to bot {bot_id}: {e}")
        raise


@router.post("/{document_id}/process", response_model=DocumentProcessingResponse)
async def process_document(
    bot_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Process a document: extract text, chunk, generate embeddings, and store.
    
    Requires editor permissions or higher.
    """
    try:
        result = await document_service.process_document(
            document_id=document_id,
            user_id=current_user.id
        )
        
        return DocumentProcessingResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        raise


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    bot_id: UUID,
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of documents to return"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    List documents for a bot.
    
    Requires viewer permissions or higher.
    """
    try:
        documents = await document_service.list_documents(
            bot_id=bot_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing documents for bot {bot_id}: {e}")
        raise


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    bot_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Get detailed information about a document.
    
    Requires viewer permissions or higher.
    """
    try:
        document_info = await document_service.get_document_info(
            document_id=document_id,
            user_id=current_user.id
        )
        
        return DocumentDetailResponse(**document_info)
        
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    bot_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Delete a document and all associated data.
    
    Requires admin permissions or higher.
    """
    try:
        await document_service.delete_document(
            document_id=document_id,
            user_id=current_user.id
        )
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise


@router.get("/search", response_model=DocumentSearchResponse)
async def search_documents(
    bot_id: UUID,
    query: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(10, ge=1, le=50, description="Number of results to return"),
    document_filter: Optional[UUID] = Query(None, description="Filter results to specific document"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Search for relevant document chunks using semantic similarity.
    
    Requires viewer permissions or higher.
    """
    try:
        results = await document_service.search_document_content(
            bot_id=bot_id,
            user_id=current_user.id,
            query=query,
            top_k=top_k,
            document_filter=document_filter
        )
        
        return DocumentSearchResponse(
            query=query,
            results=results,
            total_results=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error searching documents for bot {bot_id}: {e}")
        raise


@router.get("/stats", response_model=Dict[str, Any])
async def get_document_stats(
    bot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about documents for a bot.
    
    Requires viewer permissions or higher.
    """
    try:
        # Check if user has access to the bot
        from ..models.bot import Bot
        from ..services.permission_service import PermissionService
        
        permission_service = PermissionService(db)
        if not permission_service.check_bot_permission(current_user.id, bot_id, "view_documents"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view document statistics"
            )
        
        # Get basic document stats from database
        from ..models.document import Document
        documents = db.query(Document).filter(Document.bot_id == bot_id).all()
        
        total_documents = len(documents)
        total_size = sum(doc.file_size or 0 for doc in documents)
        total_chunks = sum(doc.chunk_count or 0 for doc in documents)
        
        # Get file type distribution
        mime_types = {}
        for doc in documents:
            mime_type = doc.mime_type or "unknown"
            mime_types[mime_type] = mime_types.get(mime_type, 0) + 1
        
        return {
            "total_documents": total_documents,
            "total_file_size": total_size,
            "total_chunks": total_chunks,
            "average_chunks_per_document": total_chunks / total_documents if total_documents > 0 else 0,
            "file_type_distribution": mime_types,
            "vector_store_stats": {"status": "not_implemented", "note": "Vector store integration pending"}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document stats for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document statistics"
        )


@router.post("/reprocess")
async def reprocess_bot_documents(
    bot_id: UUID,
    force_recreate_collection: bool = Query(
        False, 
        description="Whether to delete and recreate the vector collection"
    ),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Reprocess all documents for a bot with current embedding configuration.
    
    This endpoint is useful when:
    - The bot's embedding provider or model has changed
    - There are dimension mismatches in the vector store
    - Documents were processed with different embedding settings
    - RAG retrieval is not working properly
    
    Requires admin permissions or higher.
    """
    try:
        result = await document_service.reprocess_bot_documents(
            bot_id=bot_id,
            user_id=current_user.id,
            force_recreate_collection=force_recreate_collection
        )
        
        return {
            "success": True,
            "message": "Document reprocessing completed",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing documents for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document reprocessing failed: {str(e)}"
        )