"""
Main application factory for DotMac platforms.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI

from ..services import DeploymentAwareServiceFactory, ServiceRegistry
from .config import DeploymentContext, DeploymentMode, PlatformConfig, TenantConfig
from .endpoints import StandardEndpoints
from .lifecycle import StandardLifecycleManager
from .middleware import StandardMiddlewareStack
from .routing import RouterRegistry

logger = logging.getLogger(__name__)


class DotMacApplicationFactory:
    """Unified application factory for all DotMac platforms."""

    def __init__(self):
        self.created_apps: Dict[str, FastAPI] = {}

    async def create_app(self, config: PlatformConfig) -> FastAPI:
        """Create a FastAPI application with standard DotMac configuration."""
        logger.info(f"Creating application: {config.title}")

        # Create FastAPI app with platform-specific settings
        app = self._create_fastapi_app(config)

        # Create and configure service registry
        service_factory = DeploymentAwareServiceFactory(config.deployment_context)
        service_registry = await service_factory.create_service_registry()

        # Store service registry in app state
        app.state.services = service_registry

        # Apply standard middleware stack
        middleware_stack = StandardMiddlewareStack(config)
        middleware_stack.apply_to_app(app)

        # Set up lifecycle management with service integration
        lifecycle_manager = StandardLifecycleManager(config, service_registry)
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

        # Track created app
        self.created_apps[config.platform_name] = app

        logger.info(f"✅ {config.title} application created successfully")
        logger.info(
            f"   Routers: {registration_stats['successfully_registered']}/{registration_stats['total_attempted']}"
        )
        logger.info(f"   Middleware: Applied standard stack")
        logger.info(
            f"   Services: {len(service_registry.get_ready_services())} services ready"
        )
        logger.info(f"   Health checks: Enabled")

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

    def get_app(self, platform_name: str) -> FastAPI:
        """Get a previously created app by platform name."""
        return self.created_apps.get(platform_name)

    def list_created_apps(self) -> Dict[str, str]:
        """List all created applications."""
        return {name: app.title for name, app in self.created_apps.items()}


class DeploymentAwareApplicationFactory(DotMacApplicationFactory):
    """Enhanced factory with deployment-specific optimizations."""

    async def create_tenant_container_app(
        self, tenant_config: TenantConfig, base_config: PlatformConfig
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

        # Create the application with service integration
        app = await self.create_app(platform_config)

        # Add tenant-specific state
        app.state.tenant_id = tenant_config.tenant_id
        app.state.tenant_config = tenant_config
        app.state.isolation_level = deployment_context.isolation_level

        logger.info(f"✅ Tenant container app created for {tenant_config.tenant_id}")

        return app

    async def create_management_platform_app(self, config: PlatformConfig) -> FastAPI:
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

        # Create the application with service integration
        app = await self.create_app(platform_config)

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
            platform_config.custom_settings["max_concurrent_requests"] = (
                limits.max_concurrent_requests
            )

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
        platform_config.observability_config.custom_metrics.extend(
            [
                "active_tenant_containers",
                "container_provisioning_rate",
                "platform_resource_usage",
            ]
        )

        # Management-specific health checks
        platform_config.health_config.enabled_checks.extend(
            ["kubernetes_api", "container_registry", "tenant_health_aggregate"]
        )

        # Enable advanced features
        platform_config.custom_settings["enable_container_management"] = True
        platform_config.custom_settings["enable_partner_portal"] = True
        platform_config.custom_settings["enable_billing_automation"] = True

    async def create_development_app(self, config: PlatformConfig) -> FastAPI:
        """Create application optimized for development."""
        logger.info("Creating development application")

        deployment_context = DeploymentContext(
            mode=DeploymentMode.DEVELOPMENT, isolation_level="none"
        )

        platform_config = config.customize_for_deployment(deployment_context)

        # Development optimizations
        platform_config.fastapi_kwargs.update(
            {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
        )

        # Relaxed security for development
        platform_config.security_config.csrf_enabled = False
        platform_config.security_config.rate_limiting_enabled = False

        # Enhanced logging for development
        platform_config.observability_config.logging_level = "DEBUG"

        app = await self.create_app(platform_config)
        app.state.development_mode = True

        logger.info("✅ Development application created")
        return app


# Global factory instances
application_factory = DotMacApplicationFactory()
deployment_aware_factory = DeploymentAwareApplicationFactory()


async def create_isp_framework_app(
    tenant_config: Optional[TenantConfig] = None,
) -> FastAPI:
    """Convenience function to create ISP Framework application."""
    from .config import create_isp_platform_config

    base_config = create_isp_platform_config()

    if tenant_config:
        return await deployment_aware_factory.create_tenant_container_app(
            tenant_config, base_config
        )
    else:
        return await deployment_aware_factory.create_development_app(base_config)


async def create_management_platform_app() -> FastAPI:
    """Convenience function to create Management Platform application."""
    from .config import create_management_platform_config

    config = create_management_platform_config()
    return await deployment_aware_factory.create_management_platform_app(config)
