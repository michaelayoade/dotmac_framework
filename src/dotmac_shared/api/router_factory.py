"""
Production-ready router factory enforcing strict DRY patterns.
Manual router creation is FORBIDDEN - use factory methods only.
"""

import functools
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.dependencies import (
    AdminDeps,
    PaginatedDeps,
    SearchDeps,
    StandardDeps,
)
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit
from dotmac_shared.schemas.base_schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
    PaginatedResponseSchema,
)

logger = logging.getLogger(__name__)


class RouterValidationError(Exception):
    """Raised when routers don't follow DRY factory patterns."""

    pass


ServiceType = TypeVar("ServiceType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseCreateSchema)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseUpdateSchema)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseResponseSchema)


class RouterFactory:
    """
    MANDATORY router factory - direct APIRouter usage is FORBIDDEN.
    All routers MUST be created through factory methods.
    """

    @classmethod
    def create_crud_router(
        cls,
        service_class: Type[ServiceType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        response_schema: Type[ResponseSchemaType],
        prefix: str,
        tags: List[str],
        require_admin: bool = False,
        enable_search: bool = True,
        enable_bulk_operations: bool = False,
        custom_endpoints: Optional[List[Callable]] = None,
    ) -> APIRouter:
        """
        Create production-ready CRUD router with strict validation.

        This is the ONLY approved way to create routers.
        """
        # Validate all required parameters
        cls._validate_router_params(
            service_class, create_schema, update_schema, response_schema, prefix, tags
        )
        # Create router with enhanced metadata
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
        # Log router creation for audit
        logger.info(f"Created CRUD router: {prefix} with tags {tags}")

        # Choose dependency type based on admin requirement
        deps_type = AdminDeps if require_admin else StandardDeps

        # === CREATE ENDPOINT ===
        @router.post("/", response_model=response_schema, status_code=201)
        @rate_limit(
            max_requests=30, time_window_seconds=60
        )  # Moderate limit for creation
        @standard_exception_handler
        async def create_entity(
            data: create_schema = Body(...), deps: deps_type = Depends()
        ) -> response_schema:
            """Create a new entity."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.create(data, deps.user_id)

        # === LIST ENDPOINT ===
        @router.get("/", response_model=PaginatedResponseSchema[response_schema])
        @rate_limit(
            max_requests=100, time_window_seconds=60
        )  # Higher limit for read operations
        @standard_exception_handler
        async def list_entities(
            deps: PaginatedDeps,
            search: SearchDeps = Depends() if enable_search else None,
        ) -> PaginatedResponseSchema[response_schema]:
            """List entities with pagination and optional search."""
            service = service_class(deps.db, deps.tenant_id)

            filters = {}
            if search:
                if search.query:
                    filters["search"] = search.query
                if search.filters:
                    filters.update(search.filters)

            items = await service.list(
                skip=deps.pagination.offset,
                limit=deps.pagination.size,
                filters=filters,
                order_by=search.sort_by if search else "created_at",
                user_id=deps.user_id,
            )
            total = await service.count(filters, deps.user_id)

            return PaginatedResponseSchema(
                items=items,
                total=total,
                page=deps.pagination.page,
                size=deps.pagination.size,
            )

        # === GET ENDPOINT ===
        @router.get("/{entity_id}", response_model=response_schema)
        @rate_limit(
            max_requests=200, time_window_seconds=60
        )  # High limit for individual reads
        @standard_exception_handler
        async def get_entity(
            entity_id: UUID = Path(..., description=f"ID of the entity to retrieve"),
            deps: deps_type = Depends(),
        ) -> response_schema:
            """Get a specific entity by ID."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_by_id(entity_id, deps.user_id)

        # === UPDATE ENDPOINT ===
        @router.put("/{entity_id}", response_model=response_schema)
        @rate_limit(
            max_requests=50, time_window_seconds=60
        )  # Moderate limit for updates
        @standard_exception_handler
        async def update_entity(
            entity_id: UUID = Path(..., description=f"ID of the entity to update"),
            data: update_schema = Body(...),
            deps: deps_type = Depends(),
        ) -> response_schema:
            """Update a specific entity."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.update(entity_id, data, deps.user_id)

        # === DELETE ENDPOINT ===
        @router.delete("/{entity_id}")
        @rate_limit(
            max_requests=20, time_window_seconds=60
        )  # Strict limit for deletions
        @standard_exception_handler
        async def delete_entity(
            entity_id: UUID = Path(..., description=f"ID of the entity to delete"),
            soft_delete: bool = Query(True, description="Perform soft delete"),
            deps: deps_type = Depends(),
        ) -> Dict[str, str]:
            """Delete a specific entity."""
            service = service_class(deps.db, deps.tenant_id)
            await service.delete(entity_id, deps.user_id, soft_delete)
            return {"message": "Entity deleted successfully"}

        # === BULK OPERATIONS ===
        if enable_bulk_operations:

            @router.post("/bulk", response_model=List[response_schema])
            @rate_limit(
                max_requests=5, time_window_seconds=60
            )  # Very strict for bulk creation
            @standard_exception_handler
            async def bulk_create(
                data: List[create_schema] = Body(..., max_length=100),
                deps: deps_type = Depends(),
            ) -> List[response_schema]:
                """Create multiple entities in a single request."""
                service = service_class(deps.db, deps.tenant_id)
                return await service.bulk_create(data, deps.user_id)

            @router.put("/bulk")
            @rate_limit(
                max_requests=5, time_window_seconds=60
            )  # Very strict for bulk updates
            @standard_exception_handler
            async def bulk_update(
                updates: Dict[str, update_schema] = Body(...),
                deps: deps_type = Depends(),
            ) -> Dict[str, str]:
                """Update multiple entities by ID."""
                service = service_class(deps.db, deps.tenant_id)
                updated_count = await service.bulk_update(updates, deps.user_id)
                return {"message": f"Updated {updated_count} entities"}

            @router.delete("/bulk")
            @rate_limit(
                max_requests=3, time_window_seconds=60
            )  # Extremely strict for bulk deletions
            @standard_exception_handler
            async def bulk_delete(
                entity_ids: List[UUID] = Body(..., max_length=100),
                soft_delete: bool = Query(True),
                deps: deps_type = Depends(),
            ) -> Dict[str, str]:
                """Delete multiple entities."""
                service = service_class(deps.db, deps.tenant_id)
                deleted_count = await service.bulk_delete(
                    entity_ids, deps.user_id, soft_delete
                )
                return {"message": f"Deleted {deleted_count} entities"}

        # === CUSTOM ENDPOINTS ===
        if custom_endpoints:
            for endpoint_func in custom_endpoints:
                # Register custom endpoints with the router
                # Assumes custom endpoints are already decorated with route decorators
                router.include_router(endpoint_func)

        return router

    @classmethod
    def create_readonly_router(
        cls,
        service_class: Type[ServiceType],
        response_schema: Type[ResponseSchemaType],
        prefix: str,
        tags: List[str],
        enable_search: bool = True,
    ) -> APIRouter:
        """Create a read-only router with list and get endpoints only."""
        router = APIRouter(prefix=prefix, tags=tags)

        @router.get("/", response_model=PaginatedResponseSchema[response_schema])
        @standard_exception_handler
        async def list_entities(
            deps: PaginatedDeps,
            search: SearchDeps = Depends() if enable_search else None,
        ):
            """List entities with pagination."""
            service = service_class(deps.db, deps.tenant_id)

            filters = {}
            if search and search.query:
                filters["search"] = search.query

            items = await service.list(
                skip=deps.pagination.offset,
                limit=deps.pagination.size,
                filters=filters,
                user_id=deps.user_id,
            )
            total = await service.count(filters, deps.user_id)

            return PaginatedResponseSchema(
                items=items,
                total=total,
                page=deps.pagination.page,
                size=deps.pagination.size,
            )

        @router.get("/{entity_id}", response_model=response_schema)
        @standard_exception_handler
        async def get_entity(
            entity_id: UUID = Path(...), deps: StandardDeps = Depends()
        ):
            """Get entity by ID."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_by_id(entity_id, deps.user_id)

        return router


# === Specialized Router Factories ===


class BillingRouterFactory(RouterFactory):
    """Specialized router factory for billing-related entities."""

    @classmethod
    def create_invoice_router(
        cls, service_class, schemas, prefix="/invoices"
    ) -> APIRouter:
        """Create router for invoice management."""
        router = cls.create_crud_router(
            service_class=service_class,
            create_schema=schemas["create"],
            update_schema=schemas["update"],
            response_schema=schemas["response"],
            prefix=prefix,
            tags=["billing", "invoices"],
            enable_search=True,
            enable_bulk_operations=True,
        )

        # Add billing-specific endpoints
        @router.post("/{invoice_id}/payments", response_model=schemas["response"])
        @standard_exception_handler
        async def record_payment(
            invoice_id: UUID = Path(...),
            payment_data: Dict[str, Any] = Body(...),
            deps: StandardDeps = Depends(),
        ):
            """Record payment for an invoice."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.record_payment(invoice_id, payment_data, deps.user_id)

        @router.get("/{invoice_id}/pdf")
        @standard_exception_handler
        async def generate_pdf(
            invoice_id: UUID = Path(...), deps: StandardDeps = Depends()
        ):
            """Generate PDF for invoice."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.generate_pdf(invoice_id, deps.user_id)

        return router


class CustomerRouterFactory(RouterFactory):
    """Specialized router factory for customer-related entities."""

    @classmethod
    def create_customer_router(
        cls, service_class, schemas, prefix="/customers"
    ) -> APIRouter:
        """Create router for customer management."""
        router = cls.create_crud_router(
            service_class=service_class,
            create_schema=schemas["create"],
            update_schema=schemas["update"],
            response_schema=schemas["response"],
            prefix=prefix,
            tags=["customers"],
            enable_search=True,
            enable_bulk_operations=True,
        )

        # Add customer-specific endpoints
        @router.get("/{customer_id}/services")
        @standard_exception_handler
        async def get_customer_services(
            customer_id: UUID = Path(...), deps: StandardDeps = Depends()
        ):
            """Get all services for a customer."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.get_customer_services(customer_id, deps.user_id)

        @router.post("/{customer_id}/suspend")
        @standard_exception_handler
        async def suspend_customer(
            customer_id: UUID = Path(...),
            reason: str = Body(..., embed=True),
            deps: StandardDeps = Depends(),
        ):
            """Suspend a customer account."""
            service = service_class(deps.db, deps.tenant_id)
            return await service.suspend_customer(customer_id, reason, deps.user_id)

        return router

    @classmethod
    def _validate_router_params(
        cls,
        service_class: Type,
        create_schema: Type,
        update_schema: Type,
        response_schema: Type,
        prefix: str,
        tags: List[str],
    ):
        """Validate router factory parameters."""
        if not service_class:
            raise RouterValidationError("service_class is required")

        if not issubclass(create_schema, BaseCreateSchema):
            raise RouterValidationError(
                f"create_schema must inherit from BaseCreateSchema"
            )

        if not issubclass(update_schema, BaseUpdateSchema):
            raise RouterValidationError(
                f"update_schema must inherit from BaseUpdateSchema"
            )

        if not issubclass(response_schema, BaseResponseSchema):
            raise RouterValidationError(
                f"response_schema must inherit from BaseResponseSchema"
            )

        if not prefix.startswith("/"):
            raise RouterValidationError(f"prefix must start with '/', got: {prefix}")

        if not tags:
            raise RouterValidationError("tags list cannot be empty")

        # Validate service class has required methods
        required_methods = ["create", "get_by_id", "update", "delete", "list", "count"]
        for method in required_methods:
            if not hasattr(service_class, method):
                raise RouterValidationError(
                    f"Service class missing required method: {method}"
                )


# === Strict Enforcement ===


def validate_no_manual_routers():
    """Validate that no manual APIRouter instances exist."""
    import gc
    import sys

    # Check for direct APIRouter instantiation in production
    if "prod" in sys.argv or "gunicorn" in sys.argv[0]:
        for obj in gc.get_objects():
            if isinstance(obj, APIRouter) and not getattr(
                obj, "_factory_created", False
            ):
                logger.warning(
                    f"Found manual APIRouter: {obj.prefix}. Use RouterFactory instead."
                )


def enforce_router_patterns():
    """Decorator to enforce RouterFactory usage."""

    def decorator(func):
        """Handle decorator request."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Handle wrapper request."""
            # Check if function is trying to create manual routers
            if "APIRouter" in func.__code__.co_names:
                caller_frame = inspect.currentframe().f_back
                if "RouterFactory" not in str(caller_frame.f_locals):
                    raise RouterValidationError(
                        f"Function {func.__name__} must use RouterFactory instead of manual APIRouter"
                    )
            return func(*args, **kwargs)

        return wrapper

    return decorator


# === Usage Examples ===

"""
BEFORE (70+ lines of repetitive CRUD code per router):
router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerResponse)
async def create_customer(
    data: CustomerCreate,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        service = CustomerService(db)
        return await service.create_customer(data, current_user.id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)
    # ... repeat for all CRUD operations

AFTER (3 lines with RouterFactory):
router = RouterFactory.create_crud_router(
    service_class=CustomerService,
    create_schema=CustomerCreate,
    update_schema=CustomerUpdate,
    response_schema=CustomerResponse,
    prefix="/customers",
    tags=["customers"],
    enable_search=True,
    enable_bulk_operations=True)
# All CRUD endpoints created automatically with:
# - Proper exception handling
# - Standardized responses
# - Input validation
# - Documentation
# - Authentication
# - Pagination
# - Search functionality
"""
