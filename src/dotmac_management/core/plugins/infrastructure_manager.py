"""
Infrastructure Plugin Manager
Manages infrastructure provider plugins and provides service discovery
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional, TypeVar

from dotmac_shared.exceptions import ExceptionContext

from dotmac.application import standard_exception_handler

from .base import PluginError
from .health_monitor import PluginHealthMonitor
from .interfaces import (
    DeploymentProviderPlugin,
    DNSProviderPlugin,
    InfrastructureProviderPlugin,
)
from .registry import PluginRegistry

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="InfrastructureProviderPlugin")


class InfrastructurePluginManager:
    """
    Manages infrastructure provider plugins and provides service discovery.
    Provides high-level interface for infrastructure operations.
    """

    def __init__(self, plugin_registry: PluginRegistry):
        self.registry = plugin_registry
        self._deployment_providers: dict[str, DeploymentProviderPlugin] = {}
        self._dns_providers: dict[str, DNSProviderPlugin] = {}
        self._infrastructure_providers: dict[str, InfrastructureProviderPlugin] = {}
        self._lock = asyncio.Lock()
        self.health_monitor = PluginHealthMonitor(self)

    async def initialize(self) -> bool:
        """Initialize the infrastructure plugin manager."""
        try:
            # Load default infrastructure plugins
            await self._load_default_plugins()

            # Start health monitoring
            await self.health_monitor.start_monitoring(
                check_interval=120
            )  # Check every 2 minutes

            logger.info("✅ Infrastructure plugin manager initialized successfully")
            return True

        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            logger.error(f"Failed to initialize infrastructure plugin manager: {e}")
            return False

    async def _load_default_plugins(self):
        """Load default infrastructure plugins."""
        try:
            # Import and register default plugins
            from ...plugins.infrastructure import (
                CoolifyDeploymentPlugin,
                StandardDNSProviderPlugin,
            )

            # Register Coolify deployment plugin
            coolify_config = {
                "base_url": "http://localhost:8000",  # Default, can be overridden
                "project_id": "default",
            }
            coolify_plugin = CoolifyDeploymentPlugin(coolify_config)
            await self.register_deployment_provider("coolify", coolify_plugin)

            # Register standard DNS provider plugin
            dns_config = {}  # Will use environment variables
            dns_plugin = StandardDNSProviderPlugin(dns_config)
            await self.register_dns_provider("standard", dns_plugin)

            logger.info("Default infrastructure plugins loaded successfully")

        except (ImportError, AttributeError, PluginError, ValueError, TypeError) as e:
            logger.error(f"Failed to load default plugins: {e}")
            raise

    @standard_exception_handler
    async def register_deployment_provider(
        self, provider_name: str, plugin: DeploymentProviderPlugin
    ) -> bool:
        """Register a deployment provider plugin."""
        async with self._lock:
            try:
                # Initialize the plugin
                if not await plugin.initialize():
                    raise PluginError(
                        f"Failed to initialize deployment provider: {provider_name}"
                    )

                # Register with main registry
                if not await self.registry.register_plugin(plugin):
                    raise PluginError(
                        f"Failed to register plugin with main registry: {provider_name}"
                    )

                # Store in local registry
                self._deployment_providers[provider_name] = plugin

                logger.info(f"✅ Registered deployment provider: {provider_name}")
                return True

            except (PluginError, AttributeError, TypeError, ValueError) as e:
                logger.error(
                    f"Failed to register deployment provider {provider_name}: {e}"
                )
                return False

    @standard_exception_handler
    async def register_dns_provider(
        self, provider_name: str, plugin: DNSProviderPlugin
    ) -> bool:
        """Register a DNS provider plugin."""
        async with self._lock:
            try:
                # Initialize the plugin
                if not await plugin.initialize():
                    raise PluginError(
                        f"Failed to initialize DNS provider: {provider_name}"
                    )

                # Register with main registry
                if not await self.registry.register_plugin(plugin):
                    raise PluginError(
                        f"Failed to register plugin with main registry: {provider_name}"
                    )

                # Store in local registry
                self._dns_providers[provider_name] = plugin

                logger.info(f"✅ Registered DNS provider: {provider_name}")
                return True

            except (PluginError, AttributeError, TypeError, ValueError) as e:
                logger.error(f"Failed to register DNS provider {provider_name}: {e}")
                return False

    # Service Discovery Methods

    def get_deployment_provider(
        self, provider_name: Optional[str] = None
    ) -> Optional[DeploymentProviderPlugin]:
        """Get deployment provider by name, or default if none specified."""
        if provider_name:
            return self._deployment_providers.get(provider_name)

        # Return first available provider as default
        if self._deployment_providers:
            return list(self._deployment_providers.values())[0]

        return None

    def get_dns_provider(
        self, provider_name: Optional[str] = None
    ) -> Optional[DNSProviderPlugin]:
        """Get DNS provider by name, or default if none specified."""
        if provider_name:
            return self._dns_providers.get(provider_name)

        # Return first available provider as default
        if self._dns_providers:
            return list(self._dns_providers.values())[0]

        return None

    def list_deployment_providers(self) -> list[str]:
        """List all registered deployment providers."""
        return list(self._deployment_providers.keys())

    def list_dns_providers(self) -> list[str]:
        """List all registered DNS providers."""
        return list(self._dns_providers.keys())

    @standard_exception_handler
    async def get_provider_health(self, detailed: bool = False) -> dict[str, Any]:
        """Get health status of all infrastructure providers."""
        if detailed:
            # Return detailed health reports from monitor
            return self.health_monitor.export_health_data()
        else:
            # Return simplified health status
            summary = self.health_monitor.get_health_summary()

            # Get basic status for each provider
            deployment_status = {}
            dns_status = {}

            for name in self.list_deployment_providers():
                report = self.health_monitor.get_plugin_health(name)
                deployment_status[name] = {
                    "healthy": report.overall_status.value == "healthy"
                    if report
                    else False,
                    "status": report.overall_status.value if report else "unknown",
                    "last_check": report.last_check.isoformat()
                    if report and report.last_check
                    else None,
                }

            for name in self.list_dns_providers():
                report = self.health_monitor.get_plugin_health(name)
                dns_status[name] = {
                    "healthy": report.overall_status.value == "healthy"
                    if report
                    else False,
                    "status": report.overall_status.value if report else "unknown",
                    "last_check": report.last_check.isoformat()
                    if report and report.last_check
                    else None,
                }

            return {
                "deployment_providers": deployment_status,
                "dns_providers": dns_status,
                "overall_healthy": summary["overall_status"] == "healthy",
                "summary": summary,
            }

    # High-level Infrastructure Operations

    @standard_exception_handler
    async def deploy_application(
        self, app_config: dict[str, Any], provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Deploy application using specified or default deployment provider."""
        provider = self.get_deployment_provider(provider_name)

        if not provider:
            available = ", ".join(self.list_deployment_providers())
            raise PluginError(
                f"No deployment provider available. "
                f"Requested: {provider_name}, Available: [{available}]"
            )

        logger.info(f"Deploying application using provider: {provider.meta.name}")

        # Use the deployment provider's infrastructure ID or generate one
        infrastructure_config = {"provider": provider.meta.name, "config": app_config}

        infrastructure_result = await provider.provision_infrastructure(
            infrastructure_config
        )
        infrastructure_id = infrastructure_result.get("infrastructure_id", "default")

        # Deploy the application
        return await provider.deploy_application(app_config, infrastructure_id)

    @standard_exception_handler
    async def validate_subdomain(
        self,
        subdomain: str,
        base_domain: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Validate subdomain availability using specified or default DNS provider."""
        provider = self.get_dns_provider(provider_name)

        if not provider:
            available = ", ".join(self.list_dns_providers())
            raise PluginError(
                f"No DNS provider available. "
                f"Requested: {provider_name}, Available: [{available}]"
            )

        logger.info(f"Validating subdomain using provider: {provider.meta.name}")
        return await provider.validate_subdomain_available(subdomain, base_domain)

    @standard_exception_handler
    async def validate_ssl_certificate(
        self, domain: str, provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Validate SSL certificate using specified or default DNS provider."""
        provider = self.get_dns_provider(provider_name)

        if not provider:
            available = ", ".join(self.list_dns_providers())
            raise PluginError(
                f"No DNS provider available. "
                f"Requested: {provider_name}, Available: [{available}]"
            )

        logger.info(f"Validating SSL certificate using provider: {provider.meta.name}")
        return await provider.validate_ssl_certificate(domain)

    @standard_exception_handler
    async def get_deployment_status(
        self, deployment_id: str, provider_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Get deployment status using specified or default provider."""
        provider = self.get_deployment_provider(provider_name)

        if not provider:
            raise PluginError("No deployment provider available")

        return await provider.get_deployment_status(deployment_id)

    @asynccontextmanager
    async def get_provider_context(
        self, provider_type: str, provider_name: Optional[str] = None
    ):
        """
        Context manager for working with infrastructure providers.
        Ensures proper cleanup and error handling.
        """
        provider = None

        try:
            if provider_type == "deployment":
                provider = self.get_deployment_provider(provider_name)
            elif provider_type == "dns":
                provider = self.get_dns_provider(provider_name)
            else:
                raise PluginError(f"Unsupported provider type: {provider_type}")

            if not provider:
                raise PluginError(
                    f"Provider not found: {provider_name} ({provider_type})"
                )

            # Check provider health before use
            health = await provider.health_check()
            if not health.get("healthy", False):
                raise PluginError(f"Provider unhealthy: {health.get('error')}")

            yield provider

        except (PluginError, ExceptionContext.LIFECYCLE_EXCEPTIONS) as e:
            logger.error(f"Error in provider context: {e}")
            raise
        finally:
            # Cleanup if needed (providers handle their own cleanup)
            pass

    async def shutdown(self):
        """Shutdown all infrastructure providers."""
        logger.info("Shutting down infrastructure plugin manager...")

        # Stop health monitoring
        await self.health_monitor.stop_monitoring()

        # Shutdown deployment providers
        for name, provider in self._deployment_providers.items():
            try:
                await provider.shutdown()
                logger.info(f"✅ Shutdown deployment provider: {name}")
            except (PluginError, ExceptionContext.LIFECYCLE_EXCEPTIONS) as e:
                logger.error(f"Error shutting down deployment provider {name}: {e}")

        # Shutdown DNS providers
        for name, provider in self._dns_providers.items():
            try:
                await provider.shutdown()
                logger.info(f"✅ Shutdown DNS provider: {name}")
            except (PluginError, ExceptionContext.LIFECYCLE_EXCEPTIONS) as e:
                logger.error(f"Error shutting down DNS provider {name}: {e}")

        logger.info("✅ Infrastructure plugin manager shutdown complete")
