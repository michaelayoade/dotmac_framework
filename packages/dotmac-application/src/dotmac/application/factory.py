"""
Main application factory for DotMac platforms.
Provider-based composition for decoupled architecture.
"""

import logging

from fastapi import FastAPI

from .config import (
    DeploymentContext,
    DeploymentMode,
    IsolationLevel,
    PlatformConfig,
    Providers,
    TenantConfig,
)
from .endpoints import StandardEndpoints
from .lifecycle import StandardLifecycleManager
from .middleware import apply_standard_middleware
from .routing import RouterRegistry

logger = logging.getLogger(__name__)


class DotMacApplicationFactory:
    """Unified application factory for all DotMac platforms."""

    def __init__(self):
        self.created_apps: dict[str, FastAPI] = {}

    def create_app(
        self, config: PlatformConfig, *, providers: Providers | None = None
    ) -> FastAPI:
        """Create a FastAPI application with standard DotMac configuration."""
        logger.info(f"Creating application: {config.title}")

        # Create FastAPI app with platform-specific settings
        app = self._create_fastapi_app(config)

        # Apply standard middleware stack with providers
        applied_middleware = apply_standard_middleware(
            app, config=config, providers=providers or config.middleware_providers
        )

        # Set up lifecycle management
        lifecycle_manager = StandardLifecycleManager(config)
        app.router.lifespan_context = lifecycle_manager.lifespan

        # Register routers
        router_registry = RouterRegistry(config)
        registration_stats = router_registry.register_all_routers(app)

        # Add standard endpoints
        standard_endpoints = StandardEndpoints(config)
        standard_endpoints.add_to_app(app)

        # Store configuration in app state
        app.state.platform_config = config
        app.state.registration_stats = registration_stats
        app.state.applied_middleware = applied_middleware

        # Track created app
        self.created_apps[config.platform_name] = app

        logger.info(f"✅ {config.title} application created successfully")
        logger.info(
            f"   Routers: {registration_stats['successfully_registered']}/{registration_stats['total_attempted']}"
        )
        logger.info(f"   Middleware: {len(applied_middleware)} components applied")
        logger.info("   Health checks: Enabled")

        return app

    def _create_fastapi_app(self, config: PlatformConfig) -> FastAPI:
        """Create the base FastAPI application."""
        # Prepare FastAPI kwargs
        fastapi_kwargs = {
            "title": config.title,
            "description": config.description,
            "version": config.version,
            **config.fastapi_kwargs,
        }

        # Set docs URLs based on deployment mode
        if config.deployment_context:
            if config.deployment_context.mode == DeploymentMode.TENANT_CONTAINER:
                # Disable docs in tenant containers for security
                fastapi_kwargs.update(
                    {"docs_url": None, "redoc_url": None, "openapi_url": None}
                )
            elif config.deployment_context.mode == DeploymentMode.DEVELOPMENT:
                # Enable docs in development
                fastapi_kwargs.update(
                    {
                        "docs_url": "/docs",
                        "redoc_url": "/redoc",
                        "openapi_url": "/openapi.json",
                    }
                )

        return FastAPI(**fastapi_kwargs)

    def get_app(self, platform_name: str) -> FastAPI | None:
        """Get a previously created app by platform name."""
        return self.created_apps.get(platform_name)

    def list_created_apps(self) -> dict[str, str]:
        """List all created applications."""
        return {name: app.title for name, app in self.created_apps.items()}


class DeploymentAwareApplicationFactory(DotMacApplicationFactory):
    """Enhanced factory with deployment-specific optimizations."""

    def create_tenant_container_app(
        self,
        tenant_config: TenantConfig,
        base_config: PlatformConfig,
        *,
        providers: Providers | None = None,
    ) -> FastAPI:
        """Create ISP Framework instance optimized for tenant container deployment."""
        logger.info(
            f"Creating tenant container app for tenant: {tenant_config.tenant_id}"
        )

        # Create deployment-aware configuration
        deployment_context = tenant_config.deployment_context
        platform_config = tenant_config.to_platform_config(base_config)

        # Apply container-specific optimizations
        self._apply_container_optimizations(platform_config, tenant_config)

        # Create the application with providers
        app = self.create_app(platform_config, providers=providers)

        # Add tenant-specific state
        app.state.tenant_id = tenant_config.tenant_id
        app.state.tenant_config = tenant_config
        app.state.isolation_level = deployment_context.isolation_level

        logger.info(f"✅ Tenant container app created for {tenant_config.tenant_id}")

        return app

    def create_management_platform_app(
        self, config: PlatformConfig, *, providers: Providers | None = None
    ) -> FastAPI:
        """Create Management Platform optimized for tenant orchestration."""
        logger.info("Creating Management Platform application")

        # Set deployment context for management platform
        deployment_context = DeploymentContext(
            mode=DeploymentMode.MANAGEMENT_PLATFORM,
            isolation_level="none",  # Management platform doesn't need tenant isolation
        )

        platform_config = config.customize_for_deployment(deployment_context)

        # Apply management platform optimizations
        self._apply_management_platform_optimizations(platform_config)

        # Create the application with providers
        app = self.create_app(platform_config, providers=providers)

        # Add management-specific state
        app.state.manages_tenants = True
        app.state.deployment_mode = DeploymentMode.MANAGEMENT_PLATFORM

        logger.info("✅ Management Platform application created")

        return app

    def _apply_container_optimizations(
        self, platform_config: PlatformConfig, tenant_config: TenantConfig
    ):
        """Apply optimizations for container deployment."""
        # Resource-aware configurations
        if tenant_config.deployment_context.resource_limits:
            limits = tenant_config.deployment_context.resource_limits

            # Adjust observability based on resources
            if limits.memory_limit.endswith("Mi"):
                memory_mb = int(limits.memory_limit[:-2])
                if memory_mb < 1024:  # Less than 1GB
                    platform_config.observability_config.tier = "minimal"
                    platform_config.observability_config.tracing_enabled = False

            # Adjust connection limits
            platform_config.custom_settings["max_connections"] = limits.max_connections
            platform_config.custom_settings[
                "max_concurrent_requests"
            ] = limits.max_concurrent_requests

        # Security optimizations for tenant containers
        platform_config.security_config.tenant_isolation = True
        platform_config.security_config.api_security_suite = True

        # Disable unnecessary features in containers
        platform_config.custom_settings["disable_admin_docs"] = True
        platform_config.custom_settings["minimal_logging"] = True

    def _apply_management_platform_optimizations(self, platform_config: PlatformConfig):
        """Apply optimizations for management platform."""
        # Enhanced observability for platform monitoring
        platform_config.observability_config.tier = "comprehensive"
        platform_config.observability_config.custom_metrics = [
            "tenant_container_count",
            "partner_connection_count",
            "deployment_success_rate",
        ]

        # Management-specific health checks
        platform_config.health_config.enabled_checks.extend(
            ["kubernetes_connectivity", "tenant_containers", "websocket_connections"]
        )

        # Enable full API documentation for management platform
        platform_config.custom_settings["enable_admin_docs"] = True
        platform_config.custom_settings["comprehensive_logging"] = True


