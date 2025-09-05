"""
Service Registry for Unified Base Service Architecture

Provides centralized service discovery and management with dependency
injection and lifecycle management.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .base_service import BaseService
from .exceptions import ServiceError, ServiceNotFoundError
from .service_factory import ServiceFactory

logger = logging.getLogger(__name__)

ServiceType = TypeVar("ServiceType", bound=BaseService)


class ServiceRegistry:
    """
    Centralized registry for service discovery and management.

    Features:
    - Service registration and discovery
    - Dependency injection
    - Lifecycle management
    - Service health monitoring
    - Lazy initialization
    """

    def __init__(self, db_session: Session | AsyncSession, tenant_id: str | None = None):
        """
        Initialize service registry.

        Args:
            db_session: Database session for all services
            tenant_id: Tenant identifier for multi-tenant services
        """
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.factory = ServiceFactory(db_session, tenant_id)

        # Service registration storage
        self._service_definitions: dict[str, dict] = {}
        self._service_instances: dict[str, Any] = {}
        self._service_dependencies: dict[str, list[str]] = {}
        self._initialization_callbacks: dict[str, list[Callable]] = {}

        # Registry state
        self._initialized = False
        self._health_status: dict[str, bool] = {}

    def register_service(
        self,
        name: str,
        service_class: type[ServiceType],
        model_class: type | None = None,
        create_schema: type | None = None,
        update_schema: type | None = None,
        response_schema: type | None = None,
        dependencies: list[str] | None = None,
        singleton: bool = True,
        lazy: bool = True,
        **config,
    ) -> None:
        """
        Register a service with the registry.

        Args:
            name: Unique service name
            service_class: Service class to register
            model_class: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            dependencies: List of dependent service names
            singleton: Whether to create single instance (default: True)
            lazy: Whether to initialize lazily (default: True)
            **config: Additional service configuration
        """
        if name in self._service_definitions:
            logger.warning(f"Service '{name}' already registered. Overwriting.")

        self._service_definitions[name] = {
            "service_class": service_class,
            "model_class": model_class,
            "create_schema": create_schema,
            "update_schema": update_schema,
            "response_schema": response_schema,
            "singleton": singleton,
            "lazy": lazy,
            "config": config,
        }

        self._service_dependencies[name] = dependencies or []
        self._initialization_callbacks[name] = []

        logger.debug(f"Registered service: {name}")

        # Initialize immediately if not lazy
        if not lazy:
            self.get_service(name)

    def get_service(self, name: str) -> Any:
        """
        Get a service instance from the registry.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If service not registered
            ServiceError: If service creation fails
        """
        # Check if service is registered
        if name not in self._service_definitions:
            available = list(self._service_definitions.keys())
            raise ServiceNotFoundError(name, available)

        definition = self._service_definitions[name]

        # Return cached instance for singletons
        if definition["singleton"] and name in self._service_instances:
            return self._service_instances[name]

        # Create new instance
        try:
            # Ensure dependencies are available
            self._resolve_dependencies(name)

            # Create service instance
            service_instance = self.factory.create_service(
                service_class=definition["service_class"],
                model_class=definition["model_class"],
                create_schema=definition["create_schema"],
                update_schema=definition["update_schema"],
                response_schema=definition["response_schema"],
                **definition["config"],
            )

            # Cache singleton instances
            if definition["singleton"]:
                self._service_instances[name] = service_instance

            # Run initialization callbacks
            self._run_initialization_callbacks(name, service_instance)

            # Update health status
            self._health_status[name] = True

            logger.debug(f"Created service instance: {name}")
            return service_instance

        except Exception as e:
            self._health_status[name] = False
            error_msg = f"Failed to create service '{name}': {e}"
            logger.error(error_msg)
            raise ServiceError(error_msg) from e

    def list_services(self) -> list[str]:
        """
        Get list of all registered service names.

        Returns:
            List of registered service names
        """
        return list(self._service_definitions.keys())

    def is_registered(self, name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            name: Service name

        Returns:
            True if service is registered
        """
        return name in self._service_definitions

    def is_healthy(self, name: str) -> bool:
        """
        Check if a service is healthy (last creation succeeded).

        Args:
            name: Service name

        Returns:
            True if service is healthy
        """
        return self._health_status.get(name, False)

    def get_health_status(self) -> dict[str, bool]:
        """
        Get health status for all services.

        Returns:
            Dictionary mapping service names to health status
        """
        return self._health_status.copy()

    def unregister_service(self, name: str) -> None:
        """
        Unregister a service from the registry.

        Args:
            name: Service name
        """
        if name in self._service_definitions:
            del self._service_definitions[name]

        if name in self._service_instances:
            del self._service_instances[name]

        if name in self._service_dependencies:
            del self._service_dependencies[name]

        if name in self._initialization_callbacks:
            del self._initialization_callbacks[name]

        if name in self._health_status:
            del self._health_status[name]

        logger.debug(f"Unregistered service: {name}")

    def clear_cache(self) -> None:
        """Clear all cached service instances."""
        self._service_instances.clear()
        self.factory.clear_cache()
        logger.debug("Cleared service registry cache")

    def add_initialization_callback(self, service_name: str, callback: Callable[[Any], None]) -> None:
        """
        Add callback to run after service initialization.

        Args:
            service_name: Service name
            callback: Function to call with service instance
        """
        if service_name not in self._initialization_callbacks:
            self._initialization_callbacks[service_name] = []

        self._initialization_callbacks[service_name].append(callback)

    def get_service_info(self, name: str) -> dict[str, Any]:
        """
        Get detailed information about a registered service.

        Args:
            name: Service name

        Returns:
            Service information dictionary

        Raises:
            ServiceNotFoundError: If service not registered
        """
        if name not in self._service_definitions:
            raise ServiceNotFoundError(name, list(self._service_definitions.keys()))

        definition = self._service_definitions[name]

        return {
            "name": name,
            "service_class": definition["service_class"].__name__,
            "model_class": definition["model_class"].__name__ if definition["model_class"] else None,
            "dependencies": self._service_dependencies.get(name, []),
            "singleton": definition["singleton"],
            "lazy": definition["lazy"],
            "instantiated": name in self._service_instances,
            "healthy": self._health_status.get(name, False),
            "callbacks_count": len(self._initialization_callbacks.get(name, [])),
        }

    def _resolve_dependencies(self, service_name: str) -> None:
        """
        Ensure all dependencies for a service are available.

        Args:
            service_name: Service name

        Raises:
            ServiceError: If dependency resolution fails
        """
        dependencies = self._service_dependencies.get(service_name, [])

        for dependency in dependencies:
            if dependency not in self._service_definitions:
                raise ServiceError(f"Service '{service_name}' depends on '{dependency}' which is not registered")

            # Recursively resolve dependencies
            try:
                self.get_service(dependency)
            except Exception as e:
                raise ServiceError(
                    f"Failed to resolve dependency '{dependency}' for service '{service_name}': {e}"
                ) from e

    def _run_initialization_callbacks(self, service_name: str, service_instance: Any) -> None:
        """
        Run initialization callbacks for a service.

        Args:
            service_name: Service name
            service_instance: Service instance
        """
        callbacks = self._initialization_callbacks.get(service_name, [])

        for callback in callbacks:
            try:
                callback(service_instance)
                logger.debug(f"Ran initialization callback for {service_name}")
            except Exception as e:
                logger.warning(f"Initialization callback failed for {service_name}: {e}")


class ServiceRegistryBuilder:
    """
    Builder pattern for configuring service registry.

    Provides fluent interface for service registration and configuration.
    """

    def __init__(self, db_session: Session | AsyncSession, tenant_id: str | None = None):
        self.registry = ServiceRegistry(db_session, tenant_id)

    def register(self, name: str, service_class: type[ServiceType], **kwargs) -> ServiceRegistryBuilder:
        """Register a service with the registry."""
        self.registry.register_service(name, service_class, **kwargs)
        return self

    def with_dependency(self, service_name: str, dependency: str) -> ServiceRegistryBuilder:
        """Add a dependency to a registered service."""
        if service_name in self.registry._service_dependencies:
            self.registry._service_dependencies[service_name].append(dependency)
        return self

    def with_callback(self, service_name: str, callback: Callable[[Any], None]) -> ServiceRegistryBuilder:
        """Add initialization callback to a service."""
        self.registry.add_initialization_callback(service_name, callback)
        return self

    def build(self) -> ServiceRegistry:
        """Build the configured registry."""
        return self.registry
