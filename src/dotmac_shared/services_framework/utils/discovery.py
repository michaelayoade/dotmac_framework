"""
Service discovery utilities for the DotMac Services Framework.
"""

import asyncio
import logging
import time
from typing import Any, Optional

from ..core.base import BaseService, ServiceStatus
from ..core.registry import ServiceRegistry

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """Service discovery utility for finding and monitoring services."""

    def __init__(self, registry: ServiceRegistry):
        """__init__ service method."""
        self.registry = registry
        self._discovered_services: dict[str, dict[str, Any]] = {}
        self._discovery_cache_ttl = 300  # 5 minutes
        self._last_discovery_time = 0

    async def discover_services(self, refresh: bool = False) -> dict[str, dict[str, Any]]:
        """Discover all available services."""
        current_time = time.time()

        # Use cached results if still valid and not forced refresh
        if (
            not refresh
            and self._discovered_services
            and current_time - self._last_discovery_time < self._discovery_cache_ttl
        ):
            return self._discovered_services

        logger.info("Discovering available services...")

        discovered = {}

        for service_name in self.registry.list_services():
            service = self.registry.get_service(service_name)
            if service:
                service_info = await self._get_service_discovery_info(service)
                discovered[service_name] = service_info

        self._discovered_services = discovered
        self._last_discovery_time = current_time

        logger.info(f"Discovered {len(discovered)} services")
        return discovered

    async def _get_service_discovery_info(self, service: BaseService) -> dict[str, Any]:
        """Get discovery information for a service."""
        try:
            health = await service.health_check()

            return {
                "name": service.name,
                "status": service.get_status().value,
                "healthy": service.is_healthy(),
                "ready": service.is_ready(),
                "priority": getattr(service, "priority", 50),
                "health": {
                    "status": health.status.value,
                    "message": health.message,
                    "last_check": health.last_check,
                    "details": health.details,
                },
                "config_keys": list(service.config.keys()),
                "discovered_at": time.time(),
            }

        except Exception as e:
            logger.error(f"Failed to get discovery info for {service.name}: {e}")
            return {
                "name": service.name,
                "status": "error",
                "healthy": False,
                "ready": False,
                "error": str(e),
                "discovered_at": time.time(),
            }

    def find_services_by_status(self, status: ServiceStatus) -> list[str]:
        """Find services with a specific status."""
        return [name for name, service in self.registry.services.items() if service.get_status() == status]

    def find_ready_services(self) -> list[str]:
        """Find all ready services."""
        return [name for name, service in self.registry.services.items() if service.is_ready()]

    def find_unhealthy_services(self) -> list[str]:
        """Find all unhealthy services."""
        return [name for name, service in self.registry.services.items() if not service.is_healthy()]

    def find_services_with_priority(
        self, min_priority: Optional[int] = None, max_priority: Optional[int] = None
    ) -> list[str]:
        """Find services within a priority range."""
        results = []

        for name, service in self.registry.services.items():
            priority = getattr(service, "priority", 50)

            if min_priority is not None and priority < min_priority:
                continue

            if max_priority is not None and priority > max_priority:
                continue

            results.append(name)

        return results

    def get_service_dependencies_tree(self, service_name: str) -> dict[str, Any]:
        """Get the dependency tree for a service."""
        if not self.registry.has_service(service_name):
            raise ValueError(f"Service {service_name} not found")

        def build_dependency_tree(name: str, visited: Optional[set[str]] = None) -> dict[str, Any]:
            """build_dependency_tree service method."""
            if visited is None:
                visited = set()

            if name in visited:
                return {"name": name, "circular_dependency": True}

            visited.add(name)

            dependencies = self.registry.get_service_dependencies(name)
            dependents = self.registry.get_service_dependents(name)

            tree = {
                "name": name,
                "status": (
                    self.registry.get_service(name).get_status().value
                    if self.registry.has_service(name)
                    else "not_found"
                ),
                "dependencies": [build_dependency_tree(dep, visited.copy()) for dep in dependencies],
                "dependents": dependents,
            }

            return tree

        return build_dependency_tree(service_name)

    async def check_service_connectivity(self, service_name: str) -> dict[str, Any]:
        """Check connectivity and responsiveness of a service."""
        if not self.registry.has_service(service_name):
            return {
                "service": service_name,
                "available": False,
                "error": "Service not found in registry",
            }

        service = self.registry.get_service(service_name)
        start_time = time.time()

        try:
            health = await service.health_check()
            response_time = time.time() - start_time

            return {
                "service": service_name,
                "available": True,
                "ready": service.is_ready(),
                "healthy": service.is_healthy(),
                "response_time_ms": round(response_time * 1000, 2),
                "health": {
                    "status": health.status.value,
                    "message": health.message,
                    "details": health.details,
                },
            }

        except Exception as e:
            response_time = time.time() - start_time

            return {
                "service": service_name,
                "available": False,
                "error": str(e),
                "response_time_ms": round(response_time * 1000, 2),
            }

    async def check_all_services_connectivity(self) -> dict[str, dict[str, Any]]:
        """Check connectivity for all services."""
        results = {}

        # Run connectivity checks in parallel
        tasks = []
        service_names = list(self.registry.services.keys())

        for service_name in service_names:
            task = asyncio.create_task(self.check_service_connectivity(service_name))
            tasks.append((service_name, task))

        # Wait for all checks to complete
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
            except Exception as e:
                results[service_name] = {
                    "service": service_name,
                    "available": False,
                    "error": f"Connectivity check failed: {e}",
                }

        return results

    def get_service_topology(self) -> dict[str, Any]:
        """Get the overall service topology."""
        services = {}
        dependencies = []

        for service_name in self.registry.list_services():
            service = self.registry.get_service(service_name)

            services[service_name] = {
                "name": service_name,
                "status": service.get_status().value,
                "ready": service.is_ready(),
                "healthy": service.is_healthy(),
                "priority": getattr(service, "priority", 50),
            }

            # Add dependencies
            for dep in self.registry.get_service_dependencies(service_name):
                dependencies.append({"from": service_name, "to": dep, "type": "depends_on"})

        return {
            "services": services,
            "dependencies": dependencies,
            "total_services": len(services),
            "ready_services": len([s for s in services.values() if s["ready"]]),
            "healthy_services": len([s for s in services.values() if s["healthy"]]),
        }

    async def wait_for_services(
        self,
        service_names: list[str],
        timeout_seconds: int = 60,
        check_interval: int = 5,
    ) -> dict[str, bool]:
        """Wait for specific services to become ready."""
        start_time = time.time()
        results = dict.fromkeys(service_names, False)

        while time.time() - start_time < timeout_seconds:
            all_ready = True

            for service_name in service_names:
                if not results[service_name]:  # Only check services that aren't ready yet
                    if self.registry.has_service(service_name):
                        service = self.registry.get_service(service_name)
                        if service.is_ready():
                            results[service_name] = True
                            logger.info(f"Service {service_name} is now ready")

                    if not results[service_name]:
                        all_ready = False

            if all_ready:
                break

            await asyncio.sleep(check_interval)

        # Log final results
        ready_services = [name for name, ready in results.items() if ready]
        not_ready_services = [name for name, ready in results.items() if not ready]

        if ready_services:
            logger.info(f"Services ready: {', '.join(ready_services)}")

        if not_ready_services:
            logger.warning(f"Services not ready within timeout: {', '.join(not_ready_services)}")

        return results

    def get_discovery_stats(self) -> dict[str, Any]:
        """Get service discovery statistics."""
        return {
            "total_services": len(self.registry.services),
            "discovered_services": len(self._discovered_services),
            "last_discovery_time": self._last_discovery_time,
            "cache_ttl_seconds": self._discovery_cache_ttl,
            "ready_services": len(self.find_ready_services()),
            "unhealthy_services": len(self.find_unhealthy_services()),
            "registry_initialized": getattr(self.registry, "_registry_initialized", False),
        }
