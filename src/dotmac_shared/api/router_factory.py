"""
from __future__ import annotations
Production-ready router factory enforcing strict DRY patterns.
All routers should be created via factory methods in this module.
"""

import logging
from collections.abc import Callable
from typing import Any, Optional, TypeVar
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query

from ..schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
    PaginatedResponseSchema,
)
from .dependencies import (
    PaginatedDependencies,
    SearchParams,
    StandardDependencies,
    get_admin_deps,
    get_paginated_deps,
    get_standard_deps,
)
from .exception_handlers import standard_exception_handler
from .rate_limiting import rate_limit

logger = logging.getLogger(__name__)


ServiceType = TypeVar("ServiceType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseCreateSchema)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseUpdateSchema)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseResponseSchema)


class RouterValidationError(Exception):
    """Raised when routers don't follow DRY factory patterns."""


class RouterFactory:
    """Factory for building consistent CRUD routers."""

    @classmethod
    def create_crud_router(
        cls,
        service_class: type[ServiceType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        prefix: str,
        tags: list[str],
        require_admin: bool = False,
        enable_search: bool = True,
        enable_bulk_operations: bool = False,
        custom_endpoints: Optional[list[Callable]] = None,
    ) -> APIRouter:
        """Create a basic CRUD router for a service."""
        cls._validate_router_params(service_class, create_schema, update_schema, response_schema, prefix, tags)

        router = APIRouter(
            prefix=prefix,
            tags=tags,
            responses={
                400: {"description": "Validation Error"},
                401: {"description": "Authentication Error"},
                403: {"description": "Authorization Error"},
                404: {"description": "Not Found"},
                500: {"description": "Internal Server Error"},
            },
        )

        deps_provider = get_admin_deps if require_admin else get_standard_deps

        # CREATE
        @router.post("/", response_model=response_schema, status_code=201)
        @rate_limit(max_requests=30, time_window_seconds=60)
        @standard_exception_handler
        async def create_entity(
            data: create_schema = Body(...),
            deps: StandardDependencies = Depends(deps_provider),
        ) -> Any:
            service = service_class(deps.db, deps.tenant_id)
            return await service.create(data, deps.user_id)

        # LIST
        @router.get("/", response_model=PaginatedResponseSchema[response_schema])
        @rate_limit(max_requests=100, time_window_seconds=60)
        @standard_exception_handler
        async def list_entities(
            deps: PaginatedDependencies = Depends(get_paginated_deps),
            search: SearchParams = Depends(SearchParams),
        ) -> Any:
            service = service_class(deps.db, deps.tenant_id)
            filters: dict[str, Any] = {}
            if enable_search:
                if search.search:
                    filters["search"] = search.search
                if search.status_filter:
                    filters["status"] = search.status_filter

            items = await service.list(
                skip=deps.pagination.offset,
                limit=deps.pagination.size,
                filters=filters,
                order_by=search.sort_by,
                user_id=deps.user_id,
            )
            total = await service.count(filters, deps.user_id)

            return PaginatedResponseSchema(
                items=items,
                total=total,
                page=deps.pagination.page,
                size=deps.pagination.size,
            )

        # GET
        @router.get("/{entity_id}", response_model=response_schema)
        @rate_limit(max_requests=200, time_window_seconds=60)
        @standard_exception_handler
        async def get_entity(
            entity_id: UUID = Path(..., description="ID of the entity to retrieve"),
            deps: StandardDependencies = Depends(deps_provider),
        ) -> Any:
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_by_id(entity_id, deps.user_id)

        # UPDATE
        @router.put("/{entity_id}", response_model=response_schema)
        @rate_limit(max_requests=50, time_window_seconds=60)
        @standard_exception_handler
        async def update_entity(
            entity_id: UUID = Path(..., description="ID of the entity to update"),
            data: update_schema = Body(...),
            deps: StandardDependencies = Depends(deps_provider),
        ) -> Any:
            service = service_class(deps.db, deps.tenant_id)
            return await service.update(entity_id, data, deps.user_id)

        # DELETE
        @router.delete("/{entity_id}")
        @rate_limit(max_requests=20, time_window_seconds=60)
        @standard_exception_handler
        async def delete_entity(
            entity_id: UUID = Path(..., description="ID of the entity to delete"),
            soft_delete: bool = Query(True, description="Perform soft delete"),
            deps: StandardDependencies = Depends(deps_provider),
        ) -> dict[str, str]:
            service = service_class(deps.db, deps.tenant_id)
            await service.delete(entity_id, deps.user_id, soft_delete)
            return {"message": "Entity deleted successfully"}

        # Optionally attach any custom endpoints
        if custom_endpoints:
            for ep in custom_endpoints:
                router.add_api_route(**ep())  # custom factory returns kwargs for add_api_route

        return router

    @classmethod
    def create_standard_router(
        cls,
        prefix: str = "",
        tags: Optional[list[str]] = None,
        dependencies: Optional[list] = None,
    ) -> APIRouter:
        """Create a standard router with common configuration."""
        return APIRouter(prefix=prefix, tags=tags or [], dependencies=dependencies or [])

    @staticmethod
    def _validate_router_params(
        service_class: type[Any],
        create_schema: type[Any],
        update_schema: type[Any],
        response_schema: type[Any],
        prefix: str,
        tags: list[str],
    ) -> None:
        if not isinstance(prefix, str) or not prefix.startswith("/"):
            raise RouterValidationError("prefix must start with '/'")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise RouterValidationError("tags must be a list of strings")
        # Basic sanity checks for provided classes
        for cls in (service_class, create_schema, update_schema, response_schema):
            if not isinstance(cls, type):
                raise RouterValidationError("service and schema arguments must be types")
