"""
Rate limiting middleware for guest users
"""
import redis
from fastapi import HTTPException, Request
from datetime import datetime

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def check_rate_limit(
        self,
        identity: str,  # user_id or device_id
        max_requests: int = 10,
        window_seconds: int = 60
    ):
        """
        Check if identity exceeded rate limit
        
        Args:
            identity: user_id or device_id
            max_requests: Max requests per window
            window_seconds: Time window in seconds
        """
        key = f"ratelimit:{identity}:{datetime.utcnow().minute}"
        
        # Increment counter
        count = self.redis.incr(key)
        
        if count == 1:
            # First request in this window - set TTL
            self.redis.expire(key, window_seconds)
        
        if count > max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per minute."
            )
        
        return count

# Usage in chat.py
@router.post("/message")
async def send_message(
    request: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_optional)
):
    # ... (identity logic)
    
    # ✅ Rate limiting
    redis_client = get_redis()
    rate_limiter = RateLimiter(redis_client)
    
    try:
        rate_limiter.check_rate_limit(
            identity=identity_id,
            max_requests=10,
            window_seconds=60
        )
    except HTTPException:
        logger.warning(f"⚠️ Rate limit exceeded for {identity_id}")
        raise
    
    # ... (rest of code)