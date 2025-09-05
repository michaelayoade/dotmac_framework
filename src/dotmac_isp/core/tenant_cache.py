"""
Tenant-aware cache service with Redis namespacing.

This module provides tenant-isolated caching to prevent data leakage
between tenants in the container-per-tenant architecture.
"""

import logging
import os
from typing import Any, Optional, Union

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class TenantCacheService:
    """Redis cache service with tenant namespace isolation."""

    def __init__(self, redis_url: str, tenant_namespace: str):
        """
        Initialize tenant cache service.

        Args:
            redis_url: Redis connection URL
            tenant_namespace: Namespace prefix for this tenant (e.g., "tenant:001:")
        """
        self.redis_url = redis_url
        self.tenant_namespace = tenant_namespace
        self._redis: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None

    async def connect(self) -> None:
        """Establish Redis connection with tenant isolation."""
        try:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True,
            )
            self._redis = Redis(connection_pool=self._pool)

            # Test connection
            await self._redis.ping()

            logger.info(f"Connected to Redis with namespace: {self.tenant_namespace}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Disconnected from Redis")

    def _get_namespaced_key(self, key: str) -> str:
        """Add tenant namespace to key."""
        return f"{self.tenant_namespace}{key}"

    async def get(self, key: str) -> Optional[str]:
        """Get value by key with tenant namespace."""
        try:
            namespaced_key = self._get_namespaced_key(key)
            return await self._redis.get(namespaced_key)
        except RedisError as e:
            logger.error(f"Failed to get key {key}: {str(e)}")
            return None

    async def set(
        self, key: str, value: Union[str, int, float], ex: Optional[int] = None
    ) -> bool:
        """Set value with tenant namespace."""
        try:
            namespaced_key = self._get_namespaced_key(key)
            result = await self._redis.set(namespaced_key, value, ex=ex)
            return bool(result)
        except RedisError as e:
            logger.error(f"Failed to set key {key}: {str(e)}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys with tenant namespace."""
        try:
            namespaced_keys = [self._get_namespaced_key(key) for key in keys]
            return await self._redis.delete(*namespaced_keys)
        except RedisError as e:
            logger.error(f"Failed to delete keys {keys}: {str(e)}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists with tenant namespace."""
        try:
            namespaced_key = self._get_namespaced_key(key)
            return bool(await self._redis.exists(namespaced_key))
        except RedisError as e:
            logger.error(f"Failed to check key existence {key}: {str(e)}")
            return False

    async def hset(self, name: str, mapping: dict[str, Any]) -> int:
        """Set hash fields with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return await self._redis.hset(namespaced_name, mapping=mapping)
        except RedisError as e:
            logger.error(f"Failed to set hash {name}: {str(e)}")
            return 0

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return await self._redis.hget(namespaced_name, key)
        except RedisError as e:
            logger.error(f"Failed to get hash field {name}:{key}: {str(e)}")
            return None

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all hash fields with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return await self._redis.hgetall(namespaced_name)
        except RedisError as e:
            logger.error(f"Failed to get hash {name}: {str(e)}")
            return {}

    async def lpush(self, name: str, *values: Union[str, int]) -> int:
        """Push values to list with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return await self._redis.lpush(namespaced_name, *values)
        except RedisError as e:
            logger.error(f"Failed to push to list {name}: {str(e)}")
            return 0

    async def lrange(self, name: str, start: int, end: int) -> list[str]:
        """Get list range with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return await self._redis.lrange(namespaced_name, start, end)
        except RedisError as e:
            logger.error(f"Failed to get list range {name}: {str(e)}")
            return []

    async def expire(self, name: str, time: int) -> bool:
        """Set expiration time with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return bool(await self._redis.expire(namespaced_name, time))
        except RedisError as e:
            logger.error(f"Failed to set expiration {name}: {str(e)}")
            return False

    async def incr(self, name: str, amount: int = 1) -> Optional[int]:
        """Increment counter with tenant namespace."""
        try:
            namespaced_name = self._get_namespaced_key(name)
            return await self._redis.incr(namespaced_name, amount)
        except RedisError as e:
            logger.error(f"Failed to increment {name}: {str(e)}")
            return None

    async def get_tenant_keys(self) -> list[str]:
        """Get all keys for this tenant (for debugging/monitoring)."""
        try:
            pattern = f"{self.tenant_namespace}*"
            keys = await self._redis.keys(pattern)
            # Remove namespace prefix for cleaner output
            return [key.replace(self.tenant_namespace, "") for key in keys]
        except RedisError as e:
            logger.error(f"Failed to get tenant keys: {str(e)}")
            return []

    async def flush_tenant_cache(self) -> int:
        """Flush all cache entries for this tenant."""
        try:
            pattern = f"{self.tenant_namespace}*"
            keys = await self._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Failed to flush tenant cache: {str(e)}")
            return 0


# Global tenant cache instance
_tenant_cache: Optional[TenantCacheService] = None


def initialize_tenant_cache() -> TenantCacheService:
    """Initialize tenant cache service from environment."""
    global _tenant_cache

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    tenant_namespace = os.getenv("REDIS_NAMESPACE", "default:")
    tenant_id = os.getenv("TENANT_ID", "unknown")

    # Ensure namespace ends with colon
    if not tenant_namespace.endswith(":"):
        tenant_namespace += ":"

    logger.info(
        f"Initializing tenant cache for {tenant_id} with namespace {tenant_namespace}"
    )

    _tenant_cache = TenantCacheService(redis_url, tenant_namespace)
    return _tenant_cache


def get_tenant_cache() -> TenantCacheService:
    """Get the tenant cache service instance."""
    if _tenant_cache is None:
        return initialize_tenant_cache()
    return _tenant_cache


async def connect_tenant_cache() -> None:
    """Connect to tenant cache service."""
    cache = get_tenant_cache()
    await cache.connect()


async def disconnect_tenant_cache() -> None:
    """Disconnect from tenant cache service."""
    if _tenant_cache:
        await _tenant_cache.disconnect()
