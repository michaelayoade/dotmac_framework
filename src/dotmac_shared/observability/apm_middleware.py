"""
Enhanced APM middleware with Prometheus metrics and comprehensive performance monitoring.
Builds on existing observability infrastructure with additional Prometheus/Grafana integration.
"""

import time
import psutil
import gc
from typing import Optional, Dict, Any, Callable
from collections import defaultdict, deque
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import trace, baggage
from prometheus_client import Counter, Histogram, Gauge, Info

from .otel import get_tracer, get_meter
from .logging import get_logger, business_logger, performance_logger

logger = get_logger("dotmac.apm")

# Prometheus metrics for enhanced APM
REQUEST_COUNT = Counter(
    'dotmac_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'tenant_id']
)

REQUEST_DURATION = Histogram(
    'dotmac_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'tenant_id'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

ACTIVE_REQUESTS = Gauge(
    'dotmac_http_requests_active',
    'Currently active HTTP requests',
    ['method', 'endpoint']
)

MEMORY_USAGE = Gauge(
    'dotmac_memory_usage_bytes',
    'Current memory usage in bytes',
    ['type']
)

CPU_USAGE = Gauge(
    'dotmac_cpu_usage_percent',
    'Current CPU usage percentage'
)

THREAD_COUNT = Gauge(
    'dotmac_thread_count',
    'Current number of threads'
)

GC_COLLECTIONS = Counter(
    'dotmac_gc_collections_total',
    'Total garbage collection count',
    ['generation']
)

ERROR_RATE = Gauge(
    'dotmac_error_rate',
    'Current error rate percentage',
    ['endpoint', 'tenant_id']
)

RESPONSE_SIZE = Histogram(
    'dotmac_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000)
)

REQUEST_SIZE = Histogram(
    'dotmac_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000)
)

# Business metrics
TENANT_ACTIVITY = Counter(
    'dotmac_tenant_activity_total',
    'Total tenant activity events',
    ['tenant_id', 'activity_type']
)

API_RATE_LIMITS = Counter(
    'dotmac_api_rate_limit_hits_total',
    'API rate limit violations',
    ['tenant_id', 'endpoint', 'limit_type']
)

DATABASE_CONNECTIONS = Gauge(
    'dotmac_database_connections_active',
    'Active database connections',
    ['database', 'pool']
)

# Cache metrics
CACHE_OPERATIONS = Counter(
    'dotmac_cache_operations_total',
    'Cache operations',
    ['operation', 'backend', 'result']
)

CACHE_HIT_RATIO = Gauge(
    'dotmac_cache_hit_ratio',
    'Cache hit ratio',
    ['backend']
)

# Task processing metrics
TASK_QUEUE_SIZE = Gauge(
    'dotmac_task_queue_size',
    'Current task queue size',
    ['queue_name']
)

TASK_PROCESSING_TIME = Histogram(
    'dotmac_task_processing_duration_seconds',
    'Task processing duration',
    ['task_type', 'status'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0)
)

TASK_FAILURES = Counter(
    'dotmac_task_failures_total',
    'Total task failures',
    ['task_type', 'error_type']
)

@dataclass
class PerformanceMetrics:
    """Container for real-time performance metrics."""
    request_count: int = 0
    error_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    durations: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_request(self, duration: float, is_error: bool = False):
        """Add request metrics."""
        self.request_count += 1
        if is_error:
            self.error_count += 1
        
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.durations.append(duration)
    
    @property
    def avg_duration(self) -> float:
        """Calculate average duration."""
        return self.total_duration / self.request_count if self.request_count > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        return (self.error_count / self.request_count * 100) if self.request_count > 0 else 0.0
    
    @property
    def p95_duration(self) -> float:
        """Calculate 95th percentile duration."""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.95)
        return sorted_durations[index] if index < len(sorted_durations) else 0.0


