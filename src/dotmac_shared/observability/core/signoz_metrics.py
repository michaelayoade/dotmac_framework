"""
SignOz metrics integration for DotMac Platform.

This module provides SignOz-native monitoring using OpenTelemetry.
Migrated from Prometheus to provide unified observability.

DEPRECATED: This file has been replaced by the unified monitoring system.
Please use dotmac_shared.monitoring instead.
"""

# Re-export from unified monitoring system
from dotmac_shared.monitoring import (
    OPENTELEMETRY_AVAILABLE,
    SIGNOZ_AVAILABLE,
    MetricConfig,
    MetricType,
)
from dotmac_shared.monitoring import SignOzMonitoringService as SignOzMetrics
from dotmac_shared.monitoring import get_monitoring as get_metrics
from dotmac_shared.monitoring import init_monitoring as init_metrics

__all__ = [
    "SignOzMetrics",
    "MetricType",
    "MetricConfig",
    "get_metrics",
    "init_metrics",
    "SIGNOZ_AVAILABLE",
    "OPENTELEMETRY_AVAILABLE",
]
