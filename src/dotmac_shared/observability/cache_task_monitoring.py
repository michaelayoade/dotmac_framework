"""
Comprehensive cache and task processing monitoring for DotMac services.
Provides detailed monitoring of cache performance and task queue processing.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps
import json

from prometheus_client import Counter, Histogram, Gauge, Info
from opentelemetry import trace

from .logging import get_logger, performance_logger
from .otel import get_meter, get_tracer

logger = get_logger("dotmac.cache_task_monitoring")

# Cache Prometheus metrics
CACHE_HITS = Counter(
    'dotmac_cache_hits_total',
    'Total cache hits',
    ['cache_backend', 'cache_key_type', 'tenant_id']
)

CACHE_MISSES = Counter(
    'dotmac_cache_misses_total',
    'Total cache misses',
    ['cache_backend', 'cache_key_type', 'tenant_id']
)

CACHE_OPERATIONS = Counter(
    'dotmac_cache_operations_total',
    'Total cache operations',
    ['cache_backend', 'operation', 'status']
)

CACHE_OPERATION_DURATION = Histogram(
    'dotmac_cache_operation_duration_seconds',
    'Cache operation duration',
    ['cache_backend', 'operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

CACHE_HIT_RATIO = Gauge(
    'dotmac_cache_hit_ratio',
    'Cache hit ratio',
    ['cache_backend', 'cache_key_type']
)

CACHE_SIZE = Gauge(
    'dotmac_cache_size_bytes',
    'Current cache size in bytes',
    ['cache_backend']
)

CACHE_EVICTIONS = Counter(
    'dotmac_cache_evictions_total',
    'Total cache evictions',
    ['cache_backend', 'eviction_reason']
)

CACHE_MEMORY_USAGE = Gauge(
    'dotmac_cache_memory_usage_percent',
    'Cache memory usage percentage',
    ['cache_backend']
)

# Task Processing Prometheus metrics
TASK_QUEUE_SIZE = Gauge(
    'dotmac_task_queue_size',
    'Current task queue size',
    ['queue_name', 'priority']
)

TASK_PROCESSING_DURATION = Histogram(
    'dotmac_task_processing_duration_seconds',
    'Task processing duration',
    ['task_type', 'queue_name', 'status'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 900.0)
)

TASK_EXECUTION_COUNT = Counter(
    'dotmac_task_executions_total',
    'Total task executions',
    ['task_type', 'queue_name', 'status']
)

TASK_FAILURES = Counter(
    'dotmac_task_failures_total',
    'Total task failures',
    ['task_type', 'queue_name', 'error_type']
)

TASK_RETRIES = Counter(
    'dotmac_task_retries_total',
    'Total task retries',
    ['task_type', 'queue_name', 'retry_count']
)

TASK_WORKER_UTILIZATION = Gauge(
    'dotmac_task_worker_utilization_percent',
    'Task worker utilization percentage',
    ['queue_name', 'worker_id']
)

TASK_QUEUE_WAIT_TIME = Histogram(
    'dotmac_task_queue_wait_time_seconds',
    'Time tasks spend waiting in queue',
    ['queue_name', 'priority'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 900.0, 1800.0)
)

TASK_PROCESSING_RATE = Gauge(
    'dotmac_task_processing_rate_per_second',
    'Task processing rate per second',
    ['queue_name', 'task_type']
)

@dataclass
class CacheStats:
    """Cache statistics container."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    memory_usage_percent: float = 0.0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate hit ratio."""
        total_requests = self.hits + self.misses
        return self.hits / total_requests if total_requests > 0 else 0.0
    
    @property
    def miss_ratio(self) -> float:
        """Calculate miss ratio."""
        return 1.0 - self.hit_ratio

@dataclass
class TaskStats:
    """Task processing statistics."""
    queued: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    retried: int = 0
    avg_wait_time_seconds: float = 0.0
    avg_processing_time_seconds: float = 0.0
    processing_rate_per_second: float = 0.0

