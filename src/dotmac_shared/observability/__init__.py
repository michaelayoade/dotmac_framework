"""
DEPRECATED: dotmac_shared.observability module

This module is deprecated and will be removed in a future version.
Please migrate to the new dotmac.observability package.

Migration guide:
    
Old import:
    from dotmac_shared.observability import initialize_otel, initialize_metrics_registry
    
New import:
    from dotmac.observability import initialize_otel, initialize_metrics_registry

The new package provides:
    - Better configuration management
    - Enhanced business metrics support  
    - Improved SLO monitoring
    - Dashboard provisioning capabilities
    - Health monitoring integration
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "dotmac_shared.observability is deprecated and will be removed in the next minor release. "
    "Please migrate to dotmac.observability package. "
    "Install with: pip install dotmac-observability",
    DeprecationWarning,
    stacklevel=2
)

# Import existing implementations for backward compatibility
try:
    from .otel_bootstrap import (
        OtelBootstrap,
        OtelConfig,
        OtelExporter,
        initialize_otel as _old_initialize_otel,
        get_otel_bootstrap,
        create_default_config as _old_create_default_config,
    )

    from .metrics_schema import (
        UnifiedMetricsRegistry,
        MetricDefinition,
        MetricType,
        MetricCategory,
        MetricTimer,
        get_metrics_registry,
        initialize_metrics_registry as _old_initialize_metrics_registry,
    )

    from .tenant_metrics import (
        TenantMetricsCollector,
        BusinessMetricSpec,
        BusinessMetricType,
        SLODefinition,
        TenantMetricsExporter,
        get_tenant_metrics_collector,
        initialize_tenant_metrics as _old_initialize_tenant_metrics,
    )
    
    # Provide backward compatibility functions
    def initialize_otel(*args, **kwargs):
        warnings.warn("Use dotmac.observability.initialize_otel", DeprecationWarning, stacklevel=2)
        return _old_initialize_otel(*args, **kwargs)
        
    def create_default_config(*args, **kwargs):
        warnings.warn("Use dotmac.observability.create_default_config", DeprecationWarning, stacklevel=2)
        return _old_create_default_config(*args, **kwargs)
        
    def initialize_metrics_registry(*args, **kwargs):
        warnings.warn("Use dotmac.observability.initialize_metrics_registry", DeprecationWarning, stacklevel=2)
        return _old_initialize_metrics_registry(*args, **kwargs)
        
    def initialize_tenant_metrics(*args, **kwargs):
        warnings.warn("Use dotmac.observability.initialize_tenant_metrics", DeprecationWarning, stacklevel=2)
        return _old_initialize_tenant_metrics(*args, **kwargs)
    
except ImportError:
    # If old modules don't exist, just provide stubs
    warnings.warn("Legacy observability modules not found. Please use dotmac.observability package.", UserWarning)
    
    def initialize_otel(*args, **kwargs):
        raise ImportError("Legacy module not available. Use dotmac.observability package.")
    
    def create_default_config(*args, **kwargs):
        raise ImportError("Legacy module not available. Use dotmac.observability package.")
    
    def initialize_metrics_registry(*args, **kwargs):
        raise ImportError("Legacy module not available. Use dotmac.observability package.")
    
    def initialize_tenant_metrics(*args, **kwargs):
        raise ImportError("Legacy module not available. Use dotmac.observability package.")

# Try to also provide new package imports for migration convenience
try:
    from dotmac.observability import (
        initialize_otel as new_initialize_otel,
        initialize_metrics_registry as new_initialize_metrics_registry,
        initialize_tenant_metrics as new_initialize_tenant_metrics,
        create_default_config as new_create_default_config,
        BusinessMetricSpec as NewBusinessMetricSpec,
        TenantContext,
        get_observability_health,
    )
    
    # Add migration helpers
    def migrate_to_new_api():
        """
        Helper function to show migration examples.
        """
        print("Migration examples:")
        print("OLD: from dotmac_shared.observability import initialize_otel")
        print("NEW: from dotmac.observability import initialize_otel")
        print("")
        print("OLD: setup = initialize_otel(service_name, environment)")
        print("NEW: config = create_default_config(service_name, environment)")
        print("     otel = initialize_otel(config)")
    
except ImportError:
    # New package not available
    def migrate_to_new_api():
        print("Please install dotmac.observability package: pip install dotmac-observability")

__all__ = [
    # OTEL Bootstrap
    "OtelBootstrap",
    "OtelConfig", 
    "OtelExporter",
    "initialize_otel",
    "get_otel_bootstrap",
    "create_default_config",
    
    # Metrics Schema
    "UnifiedMetricsRegistry",
    "MetricDefinition",
    "MetricType",
    "MetricCategory", 
    "MetricTimer",
    "get_metrics_registry",
    "initialize_metrics_registry",
    
    # Tenant Metrics
    "TenantMetricsCollector",
    "BusinessMetricSpec",
    "BusinessMetricType",
    "SLODefinition",
    "TenantMetricsExporter",
    "get_tenant_metrics_collector",
    "initialize_tenant_metrics",
]