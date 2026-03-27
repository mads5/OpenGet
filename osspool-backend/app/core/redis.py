import logging

logger = logging.getLogger(__name__)

_pool = None
_available = True


async def get_redis():
    global _pool, _available
    if not _available:
        return None
    if _pool is None:
        try:
            import redis.asyncio as aioredis
            from app.core.config import get_settings
            settings = get_settings()
            _pool = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20,
            )
            await _pool.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            _pool = None
            _available = False
            return None
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