@dataclass
class CacheKeyPattern:
    """Cache key pattern for monitoring."""
    pattern: str
    key_type: str
    ttl_seconds: Optional[int] = None
    expected_hit_ratio: float = 0.8
    
    def matches(self, key: str) -> bool:
        """Check if key matches pattern."""
        import re
        return bool(re.match(self.pattern, key))

class CacheMonitor:
    """
    Comprehensive cache monitoring system.
    
    Features:
    - Multi-backend cache monitoring (Redis, Memcached, etc.)
    - Hit/miss ratio tracking by key patterns
    - Performance metrics (latency, throughput)
    - Memory usage and eviction tracking
    - Cache warming and preloading monitoring
    - Tenant-aware cache analytics
    """
    
    def __init__(self):
        self.cache_stats: Dict[str, CacheStats] = defaultdict(CacheStats)
        self.cache_patterns: List[CacheKeyPattern] = []
        self.recent_operations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Initialize default cache key patterns
        self._initialize_cache_patterns()
        
        # Start monitoring tasks
        asyncio.create_task(self._cache_metrics_collector())
        asyncio.create_task(self._cache_performance_analyzer())
    
    def _initialize_cache_patterns(self):
        """Initialize common cache key patterns."""
        patterns = [
            CacheKeyPattern(r"tenant:.*:config", "tenant_config", 3600, 0.95),
            CacheKeyPattern(r"partner:.*:branding", "partner_branding", 1800, 0.90),
            CacheKeyPattern(r"commission:.*:config", "commission_config", 3600, 0.85),
            CacheKeyPattern(r"user:.*:session", "user_session", 1800, 0.80),
            CacheKeyPattern(r"api:.*:rate_limit", "rate_limit", 60, 0.70),
            CacheKeyPattern(r"db:.*:query", "query_cache", 300, 0.60),
            CacheKeyPattern(r"template:.*", "template_cache", 7200, 0.95),
        ]
        
        self.cache_patterns.extend(patterns)
    
    def get_key_pattern(self, cache_key: str) -> Optional[CacheKeyPattern]:
        """Get matching cache key pattern."""
        for pattern in self.cache_patterns:
            if pattern.matches(cache_key):
                return pattern
        return None
    
    async def _cache_metrics_collector(self):
        """Background task to collect cache metrics."""
        while True:
            try:
                await asyncio.sleep(30)  # Collect every 30 seconds
                
                # This would integrate with actual cache backends
                # For now, we'll simulate metric collection
                
                for backend in ["redis", "memcached", "local"]:
                    stats = await self._collect_backend_stats(backend)
                    self.cache_stats[backend] = stats
                    
                    # Update Prometheus metrics
                    CACHE_HIT_RATIO.labels(cache_backend=backend, cache_key_type="all").set(stats.hit_ratio)
                    CACHE_SIZE.labels(cache_backend=backend).set(stats.total_size_bytes)
                    CACHE_MEMORY_USAGE.labels(cache_backend=backend).set(stats.memory_usage_percent)
                
            except Exception as e:
                logger.error("Error collecting cache metrics", error=str(e))
    
    async def _cache_performance_analyzer(self):
        """Analyze cache performance and detect issues."""
        while True:
            try:
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
                for backend, stats in self.cache_stats.items():
                    # Analyze hit ratios
                    if stats.hit_ratio < 0.5:  # Low hit ratio threshold
                        performance_logger.warning(
                            f"Low cache hit ratio detected: {backend}",
                            backend=backend,
                            hit_ratio=stats.hit_ratio,
                            hits=stats.hits,
                            misses=stats.misses
                        )
                    
                    # Analyze eviction rates
                    if stats.evictions > 100:  # High eviction threshold
                        performance_logger.warning(
                            f"High cache eviction rate: {backend}",
                            backend=backend,
                            evictions=stats.evictions,
                            memory_usage=stats.memory_usage_percent
                        )
                
            except Exception as e:
                logger.error("Error in cache performance analysis", error=str(e))
    
    async def _collect_backend_stats(self, backend: str) -> CacheStats:
        """Collect statistics from cache backend."""
        # This would implement actual backend-specific stat collection
        # For now, simulate the stats
        import random
        
        return CacheStats(
            hits=random.randint(1000, 10000),
            misses=random.randint(100, 1000),
            sets=random.randint(500, 2000),
            deletes=random.randint(10, 100),
            evictions=random.randint(0, 50),
            total_size_bytes=random.randint(1024*1024, 1024*1024*100),  # 1MB to 100MB
            memory_usage_percent=random.uniform(40, 90)
        )


