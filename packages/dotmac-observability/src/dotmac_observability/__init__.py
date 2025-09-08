"""
DotMac Observability - Lightweight metrics and health toolkit.

This package provides simple, efficient observability tools for DotMac services:
- Metrics collection (counters, gauges, histograms, timers)
- Health monitoring with configurable checks
- Optional FastAPI/Starlette middleware
- Optional OpenTelemetry integration
"""

__version__ = "1.0.0"

from .health import HealthMonitor
from .metrics import MetricsCollector, get_collector, reset_collector
from .types import HealthCheckResult, HealthStatus, MetricType

__all__ = [
    # Core metrics
    "MetricsCollector",
    "get_collector",
    "reset_collector",
    # Health monitoring
    "HealthMonitor",
    "HealthCheckResult",
    "HealthStatus",
    # Types
    "MetricType",
]

# Optional imports (available when extras are installed)
try:
    from .middleware import create_audit_middleware, timing_middleware

    MIDDLEWARE_AVAILABLE = True
    __all__.extend(["create_audit_middleware", "timing_middleware", "MIDDLEWARE_AVAILABLE"])
except ImportError:
    MIDDLEWARE_AVAILABLE = False
    create_audit_middleware = timing_middleware = None

try:
    from .otel import enable_otel_bridge

    OTEL_AVAILABLE = True
    __all__.extend(["enable_otel_bridge", "OTEL_AVAILABLE"])
except ImportError:
    OTEL_AVAILABLE = False
    enable_otel_bridge = None
