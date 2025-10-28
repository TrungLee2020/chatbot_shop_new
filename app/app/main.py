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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

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
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

@scheduler.scheduled_job('interval', minutes=30)
async def cleanup_old_sessions():
    """Cleanup expired sessions every 30 minutes"""
    redis_client = get_redis()
    session_manager = SessionManager(redis_client)
    
    # Scan tất cả device sessions
    for key in redis_client.scan_iter(match="device_sessions:*"):
        device_id = key.split(":")[1]
        deleted = session_manager.cleanup_device_sessions(device_id, keep_latest=5)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} sessions for device {device_id}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
    logger.info("✅ Scheduler started")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )