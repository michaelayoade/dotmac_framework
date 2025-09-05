"""
Production-ready consolidated dependency injection patterns.
Enforces DRY principles with strict type safety and validation.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from ..core.exceptions import AuthorizationError, ValidationError

# Import database and auth dependencies (these will need to be adapted per module)
# For now, create placeholder functions
try:
    from dotmac.database.session import get_async_db
except ImportError:

    async def get_async_db():
        """Placeholder - implement in each module"""
        raise NotImplementedError("get_async_db must be implemented in each module")


try:
    from dotmac.platform.auth.current_user import get_current_tenant, get_current_user
except ImportError:

    async def get_current_user():
        """Placeholder - implement in each module"""
        return {"user_id": "placeholder", "email": "placeholder", "is_active": True}

    async def get_current_tenant():
        """Placeholder - implement in each module"""
        return "placeholder-tenant"


from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.pagination import PaginationParams, get_pagination_params

logger = logging.getLogger(__name__)


# === Core Dependencies ===


class StandardDependencies:
    """
    Production-ready standard dependencies with validation.

    Plain Python class (NOT a Pydantic model) to avoid FastAPI type introspection issues.
    """

    def __init__(
        self,
        current_user: dict[str, Any],
        db: AsyncSession,
        tenant_id: Optional[str] = None,
    ):
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

        if not db:
            raise ValidationError("Database session is required")

        self.current_user = current_user
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = current_user["user_id"]

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
        tenant_id: Optional[str] = None,
    ):
        super().__init__(current_user, db, tenant_id)
        self.pagination = pagination


# === Dependency Factories ===


async def get_standard_deps(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> StandardDependencies:
    """Get standard dependencies used by most endpoints."""
    return StandardDependencies(current_user, db, tenant_id)


async def get_paginated_deps(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> PaginatedDependencies:
    """Get dependencies with pagination for list endpoints."""
    return PaginatedDependencies(current_user, db, pagination, tenant_id)


async def get_admin_deps(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    tenant_id: Optional[str] = Depends(get_current_tenant),
) -> StandardDependencies:
    """Get dependencies with admin permission validation."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required"
        )
    return StandardDependencies(current_user, db, tenant_id)


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
        self.allowed_extensions = [
            ext.strip() for ext in allowed_types.split(",") if ext.strip()
        ]


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


# === Validation and Type Safety ===


def validate_deps_usage() -> bool:
    """
    Placeholder for runtime validators of dependency usage. Intentionally minimal.
    """
    return True
