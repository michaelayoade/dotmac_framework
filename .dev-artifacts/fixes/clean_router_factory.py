"""
Clean Router Factory - DRY Migration
Production-ready router factory using standardized patterns.
"""

from typing import Any, Type, Optional, Callable
from uuid import UUID

from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from dotmac_shared.schemas.base import PaginatedResponse
from fastapi import APIRouter, Body, Depends, Path, Query
from pydantic import BaseModel


class RouterFactory:
    """Factory for creating standardized API routers with DRY patterns."""

    @staticmethod
    def create_crud_router(
        service_class: Type,
        create_schema: Type[BaseModel],
        update_schema: Type[BaseModel],
        response_schema: Type[BaseModel],
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
            deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
        ) -> response_schema:
            """Create a new entity."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.create(data, deps.user_id)

        # LIST endpoint
        @router.get("/", response_model=PaginatedResponse[response_schema])
        @standard_exception_handler
        async def list_entities(
            deps: PaginatedDependencies = Depends(get_paginated_deps),  # noqa: B008
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
            deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
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
            deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
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
            deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
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
                deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
            ) -> list[response_schema]:
                """Create multiple entities."""
                service = service_class(deps.db, deps.tenant_id)
                return await service.bulk_create(data, deps.user_id)

            @router.put("/bulk")
            @standard_exception_handler
            async def bulk_update(
                updates: dict[str, update_schema] = Body(...),
                deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
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
                deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
            ) -> dict[str, str]:
                """Delete multiple entities."""
                service = service_class(deps.db, deps.tenant_id)
                await service.bulk_delete(entity_ids, deps.user_id, soft_delete)
                return {"message": f"Deleted {len(entity_ids)} entities successfully"}

        return router

    @staticmethod
    def create_readonly_router(
        service_class: Type,
        response_schema: Type[BaseModel],
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
            deps: PaginatedDependencies = Depends(get_paginated_deps),  # noqa: B008
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
            deps: StandardDependencies = Depends(get_standard_deps),  # noqa: B008
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


# Export the factory
__all__ = ["RouterFactory"]