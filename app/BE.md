# 🚀 BACKEND COMPLETE - PART 2

## 📝 8. CHAT API

**File:** `app/models/chat.py`

```python
"""
Chat models
"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class ChatMessage(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    message: str


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    user_message: str
    ai_response: str
    products: List[Dict] = []
    intent: Optional[str] = None
    timestamp: str


class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    message_count: int
    last_activity: str
```

**File:** `app/api/chat.py`

```python
"""
Chat API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
import uuid
from datetime import datetime
import logging

from app.models.chat import ChatMessage, ChatResponse, SessionInfo
from app.models.auth import User
from app.api.auth import get_current_user
from app.services.session_manager import SessionManager
from app.services.kafka_service import kafka_service
from app.services.ai_client import ai_client
from app.core.redis_client import get_redis

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Send chat message
    
    Flow:
    1. Get or create session in Redis
    2. Add user message to session
    3. Publish to Kafka (async)
    4. Call AI API
    5. Add AI response to session
    6. Return response
    """
    # Validate user_id
    if request.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")
    
    # Initialize session manager
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    # Get or create session
    if request.session_id:
        session = session_manager.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = session_manager.create(user_id=request.user_id)
        request.session_id = session["session_id"]
    
    logger.info(f"📨 Processing message for session {request.session_id}")
    
    # Generate message ID
    message_id = str(uuid.uuid4())
    
    # Add user message to session
    session_manager.add_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    
    # Prepare Kafka message
    kafka_message = {
        "message_id": message_id,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "message": request.message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to Kafka (background task)
    background_tasks.add_task(
        kafka_service.send_chat_request,
        kafka_message
    )
    
    # Call AI API
    try:
        # Get chat history from session
        session = session_manager.get(request.session_id)
        chat_history = session.get("messages", [])[-10:]  # Last 10 messages
        
        # Call AI API
        ai_response_data = await ai_client.send_message(
            message=request.message,
            session_id=request.session_id,
            # user_id=request.user_id,
            # chat_history=chat_history
        )
        
        ai_response_text = ai_response_data.get("response", "")
        products = ai_response_data.get("products", [])
        intent = ai_response_data.get("intent")
        
    except Exception as e:
        logger.error(f"❌ Error calling AI API: {e}")
        ai_response_text = "Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại sau."
        products = []
        intent = None
    
    # Add AI response to session
    session_manager.add_message(
        session_id=request.session_id,
        role="assistant",
        content=ai_response_text,
        products=products,
        intent=intent
    )
    
    # Prepare response for Kafka
    response_kafka_message = {
        "message_id": message_id,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "response": ai_response_text,
        "products": products,
        "intent": intent,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send response to Kafka (background task)
    background_tasks.add_task(
        kafka_service.send_chat_response,
        response_kafka_message
    )
    
    logger.info(f"✅ Message processed for session {request.session_id}")
    
    return ChatResponse(
        message_id=message_id,
        session_id=request.session_id,
        user_message=request.message,
        ai_response=ai_response_text,
        products=products,
        intent=intent,
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get session info"""
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify ownership
    if session["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return SessionInfo(
        session_id=session["session_id"],
        user_id=session["user_id"],
        created_at=session["created_at"],
        message_count=len(session.get("messages", [])),
        last_activity=session["last_activity"]
    )


@router.get("/sessions", response_model=List[SessionInfo])
async def get_user_sessions(
    current_user: User = Depends(get_current_user)
):
    """
    Get all sessions for current user
    
    Note: In production, store session list in separate Redis set
    This is a simplified version scanning all session keys
    """
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    # Scan for user's sessions (simplified - not optimal for production)
    sessions = []
    for key in redis_client.scan_iter(match="session:*"):
        session_id = key.split(":")[1]
        session = session_manager.get(session_id)
        
        if session and session["user_id"] == current_user.user_id:
            sessions.append(SessionInfo(
                session_id=session["session_id"],
                user_id=session["user_id"],
                created_at=session["created_at"],
                message_count=len(session.get("messages", [])),
                last_activity=session["last_activity"]
            ))
    
    return sessions


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete session"""
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify ownership
    if session["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session_manager.delete(session_id)
    
    return {"message": "Session deleted successfully"}
```

---

## 🏠 9. MAIN APPLICATION

**File:** `app/main.py`

```python
"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api import auth, chat
from app.core.redis_client import redis_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager
    Runs on startup and shutdown
    """
    # Startup
    logger.info("🚀 Starting application...")
    
    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("⏹️  Shutting down application...")
    redis_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Check Redis
    redis_status = "healthy"
    try:
        redis_client.ping()
    except Exception as e:
        redis_status = f"unhealthy: {e}"
    
    return {
        "status": "healthy",
        "redis": redis_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

---

## 🧪 10. TESTING & USAGE

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start infrastructure

```bash
# Start Redis + Kafka
docker-compose up -d

# Check status
docker-compose ps

# Create Kafka topics
python scripts/create_topics.py
```

### Start API

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Test endpoints

**1. Login to get JWT token:**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**2. Send chat message:**

```bash
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "user_id": "user_123",
    "message": "Tìm iPhone 15 giá dưới 30 triệu"
  }'
