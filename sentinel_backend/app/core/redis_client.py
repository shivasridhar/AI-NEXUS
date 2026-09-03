import redis.asyncio as redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global redis pool
_redis_client = None

async def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        logger.info("Initializing Redis client pool")
        # Initialize connection pool exclusively from the URL in config (which reads from env)
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    return _redis_client

async def close_redis_client():
    global _redis_client
    if _redis_client is not None:
        logger.info("Closing Redis client pool")
        await _redis_client.close()
        _redis_client = None