class TaskMonitor:
    """
    Comprehensive task processing monitoring system.
    
    Features:
    - Multi-queue monitoring with priority tracking
    - Processing time and wait time analytics
    - Worker utilization monitoring
    - Task failure analysis and retry tracking
    - Tenant-aware task analytics
    - Processing rate and throughput metrics
    """
    
    def __init__(self):
        self.task_stats: Dict[str, TaskStats] = defaultdict(TaskStats)
        self.queue_depths: Dict[str, int] = defaultdict(int)
        self.worker_status: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.processing_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Start monitoring tasks
        asyncio.create_task(self._task_metrics_collector())
        asyncio.create_task(self._worker_utilization_monitor())
        asyncio.create_task(self._task_performance_analyzer())
    
    async def _task_metrics_collector(self):
        """Background task to collect task processing metrics."""
        while True:
            try:
                await asyncio.sleep(30)  # Collect every 30 seconds
                
                # This would integrate with actual task queue systems
                # For now, simulate metric collection
                
                queues = ["default", "priority", "background", "commission", "tenant_provisioning"]
                
                for queue_name in queues:
                    stats = await self._collect_queue_stats(queue_name)
                    self.task_stats[queue_name] = stats
                    
                    # Update Prometheus metrics
                    TASK_QUEUE_SIZE.labels(queue_name=queue_name, priority="normal").set(stats.queued)
                    TASK_PROCESSING_RATE.labels(queue_name=queue_name, task_type="all").set(stats.processing_rate_per_second)
                    
                    # Update queue depth
                    self.queue_depths[queue_name] = stats.queued + stats.processing
                
            except Exception as e:
                logger.error("Error collecting task metrics", error=str(e))
    
    async def _worker_utilization_monitor(self):
        """Monitor task worker utilization."""
        while True:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                
                # This would integrate with actual worker systems
                # For now, simulate worker monitoring
                
                for queue_name in self.task_stats.keys():
                    for worker_id in range(1, 5):  # Simulate 4 workers per queue
                        utilization = await self._calculate_worker_utilization(queue_name, f"worker_{worker_id}")
                        
                        TASK_WORKER_UTILIZATION.labels(
                            queue_name=queue_name,
                            worker_id=f"worker_{worker_id}"
                        ).set(utilization)
                
            except Exception as e:
                logger.error("Error monitoring worker utilization", error=str(e))
    
    async def _task_performance_analyzer(self):
        """Analyze task performance and detect issues."""
        while True:
            try:
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
                for queue_name, stats in self.task_stats.items():
                    # Analyze queue depth
                    if stats.queued > 1000:  # High queue depth threshold
                        performance_logger.warning(
                            f"High task queue depth: {queue_name}",
                            queue_name=queue_name,
                            queued_tasks=stats.queued,
                            processing_tasks=stats.processing
                        )
                    
                    # Analyze processing times
                    if stats.avg_processing_time_seconds > 300:  # 5 minute threshold
                        performance_logger.warning(
                            f"High average task processing time: {queue_name}",
                            queue_name=queue_name,
                            avg_processing_time=stats.avg_processing_time_seconds
                        )
                    
                    # Analyze failure rates
                    if stats.failed > 0 and stats.completed > 0:
                        failure_rate = stats.failed / (stats.completed + stats.failed) * 100
                        if failure_rate > 10:  # 10% failure rate threshold
                            performance_logger.warning(
                                f"High task failure rate: {queue_name}",
                                queue_name=queue_name,
                                failure_rate=failure_rate,
                                failed_tasks=stats.failed,
                                completed_tasks=stats.completed
                            )
                
            except Exception as e:
                logger.error("Error in task performance analysis", error=str(e))
    
    async def _collect_queue_stats(self, queue_name: str) -> TaskStats:
        """Collect statistics for a task queue."""
        # This would implement actual queue stat collection
        # For now, simulate the stats
        import random
        
        return TaskStats(
            queued=random.randint(0, 500),
            processing=random.randint(0, 20),
            completed=random.randint(100, 1000),
            failed=random.randint(0, 50),
            retried=random.randint(0, 20),
            avg_wait_time_seconds=random.uniform(1, 30),
            avg_processing_time_seconds=random.uniform(5, 120),
            processing_rate_per_second=random.uniform(0.5, 10.0)
        )
    
    async def _calculate_worker_utilization(self, queue_name: str, worker_id: str) -> float:
        """Calculate worker utilization percentage."""
        # This would implement actual worker utilization calculation
        # For now, simulate the calculation
        import random
        return random.uniform(20, 95)


