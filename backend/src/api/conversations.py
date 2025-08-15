"""
Conversation and session management API endpoints.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import uuid

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.conversation import (
    ConversationSessionCreate,
    ConversationSessionResponse,
    MessageCreate,
    MessageResponse,
    ChatRequest,
    ChatResponse
)
from ..services.conversation_service import ConversationService
from ..services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/sessions", response_model=ConversationSessionResponse)
async def create_session(
    session_data: ConversationSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation session."""
    try:
        conversation_service = ConversationService(db)
        session = conversation_service.create_session(current_user.id, session_data)
        return session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation session"
        )


@router.get("/sessions", response_model=List[ConversationSessionResponse])
async def list_sessions(
    bot_id: Optional[uuid.UUID] = Query(None, description="Filter by bot ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List conversation sessions for the current user."""
    conversation_service = ConversationService(db)
    sessions = conversation_service.list_user_sessions(
        current_user.id, bot_id, limit, offset
    )
    return sessions


@router.get("/sessions/{session_id}", response_model=ConversationSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation session."""
    conversation_service = ConversationService(db)
    session = conversation_service.get_session(session_id, current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return session


@router.put("/sessions/{session_id}", response_model=ConversationSessionResponse)
async def update_session(
    session_id: uuid.UUID,
    title: Optional[str] = None,
    is_shared: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a conversation session."""
    try:
        conversation_service = ConversationService(db)
        session = conversation_service.update_session(
            session_id, current_user.id, title, is_shared
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        return session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation session."""
    try:
        conversation_service = ConversationService(db)
        success = conversation_service.delete_session(session_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        return {"message": "Session deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/messages", response_model=MessageResponse)
async def add_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a message to a conversation session."""
    try:
        conversation_service = ConversationService(db)
        message = conversation_service.add_message(current_user.id, message_data)
        return message
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages from a conversation session."""
    conversation_service = ConversationService(db)
    messages = conversation_service.get_session_messages(
        session_id, current_user.id, limit, offset
    )
    return messages


@router.get("/search")
async def search_conversations(
    q: str = Query(..., min_length=1, description="Search query"),
    bot_id: Optional[uuid.UUID] = Query(None, description="Filter by bot ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search conversations across user's accessible bots."""
    conversation_service = ConversationService(db)
    results = conversation_service.search_conversations(
        current_user.id, q, bot_id, limit, offset
    )
    return {
        "query": q,
        "results": results,
        "total": len(results)
    }


@router.get("/export")
async def export_conversations(
    bot_id: Optional[uuid.UUID] = Query(None, description="Filter by bot ID"),
    session_id: Optional[uuid.UUID] = Query(None, description="Export specific session"),
    format_type: str = Query("json", description="Export format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export conversations for backup and analysis."""
    conversation_service = ConversationService(db)
    export_data = conversation_service.export_conversations(
        current_user.id, bot_id, session_id, format_type
    )
    return export_data


@router.get("/analytics")
async def get_conversation_analytics(
    bot_id: Optional[uuid.UUID] = Query(None, description="Filter by bot ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation analytics for user's accessible bots."""
    conversation_service = ConversationService(db)
    analytics = conversation_service.get_conversation_analytics(
        current_user.id, bot_id
    )
    return analytics


@router.post("/bots/{bot_id}/chat", response_model=ChatResponse)
async def chat_with_bot(
    bot_id: uuid.UUID,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a bot and get a response through the RAG pipeline."""
    try:
        chat_service = ChatService(db)
        response = await chat_service.process_message(
            bot_id=bot_id,
            user_id=current_user.id,
            chat_request=chat_request
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.post("/bots/{bot_id}/sessions", response_model=ConversationSessionResponse)
async def create_bot_session(
    bot_id: uuid.UUID,
    title: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation session for a specific bot."""
    try:
        chat_service = ChatService(db)
        session = await chat_service.create_session(
            bot_id=bot_id,
            user_id=current_user.id,
            title=title
        )
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/bots/{bot_id}/diagnose")
async def diagnose_bot_embedding_issues(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Diagnose embedding and RAG retrieval issues for a bot.
    
    This endpoint helps identify common issues when document retrieval
    is not working properly, especially when LLM and embedding providers differ.
    """
    try:
        chat_service = ChatService(db)
        diagnosis = await chat_service.diagnose_embedding_issues(
            bot_id=bot_id,
            user_id=current_user.id
        )
        return diagnosis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to diagnose embedding issues: {str(e)}"
        )


@router.post("/bots/{bot_id}/test-retrieval")
async def test_rag_retrieval(
    bot_id: uuid.UUID,
    test_query: str = "test query about documents",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test RAG retrieval with a specific query to debug document fetching issues.
    
    This endpoint performs the same retrieval process as chat but returns
    detailed debugging information about each step.
    """
    try:
        chat_service = ChatService(db)
        
        # Get bot configuration
        from ..models.bot import Bot
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # Check permissions
        if not chat_service.permission_service.check_bot_permission(
            current_user.id, bot_id, "view_conversations"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have permission to test this bot"
            )
        
        # Test the retrieval process step by step
        result = {
            "test_query": test_query,
            "bot_config": {
                "embedding_provider": bot.embedding_provider,
                "embedding_model": bot.embedding_model,
                "llm_provider": bot.llm_provider,
                "llm_model": bot.llm_model
            },
            "steps": {},
            "retrieved_chunks": [],
            "errors": []
        }
        
        try:
            # Step 1: Check if bot has documents
            has_docs = await chat_service._bot_has_documents(bot_id)
            result["steps"]["has_documents"] = has_docs
            
            if not has_docs:
                result["errors"].append("No documents uploaded for this bot")
                return result
            
            # Step 2: Check vector collection exists
            collection_exists = await chat_service.vector_service.vector_store.collection_exists(str(bot_id))
            result["steps"]["collection_exists"] = collection_exists
            
            if not collection_exists:
                result["errors"].append("Vector collection does not exist")
                return result
            
            # Step 3: Get collection info
            try:
                collection_info = await chat_service.vector_service.get_bot_collection_stats(str(bot_id))
                result["steps"]["collection_info"] = collection_info
            except Exception as e:
                result["errors"].append(f"Failed to get collection info: {str(e)}")
            
            # Step 4: Check API key
            try:
                api_key = chat_service._get_user_api_key_sync(bot.owner_id, bot.embedding_provider)
                result["steps"]["api_key_available"] = bool(api_key)
            except Exception as e:
                result["steps"]["api_key_available"] = False
                result["errors"].append(f"API key issue: {str(e)}")
                return result
            
            # Step 5: Generate query embedding
            try:
                query_embedding = await chat_service.embedding_service.generate_single_embedding(
                    provider=bot.embedding_provider,
                    text=test_query,
                    model=bot.embedding_model,
                    api_key=api_key
                )
                result["steps"]["query_embedding_generated"] = True
                result["steps"]["query_embedding_dimension"] = len(query_embedding)
            except Exception as e:
                result["steps"]["query_embedding_generated"] = False
                result["errors"].append(f"Failed to generate query embedding: {str(e)}")
                return result
            
            # Step 6: Search with different thresholds
            thresholds = [0.9, 0.8, 0.7, 0.6, 0.5, 0.3, 0.1]
            
            for threshold in thresholds:
                try:
                    chunks = await chat_service.vector_service.search_relevant_chunks(
                        bot_id=str(bot_id),
                        query_embedding=query_embedding,
                        top_k=10,  # Get more results for testing
                        score_threshold=threshold
                    )
                    
                    if chunks:
                        result["steps"][f"chunks_found_at_threshold_{threshold}"] = len(chunks)
                        if not result["retrieved_chunks"]:  # Store first successful retrieval
                            result["retrieved_chunks"] = [
                                {
                                    "id": chunk["id"],
                                    "score": chunk["score"],
                                    "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                                    "metadata": chunk["metadata"]
                                }
                                for chunk in chunks[:5]  # Top 5 chunks
                            ]
                        break
                    else:
                        result["steps"][f"chunks_found_at_threshold_{threshold}"] = 0
                        
                except Exception as e:
                    result["errors"].append(f"Search failed at threshold {threshold}: {str(e)}")
            
            # Step 7: Raw search without threshold
            try:
                raw_chunks = await chat_service.vector_service.search_relevant_chunks(
                    bot_id=str(bot_id),
                    query_embedding=query_embedding,
                    top_k=10,
                    score_threshold=None  # No threshold
                )
                result["steps"]["raw_search_results"] = len(raw_chunks)
                
                if raw_chunks and not result["retrieved_chunks"]:
                    result["retrieved_chunks"] = [
                        {
                            "id": chunk["id"],
                            "score": chunk["score"],
                            "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                            "metadata": chunk["metadata"]
                        }
                        for chunk in raw_chunks[:5]
                    ]
                    
            except Exception as e:
                result["errors"].append(f"Raw search failed: {str(e)}")
            
            return result
            
        except Exception as e:
            result["errors"].append(f"Test failed: {str(e)}")
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test RAG retrieval: {str(e)}"
        )