```

**Response:**
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "660e9411-f39c-52e5-b827-557766551111",
  "user_message": "Tìm iPhone 15 giá dưới 30 triệu",
  "ai_response": "Tôi đã tìm thấy 5 sản phẩm iPhone 15 phù hợp...",
  "products": [
    {
      "product_id": "prod_001",
      "product_name": "iPhone 15 Pro Max 256GB",
      "price": 29500000,
      "shop_name": "TechZone Vietnam"
    }
  ],
  "intent": "product_search",
  "timestamp": "2025-10-28T10:30:00Z"
}
```

**3. Get session info:**

```bash
curl -X GET http://localhost:8000/chat/session/YOUR_SESSION_ID \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**4. Get user sessions:**

```bash
curl -X GET http://localhost:8000/chat/sessions \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**5. Health check:**

```bash
curl http://localhost:8000/health
```

---

## 🔍 11. KAFKA CONSUMER (Background Worker)

**File:** `app/consumer.py`

```python
"""
Kafka Consumer - Background worker to process messages
Run separately from main API
"""
import logging
from app.services.kafka_service import kafka_service
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_chat_request(data: dict):
    """
    Process chat request from Kafka
    
    This is where you can add additional processing:
    - Analytics
    - Logging to MongoDB
    - Trigger notifications
    - etc.
    """
    logger.info(f"Processing chat request: {data['message_id']}")
    logger.info(f"  Session: {data['session_id']}")
    logger.info(f"  User: {data['user_id']}")
    logger.info(f"  Message: {data['message']}")
    
    # TODO: Add your processing logic here
    # - Save to MongoDB
    # - Send to analytics
    # - etc.


def process_chat_response(data: dict):
    """
    Process chat response from Kafka
    """
    logger.info(f"Processing chat response: {data['message_id']}")
    logger.info(f"  Response: {data['response'][:50]}...")
    
    # TODO: Add your processing logic here


def main():
    """Main consumer loop"""
    logger.info("🔄 Starting Kafka consumer...")
    
    # Consume chat requests
    kafka_service.consume_messages(
        topics=[
            settings.KAFKA_TOPIC_CHAT_REQUESTS,
            settings.KAFKA_TOPIC_CHAT_RESPONSES
        ],
        callback=lambda data: (
            process_chat_request(data) 
            if 'message' in data 
            else process_chat_response(data)
        )
    )


if __name__ == "__main__":
    main()
```

**Run consumer (separate terminal):**
```bash
python app/consumer.py
```

---

## 📊 12. MONITORING

### Check Kafka messages in UI

Open: http://localhost:8080

- View topics
- See message counts
- Monitor consumer lag

### Check Redis keys

```bash
docker exec -it chatbot-redis redis-cli

# List all session keys
KEYS session:*

# Get session data
GET session:YOUR_SESSION_ID

# Check TTL
TTL session:YOUR_SESSION_ID
```

### Application logs

```bash
# API logs
tail -f logs/api.log

# Consumer logs
tail -f logs/consumer.log
```

---

## 🚀 13. DEPLOYMENT

### Environment variables for production

```env
# Production settings
DEBUG=False
JWT_SECRET_KEY=super-secret-key-change-in-production-min-32-chars

# Use managed services
REDIS_HOST=your-redis-host.com
REDIS_PASSWORD=your-redis-password
KAFKA_BOOTSTRAP_SERVERS=broker1:9092,broker2:9092,broker3:9092

# AI API
AI_API_URL=https://your-ai-api.com/chat
AI_API_KEY=your-production-api-key
```

### Docker for production

**File:** `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**

```bash
docker build -t chatbot-api .
docker run -p 8000:8000 --env-file .env chatbot-api
```

---

## ✅ COMPLETE CHECKLIST

- [x] **Kafka setup** - docker-compose.yml
- [x] **Kafka Producer** - Send messages
- [x] **Kafka Consumer** - Process messages  
- [x] **Redis setup** - docker-compose.yml
- [x] **Session Manager** - Redis sessions with TTL
- [x] **JWT Authentication** - Login + protected routes
- [x] **Chat API** - Send/receive messages
- [x] **AI Client** - Call external AI API
- [x] **Health check** - Monitor services
- [x] **CORS** - Cross-origin requests
- [x] **Background tasks** - Async Kafka publishing
- [x] **Error handling** - Proper exceptions
- [x] **Logging** - Structured logs

---

## 🎉 YOU'RE DONE!

Toàn bộ backend đã ready:
- ✅ JWT authentication
- ✅ Redis session management  
- ✅ Kafka message queue
- ✅ FastAPI với tất cả endpoints
- ✅ Integration với AI API của bạn

**Start everything:**
```bash
# 1. Infrastructure
docker-compose up -d

# 2. Create Kafka topics
python scripts/create_topics.py

# 3. Start API
uvicorn app.main:app --reload

# 4. Start consumer (optional)
python app/consumer.py
```

**Test:**
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  | jq -r '.access_token')

# Send message
curl -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_123","message":"Hello"}'
```
