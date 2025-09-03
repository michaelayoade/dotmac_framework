"""
Redis-based caching implementation with smart features.

Provides intelligent caching with pattern invalidation, statistics,
health monitoring, and JSON serialization with proper error handling.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Pattern
from dataclasses import dataclass, asdict
import re

try:
    import redis
    from redis import Redis
    from redis.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None
    ConnectionPool = None

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Raised when cache operations fail."""
    pass


@dataclass
class CacheStats:
    """Cache statistics and performance metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_operations: int = 0
    hit_rate: float = 0.0
    error_rate: float = 0.0
    average_response_time: float = 0.0
    last_reset: datetime = None
    
    def __post_init__(self):
        if self.last_reset is None:
            self.last_reset = datetime.utcnow()
    
    def calculate_rates(self) -> None:
        """Calculate hit and error rates."""
        if self.total_operations > 0:
            self.hit_rate = self.hits / self.total_operations
            self.error_rate = self.errors / self.total_operations


class RedisManager:
    """
    Manages Redis connection pool and client instances.
    
    Provides centralized Redis connection management with
    health checks and failover capabilities.
    """
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._config: Dict[str, Any] = {}
    
    def configure(
        self,
        redis_url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
        **kwargs: Any,
    ) -> None:
        """
        Configure Redis connection parameters.
        
        Args:
            redis_url: Redis URL (takes precedence over individual params)
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            max_connections: Maximum connection pool size
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Retry on timeout errors
            health_check_interval: Health check interval in seconds
            **kwargs: Additional Redis configuration
        """
        if not REDIS_AVAILABLE:
            raise CacheError(
                "Redis not available. Install with: pip install dotmac-database[redis]"
            )
        
        # Use environment variables if not provided
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            # Parse Redis URL
            self._config = {
                "connection_pool": redis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=max_connections,
                    socket_timeout=socket_timeout,
                    socket_connect_timeout=socket_connect_timeout,
                    retry_on_timeout=retry_on_timeout,
                    health_check_interval=health_check_interval,
                    **kwargs
                )
            }
        else:
            # Build from individual parameters
            self._config = {
                "host": host,
                "port": port,
                "db": db,
                "password": password,
                "socket_timeout": socket_timeout,
                "socket_connect_timeout": socket_connect_timeout,
                "retry_on_timeout": retry_on_timeout,
                "health_check_interval": health_check_interval,
                **kwargs
            }
            
            # Create connection pool
            self._pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                retry_on_timeout=retry_on_timeout,
                health_check_interval=health_check_interval,
                **kwargs
            )
            
            self._config["connection_pool"] = self._pool
    
    def get_pool(self) -> ConnectionPool:
        """Get Redis connection pool."""
        if not REDIS_AVAILABLE:
            raise CacheError("Redis not available")
        
        if self._pool is None:
            if "connection_pool" in self._config:
                self._pool = self._config["connection_pool"]
            else:
                raise CacheError("Redis not configured. Call configure() first.")
        
        return self._pool
    
    def get_client(self) -> Redis:
        """Get Redis client instance."""
        if not REDIS_AVAILABLE:
            raise CacheError("Redis not available")
        
        if self._client is None:
            if "connection_pool" in self._config:
                self._client = redis.Redis(connection_pool=self._config["connection_pool"])
            else:
                self._client = redis.Redis(**self._config)
        
        return self._client
    
    def health_check(self) -> bool:
        """
        Perform Redis health check.
        
        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            client = self.get_client()
            response = client.ping()
            return response is True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    def reset(self) -> None:
        """Reset Redis manager state."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        
        self._client = None
        self._pool = None
        self._config.clear()


# Global Redis manager instance
_redis_manager = RedisManager()


def configure_redis(**kwargs: Any) -> None:
    """Configure global Redis connection."""
    _redis_manager.configure(**kwargs)


def get_redis_pool() -> ConnectionPool:
    """Get Redis connection pool."""
    return _redis_manager.get_pool()


def get_redis_client() -> Redis:
    """Get Redis client instance."""
    return _redis_manager.get_client()


class SmartCache:
    """
    Intelligent Redis-based cache with advanced features.
    
    Features:
    - Namespace isolation
    - TTL management
    - Pattern-based invalidation
    - Statistics tracking
    - JSON serialization with fallback
    - Compression for large values
    - Batch operations
    """
    
    def __init__(
        self,
        namespace: str,
        default_ttl: int = 3600,
        redis_client: Optional[Redis] = None,
        key_prefix: str = "dotmac:",
        enable_compression: bool = False,
        compression_threshold: int = 1024,
        track_stats: bool = True,
    ):
        """
        Initialize SmartCache.
        
        Args:
            namespace: Cache namespace for key isolation
            default_ttl: Default TTL in seconds
            redis_client: Custom Redis client (uses global if None)
            key_prefix: Global key prefix
            enable_compression: Enable compression for large values
            compression_threshold: Compress values larger than this size
            track_stats: Enable statistics tracking
        """
        if not REDIS_AVAILABLE:
            raise CacheError(
                "Redis not available. Install with: pip install dotmac-database[redis]"
            )
        
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold
        self.track_stats = track_stats
        
        # Redis client
        self._redis = redis_client or get_redis_client()
        
        # Statistics
        self._stats = CacheStats() if track_stats else None
        
        # JSON encoder for consistent serialization
        self._json_kwargs = {
            "ensure_ascii": False,
            "sort_keys": True,
            "separators": (',', ':'),
        }
    
    def _build_key(self, key: str, subkey: Optional[str] = None) -> str:
        """Build full cache key with namespace and prefix."""
        parts = [self.key_prefix, self.namespace]
        if isinstance(key, (list, tuple)):
            parts.extend(str(k) for k in key)
        else:
            parts.append(str(key))
        
        if subkey:
            parts.append(str(subkey))
        
        return ":".join(parts)
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            json_str = json.dumps(value, **self._json_kwargs)
            data = json_str.encode('utf-8')
            
            # Compress if enabled and threshold exceeded
            if (self.enable_compression and 
                len(data) > self.compression_threshold):
                try:
                    import zlib
                    compressed = zlib.compress(data)
                    # Only use compression if it actually reduces size
                    if len(compressed) < len(data):
                        return b'ZLIB:' + compressed
                except ImportError:
                    pass  # Compression not available
            
            return data
            
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize value: {e}")
            # Fallback: store as string
            return str(value).encode('utf-8')
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Check for compression marker
            if data.startswith(b'ZLIB:'):
                try:
                    import zlib
                    data = zlib.decompress(data[5:])  # Remove 'ZLIB:' prefix
                except ImportError:
                    logger.error("Cannot decompress: zlib not available")
                    raise CacheError("Compressed data found but zlib not available")
            
            # Deserialize JSON
            json_str = data.decode('utf-8')
            return json.loads(json_str)
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to deserialize value: {e}")
            # Fallback: return as string
            return data.decode('utf-8', errors='replace')
    
    def _update_stats(self, operation: str, success: bool = True) -> None:
        """Update cache statistics."""
        if not self._stats:
            return
        
        if success:
            if operation == 'get':
                self._stats.hits += 1
            elif operation == 'miss':
                self._stats.misses += 1
            elif operation == 'set':
                self._stats.sets += 1
            elif operation == 'delete':
                self._stats.deletes += 1
        else:
            self._stats.errors += 1
        
        self._stats.total_operations += 1
        self._stats.calculate_rates()
    
    async def get(self, key: str, subkey: Optional[str] = None, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Primary key
            subkey: Optional subkey
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        cache_key = self._build_key(key, subkey)
        
        try:
            data = self._redis.get(cache_key)
            if data is not None:
                value = self._deserialize_value(data)
                self._update_stats('get', True)
                logger.debug(f"Cache hit: {cache_key}")
                return value
            else:
                self._update_stats('miss', True)
                logger.debug(f"Cache miss: {cache_key}")
                return default
                
        except Exception as e:
            self._update_stats('get', False)
            logger.error(f"Cache get error for {cache_key}: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        subkey: Optional[str] = None,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Primary key
            value: Value to cache
            subkey: Optional subkey
            ttl: TTL in seconds (uses default if None)
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            True if value was set
        """
        cache_key = self._build_key(key, subkey)
        ttl = ttl or self.default_ttl
        
        try:
            data = self._serialize_value(value)
            
            # Set with appropriate flags
            result = self._redis.set(
                cache_key,
                data,
                ex=ttl,
                nx=nx,
                xx=xx
            )
            
            success = result is True
            self._update_stats('set', success)
            
            if success:
                logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            
            return success
            
        except Exception as e:
            self._update_stats('set', False)
            logger.error(f"Cache set error for {cache_key}: {e}")
            return False
    
    async def delete(self, key: str, subkey: Optional[str] = None) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Primary key
            subkey: Optional subkey
            
        Returns:
            True if key was deleted
        """
        cache_key = self._build_key(key, subkey)
        
        try:
            result = self._redis.delete(cache_key)
            success = result > 0
            self._update_stats('delete', success)
            
            if success:
                logger.debug(f"Cache delete: {cache_key}")
            
            return success
            
        except Exception as e:
            self._update_stats('delete', False)
            logger.error(f"Cache delete error for {cache_key}: {e}")
            return False
    
    async def exists(self, key: str, subkey: Optional[str] = None) -> bool:
        """Check if key exists in cache."""
        cache_key = self._build_key(key, subkey)
        
        try:
            result = self._redis.exists(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists error for {cache_key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int, subkey: Optional[str] = None) -> bool:
        """Set TTL on existing key."""
        cache_key = self._build_key(key, subkey)
        
        try:
            result = self._redis.expire(cache_key, ttl)
            return result
        except Exception as e:
            logger.error(f"Cache expire error for {cache_key}: {e}")
            return False
    
    async def ttl(self, key: str, subkey: Optional[str] = None) -> int:
        """Get TTL of key (-1 if no expiry, -2 if not exists)."""
        cache_key = self._build_key(key, subkey)
        
        try:
            return self._redis.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for {cache_key}: {e}")
            return -2
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Pattern to match (supports * and ? wildcards)
            
        Returns:
            Number of keys deleted
        """
        cache_pattern = self._build_key(pattern)
        
        try:
            # Get all matching keys
            keys = self._redis.keys(cache_pattern)
            
            if keys:
                result = self._redis.delete(*keys)
                logger.info(f"Invalidated {result} keys matching pattern: {cache_pattern}")
                return result
            
            return 0
            
        except Exception as e:
            logger.error(f"Pattern invalidation error for {cache_pattern}: {e}")
            return 0
    
    async def clear_namespace(self) -> int:
        """Clear all keys in this namespace."""
        return await self.invalidate_pattern("*")
    
    async def get_stats(self) -> Optional[CacheStats]:
        """Get cache statistics."""
        return self._stats
    
    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        if self._stats:
            self._stats = CacheStats()
    
    async def multi_get(self, keys: List[str], subkeys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get multiple values in a single operation.
        
        Args:
            keys: List of primary keys
            subkeys: Optional list of subkeys (must match keys length)
            
        Returns:
            Dictionary of key -> value pairs
        """
        if subkeys and len(subkeys) != len(keys):
            raise ValueError("subkeys length must match keys length")
        
        cache_keys = []
        key_mapping = {}
        
        for i, key in enumerate(keys):
            subkey = subkeys[i] if subkeys else None
            cache_key = self._build_key(key, subkey)
            cache_keys.append(cache_key)
            key_mapping[cache_key] = key
        
        try:
            values = self._redis.mget(cache_keys)
            result = {}
            
            for cache_key, data in zip(cache_keys, values):
                original_key = key_mapping[cache_key]
                if data is not None:
                    try:
                        result[original_key] = self._deserialize_value(data)
                        self._update_stats('get', True)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize {cache_key}: {e}")
                        self._update_stats('get', False)
                else:
                    self._update_stats('miss', True)
            
            return result
            
        except Exception as e:
            logger.error(f"Multi-get error: {e}")
            return {}
    
    async def multi_set(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        subkey_map: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Set multiple values in a single operation.
        
        Args:
            items: Dictionary of key -> value pairs
            ttl: TTL in seconds
            subkey_map: Optional mapping of key -> subkey
            
        Returns:
            Number of items successfully set
        """
        ttl = ttl or self.default_ttl
        pipeline = self._redis.pipeline()
        
        try:
            for key, value in items.items():
                subkey = subkey_map.get(key) if subkey_map else None
                cache_key = self._build_key(key, subkey)
                data = self._serialize_value(value)
                pipeline.setex(cache_key, ttl, data)
            
            results = pipeline.execute()
            success_count = sum(1 for r in results if r is True)
            
            self._update_stats('set', True)
            logger.debug(f"Multi-set: {success_count}/{len(items)} successful")
            
            return success_count
            
        except Exception as e:
            logger.error(f"Multi-set error: {e}")
            self._update_stats('set', False)
            return 0