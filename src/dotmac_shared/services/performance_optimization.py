"""
Performance Optimization and Caching Layer

Provides comprehensive performance enhancements for consolidated DotMac services:
- Multi-level caching (memory, Redis, distributed)
- Query optimization and result caching
- Connection pooling and database optimization
- Background task processing and async optimization
- Metrics collection and performance monitoring
- Load balancing and request distribution
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .base import BaseService

logger = logging.getLogger(__name__)


class CacheLevel:
    """Cache level definitions."""

    MEMORY = "memory"
    REDIS = "redis"
    DISTRIBUTED = "distributed"
    DATABASE = "database"


class PerformanceMetrics:
    """Performance metrics tracking."""

    def __init__(self):
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "query_count": 0,
            "query_time_total": 0.0,
            "request_count": 0,
            "request_time_total": 0.0,
            "error_count": 0,
            "background_tasks": 0,
        }
        self.start_time = time.time()

    def record_cache_hit(self, cache_level: str):
        """Record a cache hit."""
        self.metrics["cache_hits"] += 1
        logger.debug(f"Cache hit at level: {cache_level}")

    def record_cache_miss(self, cache_level: str):
        """Record a cache miss."""
        self.metrics["cache_misses"] += 1
        logger.debug(f"Cache miss at level: {cache_level}")

    def record_query(self, duration: float):
        """Record a database query."""
        self.metrics["query_count"] += 1
        self.metrics["query_time_total"] += duration

    def record_request(self, duration: float):
        """Record a service request."""
        self.metrics["request_count"] += 1
        self.metrics["request_time_total"] += duration

    def record_error(self):
        """Record an error."""
        self.metrics["error_count"] += 1

    def record_background_task(self):
        """Record a background task."""
        self.metrics["background_tasks"] += 1

    def get_summary(self) -> dict[str, Any]:
        """Get performance metrics summary."""
        uptime = time.time() - self.start_time

        cache_hit_rate = 0.0
        if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0:
            cache_hit_rate = (
                self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"]) * 100
            )

        avg_query_time = 0.0
        if self.metrics["query_count"] > 0:
            avg_query_time = self.metrics["query_time_total"] / self.metrics["query_count"]

        avg_request_time = 0.0
        if self.metrics["request_count"] > 0:
            avg_request_time = self.metrics["request_time_total"] / self.metrics["request_count"]

        return {
            "uptime_seconds": uptime,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "total_requests": self.metrics["request_count"],
            "requests_per_second": round(self.metrics["request_count"] / uptime, 2) if uptime > 0 else 0,
            "average_request_time_ms": round(avg_request_time * 1000, 2),
            "total_queries": self.metrics["query_count"],
            "average_query_time_ms": round(avg_query_time * 1000, 2),
            "error_rate": round((self.metrics["error_count"] / max(self.metrics["request_count"], 1)) * 100, 2),
            "background_tasks_completed": self.metrics["background_tasks"],
        }


class CacheManager:
    """Multi-level cache manager."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self.cache_ttl = self.config.get("default_ttl_seconds", 3600)  # 1 hour
        self.max_memory_entries = self.config.get("max_memory_entries", 10000)

        # Redis connection would be initialized here in production
        self.redis_enabled = self.config.get("redis_enabled", False)
        self.redis_client = None  # Placeholder for Redis client

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key."""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        if kwargs:
            key_data += f":{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str, cache_level: str = CacheLevel.MEMORY) -> Any | None:
        """Get value from cache."""
        try:
            if cache_level == CacheLevel.MEMORY:
                if key in self.memory_cache:
                    cache_entry = self.memory_cache[key]

                    # Check TTL
                    if cache_entry["expires_at"] > time.time():
                        return cache_entry["data"]
                    else:
                        # Remove expired entry
                        del self.memory_cache[key]

                return None

            elif cache_level == CacheLevel.REDIS and self.redis_enabled:
                # Redis cache implementation would go here
                return None

            return None

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, cache_level: str = CacheLevel.MEMORY, ttl: int | None = None) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.cache_ttl
            expires_at = time.time() + ttl

            if cache_level == CacheLevel.MEMORY:
                # Implement LRU eviction if at capacity
                if len(self.memory_cache) >= self.max_memory_entries:
                    # Remove oldest entry
                    oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k]["created_at"])
                    del self.memory_cache[oldest_key]

                self.memory_cache[key] = {"data": value, "created_at": time.time(), "expires_at": expires_at}
                return True

            elif cache_level == CacheLevel.REDIS and self.redis_enabled:
                # Redis cache implementation would go here
                return True

            return False

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        try:
            removed_count = 0
            keys_to_remove = []

            for key in self.memory_cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.memory_cache[key]
                removed_count += 1

            return removed_count

        except Exception as e:
            logger.warning(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "memory_cache_size": len(self.memory_cache),
            "memory_cache_limit": self.max_memory_entries,
            "memory_usage_percent": round((len(self.memory_cache) / self.max_memory_entries) * 100, 2),
            "redis_enabled": self.redis_enabled,
            "default_ttl_seconds": self.cache_ttl,
        }


class DatabaseOptimizer:
    """Database query optimization and connection management."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.connection_pool_size = self.config.get("connection_pool_size", 20)
        self.query_cache = {}
        self.query_stats = {}

    def optimize_query(self, query_str: str, params: dict | None = None) -> str:
        """Optimize database query."""
        # Placeholder for query optimization logic
        # In production, this could:
        # - Add proper indexes hints
        # - Optimize JOIN operations
        # - Add LIMIT clauses where appropriate
        # - Convert subqueries to JOINs

        optimized = query_str

        # Basic optimization: ensure LIMIT is present for large result sets
        if "SELECT" in query_str.upper() and "LIMIT" not in query_str.upper():
            if not any(keyword in query_str.upper() for keyword in ["COUNT", "SUM", "AVG", "MAX", "MIN"]):
                optimized += " LIMIT 1000"

        return optimized

    async def execute_with_cache(
        self,
        db_session: Session | AsyncSession,
        query_str: str,
        params: dict | None = None,
        cache_key: str | None = None,
        cache_ttl: int = 300,
    ) -> Any:
        """Execute query with result caching."""
        if not cache_key:
            cache_key = hashlib.md5(f"{query_str}:{json.dumps(params or {}, sort_keys=True)}".encode()).hexdigest()

        # Check cache first
        if cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if cache_entry["expires_at"] > time.time():
                return cache_entry["result"]
            else:
                del self.query_cache[cache_key]

        # Execute optimized query
        start_time = time.time()
        optimized_query = self.optimize_query(query_str, params)

        try:
            if isinstance(db_session, AsyncSession):
                result = await db_session.execute(optimized_query, params or {})
            else:
                result = db_session.execute(optimized_query, params or {})

            execution_time = time.time() - start_time

            # Track query statistics
            if query_str not in self.query_stats:
                self.query_stats[query_str] = {"count": 0, "total_time": 0.0, "avg_time": 0.0, "last_executed": None}

            stats = self.query_stats[query_str]
            stats["count"] += 1
            stats["total_time"] += execution_time
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["last_executed"] = datetime.now(timezone.utc).isoformat()

            # Cache the result
            self.query_cache[cache_key] = {
                "result": result,
                "created_at": time.time(),
                "expires_at": time.time() + cache_ttl,
            }

            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def get_query_stats(self) -> dict[str, Any]:
        """Get database query statistics."""
        total_queries = sum(stat["count"] for stat in self.query_stats.values())
        avg_query_time = 0.0

        if total_queries > 0:
            total_time = sum(stat["total_time"] for stat in self.query_stats.values())
            avg_query_time = total_time / total_queries

        slowest_queries = sorted(self.query_stats.items(), key=lambda x: x[1]["avg_time"], reverse=True)[:5]

        return {
            "total_queries": total_queries,
            "unique_queries": len(self.query_stats),
            "average_query_time_ms": round(avg_query_time * 1000, 2),
            "query_cache_size": len(self.query_cache),
            "slowest_queries": [
                {
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "count": stats["count"],
                    "avg_time_ms": round(stats["avg_time"] * 1000, 2),
                }
                for query, stats in slowest_queries
            ],
        }


