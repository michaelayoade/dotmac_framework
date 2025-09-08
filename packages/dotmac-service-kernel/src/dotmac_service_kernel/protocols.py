"""
Protocol definitions for services and repositories.

This module defines the core protocols (interfaces) that services and repositories
should implement to ensure consistency across the DotMac platform.
"""

from typing import Generic, Protocol, TypeVar, runtime_checkable
from uuid import UUID

from .pagination import Page
from .types import ID

T = TypeVar("T")  # Entity type
CreateT = TypeVar("CreateT")  # Create schema type
UpdateT = TypeVar("UpdateT")  # Update schema type


@runtime_checkable
class RepositoryProtocol(Protocol, Generic[T, CreateT, UpdateT]):
    """Protocol for repository implementations.

    This protocol defines the standard interface that all repositories should implement,
    providing consistent CRUD operations with type safety.

    Type Parameters:
        T: The entity type this repository manages
        CreateT: The schema type for creating new entities
        UpdateT: The schema type for updating existing entities
    """

    async def create(self, obj_in: CreateT, **kwargs) -> T:
        """Create a new entity.

        Args:
            obj_in: The data for creating the new entity
            **kwargs: Additional keyword arguments (e.g., user_id, tenant_id)

        Returns:
            The created entity

        Raises:
            RepositoryError: If creation fails
        """
        ...

    async def get(self, entity_id: ID) -> T | None:
        """Get an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        ...

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> list[T]:
        """Get multiple entities with optional filtering.

        Args:
            skip: Number of entities to skip
            limit: Maximum number of entities to return
            **filters: Optional filters to apply

        Returns:
            List of entities matching the criteria
        """
        ...

    async def get_page(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> Page[T]:
        """Get a page of entities with optional filtering.

        Args:
            page: Page number (1-based)
            page_size: Number of entities per page
            **filters: Optional filters to apply

        Returns:
            Page containing entities and pagination metadata
        """
        ...

    async def update(self, db_obj: T, obj_in: UpdateT | dict) -> T:
        """Update an existing entity.

        Args:
            db_obj: The existing entity to update
            obj_in: The update data (schema or dictionary)

        Returns:
            The updated entity

        Raises:
            RepositoryError: If update fails
        """
        ...

    async def delete(self, entity_id: ID) -> bool:
        """Delete an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity to delete

        Returns:
            True if the entity was deleted, False if not found
        """
        ...

    async def count(self, **filters) -> int:
        """Count entities with optional filtering.

        Args:
            **filters: Optional filters to apply

        Returns:
            Number of entities matching the criteria
        """
        ...


@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol for service implementations.

    This is a marker protocol that services can implement to indicate they
    follow the service pattern. Services typically orchestrate business logic
    and coordinate between repositories and external systems.
    """

    pass


@runtime_checkable
class UnitOfWork(Protocol):
    """Protocol for unit of work implementations.

    The unit of work pattern maintains a list of objects affected by a business
    transaction and coordinates writing out changes and resolving concurrency problems.
    """

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the unit of work context.

        Returns:
            The unit of work instance
        """
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the unit of work context.

        If an exception occurred, rollback the transaction.
        Otherwise, commit the transaction.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        ...

    async def commit(self) -> None:
        """Commit the current transaction.

        Saves all changes made within this unit of work.

        Raises:
            RepositoryError: If commit fails
        """
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction.

        Discards all changes made within this unit of work.
        """
        ...


@runtime_checkable
class TenantAwareRepository(RepositoryProtocol[T, CreateT, UpdateT], Protocol):
    """Protocol for tenant-aware repository implementations.

    This protocol extends the base repository protocol with tenant isolation
    capabilities, ensuring that all operations are scoped to a specific tenant.

    Type Parameters:
        T: The entity type this repository manages
        CreateT: The schema type for creating new entities
        UpdateT: The schema type for updating existing entities
    """

    @property
    def tenant_id(self) -> UUID:
        """Get the tenant ID this repository is scoped to.

        Returns:
            The UUID of the current tenant
        """
        ...

    async def get_by_tenant(self, entity_id: ID, tenant_id: UUID) -> T | None:
        """Get an entity by ID within a specific tenant scope.

        Args:
            entity_id: The unique identifier of the entity
            tenant_id: The tenant ID to scope the query to

        Returns:
            The entity if found within the tenant, None otherwise
        """
        ...


@runtime_checkable
class CacheableRepository(RepositoryProtocol[T, CreateT, UpdateT], Protocol):
    """Protocol for repository implementations with caching support.

    This protocol extends the base repository protocol with caching capabilities,
    allowing repositories to implement various caching strategies.

    Type Parameters:
        T: The entity type this repository manages
        CreateT: The schema type for creating new entities
        UpdateT: The schema type for updating existing entities
    """

    async def invalidate_cache(self, entity_id: ID) -> None:
        """Invalidate cached data for a specific entity.

        Args:
            entity_id: The unique identifier of the entity to invalidate
        """
        ...

    async def invalidate_cache_pattern(self, pattern: str) -> None:
        """Invalidate cached data matching a pattern.

        Args:
            pattern: The cache key pattern to invalidate
        """
        ...

    async def warm_cache(self, ids: list[ID]) -> None:
        """Pre-load entities into cache.

        Args:
            ids: List of entity IDs to pre-load into cache
        """
        ...


__all__ = [
    "RepositoryProtocol",
    "ServiceProtocol",
    "UnitOfWork",
    "TenantAwareRepository",
    "CacheableRepository",
]
