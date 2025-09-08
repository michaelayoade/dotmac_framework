"""
Service registry for managing business service dependencies and lifecycle.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import BaseService, ServiceHealth, ServiceStatus

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for service registry and common services."""

    # Authentication service config
    auth_enabled: bool = True
    auth_jwt_secret: Optional[str] = None
    auth_issuer: Optional[str] = None
    auth_expiry_hours: int = 24

    # Payment service config
    payment_enabled: bool = True
    payment_provider: str = "stripe"  # stripe, paypal, square
    payment_api_key: Optional[str] = None
    payment_webhook_secret: Optional[str] = None

    # Notification service config
    notification_enabled: bool = True
    notification_providers: list[str] = field(default_factory=lambda: ["email", "sms"])
    email_provider: str = "sendgrid"  # sendgrid, ses, mailgun
    sms_provider: str = "twilio"  # twilio, aws-sns

    # Analytics service config
    analytics_enabled: bool = True
    analytics_provider: str = "prometheus"  # prometheus, datadog, newrelic
    analytics_endpoint: Optional[str] = None

    # Registry configuration
    initialization_timeout_seconds: int = 300  # 5 minutes
    health_check_interval_seconds: int = 30
    retry_failed_services: bool = True
    max_retry_attempts: int = 3

    # Custom service configurations
    custom_services: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class ServiceDependency:
    """Represents a service dependency relationship."""

    service_name: str
    depends_on: str
    required: bool = True  # If true, dependency must be ready before service can initialize