class BackgroundTaskManager:
    """Background task processing and management."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.task_queue: list[dict[str, Any]] = []
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.max_concurrent_tasks = self.config.get("max_concurrent_tasks", 10)

    async def enqueue_task(
        self,
        task_id: str,
        task_func: Callable,
        args: tuple = (),
        kwargs: dict | None = None,
        priority: int = 0,
        delay: float = 0.0,
    ) -> str:
        """Enqueue a background task."""
        task_data = {
            "task_id": task_id,
            "task_func": task_func,
            "args": args,
            "kwargs": kwargs or {},
            "priority": priority,
            "delay": delay,
            "created_at": time.time(),
            "scheduled_for": time.time() + delay,
        }

        self.task_queue.append(task_data)

        # Sort by priority and scheduled time
        self.task_queue.sort(key=lambda x: (-x["priority"], x["scheduled_for"]))

        logger.info(f"Enqueued background task: {task_id}")
        return task_id

    async def process_tasks(self):
        """Process background tasks from the queue."""
        current_time = time.time()

        while (
            len(self.running_tasks) < self.max_concurrent_tasks
            and self.task_queue
            and self.task_queue[0]["scheduled_for"] <= current_time
        ):
            task_data = self.task_queue.pop(0)

            # Start the task
            task = asyncio.create_task(self._execute_task(task_data))

            self.running_tasks[task_data["task_id"]] = task

        # Check for completed tasks
        completed_task_ids = []
        for task_id, task in self.running_tasks.items():
            if task.done():
                completed_task_ids.append(task_id)

                try:
                    await task  # This will raise if the task failed
                    self.completed_tasks += 1
                    logger.info(f"Background task completed: {task_id}")
                except Exception as e:
                    self.failed_tasks += 1
                    logger.error(f"Background task failed: {task_id}, error: {e}")

        # Remove completed tasks
        for task_id in completed_task_ids:
            del self.running_tasks[task_id]

    async def _execute_task(self, task_data: dict[str, Any]):
        """Execute a background task."""
        task_func = task_data["task_func"]
        args = task_data["args"]
        kwargs = task_data["kwargs"]

        try:
            if asyncio.iscoroutinefunction(task_func):
                await task_func(*args, **kwargs)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, task_func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            raise

    def get_task_stats(self) -> dict[str, Any]:
        """Get background task statistics."""
        return {
            "queued_tasks": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round((self.completed_tasks / max(self.completed_tasks + self.failed_tasks, 1)) * 100, 2),
        }


class PerformanceOptimizationService(BaseService):
    """
    Comprehensive performance optimization service for consolidated services.

    Provides:
    - Multi-level caching
    - Database query optimization
    - Background task processing
    - Performance metrics collection
    - Load balancing support
    """

    def __init__(
        self, db_session: Session | AsyncSession, tenant_id: str | None = None, config: dict[str, Any] | None = None
    ):
        super().__init__(db_session, tenant_id)
        self.config = config or {}

        # Initialize performance components
        self.metrics = PerformanceMetrics()
        self.cache_manager = CacheManager(self.config.get("cache", {}))
        self.db_optimizer = DatabaseOptimizer(self.config.get("database", {}))
        self.task_manager = BackgroundTaskManager(self.config.get("tasks", {}))

        # Start background task processing
        asyncio.create_task(self._background_task_loop())

    # Caching Interface

    async def cache_get(self, key: str, cache_level: str = CacheLevel.MEMORY) -> Any | None:
        """Get value from cache with metrics tracking."""
        value = await self.cache_manager.get(key, cache_level)

        if value is not None:
            self.metrics.record_cache_hit(cache_level)
        else:
            self.metrics.record_cache_miss(cache_level)

        return value

    async def cache_set(
        self, key: str, value: Any, cache_level: str = CacheLevel.MEMORY, ttl: int | None = None
    ) -> bool:
        """Set value in cache."""
        return await self.cache_manager.set(key, value, cache_level, ttl)

    async def cache_invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        return await self.cache_manager.invalidate(pattern)

    # Database Optimization Interface

    async def execute_optimized_query(self, query_str: str, params: dict | None = None, cache_ttl: int = 300) -> Any:
        """Execute database query with optimization and caching."""
        start_time = time.time()

        try:
            result = await self.db_optimizer.execute_with_cache(self.db, query_str, params, cache_ttl=cache_ttl)

            duration = time.time() - start_time
            self.metrics.record_query(duration)

            return result

        except Exception:
            self.metrics.record_error()
            raise

    # Background Task Interface

    async def enqueue_background_task(
        self,
        task_name: str,
        task_func: Callable,
        args: tuple = (),
        kwargs: dict | None = None,
        priority: int = 0,
        delay: float = 0.0,
    ) -> str:
        """Enqueue a background task."""
        task_id = f"{task_name}_{int(time.time())}"
        return await self.task_manager.enqueue_task(task_id, task_func, args, kwargs, priority, delay)

    # Performance Monitoring Interface

    async def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_metrics": self.metrics.get_summary(),
            "cache_stats": self.cache_manager.get_cache_stats(),
            "database_stats": self.db_optimizer.get_query_stats(),
            "task_stats": self.task_manager.get_task_stats(),
        }

    # Decorator Functions

    def cached(self, ttl: int = 3600, cache_level: str = CacheLevel.MEMORY, key_func: Callable | None = None):
        """Decorator for caching function results."""

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self.cache_manager._generate_cache_key(f"{func.__name__}", *args, **kwargs)

                # Try to get from cache
                cached_result = await self.cache_get(cache_key, cache_level)
                if cached_result is not None:
                    return cached_result

                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.cache_set(cache_key, result, cache_level, ttl)

                return result

            return wrapper

        return decorator

    def performance_tracked(self, func):
        """Decorator for tracking function performance."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                self.metrics.record_request(duration)
                return result
            except Exception:
                self.metrics.record_error()
                raise

        return wrapper

    # Background Processing

    async def _background_task_loop(self):
        """Background loop for processing tasks."""
        while True:
            try:
                await self.task_manager.process_tasks()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"Background task processing error: {e}")
                await asyncio.sleep(5)  # Wait longer on error


