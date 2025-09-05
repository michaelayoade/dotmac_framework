"""
Observability setup for DotMac applications.
Wires OTEL, metrics, and business SLOs into the shared factory.
"""

import logging
import os
from typing import Any, Optional

from fastapi import FastAPI

from ..auth.edge_validation import EdgeAuthMiddleware, EdgeJWTValidator
from ..auth.service_tokens import ServiceAuthMiddleware, configure_service_auth
from ..observability import (
    create_default_config,
    initialize_metrics_registry,
    initialize_otel,
    initialize_tenant_metrics,
)
from ..tenant.identity import TenantIdentityResolver
from ..tenant.middleware import TenantMiddleware
from .config import DeploymentMode, PlatformConfig

logger = logging.getLogger(__name__)


async def setup_observability(
    app: FastAPI, platform_config: PlatformConfig, enable_business_slos: bool = True
) -> dict[str, Any]:
    """
    Set up comprehensive observability for a DotMac application.

    Features:
    - OpenTelemetry initialization with auto-instrumentation
    - Unified metrics registry (OTEL + Prometheus)
    - Tenant-scoped business metrics and dashboards
    - SLO monitoring with alerts
    - Service authentication system
    - Tenant identity resolution and middleware

    Args:
        app: FastAPI application instance
        platform_config: Platform configuration
        enable_business_slos: Enable business SLO monitoring

    Returns:
        Dictionary of initialized observability components
    """
    logger.info("🔍 Setting up comprehensive observability system...")

    # Determine service configuration
    service_name = _get_service_name(platform_config)
    environment = os.getenv("ENVIRONMENT", "production")
    service_version = os.getenv("APP_VERSION", "1.0.0")

    components = {}

    try:
        # 1. Initialize OpenTelemetry with environment-specific configuration
        logger.info("Initializing OpenTelemetry...")
        otel_config = create_default_config(
            service_name=service_name,
            environment=environment,
            service_version=service_version,
            custom_resource_attributes=_get_resource_attributes(platform_config),
        )

        # Environment-specific exporter configuration
        if environment == "development":
            otel_config.tracing_exporters = ["console"]
            otel_config.metrics_exporters = ["console"]
        elif environment == "staging":
            otel_config.tracing_exporters = ["otlp", "console"]
            otel_config.metrics_exporters = ["otlp", "prometheus"]
        else:  # production
            otel_config.tracing_exporters = ["otlp"]
            otel_config.metrics_exporters = ["otlp", "prometheus"]

        otel_bootstrap = initialize_otel(otel_config)
        components["otel_bootstrap"] = otel_bootstrap

        # 2. Initialize unified metrics registry
        logger.info("Setting up unified metrics registry...")
        metrics_registry = initialize_metrics_registry(service_name, enable_prometheus=True)

        # Connect OTEL meter to metrics registry
        if otel_bootstrap and otel_bootstrap.get_meter():
            metrics_registry.set_otel_meter(otel_bootstrap.get_meter())

        components["metrics_registry"] = metrics_registry

        # 3. Register business SLO metrics
        if enable_business_slos:
            logger.info("Registering business SLO metrics...")
            _register_business_slo_metrics(metrics_registry, platform_config)

        # 4. Initialize tenant metrics system
        logger.info("Setting up tenant-scoped metrics...")
        tenant_metrics = initialize_tenant_metrics(
            service_name=service_name,
            metrics_registry=metrics_registry,
            enable_dashboards=True,
            enable_slo_monitoring=enable_business_slos,
        )

        # Register platform-specific business metrics
        _register_platform_business_metrics(tenant_metrics, platform_config)

        components["tenant_metrics"] = tenant_metrics

        # 5. Configure service-to-service authentication
        logger.info("Setting up service authentication...")
        service_signing_secret = os.getenv("SERVICE_SIGNING_SECRET", "dev-secret-key-change-in-production")
        service_token_manager = configure_service_auth(service_signing_secret)

        # Register service capabilities
        _register_service_capabilities(
            service_token_manager, service_name, service_version, environment, platform_config
        )

        components["service_token_manager"] = service_token_manager

        # 6. Configure tenant identity resolution
        logger.info("Setting up tenant identity system...")
        tenant_resolver = TenantIdentityResolver()
        _configure_tenant_patterns(tenant_resolver, platform_config)
        components["tenant_resolver"] = tenant_resolver

        # 7. Configure edge authentication
        logger.info("Setting up edge JWT validation...")
        jwt_secret = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")
        edge_validator = EdgeJWTValidator(jwt_secret=jwt_secret, tenant_resolver=tenant_resolver)
        _configure_route_sensitivity(edge_validator, platform_config)
        components["edge_validator"] = edge_validator

        # 8. Apply middleware stack in correct order
        logger.info("Applying observability middleware stack...")
        _apply_observability_middleware(app, components)

        # 9. Store components in app state
        _store_components_in_app_state(app, components)

        # 10. Set up health check integration
        _setup_observability_health_checks(app, components)

        # 11. Set up platform dashboards and alerts
        logger.info("Setting up platform dashboards...")
        tenant_id = None
        if platform_config.deployment_context and hasattr(platform_config.deployment_context, "tenant_id"):
            tenant_id = platform_config.deployment_context.tenant_id

        dashboard_results = await setup_platform_dashboards(app, platform_config, tenant_id)
        components["dashboards"] = dashboard_results

        logger.info("✅ Observability system setup complete")
        logger.info(f"   Service: {service_name}")
        logger.info(f"   Environment: {environment}")
        logger.info("   OTEL Enabled: True")
        logger.info(f"   Metrics Registry: {len(metrics_registry.metric_definitions)} metrics")
        logger.info(f"   Business SLOs: {'Enabled' if enable_business_slos else 'Disabled'}")

        return components

    except Exception as e:
        logger.error(f"❌ Observability setup failed: {e}")
        raise


