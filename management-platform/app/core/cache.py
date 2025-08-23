"""
Comprehensive caching layer for improved performance.
"""

import json
import pickle
import hashlib
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio

import redis.asyncio as aioredis
from pydantic import BaseModel

from ..config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    
    default_ttl: int = 3600  # 1 hour
    key_prefix: str = "dotmac:mgmt:"
    max_key_length: int = 250
    compression_threshold: int = 1024  # Compress values larger than 1KB
    serializer: str = "json"  # json, pickle


class CacheStats(BaseModel):
    """Cache statistics."""
    
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheManager:
    """Comprehensive cache manager with Redis backend."""
    
    def __init__(self, redis_url: str = None, config: CacheConfig = None):
        self.redis_url = redis_url or settings.redis_url
        self.config = config or CacheConfig()
        self.redis_pool: Optional[aioredis.Redis] = None
        self.stats = CacheStats()
        self._local_cache: Dict[str, tuple] = {}  # Local memory cache for critical data
        self._local_cache_max_size = 1000
    
    async def init_connection(self):
        """Initialize Redis connection pool."""
        try:
            self.redis_pool = aioredis.from_url(
                self.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=False,  # We handle encoding ourselves
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_pool.ping()
            logger.info("Cache manager initialized with Redis connection")
            
        except Exception as e:
            logger.error("Failed to initialize cache manager", error=str(e), exc_info=True)
            self.redis_pool = None
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_pool:
            await self.redis_pool.close()
    
    def _generate_key(self, key: str, namespace: str = None) -> str:
        """Generate cache key with namespace and prefix."""
        if namespace:
            full_key = f"{self.config.key_prefix}{namespace}:{key}"
        else:
            full_key = f"{self.config.key_prefix}{key}"
        
        # Hash key if too long
        if len(full_key) > self.config.max_key_length:
            key_hash = hashlib.sha256(full_key.encode()).hexdigest()
            full_key = f"{self.config.key_prefix}hashed:{key_hash}"
        
        return full_key
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.serializer == "pickle":
            return pickle.dumps(value)
        else:
            # JSON serialization with support for datetime and other types
            return json.dumps(value, default=str).encode('utf-8')
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.config.serializer == "pickle":
            return pickle.loads(data)
        else:
            return json.loads(data.decode('utf-8'))
    
    async def get(self, key: str, namespace: str = None, default: Any = None) -> Any:
        """Get value from cache."""
        cache_key = self._generate_key(key, namespace)
        
        try:
            # Check local cache first for critical data
            if cache_key in self._local_cache:
                value, expiry = self._local_cache[cache_key]
                if datetime.utcnow() < expiry:
                    self.stats.hits += 1
                    return value
                else:
                    del self._local_cache[cache_key]
            
            # Check Redis cache
            if self.redis_pool:
                data = await self.redis_pool.get(cache_key)
                if data:
                    value = self._deserialize_value(data)
                    self.stats.hits += 1
                    logger.debug("Cache hit", key=cache_key)
                    return value
            
            self.stats.misses += 1
            logger.debug("Cache miss", key=cache_key)
            return default
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache get error", key=cache_key, error=str(e))
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = None, 
        namespace: str = None,
        local_cache: bool = False
    ) -> bool:
        """Set value in cache."""
        cache_key = self._generate_key(key, namespace)
        ttl = ttl or self.config.default_ttl
        
        try:
            # Store in local cache if requested (for critical data)
            if local_cache:
                if len(self._local_cache) >= self._local_cache_max_size:
                    # Remove oldest item
                    oldest_key = min(self._local_cache.keys(), 
                                   key=lambda k: self._local_cache[k][1])
                    del self._local_cache[oldest_key]
                
                expiry = datetime.utcnow() + timedelta(seconds=ttl)
                self._local_cache[cache_key] = (value, expiry)
            
            # Store in Redis
            if self.redis_pool:
                data = self._serialize_value(value)
                await self.redis_pool.setex(cache_key, ttl, data)
                
                self.stats.sets += 1
                logger.debug("Cache set", key=cache_key, ttl=ttl)
                return True
            
            return False
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache set error", key=cache_key, error=str(e))
            return False
    
    async def delete(self, key: str, namespace: str = None) -> bool:
        """Delete value from cache."""
        cache_key = self._generate_key(key, namespace)
        
        try:
            # Remove from local cache
            if cache_key in self._local_cache:
                del self._local_cache[cache_key]
            
            # Remove from Redis
            if self.redis_pool:
                result = await self.redis_pool.delete(cache_key)
                self.stats.deletes += 1
                logger.debug("Cache delete", key=cache_key, found=bool(result))
                return bool(result)
            
            return False
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache delete error", key=cache_key, error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str, namespace: str = None) -> int:
        """Delete keys matching pattern."""
        search_pattern = self._generate_key(pattern, namespace)
        
        try:
            if self.redis_pool:
                keys = await self.redis_pool.keys(search_pattern)
                if keys:
                    deleted = await self.redis_pool.delete(*keys)
                    logger.debug("Cache pattern delete", pattern=search_pattern, count=deleted)
                    return deleted
            
            return 0
            
        except Exception as e:
            self.stats.errors += 1
            logger.error("Cache pattern delete error", pattern=search_pattern, error=str(e))
            return 0
    
    async def exists(self, key: str, namespace: str = None) -> bool:
        """Check if key exists in cache."""
        cache_key = self._generate_key(key, namespace)
        
        try:
            if cache_key in self._local_cache:
                _, expiry = self._local_cache[cache_key]
                if datetime.utcnow() < expiry:
                    return True
                else:
                    del self._local_cache[cache_key]
            
            if self.redis_pool:
                result = await self.redis_pool.exists(cache_key)
                return bool(result)
            
            return False
            
        except Exception as e:
            logger.error("Cache exists error", key=cache_key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1, namespace: str = None) -> int:
        """Increment counter value."""
        cache_key = self._generate_key(key, namespace)
        
        try:
            if self.redis_pool:
                result = await self.redis_pool.incrby(cache_key, amount)
                return result
            
            return amount
            
        except Exception as e:
            logger.error("Cache increment error", key=cache_key, error=str(e))
            return 0
    
    async def expire(self, key: str, ttl: int, namespace: str = None) -> bool:
        """Set expiration for existing key."""
        cache_key = self._generate_key(key, namespace)
        
        try:
            if self.redis_pool:
                result = await self.redis_pool.expire(cache_key, ttl)
                return bool(result)
            
            return False
            
        except Exception as e:
            logger.error("Cache expire error", key=cache_key, error=str(e))
            return False
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats
    
    async def flush_namespace(self, namespace: str) -> int:
        """Flush all keys in a namespace."""
        pattern = f"{self.config.key_prefix}{namespace}:*"
        return await self.delete_pattern(pattern)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        try:
            if not self.redis_pool:
                return {"status": "unhealthy", "reason": "No Redis connection"}
            
            # Test basic operations
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            await self.set(test_key, test_value, ttl=60)
            retrieved_value = await self.get(test_key)
            
            if retrieved_value != test_value:
                return {"status": "unhealthy", "reason": "Data integrity check failed"}
            
            await self.delete(test_key)
            
            return {
                "status": "healthy",
                "stats": self.stats.dict(),
                "local_cache_size": len(self._local_cache)
            }
            
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.init_connection()
    
    return _cache_manager


