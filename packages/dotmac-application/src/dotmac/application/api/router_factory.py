"""
Clean Router Factory - DRY Migration
Production-ready router factory using standardized patterns.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query
from pydantic import BaseModel

from dotmac.application.dependencies.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from dotmac.core.schemas.base_schemas import PaginatedResponseSchema

# Type alias for cleaner imports
PaginatedResponse = PaginatedResponseSchema


# Service Protocol for better type safety
@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol defining the expected interface for services used with RouterFactory."""

    async def create(self, data: BaseModel, user_id: Any) -> BaseModel:
        """Create a new entity."""
        ...

    async def list(self, skip: int, limit: int, user_id: Any) -> list[BaseModel]:
        """List entities with pagination."""
        ...

    async def count(self, user_id: Any) -> int:
        """Count total entities."""
        ...

    async def get_by_id(self, entity_id: UUID, user_id: Any) -> BaseModel:
        """Get entity by ID."""
        ...

    async def update(self, entity_id: UUID, data: BaseModel, user_id: Any) -> BaseModel:
        """Update an entity."""
        ...

    async def delete(self, entity_id: UUID, user_id: Any, soft_delete: bool = True) -> None:
        """Delete an entity."""
        ...

    # Optional bulk operations
    async def bulk_create(self, data: list[BaseModel], user_id: Any) -> list[BaseModel]:
        """Bulk create entities."""
        ...

    async def bulk_update(self, updates: dict[str, BaseModel], user_id: Any) -> None:
        """Bulk update entities."""
        ...

    async def bulk_delete(self, entity_ids: list[UUID], user_id: Any, soft_delete: bool = True) -> None:
        """Bulk delete entities."""
        ...


