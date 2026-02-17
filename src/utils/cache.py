"""Redis cache management"""

import json
from typing import Any, Optional
import redis
from functools import wraps

from src.config.settings import settings
from src.config.constants import CACHE_CONFIG
from src.utils.logger import main_logger

# Redis client
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)


def get_cache(key: str) -> Optional[Any]:
    """
    Get value from cache
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None
    """
    try:
        value = redis_client.get(key)
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
    try:
        redis_client.setex(
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
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        main_logger.error(f"Cache delete error for key {key}: {e}")
        return False


def clear_cache_pattern(pattern: str) -> int:
    """
    Clear all cache keys matching pattern
    
    Args:
        pattern: Key pattern (e.g., "market_data:*")
        
    Returns:
        Number of keys deleted
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        main_logger.error(f"Cache clear error for pattern {pattern}: {e}")
        return 0


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        
    Usage:
        @cached(ttl=60, key_prefix="market_data")
        def get_market_data(symbol: str):
            return fetch_data(symbol)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            set_cache(cache_key, result, ttl)
            
            return result
        return wrapper
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
