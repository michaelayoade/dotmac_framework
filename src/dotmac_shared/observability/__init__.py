"""
Observability Module

Provides comprehensive monitoring and observability capabilities for the
DotMac framework including metrics collection, distributed tracing,
health monitoring, and alerting.
"""

from .monitoring_stack import (
    Alert,
    AlertManager,
    AlertSeverity,
    DistributedTracer,
    HealthCheck,
    HealthMonitor,
    HealthStatus,
    Metric,
    MetricsCollector,
    MetricType,
    MonitoringStack,
    MonitoringStackFactory,
    TraceSpan,
    setup_comprehensive_monitoring,
)

__all__ = [
    "MonitoringStack",
    "MonitoringStackFactory",
    "MetricsCollector",
    "DistributedTracer",
    "AlertManager",
    "HealthMonitor",
    "Metric",
    "TraceSpan",
    "Alert",
    "HealthCheck",
    "MetricType",
    "AlertSeverity",
    "HealthStatus",
    "setup_comprehensive_monitoring",
]
