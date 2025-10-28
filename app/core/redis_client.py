"""
Redis connection
"""
import redis
from app.config import settings

# Global Redis client
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True
)


def get_redis():
    """Get Redis client"""
    return redis_client