"""
Chat API - Support both guest and authenticated users
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import uuid
from datetime import datetime

from app.models.chat import ChatMessage, ChatResponse
from app.models.auth import User
from app.api.auth import get_current_user_optional
from app.services.session_manager import SessionManager
from app.services.kafka_service import kafka_service
from app.services.ai_client import ai_client
from app.core.redis_client import get_redis

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Send chat message
    
    Works for both:
    - Guest users (provide device_id)
    - Logged-in users (provide user_id, or auto-detected from JWT)
    """
    # Determine identity
    if current_user:
        # Logged-in user
        identity_id = current_user.user_id
        is_authenticated = True
        request.user_id = current_user.user_id
    else:
        # Guest user - must provide device_id
        if not request.device_id:
            raise HTTPException(
                status_code=400,
                detail="device_id required for guest users"
            )
        identity_id = request.device_id
        is_authenticated = False
    
    # Initialize session manager
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    # Get or create session
    if request.session_id:
        session = session_manager.get(request.session_id)
        if not session:
            # Session expired or invalid - create new one
            logger.warning(f"Session {request.session_id} not found, creating new")
            session = session_manager.create(
                user_id=request.user_id,
                device_id=request.device_id
            )
            request.session_id = session["session_id"]
    else:
        # First message - create new session
        session = session_manager.create(
            user_id=request.user_id,
            device_id=request.device_id
        )
        request.session_id = session["session_id"]
        logger.info(f"✨ New session created: {request.session_id}")
    
    # Generate message ID
    message_id = str(uuid.uuid4())
    
    # Add user message
    session_manager.add_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    
    # Publish to Kafka
    kafka_message = {
        "message_id": message_id,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "device_id": request.device_id,
        "is_authenticated": is_authenticated,
        "message": request.message,
        "timestamp": datetime.utcnow().isoformat()
    }
    background_tasks.add_task(
        kafka_service.send_chat_request,
        kafka_message
    )
    
    # Call AI API
    try:
        session = session_manager.get(request.session_id)
        chat_history = session.get("messages", [])[-10:]
        
        ai_response_data = await ai_client.send_message(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id or request.device_id,
            chat_history=chat_history
        )
        
        ai_response_text = ai_response_data.get("response", "")
        products = ai_response_data.get("products", [])
        intent = ai_response_data.get("intent")
        
    except Exception as e:
        ai_response_text = "Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại sau."
        products = []
        intent = None
    
    # Add AI response
    session_manager.add_message(
        session_id=request.session_id,
        role="assistant",
        content=ai_response_text,
        products=products,
        intent=intent
    )
    
    return ChatResponse(
        message_id=message_id,
        session_id=request.session_id,
        device_id=request.device_id,
        user_id=request.user_id,
        user_message=request.message,
        ai_response=ai_response_text,
        products=products,
        intent=intent,
        timestamp=datetime.utcnow().isoformat(),
        is_authenticated=is_authenticated
    )