class EnhancedAPMMiddleware(BaseHTTPMiddleware):
    """
    Enhanced APM middleware with comprehensive monitoring capabilities.
    
    Features:
    - Prometheus metrics integration
    - Real-time performance monitoring
    - System resource tracking
    - Business metrics collection
    - SLA tracking
    - Anomaly detection
    """
    
    def __init__(
        self,
        app,
        enable_system_metrics: bool = True,
        enable_business_metrics: bool = True,
        enable_anomaly_detection: bool = True,
        metrics_update_interval: float = 30.0,
        performance_threshold_percentile: float = 95.0,
        error_rate_threshold: float = 5.0
    ):
        super().__init__(app)
        self.enable_system_metrics = enable_system_metrics
        self.enable_business_metrics = enable_business_metrics
        self.enable_anomaly_detection = enable_anomaly_detection
        self.metrics_update_interval = metrics_update_interval
        self.performance_threshold_percentile = performance_threshold_percentile
        self.error_rate_threshold = error_rate_threshold
        
        # Performance tracking
        self.endpoint_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.tenant_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.global_metrics = PerformanceMetrics()
        
        # System monitoring
        self.last_gc_stats = {i: gc.get_stats()[i]['collections'] for i in range(3)}
        
        # Start background metrics collection
        if self.enable_system_metrics:
            asyncio.create_task(self._system_metrics_collector())
        
        if self.enable_anomaly_detection:
            asyncio.create_task(self._anomaly_detector())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enhanced request processing with comprehensive monitoring."""
        start_time = time.perf_counter()
        
        # Extract request metadata
        method = request.method
        path = self._get_route_pattern(request)
        tenant_id = self._extract_tenant_id(request)
        endpoint_key = f"{method}:{path}"
        
        # Get request size
        request_size = self._get_request_size(request)
        if request_size > 0:
            REQUEST_SIZE.labels(method=method, endpoint=path).observe(request_size)
        
        # Increment active requests
        ACTIVE_REQUESTS.labels(method=method, endpoint=path).inc()
        
        # Get current span for enhanced tracing
        span = trace.get_current_span()
        
        response = None
        status_code = 500
        error_occurred = False
        
        try:
            # Enhanced span attributes
            if span.is_recording():
                span.set_attribute("http.method", method)
                span.set_attribute("http.route", path)
                span.set_attribute("http.request_size", request_size)
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                
                # Add performance context
                span.set_attribute("performance.monitoring.enabled", True)
                span.set_attribute("apm.middleware.version", "2.0")
            
            response = await call_next(request)
            status_code = response.status_code
            
            # Check for errors
            error_occurred = status_code >= 400
            
        except Exception as e:
            error_occurred = True
            status_code = 500
            
            # Enhanced error tracking
            if span.is_recording():
                span.record_exception(e)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
            
            logger.error(
                "Request processing error",
                error=str(e),
                method=method,
                path=path,
                tenant_id=tenant_id,
                exc_info=True
            )
            raise
        
        finally:
            # Calculate metrics
            duration = time.perf_counter() - start_time
            duration_seconds = duration
            
            # Decrement active requests
            ACTIVE_REQUESTS.labels(method=method, endpoint=path).dec()
            
            # Record Prometheus metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status_code=str(status_code),
                tenant_id=tenant_id or "unknown"
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=path,
                tenant_id=tenant_id or "unknown"
            ).observe(duration_seconds)
            
            # Record response size
            if response:
                response_size = self._get_response_size(response)
                if response_size > 0:
                    RESPONSE_SIZE.labels(method=method, endpoint=path).observe(response_size)
                
                if span.is_recording():
                    span.set_attribute("http.response_size", response_size)
                    span.set_attribute("http.status_code", status_code)
                    span.set_attribute("http.response_time_ms", duration * 1000)
            
            # Update internal performance metrics
            self.global_metrics.add_request(duration_seconds, error_occurred)
            self.endpoint_metrics[endpoint_key].add_request(duration_seconds, error_occurred)
            if tenant_id:
                self.tenant_metrics[tenant_id].add_request(duration_seconds, error_occurred)
                
                # Record tenant activity
                if self.enable_business_metrics:
                    TENANT_ACTIVITY.labels(
                        tenant_id=tenant_id,
                        activity_type=self._categorize_activity(method, path)
                    ).inc()
            
            # Update error rate gauge
            endpoint_error_rate = self.endpoint_metrics[endpoint_key].error_rate
            ERROR_RATE.labels(
                endpoint=path,
                tenant_id=tenant_id or "unknown"
            ).set(endpoint_error_rate)
            
            # Performance logging
            if duration_seconds > 1.0:  # Log slow requests
                performance_logger.warning(
                    "Slow request detected",
                    duration_seconds=duration_seconds,
                    method=method,
                    path=path,
                    tenant_id=tenant_id,
                    status_code=status_code
                )
            
            # Business metrics logging
            if self.enable_business_metrics and tenant_id:
                business_logger.info(
                    "API request completed",
                    tenant_id=tenant_id,
                    endpoint=path,
                    method=method,
                    duration_ms=duration * 1000,
                    status_code=status_code,
                    request_size=request_size,
                    response_size=self._get_response_size(response) if response else 0
                )
        
        return response
    
    async def _system_metrics_collector(self):
        """Background task to collect system-level metrics."""
        while True:
            try:
                # Memory metrics
                memory = psutil.virtual_memory()
                MEMORY_USAGE.labels(type='used').set(memory.used)
                MEMORY_USAGE.labels(type='available').set(memory.available)
                MEMORY_USAGE.labels(type='total').set(memory.total)
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                CPU_USAGE.set(cpu_percent)
                
                # Thread count
                process = psutil.Process()
                THREAD_COUNT.set(process.num_threads())
                
                # Garbage collection metrics
                current_gc_stats = {i: gc.get_stats()[i]['collections'] for i in range(3)}
                for gen, count in current_gc_stats.items():
                    if count > self.last_gc_stats[gen]:
                        GC_COLLECTIONS.labels(generation=str(gen)).inc(
                            count - self.last_gc_stats[gen]
                        )
                self.last_gc_stats = current_gc_stats
                
                await asyncio.sleep(self.metrics_update_interval)
                
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(self.metrics_update_interval)
    
    async def _anomaly_detector(self):
        """Background anomaly detection for performance issues."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Global anomaly detection
                if self.global_metrics.error_rate > self.error_rate_threshold:
                    logger.critical(
                        "High global error rate detected",
                        error_rate=self.global_metrics.error_rate,
                        threshold=self.error_rate_threshold
                    )
                
                # Endpoint-level anomaly detection
                for endpoint, metrics in self.endpoint_metrics.items():
                    if metrics.request_count < 10:  # Skip low-traffic endpoints
                        continue
                    
                    # Check error rate
                    if metrics.error_rate > self.error_rate_threshold:
                        logger.warning(
                            "High error rate on endpoint",
                            endpoint=endpoint,
                            error_rate=metrics.error_rate,
                            request_count=metrics.request_count
                        )
                    
                    # Check performance degradation
                    if metrics.p95_duration > 5.0:  # 5 second threshold
                        logger.warning(
                            "Performance degradation detected",
                            endpoint=endpoint,
                            p95_duration=metrics.p95_duration,
                            avg_duration=metrics.avg_duration
                        )
                
                # Tenant-level anomaly detection
                for tenant_id, metrics in self.tenant_metrics.items():
                    if metrics.request_count < 5:  # Skip low-activity tenants
                        continue
                    
                    if metrics.error_rate > self.error_rate_threshold:
                        business_logger.warning(
                            "Tenant experiencing high error rate",
                            tenant_id=tenant_id,
                            error_rate=metrics.error_rate,
                            request_count=metrics.request_count
                        )
                
            except Exception as e:
                logger.error("Error in anomaly detection", error=str(e))
    
    def _get_route_pattern(self, request: Request) -> str:
        """Extract route pattern from request."""
        if hasattr(request, "scope") and request.scope.get("route"):
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        return request.url.path
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        # Try header first
        tenant_id = request.headers.get("x-tenant-id")
        if tenant_id:
            return tenant_id
        
        # Try path parameter
        path_parts = request.url.path.strip("/").split("/")
        if "tenants" in path_parts:
            try:
                tenant_index = path_parts.index("tenants")
                if tenant_index + 1 < len(path_parts):
                    return path_parts[tenant_index + 1]
            except (ValueError, IndexError):
                pass
        
        # Try baggage context
        baggage_tenant = baggage.get_baggage("tenant.id")
        if baggage_tenant and baggage_tenant != "unknown":
            return baggage_tenant
        
        return None
    
    def _get_request_size(self, request: Request) -> int:
        """Get request body size."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return 0
    
    def _get_response_size(self, response: Response) -> int:
        """Get response body size."""
        if hasattr(response, "headers"):
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    return int(content_length)
                except ValueError:
                    pass
        return 0
    
    def _categorize_activity(self, method: str, path: str) -> str:
        """Categorize API activity for business metrics."""
        if "/api/" not in path:
            return "other"
        
        if method == "GET":
            if "tenants" in path or "customers" in path:
                return "data_access"
            elif "monitoring" in path or "health" in path:
                return "monitoring"
            else:
                return "read_operation"
        elif method == "POST":
            if "tenants" in path:
                return "tenant_creation"
            elif "customers" in path:
                return "customer_management"
            else:
                return "create_operation"
        elif method in ["PUT", "PATCH"]:
            return "update_operation"
        elif method == "DELETE":
            return "delete_operation"
        else:
            return "other"


def record_cache_operation(operation: str, backend: str, hit: bool):
    """Record cache operation metrics."""
    result = "hit" if hit else "miss"
    CACHE_OPERATIONS.labels(
        operation=operation,
        backend=backend,
        result=result
    ).inc()


def record_cache_hit_ratio(backend: str, ratio: float):
    """Record cache hit ratio."""
    CACHE_HIT_RATIO.labels(backend=backend).set(ratio)


def record_task_queue_size(queue_name: str, size: int):
    """Record current task queue size."""
    TASK_QUEUE_SIZE.labels(queue_name=queue_name).set(size)


def record_task_processing(task_type: str, duration: float, success: bool):
    """Record task processing metrics."""
    status = "success" if success else "failure"
    TASK_PROCESSING_TIME.labels(
        task_type=task_type,
        status=status
    ).observe(duration)


def record_task_failure(task_type: str, error_type: str):
    """Record task failure."""
    TASK_FAILURES.labels(
        task_type=task_type,
        error_type=error_type
    ).inc()


def record_database_connections(database: str, pool: str, count: int):
    """Record active database connections."""
    DATABASE_CONNECTIONS.labels(
        database=database,
        pool=pool
    ).set(count)


def record_rate_limit_hit(tenant_id: str, endpoint: str, limit_type: str):
    """Record API rate limit violation."""
    API_RATE_LIMITS.labels(
        tenant_id=tenant_id,
        endpoint=endpoint,
        limit_type=limit_type
    ).inc()