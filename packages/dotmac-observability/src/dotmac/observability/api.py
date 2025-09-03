"""
Internal API module for dotmac.observability package.
This module contains the implementation that gets re-exported in __init__.py.
"""

# Re-export all public APIs from submodules
from .config import (
    create_default_config,
    create_metrics_config,
    create_dashboard_config,
    OTelConfig,
    MetricsConfig,
    DashboardConfig,
    Environment,
    ExporterType,
    ExporterConfig,
)

from .bootstrap import (
    initialize_otel,
    shutdown_otel,
    get_current_span_context,
    create_child_span,
    OTelBootstrap,
)

from .metrics import (
    initialize_metrics_registry,
    initialize_tenant_metrics,
    MetricsRegistry,
    TenantMetrics,
    MetricDefinition,
    MetricType,
    BusinessMetricSpec,
    BusinessMetricType,
    TenantContext,
    SLOEvaluation,
)

from .dashboards import (
    provision_platform_dashboards,
    DashboardProvisioningResult,
    DashboardConfig as DashboardProvisioningConfig,
)

from .health import (
    get_observability_health,
    create_health_endpoint_handler,
    check_otel_health,
    check_metrics_registry_health,
    check_tenant_metrics_health,
    ObservabilityHealth,
    HealthCheck,
    HealthStatus,
)

# Version information
__version__ = "1.0.0"

# Public API exports
__all__ = [
    # Configuration
    "create_default_config",
    "create_metrics_config", 
    "create_dashboard_config",
    "OTelConfig",
    "MetricsConfig",
    "DashboardConfig",
    "Environment",
    "ExporterType",
    "ExporterConfig",
    
    # Bootstrap
    "initialize_otel",
    "shutdown_otel",
    "get_current_span_context",
    "create_child_span",
    "OTelBootstrap",
    
    # Metrics
    "initialize_metrics_registry",
    "initialize_tenant_metrics",
    "MetricsRegistry",
    "TenantMetrics",
    "MetricDefinition",
    "MetricType",
    "BusinessMetricSpec",
    "BusinessMetricType",
    "TenantContext",
    "SLOEvaluation",
    
    # Dashboards
    "provision_platform_dashboards",
    "DashboardProvisioningResult",
    "DashboardProvisioningConfig",
    
    # Health
    "get_observability_health",
    "create_health_endpoint_handler",
    "check_otel_health",
    "check_metrics_registry_health",
    "check_tenant_metrics_health",
    "ObservabilityHealth",
    "HealthCheck",
    "HealthStatus",
    
    # Package info
    "__version__",
]