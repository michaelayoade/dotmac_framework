"""
DotMac Container Monitoring & Health Service

Provides comprehensive health monitoring and lifecycle management for
ISP containers post-provisioning.
"""

from .collectors.app_metrics import AppMetricsCollector
from .collectors.database_metrics import DatabaseMetricsCollector
from .collectors.system_metrics import SystemMetricsCollector
from .core.health_monitor import (
    ContainerHealthMonitor,
    HealthCheck,
    HealthReport,
    HealthStatus,
    monitor_container_health,
)
from .core.lifecycle_manager import (
    ContainerLifecycleManager,
    LifecycleAction,
    LifecycleEvent,
    LifecycleEventType,
    LifecycleResult,
    manage_container_lifecycle,
)
from .core.metrics_collector import (
    ApplicationMetrics,
    DatabaseMetrics,
    MetricsCollector,
    MetricsSnapshot,
    SystemMetrics,
    collect_performance_metrics,
)
from .core.scaling_advisor import (
    ScalingAction,
    ScalingAdvisor,
    ScalingReason,
    ScalingRecommendation,
    ScalingUrgency,
    recommend_scaling,
)

__version__ = "1.0.0"

__all__ = [
    # Health monitoring
    "ContainerHealthMonitor",
    "monitor_container_health",
    "HealthStatus",
    "HealthCheck",
    "HealthReport",
    # Lifecycle management
    "ContainerLifecycleManager",
    "manage_container_lifecycle",
    "LifecycleAction",
    "LifecycleEventType",
    "LifecycleEvent",
    "LifecycleResult",
    # Metrics collection
    "MetricsCollector",
    "collect_performance_metrics",
    "MetricsSnapshot",
    "SystemMetrics",
    "ApplicationMetrics",
    "DatabaseMetrics",
    # Scaling advice
    "ScalingAdvisor",
    "recommend_scaling",
    "ScalingRecommendation",
    "ScalingAction",
    "ScalingReason",
    "ScalingUrgency",
    # Specialized collectors
    "SystemMetricsCollector",
    "AppMetricsCollector",
    "DatabaseMetricsCollector",
]