def monitored_cache_operation(
    backend: str,
    operation: str,
    cache_key: str,
    tenant_id: Optional[str] = None
):
    """
    Decorator to monitor cache operations.
    
    Args:
        backend: Cache backend name (e.g., 'redis', 'memcached')
        operation: Operation type (e.g., 'get', 'set', 'delete')
        cache_key: Cache key being operated on
        tenant_id: Optional tenant ID for tenant-aware metrics
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            # Get cache key pattern
            pattern = cache_monitor.get_key_pattern(cache_key)
            cache_key_type = pattern.key_type if pattern else "unknown"
            
            # Start tracing
            tracer = get_tracer("dotmac-cache")
            with tracer.start_as_current_span(f"cache.{operation}") as span:
                span.set_attribute("cache.backend", backend)
                span.set_attribute("cache.operation", operation)
                span.set_attribute("cache.key_type", cache_key_type)
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                
                try:
                    result = await func(*args, **kwargs)
                    status = "success"
                    
                    # Determine if it was a hit or miss for get operations
                    if operation == "get":
                        is_hit = result is not None
                        if is_hit:
                            CACHE_HITS.labels(
                                cache_backend=backend,
                                cache_key_type=cache_key_type,
                                tenant_id=tenant_id or "unknown"
                            ).inc()
                        else:
                            CACHE_MISSES.labels(
                                cache_backend=backend,
                                cache_key_type=cache_key_type,
                                tenant_id=tenant_id or "unknown"
                            ).inc()
                        
                        span.set_attribute("cache.hit", is_hit)
                    
                    return result
                    
                except Exception as e:
                    status = "error"
                    span.record_exception(e)
                    span.set_attribute("cache.error", str(e))
                    raise
                    
                finally:
                    duration = time.perf_counter() - start_time
                    
                    # Record metrics
                    CACHE_OPERATIONS.labels(
                        cache_backend=backend,
                        operation=operation,
                        status=status
                    ).inc()
                    
                    CACHE_OPERATION_DURATION.labels(
                        cache_backend=backend,
                        operation=operation
                    ).observe(duration)
                    
                    span.set_attribute("cache.duration_ms", duration * 1000)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            pattern = cache_monitor.get_key_pattern(cache_key)
            cache_key_type = pattern.key_type if pattern else "unknown"
            
            tracer = get_tracer("dotmac-cache")
            with tracer.start_as_current_span(f"cache.{operation}") as span:
                span.set_attribute("cache.backend", backend)
                span.set_attribute("cache.operation", operation)
                span.set_attribute("cache.key_type", cache_key_type)
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                
                try:
                    result = func(*args, **kwargs)
                    status = "success"
                    
                    if operation == "get":
                        is_hit = result is not None
                        if is_hit:
                            CACHE_HITS.labels(
                                cache_backend=backend,
                                cache_key_type=cache_key_type,
                                tenant_id=tenant_id or "unknown"
                            ).inc()
                        else:
                            CACHE_MISSES.labels(
                                cache_backend=backend,
                                cache_key_type=cache_key_type,
                                tenant_id=tenant_id or "unknown"
                            ).inc()
                        
                        span.set_attribute("cache.hit", is_hit)
                    
                    return result
                    
                except Exception as e:
                    status = "error"
                    span.record_exception(e)
                    raise
                    
                finally:
                    duration = time.perf_counter() - start_time
                    
                    CACHE_OPERATIONS.labels(
                        cache_backend=backend,
                        operation=operation,
                        status=status
                    ).inc()
                    
                    CACHE_OPERATION_DURATION.labels(
                        cache_backend=backend,
                        operation=operation
                    ).observe(duration)
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def monitored_task_processing(
    task_type: str,
    queue_name: str,
    tenant_id: Optional[str] = None
):
    """
    Decorator to monitor task processing.
    
    Args:
        task_type: Type of task being processed
        queue_name: Name of the task queue
        tenant_id: Optional tenant ID for tenant-aware metrics
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            tracer = get_tracer("dotmac-tasks")
            with tracer.start_as_current_span(f"task.{task_type}") as span:
                span.set_attribute("task.type", task_type)
                span.set_attribute("task.queue", queue_name)
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                
                try:
                    result = await func(*args, **kwargs)
                    status = "success"
                    
                    span.set_attribute("task.success", True)
                    return result
                    
                except Exception as e:
                    status = "failure"
                    error_type = type(e).__name__
                    
                    span.record_exception(e)
                    span.set_attribute("task.success", False)
                    span.set_attribute("task.error_type", error_type)
                    
                    # Record failure metrics
                    TASK_FAILURES.labels(
                        task_type=task_type,
                        queue_name=queue_name,
                        error_type=error_type
                    ).inc()
                    
                    raise
                    
                finally:
                    duration = time.perf_counter() - start_time
                    
                    # Record execution metrics
                    TASK_EXECUTION_COUNT.labels(
                        task_type=task_type,
                        queue_name=queue_name,
                        status=status
                    ).inc()
                    
                    TASK_PROCESSING_DURATION.labels(
                        task_type=task_type,
                        queue_name=queue_name,
                        status=status
                    ).observe(duration)
                    
                    span.set_attribute("task.duration_ms", duration * 1000)
                    
                    performance_logger.info(
                        f"Task processed: {task_type}",
                        task_type=task_type,
                        queue_name=queue_name,
                        duration_ms=duration * 1000,
                        status=status,
                        tenant_id=tenant_id
                    )
        
        return async_wrapper
    
    return decorator


