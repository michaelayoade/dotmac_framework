"""
Redis storage backend for background operations.

Provides a Redis implementation of the storage interface with
durable persistence and distributed lock support.
"""

import json
import time
from typing import Any, Dict, List, Optional

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    Redis = None
    REDIS_AVAILABLE = False

from .base import Storage, StorageConnectionError, StorageTimeoutError, LockAcquisitionError


class RedisStorage(Storage):
    """
    Redis storage backend for distributed deployments.
    
    Uses Redis data structures to store idempotency keys, saga workflows,
    and operation history with proper TTL and indexing support.
    
    Redis Schema:
    - Idempotency: bgops:idempo:{key} (HASH)
    - Index: bgops:idempo:index (ZSET) 
    - Saga: bgops:saga:{saga_id} (JSON blob)
    - History: bgops:saga:history:{saga_id} (LIST)
    - Operations: bgops:operation:{operation_id} (HASH)
    - Locks: bgops:lock:{lock_key} (String with TTL)
    """

    def __init__(
        self, 
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "bgops",
        max_connections: int = 10,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        **redis_kwargs: Any
    ) -> None:
        """
        Initialize Redis storage.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            **redis_kwargs: Additional Redis client parameters
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis is not available. Install with: pip install 'dotmac-tasks[redis]'"
            )
        
        self.prefix = prefix
        self.retry_on_timeout = retry_on_timeout
        
        # Create Redis client
        self.redis: Redis = redis.from_url(
            redis_url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True,
            **redis_kwargs
        )

    def _key(self, key_type: str, identifier: str) -> str:
        """Generate prefixed key."""
        return f"{self.prefix}:{key_type}:{identifier}"

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute Redis operation with optional retry on timeout."""
        try:
            return await operation(*args, **kwargs)
        except redis.TimeoutError as e:
            if self.retry_on_timeout:
                # Single retry on timeout
                try:
                    return await operation(*args, **kwargs)
                except redis.TimeoutError:
                    raise StorageTimeoutError(f"Redis operation timed out: {e}")
            else:
                raise StorageTimeoutError(f"Redis operation timed out: {e}")
        except redis.ConnectionError as e:
            raise StorageConnectionError(f"Redis connection failed: {e}")

    async def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        """Get idempotency data by key."""
        redis_key = self._key("idempo", key)
        
        data = await self._execute_with_retry(self.redis.hgetall, redis_key)
        if not data:
            return None
        
        # Convert Redis string values back to appropriate types
        result = dict(data)
        
        # Parse JSON result if present
        if result.get("result"):
            try:
                result["result"] = json.loads(result["result"])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if not valid JSON
        
        return result

    async def set_idempotency(
        self, 
        key: str, 
        mapping: Dict[str, Any], 
        ttl_seconds: int
    ) -> None:
        """Set idempotency data with TTL."""
        redis_key = self._key("idempo", key)
        
        # Prepare data for Redis (serialize result as JSON)
        redis_data = mapping.copy()
        if redis_data.get("result") is not None:
            redis_data["result"] = json.dumps(redis_data["result"])
        
        # Use pipeline for atomic operation
        pipe = self.redis.pipeline()
        pipe.hset(redis_key, mapping=redis_data)
        pipe.expire(redis_key, ttl_seconds)
        
        await self._execute_with_retry(pipe.execute)

    async def delete_idempotency(self, key: str) -> bool:
        """Delete idempotency data by key."""
        redis_key = self._key("idempo", key)
        index_key = self._key("idempo", "index")
        
        # Use pipeline for atomic operation
        pipe = self.redis.pipeline()
        pipe.delete(redis_key)
        pipe.zrem(index_key, key)
        
        results = await self._execute_with_retry(pipe.execute)
        return results[0] > 0  # First result is from DELETE

    async def index_idempotency(self, key: str, timestamp: float) -> None:
        """Index idempotency key by timestamp."""
        index_key = self._key("idempo", "index")
        await self._execute_with_retry(
            self.redis.zadd, index_key, {key: timestamp}
        )

    async def get_expired_idempotency_keys(self, before_timestamp: float) -> List[str]:
        """Get idempotency keys that expired before the given timestamp."""
        index_key = self._key("idempo", "index")
        
        # Get keys with score (timestamp) less than before_timestamp
        expired_keys = await self._execute_with_retry(
            self.redis.zrangebyscore, 
            index_key, 
            "-inf", 
            before_timestamp
        )
        
        return expired_keys

    async def get_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Get saga workflow data by ID."""
        redis_key = self._key("saga", saga_id)
        
        data = await self._execute_with_retry(self.redis.get, redis_key)
        if not data:
            return None
        
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    async def set_saga(self, saga_id: str, mapping: Dict[str, Any]) -> None:
        """Set saga workflow data."""
        redis_key = self._key("saga", saga_id)
        
        json_data = json.dumps(mapping, default=str)
        await self._execute_with_retry(self.redis.set, redis_key, json_data)

    async def delete_saga(self, saga_id: str) -> bool:
        """Delete saga workflow data by ID."""
        saga_key = self._key("saga", saga_id)
        history_key = self._key("saga:history", saga_id)
        
        # Use pipeline for atomic operation
        pipe = self.redis.pipeline()
        pipe.delete(saga_key)
        pipe.delete(history_key)
        
        results = await self._execute_with_retry(pipe.execute)
        return results[0] > 0  # First result is from saga deletion

    async def append_saga_history(
        self, 
        saga_id: str, 
        entry: Dict[str, Any]
    ) -> None:
        """Append an entry to saga execution history."""
        history_key = self._key("saga:history", saga_id)
        
        json_entry = json.dumps(entry, default=str)
        await self._execute_with_retry(self.redis.rpush, history_key, json_entry)

    async def get_saga_history(
        self, 
        saga_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get saga execution history."""
        history_key = self._key("saga:history", saga_id)
        
        # Get all entries (newest first by reversing the list)
        if limit is None:
            entries = await self._execute_with_retry(self.redis.lrange, history_key, 0, -1)
        else:
            # Get latest entries (from the end of the list)
            entries = await self._execute_with_retry(
                self.redis.lrange, history_key, -limit, -1
            )
        
        # Reverse to get newest first and parse JSON
        result = []
        for entry in reversed(entries):
            try:
                result.append(json.loads(entry))
            except json.JSONDecodeError:
                continue
        
        return result

    async def clear_saga_history(self, saga_id: str) -> None:
        """Clear saga execution history."""
        history_key = self._key("saga:history", saga_id)
        await self._execute_with_retry(self.redis.delete, history_key)

    async def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get background operation data by ID."""
        redis_key = self._key("operation", operation_id)
        
        data = await self._execute_with_retry(self.redis.hgetall, redis_key)
        if not data:
            return None
        
        # Convert Redis string values back to appropriate types
        result = dict(data)
        
        # Parse JSON result if present
        if result.get("result"):
            try:
                result["result"] = json.loads(result["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        
        return result

    async def set_operation(
        self, 
        operation_id: str, 
        mapping: Dict[str, Any]
    ) -> None:
        """Set background operation data."""
        redis_key = self._key("operation", operation_id)
        
        # Prepare data for Redis (serialize result as JSON)
        redis_data = mapping.copy()
        if redis_data.get("result") is not None:
            redis_data["result"] = json.dumps(redis_data["result"])
        
        await self._execute_with_retry(self.redis.hset, redis_key, mapping=redis_data)

    async def delete_operation(self, operation_id: str) -> bool:
        """Delete background operation data by ID."""
        redis_key = self._key("operation", operation_id)
        
        result = await self._execute_with_retry(self.redis.delete, redis_key)
        return result > 0

    async def list_operations_by_tenant(
        self, 
        tenant_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List background operations for a tenant."""
        # This is a simplified implementation - in production you might want
        # to use Redis secondary indexes or search modules for better performance
        pattern = self._key("operation", "*")
        
        operations = []
        cursor = 0
        
        while True:
            cursor, keys = await self._execute_with_retry(
                self.redis.scan, cursor, match=pattern, count=1000
            )
            
            if keys:
                pipe = self.redis.pipeline()
                for key in keys:
                    pipe.hgetall(key)
                
                results = await self._execute_with_retry(pipe.execute)
                
                for data in results:
                    if data and data.get("tenant_id") == tenant_id:
                        # Parse JSON result if present
                        if data.get("result"):
                            try:
                                data["result"] = json.loads(data["result"])
                            except (json.JSONDecodeError, TypeError):
                                pass
                        operations.append(dict(data))
            
            if cursor == 0:
                break
        
        # Sort by created_at (newest first)
        operations.sort(
            key=lambda x: x.get("created_at", ""), 
            reverse=True
        )
        
        # Apply pagination
        end_idx = offset + limit
        return operations[offset:end_idx]

    async def list_sagas_by_tenant(
        self, 
        tenant_id: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List saga workflows for a tenant."""
        pattern = self._key("saga", "*")
        
        sagas = []
        cursor = 0
        
        while True:
            cursor, keys = await self._execute_with_retry(
                self.redis.scan, cursor, match=pattern, count=1000
            )
            
            if keys:
                pipe = self.redis.pipeline()
                for key in keys:
                    pipe.get(key)
                
                results = await self._execute_with_retry(pipe.execute)
                
                for data in results:
                    if data:
                        try:
                            saga_data = json.loads(data)
                            if saga_data.get("tenant_id") == tenant_id:
                                sagas.append(saga_data)
                        except json.JSONDecodeError:
                            continue
            
            if cursor == 0:
                break
        
        # Sort by created_at (newest first)
        sagas.sort(
            key=lambda x: x.get("created_at", ""), 
            reverse=True
        )
        
        # Apply pagination
        end_idx = offset + limit
        return sagas[offset:end_idx]

    async def acquire_lock(
        self, 
        lock_key: str, 
        timeout_seconds: int = 30
    ) -> bool:
        """Acquire a distributed lock for saga execution."""
        redis_key = self._key("lock", lock_key)
        lock_value = f"{time.time()}"  # Use timestamp as lock value
        
        # Use SET with NX (only set if key doesn't exist) and EX (expiry)
        result = await self._execute_with_retry(
            self.redis.set, 
            redis_key, 
            lock_value, 
            nx=True, 
            ex=timeout_seconds
        )
        
        return result is True

    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock."""
        redis_key = self._key("lock", lock_key)
        
        result = await self._execute_with_retry(self.redis.delete, redis_key)
        return result > 0

    async def cleanup_expired_data(self) -> int:
        """Clean up expired data."""
        cleaned_count = 0
        
        # Clean up expired idempotency keys from index
        index_key = self._key("idempo", "index")
        now = time.time()
        
        expired_keys = await self.get_expired_idempotency_keys(now)
        
        if expired_keys:
            pipe = self.redis.pipeline()
            for key in expired_keys:
                redis_key = self._key("idempo", key)
                pipe.delete(redis_key)
                pipe.zrem(index_key, key)
                cleaned_count += 1
            
            await self._execute_with_retry(pipe.execute)
        
        # Expired locks are automatically cleaned up by Redis TTL
        
        return cleaned_count

    async def health_check(self) -> Dict[str, Any]:
        """Perform storage health check."""
        try:
            # Test basic connectivity
            pong = await self._execute_with_retry(self.redis.ping)
            
            # Get some basic info
            info = await self._execute_with_retry(self.redis.info, "server")
            
            # Count our keys
            pattern = f"{self.prefix}:*"
            cursor = 0
            key_counts = {
                "idempo": 0,
                "saga": 0,
                "operation": 0,
                "lock": 0,
            }
            
            while True:
                cursor, keys = await self._execute_with_retry(
                    self.redis.scan, cursor, match=pattern, count=1000
                )
                
                for key in keys:
                    if ":idempo:" in key:
                        key_counts["idempo"] += 1
                    elif ":saga:" in key:
                        key_counts["saga"] += 1
                    elif ":operation:" in key:
                        key_counts["operation"] += 1
                    elif ":lock:" in key:
                        key_counts["lock"] += 1
                
                if cursor == 0:
                    break
            
            return {
                "status": "healthy" if pong else "unhealthy",
                "backend": "redis",
                "server_info": {
                    "redis_version": info.get("redis_version"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                },
                "metrics": key_counts,
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "redis",
                "error": str(e),
                "metrics": {},
            }

    async def close(self) -> None:
        """Close storage connections and clean up resources."""
        if hasattr(self.redis, 'close'):
            await self.redis.close()
        
        # Close connection pool
        if hasattr(self.redis, 'connection_pool'):
            await self.redis.connection_pool.disconnect()