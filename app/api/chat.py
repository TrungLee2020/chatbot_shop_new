"""
Chat API - REVISED LOGIC
Support both guest and authenticated users properly
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import uuid
from datetime import datetime
import logging

from app.models.chat import ChatMessage, ChatResponse
from app.models.auth import User
from app.api.auth import get_current_user_optional
from app.services.session_manager import SessionManager
from app.services.kafka_service import kafka_service
from app.services.ai_client import ai_client
from app.core.redis_client import get_redis
from app.middleware.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Send chat message - Works for BOTH guest and authenticated users
    
    Guest: Provide device_id (from browser fingerprint/UUID)
    Authenticated: JWT token in header (optional user_id in body)
    
    Flow:
    1. Determine identity (guest device_id OR authenticated user_id)
    2. Get/create session in Redis
    3. Add user message to session
    4. Publish to Kafka (background)
    5. Call AI API immediately
    6. Return response
    """
    
    # ========================================
    # STEP 1: Determine User Identity
    # ========================================
    if current_user:
        identity_id = current_user.user_id
    else:
        if not request.device_id:
            raise HTTPException(400, "device_id required for guest users")
        identity_id = request.device_id
    
    # ✅ Rate limiting
    redis_client = get_redis()
    rate_limiter = RateLimiter(redis_client)
    
    try:
        rate_limiter.check_rate_limit(
            identity=identity_id,
            max_requests=10,
            window_seconds=60
        )
    except HTTPException as e:
        logger.warning(f"⚠️ Rate limit exceeded: {identity_id}")
        raise

    if not current_user and request.device_id:
        # Optional: cleanup in background
        background_tasks.add_task(
            session_manager.cleanup_device_sessions,
            request.device_id,
            keep_latest=5
        )
    # ========================================
    # STEP 2: Rate Limiting
    # ========================================
    redis_client = get_redis()
    rate_limiter = RateLimiter(redis_client)
    
    try:
        rate_limiter.check_rate_limit(
            identity=identity_id,
            max_requests=10,  # 10 messages per minute
            window_seconds=60
        )
    except HTTPException as e:
        logger.warning(f"⚠️ Rate limit exceeded: {identity_id}")
        raise
    
    # ========================================
    # STEP 3: Session Management
    # ========================================
    session_manager = SessionManager(redis_client)
    
    if request.session_id:
        # Use existing session
        session = session_manager.get(request.session_id)
        
        if not session:
            # Session expired or invalid - create new
            logger.warning(f"⚠️ Session not found: {request.session_id}, creating new")
            session = session_manager.create(
                user_id=current_user.user_id if current_user else None,
                device_id=request.device_id if not current_user else None
            )
            request.session_id = session["session_id"]
        else:
            # Verify session ownership
            if is_authenticated and session.get("user_id") != identity_id:
                raise HTTPException(403, "Session does not belong to you")
            if not is_authenticated and session.get("device_id") != identity_id:
                raise HTTPException(403, "Session does not belong to this device")
            
            logger.info(f"✅ Using existing session: {request.session_id}")
    else:
        # Create new session (first message)
        session = session_manager.create(
            user_id=current_user.user_id if current_user else None,
            device_id=request.device_id if not current_user else None
        )
        request.session_id = session["session_id"]
        logger.info(f"✨ New session created: {request.session_id}")
    
    # ========================================
    # STEP 4: Save User Message
    # ========================================
    message_id = str(uuid.uuid4())
    
    session_manager.add_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    
    logger.info(f"💾 User message saved to session")
    
    # ========================================
    # STEP 5: Publish to Kafka (Background)
    # ========================================
    kafka_message = {
        "message_id": message_id,
        "session_id": request.session_id,
        "user_id": current_user.user_id if current_user else None,
        "device_id": request.device_id if not current_user else None,
        "is_authenticated": is_authenticated,
        "message": request.message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to Kafka in background (non-blocking)
    background_tasks.add_task(
        kafka_service.send_chat_request,
        kafka_message
    )
    
    logger.info(f"📨 Kafka publish scheduled")
    
    # ========================================
    # STEP 6: Call AI API (Synchronous)
    # ========================================
    try:
        # Get chat history for context
        session = session_manager.get(request.session_id)
        chat_history = session.get("messages", [])[-10:]  # Last 10 messages
        
        # ✅ SIMPLIFIED AI API CALL - Only message + session_id
        ai_response_data = await ai_client.send_message(
            message=request.message,
            session_id=request.session_id
        )
        
        ai_response_text = ai_response_data.get("response", "")
        products = ai_response_data.get("products", [])
        intent = ai_response_data.get("intent")
        confidence = ai_response_data.get("confidence", 0)
        
        logger.info(f"🤖 AI response received: intent={intent}, products={len(products)}")
        
    except Exception as e:
        logger.error(f"❌ AI API error: {e}")
        # Fallback response
        ai_response_text = "Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau."
        products = []
        intent = "system_error"
        confidence = 0
    
    # ========================================
    # STEP 7: Save AI Response
    # ========================================
    session_manager.add_message(
        session_id=request.session_id,
        role="assistant",
        content=ai_response_text,
        products=products,
        intent=intent
    )
    
    # ========================================
    # STEP 8: Publish Response to Kafka (Background)
    # ========================================
    response_kafka_message = {
        "message_id": message_id,
        "session_id": request.session_id,
        "user_id": current_user.user_id if current_user else None,
        "device_id": request.device_id if not current_user else None,
        "response": ai_response_text,
        "products": products,
        "intent": intent,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    background_tasks.add_task(
        kafka_service.send_chat_response,
        response_kafka_message
    )
    
    # ========================================
    # STEP 9: Return Response to Frontend
    # ========================================
    logger.info(f"✅ Message processed successfully")
    
    return ChatResponse(
        message_id=message_id,
        session_id=request.session_id,
        device_id=request.device_id if not current_user else None,
        user_id=current_user.user_id if current_user else None,
        user_message=request.message,
        ai_response=ai_response_text,
        products=products,
        intent=intent,
        timestamp=datetime.utcnow().isoformat(),
        is_authenticated=is_authenticated
    )


@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get session info - Works for both guest and authenticated
    
    Authenticated: Verify session belongs to user
    Guest: No verification (anyone with session_id can access)
    """
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found or expired")
    
    # If authenticated, verify ownership
    if current_user and session.get("user_id") != current_user.user_id:
        raise HTTPException(403, "Access denied")
    
    return {
        "session_id": session["session_id"],
        "user_id": session.get("user_id"),
        "device_id": session.get("device_id"),
        "is_authenticated": session.get("is_authenticated", False),
        "created_at": session["created_at"],
        "last_activity": session["last_activity"],
        "message_count": len(session.get("messages", [])),
        "messages": session.get("messages", [])[-20:]  # Last 20 messages
    }


@router.post("/session/upgrade")
async def upgrade_session(
    session_id: str,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Upgrade guest session to authenticated session
    Called after guest user logs in or registers
    """
    if not current_user:
        raise HTTPException(401, "Must be authenticated to upgrade session")
    
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    try:
        upgraded_session = session_manager.upgrade_to_authenticated(
            session_id=session_id,
            user_id=current_user.user_id
        )
        
        logger.info(f"✨ Session upgraded: {session_id} → user {current_user.user_id}")
        
        return {
            "message": "Session upgraded successfully",
            "session_id": upgraded_session["session_id"],
            "user_id": upgraded_session["user_id"]
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user_optional)
):
    """Delete session - authenticated users only"""
    if not current_user:
        raise HTTPException(401, "Authentication required")
    
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Verify ownership
    if session.get("user_id") != current_user.user_id:
        raise HTTPException(403, "Access denied")
    
    redis_client.delete(f"session:{session_id}")
    
    return {"message": "Session deleted successfully"}