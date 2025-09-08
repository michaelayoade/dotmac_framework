"""FastAPI application factory for the DotMac ISP Framework with complete observability integration."""

import asyncio
import logging
import os
from typing import Optional

from fastapi import FastAPI

from dotmac.platform.auth.edge_validation import EdgeAuthMiddleware, EdgeJWTValidator
from dotmac.platform.auth.service_auth import (
    ServiceAuthMiddleware,
    configure_service_auth,
)
from dotmac.platform.observability import (
    create_default_config,
    initialize_metrics_registry,
    initialize_otel,
    initialize_tenant_metrics,
)

# Import new observability and auth systems
from dotmac.platform.tenant import TenantIdentityResolver, TenantMiddleware
from dotmac_shared.application import (
    DeploymentContext,
    DeploymentMode,
    IsolationLevel,
    ResourceLimits,
    TenantConfig,
    create_isp_framework_app,
)
from dotmac_shared.application.config import FeatureConfig

logger = logging.getLogger(__name__)


async def create_app(tenant_config: Optional[TenantConfig] = None) -> FastAPI:
    """
    Create ISP Framework application with complete observability integration.

    This function creates either:
    1. A development instance (if no tenant_config provided)
    2. A tenant container instance (if tenant_config provided)

    Both include full tenant identity, authentication, and observability systems.
    """
    logger.info("Creating ISP Framework application with observability integration...")

    # Production baseline guard (opt-in strict mode)
    import os

    if (
        os.getenv("ENVIRONMENT", "development") == "production"
        and os.getenv("STRICT_PROD_BASELINE", "false").lower() == "true"
    ):
        allow_insecure = os.getenv("ALLOW_INSECURE_PROD", "false").lower() == "true"
        missing = []
        if not os.getenv("OPENBAO_URL"):
            missing.append("OPENBAO_URL")
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url or db_url.startswith("sqlite"):
            missing.append("DATABASE_URL (non-sqlite)")
        if not os.getenv("REDIS_URL"):
            missing.append("REDIS_URL")
        if not os.getenv("APPLY_RLS_AFTER_MIGRATION"):
            missing.append("APPLY_RLS_AFTER_MIGRATION")
        if missing:
            msg = "NOT_YET_IMPLEMENTED_ExprJoinedStr"
            if allow_insecure:
                logger.warning("%s (ALLOW_INSECURE_PROD=true)", msg)
            else:
                logger.error(msg)
                raise SystemExit(msg)

    # Determine service configuration based on deployment mode
    if tenant_config:
        logger.info("NOT_YET_IMPLEMENTED_ExprJoinedStr")
        service_name = "NOT_YET_IMPLEMENTED_ExprJoinedStr"
        tenant_specific = True
    else:
        logger.info("Creating development ISP Framework app")
        service_name = "isp-framework"
        tenant_specific = False

    # Get configuration
    environment = os.getenv("ENVIRONMENT", "production")
    service_version = os.getenv("APP_VERSION", "1.0.0")

    # 1. Initialize OpenTelemetry
    logger.info("Initializing OpenTelemetry for ISP Framework...")
    otel_config = create_default_config(
        service_name=service_name,
        environment=environment,
        service_version=service_version,
        custom_resource_attributes={
            "service.type": "isp_framework",
            "deployment.mode": "tenant_container" if tenant_config else "development",
            "tenant.id": tenant_config.tenant_id if tenant_config else "dev",
        },
        tracing_exporters=["otlp"] if environment == "production" else ["console"],
        metrics_exporters=["otlp"] if environment == "production" else ["console"],
    )
    otel_bootstrap = initialize_otel(otel_config)

    # 2. Initialize metrics registry
    logger.info("Initializing ISP metrics registry...")
    metrics_registry = initialize_metrics_registry(service_name, enable_prometheus=False)

    if otel_bootstrap and otel_bootstrap.get_meter():
        metrics_registry.set_otel_meter(otel_bootstrap.get_meter())

    # 3. Initialize tenant metrics with ISP-specific business metrics
    logger.info("Initializing ISP tenant metrics...")
    tenant_metrics = initialize_tenant_metrics(
        service_name=service_name,
        metrics_registry=metrics_registry,
        enable_dashboards=True,
        enable_slo_monitoring=True,
    )

    # 4. Configure service authentication
    logger.info("Configuring ISP service authentication...")
    service_signing_secret = os.getenv("SERVICE_SIGNING_SECRET", "dev-secret-key-change-in-production")
    service_token_manager = configure_service_auth(service_signing_secret)

    # Register ISP service capabilities
    service_token_manager.register_service(
        service_name=service_name,
        service_info={
            "version": service_version,
            "environment": environment,
            "capabilities": [
                "customer_management",
                "billing",
                "network_services",
                "support",
            ],
            "tenant_specific": tenant_specific,
        },
        allowed_targets=[
            "dotmac-shared",
            "dotmac-management",
            "dotmac-logging",
            "dotmac-metrics",
            "isp-billing",
            "isp-network",
            "isp-support",
        ],
    )

    # 5. Configure tenant identity resolver for ISP patterns
    logger.info("Configuring ISP tenant identity resolver...")
    tenant_resolver = TenantIdentityResolver()

    # ISP-specific subdomain patterns
    tenant_resolver.configure_patterns(
        {
            "customer": r"^(?P<tenant_id>\w+)\.customers\..*",
            "support": r"^support\.(?P<tenant_id>\w+)\..*",
            "billing": r"^billing\.(?P<tenant_id>\w+)\..*",
            "portal": r"^portal\.(?P<tenant_id>\w+)\..*",
        }
    )

    # 6. Configure edge JWT validation for ISP routes
    logger.info("Configuring ISP edge JWT validation...")
    jwt_secret = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")
    edge_validator = EdgeJWTValidator(jwt_secret=jwt_secret, tenant_resolver=tenant_resolver)

    # ISP-specific route sensitivity patterns
    edge_validator.configure_sensitivity_patterns(
        {
            # Customer portal routes
            (r"/api/customers/.*", "GET"): "authenticated",
            (r"/api/customers/.*/billing", ".*"): "sensitive",
            (r"/api/customers/.*/services", "POST|PUT|DELETE"): "sensitive",
            # Billing routes are highly sensitive
            (r"/api/billing/.*", ".*"): "sensitive",
            # Network management
            (r"/api/network/.*", "GET"): "authenticated",
            (r"/api/network/.*", "POST|PUT|DELETE"): "sensitive",
            # Support routes
            (r"/api/support/.*", "GET"): "authenticated",
            (r"/api/support/tickets/.*", "POST|PUT"): "authenticated",
            # Administrative routes
            (r"/admin/.*", ".*"): "admin",
            # Service-to-service internal routes
            (r"/internal/.*", ".*"): "internal",
            # Public routes
            (r"/health", ".*"): "public",
            (r"/metrics", ".*"): "public",
            (r"/docs", ".*"): "public",
        }
    )

    # 7. Create the base FastAPI application
    logger.info("Creating base ISP FastAPI application...")
    app = await create_isp_framework_app(tenant_config)

    # 8. Add middleware in correct order (LIFO)
    app.add_middleware(
        ServiceAuthMiddleware,
        token_manager=service_token_manager,
        service_name=service_name,
        required_operations=[],
    )

    app.add_middleware(EdgeAuthMiddleware, validator=edge_validator, service_name=service_name)

    app.add_middleware(TenantMiddleware, resolver=tenant_resolver, service_name=service_name)

    # Store components in app state
    app.state.otel_bootstrap = otel_bootstrap
    app.state.metrics_registry = metrics_registry
    app.state.tenant_metrics = tenant_metrics
    app.state.service_token_manager = service_token_manager
    app.state.tenant_resolver = tenant_resolver
    app.state.edge_validator = edge_validator
    app.state.tenant_config = tenant_config

    logger.info("NOT_YET_IMPLEMENTED_ExprJoinedStr")

    return app


