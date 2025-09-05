"""
Infrastructure Service
High-level service layer that integrates infrastructure plugins with business logic
"""

from datetime import datetime, timezone
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger

from dotmac.application import standard_exception_handler

from ..core.plugins.base import PluginError
from ..core.plugins.infrastructure_manager import InfrastructurePluginManager
from ..core.plugins.registry import PluginRegistry

logger = get_logger(__name__)


class InfrastructureService:
    """
    Service layer for infrastructure operations using plugins.
    Provides a clean interface between business logic and infrastructure providers.
    """

    def __init__(self):
        self.plugin_registry = PluginRegistry()
        self.infrastructure_manager = InfrastructurePluginManager(self.plugin_registry)
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the infrastructure service."""
        try:
            if self._initialized:
                return True

            # Initialize plugin registry and infrastructure manager
            if not await self.infrastructure_manager.initialize():
                raise Exception("Failed to initialize infrastructure manager")

            self._initialized = True
            logger.info("✅ Infrastructure service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize infrastructure service: {e}")
            return False

    @standard_exception_handler
    async def get_health_status(self) -> dict[str, Any]:
        """Get health status of all infrastructure providers."""
        if not self._initialized:
            return {
                "healthy": False,
                "error": "Service not initialized",
                "providers": {},
            }

        health_data = await self.infrastructure_manager.get_provider_health()

        return {
            "healthy": health_data.get("overall_healthy", False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "providers": {
                "deployment": health_data.get("deployment_providers", {}),
                "dns": health_data.get("dns_providers", {}),
            },
        }

    # Deployment Operations (replaces CoolifyClient usage)

    @standard_exception_handler
    async def deploy_tenant_application(
        self, tenant_config: dict[str, Any], provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Deploy tenant application using infrastructure plugins.
        Replaces direct CoolifyClient usage in tenant provisioning.
        """
        logger.info(
            f"Deploying tenant application: {tenant_config.get('name', 'unnamed')}"
        )

        # Convert tenant config to deployment config
        app_config = self._convert_tenant_to_app_config(tenant_config)

        # Deploy using infrastructure manager
        result = await self.infrastructure_manager.deploy_application(
            app_config, provider_name
        )

        # Add tenant-specific metadata
        result["tenant_id"] = tenant_config.get("tenant_id")
        result["tenant_name"] = tenant_config.get("name")
        result["deployment_type"] = "tenant_application"

        logger.info(f"✅ Tenant application deployed: {result.get('deployment_id')}")
        return result

    @standard_exception_handler
    async def create_database_service(
        self, db_config: dict[str, Any], provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Create database service using deployment provider."""
        provider = self.infrastructure_manager.get_deployment_provider(provider_name)

        if not provider:
            raise PluginError("No deployment provider available for database creation")

        # Check if provider has database creation method (Coolify-specific)
        if hasattr(provider, "create_database_service"):
            return await provider.create_database_service(db_config)
        else:
            # Generic database deployment via application deployment
            app_config = self._convert_db_to_app_config(db_config)
            return await self.infrastructure_manager.deploy_application(
                app_config, provider_name
            )

    @standard_exception_handler
    async def create_redis_service(
        self, redis_config: dict[str, Any], provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Create Redis service using deployment provider."""
        provider = self.infrastructure_manager.get_deployment_provider(provider_name)

        if not provider:
            raise PluginError("No deployment provider available for Redis creation")

        # Check if provider has Redis creation method (Coolify-specific)
        if hasattr(provider, "create_redis_service"):
            return await provider.create_redis_service(redis_config)
        else:
            # Generic Redis deployment via application deployment
            app_config = self._convert_redis_to_app_config(redis_config)
            return await self.infrastructure_manager.deploy_application(
                app_config, provider_name
            )

    @standard_exception_handler
    async def get_deployment_status(
        self, deployment_id: str, provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Get deployment status from infrastructure provider."""
        return await self.infrastructure_manager.get_deployment_status(
            deployment_id, provider_name
        )

    @standard_exception_handler
    async def set_application_domain(
        self, deployment_id: str, domain: str, provider_name: Optional[str] = None
    ) -> bool:
        """Set domain for deployed application."""
        provider = self.infrastructure_manager.get_deployment_provider(provider_name)

        if not provider:
            raise PluginError("No deployment provider available")

        # Check if provider has domain setting method (Coolify-specific)
        if hasattr(provider, "set_domain"):
            return await provider.set_domain(deployment_id, domain)
        else:
            logger.warning(
                f"Provider {provider.meta.name} does not support domain setting"
            )
            return False

    # DNS Operations (replaces DNSValidator usage)

    @standard_exception_handler
    async def validate_subdomain_availability(
        self,
        subdomain: str,
        base_domain: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Validate subdomain availability using DNS plugins.
        Replaces direct DNSValidator usage in tenant provisioning.
        """
        logger.info(f"Validating subdomain availability: {subdomain}")

        result = await self.infrastructure_manager.validate_subdomain(
            subdomain, base_domain, provider_name
        )

        # Add service-level metadata
        result["validation_timestamp"] = datetime.now(timezone.utc).isoformat()
        result["provider_used"] = provider_name or "default"

        status = "available" if result.get("available", False) else "unavailable"
        logger.info(f"Subdomain validation result: {subdomain} is {status}")

        return result

    @standard_exception_handler
    async def validate_ssl_certificate(
        self, domain: str, provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Validate SSL certificate for domain."""
        logger.info(f"Validating SSL certificate for: {domain}")

        result = await self.infrastructure_manager.validate_ssl_certificate(
            domain, provider_name
        )

        # Add service-level metadata
        result["validation_timestamp"] = datetime.now(timezone.utc).isoformat()
        result["provider_used"] = provider_name or "default"

        status = "valid" if result.get("valid", False) else "invalid"
        logger.info(f"SSL validation result: {domain} certificate is {status}")

        return result

    @standard_exception_handler
    async def check_dns_propagation(
        self,
        domain: str,
        expected_value: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Check DNS propagation status."""
        provider = self.infrastructure_manager.get_dns_provider(provider_name)

        if not provider:
            raise PluginError("No DNS provider available")

        result = await provider.check_dns_propagation(domain, expected_value)

        # Add service-level metadata
        result["check_timestamp"] = datetime.now(timezone.utc).isoformat()
        result["provider_used"] = provider_name or "default"

        return result

    # Utility Methods

    def _convert_tenant_to_app_config(
        self, tenant_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert tenant configuration to application deployment configuration."""
        return {
            "name": tenant_config.get(
                "name", f"tenant-{tenant_config.get('tenant_id', 'unknown')}"
            ),
            "description": f"Tenant application for {tenant_config.get('name', 'Unknown')}",
            "docker_compose": tenant_config.get("docker_compose", ""),
            "environment": tenant_config.get("environment_variables", {}),
            "domains": tenant_config.get("domains", []),
            "tenant_id": tenant_config.get("tenant_id"),
            "tenant_metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "provisioning_type": "automated",
            },
        }

    def _convert_db_to_app_config(self, db_config: dict[str, Any]) -> dict[str, Any]:
        """Convert database config to application deployment configuration."""
        db_type = db_config.get("type", "postgresql")
        version = db_config.get(
            "version", "15" if db_type == "postgresql" else "latest"
        )

        # Generate docker-compose for database
        docker_compose = f"""
version: '3.8'
services:
  {db_config['name']}:
    image: {db_type}:{version}
    environment:
      POSTGRES_DB: {db_config['database']}
      POSTGRES_USER: {db_config['username']}
      POSTGRES_PASSWORD: {db_config['password']}
    volumes:
      - {db_config['name']}_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  {db_config['name']}_data:
"""

        return {
            "name": db_config["name"],
            "description": f"Database service: {db_type}",
            "docker_compose": docker_compose.strip(),
            "environment": {
                "POSTGRES_DB": db_config["database"],
                "POSTGRES_USER": db_config["username"],
                "POSTGRES_PASSWORD": db_config["password"],
            },
            "service_type": "database",
            "database_type": db_type,
        }

    def _convert_redis_to_app_config(
        self, redis_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert Redis config to application deployment configuration."""
        version = redis_config.get("version", "7")

        # Generate docker-compose for Redis
        docker_compose = f"""
version: '3.8'
services:
  {redis_config['name']}:
    image: redis:{version}
    command: redis-server --requirepass {redis_config.get('password', '')}
    volumes:
      - {redis_config['name']}_data:/data
    ports:
      - "6379:6379"

volumes:
  {redis_config['name']}_data:
"""

        return {
            "name": redis_config["name"],
            "description": "Redis cache service",
            "docker_compose": docker_compose.strip(),
            "environment": {"REDIS_PASSWORD": redis_config.get("password", "")},
            "service_type": "cache",
            "cache_type": "redis",
        }

    # Provider Management

    def list_available_providers(self) -> dict[str, list[str]]:
        """List all available infrastructure providers."""
        return {
            "deployment_providers": self.infrastructure_manager.list_deployment_providers(),
            "dns_providers": self.infrastructure_manager.list_dns_providers(),
        }

    @standard_exception_handler
    async def register_custom_provider(
        self,
        provider_type: str,
        provider_name: str,
        plugin_class: type,
        config: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Register a custom infrastructure provider plugin."""
        try:
            plugin_instance = plugin_class(config or {})

            if provider_type == "deployment":
                return await self.infrastructure_manager.register_deployment_provider(
                    provider_name, plugin_instance
                )
            elif provider_type == "dns":
                return await self.infrastructure_manager.register_dns_provider(
                    provider_name, plugin_instance
                )
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")

        except Exception as e:
            logger.error(f"Failed to register custom provider {provider_name}: {e}")
            return False

    async def shutdown(self):
        """Shutdown the infrastructure service."""
        logger.info("Shutting down infrastructure service...")

        if self._initialized:
            await self.infrastructure_manager.shutdown()
            self._initialized = False

        logger.info("✅ Infrastructure service shutdown complete")


# Global infrastructure service instance
_infrastructure_service: Optional[InfrastructureService] = None


async def get_infrastructure_service() -> InfrastructureService:
    """Get or create the global infrastructure service instance."""
    global _infrastructure_service

    if _infrastructure_service is None:
        _infrastructure_service = InfrastructureService()
        await _infrastructure_service.initialize()

    return _infrastructure_service
