"""Metrics collection and registry for DotMac observability."""

from .business import (
    BusinessMetricSpec,
    BusinessMetricType,
    SLOEvaluation,
    TenantContext,
    TenantMetrics,
    initialize_tenant_metrics,
)
from .registry import (
    MetricDefinition,
    MetricsRegistry,
    MetricType,
    initialize_metrics_registry,
)

__all__ = [
    "MetricDefinition",
    "MetricsRegistry",
    "initialize_metrics_registry",
    "MetricType",
    "BusinessMetricSpec",
    "BusinessMetricType",
    "TenantContext",
    "TenantMetrics",
    "initialize_tenant_metrics",
    "SLOEvaluation",
]
