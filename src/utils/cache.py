"""Redis cache management"""

import json
from typing import Any, Optional
import redis
from functools import wraps
import asyncio

from src.config.settings import settings
from src.config.constants import CACHE_CONFIG
from src.utils.logger import main_logger

# Lazy Redis client — created on first use to avoid crashing at import time
_redis_client: Optional[redis.Redis] = None


def _get_redis() -> Optional[redis.Redis]:
    """
    Return a Redis client, creating it lazily on first call.
    Returns None if Redis is unavailable so callers can degrade gracefully.
    """
    global _redis_client
    if _redis_client is None:
        try:
            client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Verify connection
            client.ping()
            _redis_client = client
        except Exception as e:
            main_logger.warning(f"Redis unavailable, cache disabled: {e}")
            return None
    return _redis_client


def get_cache(key: str) -> Optional[Any]:
    """
    Get value from cache

    Args:
        key: Cache key

    Returns:
        Cached value or None
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        main_logger.error(f"Cache get error for key {key}: {e}")
        return None


def set_cache(key: str, value: Any, ttl: int = 300) -> bool:
    """
    Set value in cache

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds

    Returns:
        Success status
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        client.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
        return True
    except Exception as e:
        main_logger.error(f"Cache set error for key {key}: {e}")
        return False


def delete_cache(key: str) -> bool:
    """
    Delete value from cache

    Args:
        key: Cache key

    Returns:
        Success status
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception as e:
        main_logger.error(f"Cache delete error for key {key}: {e}")
        return False


def clear_cache_pattern(pattern: str) -> int:
    """
    Clear all cache keys matching pattern.
    Uses SCAN instead of KEYS to avoid blocking Redis in production.

    Args:
        pattern: Key pattern (e.g., "market_data:*")

    Returns:
        Number of keys deleted
    """
    client = _get_redis()
    if client is None:
        return 0
    try:
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted += client.delete(*keys)
            if cursor == 0:
                break
        return deleted
    except Exception as e:
        main_logger.error(f"Cache clear error for pattern {pattern}: {e}")
        return 0


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results. Supports both sync and async functions.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Usage:
        @cached(ttl=60, key_prefix="market_data")
        async def get_market_data(symbol: str):
            return await fetch_data(symbol)
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                cached_value = get_cache(cache_key)
                if cached_value is not None:
                    return cached_value
                result = await func(*args, **kwargs)
                set_cache(cache_key, result, ttl)
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                cached_value = get_cache(cache_key)
                if cached_value is not None:
                    return cached_value
                result = func(*args, **kwargs)
                set_cache(cache_key, result, ttl)
                return result
            return sync_wrapper
    return decorator


class CacheKeys:
    """Cache key templates"""

    @staticmethod
    def market_data(symbol: str, timeframe: str) -> str:
        return f"market_data:{symbol}:{timeframe}"

    @staticmethod
    def order_book(symbol: str) -> str:
        return f"order_book:{symbol}"

    @staticmethod
    def indicator(symbol: str, indicator_name: str) -> str:
        return f"indicator:{symbol}:{indicator_name}"

    @staticmethod
    def sentiment(symbol: str) -> str:
        return f"sentiment:{symbol}"

    @staticmethod
    def onchain(symbol: str) -> str:
        return f"onchain:{symbol}"

    @staticmethod
    def signal(symbol: str) -> str:
        return f"signal:{symbol}"