def _get_service_name(platform_config: PlatformConfig) -> str:
    """Determine service name from platform configuration."""
    if not platform_config.deployment_context:
        return platform_config.platform_name

    mode = platform_config.deployment_context.mode

    if mode == DeploymentMode.TENANT_CONTAINER:
        tenant_id = getattr(platform_config.deployment_context, "tenant_id", "unknown")
        return f"isp-{tenant_id}"
    elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
        return "dotmac-management"
    else:
        return platform_config.platform_name


def _get_resource_attributes(platform_config: PlatformConfig) -> dict[str, str]:
    """Get OpenTelemetry resource attributes."""
    attributes = {"service.namespace": "dotmac", "deployment.environment": os.getenv("ENVIRONMENT", "production")}

    if platform_config.deployment_context:
        mode = platform_config.deployment_context.mode
        attributes["deployment.mode"] = mode.value if hasattr(mode, "value") else str(mode)

        if hasattr(platform_config.deployment_context, "tenant_id"):
            attributes["tenant.id"] = platform_config.deployment_context.tenant_id

    return attributes


def _register_business_slo_metrics(metrics_registry, platform_config: PlatformConfig):
    """Register business SLO metrics."""
    from ..observability.metrics_schema import MetricCategory, MetricDefinition, MetricType

    # Core business SLOs
    business_metrics = [
        # Authentication/Login SLOs
        MetricDefinition(
            name="login_attempts_total",
            type=MetricType.COUNTER,
            category=MetricCategory.BUSINESS,
            description="Total login attempts",
            labels=["result", "auth_method"],
            help_text="Total number of login attempts with result and method",
        ),
        MetricDefinition(
            name="login_duration_seconds",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.BUSINESS,
            description="Login duration in seconds",
            unit="seconds",
            labels=["auth_method", "result"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            help_text="Time taken for login process (p95 SLO target: <2s)",
        ),
        # Provisioning SLOs
        MetricDefinition(
            name="provisioning_requests_total",
            type=MetricType.COUNTER,
            category=MetricCategory.BUSINESS,
            description="Total provisioning requests",
            labels=["service_type", "result"],
            help_text="Total service provisioning requests",
        ),
        MetricDefinition(
            name="provisioning_duration_seconds",
            type=MetricType.HISTOGRAM,
            category=MetricCategory.BUSINESS,
            description="Service provisioning duration",
            unit="seconds",
            labels=["service_type", "result"],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 180.0, 300.0],
            help_text="Time to provision services (SLO target: <60s)",
        ),
        # Success Rate SLOs
        MetricDefinition(
            name="business_operations_total",
            type=MetricType.COUNTER,
            category=MetricCategory.BUSINESS,
            description="Total business operations",
            labels=["operation_type", "result"],
            help_text="All business operations for success rate calculation",
        ),
        # Customer Experience SLOs
        MetricDefinition(
            name="customer_satisfaction_score",
            type=MetricType.GAUGE,
            category=MetricCategory.BUSINESS,
            description="Customer satisfaction score",
            labels=["score_type"],
            help_text="Customer satisfaction metrics (NPS, CSAT, etc.)",
        ),
        # Revenue SLOs
        MetricDefinition(
            name="revenue_transactions_total",
            type=MetricType.COUNTER,
            category=MetricCategory.BUSINESS,
            description="Revenue generating transactions",
            labels=["transaction_type", "currency"],
            help_text="Count of revenue transactions",
        ),
        MetricDefinition(
            name="revenue_amount",
            type=MetricType.GAUGE,
            category=MetricCategory.BUSINESS,
            description="Revenue amount in base currency",
            unit="currency",
            labels=["revenue_type", "period"],
            help_text="Revenue amounts for tracking",
        ),
    ]

    for metric in business_metrics:
        success = metrics_registry.register_metric(metric)
        if success:
            logger.debug(f"Registered business SLO metric: {metric.name}")


