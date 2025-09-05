"""
Base monitoring classes for DotMac unified monitoring system.

This module provides the core monitoring interface using OpenTelemetry and SignOz
for unified observability without Prometheus dependencies.
"""

import abc
import time
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .config import MonitoringConfig, create_monitoring_config

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class MetricType(Enum):
    """OpenTelemetry metric types for SignOz."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    UP_DOWN_COUNTER = "updowncounter"


@dataclass
class MetricConfig:
    """Configuration for an OpenTelemetry metric."""

    name: str
    description: str
    metric_type: MetricType
    unit: Optional[str] = None
    labels: Optional[list[str]] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = []


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Health check result."""

    name: str
    status: HealthStatus
    message: str
    timestamp: float = None
    details: dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.details is None:
            self.details = {}


class BaseMonitoringService(abc.ABC):
    """
    Abstract base class for monitoring services using OpenTelemetry/SignOz.

    This replaces Prometheus-based monitoring with native SignOz integration.
    """

    def __init__(
        self,
        service_name: str,
        tenant_id: Optional[str] = None,
        config: Optional[MonitoringConfig] = None,
    ):
        """Initialize monitoring service."""
        self.service_name = service_name
        self.tenant_id = tenant_id
        self.config = config or create_monitoring_config(service_name)

        # Initialize OpenTelemetry components
        self._setup_otel_providers()

    def _setup_otel_providers(self):
        """Setup OpenTelemetry providers for SignOz."""
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry not available - monitoring will be disabled")
            self.tracer = None
            self.meter = None
            return

        # Create resource
        resource = Resource.create(
            {
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.config.version,
                "service.instance.id": f"{self.service_name}-{self.tenant_id or 'default'}",
                "deployment.environment": self.config.environment,
            }
        )

        # Setup tracing
        trace.set_tracer_provider(TracerProvider(resource=resource))
        self.tracer = trace.get_tracer(self.service_name)

        # Setup metrics
        signoz_endpoint = self._get_signoz_endpoint()
        if signoz_endpoint:
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=signoz_endpoint),
                export_interval_millis=10000,  # 10 seconds
            )
            metrics.set_meter_provider(
                MeterProvider(resource=resource, metric_readers=[metric_reader])
            )

        self.meter = metrics.get_meter(self.service_name)

        # Initialize metrics
        self._init_metrics()

    def _get_signoz_endpoint(self) -> Optional[str]:
        """Get SignOz OTLP endpoint from environment."""
        import os

        return os.getenv("SIGNOZ_ENDPOINT", "http://localhost:4317")

    def _init_metrics(self):
        """Initialize standard metrics."""
        if not self.meter:
            return

        # Standard service metrics
        self.http_requests_counter = self.meter.create_counter(
            name="http_requests_total", description="Total HTTP requests", unit="1"
        )

        self.http_duration_histogram = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration",
            unit="s",
        )

        self.database_queries_counter = self.meter.create_counter(
            name="database_queries_total",
            description="Total database queries",
            unit="1",
        )

        self.database_duration_histogram = self.meter.create_histogram(
            name="database_query_duration_seconds",
            description="Database query duration",
            unit="s",
        )

        self.cache_operations_counter = self.meter.create_counter(
            name="cache_operations_total",
            description="Total cache operations",
            unit="1",
        )

        self.errors_counter = self.meter.create_counter(
            name="errors_total", description="Total errors by type", unit="1"
        )

    @abstractmethod
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        tenant_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Record HTTP request metrics."""
        pass

    @abstractmethod
    def record_database_query(
        self,
        operation: str,
        table: str,
        duration: float,
        success: bool,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record database query metrics."""
        pass

    @abstractmethod
    def record_cache_operation(
        self,
        operation: str,
        cache_name: str,
        success: bool,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record cache operation metrics."""
        pass

    @abstractmethod
    def record_error(
        self,
        error_type: str,
        service: str,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record error occurrence."""
        pass

    @abstractmethod
    def perform_health_check(self) -> list[HealthCheck]:
        """Perform service health checks."""
        pass

    @abstractmethod
    def get_metrics_endpoint(self) -> tuple[str, str]:
        """Get metrics data and content type."""
        pass

    @abstractmethod
    def _record_operation_duration(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        labels: dict[str, str],
    ) -> None:
        """Record operation duration (implementation-specific)."""
        pass


class SignOzMonitoringService(BaseMonitoringService):
    """
    SignOz-native monitoring service implementation using OpenTelemetry.
    """

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        tenant_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Record HTTP request using OpenTelemetry metrics."""
        effective_tenant_id = tenant_id or self.tenant_id or "unknown"

        if self.http_requests_counter:
            self.http_requests_counter.add(
                1,
                {
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": str(status_code),
                    "tenant_id": effective_tenant_id,
                },
            )

        if self.http_duration_histogram:
            self.http_duration_histogram.record(
                duration,
                {
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": str(status_code),
                    "tenant_id": effective_tenant_id,
                },
            )

    def record_database_query(
        self,
        operation: str,
        table: str,
        duration: float,
        success: bool,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record database query using OpenTelemetry metrics."""
        effective_tenant_id = tenant_id or self.tenant_id or "unknown"

        if self.database_queries_counter:
            self.database_queries_counter.add(
                1,
                {
                    "operation": operation,
                    "table": table,
                    "success": str(success),
                    "tenant_id": effective_tenant_id,
                },
            )

        if self.database_duration_histogram:
            self.database_duration_histogram.record(
                duration,
                {
                    "operation": operation,
                    "table": table,
                    "success": str(success),
                    "tenant_id": effective_tenant_id,
                },
            )

    def record_cache_operation(
        self,
        operation: str,
        cache_name: str,
        success: bool,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record cache operation using OpenTelemetry metrics."""
        effective_tenant_id = tenant_id or self.tenant_id or "unknown"

        if self.cache_operations_counter:
            self.cache_operations_counter.add(
                1,
                {
                    "operation": operation,
                    "cache_name": cache_name,
                    "success": str(success),
                    "tenant_id": effective_tenant_id,
                },
            )

    def record_error(
        self,
        error_type: str,
        service: str,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record error using OpenTelemetry metrics."""
        effective_tenant_id = tenant_id or self.tenant_id or "unknown"

        if self.errors_counter:
            self.errors_counter.add(
                1,
                {
                    "error_type": error_type,
                    "service": service,
                    "tenant_id": effective_tenant_id,
                },
            )

    def perform_health_check(self) -> list[HealthCheck]:
        """Perform service health checks."""
        checks = []

        # Basic service health
        checks.append(
            HealthCheck(
                name="service_status",
                status=HealthStatus.HEALTHY,
                message=f"Service {self.service_name} is running",
            )
        )

        # OpenTelemetry status
        if OPENTELEMETRY_AVAILABLE and self.meter:
            checks.append(
                HealthCheck(
                    name="opentelemetry_status",
                    status=HealthStatus.HEALTHY,
                    message="OpenTelemetry metrics active",
                )
            )
        else:
            checks.append(
                HealthCheck(
                    name="opentelemetry_status",
                    status=HealthStatus.DEGRADED,
                    message="OpenTelemetry not available",
                )
            )

        return checks

    def get_metrics_endpoint(self) -> tuple[str, str]:
        """Get metrics info for SignOz integration."""
        info = f"""# SignOz monitoring for {self.service_name}
# Service: {self.service_name}
# Tenant: {self.tenant_id}
# Version: {self.config.version}
# Environment: {self.config.environment}
# Metrics exported to SignOz via OpenTelemetry
"""
        return info, "text/plain"

    def _record_operation_duration(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        labels: dict[str, str],
    ) -> None:
        """Record operation duration using OpenTelemetry."""
        if self.meter:
            # Create dynamic histogram for custom operations
            histogram = self.meter.create_histogram(
                name=f"{operation_name}_duration_seconds",
                description=f"Duration of {operation_name} operations",
                unit="s",
            )

            histogram.record(
                duration,
                {
                    **labels,
                    "success": str(success),
                    "operation": operation_name,
                },
            )


class NoOpMonitoringService(BaseMonitoringService):
    """No-operation monitoring service for testing/disabled environments."""

    def record_http_request(self, *args, **kwargs) -> None:
        """No-op HTTP request recording."""
        pass

    def record_database_query(self, *args, **kwargs) -> None:
        """No-op database query recording."""
        pass

    def record_cache_operation(self, *args, **kwargs) -> None:
        """No-op cache operation recording."""
        pass

    def record_error(self, *args, **kwargs) -> None:
        """No-op error recording."""
        pass

    def perform_health_check(self) -> list[HealthCheck]:
        """Basic health check for no-op service."""
        return [
            HealthCheck(
                name="service_status",
                status=HealthStatus.HEALTHY,
                message=f"Service {self.service_name} is running (no-op monitoring)",
            )
        ]

    def get_metrics_endpoint(self) -> tuple[str, str]:
        """No-op metrics endpoint."""
        return f"# No-op monitoring for {self.service_name}\n", "text/plain"

    def _record_operation_duration(self, *args, **kwargs) -> None:
        """No-op operation duration recording."""
        pass


# Factory functions
def create_monitoring_service(
    service_name: str,
    tenant_id: Optional[str] = None,
    config: Optional[MonitoringConfig] = None,
    force_noop: bool = False,
) -> BaseMonitoringService:
    """
    Factory function to create appropriate monitoring service.

    Returns SignOzMonitoringService by default, NoOpMonitoringService if disabled.
    """
    if force_noop or not OPENTELEMETRY_AVAILABLE:
        return NoOpMonitoringService(service_name, tenant_id, config)

    return SignOzMonitoringService(service_name, tenant_id, config)


def get_monitoring(
    service_name: str, tenant_id: Optional[str] = None
) -> BaseMonitoringService:
    """Get monitoring service instance."""
    return create_monitoring_service(service_name, tenant_id)


def init_monitoring(
    service_name: str,
    tenant_id: Optional[str] = None,
    config: Optional[MonitoringConfig] = None,
) -> BaseMonitoringService:
    """Initialize monitoring service."""
    return create_monitoring_service(service_name, tenant_id, config)


# Export availability flag
SIGNOZ_AVAILABLE = OPENTELEMETRY_AVAILABLE

__all__ = [
    "BaseMonitoringService",
    "SignOzMonitoringService",
    "NoOpMonitoringService",
    "MetricType",
    "MetricConfig",
    "HealthStatus",
    "HealthCheck",
    "create_monitoring_service",
    "get_monitoring",
    "init_monitoring",
    "SIGNOZ_AVAILABLE",
    "OPENTELEMETRY_AVAILABLE",
]
