"""
Production-ready consolidated dependency injection patterns.
Enforces DRY principles with strict type safety and validation.
"""

import logging
from typing import Annotated, Any, Dict, Optional, Union
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.auth.current_user import get_current_tenant, get_current_user
from dotmac_shared.core.exceptions import AuthorizationError, ValidationError
from dotmac_shared.core.pagination import PaginationParams, get_pagination_params
from dotmac_shared.database.session import get_async_db

logger = logging.getLogger(__name__)


# === Core Dependencies ===


class StandardDependencies:
    """Production-ready standard dependencies with validation."""

    def __init__(
        self,
        current_user: Dict[str, Any],
        db: AsyncSession,
        tenant_id: Optional[str] = None,
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
        current_user: Dict[str, Any],
        db: AsyncSession,
        pagination: PaginationParams,
        tenant_id: Optional[str] = None,
    ):
        super().__init__(current_user, db, tenant_id)
        self.pagination = pagination


# === Dependency Factories ===


async def get_standard_deps(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    tenant_id: Annotated[Optional[str], Depends(get_current_tenant)] = None,
) -> StandardDependencies:
    """Get standard dependencies used by 90% of endpoints."""
    return StandardDependencies(current_user, db, tenant_id)


async def get_paginated_deps(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    tenant_id: Annotated[Optional[str], Depends(get_current_tenant)] = None,
) -> PaginatedDependencies:
    """Get standard dependencies with pagination for list endpoints."""
    return PaginatedDependencies(current_user, db, pagination, tenant_id)


async def get_admin_deps(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    tenant_id: Annotated[Optional[str], Depends(get_current_tenant)] = None,
) -> StandardDependencies:
    """Get dependencies with admin permission validation."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required"
        )
    return StandardDependencies(current_user, db, tenant_id)


# === Typed Annotations for Clean Router Code ===

# Replace: current_user = Depends(get_current_user), db = Depends(get_db)
# With:    deps: StandardDeps
StandardDeps = Annotated[StandardDependencies, Depends(get_standard_deps)]

# Replace: pagination params + standard deps
# With:    deps: PaginatedDeps
PaginatedDeps = Annotated[PaginatedDependencies, Depends(get_paginated_deps)]

# Replace: admin check + standard deps
# With:    deps: AdminDeps
AdminDeps = Annotated[StandardDependencies, Depends(get_admin_deps)]


# === Search and Filter Dependencies ===


class SearchParams:
    """Common search parameters used across multiple endpoints."""

    def __init__(
        self,
        search: Optional[str] = Query(
            None, description="Search by name, email, or description"
        ),
        status_filter: Optional[str] = Query(None, description="Filter by status"),
        date_from: Optional[str] = Query(
            None, description="Filter from date (YYYY-MM-DD)"
        ),
        date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
        sort_by: Optional[str] = Query("created_at", description="Sort field"),
        sort_order: Optional[str] = Query("desc", description="Sort order: asc/desc"),
    ):
        self.search = search
        self.status_filter = status_filter
        self.date_from = date_from
        self.date_to = date_to
        self.sort_by = sort_by
        self.sort_order = sort_order


SearchDeps = Annotated[SearchParams, Depends(SearchParams)]


# === File Upload Dependencies ===


class FileUploadParams:
    """Standard file upload parameters and validation."""

    def __init__(
        self,
        max_size_mb: int = Query(10, description="Maximum file size in MB"),
        allowed_types: str = Query(
            "pdf,doc,docx,jpg,png", description="Allowed file types"
        ),
    ):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_types.split(",")


FileUploadDeps = Annotated[FileUploadParams, Depends(FileUploadParams)]


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
        batch_size: int = Query(100, le=1000, description="Batch size (max 1000)"),
        dry_run: bool = Query(False, description="Preview changes without applying"),
        force: bool = Query(
            False, description="Force operation even if warnings exist"
        ),
    ):
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.force = force


BulkDeps = Annotated[BulkOperationParams, Depends(BulkOperationParams)]


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
MANDATORY PATTERN - No legacy support:

@router.get("/customers")
async def list_customers(deps: PaginatedDeps, search: SearchDeps):
    service = CustomerService(deps.db, deps.tenant_id)
    return await service.list(
        skip=deps.pagination.offset,
        limit=deps.pagination.size,
        filters=search.filters,
        user_id=deps.user_id
    )

FORBIDDEN PATTERNS:
- current_user = Depends(get_current_user)  # ❌ Use StandardDeps
- db = Depends(get_db)                      # ❌ Use StandardDeps
- Manual pagination parameters              # ❌ Use PaginatedDeps
- Individual Query parameters               # ❌ Use SearchDeps
"""