class ServiceRegistry:
    """Registry for managing business service dependencies and lifecycle."""

    def __init__(self, config: ServiceConfig = None):
        """__init__ service method."""
        self.config = config or ServiceConfig()
        self.services: dict[str, BaseService] = {}
        self.dependencies: list[ServiceDependency] = []
        self.initialization_order: list[str] = []
        self._initialization_lock = asyncio.Lock()
        self._initialization_results: dict[str, bool] = {}
        self._retry_counts: dict[str, int] = {}

        # Common service references for easy access
        self.auth: Optional[BaseService] = None
        self.payment: Optional[BaseService] = None
        self.notification: Optional[BaseService] = None
        self.analytics: Optional[BaseService] = None

        # Registry state
        self._registry_initialized = False
        self._last_health_check = 0

    def register_service(self, name: str, service: BaseService, priority: Optional[int] = None):
        """Register a service with the registry."""
        if name in self.services:
            logger.warning(f"Service {name} already registered, replacing")

        # Set priority if provided
        if priority is not None:
            service.priority = priority

        self.services[name] = service

        # Reset initialization order to trigger recalculation
        self._calculate_initialization_order()

        # Set common service references
        self._set_common_service_references(name, service)

        logger.info(f"Registered service: {name} (priority: {service.priority})")

    def add_dependency(self, service_name: str, depends_on: str, required: bool = True):
        """Add a service dependency."""
        dependency = ServiceDependency(service_name, depends_on, required)

        # Check for circular dependencies
        if self._would_create_circular_dependency(dependency):
            raise ValueError(f"Adding dependency {service_name} -> {depends_on} would create circular dependency")

        self.dependencies.append(dependency)
        self._calculate_initialization_order()

        logger.info(f"Added dependency: {service_name} depends on {depends_on} (required: {required})")

    def _would_create_circular_dependency(self, new_dependency: ServiceDependency) -> bool:
        """Check if adding a dependency would create a circular reference."""
        # Build dependency graph including new dependency
        graph = {}
        all_deps = self.dependencies + [new_dependency]

        for dep in all_deps:
            if dep.service_name not in graph:
                graph[dep.service_name] = []
            graph[dep.service_name].append(dep.depends_on)

        # Check for cycles using DFS
        def has_cycle(node: str, visited: set[str], rec_stack: set[str]) -> bool:
            """has_cycle service method."""
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for node in graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    return True

        return False

    def _calculate_initialization_order(self):
        """Calculate service initialization order based on priorities and dependencies."""
        # First, sort by priority (higher priority first)
        services_by_priority = sorted(self.services.items(), key=lambda x: x[1].priority, reverse=True)

        # Apply dependency constraints
        ordered = []
        remaining = dict(services_by_priority)

        while remaining:
            # Find services with no unfulfilled dependencies
            ready_services = []

            for name, service in remaining.items():
                dependencies = [dep for dep in self.dependencies if dep.service_name == name and dep.required]
                unfulfilled_deps = [dep.depends_on for dep in dependencies if dep.depends_on in remaining]

                if not unfulfilled_deps:
                    ready_services.append((name, service))

            if not ready_services:
                # No services are ready - check for circular dependencies
                logger.warning(f"Possible circular dependency detected. Remaining services: {list(remaining.keys())}")
                # Add remaining services in priority order to break deadlock
                ready_services = list(remaining.items())

            # Sort ready services by priority and add to order
            ready_services.sort(key=lambda x: x[1].priority, reverse=True)

            for name, _ in ready_services:
                ordered.append(name)
                remaining.pop(name)

        self.initialization_order = ordered
        logger.debug(f"Calculated initialization order: {self.initialization_order}")

    def _set_common_service_references(self, name: str, service: BaseService):
        """Set common service references for easy access."""
        if name == "auth":
            self.auth = service
        elif name == "payment":
            self.payment = service
        elif name == "notification":
            self.notification = service
        elif name == "analytics":
            self.analytics = service

    def get_service(self, name: str) -> Optional[BaseService]:
        """Get a service by name."""
        return self.services.get(name)

    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self.services

    def list_services(self) -> list[str]:
        """List all registered service names."""
        return list(self.services.keys())

    def get_service_dependencies(self, service_name: str) -> list[str]:
        """Get list of services that the given service depends on."""
        return [dep.depends_on for dep in self.dependencies if dep.service_name == service_name]

    def get_service_dependents(self, service_name: str) -> list[str]:
        """Get list of services that depend on the given service."""
        return [dep.service_name for dep in self.dependencies if dep.depends_on == service_name]

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all registered services in dependency order."""
        async with self._initialization_lock:
            if self._registry_initialized:
                logger.info("Service registry already initialized")
                return self._initialization_results

            logger.info("Starting service registry initialization...")
            self._initialization_results = {}
            self._retry_counts = {}

            # Calculate initialization order if not done
            if not self.initialization_order:
                self._calculate_initialization_order()

            # Initialize services in order
            for service_name in self.initialization_order:
                await self._initialize_single_service(service_name)

            # Log summary
            successful = sum(1 for success in self._initialization_results.values() if success)
            total = len(self._initialization_results)

            if successful == total:
                logger.info(f"✅ Service registry initialization complete: {successful}/{total} services ready")
                self._registry_initialized = True
            else:
                logger.warning(f"⚠️ Service registry initialization partial: {successful}/{total} services ready")

            return self._initialization_results

    async def _initialize_single_service(self, service_name: str) -> bool:
        """Initialize a single service with dependency checking."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found in registry")
            self._initialization_results[service_name] = False
            return False

        service = self.services[service_name]

        # Check if dependencies are ready
        dependencies = [dep for dep in self.dependencies if dep.service_name == service_name]
        for dep in dependencies:
            if dep.required and dep.depends_on in self.services:
                dep_service = self.services[dep.depends_on]
                if not dep_service.is_ready():
                    logger.warning(f"Service {service_name} waiting for dependency {dep.depends_on}")
                    # For now, continue anyway - could implement waiting logic here

        # Initialize the service
        try:
            logger.info(f"Initializing service: {service_name}")
            success = await asyncio.wait_for(service.initialize(), timeout=self.config.initialization_timeout_seconds)

            self._initialization_results[service_name] = success

            if success:
                logger.info(f"✅ Service {service_name} initialized successfully")
            else:
                logger.error(f"❌ Service {service_name} initialization failed")

                # Retry if configured
                if self.config.retry_failed_services:
                    retry_count = self._retry_counts.get(service_name, 0)
                    if retry_count < self.config.max_retry_attempts:
                        self._retry_counts[service_name] = retry_count + 1
                        logger.info(f"Retrying service {service_name} initialization (attempt {retry_count + 1})")
                        return await self._initialize_single_service(service_name)

        except asyncio.TimeoutError:
            logger.error(f"❌ Service {service_name} initialization timed out")
            self._initialization_results[service_name] = False
            return False

        except Exception as e:
            logger.error(f"❌ Service {service_name} initialization error: {e}")
            self._initialization_results[service_name] = False
            return False

        return self._initialization_results[service_name]

    async def shutdown_all(self) -> dict[str, bool]:
        """Shutdown all services in reverse initialization order."""
        logger.info("Starting service registry shutdown...")
        results = {}

        # Shutdown in reverse order
        for service_name in reversed(self.initialization_order):
            if service_name not in self.services:
                continue

            service = self.services[service_name]

            try:
                logger.info(f"Shutting down service: {service_name}")
                success = await asyncio.wait_for(
                    service.shutdown(),
                    timeout=30,  # 30 second timeout for shutdown
                )
                results[service_name] = success

                if success:
                    logger.info(f"✅ Service {service_name} shutdown successfully")
                else:
                    logger.warning(f"⚠️ Service {service_name} shutdown failed")

            except asyncio.TimeoutError:
                logger.error(f"❌ Service {service_name} shutdown timed out")
                results[service_name] = False

            except Exception as e:
                logger.error(f"❌ Service {service_name} shutdown error: {e}")
                results[service_name] = False

        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"Service registry shutdown complete: {successful}/{total} services shutdown")

        self._registry_initialized = False
        return results

    async def health_check_all(self) -> dict[str, ServiceHealth]:
        """Perform health checks on all services."""
        health_results = {}
        current_time = time.time()

        # Only run health checks at configured intervals
        if current_time - self._last_health_check < self.config.health_check_interval_seconds:
            # Return cached results if available
            for service_name, service in self.services.items():
                health_results[service_name] = service.get_health()
            return health_results

        self._last_health_check = current_time

        # Run health checks
        for service_name, service in self.services.items():
            try:
                health = await service.health_check()
                health_results[service_name] = health

                # Log health issues
                if health.status == ServiceStatus.ERROR:
                    logger.error(f"Service {service_name} health check failed: {health.message}")

            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_results[service_name] = ServiceHealth(
                    status=ServiceStatus.ERROR,
                    message=f"Health check exception: {e}",
                    details={"exception": str(e)},
                )

        return health_results

    def get_ready_services(self) -> list[str]:
        """Get list of services that are ready."""
        return [name for name, service in self.services.items() if service.is_ready()]

    def get_unhealthy_services(self) -> list[str]:
        """Get list of services that are not healthy."""
        return [name for name, service in self.services.items() if not service.is_healthy()]

    def get_service_status_summary(self) -> dict[str, str]:
        """Get summary of all service statuses."""
        return {name: service.get_status().value for name, service in self.services.items()}

    def is_all_services_ready(self) -> bool:
        """Check if all registered services are ready."""
        return all(service.is_ready() for service in self.services.values())

    def is_registry_healthy(self) -> bool:
        """Check if the registry and all services are healthy."""
        if not self._registry_initialized:
            return False

        return all(service.is_healthy() for service in self.services.values())

    def get_registry_status(self) -> dict[str, Any]:
        """Get comprehensive registry status."""
        return {
            "initialized": self._registry_initialized,
            "total_services": len(self.services),
            "ready_services": len(self.get_ready_services()),
            "unhealthy_services": len(self.get_unhealthy_services()),
            "all_ready": self.is_all_services_ready(),
            "registry_healthy": self.is_registry_healthy(),
            "initialization_order": self.initialization_order,
            "last_health_check": self._last_health_check,
            "service_statuses": self.get_service_status_summary(),
        }

    def get_service_config_for(self, service_name: str) -> dict[str, Any]:
        """Get configuration for a specific service."""
        if service_name == "auth":
            return {
                "enabled": self.config.auth_enabled,
                "jwt_secret": self.config.auth_jwt_secret,
                "issuer": self.config.auth_issuer,
                "expiry_hours": self.config.auth_expiry_hours,
            }
        elif service_name == "payment":
            return {
                "enabled": self.config.payment_enabled,
                "provider": self.config.payment_provider,
                "api_key": self.config.payment_api_key,
                "webhook_secret": self.config.payment_webhook_secret,
            }
        elif service_name == "notification":
            return {
                "enabled": self.config.notification_enabled,
                "providers": self.config.notification_providers,
                "email_provider": self.config.email_provider,
                "sms_provider": self.config.sms_provider,
            }
        elif service_name == "analytics":
            return {
                "enabled": self.config.analytics_enabled,
                "provider": self.config.analytics_provider,
                "endpoint": self.config.analytics_endpoint,
            }
        else:
            return self.config.custom_services.get(service_name, {})

    def __getattr__(self, name: str) -> Optional[BaseService]:
        """Allow accessing services as attributes (registry.auth, registry.payment, etc.)."""
        if name in self.services:
            return self.services[name]
        raise AttributeError(f"Service '{name}' not found in registry")
