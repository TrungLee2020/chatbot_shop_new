"""
Redis connection
"""
import redis
from config import settings

# Global Redis client
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=50,  # Pool size
    socket_keepalive=True,
    socket_connect_timeout=5,
    health_check_interval=30
)


def get_redis():
    """Get Redis client"""
    return redis_client