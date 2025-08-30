"""
Core observability components for DotMac services.
"""

# Import core components with graceful handling
try:
    from .distributed_tracing import (
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
    from dotmac_shared.monitoring import MetricConfig, MetricType
    from dotmac_shared.monitoring import (
        PrometheusMonitoringService as PrometheusMetrics,
    )
    from dotmac_shared.monitoring import get_monitoring as get_metrics
    from dotmac_shared.monitoring import init_monitoring as init_metrics
except ImportError as e:
    import warnings

    warnings.warn(f"Prometheus metrics not available: {e}")
    PrometheusMetrics = MetricType = MetricConfig = get_metrics = init_metrics = None

try:
    from .signoz_integration import SignOzTelemetry, get_signoz, init_signoz, trace
except ImportError as e:
    import warnings

    warnings.warn(f"SignOz integration not available: {e}")
    SignOzTelemetry = init_signoz = get_signoz = trace = None

try:
    from .health_reporter import (
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

__all__ = [
    # Distributed tracing
    "DistributedTracer",
    "TraceContext",
    "TraceHeaders",
    "TracePropagator",
    "TraceAnalyzer",
    "CorrelationManager",
    "trace_async",
    "trace_sync",
    "start_trace",
    # Prometheus metrics
    "PrometheusMetrics",
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
]
