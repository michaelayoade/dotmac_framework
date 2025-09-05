"""
from __future__ import annotations
Deployment-aware service factory for DotMac platforms.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DeploymentAwareServiceFactory:
    """Factory for creating services based on deployment context."""

    def __init__(self, deployment_context: Optional[Any] = None):
        """__init__ service method."""
        self._services: dict[str, Any] = {}
        self._deployment_context = deployment_context

    def register_service(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service
        logger.info(f"Registered service: {name}")

    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered service."""
        return self._services.get(name)

    def list_services(self) -> dict[str, Any]:
        """List all registered services."""
        return self._services.copy()

    async def create_service_registry(self):
        """
        Create a service registry instance.

        Returns:
            ServiceRegistry instance
        """
        from .service_registry import ServiceRegistry

        # Create registry with deployment context
        registry = ServiceRegistry()

        # Register any existing services with the registry
        for name, service in self._services.items():
            registry.register(
                name, service, "factory_service", f"Service from factory: {name}"
            )

        logger.info("Created service registry from factory")
        return registry
