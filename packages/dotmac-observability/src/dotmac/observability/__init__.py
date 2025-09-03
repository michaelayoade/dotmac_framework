"""
DotMac Observability Package

Provides comprehensive observability capabilities including:
- OpenTelemetry bootstrap and configuration
- Unified metrics registry (OTEL + Prometheus)  
- Tenant-scoped business metrics and SLO monitoring
- Dashboard provisioning for SigNoz/Grafana
- Health checks and monitoring

Usage:
    Basic setup:
    
    ```python
    from dotmac.observability import (
        create_default_config,
        initialize_otel,
        initialize_metrics_registry,
    )
    
    # Configure OpenTelemetry
    config = create_default_config(
        service_name="my-service",
        environment="production",
        service_version="1.0.0",
    )
    
    # Initialize OpenTelemetry
    otel = initialize_otel(config)
    
    # Initialize metrics registry
    metrics = initialize_metrics_registry("my-service")
    ```
    
    Business metrics and SLOs:
    
    ```python
    from dotmac.observability import (
        initialize_tenant_metrics,
        BusinessMetricSpec,
        BusinessMetricType,
        TenantContext,
    )
    
    # Initialize tenant metrics
    tenant_metrics = initialize_tenant_metrics("my-service", metrics)
    
    # Register business metric
    spec = BusinessMetricSpec(
        name="login_success_rate",
        metric_type=BusinessMetricType.SUCCESS_RATE,
        description="User login success rate",
        slo_target=0.99,
        alert_threshold=0.95,
    )
    tenant_metrics.register_business_metric(spec)
    
    # Record metrics
    context = TenantContext(tenant_id="tenant-123", service="auth")
    tenant_metrics.record_business_metric("login_success_rate", 1, context)
    
    # Evaluate SLOs
    slos = tenant_metrics.evaluate_slos(context)
    ```
"""

# Import all public APIs from the internal api module
from .api import *

# Package metadata
__package_name__ = "dotmac-observability"
__author__ = "DotMac Framework Team"
__email__ = "dev@dotmac.com"