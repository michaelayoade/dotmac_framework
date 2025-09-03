"""
Health integration helpers for observability components.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


@dataclass
class ObservabilityHealth:
    """Overall observability system health."""
    status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime
    
    @property
    def is_healthy(self) -> bool:
        """Check if all components are healthy."""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def summary(self) -> Dict[str, Any]:
        """Get health summary."""
        status_counts = {}
        for check in self.checks:
            status = check.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "overall_status": self.status.value,
            "total_checks": len(self.checks),
            "status_breakdown": status_counts,
            "timestamp": self.timestamp.isoformat(),
        }


def check_otel_health(bootstrap: Any) -> HealthCheck:
    """
    Check OpenTelemetry health status.
    
    Args:
        bootstrap: OTelBootstrap instance
        
    Returns:
        Health check result
    """
    start_time = datetime.utcnow()
    
    try:
        if not bootstrap:
            return HealthCheck(
                name="opentelemetry",
                status=HealthStatus.UNHEALTHY,
                message="OpenTelemetry not initialized",
                timestamp=start_time,
            )
        
        if not bootstrap.is_initialized:
            return HealthCheck(
                name="opentelemetry",
                status=HealthStatus.UNHEALTHY,
                message="OpenTelemetry providers not initialized",
                timestamp=start_time,
            )
        
        # Check if providers are working
        details = {
            "tracer_provider_available": bootstrap.tracer_provider is not None,
            "meter_provider_available": bootstrap.meter_provider is not None,
            "tracer_available": bootstrap.tracer is not None,
            "meter_available": bootstrap.meter is not None,
            "exporters": {
                exporter_type: len(exporters)
                for exporter_type, exporters in bootstrap.exporters.items()
            },
        }
        
        # Determine status
        if bootstrap.tracer_provider and bootstrap.meter_provider:
            status = HealthStatus.HEALTHY
            message = "OpenTelemetry fully operational"
        elif bootstrap.tracer_provider or bootstrap.meter_provider:
            status = HealthStatus.DEGRADED
            message = "OpenTelemetry partially operational"
        else:
            status = HealthStatus.UNHEALTHY
            message = "OpenTelemetry providers not working"
        
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheck(
            name="opentelemetry",
            status=status,
            message=message,
            timestamp=start_time,
            details=details,
            duration_ms=duration,
        )
        
    except Exception as e:
        logger.error(f"OpenTelemetry health check failed: {e}")
        return HealthCheck(
            name="opentelemetry",
            status=HealthStatus.UNHEALTHY,
            message=f"Health check failed: {e}",
            timestamp=start_time,
        )


def check_metrics_registry_health(registry: Any) -> HealthCheck:
    """
    Check metrics registry health status.
    
    Args:
        registry: MetricsRegistry instance
        
    Returns:
        Health check result
    """
    start_time = datetime.utcnow()
    
    try:
        if not registry:
            return HealthCheck(
                name="metrics_registry",
                status=HealthStatus.UNHEALTHY,
                message="Metrics registry not initialized",
                timestamp=start_time,
            )
        
        # Get registry information
        metric_count = len(registry.list_metrics())
        prometheus_available = registry.enable_prometheus
        
        details = {
            "service_name": registry.service_name,
            "registered_metrics": metric_count,
            "prometheus_enabled": prometheus_available,
        }
        
        # Test basic functionality
        try:
            metrics_info = registry.get_metrics_info()
            details["metrics_info_available"] = True
            details["metric_types"] = list(set(
                info.get("type") for info in metrics_info.values()
            ))
        except Exception as e:
            details["metrics_info_available"] = False
            details["metrics_info_error"] = str(e)
        
        # Test Prometheus metrics if enabled
        if prometheus_available:
            try:
                prometheus_metrics = registry.get_prometheus_metrics()
                details["prometheus_metrics_available"] = True
                details["prometheus_metrics_length"] = len(prometheus_metrics)
            except Exception as e:
                details["prometheus_metrics_available"] = False
                details["prometheus_metrics_error"] = str(e)
        
        # Determine status
        if metric_count > 0:
            if prometheus_available and details.get("prometheus_metrics_available", False):
                status = HealthStatus.HEALTHY
                message = f"Metrics registry operational with {metric_count} metrics"
            elif prometheus_available:
                status = HealthStatus.DEGRADED
                message = f"Metrics registry partially operational (Prometheus issues)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Metrics registry operational with {metric_count} metrics (no Prometheus)"
        else:
            status = HealthStatus.DEGRADED
            message = "Metrics registry has no registered metrics"
        
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheck(
            name="metrics_registry",
            status=status,
            message=message,
            timestamp=start_time,
            details=details,
            duration_ms=duration,
        )
        
    except Exception as e:
        logger.error(f"Metrics registry health check failed: {e}")
        return HealthCheck(
            name="metrics_registry",
            status=HealthStatus.UNHEALTHY,
            message=f"Health check failed: {e}",
            timestamp=start_time,
        )


def check_tenant_metrics_health(tenant_metrics: Any) -> HealthCheck:
    """
    Check tenant metrics health status.
    
    Args:
        tenant_metrics: TenantMetrics instance
        
    Returns:
        Health check result
    """
    start_time = datetime.utcnow()
    
    try:
        if not tenant_metrics:
            return HealthCheck(
                name="tenant_metrics",
                status=HealthStatus.UNHEALTHY,
                message="Tenant metrics not initialized",
                timestamp=start_time,
            )
        
        # Get tenant metrics information
        business_metrics = tenant_metrics.get_business_metrics_info()
        
        details = {
            "service_name": tenant_metrics.service_name,
            "business_metrics_count": len(business_metrics),
            "slo_monitoring_enabled": tenant_metrics.enable_slo_monitoring,
            "dashboards_enabled": tenant_metrics.enable_dashboards,
            "business_metric_types": list(set(
                info.get("type") for info in business_metrics.values()
            )),
        }
        
        # Determine status
        if len(business_metrics) > 0:
            status = HealthStatus.HEALTHY
            message = f"Tenant metrics operational with {len(business_metrics)} business metrics"
        else:
            status = HealthStatus.DEGRADED
            message = "Tenant metrics has no registered business metrics"
        
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return HealthCheck(
            name="tenant_metrics",
            status=status,
            message=message,
            timestamp=start_time,
            details=details,
            duration_ms=duration,
        )
        
    except Exception as e:
        logger.error(f"Tenant metrics health check failed: {e}")
        return HealthCheck(
            name="tenant_metrics",
            status=HealthStatus.UNHEALTHY,
            message=f"Health check failed: {e}",
            timestamp=start_time,
        )


def get_observability_health(
    otel_bootstrap: Optional[Any] = None,
    metrics_registry: Optional[Any] = None,
    tenant_metrics: Optional[Any] = None,
) -> ObservabilityHealth:
    """
    Get overall observability system health.
    
    Args:
        otel_bootstrap: OpenTelemetry bootstrap instance
        metrics_registry: Metrics registry instance
        tenant_metrics: Tenant metrics instance
        
    Returns:
        Overall health status
    """
    checks = []
    
    # Check OpenTelemetry
    if otel_bootstrap is not None:
        checks.append(check_otel_health(otel_bootstrap))
    
    # Check metrics registry
    if metrics_registry is not None:
        checks.append(check_metrics_registry_health(metrics_registry))
    
    # Check tenant metrics
    if tenant_metrics is not None:
        checks.append(check_tenant_metrics_health(tenant_metrics))
    
    # Determine overall status
    if not checks:
        overall_status = HealthStatus.UNKNOWN
    else:
        statuses = [check.status for check in checks]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
    
    return ObservabilityHealth(
        status=overall_status,
        checks=checks,
        timestamp=datetime.utcnow(),
    )


def create_health_endpoint_handler(
    otel_bootstrap: Optional[Any] = None,
    metrics_registry: Optional[Any] = None,
    tenant_metrics: Optional[Any] = None,
) -> callable:
    """
    Create a health endpoint handler function.
    
    Args:
        otel_bootstrap: OpenTelemetry bootstrap instance
        metrics_registry: Metrics registry instance  
        tenant_metrics: Tenant metrics instance
        
    Returns:
        Handler function that returns health status
    """
    def health_handler() -> Dict[str, Any]:
        """Health endpoint handler."""
        health = get_observability_health(
            otel_bootstrap=otel_bootstrap,
            metrics_registry=metrics_registry,
            tenant_metrics=tenant_metrics,
        )
        
        return {
            "status": health.status.value,
            "timestamp": health.timestamp.isoformat(),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "details": check.details,
                }
                for check in health.checks
            ],
            "summary": health.summary,
        }
    
    return health_handler