# Decorators for caching
def cached(
    ttl: int = 3600,
    namespace: str = None,
    key_builder: Callable = None,
    local_cache: bool = False,
    condition: Callable = None
):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key from function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            cache_manager = await get_cache_manager()
            
            # Check condition if provided
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_manager.set(cache_key, result, ttl, namespace, local_cache)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            loop = asyncio.get_event_loop()
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            async def _async_execution():
                cache_manager = await get_cache_manager()
                
                # Check condition if provided
                if condition and not condition(*args, **kwargs):
                    return func(*args, **kwargs)
                
                # Try to get from cache
                cached_result = await cache_manager.get(cache_key, namespace)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                
                # Cache the result
                await cache_manager.set(cache_key, result, ttl, namespace, local_cache)
                
                return result
            
            return loop.run_until_complete(_async_execution())
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_invalidate(namespace: str = None, pattern: str = None):
    """Decorator to invalidate cache after function execution."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            cache_manager = await get_cache_manager()
            
            if pattern:
                await cache_manager.delete_pattern(pattern, namespace)
            elif namespace:
                await cache_manager.flush_namespace(namespace)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            loop = asyncio.get_event_loop()
            
            async def _invalidate():
                cache_manager = await get_cache_manager()
                
                if pattern:
                    await cache_manager.delete_pattern(pattern, namespace)
                elif namespace:
                    await cache_manager.flush_namespace(namespace)
            
            loop.run_until_complete(_invalidate())
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Common cache operations
class TenantCache:
    """Cache operations specific to tenant data."""
    
    NAMESPACE = "tenants"
    DEFAULT_TTL = 1800  # 30 minutes
    
    @staticmethod
    async def get_tenant_config(tenant_id: str) -> Optional[Dict]:
        """Get tenant configuration from cache."""
        cache_manager = await get_cache_manager()
        return await cache_manager.get(f"config:{tenant_id}", TenantCache.NAMESPACE)
    
    @staticmethod
    async def set_tenant_config(tenant_id: str, config: Dict, ttl: int = None):
        """Cache tenant configuration."""
        cache_manager = await get_cache_manager()
        await cache_manager.set(
            f"config:{tenant_id}", 
            config, 
            ttl or TenantCache.DEFAULT_TTL,
            TenantCache.NAMESPACE
        )
    
    @staticmethod
    async def invalidate_tenant(tenant_id: str):
        """Invalidate all cache entries for a tenant."""
        cache_manager = await get_cache_manager()
        await cache_manager.delete_pattern(f"*{tenant_id}*", TenantCache.NAMESPACE)


class UserCache:
    """Cache operations specific to user data."""
    
    NAMESPACE = "users"
    DEFAULT_TTL = 900  # 15 minutes
    
    @staticmethod
    async def get_user_permissions(user_id: str) -> Optional[List]:
        """Get user permissions from cache."""
        cache_manager = await get_cache_manager()
        return await cache_manager.get(f"permissions:{user_id}", UserCache.NAMESPACE)
    
    @staticmethod
    async def set_user_permissions(user_id: str, permissions: List, ttl: int = None):
        """Cache user permissions."""
        cache_manager = await get_cache_manager()
        await cache_manager.set(
            f"permissions:{user_id}",
            permissions,
            ttl or UserCache.DEFAULT_TTL,
            UserCache.NAMESPACE,
            local_cache=True  # Cache permissions locally for faster access
        )
    
    @staticmethod
    async def invalidate_user(user_id: str):
        """Invalidate all cache entries for a user."""
        cache_manager = await get_cache_manager()
        await cache_manager.delete_pattern(f"*{user_id}*", UserCache.NAMESPACE)


# Alias for backward compatibility
CacheService = CacheManager