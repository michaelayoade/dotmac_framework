"""
Redis adapter for distributed locks and caching.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set

import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class RedisLock:
    """Distributed lock implementation using Redis."""

    def __init__(self, redis_client: redis.Redis, key: str, timeout: int = 30, retry_delay: float = 0.1):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.lock_value = None
        self._acquired = False

    async def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire the distributed lock."""
        import uuid

        self.lock_value = str(uuid.uuid4())
        end_time = datetime.now() + timedelta(seconds=timeout or self.timeout)

        while True:
            # Try to acquire lock with expiration
            acquired = await self.redis.set(
                self.key,
                self.lock_value,
                nx=True,  # Only set if key doesn't exist
                ex=self.timeout  # Expiration time
            )

            if acquired:
                self._acquired = True
                logger.debug("Acquired distributed lock", key=self.key, value=self.lock_value)
                return True

            if not blocking or (timeout and datetime.now() >= end_time):
                return False

            await asyncio.sleep(self.retry_delay)

    async def release(self) -> bool:
        """Release the distributed lock."""
        if not self._acquired or not self.lock_value:
            return False

        # Use Lua script to ensure atomic check-and-delete
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """

        result = await self.redis.eval(lua_script, 1, self.key, self.lock_value)
        released = bool(result)

        if released:
            self._acquired = False
            logger.debug("Released distributed lock", key=self.key, value=self.lock_value)

        return released

    async def extend(self, additional_time: int = 30) -> bool:
        """Extend the lock expiration time."""
        if not self._acquired or not self.lock_value:
            return False

        # Use Lua script to extend expiration atomically
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("EXPIRE", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        result = await self.redis.eval(lua_script, 1, self.key, self.lock_value, additional_time)
        return bool(result)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


class RedisAdapter:
    """Redis adapter for distributed locks, caching, and coordination."""

    def __init__(self, redis_url: str, max_connections: int = 100):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.redis: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize Redis connection."""
        async with self._lock:
            if self.redis is None:
                self.redis = redis.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    retry_on_timeout=True,
                    socket_timeout=5.0
                )
                # Test connection
                await self.redis.ping()
                logger.info("Redis adapter initialized")

    async def close(self):
        """Close Redis connection."""
        async with self._lock:
            if self.redis:
                await self.redis.close()
                self.redis = None
                logger.info("Redis adapter closed")

    def get_lock(self, resource_key: str, timeout: int = 30) -> RedisLock:
        """Get a distributed lock for a resource."""
        if not self.redis:
            raise RuntimeError("Redis adapter not initialized")
        return RedisLock(self.redis, resource_key, timeout)

    async def acquire_resource_lock(
        self,
        resource_type: str,
        resource_id: str,
        tenant_id: str,
        timeout: int = 30
    ) -> RedisLock:
        """
        Acquire a lock for a specific resource (e.g., device:123, site:456).

        Args:
            resource_type: Type of resource (device, site, etc.)
            resource_id: Unique identifier for the resource
            tenant_id: Tenant ID for isolation
            timeout: Lock timeout in seconds

        Returns:
            RedisLock instance
        """
        lock_key = f"{tenant_id}:{resource_type}:{resource_id}"
        lock = self.get_lock(lock_key, timeout)
        await lock.acquire()
        return lock

    async def set_with_expiry(self, key: str, value: Any, expiry_seconds: int = 3600):
        """Set a value with expiration."""
        if not self.redis:
            await self.initialize()

        serialized_value = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        await self.redis.setex(key, expiry_seconds, serialized_value)

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        if not self.redis:
            await self.initialize()

        value = await self.redis.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value.decode() if isinstance(value, bytes) else value

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.redis:
            await self.initialize()

        result = await self.redis.delete(key)
        return bool(result)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        if not self.redis:
            await self.initialize()

        result = await self.redis.exists(key)
        return bool(result)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        if not self.redis:
            await self.initialize()

        return await self.redis.incrby(key, amount)

    async def set_add(self, key: str, *values: str):
        """Add values to a set."""
        if not self.redis:
            await self.initialize()

        if values:
            await self.redis.sadd(key, *values)

    async def set_remove(self, key: str, *values: str):
        """Remove values from a set."""
        if not self.redis:
            await self.initialize()

        if values:
            await self.redis.srem(key, *values)

    async def set_members(self, key: str) -> Set[str]:
        """Get all members of a set."""
        if not self.redis:
            await self.initialize()

        members = await self.redis.smembers(key)
        return {member.decode() if isinstance(member, bytes) else member for member in members}

    async def list_push(self, key: str, *values: str):
        """Push values to the left of a list."""
        if not self.redis:
            await self.initialize()

        if values:
            await self.redis.lpush(key, *values)

    async def list_pop(self, key: str, timeout: int = 0) -> Optional[str]:
        """Pop a value from the right of a list (blocking if timeout > 0)."""
        if not self.redis:
            await self.initialize()

        if timeout > 0:
            result = await self.redis.brpop(key, timeout)
            return result[1].decode() if result else None
        else:
            result = await self.redis.rpop(key)
            return result.decode() if result else None

    async def hash_set(self, key: str, field: str, value: Any):
        """Set a field in a hash."""
        if not self.redis:
            await self.initialize()

        serialized_value = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        await self.redis.hset(key, field, serialized_value)

    async def hash_get(self, key: str, field: str) -> Optional[Any]:
        """Get a field from a hash."""
        if not self.redis:
            await self.initialize()

        value = await self.redis.hget(key, field)
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value.decode() if isinstance(value, bytes) else value

    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """Get all fields from a hash."""
        if not self.redis:
            await self.initialize()

        hash_data = await self.redis.hgetall(key)
        result = {}

        for field, value in hash_data.items():
            field_str = field.decode() if isinstance(field, bytes) else field
            try:
                result[field_str] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[field_str] = value.decode() if isinstance(value, bytes) else value

        return result

    async def publish(self, channel: str, message: Any):
        """Publish a message to a Redis channel."""
        if not self.redis:
            await self.initialize()

        serialized_message = json.dumps(message) if not isinstance(message, (str, bytes)) else message
        await self.redis.publish(channel, serialized_message)

    async def subscribe(self, *channels: str):
        """Subscribe to Redis channels."""
        if not self.redis:
            await self.initialize()

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub

    async def rate_limit_check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if an operation is within rate limits using sliding window.

        Args:
            key: Rate limit key
            limit: Maximum number of operations
            window_seconds: Time window in seconds
            tenant_id: Optional tenant ID for isolation

        Returns:
            True if within limits, False if rate limited
        """
        if not self.redis:
            await self.initialize()

        rate_key = f"rate_limit:{tenant_id}:{key}" if tenant_id else f"rate_limit:{key}"
        now = datetime.now().timestamp()
        window_start = now - window_seconds

        # Use Lua script for atomic sliding window rate limiting
        lua_script = """
        local key = KEYS[1]
        local window_start = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local window_seconds = tonumber(ARGV[4])

        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Count current entries
        local current = redis.call('ZCARD', key)

        if current < limit then
            -- Add current request
            redis.call('ZADD', key, now, now)
            -- Set expiration
            redis.call('EXPIRE', key, window_seconds)
            return 1
        else
            return 0
        end
        """

        result = await self.redis.eval(
            lua_script, 1, rate_key, window_start, now, limit, window_seconds
        )

        return bool(result)

    async def get_rate_limit_status(
        self,
        key: str,
        window_seconds: int,
        tenant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get current rate limit status."""
        if not self.redis:
            await self.initialize()

        rate_key = f"rate_limit:{tenant_id}:{key}" if tenant_id else f"rate_limit:{key}"
        now = datetime.now().timestamp()
        window_start = now - window_seconds

        # Clean up expired entries and count current
        await self.redis.zremrangebyscore(rate_key, 0, window_start)
        current_count = await self.redis.zcard(rate_key)

        return {
            "current_count": current_count,
            "window_seconds": window_seconds,
            "window_start": int(window_start),
            "window_end": int(now)
        }
