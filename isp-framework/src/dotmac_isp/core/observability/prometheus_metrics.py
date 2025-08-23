"""
Prometheus metrics integration for DotMac Platform.

Provides standardized Prometheus metrics collection and exposition
with tenant isolation and business metrics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        Summary,
        generate_latest,
        multiprocess,
        values,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Define fallback types when prometheus_client is not available
    CollectorRegistry = type("CollectorRegistry", (), {})

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Prometheus metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"


@dataclass
class MetricConfig:
    """Configuration for a Prometheus metric."""

    name: str
    help: str
    metric_type: MetricType
    labels: list[str] = None
    buckets: list[float] = None  # For histograms

    def __post_init__(self):
        if self.labels is None:
            self.labels = []


class PrometheusMetrics:
    """Prometheus metrics manager for DotMac services."""

    def __init__(self, service_name: str, registry: CollectorRegistry | None = None):
        self.service_name = service_name
        self.registry = registry or CollectorRegistry()
        self._metrics: dict[str, Any] = {}

        # Initialize core service metrics
        self._init_core_metrics()

    def _init_core_metrics(self):
        """Initialize core metrics for all DotMac services."""

        # HTTP Request metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code", "tenant_id"],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint", "tenant_id"],
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        self.http_request_size_bytes = Histogram(
            "http_request_size_bytes",
            "HTTP request size in bytes",
            ["method", "endpoint"],
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=self.registry,
        )

        self.http_response_size_bytes = Histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
            ["method", "endpoint"],
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=self.registry,
        )

        # Database metrics
        self.database_connections_active = Gauge(
            "database_connections_active",
            "Active database connections",
            ["pool_name"],
            registry=self.registry,
        )

        self.database_query_duration_seconds = Histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table", "tenant_id"],
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry,
        )

        self.database_queries_total = Counter(
            "database_queries_total",
            "Total database queries",
            ["operation", "table", "status", "tenant_id"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_operations_total = Counter(
            "cache_operations_total",
            "Total cache operations",
            ["operation", "cache_name", "status"],
            registry=self.registry,
        )

        self.cache_hit_ratio = Gauge(
            "cache_hit_ratio", "Cache hit ratio", ["cache_name"], registry=self.registry
        )

        # Business metrics
        self.tenant_active_sessions = Gauge(
            "tenant_active_sessions",
            "Active user sessions per tenant",
            ["tenant_id"],
            registry=self.registry,
        )

        self.tenant_api_calls_total = Counter(
            "tenant_api_calls_total",
            "Total API calls per tenant",
            ["tenant_id", "service", "endpoint"],
            registry=self.registry,
        )

        self.tenant_resource_usage = Gauge(
            "tenant_resource_usage",
            "Resource usage per tenant",
            ["tenant_id", "resource_type"],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            "errors_total",
            "Total errors by type",
            ["error_type", "service", "tenant_id"],
            registry=self.registry,
        )

        self.circuit_breaker_state = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["service", "operation"],
            registry=self.registry,
        )

        # Rate limiting metrics
        self.rate_limit_hits_total = Counter(
            "rate_limit_hits_total",
            "Total rate limit hits",
            ["tenant_id", "endpoint", "limit_type"],
            registry=self.registry,
        )

        self.rate_limit_remaining = Gauge(
            "rate_limit_remaining",
            "Remaining rate limit quota",
            ["tenant_id", "endpoint", "limit_type"],
            registry=self.registry,
        )

        # Service health metrics
        self.service_info = Info(
            "service_info", "Service information", registry=self.registry
        )

        self.service_uptime_seconds = Gauge(
            "service_uptime_seconds",
            "Service uptime in seconds",
            registry=self.registry,
        )

        self.dependency_status = Gauge(
            "dependency_status",
            "Dependency health status (1=healthy, 0=unhealthy)",
            ["dependency_name", "dependency_type"],
            registry=self.registry,
        )

        # Store all metrics for easy access
        self._metrics.update(
            {
                "http_requests_total": self.http_requests_total,
                "http_request_duration_seconds": self.http_request_duration_seconds,
                "http_request_size_bytes": self.http_request_size_bytes,
                "http_response_size_bytes": self.http_response_size_bytes,
                "database_connections_active": self.database_connections_active,
                "database_query_duration_seconds": self.database_query_duration_seconds,
                "database_queries_total": self.database_queries_total,
                "cache_operations_total": self.cache_operations_total,
                "cache_hit_ratio": self.cache_hit_ratio,
                "tenant_active_sessions": self.tenant_active_sessions,
                "tenant_api_calls_total": self.tenant_api_calls_total,
                "tenant_resource_usage": self.tenant_resource_usage,
                "errors_total": self.errors_total,
                "circuit_breaker_state": self.circuit_breaker_state,
                "rate_limit_hits_total": self.rate_limit_hits_total,
                "rate_limit_remaining": self.rate_limit_remaining,
                "service_info": self.service_info,
                "service_uptime_seconds": self.service_uptime_seconds,
                "dependency_status": self.dependency_status,
            }
        )

        # Set service info
        self.service_info.info(
            {
                "service": self.service_name,
                "version": "1.0.0",  # Should come from config
                "environment": "production",  # Should come from config
            }
        )

    def create_custom_metric(self, config: MetricConfig) -> Any:
        """Create a custom metric."""
        if config.name in self._metrics:
            return self._metrics[config.name]

        labels = config.labels or []

        if config.metric_type == MetricType.COUNTER:
            metric = Counter(config.name, config.help, labels, registry=self.registry)
        elif config.metric_type == MetricType.GAUGE:
            metric = Gauge(config.name, config.help, labels, registry=self.registry)
        elif config.metric_type == MetricType.HISTOGRAM:
            buckets = config.buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
            metric = Histogram(
                config.name,
                config.help,
                labels,
                buckets=buckets,
                registry=self.registry,
            )
        elif config.metric_type == MetricType.SUMMARY:
            metric = Summary(config.name, config.help, labels, registry=self.registry)
        elif config.metric_type == MetricType.INFO:
            metric = Info(config.name, config.help, registry=self.registry)
        else:
            raise ValueError(f"Unsupported metric type: {config.metric_type}")

        self._metrics[config.name] = metric
        return metric

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        tenant_id: str = "unknown",
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
            tenant_id=tenant_id,
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method, endpoint=endpoint, tenant_id=tenant_id
        ).observe(duration)

        if request_size > 0:
            self.http_request_size_bytes.labels(
                method=method, endpoint=endpoint
            ).observe(request_size)

        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method, endpoint=endpoint
            ).observe(response_size)

    def record_database_query(
        self,
        operation: str,
        table: str,
        duration: float,
        success: bool,
        tenant_id: str = "unknown",
    ):
        """Record database query metrics."""
        status = "success" if success else "error"

        self.database_queries_total.labels(
            operation=operation, table=table, status=status, tenant_id=tenant_id
        ).inc()

        self.database_query_duration_seconds.labels(
            operation=operation, table=table, tenant_id=tenant_id
        ).observe(duration)

    def record_cache_operation(self, operation: str, cache_name: str, success: bool):
        """Record cache operation metrics."""
        status = (
            "hit"
            if operation == "get" and success
            else "miss" if operation == "get" else "success" if success else "error"
        )

        self.cache_operations_total.labels(
            operation=operation, cache_name=cache_name, status=status
        ).inc()

    def update_cache_hit_ratio(self, cache_name: str, hit_ratio: float):
        """Update cache hit ratio metric."""
        self.cache_hit_ratio.labels(cache_name=cache_name).set(hit_ratio)

    def record_error(self, error_type: str, service: str, tenant_id: str = "unknown"):
        """Record error occurrence."""
        self.errors_total.labels(
            error_type=error_type, service=service, tenant_id=tenant_id
        ).inc()

    def update_circuit_breaker_state(self, service: str, operation: str, state: int):
        """Update circuit breaker state (0=closed, 1=open, 2=half-open)."""
        self.circuit_breaker_state.labels(service=service, operation=operation).set(
            state
        )

    def record_rate_limit_hit(self, tenant_id: str, endpoint: str, limit_type: str):
        """Record rate limit hit."""
        self.rate_limit_hits_total.labels(
            tenant_id=tenant_id, endpoint=endpoint, limit_type=limit_type
        ).inc()

    def update_rate_limit_remaining(
        self, tenant_id: str, endpoint: str, limit_type: str, remaining: int
    ):
        """Update remaining rate limit quota."""
        self.rate_limit_remaining.labels(
            tenant_id=tenant_id, endpoint=endpoint, limit_type=limit_type
        ).set(remaining)

    def update_dependency_status(
        self, dependency_name: str, dependency_type: str, healthy: bool
    ):
        """Update dependency health status."""
        status = 1.0 if healthy else 0.0
        self.dependency_status.labels(
            dependency_name=dependency_name, dependency_type=dependency_type
        ).set(status)

    def update_service_uptime(self, uptime_seconds: float):
        """Update service uptime."""
        self.service_uptime_seconds.set(uptime_seconds)

    def update_tenant_sessions(self, tenant_id: str, session_count: int):
        """Update active session count for tenant."""
        self.tenant_active_sessions.labels(tenant_id=tenant_id).set(session_count)

    def record_tenant_api_call(self, tenant_id: str, service: str, endpoint: str):
        """Record API call for tenant."""
        self.tenant_api_calls_total.labels(
            tenant_id=tenant_id, service=service, endpoint=endpoint
        ).inc()

    def update_tenant_resource_usage(
        self, tenant_id: str, resource_type: str, usage: float
    ):
        """Update resource usage for tenant."""
        self.tenant_resource_usage.labels(
            tenant_id=tenant_id, resource_type=resource_type
        ).set(usage)

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics in exposition format."""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available")
            return "# Prometheus client not available\n"

        try:
            return generate_latest(self.registry)
        except Exception as e:
            logger.error(f"Failed to generate metrics: {e}")
            return f"# Error generating metrics: {e}\n"

    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else "text/plain"


# Global metrics instance
_metrics_instance: PrometheusMetrics | None = None


def get_metrics(service_name: str = "dotmac") -> PrometheusMetrics:
    """Get or create global metrics instance."""
    global _metrics_instance

    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics(service_name)

    return _metrics_instance


def init_metrics(
    service_name: str, registry: CollectorRegistry | None = None
) -> PrometheusMetrics:
    """Initialize metrics for a service."""
    global _metrics_instance
    _metrics_instance = PrometheusMetrics(service_name, registry)
    return _metrics_instance
