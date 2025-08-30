"""
DotMac Observability Package - Complete Observability Stack

This package provides a comprehensive observability solution including:
- Distributed tracing with OpenTelemetry
- SignOz native monitoring for unified metrics, traces, and logs
- Health status reporting and monitoring
- Cross-platform telemetry collection

Features:
- SignOz-native unified observability (metrics, traces, logs)
- Tenant-aware metrics and tracing
- Business metrics and KPI tracking
- Performance monitoring and alerting
- Automatic instrumentation for FastAPI, SQLAlchemy, Redis
- Health checks for databases, services, and dependencies
- Correlation ID management across services
"""

from typing import Optional

# Import core components with graceful handling
try:
    from .core.distributed_tracing import (
        CorrelationManager,
        DistributedTracer,
        TraceAnalyzer,
        TraceContext,
        TraceHeaders,
        TracePropagator,
        start_trace,
        trace_async,
        trace_sync,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Distributed tracing not available: {e}")
    DistributedTracer = TraceContext = TraceHeaders = TracePropagator = None
    TraceAnalyzer = CorrelationManager = trace_async = trace_sync = start_trace = None

try:
    from .core.signoz_metrics import (
        MetricConfig,
        MetricType,
        SignOzMetrics,
        get_metrics,
        init_metrics,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"SignOz metrics not available: {e}")
    SignOzMetrics = MetricType = MetricConfig = get_metrics = init_metrics = None

try:
    from .core.signoz_integration import SignOzTelemetry, get_signoz, init_signoz, trace
except ImportError as e:
    import warnings

    warnings.warn(f"SignOz integration not available: {e}")
    SignOzTelemetry = init_signoz = get_signoz = trace = None

try:
    from .core.health_reporter import (
        HealthReporter,
        get_health_reporter,
        start_health_reporting,
        stop_health_reporting,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Health reporter not available: {e}")
    HealthReporter = get_health_reporter = start_health_reporting = (
        stop_health_reporting
    ) = None

# Adapters for platform integration
try:
    from .adapters.isp_adapter import ISPObservabilityAdapter
except ImportError:
    ISPObservabilityAdapter = None

try:
    from .adapters.management_adapter import ManagementPlatformAdapter
except ImportError:
    ManagementPlatformAdapter = None

# Configuration and utilities
from .config import ObservabilityConfig, get_default_config

# Version info
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main exports
__all__ = [
    # Core tracing
    "DistributedTracer",
    "TraceContext",
    "TraceHeaders",
    "TracePropagator",
    "TraceAnalyzer",
    "CorrelationManager",
    "trace_async",
    "trace_sync",
    "start_trace",
    # Metrics
    "SignOzMetrics",
    "MetricType",
    "MetricConfig",
    "get_metrics",
    "init_metrics",
    # SignOz integration
    "SignOzTelemetry",
    "init_signoz",
    "get_signoz",
    "trace",
    # Health monitoring
    "HealthReporter",
    "get_health_reporter",
    "start_health_reporting",
    "stop_health_reporting",
    # Platform adapters
    "ISPObservabilityAdapter",
    "ManagementPlatformAdapter",
    # Configuration
    "ObservabilityConfig",
    "get_default_config",
    # Version info
    "__version__",
]

# Configuration defaults
DEFAULT_CONFIG = {
    "tracing": {
        "enabled": True,
        "service_name": "dotmac-service",
        "service_version": "1.0.0",
        "sampling_rate": 1.0,
        "max_spans_per_trace": 1000,
        "export_timeout_ms": 30000,
    },
    "metrics": {
        "enabled": True,
        "signoz_enabled": True,
        "export_interval_ms": 30000,
        "histogram_buckets": [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    },
    "signoz": {
        "enabled": True,
        "endpoint": "localhost:4317",
        "insecure": True,
        "enable_profiling": False,
        "access_token": None,
    },
    "health": {
        "enabled": True,
        "reporting_interval": 60,
        "auto_start": True,
        "include_system_metrics": True,
        "include_business_metrics": True,
    },
    "correlation": {
        "enabled": True,
        "header_names": {
            "trace_id": "X-Trace-Id",
            "correlation_id": "X-Correlation-Id",
            "tenant_id": "X-Tenant-Id",
            "user_id": "X-User-Id",
        },
    },
}


def get_version():
    """Get package version."""
    return __version__


def get_config():
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()


# Global observability manager
_observability_manager: Optional["ObservabilityManager"] = None


class ObservabilityManager:
    """Unified observability manager for DotMac services."""

    def __init__(self, config: Optional[dict] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.tracer = None
        self.metrics = None
        self.signoz = None
        self.health_reporter = None

    def initialize(self, service_name: str, service_version: str = "1.0.0"):
        """Initialize observability components."""
        # Update service info in config
        self.config["tracing"]["service_name"] = service_name
        self.config["tracing"]["service_version"] = service_version

        # Initialize tracing
        if self.config["tracing"]["enabled"] and DistributedTracer:
            self.tracer = DistributedTracer(
                service_name=service_name, version=service_version
            )

        # Initialize metrics
        if self.config["metrics"]["enabled"]:
            if self.config["metrics"]["signoz_enabled"] and SignOzMetrics:
                self.metrics = init_metrics(service_name) if init_metrics else None

            if self.config["signoz"]["enabled"] and SignOzTelemetry:
                self.signoz = init_signoz(
                    service_name=service_name,
                    service_version=service_version,
                    **self.config["signoz"],
                )

        # Initialize health reporting
        if self.config["health"]["enabled"] and HealthReporter:
            self.health_reporter = get_health_reporter()
            if self.config["health"]["auto_start"]:
                import asyncio

                asyncio.create_task(start_health_reporting())

    def shutdown(self):
        """Shutdown observability components."""
        if self.signoz:
            self.signoz.shutdown()

        if self.health_reporter and stop_health_reporting:
            stop_health_reporting()


def init_observability(
    service_name: str, service_version: str = "1.0.0", config: Optional[dict] = None
) -> ObservabilityManager:
    """Initialize global observability manager."""
    global _observability_manager
    _observability_manager = ObservabilityManager(config)
    _observability_manager.initialize(service_name, service_version)
    return _observability_manager


def get_observability() -> Optional[ObservabilityManager]:
    """Get global observability manager."""
    return _observability_manager
