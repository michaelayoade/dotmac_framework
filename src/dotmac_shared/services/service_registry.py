"""
from __future__ import annotations
Service registry for DotMac platforms.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Information about a registered service."""

    name: str
    instance: Any
    service_type: str
    description: Optional[str] = None


class ServiceRegistry:
    """Registry for managing services across the platform."""

    def __init__(self):
        """__init__ service method."""
        self._services: dict[str, ServiceInfo] = {}

    def register(
        self,
        name: str,
        instance: Any,
        service_type: str = "unknown",
        description: Optional[str] = None,
    ) -> None:
        """Register a service in the registry."""
        service_info = ServiceInfo(
            name=name,
            instance=instance,
            service_type=service_type,
            description=description,
        )
        self._services[name] = service_info
        logger.info(f"Registered service '{name}' of type '{service_type}'")

    def get(self, name: str) -> Optional[Any]:
        """Get a service instance by name."""
        service_info = self._services.get(name)
        return service_info.instance if service_info else None

    def get_by_type(self, service_type: str) -> list[Any]:
        """Get all services of a specific type."""
        return [info.instance for info in self._services.values() if info.service_type == service_type]

    def list_all(self) -> dict[str, ServiceInfo]:
        """List all registered services."""
        return self._services.copy()

    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            logger.info(f"Unregistered service '{name}'")
            return True
        return False

    def get_ready_services(self) -> dict[str, dict[str, Any]]:
        """
        Get services that are ready for use.

        Returns:
            Dict of ready services with their metadata
        """
        ready_services = {}

        for name, service_info in self._services.items():
            # Basic readiness check - service exists and is not None
            if service_info.instance is not None:
                ready_services[name] = {
                    "service": service_info.instance,
                    "status": "ready",
                    "type": service_info.service_type,
                    "description": service_info.description or f"Service: {name}",
                }
            else:
                ready_services[name] = {
                    "service": None,
                    "status": "not_ready",
                    "type": service_info.service_type,
                    "description": service_info.description or f"Service: {name}",
                }

        logger.debug(
            f"Ready services check: {len([s for s in ready_services.values() if s['status'] == 'ready'])} ready"
        )
        return ready_services
