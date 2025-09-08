"""Redis-based storage implementations."""
from __future__ import annotations

import asyncio
import pickle
import threading
import time
from contextlib import asynccontextmanager, contextmanager, suppress
from typing import TYPE_CHECKING, Any

from .base import SyncIdempotencyStore, SyncLockStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    # Graceful degradation when Redis is not installed
    REDIS_AVAILABLE = False
    aioredis = redis = None


class RedisIdempotencyStore:
    """Redis-based idempotency store."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "idempotency:"):
        if not REDIS_AVAILABLE:
            msg = "Redis extras not installed. Install with: pip install dotmac-tasks-utils[redis]"
            raise ImportError(msg)

        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url)
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """Get a stored result by key."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)

        data = await redis_client.get(redis_key)
        if data is None:
            return None

        try:
            return pickle.loads(data)
        except (pickle.PickleError, TypeError, ValueError):
            # If unpickling fails, return None and clean up
            await redis_client.delete(redis_key)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a result with optional TTL in seconds."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)

        try:
            data = pickle.dumps(value)

            if ttl:
                await redis_client.setex(redis_key, ttl, data)
            else:
                await redis_client.set(redis_key, data)
        except (pickle.PickleError, TypeError) as e:
            msg = f"Cannot serialize value for key {key}: {e}"
            raise ValueError(msg) from e

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)
        return bool(await redis_client.exists(redis_key))

    async def delete(self, key: str) -> None:
        """Delete a key from the store."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)
        await redis_client.delete(redis_key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


class RedisLockStore:
    """Redis-based distributed lock store."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "lock:"):
        if not REDIS_AVAILABLE:
            msg = "Redis extras not installed. Install with: pip install dotmac-tasks-utils[redis]"
            raise ImportError(msg)

        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url)
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"

    @asynccontextmanager
    async def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        ttl: float = 60.0,
    ) -> AsyncIterator[bool]:
        """Acquire a distributed lock using Redis SET NX EX."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)
        lock_value = f"{time.time()}_{asyncio.current_task().get_name()}"

        acquired = False
        start_time = time.time()

        # Try to acquire lock within timeout
        while time.time() - start_time < timeout:
            # Use SET NX EX for atomic lock acquisition with TTL
            result = await redis_client.set(
                redis_key,
                lock_value,
                nx=True,  # Only set if key doesn't exist
                ex=int(ttl)  # Set expiration in seconds
            )

            if result:
                acquired = True
                break

            # Wait a bit before retrying
            await asyncio.sleep(0.01)

        try:
            yield acquired
        finally:
            if acquired:
                # Use Lua script for safe lock release
                # Only release if we still own the lock
                lua_script = """
                if redis.call("GET", KEYS[1]) == ARGV[1] then
                    return redis.call("DEL", KEYS[1])
                else
                    return 0
                end
                """
                with suppress(Exception):
                    await redis_client.eval(lua_script, 1, redis_key, lock_value)

    async def is_locked(self, key: str) -> bool:
        """Check if a lock is currently held."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)
        return bool(await redis_client.exists(redis_key))

    async def release_lock(self, key: str) -> None:
        """Force release a lock (use with caution)."""
        redis_client = await self._get_redis()
        redis_key = self._make_key(key)
        await redis_client.delete(redis_key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


class SyncRedisIdempotencyStore(SyncIdempotencyStore):
    """Synchronous Redis-based idempotency store."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "idempotency:"):
        if not REDIS_AVAILABLE:
            msg = "Redis extras not installed. Install with: pip install dotmac-tasks-utils[redis]"
            raise ImportError(msg)

        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Any | None:
        """Get a stored result by key."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)

        data = redis_client.get(redis_key)
        if data is None:
            return None

        try:
            return pickle.loads(data)
        except (pickle.PickleError, TypeError, ValueError):
            # If unpickling fails, return None and clean up
            redis_client.delete(redis_key)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a result with optional TTL in seconds."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)

        try:
            data = pickle.dumps(value)

            if ttl:
                redis_client.setex(redis_key, ttl, data)
            else:
                redis_client.set(redis_key, data)
        except (pickle.PickleError, TypeError) as e:
            msg = f"Cannot serialize value for key {key}: {e}"
            raise ValueError(msg) from e

    def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)
        return bool(redis_client.exists(redis_key))

    def delete(self, key: str) -> None:
        """Delete a key from the store."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)
        redis_client.delete(redis_key)

    def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            self._redis.close()


class SyncRedisLockStore(SyncLockStore):
    """Synchronous Redis-based distributed lock store."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "lock:"):
        if not REDIS_AVAILABLE:
            msg = "Redis extras not installed. Install with: pip install dotmac-tasks-utils[redis]"
            raise ImportError(msg)

        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key."""
        return f"{self.prefix}{key}"

    @contextmanager
    def acquire_lock(
        self,
        key: str,
        timeout: float = 10.0,
        ttl: float = 60.0,
    ) -> Iterator[bool]:
        """Acquire a distributed lock using Redis SET NX EX."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)
        lock_value = f"{time.time()}_{threading.current_thread().ident}"

        acquired = False
        start_time = time.time()

        # Try to acquire lock within timeout
        while time.time() - start_time < timeout:
            # Use SET NX EX for atomic lock acquisition with TTL
            result = redis_client.set(
                redis_key,
                lock_value,
                nx=True,  # Only set if key doesn't exist
                ex=int(ttl)  # Set expiration in seconds
            )

            if result:
                acquired = True
                break

            # Wait a bit before retrying
            time.sleep(0.01)

        try:
            yield acquired
        finally:
            if acquired:
                # Use Lua script for safe lock release
                lua_script = """
                if redis.call("GET", KEYS[1]) == ARGV[1] then
                    return redis.call("DEL", KEYS[1])
                else
                    return 0
                end
                """
                with suppress(Exception):
                    redis_client.eval(lua_script, 1, redis_key, lock_value)

    def is_locked(self, key: str) -> bool:
        """Check if a lock is currently held."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)
        return bool(redis_client.exists(redis_key))

    def release_lock(self, key: str) -> None:
        """Force release a lock (use with caution)."""
        redis_client = self._get_redis()
        redis_key = self._make_key(key)
        redis_client.delete(redis_key)

    def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
