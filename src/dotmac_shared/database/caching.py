"""
Advanced database result caching and intelligent prefetching for DotMac Framework.
Provides Redis-based caching, intelligent cache warming, and prefetch strategies.
"""

import asyncio
import functools
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union
from contextlib import asynccontextmanager
from collections import defaultdict

import redis.asyncio as redis
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dotmac_shared.observability.logging import get_logger
from .session import get_read_session, get_write_session

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

# Redis connection pool
_redis_pool = None


# === REDIS CONNECTION MANAGEMENT ===

async def get_redis_pool():
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        _redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            retry_on_timeout=True,
            health_check_interval=30
        )
    return _redis_pool


async def get_redis_client():
    """Get Redis client from pool."""
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool, decode_responses=True)


# === INTELLIGENT CACHING SYSTEM ===

class SmartCache:
    """Intelligent caching system with Redis backend."""
    
    def __init__(self, prefix: str = "dotmac", default_ttl: int = 300):
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.access_patterns = defaultdict(list)  # Track access patterns for prefetching
        
    def _generate_key(self, namespace: str, identifier: str, version: str = "v1") -> str:
        """Generate cache key with namespace and versioning."""
        return f"{self.prefix}:{version}:{namespace}:{identifier}"
    
    def _hash_parameters(self, params: Dict[str, Any]) -> str:
        """Create hash from parameters for cache key."""
        return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    async def get(self, namespace: str, key: str, version: str = "v1") -> Optional[Any]:
        """Get cached value."""
        try:
            redis_client = await get_redis_client()
            cache_key = self._generate_key(namespace, key, version)
            
            # Track access for prefetching intelligence
            self.access_patterns[namespace].append({
                "key": key,
                "timestamp": datetime.utcnow(),
                "operation": "get"
            })
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached_data)
                
            logger.debug(f"Cache miss: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for {namespace}:{key}: {e}")
            return None
    
    async def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None, 
                  version: str = "v1") -> bool:
        """Set cached value."""
        try:
            redis_client = await get_redis_client()
            cache_key = self._generate_key(namespace, key, version)
            ttl = ttl or self.default_ttl
            
            cached_data = json.dumps(value, default=str)
            await redis_client.setex(cache_key, ttl, cached_data)
            
            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {namespace}:{key}: {e}")
            return False
    
    async def delete(self, namespace: str, key: str, version: str = "v1") -> bool:
        """Delete cached value."""
        try:
            redis_client = await get_redis_client()
            cache_key = self._generate_key(namespace, key, version)
            
            deleted_count = await redis_client.delete(cache_key)
            logger.debug(f"Cache delete: {cache_key} (deleted: {deleted_count})")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Cache delete error for {namespace}:{key}: {e}")
            return False
    
    async def invalidate_pattern(self, namespace: str, pattern: str = "*", 
                               version: str = "v1") -> int:
        """Invalidate cache entries matching a pattern."""
        try:
            redis_client = await get_redis_client()
            cache_pattern = self._generate_key(namespace, pattern, version)
            
            keys = await redis_client.keys(cache_pattern)
            if keys:
                deleted_count = await redis_client.delete(*keys)
                logger.info(f"Cache pattern invalidated: {cache_pattern} ({deleted_count} keys)")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache pattern invalidation error for {namespace}:{pattern}: {e}")
            return 0
    
    async def get_stats(self, namespace: str) -> Dict[str, Any]:
        """Get cache statistics for namespace."""
        try:
            redis_client = await get_redis_client()
            pattern = self._generate_key(namespace, "*", "*")
            keys = await redis_client.keys(pattern)
            
            stats = {
                "total_keys": len(keys),
                "namespace": namespace,
                "access_patterns": len(self.access_patterns.get(namespace, [])),
                "memory_usage": 0,  # Could be enhanced with Redis memory commands
                "hit_rate": 0.0  # Would need hit/miss tracking
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Cache stats error for {namespace}: {e}")
            return {"error": str(e)}


# Global cache instance
smart_cache = SmartCache()


# === CACHING DECORATORS ===

def redis_cache(namespace: str, ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Redis-based caching decorator with intelligent key generation.
    
    Args:
        namespace: Cache namespace for organization
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from args
        
    Usage:
        @redis_cache("commission_configs", ttl=600)
        async def get_commission_config(config_id: str):
            # Function implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation from function name and parameters
                params = {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                }
                cache_key = smart_cache._hash_parameters(params)
            
            # Try cache first
            cached_result = await smart_cache.get(namespace, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the result
            await smart_cache.set(namespace, cache_key, result, ttl)
            
            logger.debug(
                f"Function executed and cached: {func.__name__} ({execution_time:.3f}s)",
                extra={
                    "namespace": namespace,
                    "cache_key": cache_key[:20] + "...",
                    "execution_time": execution_time
                }
            )
            
            return result
            
        return wrapper
    return decorator


def cache_invalidator(namespace: str, pattern: str = "*"):
    """
    Decorator to invalidate cache entries after function execution.
    
    Usage:
        @cache_invalidator("commission_configs", "config_*")
        async def update_commission_config(config_id: str, data: dict):
            # Function implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache after successful execution
            invalidated_count = await smart_cache.invalidate_pattern(namespace, pattern)
            
            logger.debug(
                f"Cache invalidated after {func.__name__}: {invalidated_count} entries",
                extra={
                    "namespace": namespace,
                    "pattern": pattern,
                    "function": func.__name__
                }
            )
            
            return result
            
        return wrapper
    return decorator


# === INTELLIGENT PREFETCHING ===

class PrefetchStrategy:
    """Intelligent prefetching based on access patterns."""
    
    def __init__(self, cache_instance: SmartCache):
        self.cache = cache_instance
        self.prefetch_queue = asyncio.Queue()
        self.running = False
        
    async def start_prefetch_worker(self):
        """Start background prefetch worker."""
        if self.running:
            return
        
        self.running = True
        asyncio.create_task(self._prefetch_worker())
        logger.info("Prefetch worker started")
    
    async def stop_prefetch_worker(self):
        """Stop background prefetch worker."""
        self.running = False
        logger.info("Prefetch worker stopped")
    
    async def _prefetch_worker(self):
        """Background worker for processing prefetch queue."""
        while self.running:
            try:
                # Get prefetch task from queue
                prefetch_task = await asyncio.wait_for(
                    self.prefetch_queue.get(), timeout=1.0
                )
                
                await self._execute_prefetch(prefetch_task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Prefetch worker error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_prefetch(self, task: Dict[str, Any]):
        """Execute a prefetch task."""
        try:
            namespace = task["namespace"]
            key = task["key"]
            fetch_func = task["fetch_func"]
            params = task.get("params", {})
            
            # Check if already cached
            cached = await self.cache.get(namespace, key)
            if cached is not None:
                return
            
            # Fetch and cache
            start_time = time.time()
            result = await fetch_func(**params)
            execution_time = time.time() - start_time
            
            await self.cache.set(namespace, key, result)
            
            logger.debug(
                f"Prefetched and cached: {namespace}:{key} ({execution_time:.3f}s)",
                extra={
                    "namespace": namespace,
                    "key": key[:20] + "...",
                    "execution_time": execution_time
                }
            )
            
        except Exception as e:
            logger.error(f"Prefetch execution failed: {e}")
    
    async def schedule_prefetch(self, namespace: str, key: str, fetch_func: Callable, 
                              params: Optional[Dict[str, Any]] = None):
        """Schedule a prefetch operation."""
        task = {
            "namespace": namespace,
            "key": key,
            "fetch_func": fetch_func,
            "params": params or {}
        }
        
        try:
            await self.prefetch_queue.put(task)
            logger.debug(f"Prefetch scheduled: {namespace}:{key}")
        except Exception as e:
            logger.error(f"Failed to schedule prefetch: {e}")
    
    def analyze_access_patterns(self, namespace: str) -> Dict[str, Any]:
        """Analyze access patterns to suggest prefetch opportunities."""
        patterns = self.cache.access_patterns.get(namespace, [])
        if not patterns:
            return {"suggestions": []}
        
        # Group by key and analyze frequency
        key_access = defaultdict(list)
        for access in patterns:
            key_access[access["key"]].append(access["timestamp"])
        
        suggestions = []
        for key, timestamps in key_access.items():
            if len(timestamps) > 1:
                # Calculate average access interval
                intervals = []
                for i in range(1, len(timestamps)):
                    interval = (timestamps[i] - timestamps[i-1]).total_seconds()
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                
                if avg_interval < 3600:  # Less than 1 hour interval
                    suggestions.append({
                        "key": key,
                        "access_frequency": len(timestamps),
                        "avg_interval_seconds": avg_interval,
                        "prefetch_recommended": True
                    })
        
        return {
            "namespace": namespace,
            "total_accesses": len(patterns),
            "unique_keys": len(key_access),
            "suggestions": suggestions
        }


# Global prefetch strategy
prefetch_strategy = PrefetchStrategy(smart_cache)


# === CACHE WARMING STRATEGIES ===

async def warm_commission_config_cache():
    """Warm cache for frequently accessed commission configurations."""
    logger.info("Starting commission config cache warming")
    
    try:
        async with get_read_session() as session:
            # Load default and active configurations
            from dotmac_management.models.commission_config import CommissionConfig
            
            query = select(CommissionConfig).where(
                and_(
                    CommissionConfig.is_active == True,
                    or_(
                        CommissionConfig.is_default == True,
                        CommissionConfig.reseller_type.isnot(None)
                    )
                )
            )
            
            result = await session.execute(query)
            configs = result.scalars().all()
            
            # Cache each configuration
            for config in configs:
                cache_key = f"config_{config.id}"
                config_data = {
                    "id": str(config.id),
                    "name": config.name,
                    "rate_config": config.rate_config,
                    "is_default": config.is_default,
                    "is_active": config.is_active,
                    "commission_structure": config.commission_structure.value if config.commission_structure else None,
                    "reseller_type": config.reseller_type.value if config.reseller_type else None,
                    "territory": config.territory
                }
                
                await smart_cache.set("commission_configs", cache_key, config_data, ttl=1800)
            
            logger.info(f"Warmed cache for {len(configs)} commission configurations")
            
    except Exception as e:
        logger.error(f"Failed to warm commission config cache: {e}")


async def warm_partner_branding_cache():
    """Warm cache for partner branding configurations."""
    logger.info("Starting partner branding cache warming")
    
    try:
        async with get_read_session() as session:
            from dotmac_management.models.partner_branding import PartnerBrandConfig
            
            # Load active brand configurations
            query = select(PartnerBrandConfig).where(
                PartnerBrandConfig.is_active == True
            ).options(selectinload(PartnerBrandConfig.partner))
            
            result = await session.execute(query)
            brand_configs = result.scalars().all()
            
            # Cache each brand configuration
            for brand_config in brand_configs:
                cache_key = f"brand_{brand_config.partner_id}"
                brand_data = {
                    "id": str(brand_config.id),
                    "partner_id": str(brand_config.partner_id),
                    "brand_name": brand_config.brand_name,
                    "primary_color": brand_config.primary_color,
                    "secondary_color": brand_config.secondary_color,
                    "logo_url": brand_config.logo_url,
                    "custom_domain": brand_config.custom_domain,
                    "domain_verified": brand_config.domain_verified,
                    "generated_assets": brand_config.generated_assets,
                    "is_active": brand_config.is_active
                }
                
                await smart_cache.set("partner_branding", cache_key, brand_data, ttl=3600)
                
                # Also cache by domain if available and verified
                if brand_config.custom_domain and brand_config.domain_verified:
                    domain_key = f"domain_{brand_config.custom_domain}"
                    await smart_cache.set("partner_branding", domain_key, brand_data, ttl=3600)
            
            logger.info(f"Warmed cache for {len(brand_configs)} partner brand configurations")
            
    except Exception as e:
        logger.error(f"Failed to warm partner branding cache: {e}")


async def warm_all_caches():
    """Warm all application caches."""
    logger.info("Starting comprehensive cache warming")
    
    start_time = time.time()
    
    # Run cache warming operations concurrently
    await asyncio.gather(
        warm_commission_config_cache(),
        warm_partner_branding_cache(),
        return_exceptions=True
    )
    
    total_time = time.time() - start_time
    logger.info(f"Cache warming completed in {total_time:.2f} seconds")


# === CACHE MANAGEMENT API ===

async def get_cache_health() -> Dict[str, Any]:
    """Get overall cache health and statistics."""
    try:
        redis_client = await get_redis_client()
        
        # Redis info
        redis_info = await redis_client.info()
        
        # Cache statistics
        commission_stats = await smart_cache.get_stats("commission_configs")
        branding_stats = await smart_cache.get_stats("partner_branding")
        
        health = {
            "healthy": True,
            "redis_connected": True,
            "redis_memory_used": redis_info.get("used_memory_human", "N/A"),
            "redis_connected_clients": redis_info.get("connected_clients", 0),
            "cache_stats": {
                "commission_configs": commission_stats,
                "partner_branding": branding_stats
            },
            "prefetch_queue_size": prefetch_strategy.prefetch_queue.qsize(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return health
        
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def clear_all_caches():
    """Clear all application caches."""
    try:
        redis_client = await get_redis_client()
        
        # Clear by pattern
        patterns = ["dotmac:*"]
        total_deleted = 0
        
        for pattern in patterns:
            keys = await redis_client.keys(pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} cache entries")
        return total_deleted
        
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        return 0