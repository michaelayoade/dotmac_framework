"""
Management Platform Adapter for Observability

Integrates the observability package with management platform services
and provides management-specific metrics and monitoring capabilities.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ManagementPlatformAdapter:
    """Adapter for integrating observability with management platform services."""

    def __init__(self, tracer=None, metrics=None, health_reporter=None, signoz=None):
        """
        Initialize management platform observability adapter.

        Args:
            tracer: Distributed tracer instance
            metrics: Prometheus metrics instance
            health_reporter: Health reporter instance
            signoz: SignOz integration instance
        """
        self.tracer = tracer
        self.metrics = metrics
        self.health_reporter = health_reporter
        self.signoz = signoz

        # Management platform specific configuration
        self.service_name = "management-platform"
        self.platform_metrics_enabled = True

    def record_tenant_operation(
        self,
        operation: str,
        tenant_id: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record management platform tenant operations."""

        # Create trace context if tracer available
        if self.tracer:
            tags = {
                "operation.type": "tenant_management",
                "tenant.operation": operation,
                "tenant.id": tenant_id,
                "operation.success": success,
            }
            if duration_ms:
                tags["operation.duration_ms"] = duration_ms
            if metadata:
                tags.update(metadata)

            with self.tracer.span(f"tenant.{operation}", tags=tags):
                pass

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"tenant.{operation}",
                tenant_id=tenant_id,
                attributes={
                    "operation": operation,
                    "success": success,
                    "service": "tenant_management",
                    **(metadata or {}),
                },
            )

        # Record in Prometheus
        if self.metrics:
            self.metrics.record_tenant_api_call(
                tenant_id=tenant_id, service="tenant_service", endpoint=operation
            )

    def record_deployment_event(
        self,
        deployment_id: str,
        event_type: str,
        target_tenant: str,
        status: str,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record management platform deployment events."""

        # Record deployment as background job if duration provided
        if self.metrics and duration_ms:
            self.metrics.record_background_job(
                job_type=f"deployment_{event_type}",
                duration=duration_ms / 1000,  # Convert to seconds
                success=(status == "completed"),
                tenant_id=target_tenant,
            )

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"deployment.{event_type}",
                tenant_id=target_tenant,
                attributes={
                    "deployment_id": deployment_id,
                    "event_type": event_type,
                    "status": status,
                    "duration_ms": duration_ms,
                    "service": "deployment_service",
                    **(metadata or {}),
                },
            )

    def record_billing_operation(
        self,
        operation: str,
        tenant_id: str,
        amount: Optional[float] = None,
        currency: str = "USD",
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record management platform billing operations."""

        # Record revenue if amount provided
        if amount is not None and self.signoz:
            self.signoz.record_revenue(
                amount=amount,
                currency=currency,
                tenant_id=tenant_id,
                transaction_type=operation,
            )

        # Record billing event
        attributes = {
            "billing_operation": operation,
            "currency": currency,
            "success": success,
            "service": "billing_service",
        }
        if metadata:
            attributes.update(metadata)

        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"billing.{operation}",
                tenant_id=tenant_id,
                value=amount or 1.0,
                attributes=attributes,
            )

        # Record error if operation failed
        if not success and self.metrics:
            self.metrics.record_error(
                error_type=f"billing_{operation}_failure",
                service="billing_service",
                tenant_id=tenant_id,
            )

    def record_monitoring_event(
        self,
        event_type: str,
        target_tenant: Optional[str] = None,
        alert_level: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record management platform monitoring events."""

        attributes = {
            "monitoring_event": event_type,
            "service": "monitoring_service",
        }
        if target_tenant:
            attributes["target_tenant"] = target_tenant
        if alert_level:
            attributes["alert_level"] = alert_level
        if component:
            attributes["component"] = component
        if metadata:
            attributes.update(metadata)

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"monitoring.{event_type}",
                tenant_id=target_tenant or "management",
                attributes=attributes,
            )

        # Record in Prometheus
        if self.metrics:
            self.metrics.record_tenant_api_call(
                tenant_id=target_tenant or "management",
                service="monitoring_service",
                endpoint=event_type,
            )

    def record_plugin_operation(
        self,
        plugin_name: str,
        operation: str,
        tenant_id: Optional[str] = None,
        success: bool = True,
        duration_ms: Optional[float] = None,
    ):
        """Record management platform plugin operations."""

        # Create trace for plugin operation
        if self.tracer:
            tags = {
                "plugin.name": plugin_name,
                "plugin.operation": operation,
                "operation.success": success,
            }
            if tenant_id:
                tags["tenant.id"] = tenant_id
            if duration_ms:
                tags["operation.duration_ms"] = duration_ms

            with self.tracer.span(f"plugin.{operation}", tags=tags):
                pass

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"plugin.{operation}",
                tenant_id=tenant_id or "management",
                attributes={
                    "plugin_name": plugin_name,
                    "operation": operation,
                    "success": success,
                    "service": "plugin_service",
                    "duration_ms": duration_ms,
                },
            )

    def record_user_management_event(
        self,
        event_type: str,
        user_id: str,
        user_role: Optional[str] = None,
        target_tenant: Optional[str] = None,
        success: bool = True,
    ):
        """Record management platform user management events."""

        attributes = {
            "user_event": event_type,
            "user_id": user_id,
            "success": success,
            "service": "user_management_service",
        }
        if user_role:
            attributes["user_role"] = user_role
        if target_tenant:
            attributes["target_tenant"] = target_tenant

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"user_management.{event_type}",
                tenant_id=target_tenant or "management",
                attributes=attributes,
            )

        # Record authentication failure if applicable
        if not success and event_type in ["login", "authentication"] and self.metrics:
            self.metrics.record_error(
                error_type=f"user_auth_failure",
                service="user_management_service",
                tenant_id=target_tenant or "management",
            )

    def record_analytics_event(
        self,
        event_type: str,
        tenant_id: Optional[str] = None,
        data_points: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record management platform analytics events."""

        # Record as background job if processing time provided
        if self.metrics and processing_time_ms:
            self.metrics.record_background_job(
                job_type=f"analytics_{event_type}",
                duration=processing_time_ms / 1000,  # Convert to seconds
                success=True,
                tenant_id=tenant_id or "management",
            )

        attributes = {
            "analytics_event": event_type,
            "service": "analytics_service",
        }
        if data_points:
            attributes["data_points"] = data_points
        if processing_time_ms:
            attributes["processing_time_ms"] = processing_time_ms
        if metadata:
            attributes.update(metadata)

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"analytics.{event_type}",
                tenant_id=tenant_id or "management",
                attributes=attributes,
            )

    def get_platform_health_summary(self) -> Dict[str, Any]:
        """Get health summary for the management platform."""

        if not self.health_reporter:
            return {"error": "Health reporter not available"}

        # Get general health data
        health_data = self.health_reporter.get_latest_health_data()

        # Add management platform specific health checks
        platform_health = {
            "service_type": "management_platform",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform_components": {
                "tenant_service": "unknown",
                "deployment_service": "unknown",
                "billing_service": "unknown",
                "monitoring_service": "unknown",
                "analytics_service": "unknown",
                "user_management_service": "unknown",
            },
        }

        # Add general health data if available
        if health_data.get("health_data"):
            platform_health.update(health_data["health_data"])

        return platform_health

    def create_platform_dashboard_config(self) -> Dict[str, Any]:
        """Create management platform dashboard configuration."""

        dashboard_config = {
            "title": "Management Platform Dashboard",
            "service": "management_platform",
            "widgets": [
                {
                    "title": "Tenant Operations",
                    "type": "counter",
                    "metric": "business.events.count",
                    "filters": {
                        "event.type": "tenant.*",
                        "service.name": "management_platform",
                    },
                },
                {
                    "title": "Deployment Events",
                    "type": "histogram",
                    "metric": "background_job_duration_seconds",
                    "filters": {"job_type": "deployment_*"},
                },
                {
                    "title": "Platform Revenue",
                    "type": "gauge",
                    "metric": "business.revenue.total",
                    "filters": {"service.name": "management_platform"},
                },
                {
                    "title": "Platform Errors",
                    "type": "counter",
                    "metric": "errors_total",
                    "filters": {"service": "management_platform"},
                },
                {
                    "title": "User Management Events",
                    "type": "counter",
                    "metric": "business.events.count",
                    "filters": {"event.type": "user_management.*"},
                },
                {
                    "title": "Plugin Operations",
                    "type": "histogram",
                    "metric": "business.events.count",
                    "filters": {"event.type": "plugin.*"},
                },
            ],
        }

        return dashboard_config

    def setup_platform_monitoring(self, config: Optional[Dict[str, Any]] = None):
        """Setup monitoring for the management platform."""
        config = config or {}

        logger.info("Setting up management platform monitoring")

        # Initialize platform-specific health reporting
        if self.health_reporter:
            # Configure management platform specific health checks
            platform_config = {
                "include_platform_metrics": True,
                "monitor_tenant_services": True,
                "monitor_deployment_pipeline": True,
                **config,
            }

        # Setup SignOz dashboard if available
        if self.signoz:
            dashboard_config = self.create_platform_dashboard_config()
            logger.info("Created management platform dashboard config")

        logger.info("Management platform monitoring setup completed")

    def get_platform_business_metrics(self) -> Dict[str, Any]:
        """Get management platform specific business metrics."""

        # This would typically query metrics from the observability backends
        # For now, return a structure showing what would be available
        return {
            "service": "management_platform",
            "metrics": {
                "tenant_operations": {
                    "tenant_creations": 0,
                    "tenant_updates": 0,
                    "tenant_deletions": 0,
                    "tenant_activations": 0,
                },
                "deployment_metrics": {
                    "deployments_initiated": 0,
                    "deployments_completed": 0,
                    "deployments_failed": 0,
                    "average_deployment_time": 0.0,
                },
                "billing_metrics": {
                    "invoices_generated": 0,
                    "payments_processed": 0,
                    "platform_revenue": 0.0,
                    "commission_calculated": 0.0,
                },
                "monitoring_metrics": {
                    "alerts_generated": 0,
                    "health_checks_performed": 0,
                    "tenant_health_reports": 0,
                },
                "user_management_metrics": {
                    "user_logins": 0,
                    "user_registrations": 0,
                    "permission_updates": 0,
                    "failed_authentications": 0,
                },
                "plugin_metrics": {
                    "plugin_executions": 0,
                    "plugin_installations": 0,
                    "plugin_errors": 0,
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_multi_tenant_summary(self) -> Dict[str, Any]:
        """Get summary metrics across all tenants managed by the platform."""

        return {
            "platform": "management_platform",
            "summary": {
                "total_tenants": 0,
                "active_tenants": 0,
                "tenant_health": {
                    "healthy": 0,
                    "warning": 0,
                    "unhealthy": 0,
                },
                "resource_utilization": {
                    "total_cpu_usage": 0.0,
                    "total_memory_usage": 0.0,
                    "total_storage_usage": 0.0,
                },
                "business_metrics": {
                    "total_revenue": 0.0,
                    "total_api_calls": 0,
                    "total_active_users": 0,
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
