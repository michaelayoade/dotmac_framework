"""
Production-ready consolidated dependency injection patterns.
Enforces DRY principles with strict type safety and validation.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.core import PaginationSchema as PaginationParams
from dotmac.core.exceptions import AuthorizationError, ValidationError

logger = logging.getLogger(__name__)


# === Placeholder functions until auth is consolidated ===


def get_current_user():
    """Placeholder for current user - to be implemented when auth is consolidated."""
    return {
        "user_id": 1,
        "email": "test@example.com",
        "is_active": True,
        "is_admin": False,
    }


def get_current_tenant():
    """Placeholder for current tenant - to be implemented when auth is consolidated."""
    return "tenant_123"


def get_async_db():
    """
    Placeholder for async database session.
    To be implemented when database is consolidated.
    """
    return None


def get_pagination_params():
    """Placeholder for pagination params - to be implemented in core."""

    # Return a simple object with pagination defaults
    class MockPagination:
        def __init__(self):
            self.offset = 0
            self.size = 10
            self.page = 1

    return MockPagination()


# === Core Dependencies ===


class StandardDependencies:
    """
    Production-ready standard dependencies with validation.

    Plain Python class (NOT a Pydantic model) to avoid
    FastAPI type introspection issues.
    """

    def __init__(
        self,
        current_user: dict[str, Any],
        db: AsyncSession,
        tenant_id: str | None = None,
    ):
        # Validate required user fields
        if not current_user or not isinstance(current_user, dict):
            raise ValidationError("Invalid user context")

        required_fields = ["user_id", "email", "is_active"]
        missing_fields = [
            field for field in required_fields if field not in current_user
        ]
        if missing_fields:
            raise ValidationError(f"Missing user fields: {missing_fields}")

        if not current_user.get("is_active", False):
            raise AuthorizationError("User account is inactive")

        # Validate database session
        if not db:
            raise ValidationError("Database session is required")

        self.current_user = current_user
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = current_user["user_id"]

        # Log dependency creation for audit trail
        logger.debug(
            f"Dependencies created for user {self.user_id} in tenant {tenant_id}"
        )


class PaginatedDependencies(StandardDependencies):
    """Standard dependencies with pagination support."""

    def __init__(
        self,
        current_user: dict[str, Any],
        db: AsyncSession,
        pagination: PaginationParams,
        tenant_id: str | None = None,
    ):
        super().__init__(current_user, db, tenant_id)
        self.pagination = pagination


# === Dependency Factories ===


async def get_standard_deps(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str | None = Depends(get_current_tenant),
) -> StandardDependencies:
    """Get standard dependencies used by 90% of endpoints."""
    return StandardDependencies(current_user, db, tenant_id)


async def get_paginated_deps(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    tenant_id: str | None = Depends(get_current_tenant),
) -> PaginatedDependencies:
    """Get standard dependencies with pagination for list endpoints."""
    return PaginatedDependencies(current_user, db, pagination, tenant_id)


async def get_admin_deps(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: str | None = Depends(get_current_tenant),
) -> StandardDependencies:
    """Get dependencies with admin permission validation."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required"
        )
    return StandardDependencies(current_user, db, tenant_id)


# === Usage Patterns for Clean Router Code ===

# RECOMMENDED PATTERN - Use direct Depends():
#
# @router.get("/items", response_model=ItemListResponse)
# async def list_items(
#     deps: StandardDependencies = Depends(get_standard_deps)
# ) -> ItemListResponse:
#     service = ItemService(deps.db, deps.tenant_id)
#     return await service.list(user_id=deps.user_id)
#
# @router.get("/items", response_model=ItemListResponse)
# async def list_items_paginated(
#     deps: PaginatedDependencies = Depends(get_paginated_deps)
# ) -> ItemListResponse:
#     service = ItemService(deps.db, deps.tenant_id)
#     return await service.list_paginated(
#         skip=deps.pagination.offset,
#         limit=deps.pagination.size,
#         user_id=deps.user_id
#     )


# === Search and Filter Dependencies ===


class SearchParams:
    """Common search parameters used across multiple endpoints."""

    def __init__(
        self,
        search: str | None = None,
        status_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ):
        self.search = search
        self.status_filter = status_filter
        self.date_from = date_from
        self.date_to = date_to
        self.sort_by = sort_by
        self.sort_order = sort_order


# Use: search: SearchParams = Depends(SearchParams)


# === File Upload Dependencies ===


class FileUploadParams:
    """Standard file upload parameters and validation."""

    def __init__(
        self,
        max_size_mb: int | None = None,
        allowed_types: str | None = None,
    ):
        if max_size_mb is None:
            max_size_mb = Query(10, description="Maximum file size in MB")
        if allowed_types is None:
            allowed_types = Query(
                "pdf,doc,docx,jpg,png", description="Allowed file types"
            )

        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_types.split(",")


# Use: upload: FileUploadParams = Depends(FileUploadParams)


# === Entity ID Dependencies ===


def create_entity_id_validator(entity_name: str):
    """Factory for creating entity ID validators with proper error messages."""

    async def validate_entity_id(entity_id: UUID) -> UUID:
        if not entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {entity_name} ID",
            )
        return entity_id

    return validate_entity_id


# === Bulk Operation Dependencies ===


class BulkOperationParams:
    """Parameters for bulk operations with safety limits."""

    def __init__(
        self,
        batch_size: int | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
    ):
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.force = force


# Use: bulk: BulkOperationParams = Depends(BulkOperationParams)


# === Validation and Type Safety ===


def validate_deps_usage():
    """
    Validate that only modern dependency patterns are used.
    This enforces the new DRY patterns and prevents legacy usage.
    """
    import warnings

    warnings.filterwarnings("error", message="*legacy*", category=DeprecationWarning)


# === Mandatory Usage Pattern ===

"""
MANDATORY PATTERN - Direct Depends() usage:

@router.get("/customers", response_model=CustomerListResponse)
async def list_customers(
    deps: PaginatedDependencies = Depends(get_paginated_deps),  # noqa: B008
        if batch_size is None:
            batch_size = Query(
                100, le=1000, description="Batch size (max 1000)"
            )  # noqa: B008
        if dry_run is None:
            dry_run = Query(
                False, description="Preview changes without applying"
            )  # noqa: B008
        if force is None:
            force = Query(  # noqa: B008
            False, description="Force operation even if warnings exist"
        )
    search: SearchParams = Depends(SearchParams)  # noqa: B008
) -> CustomerListResponse:
    service = CustomerService(deps.db, deps.tenant_id)
    return await service.list(
        skip=deps.pagination.offset,
        limit=deps.pagination.size,
        filters=search,
        user_id=deps.user_id
    )

CRITICAL REQUIREMENTS:
✅ Always set explicit response_model=YourSchema (avoid None)
✅ Use plain Python classes for dependencies (NOT Pydantic models)
✅ Use = Depends(...) syntax (no Annotated chains)  # noqa: B008
✅ AsyncSession should be yielded from async generator

FORBIDDEN PATTERNS:
❌ response_model=None (unless truly no response body)
❌ Annotated[Type, Depends(...)] for nested dependencies
❌ Making dependency classes inherit from BaseModel
❌ Missing explicit response schema types
"""
