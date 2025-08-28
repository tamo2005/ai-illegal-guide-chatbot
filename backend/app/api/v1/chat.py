# backend/app/api/v1/chat.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import asyncio
import json
import time
import uuid
from datetime import datetime

from ...models.schemas import (
    ChatRequest, 
    ChatResponse, 
    StreamingChatResponse,
    HealthCheck,
    ChatSession,
    UserFeedback
)
from ...services.rag_service import RAGService
from ...services.chat_service import ChatService
from ...services.session_service import SessionService
from ...services.safety_service import SafetyService
from ...core.logging import get_logger
from ...core.rate_limiter import RateLimiter
from ...core.exceptions import ChatException, SafetyException

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])

# Initialize services
rag_service = RAGService()
chat_service = ChatService()
session_service = SessionService()
safety_service = SafetyService()
rate_limiter = RateLimiter()

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint with service status"""
    try:
        # Check service health
        services_status = {
            "rag_service": await rag_service.health_check(),
            "chat_service": await chat_service.health_check(),
            "session_service": session_service.is_healthy(),
            "safety_service": safety_service.is_healthy()
        }
        
        all_healthy = all(services_status.values())
        
        return HealthCheck(
            status="healthy" if all_healthy else "degraded",
            timestamp=datetime.utcnow(),
            services=services_status,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_ip: str = Depends(lambda: "127.0.0.1")  # You can implement IP extraction
):
    """Main chat endpoint with comprehensive error handling"""
    chat_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(user_ip)
        
        # Input validation and safety check
        safety_result = await safety_service.check_safety(request.message)
        if not safety_result.is_safe:
            logger.warning(f"Unsafe content detected: {safety_result.reason}")
            raise SafetyException(safety_result.reason)
        
        # Process chat request
        logger.info(f"Processing chat request {chat_id}: {request.message[:50]}...")
        
        # Get or create session
        session = await session_service.get_or_create_session(
            request.session_id, 
            request.user_id
        )
        
        # Generate response using RAG and chat services
        rag_context = await rag_service.get_relevant_context(
            request.message, 
            k=request.context_size or 5
        )
        
        response_text = await chat_service.generate_response(
            message=request.message,
            context=rag_context,
            session_history=session.messages[-10:] if session.messages else [],
            location=request.location,
            language=request.language or "en"
        )
        
        # Calculate confidence and risk assessment
        confidence_score = await chat_service.calculate_confidence(
            request.message, 
            response_text, 
            rag_context
        )
        
        risk_assessment = await safety_service.assess_response_risk(
            request.message, 
            response_text
        )
        
        processing_time = time.time() - start_time
        
        # Create response
        chat_response = ChatResponse(
            id=chat_id,
            message=response_text,
            confidence_score=confidence_score,
            risk_assessment=risk_assessment,
            sources=rag_context.get("sources", []) if rag_context else [],
            processing_time=processing_time,
            session_id=session.id,
            timestamp=datetime.utcnow()
        )
        
        # Save to session in background
        background_tasks.add_task(
            session_service.add_message_to_session,
            session.id,
            request.message,
            response_text,
            confidence_score
        )
        
        logger.info(f"Chat request {chat_id} completed in {processing_time:.2f}s")
        return chat_response
        
    except SafetyException as e:
        logger.warning(f"Safety violation in chat {chat_id}: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "safety_violation",
                "message": "Content violates safety guidelines",
                "details": str(e)
            }
        )
    except ChatException as e:
        logger.error(f"Chat error {chat_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "chat_processing_error",
                "message": "Failed to process chat request",
                "chat_id": chat_id
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat {chat_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "chat_id": chat_id
            }
        )

@router.post("/chat/stream")
async def stream_chat_endpoint(
    request: ChatRequest,
    user_ip: str = Depends(lambda: "127.0.0.1")
):
    """Streaming chat endpoint for real-time responses"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        chat_id = str(uuid.uuid4())
        try:
            # Rate limiting
            await rate_limiter.check_rate_limit(user_ip)
            
            # Safety check
            safety_result = await safety_service.check_safety(request.message)
            if not safety_result.is_safe:
                yield f"data: {json.dumps({'error': 'safety_violation', 'message': safety_result.reason})}\n\n"
                return
            
            # Get context
            rag_context = await rag_service.get_relevant_context(request.message)
            
            # Stream response
            async for chunk in chat_service.generate_streaming_response(
                message=request.message,
                context=rag_context,
                chat_id=chat_id
            ):
                streaming_response = StreamingChatResponse(
                    id=chat_id,
                    chunk=chunk.get("text", ""),
                    is_complete=chunk.get("is_complete", False),
                    metadata=chunk.get("metadata", {})
                )
                yield f"data: {streaming_response.json()}\n\n"
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Streaming error {chat_id}: {str(e)}")
            error_response = {
                "error": "streaming_error",
                "message": "Stream interrupted",
                "chat_id": chat_id
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.post("/feedback")
async def submit_feedback(feedback: UserFeedback):
    """Submit user feedback for response improvement"""
    try:
        feedback_id = await session_service.save_feedback(feedback)
        logger.info(f"Feedback submitted: {feedback_id}")
        return {"message": "Feedback submitted successfully", "id": feedback_id}
    except Exception as e:
        logger.error(f"Feedback submission failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get chat session history"""
    try:
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete chat session"""
    try:
        await session_service.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.get("/analytics/stats")
async def get_analytics():
    """Get basic analytics and usage stats"""
    try:
        stats = await session_service.get_usage_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")