class RouterFactory:
    """Factory for creating standardized API routers with DRY patterns."""

    @staticmethod
    def create_crud_router(
        service_class: type[ServiceProtocol],
        create_schema: type[BaseModel],
        update_schema: type[BaseModel],
        response_schema: type[BaseModel],
        prefix: str,
        tags: list[str] | None = None,
        enable_search: bool = False,
        enable_bulk_operations: bool = False,
    ) -> APIRouter:
        """Create a complete CRUD router with standardized endpoints."""
        from dotmac.application import standard_exception_handler

        router = APIRouter(prefix=prefix, tags=tags or [])

        # CREATE endpoint
        @router.post("/", response_model=response_schema, status_code=201)
        @standard_exception_handler
        async def create_entity(
            data: create_schema = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps),
        ) -> response_schema:
            """Create a new entity."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.create(data, deps.user_id)

        # LIST endpoint
        @router.get("/", response_model=PaginatedResponse[response_schema])
        @standard_exception_handler
        async def list_entities(
            deps: PaginatedDependencies = Depends(get_paginated_deps),
        ) -> PaginatedResponse[response_schema]:
            """List entities with pagination."""
            service = service_class(deps.db, deps.tenant_id)

            items = await service.list(
                skip=deps.pagination.offset,
                limit=deps.pagination.size,
                user_id=deps.user_id,
            )
            total = await service.count(deps.user_id)

            return PaginatedResponse(
                items=items,
                total=total,
                page=deps.pagination.page,
                size=deps.pagination.size,
            )

        # GET endpoint
        @router.get("/{entity_id}", response_model=response_schema)
        @standard_exception_handler
        async def get_entity(
            entity_id: UUID = Path(..., description="ID of the entity to retrieve"),
            deps: StandardDependencies = Depends(get_standard_deps),
        ) -> response_schema:
            """Get a specific entity by ID."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_by_id(entity_id, deps.user_id)

        # UPDATE endpoint
        @router.put("/{entity_id}", response_model=response_schema)
        @standard_exception_handler
        async def update_entity(
            entity_id: UUID = Path(..., description="ID of the entity to update"),
            data: update_schema = Body(...),
            deps: StandardDependencies = Depends(get_standard_deps),
        ) -> response_schema:
            """Update a specific entity."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.update(entity_id, data, deps.user_id)

        # DELETE endpoint
        @router.delete("/{entity_id}")
        @standard_exception_handler
        async def delete_entity(
            entity_id: UUID = Path(..., description="ID of the entity to delete"),
            soft_delete: bool = Query(True, description="Perform soft delete"),
            deps: StandardDependencies = Depends(get_standard_deps),
        ) -> dict[str, str]:
            """Delete a specific entity."""
            service = service_class(deps.db, deps.tenant_id)
            await service.delete(entity_id, deps.user_id, soft_delete)
            return {"message": "Entity deleted successfully"}

        # Bulk operations if enabled
        if enable_bulk_operations:

            @router.post("/bulk", response_model=list[response_schema])
            @standard_exception_handler
            async def bulk_create(
                data: list[create_schema] = Body(..., max_length=100),
                deps: StandardDependencies = Depends(get_standard_deps),
            ) -> list[response_schema]:
                """Create multiple entities."""
                service = service_class(deps.db, deps.tenant_id)
                return await service.bulk_create(data, deps.user_id)

            @router.put("/bulk")
            @standard_exception_handler
            async def bulk_update(
                updates: dict[str, update_schema] = Body(...),
                deps: StandardDependencies = Depends(get_standard_deps),
            ) -> dict[str, str]:
                """Update multiple entities by ID."""
                service = service_class(deps.db, deps.tenant_id)
                await service.bulk_update(updates, deps.user_id)
                return {"message": f"Updated {len(updates)} entities successfully"}

            @router.delete("/bulk")
            @standard_exception_handler
            async def bulk_delete(
                entity_ids: list[UUID] = Body(..., max_length=100),
                soft_delete: bool = Query(True, description="Perform soft delete"),
                deps: StandardDependencies = Depends(get_standard_deps),
            ) -> dict[str, str]:
                """Delete multiple entities."""
                service = service_class(deps.db, deps.tenant_id)
                await service.bulk_delete(entity_ids, deps.user_id, soft_delete)
                return {"message": f"Deleted {len(entity_ids)} entities successfully"}

        return router

    @staticmethod
    def create_readonly_router(
        service_class: type,
        response_schema: type[BaseModel],
        prefix: str,
        tags: list[str] | None = None,
        enable_search: bool = True,
    ) -> APIRouter:
        """Create a read-only router for resources that only support GET operations."""
        from dotmac.application import standard_exception_handler

        router = APIRouter(prefix=prefix, tags=tags or [])

        # LIST endpoint
        @router.get("/", response_model=PaginatedResponse[response_schema])
        @standard_exception_handler
        async def list_entities(
            deps: PaginatedDependencies = Depends(get_paginated_deps),
        ) -> PaginatedResponse[response_schema]:
            """List entities with pagination."""
            service = service_class(deps.db, deps.tenant_id)

            items = await service.list(
                skip=deps.pagination.offset,
                limit=deps.pagination.size,
                user_id=deps.user_id,
            )
            total = await service.count(deps.user_id)

            return PaginatedResponse(
                items=items,
                total=total,
                page=deps.pagination.page,
                size=deps.pagination.size,
            )

        # GET endpoint
        @router.get("/{entity_id}", response_model=response_schema)
        @standard_exception_handler
        async def get_entity(
            entity_id: UUID = Path(..., description="ID of the entity to retrieve"),
            deps: StandardDependencies = Depends(get_standard_deps),
        ) -> response_schema:
            """Get a specific entity by ID."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_by_id(entity_id, deps.user_id)

        return router

    @staticmethod
    def create_standard_router(
        prefix: str,
        tags: list[str] | None = None,
    ) -> APIRouter:
        """Create a basic router for custom endpoints."""
        return APIRouter(prefix=prefix, tags=tags or [])


# Convenience functions for backward compatibility
def create_crud_router(
    service_class: type,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    response_schema: type[BaseModel],
    prefix: str,
    tags: list[str] | None = None,
    enable_search: bool = False,
    enable_bulk_operations: bool = False,
) -> APIRouter:
    """Convenience function for RouterFactory.create_crud_router."""
    return RouterFactory.create_crud_router(
        service_class=service_class,
        create_schema=create_schema,
        update_schema=update_schema,
        response_schema=response_schema,
        prefix=prefix,
        tags=tags,
        enable_search=enable_search,
        enable_bulk_operations=enable_bulk_operations,
    )

def create_router(prefix: str, tags: list[str] | None = None) -> APIRouter:
    """Convenience function for RouterFactory.create_standard_router."""
    return RouterFactory.create_standard_router(prefix=prefix, tags=tags)

# Export the factory and convenience functions
__all__ = ["RouterFactory", "create_crud_router", "create_router"]
