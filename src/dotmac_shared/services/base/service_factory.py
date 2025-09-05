"""
Service Factory for Unified Base Service Architecture

Provides factory pattern for creating service instances with proper
dependency injection and configuration management.
"""
from __future__ import annotations

import logging
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .base_service import BaseManagementService, BaseService
from .exceptions import ServiceConfigurationError, ServiceDependencyError

logger = logging.getLogger(__name__)

ServiceType = TypeVar("ServiceType", bound=BaseService)


class ServiceFactory:
    """
    Factory for creating service instances with standardized configuration.

    Features:
    - Automatic dependency injection
    - Service configuration validation
    - Type-safe service creation
    - Centralized service instantiation
    """

    def __init__(self, db_session: Session | AsyncSession, tenant_id: str | None = None):
        """
        Initialize service factory.

        Args:
            db_session: Database session for all created services
            tenant_id: Tenant identifier for multi-tenant services
        """
        self.db_session = db_session
        self.tenant_id = tenant_id
        self._service_cache: dict[str, Any] = {}

    def create_service(
        self,
        service_class: type[ServiceType],
        model_class: type | None = None,
        create_schema: type | None = None,
        update_schema: type | None = None,
        response_schema: type | None = None,
        **kwargs,
    ) -> ServiceType:
        """
        Create a service instance with proper dependency injection.

        Args:
            service_class: Service class to instantiate
            model_class: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            **kwargs: Additional service-specific configuration

        Returns:
            Configured service instance

        Raises:
            ServiceConfigurationError: If service configuration is invalid
            ServiceDependencyError: If required dependencies are missing
        """
        try:
            # Validate required dependencies
            self._validate_dependencies(service_class, model_class)

            # Create service configuration
            service_config = {
                "db_session": self.db_session,
                "tenant_id": self.tenant_id,
                "model_class": model_class,
                "create_schema": create_schema,
                "update_schema": update_schema,
                "response_schema": response_schema,
                **kwargs,
            }

            # Remove None values to allow defaults
            service_config = {k: v for k, v in service_config.items() if v is not None}

            # Create service instance
            service_instance = service_class(**service_config)

            logger.debug(f"Created service instance: {service_class.__name__}")

            return service_instance

        except Exception as e:
            error_msg = f"Failed to create service {service_class.__name__}: {e}"
            logger.error(error_msg)
            raise ServiceConfigurationError(service_class.__name__, str(e)) from e

    def create_management_service(
        self,
        service_class: type[ServiceType],
        model_class: type | None = None,
        create_schema: type | None = None,
        update_schema: type | None = None,
        response_schema: type | None = None,
        **kwargs,
    ) -> ServiceType:
        """
        Create a management-specific service instance.

        This is a convenience method that ensures management services
        get the BaseManagementService functionality.

        Args:
            service_class: Management service class to instantiate
            model_class: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            **kwargs: Additional service-specific configuration

        Returns:
            Configured management service instance
        """
        # Ensure the service inherits from BaseManagementService
        if not issubclass(service_class, BaseManagementService):
            logger.warning(
                f"Service {service_class.__name__} does not inherit from BaseManagementService. "
                "Consider using BaseManagementService for management platform services."
            )

        return self.create_service(
            service_class=service_class,
            model_class=model_class,
            create_schema=create_schema,
            update_schema=update_schema,
            response_schema=response_schema,
            **kwargs,
        )

    def get_cached_service(self, service_name: str) -> Any | None:
        """
        Get a cached service instance.

        Args:
            service_name: Name of the cached service

        Returns:
            Cached service instance or None
        """
        return self._service_cache.get(service_name)

    def cache_service(self, service_name: str, service_instance: Any) -> None:
        """
        Cache a service instance for reuse.

        Args:
            service_name: Name to cache the service under
            service_instance: Service instance to cache
        """
        self._service_cache[service_name] = service_instance
        logger.debug(f"Cached service: {service_name}")

    def clear_cache(self) -> None:
        """Clear all cached service instances."""
        self._service_cache.clear()
        logger.debug("Cleared service cache")

    def _validate_dependencies(self, service_class: type[ServiceType], model_class: type | None) -> None:
        """
        Validate that required dependencies are available.

        Args:
            service_class: Service class being created
            model_class: SQLAlchemy model class

        Raises:
            ServiceDependencyError: If required dependencies are missing
        """
        # Check database session
        if not self.db_session:
            raise ServiceDependencyError(
                service_class.__name__, "database_session", "Database session is required but not provided"
            )

        # Check model class if service requires it
        if hasattr(service_class, "_requires_model") and service_class._requires_model and not model_class:
            raise ServiceDependencyError(
                service_class.__name__, "model_class", "Service requires model class but none provided"
            )

        # Validate session type compatibility
        if hasattr(service_class, "_async_only") and service_class._async_only:
            if not isinstance(self.db_session, AsyncSession):
                raise ServiceDependencyError(
                    service_class.__name__, "async_session", "Service requires AsyncSession but sync Session provided"
                )


class ServiceBuilder:
    """
    Builder pattern for complex service creation with method chaining.

    Provides a fluent interface for configuring services before creation.
    """

    def __init__(self, factory: ServiceFactory):
        self.factory = factory
        self._service_class: type[ServiceType] | None = None
        self._model_class: type | None = None
        self._create_schema: type | None = None
        self._update_schema: type | None = None
        self._response_schema: type | None = None
        self._config: dict[str, Any] = {}

    def with_service(self, service_class: type[ServiceType]) -> ServiceBuilder:
        """Set the service class to create."""
        self._service_class = service_class
        return self

    def with_model(self, model_class: type) -> ServiceBuilder:
        """Set the SQLAlchemy model class."""
        self._model_class = model_class
        return self

    def with_schemas(
        self, create_schema: type | None = None, update_schema: type | None = None, response_schema: type | None = None
    ) -> ServiceBuilder:
        """Set the Pydantic schemas."""
        if create_schema:
            self._create_schema = create_schema
        if update_schema:
            self._update_schema = update_schema
        if response_schema:
            self._response_schema = response_schema
        return self

    def with_config(self, **kwargs) -> ServiceBuilder:
        """Add additional configuration."""
        self._config.update(kwargs)
        return self

    def build(self) -> ServiceType:
        """
        Build the configured service.

        Returns:
            Configured service instance

        Raises:
            ServiceConfigurationError: If service class not specified
        """
        if not self._service_class:
            raise ServiceConfigurationError("ServiceBuilder", "Service class not specified")

        return self.factory.create_service(
            service_class=self._service_class,
            model_class=self._model_class,
            create_schema=self._create_schema,
            update_schema=self._update_schema,
            response_schema=self._response_schema,
            **self._config,
        )
