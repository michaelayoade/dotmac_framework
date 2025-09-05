"""Service registry for dependency injection and service boundaries."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceFactory(Protocol):
    """Protocol for service factory functions."""

    def __call__(self, db: Session, tenant_id: UUID, **kwargs) -> Any:
        """Create service instance."""
        ...


class IServiceRegistry(ABC):
    """Interface for service registry."""

    @abstractmethod
    def register(self, service_type: type[T], factory: ServiceFactory) -> None:
        """Register a service factory."""

    @abstractmethod
    def get(self, service_type: type[T], db: Session, tenant_id: UUID, **kwargs) -> T:
        """Get service instance."""

    @abstractmethod
    def is_registered(self, service_type: type[T]) -> bool:
        """Check if service type is registered."""


class ServiceRegistry(IServiceRegistry):
    """Service registry implementation with dependency injection."""

    def __init__(self):
        """Init   operation."""
        self._factories: dict[type, ServiceFactory] = {}
        self._instances: dict[str, Any] = {}  # For singleton services
        self._singleton_types: set = set()

    def register(
        self, service_type: type[T], factory: ServiceFactory, singleton: bool = False
    ) -> None:
        """Register a service factory.

        Args:
            service_type: The service interface or class type
            factory: Factory function to create service instances
            singleton: Whether to create singleton instances per tenant
        """
        logger.debug(f"Registering service: {service_type.__name__}")
        self._factories[service_type] = factory
        if singleton:
            self._singleton_types.add(service_type)

    def get(self, service_type: type[T], db: Session, tenant_id: UUID, **kwargs) -> T:
        """Get service instance.

        Args:
            service_type: The service type to retrieve
            db: Database session
            tenant_id: Tenant identifier
            **kwargs: Additional arguments for service creation

        Returns:
            Service instance

        Raises:
            ValueError: If service type is not registered
        """
        if service_type not in self._factories:
            raise ValueError(f"Service type {service_type.__name__} is not registered")

        # Check if singleton and already created for this tenant
        if service_type in self._singleton_types:
            instance_key = f"{service_type.__name__}_{tenant_id}"
            if instance_key in self._instances:
                return self._instances[instance_key]

        # Create new instance
        factory = self._factories[service_type]
        logger.debug(f"Creating service instance: {service_type.__name__}")

        instance = factory(db, tenant_id, **kwargs)

        # Store singleton instance
        if service_type in self._singleton_types:
            instance_key = f"{service_type.__name__}_{tenant_id}"
            self._instances[instance_key] = instance

        return instance

    def is_registered(self, service_type: type[T]) -> bool:
        """Check if service type is registered."""
        return service_type in self._factories

    def clear_singletons(self, tenant_id: Optional[UUID] = None) -> None:
        """Clear singleton instances.

        Args:
            tenant_id: If provided, only clear singletons for this tenant
        """
        if tenant_id:
            # Clear only for specific tenant
            keys_to_remove = [
                key for key in self._instances.keys() if key.endswith(f"_{tenant_id}")
            ]
            for key in keys_to_remove:
                del self._instances[key]
        else:
            # Clear all singletons
            self._instances.clear()

    def get_registered_services(self) -> list:
        """Get list of registered service types."""
        return list(self._factories.keys())


# Global service registry instance
_service_registry = ServiceRegistry()


def get_service_registry() -> IServiceRegistry:
    """Get the global service registry."""
    return _service_registry


def register_service(
    service_type: type[T], factory: ServiceFactory, singleton: bool = False
):
    """Decorator to register a service factory.

    Args:
        service_type: The service interface or class type
        factory: Factory function to create service instances
        singleton: Whether to create singleton instances per tenant
    """

    def decorator(func):
        """Decorator operation."""
        _service_registry.register(service_type, factory or func, singleton)
        return func

    return decorator


# Service boundary enforcement
class ServiceBoundary:
    """Enforces service boundaries and dependencies."""

    def __init__(self, registry: IServiceRegistry):
        """Init   operation."""
        self.registry = registry
        self._dependencies: dict[type, set] = {}

    def add_dependency(self, service_type: type, dependency_type: type) -> None:
        """Add allowed dependency between services."""
        if service_type not in self._dependencies:
            self._dependencies[service_type] = set()
        self._dependencies[service_type].add(dependency_type)

    def validate_dependency(self, service_type: type, dependency_type: type) -> bool:
        """Validate if dependency is allowed."""
        allowed_deps = self._dependencies.get(service_type, set())
        return dependency_type in allowed_deps

    def get_service_with_validation(
        self,
        service_type: type[T],
        requesting_service: Optional[type],
        db: Session,
        tenant_id: UUID,
        **kwargs,
    ) -> T:
        """Get service with boundary validation."""
        if requesting_service:
            if not self.validate_dependency(requesting_service, service_type):
                raise ValueError(
                    f"Service {requesting_service.__name__} is not allowed to depend on {service_type.__name__}"
                )
        return self.registry.get(service_type, db, tenant_id, **kwargs)


# Service context for managing service lifecycles
class ServiceContext:
    """Context manager for service lifecycle management."""

    def __init__(
        self, db, tenant_id: str, registry: Optional["ServiceRegistry"] = None
    ):
        """Initialize service context."""
        self.db = db
        self.tenant_id = tenant_id
        self.registry = registry or get_service_registry()
        self._services: dict[type, Any] = {}

    def get_service(self, service_type: type[T], **kwargs) -> T:
        """Get service instance within this context."""
        if service_type not in self._services:
            self._services[service_type] = self.registry.get(
                service_type, self.db, self.tenant_id, **kwargs
            )
        return self._services[service_type]

    def __enter__(self):
        """Enter   operation."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit   operation."""
        # Cleanup services if needed
        self._services.clear()


# Domain service base class
class DomainService:
    """Base class for domain services."""

    def __init__(self, tenant_id: UUID):
        """Init   operation."""
        self.tenant_id = tenant_id

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self.__class__.__name__

    def validate_tenant_access(self, resource_tenant_id: UUID) -> None:
        """Validate tenant access to resource."""
        if resource_tenant_id != self.tenant_id:
            raise PermissionError(
                f"Service {self.service_name} cannot access resource from different tenant"
            )


# Service health check
class ServiceHealthCheck:
    """Health check for services."""

    def __init__(self, registry: IServiceRegistry):
        """Init   operation."""
        self.registry = registry

    def check_service_health(
        self, service_type: type, db: Session, tenant_id: UUID
    ) -> dict[str, Any]:
        """Check health of a specific service."""
        # Try to create service instance
        service = self.registry.get(service_type, db, tenant_id)

        # Check if service has health check method
        if hasattr(service, "health_check"):
            return service.health_check()

        return {
            "status": "healthy",
            "service": service_type.__name__,
            "message": "Service created successfully",
        }

    def check_all_services_health(self, db: Session, tenant_id: UUID) -> dict[str, Any]:
        """Check health of all registered services."""
        results = {}
        registered_services = self.registry.get_registered_services()

        for service_type in registered_services:
            service_name = service_type.__name__
            results[service_name] = self.check_service_health(
                service_type, db, tenant_id
            )
        # Calculate overall health
        unhealthy_count = sum(
            1 for result in results.values() if result["status"] == "unhealthy"
        )
        overall_status = "healthy" if unhealthy_count == 0 else "unhealthy"

        return {
            "overall_status": overall_status,
            "total_services": len(results),
            "healthy_services": len(results) - unhealthy_count,
            "unhealthy_services": unhealthy_count,
            "services": results,
        }