def _register_platform_business_metrics(tenant_metrics, platform_config: PlatformConfig):
    """Register platform-specific business metrics."""
    if not platform_config.deployment_context:
        return

    mode = platform_config.deployment_context.mode

    if mode == DeploymentMode.MANAGEMENT_PLATFORM:
        # Management Platform metrics
        from ..observability.tenant_metrics import BusinessMetricSpec, BusinessMetricType

        management_metrics = [
            BusinessMetricSpec(
                name="active_tenant_containers",
                metric_type=BusinessMetricType.GAUGE,
                description="Number of active tenant containers",
                slo_target=0.99,  # 99% uptime
                alert_threshold=0.95,
            ),
            BusinessMetricSpec(
                name="container_provisioning_success_rate",
                metric_type=BusinessMetricType.SUCCESS_RATE,
                description="Container provisioning success rate",
                slo_target=0.95,  # 95% success rate
                alert_threshold=0.90,
            ),
            BusinessMetricSpec(
                name="partner_portal_response_time",
                metric_type=BusinessMetricType.LATENCY,
                description="Partner portal response time",
                slo_target=2.0,  # 2 second target
                alert_threshold=3.0,
            ),
        ]

        for metric_spec in management_metrics:
            tenant_metrics.register_business_metric(metric_spec)

    elif mode == DeploymentMode.TENANT_CONTAINER:
        # ISP Framework metrics
        from ..observability.tenant_metrics import BusinessMetricSpec, BusinessMetricType

        isp_metrics = [
            BusinessMetricSpec(
                name="customer_login_success_rate",
                metric_type=BusinessMetricType.SUCCESS_RATE,
                description="Customer login success rate",
                slo_target=0.98,  # 98% success rate
                alert_threshold=0.95,
            ),
            BusinessMetricSpec(
                name="service_provisioning_time",
                metric_type=BusinessMetricType.LATENCY,
                description="Service provisioning time",
                slo_target=60.0,  # 60 second target
                alert_threshold=120.0,
            ),
            BusinessMetricSpec(
                name="customer_support_resolution_time",
                metric_type=BusinessMetricType.LATENCY,
                description="Support ticket resolution time",
                slo_target=3600.0,  # 1 hour target
                alert_threshold=7200.0,
            ),
        ]

        for metric_spec in isp_metrics:
            tenant_metrics.register_business_metric(metric_spec)