# Global monitoring instances
cache_monitor = CacheMonitor()
task_monitor = TaskMonitor()

# Convenience functions
def record_cache_hit(backend: str, cache_key: str, tenant_id: Optional[str] = None):
    """Record cache hit."""
    pattern = cache_monitor.get_key_pattern(cache_key)
    cache_key_type = pattern.key_type if pattern else "unknown"
    
    CACHE_HITS.labels(
        cache_backend=backend,
        cache_key_type=cache_key_type,
        tenant_id=tenant_id or "unknown"
    ).inc()

def record_cache_miss(backend: str, cache_key: str, tenant_id: Optional[str] = None):
    """Record cache miss."""
    pattern = cache_monitor.get_key_pattern(cache_key)
    cache_key_type = pattern.key_type if pattern else "unknown"
    
    CACHE_MISSES.labels(
        cache_backend=backend,
        cache_key_type=cache_key_type,
        tenant_id=tenant_id or "unknown"
    ).inc()

def record_task_queue_size(queue_name: str, size: int, priority: str = "normal"):
    """Record current task queue size."""
    TASK_QUEUE_SIZE.labels(queue_name=queue_name, priority=priority).set(size)

def record_task_wait_time(queue_name: str, wait_time_seconds: float, priority: str = "normal"):
    """Record task queue wait time."""
    TASK_QUEUE_WAIT_TIME.labels(queue_name=queue_name, priority=priority).observe(wait_time_seconds)

def get_cache_stats(backend: str = None) -> Dict[str, CacheStats]:
    """Get current cache statistics."""
    if backend:
        return {backend: cache_monitor.cache_stats.get(backend, CacheStats())}
    return dict(cache_monitor.cache_stats)

def get_task_stats(queue_name: str = None) -> Dict[str, TaskStats]:
    """Get current task statistics."""
    if queue_name:
        return {queue_name: task_monitor.task_stats.get(queue_name, TaskStats())}
    return dict(task_monitor.task_stats)