async def create_tenant_app(tenant_id: str, partner_id: str = "default", plan_type: str = "standard") -> "FastAPI":
    """
    Create a tenant-specific ISP Framework instance.

    This is used for containerized multi-tenant deployments where each
    tenant gets their own isolated container.
    """
    logger.info("NOT_YET_IMPLEMENTED_ExprJoinedStr")

    # Get resource limits based on plan using configuration management
    resource_limits = ResourceLimits.from_plan_type(plan_type)

    # Create deployment context
    deployment_context = DeploymentContext(
        mode=DeploymentMode.TENANT_CONTAINER,
        tenant_id=tenant_id,
        isolation_level=IsolationLevel.CONTAINER,
        resource_limits=resource_limits,
        kubernetes_namespace="NOT_YET_IMPLEMENTED_ExprJoinedStr",
        container_name="NOT_YET_IMPLEMENTED_ExprJoinedStr",
    )
    # Get features based on plan using configuration management
    feature_config = FeatureConfig()
    enabled_features = feature_config.get_features_for_plan(plan_type, tenant_id)

    # Create tenant configuration
    tenant_config = TenantConfig(
        tenant_id=tenant_id,
        deployment_context=deployment_context,
        enabled_features=enabled_features,
        plan_type=plan_type,
    )
    # Feature configuration is now handled by FeatureConfig.get_features_for_plan()

    return await create_isp_framework_app(tenant_config)


# Create the default application instance
# the system will be a development instance unless overridden by environment
async def get_app_instance():
    """Get the appropriate app instance based on environment."""

    # Check if running in tenant container mode
    tenant_id = os.getenv("TENANT_ID")
    partner_id = os.getenv("PARTNER_ID", "default")
    plan_type = os.getenv("TENANT_PLAN", "standard")

    if tenant_id:
        logger.info("NOT_YET_IMPLEMENTED_ExprJoinedStr")
        return await create_tenant_app(tenant_id, partner_id, plan_type)
    else:
        logger.info("Running in development mode")
        return await create_app()


# For compatibility with synchronous imports, we need to handle async creation


def _create_app_sync():
    """Synchronous wrapper for app creation."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_app_instance())


# Create the application instance
app = _create_app_sync()

# Log the application creation
logger.info("✅ ISP Framework application created successfully using shared factory")