def _register_service_capabilities(
    service_token_manager, service_name: str, version: str, environment: str, platform_config: PlatformConfig
):
    """Register service capabilities for inter-service communication."""
    capabilities = ["health_checks", "metrics", "monitoring"]
    allowed_targets = ["dotmac-shared", "dotmac-logging", "dotmac-metrics"]

    if platform_config.deployment_context:
        mode = platform_config.deployment_context.mode

        if mode == DeploymentMode.MANAGEMENT_PLATFORM:
            capabilities.extend(
                ["tenant_management", "partner_management", "billing", "container_orchestration", "plugin_management"]
            )
            allowed_targets.extend(["isp-customer", "isp-billing", "isp-network", "isp-support"])
        elif mode == DeploymentMode.TENANT_CONTAINER:
            capabilities.extend(["customer_management", "billing", "network_services", "support"])
            allowed_targets.extend(["dotmac-management", "isp-billing", "isp-network", "isp-support"])

    service_token_manager.register_service(
        service_name=service_name,
        service_info={"version": version, "environment": environment, "capabilities": capabilities},
        allowed_targets=allowed_targets,
    )


def _configure_tenant_patterns(tenant_resolver: TenantIdentityResolver, platform_config: PlatformConfig):
    """Configure tenant identity patterns based on platform."""
    if not platform_config.deployment_context:
        # Default patterns for development
        tenant_resolver.configure_patterns({"default": r"^(?P<tenant_id>\w+)\..*"})
        return

    mode = platform_config.deployment_context.mode

    if mode == DeploymentMode.MANAGEMENT_PLATFORM:
        tenant_resolver.configure_patterns(
            {
                "management": r"^admin\.(?P<tenant_id>\w+)\..*",
                "partner": r"^partner\.(?P<tenant_id>\w+)\..*",
                "reseller": r"^(?P<tenant_id>\w+)\.reseller\..*",
            }
        )
    elif mode == DeploymentMode.TENANT_CONTAINER:
        tenant_resolver.configure_patterns(
            {
                "customer": r"^(?P<tenant_id>\w+)\.customers\..*",
                "support": r"^support\.(?P<tenant_id>\w+)\..*",
                "billing": r"^billing\.(?P<tenant_id>\w+)\..*",
                "portal": r"^portal\.(?P<tenant_id>\w+)\..*",
            }
        )


def _configure_route_sensitivity(edge_validator: EdgeJWTValidator, platform_config: PlatformConfig):
    """Configure route sensitivity patterns based on platform."""
    base_patterns = {
        # Public routes
        (r"/health", ".*"): "public",
        (r"/metrics", ".*"): "public",
        (r"/docs", ".*"): "public",
        (r"/openapi.json", ".*"): "public",
        # Internal routes
        (r"/internal/.*", ".*"): "internal",
    }

    if not platform_config.deployment_context:
        edge_validator.configure_sensitivity_patterns(base_patterns)
        return

    mode = platform_config.deployment_context.mode

    if mode == DeploymentMode.MANAGEMENT_PLATFORM:
        management_patterns = {
            # Admin routes
            (r"/admin/.*", ".*"): "admin",
            (r"/api/admin/.*", ".*"): "admin",
            # Tenant management
            (r"/api/tenants/.*", "GET"): "authenticated",
            (r"/api/tenants/.*", "POST|PUT|DELETE"): "sensitive",
            # Partner routes
            (r"/api/partners/.*", "GET"): "authenticated",
            (r"/api/partners/.*", "POST|PUT|DELETE"): "sensitive",
            # Billing routes
            (r"/api/billing/.*", ".*"): "sensitive",
        }
        base_patterns.update(management_patterns)

    elif mode == DeploymentMode.TENANT_CONTAINER:
        isp_patterns = {
            # Customer routes
            (r"/api/customers/.*", "GET"): "authenticated",
            (r"/api/customers/.*/billing", ".*"): "sensitive",
            (r"/api/customers/.*/services", "POST|PUT|DELETE"): "sensitive",
            # Billing routes
            (r"/api/billing/.*", ".*"): "sensitive",
            # Network management
            (r"/api/network/.*", "GET"): "authenticated",
            (r"/api/network/.*", "POST|PUT|DELETE"): "sensitive",
            # Support routes
            (r"/api/support/.*", "GET"): "authenticated",
            (r"/api/support/tickets/.*", "POST|PUT"): "authenticated",
            # Admin routes
            (r"/admin/.*", ".*"): "admin",
        }
        base_patterns.update(isp_patterns)

    edge_validator.configure_sensitivity_patterns(base_patterns)


