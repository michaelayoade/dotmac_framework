"""
Caching utilities for dotmac-database.

Provides Redis-based caching with intelligent invalidation,
statistics tracking, and pattern-based operations.
"""

from .redis_cache import (
    SmartCache,
    get_redis_client,
    get_redis_pool,
    configure_redis,
    CacheError,
    CacheStats,
)

__all__ = [
    "SmartCache",
    "get_redis_client", 
    "get_redis_pool",
    "configure_redis",
    "CacheError",
    "CacheStats",
]