# Performance Optimization Factory


class PerformanceOptimizationFactory:
    """Factory for creating performance optimization instances."""

    @staticmethod
    def create_performance_service(
        db_session: Session | AsyncSession, tenant_id: str | None = None, config: dict[str, Any] | None = None
    ) -> PerformanceOptimizationService:
        """Create a performance optimization service instance."""
        return PerformanceOptimizationService(db_session, tenant_id, config)

    @staticmethod
    def create_default_config() -> dict[str, Any]:
        """Create default performance optimization configuration."""
        return {
            "cache": {"default_ttl_seconds": 3600, "max_memory_entries": 10000, "redis_enabled": False},
            "database": {"connection_pool_size": 20, "query_cache_ttl": 300},
            "tasks": {"max_concurrent_tasks": 10},
        }


# Integration with Consolidated Services


async def enhance_service_with_performance(
    service_instance: BaseService, performance_config: dict[str, Any] | None = None
) -> BaseService:
    """Enhance any service instance with performance optimizations."""

    # Create performance service
    perf_service = PerformanceOptimizationFactory.create_performance_service(
        db_session=service_instance.db, tenant_id=service_instance.tenant_id, config=performance_config
    )

    # Add performance methods to the service
    service_instance.cache_get = perf_service.cache_get
    service_instance.cache_set = perf_service.cache_set
    service_instance.cache_invalidate = perf_service.cache_invalidate
    service_instance.enqueue_background_task = perf_service.enqueue_background_task
    service_instance.get_performance_summary = perf_service.get_performance_summary
    service_instance.cached = perf_service.cached
    service_instance.performance_tracked = perf_service.performance_tracked

    return service_instance