def _apply_observability_middleware(app: FastAPI, components: dict[str, Any]):
    """Apply observability middleware in correct order (LIFO)."""
    # Service auth middleware (innermost - applied last)
    app.add_middleware(
        ServiceAuthMiddleware,
        token_manager=components["service_token_manager"],
        service_name=_get_service_name_from_components(components),
        required_operations=[],
    )

    # Edge JWT validation middleware
    app.add_middleware(
        EdgeAuthMiddleware,
        validator=components["edge_validator"],
        service_name=_get_service_name_from_components(components),
    )

    # Tenant middleware (outermost - applied first)
    app.add_middleware(
        TenantMiddleware,
        resolver=components["tenant_resolver"],
        service_name=_get_service_name_from_components(components),
    )


def _store_components_in_app_state(app: FastAPI, components: dict[str, Any]):
    """Store observability components in app state for access in routes."""
    for component_name, component in components.items():
        setattr(app.state, component_name, component)


def _setup_observability_health_checks(app: FastAPI, components: dict[str, Any]):
    """Set up health checks for observability components."""
    # This would integrate with the existing health check system
    pass


async def setup_platform_dashboards(
    app: FastAPI, platform_config: PlatformConfig, tenant_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Set up platform-specific dashboards and alerts.

    Args:
        app: FastAPI application instance
        platform_config: Platform configuration
        tenant_id: Optional tenant ID for tenant-specific dashboards

    Returns:
        Dictionary of dashboard provisioning results
    """
    logger.info("🎨 Setting up platform dashboards and alerts...")

    try:
        from .dashboards.dashboard_manager import provision_platform_dashboards

        # Determine platform type
        platform_type = _get_platform_type(platform_config)

        # Prepare custom variables
        custom_variables = {
            "environment": os.getenv("ENVIRONMENT", "production"),
            "cluster_name": os.getenv("CLUSTER_NAME", "dotmac-cluster"),
            "namespace": os.getenv("KUBERNETES_NAMESPACE", "default"),
            "version": os.getenv("APP_VERSION", "1.0.0"),
        }

        # Provision dashboards
        dashboard_results = await provision_platform_dashboards(
            platform_type=platform_type, tenant_id=tenant_id, custom_variables=custom_variables
        )

        # Store dashboard configs in app state
        app.state.dashboard_configs = dashboard_results

        logger.info("✅ Platform dashboards provisioned successfully")
        logger.info(f"   Platform: {platform_type}")
        logger.info(f"   Grafana dashboards: {len(dashboard_results.get('grafana_dashboards', []))}")
        logger.info(f"   Signoz dashboards: {len(dashboard_results.get('signoz_dashboards', []))}")
        logger.info(f"   Alert rules: {len(dashboard_results.get('alerts', []))}")

        return dashboard_results

    except ImportError:
        logger.warning("Dashboard manager not available, skipping dashboard setup")
        return {"status": "skipped", "reason": "Dashboard manager not available"}
    except Exception as e:
        logger.error(f"Dashboard setup failed: {e}")
        return {"status": "error", "error": str(e)}


def _get_platform_type(platform_config: PlatformConfig) -> str:
    """Determine platform type from configuration."""
    if not platform_config.deployment_context:
        return "development"

    mode = platform_config.deployment_context.mode

    if mode == DeploymentMode.MANAGEMENT_PLATFORM:
        return "management"
    elif mode == DeploymentMode.TENANT_CONTAINER:
        return "isp"
    else:
        return "development"


def _get_service_name_from_components(components: dict[str, Any]) -> str:
    """Extract service name from components."""
    if "otel_bootstrap" in components:
        otel_bootstrap = components["otel_bootstrap"]
        if hasattr(otel_bootstrap, "config") and hasattr(otel_bootstrap.config, "service_name"):
            return otel_bootstrap.config.service_name

    return "dotmac-service"