# Convenience functions for common app creation patterns
def create_app(
    config: PlatformConfig, *, providers: Providers | None = None
) -> FastAPI:
    """Create a standard DotMac application."""
    factory = DotMacApplicationFactory()
    return factory.create_app(config, providers=providers)


def create_management_platform_app(
    config: PlatformConfig | None = None, *, providers: Providers | None = None
) -> FastAPI:
    """Create a management platform application with defaults."""
    if config is None:
        config = _create_default_management_config()

    factory = DeploymentAwareApplicationFactory()
    return factory.create_management_platform_app(config, providers=providers)


def create_isp_framework_app(
    tenant_config: TenantConfig | None = None,
    base_config: PlatformConfig | None = None,
    *,
    providers: Providers | None = None,
) -> FastAPI:
    """Create an ISP framework application."""
    if base_config is None:
        base_config = _create_default_isp_config()

    factory = DeploymentAwareApplicationFactory()

    if tenant_config is not None:
        return factory.create_tenant_container_app(
            tenant_config, base_config, providers=providers
        )
    else:
        # Create standalone ISP framework app
        deployment_context = DeploymentContext(
            mode=DeploymentMode.STANDALONE, isolation_level=IsolationLevel.NONE
        )
        config = base_config.customize_for_deployment(deployment_context)
        return factory.create_app(config, providers=providers)


def _create_default_management_config() -> PlatformConfig:
    """Create default Management Platform configuration."""
    from .config import HealthCheckConfig, ObservabilityConfig, RouterConfig

    return PlatformConfig(
        platform_name="management_platform",
        title="DotMac Multi-App Management Platform",
        description="Multi-app SaaS platform for managing tenant organizations with multiple applications",
        routers=[
            RouterConfig("dotmac_management.modules", "/api/v1", auto_discover=True),
            RouterConfig(
                "dotmac_management.api_new.websocket", "/api/ws", required=False
            ),
            RouterConfig(
                "dotmac_management.api_new.files", "/api/files", required=False
            ),
            RouterConfig(
                "dotmac_management.api_new.security", "/api/security", required=False
            ),
        ],
        startup_tasks=[
            "initialize_plugin_system",
            "start_tenant_monitoring",
            "configure_kubernetes_client",
        ],
        health_config=HealthCheckConfig(
            enabled_checks=[
                "database",
                "cache",
                "kubernetes_connectivity",
                "tenant_containers",
                "websocket_connections",
            ]
        ),
        observability_config=ObservabilityConfig(
            tier="comprehensive",
            custom_metrics=[
                "tenant_container_count",
                "partner_connection_count",
                "deployment_success_rate",
            ],
        ),
    )


def _create_default_isp_config() -> PlatformConfig:
    """Create default ISP Framework configuration."""
    from .config import HealthCheckConfig, RouterConfig

    return PlatformConfig(
        platform_name="isp_framework",
        title="DotMac ISP Framework",
        description="Comprehensive ISP management system",
        routers=[
            RouterConfig("dotmac_isp.modules", "/api/v1", auto_discover=True),
            RouterConfig("dotmac_isp.portals", "/api/v1", auto_discover=True),
            RouterConfig(
                "dotmac_isp.api.security_endpoints", "/api/v1/security", required=False
            ),
            RouterConfig("dotmac_isp.api.websocket_router", "/api/ws", required=False),
            RouterConfig("dotmac_isp.api.file_router", "/api/files", required=False),
        ],
        startup_tasks=[
            "initialize_ssl_manager",
            "start_celery_monitoring",
            "configure_tenant_isolation",
        ],
        health_config=HealthCheckConfig(
            enabled_checks=["database", "cache", "celery", "ssl_certificates"]
        ),
    )
