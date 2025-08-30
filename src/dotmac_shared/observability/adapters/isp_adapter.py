"""
ISP Platform Adapter for Observability

Integrates the observability package with ISP framework services
and provides ISP-specific metrics and monitoring capabilities.
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


class ISPObservabilityAdapter:
    """Adapter for integrating observability with ISP platform services."""

    def __init__(
        self,
        tracer=None,
        metrics=None,
        health_reporter=None,
        signoz=None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize ISP observability adapter.

        Args:
            tracer: Distributed tracer instance
            metrics: Prometheus metrics instance
            health_reporter: Health reporter instance
            signoz: SignOz integration instance
            tenant_id: Default tenant ID for metrics
        """
        self.tracer = tracer
        self.metrics = metrics
        self.health_reporter = health_reporter
        self.signoz = signoz
        self.tenant_id = tenant_id or "default"

        # ISP-specific configuration
        self.service_name = "isp-framework"
        self.isp_metrics_enabled = True

    def record_customer_event(
        self,
        event_type: str,
        customer_id: str,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record ISP customer-specific events."""
        tenant_id = tenant_id or self.tenant_id

        # Record in SignOz if available
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"customer.{event_type}",
                tenant_id=tenant_id,
                attributes={
                    "customer_id": customer_id,
                    "event_category": "customer",
                    **(metadata or {}),
                },
            )

        # Record in Prometheus if available
        if self.metrics:
            self.metrics.record_tenant_api_call(
                tenant_id=tenant_id, service="customer_service", endpoint=event_type
            )

    def record_billing_event(
        self,
        event_type: str,
        amount: Optional[float] = None,
        currency: str = "USD",
        customer_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Record ISP billing-specific events."""
        tenant_id = tenant_id or self.tenant_id

        # Record revenue if amount provided
        if amount is not None:
            if self.signoz:
                self.signoz.record_revenue(
                    amount=amount,
                    currency=currency,
                    tenant_id=tenant_id,
                    transaction_type=event_type,
                )

        # Record billing event
        attributes = {
            "billing_event": event_type,
            "currency": currency,
        }
        if customer_id:
            attributes["customer_id"] = customer_id

        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"billing.{event_type}",
                tenant_id=tenant_id,
                value=amount or 1.0,
                attributes=attributes,
            )

        if self.metrics:
            self.metrics.record_tenant_api_call(
                tenant_id=tenant_id, service="billing_service", endpoint=event_type
            )

    def record_network_operation(
        self,
        operation: str,
        device_type: Optional[str] = None,
        success: bool = True,
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
    ):
        """Record ISP network operations."""
        tenant_id = tenant_id or self.tenant_id

        # Create trace context if tracer available
        if self.tracer:
            tags = {
                "operation.type": "network",
                "network.operation": operation,
                "network.success": success,
            }
            if device_type:
                tags["network.device_type"] = device_type
            if duration_ms:
                tags["network.duration_ms"] = duration_ms

            with self.tracer.span(f"network.{operation}", tags=tags):
                pass

        # Record in SignOz
        if self.signoz:
            attributes = {
                "network_operation": operation,
                "success": success,
            }
            if device_type:
                attributes["device_type"] = device_type

            self.signoz.record_business_event(
                event_type=f"network.{operation}",
                tenant_id=tenant_id,
                attributes=attributes,
            )

    def record_service_provisioning(
        self,
        service_type: str,
        customer_id: str,
        status: str,
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
    ):
        """Record ISP service provisioning events."""
        tenant_id = tenant_id or self.tenant_id

        # Record provisioning metrics
        if self.metrics:
            # Record background job if this is a provisioning task
            if duration_ms:
                self.metrics.record_background_job(
                    job_type=f"provision_{service_type}",
                    duration=duration_ms / 1000,  # Convert to seconds
                    success=(status == "completed"),
                    tenant_id=tenant_id,
                )

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type="service.provisioning",
                tenant_id=tenant_id,
                attributes={
                    "service_type": service_type,
                    "customer_id": customer_id,
                    "status": status,
                    "duration_ms": duration_ms,
                },
            )

    def record_support_ticket(
        self,
        ticket_id: str,
        event_type: str,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        customer_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Record ISP support ticket events."""
        tenant_id = tenant_id or self.tenant_id

        attributes = {
            "ticket_id": ticket_id,
            "event_type": event_type,
        }
        if priority:
            attributes["priority"] = priority
        if category:
            attributes["category"] = category
        if customer_id:
            attributes["customer_id"] = customer_id

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"support.{event_type}",
                tenant_id=tenant_id,
                attributes=attributes,
            )

        # Record in Prometheus
        if self.metrics:
            self.metrics.record_tenant_api_call(
                tenant_id=tenant_id, service="support_service", endpoint=event_type
            )

    def record_authentication_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None,
        success: bool = True,
        tenant_id: Optional[str] = None,
    ):
        """Record ISP authentication events."""
        tenant_id = tenant_id or self.tenant_id

        attributes = {
            "auth_event": event_type,
            "success": success,
        }
        if user_id:
            attributes["user_id"] = user_id
        if user_type:
            attributes["user_type"] = user_type

        # Record security metrics
        if not success and self.metrics:
            self.metrics.record_error(
                error_type=f"auth_failure_{event_type}",
                service="auth_service",
                tenant_id=tenant_id,
            )

        # Record in SignOz
        if self.signoz:
            self.signoz.record_business_event(
                event_type=f"auth.{event_type}",
                tenant_id=tenant_id,
                attributes=attributes,
            )

    def record_api_usage(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Record ISP API usage metrics."""
        tenant_id = tenant_id or self.tenant_id

        # Record HTTP metrics
        if self.metrics:
            self.metrics.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration_ms / 1000,  # Convert to seconds
                tenant_id=tenant_id,
            )

        # Record in SignOz
        if self.signoz:
            self.signoz.record_http_metrics(
                method=method,
                path=endpoint,
                status_code=status_code,
                duration=duration_ms,
                tenant_id=tenant_id,
            )

    def get_tenant_health_summary(
        self, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get health summary for a specific tenant."""
        tenant_id = tenant_id or self.tenant_id

        if not self.health_reporter:
            return {"error": "Health reporter not available"}

        # Get general health data
        health_data = self.health_reporter.get_latest_health_data()

        # Add ISP-specific health checks
        isp_health = {
            "tenant_id": tenant_id,
            "service_type": "isp_framework",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add ISP-specific metrics if available
        if health_data.get("health_data"):
            isp_health.update(health_data["health_data"])

        return isp_health

    def create_tenant_dashboard_config(
        self, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create ISP tenant-specific dashboard configuration."""
        tenant_id = tenant_id or self.tenant_id

        dashboard_config = {
            "title": f"ISP Tenant Dashboard - {tenant_id}",
            "tenant_id": tenant_id,
            "service": "isp_framework",
            "widgets": [
                {
                    "title": "Customer Events",
                    "type": "counter",
                    "metric": "business.events.count",
                    "filters": {"tenant.id": tenant_id, "event.type": "customer.*"},
                },
                {
                    "title": "Billing Revenue",
                    "type": "gauge",
                    "metric": "business.revenue.total",
                    "filters": {"tenant.id": tenant_id},
                },
                {
                    "title": "Network Operations",
                    "type": "histogram",
                    "metric": "business.events.count",
                    "filters": {"tenant.id": tenant_id, "event.type": "network.*"},
                },
                {
                    "title": "Support Tickets",
                    "type": "counter",
                    "metric": "business.events.count",
                    "filters": {"tenant.id": tenant_id, "event.type": "support.*"},
                },
                {
                    "title": "API Usage",
                    "type": "histogram",
                    "metric": "http.server.request.count",
                    "filters": {"tenant.id": tenant_id},
                },
            ],
        }

        return dashboard_config

    def setup_tenant_monitoring(
        self, tenant_id: str, config: Optional[Dict[str, Any]] = None
    ):
        """Setup monitoring for a specific ISP tenant."""
        config = config or {}

        logger.info(f"Setting up ISP monitoring for tenant: {tenant_id}")

        # Initialize tenant-specific health reporting
        if self.health_reporter:
            # Configure tenant-specific health checks
            tenant_config = {
                "tenant_id": tenant_id,
                "include_isp_metrics": True,
                **config,
            }

        # Setup SignOz dashboard if available
        if self.signoz:
            dashboard_config = self.create_tenant_dashboard_config(tenant_id)
            logger.info(f"Created dashboard config for tenant {tenant_id}")

        logger.info(f"ISP monitoring setup completed for tenant: {tenant_id}")

    def get_isp_business_metrics(
        self, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get ISP-specific business metrics."""
        tenant_id = tenant_id or self.tenant_id

        # This would typically query metrics from the observability backends
        # For now, return a structure showing what would be available
        return {
            "tenant_id": tenant_id,
            "metrics": {
                "customer_events": {
                    "registrations": 0,
                    "activations": 0,
                    "deactivations": 0,
                },
                "billing_events": {
                    "payments": 0,
                    "invoices": 0,
                    "revenue": 0.0,
                },
                "network_operations": {
                    "device_configs": 0,
                    "provisioning": 0,
                    "maintenance": 0,
                },
                "support_metrics": {
                    "tickets_created": 0,
                    "tickets_resolved": 0,
                    "average_resolution_time": 0.0,
                },
                "api_usage": {
                    "total_requests": 0,
                    "error_rate": 0.0,
                    "average_response_time": 0.0,
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
