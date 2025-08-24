"""Redis-based caching system for the DotMac ISP Framework."""

import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from functools import wraps
import hashlib
import logging

import redis
from redis.connection import ConnectionPool

from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis-based cache manager with advanced features."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with Redis connection."""
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url

        # Parse Redis URL and create connection pool
        self.pool = ConnectionPool.from_url(
            self.redis_url,
            max_connections=20,
            retry_on_timeout=True,
            health_check_interval=30,
        )

        self.redis_client = redis.Redis(connection_pool=self.pool)

        # Test connection
        try:
            self.redis_client.ping()
            logger.info("✅ Redis cache connection established")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            # Fall back to a mock cache for development
            self.redis_client = MockRedisClient()

    def _serialize_key(self, key: str, namespace: str = "default") -> str:
        """Create a namespaced cache key."""
        return f"dotmac:{namespace}:{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for cache storage."""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode()
        else:
            # Use pickle for complex objects
            return pickle.dumps(value)

    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from cache storage."""
        try:
            # Try JSON first (for simple types)
            return json.loads(value.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle for complex objects
            return pickle.loads(value)

    def set(
        self, key: str, value: Any, ttl: int = 3600, namespace: str = "default"
    ) -> bool:
        """Set a cache value with TTL in seconds."""
        try:
            cache_key = self._serialize_key(key, namespace)
            serialized_value = self._serialize_value(value)

            result = self.redis_client.setex(cache_key, ttl, serialized_value)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get a value from cache."""
        try:
            cache_key = self._serialize_key(key, namespace)
            value = self.redis_client.get(cache_key)

            if value is None:
                return None

            return self._deserialize_value(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete a cache key."""
        try:
            cache_key = self._serialize_key(key, namespace)
            result = self.redis_client.delete(cache_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if a cache key exists."""
        try:
            cache_key = self._serialize_key(key, namespace)
            return bool(self.redis_client.exists(cache_key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def increment(
        self, key: str, amount: int = 1, namespace: str = "default"
    ) -> Optional[int]:
        """Increment a numeric cache value."""
        try:
            cache_key = self._serialize_key(key, namespace)
            return self.redis_client.incr(cache_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None

    def set_hash(
        self, hash_key: str, field: str, value: Any, namespace: str = "default"
    ) -> bool:
        """Set a field in a hash."""
        try:
            cache_key = self._serialize_key(hash_key, namespace)
            serialized_value = self._serialize_value(value)
            result = self.redis_client.hset(cache_key, field, serialized_value)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache hash set error for {hash_key}.{field}: {e}")
            return False

    def get_hash(
        self, hash_key: str, field: str, namespace: str = "default"
    ) -> Optional[Any]:
        """Get a field from a hash."""
        try:
            cache_key = self._serialize_key(hash_key, namespace)
            value = self.redis_client.hget(cache_key, field)

            if value is None:
                return None

            return self._deserialize_value(value)
        except Exception as e:
            logger.error(f"Cache hash get error for {hash_key}.{field}: {e}")
            return None

    def get_all_hash(self, hash_key: str, namespace: str = "default") -> Dict[str, Any]:
        """Get all fields from a hash."""
        try:
            cache_key = self._serialize_key(hash_key, namespace)
            hash_data = self.redis_client.hgetall(cache_key)

            return {
                field.decode(): self._deserialize_value(value)
                for field, value in hash_data.items()
            }
        except Exception as e:
            logger.error(f"Cache hash getall error for {hash_key}: {e}")
            return {}

    def delete_hash_field(
        self, hash_key: str, field: str, namespace: str = "default"
    ) -> bool:
        """Delete a field from a hash."""
        try:
            cache_key = self._serialize_key(hash_key, namespace)
            result = self.redis_client.hdel(cache_key, field)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache hash delete error for {hash_key}.{field}: {e}")
            return False

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        try:
            pattern = f"dotmac:{namespace}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear namespace error for {namespace}: {e}")
            return 0

    def set_with_tags(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        tags: List[str] = None,
        namespace: str = "default",
    ) -> bool:
        """Set a cache value with tags for bulk invalidation."""
        try:
            # Set the main value
            if not self.set(key, value, ttl, namespace):
                return False

            # Set tag associations
            if tags:
                for tag in tags:
                    tag_key = self._serialize_key(f"tag:{tag}", namespace)
                    self.redis_client.sadd(tag_key, key)
                    # Set TTL for tag keys (slightly longer than main TTL)
                    self.redis_client.expire(tag_key, ttl + 300)

            return True
        except Exception as e:
            logger.error(f"Cache set with tags error for key {key}: {e}")
            return False

    def invalidate_by_tag(self, tag: str, namespace: str = "default") -> int:
        """Invalidate all cache entries with a specific tag."""
        try:
            tag_key = self._serialize_key(f"tag:{tag}", namespace)
            keys = self.redis_client.smembers(tag_key)

            if not keys:
                return 0

            # Delete all keys associated with this tag
            cache_keys = [self._serialize_key(key.decode(), namespace) for key in keys]
            deleted_count = self.redis_client.delete(*cache_keys)

            # Delete the tag key itself
            self.redis_client.delete(tag_key)

            return deleted_count
        except Exception as e:
            logger.error(f"Cache invalidate by tag error for {tag}: {e}")
            return 0


class MockRedisClient:
    """Mock Redis client for development when Redis is not available."""

    def __init__(self):
        """  Init   operation."""
        self._data = {}
        self._hash_data = {}
        self._sets = {}

    def ping(self):
        """Ping operation."""
        return True

    def setex(self, key: str, ttl: int, value: bytes) -> bool:
        """Setex operation."""
        self._data[key] = value
        return True

    def get(self, key: str) -> Optional[bytes]:
        """Get operation."""
        return self._data.get(key)

    def delete(self, *keys) -> int:
        """Delete operation."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count

    def exists(self, key: str) -> bool:
        """Exists operation."""
        return key in self._data

    def incr(self, key: str, amount: int = 1) -> int:
        """Incr operation."""
        current = int(self._data.get(key, b"0"))
        new_value = current + amount
        self._data[key] = str(new_value).encode()
        return new_value

    def hset(self, hash_key: str, field: str, value: bytes) -> bool:
        """Hset operation."""
        if hash_key not in self._hash_data:
            self._hash_data[hash_key] = {}
        self._hash_data[hash_key][field] = value
        return True

    def hget(self, hash_key: str, field: str) -> Optional[bytes]:
        """Hget operation."""
        return self._hash_data.get(hash_key, {}).get(field)

    def hgetall(self, hash_key: str) -> Dict[bytes, bytes]:
        """Hgetall operation."""
        hash_dict = self._hash_data.get(hash_key, {})
        return {k.encode(): v for k, v in hash_dict.items()}

    def hdel(self, hash_key: str, field: str) -> bool:
        """Hdel operation."""
        if hash_key in self._hash_data and field in self._hash_data[hash_key]:
            del self._hash_data[hash_key][field]
            return True
        return False

    def keys(self, pattern: str) -> List[bytes]:
        """Keys operation."""
        # Simple pattern matching for mock
        return [k.encode() for k in self._data.keys() if pattern.replace("*", "") in k]

    def sadd(self, key: str, *values) -> int:
        """Sadd operation."""
        if key not in self._sets:
            self._sets[key] = set()
        count = 0
        for value in values:
            if value not in self._sets[key]:
                self._sets[key].add(value)
                count += 1
        return count

    def smembers(self, key: str) -> set:
        """Smembers operation."""
        return self._sets.get(key, set())

    def expire(self, key: str, ttl: int) -> bool:
        """Expire operation."""
        # Mock implementation - doesn't actually expire
        return True


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Convenience functions
def cache_set(
    key: str, value: Any, ttl: int = 3600, namespace: str = "default"
) -> bool:
    """Set a cache value."""
    return get_cache_manager().set(key, value, ttl, namespace)


def cache_get(key: str, namespace: str = "default") -> Optional[Any]:
    """Get a cache value."""
    return get_cache_manager().get(key, namespace)


def cache_delete(key: str, namespace: str = "default") -> bool:
    """Delete a cache key."""
    return get_cache_manager().delete(key, namespace)


def cache_invalidate_tag(tag: str, namespace: str = "default") -> int:
    """Invalidate all cache entries with a tag."""
    return get_cache_manager().invalidate_by_tag(tag, namespace)


# Caching decorators
def cached(
    ttl: int = 3600, namespace: str = "default", key_func=None, tags: List[str] = None
):
    """Decorator to cache function results."""

    def decorator(func):
        """Decorator operation."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper operation."""
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation from function name and arguments
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = (
                    f"{func.__name__}:{hashlib.sha256(args_str.encode()).hexdigest()}"
                )

            cache_manager = get_cache_manager()

            # Try to get from cache
            cached_result = cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)

            if tags:
                cache_manager.set_with_tags(cache_key, result, ttl, tags, namespace)
            else:
                cache_manager.set(cache_key, result, ttl, namespace)

            return result

        # Add cache control methods to the decorated function
        wrapper.cache_clear = lambda: cache_delete(f"{func.__name__}:*", namespace)
        wrapper.cache_invalidate_tags = lambda tag_list: [
            cache_invalidate_tag(tag, namespace) for tag in tag_list
        ]

        return wrapper

    return decorator


def cache_user_data(user_id: str, ttl: int = 1800):
    """Decorator specifically for caching user-specific data."""
    return cached(
        ttl=ttl, namespace="users", key_func=lambda *args, **kwargs: f"user:{user_id}"
    )


def cache_tenant_data(tenant_id: str, ttl: int = 3600):
    """Decorator specifically for caching tenant-specific data."""
    return cached(
        ttl=ttl,
        namespace="tenants",
        key_func=lambda *args, **kwargs: f"tenant:{tenant_id}",
    )


# Session management
class SessionManager:
    """Redis-based session manager."""

    def __init__(self, cache_manager: CacheManager = None):
        """  Init   operation."""
        self.cache = cache_manager or get_cache_manager()
        self.namespace = "sessions"
        self.default_ttl = 1800  # 30 minutes

    def create_session(
        self, session_id: str, user_id: str, data: Dict[str, Any] = None
    ) -> bool:
        """Create a new session."""
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            **(data or {}),
        }

        return self.cache.set(
            f"session:{session_id}", session_data, self.default_ttl, self.namespace
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data and update last accessed time."""
        session_data = self.cache.get(f"session:{session_id}", self.namespace)

        if session_data:
            # Update last accessed time
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            self.cache.set(
                f"session:{session_id}", session_data, self.default_ttl, self.namespace
            )

        return session_data

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data."""
        session_data = self.cache.get(f"session:{session_id}", self.namespace)

        if session_data:
            session_data.update(data)
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            return self.cache.set(
                f"session:{session_id}", session_data, self.default_ttl, self.namespace
            )

        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.cache.delete(f"session:{session_id}", self.namespace)

    def extend_session(self, session_id: str, ttl: int = None) -> bool:
        """Extend session TTL."""
        ttl = ttl or self.default_ttl
        session_data = self.cache.get(f"session:{session_id}", self.namespace)

        if session_data:
            return self.cache.set(
                f"session:{session_id}", session_data, ttl, self.namespace
            )

        return False


# Global session manager
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
