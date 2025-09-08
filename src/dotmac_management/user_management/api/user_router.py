"""
User Management API Router - DRY Migration
Production-ready user management using RouterFactory patterns.
"""

from typing import Any
from uuid import UUID

from fastapi import Body, Depends, Path, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import StandardDependencies, get_standard_deps

from ..schemas.user_schemas import (
    UserCreateSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from ..services.user_service import UserService

# === Additional Request Schemas ===


class UserSearchRequest(BaseModel):
    """User search request schema."""

    query: str | None = Field(None, description="Search query")
    filters: dict[str, Any] = Field(default_factory=dict, description="Search filters")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")


class BulkUserOperation(BaseModel):
    """Bulk user operation request."""

    operation: str = Field(..., description="Operation type (activate, deactivate, delete)")
    user_ids: list[UUID] = Field(..., description="List of user IDs")
    reason: str | None = Field(None, description="Operation reason")


# === Main User Router ===

user_router = RouterFactory.create_crud_router(
    service_class=UserService,
    create_schema=UserCreateSchema,
    update_schema=UserUpdateSchema,
    response_schema=UserResponseSchema,
    prefix="/users",
    tags=["users", "user-management"],
    enable_search=True,
    enable_bulk_operations=True,
)


# === User Profile Management ===


@user_router.get("/me", response_model=UserResponseSchema)
@standard_exception_handler
async def get_current_user_profile(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Get current user's profile."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.get_user(deps.user_id, include_profile=True)


@user_router.put("/me", response_model=UserResponseSchema)
@standard_exception_handler
async def update_current_user_profile(
    user_data: UserUpdateSchema,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Update current user's profile."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.update_user(
        user_id=UUID(deps.user_id),
        user_data=user_data,
        updated_by=UUID(deps.user_id),
    )


# === User Search ===


@user_router.post("/search", response_model=dict[str, Any])
@standard_exception_handler
async def search_users(
    search_request: UserSearchRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Search users with advanced filtering."""
    service = UserService(deps.db, deps.tenant_id)
    users, total_count = await service.search_users(search_request)

    return {
        "items": users,
        "total": total_count,
        "page": search_request.page,
        "page_size": search_request.page_size,
        "total_pages": (total_count // search_request.page_size) + (1 if total_count % search_request.page_size else 0),
    }


@user_router.get("/username/{username}", response_model=UserResponseSchema)
@standard_exception_handler
async def get_user_by_username(
    username: str = Path(..., description="Username to lookup"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Get user by username."""
    service = UserService(deps.db, deps.tenant_id)
    user = await service.get_user_by_username(username)
    if not user:
        from dotmac_shared.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"User not found with username: {username}")
    return user


@user_router.get("/email/{email}", response_model=UserResponseSchema)
@standard_exception_handler
async def get_user_by_email(
    email: str = Path(..., description="Email to lookup"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Get user by email."""
    service = UserService(deps.db, deps.tenant_id)
    user = await service.get_user_by_email(email)
    if not user:
        from dotmac_shared.exceptions import EntityNotFoundError

        raise EntityNotFoundError(f"User not found with email: {email}")
    return user


# === User Status Management ===


@user_router.post("/{user_id}/activate", response_model=UserResponseSchema)
@standard_exception_handler
async def activate_user(
    user_id: UUID = Path(..., description="User ID to activate"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Activate user account."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.activate_user(user_id, UUID(deps.user_id))


@user_router.post("/{user_id}/deactivate", response_model=UserResponseSchema)
@standard_exception_handler
async def deactivate_user(
    user_id: UUID = Path(..., description="User ID to deactivate"),
    reason: str = Body(..., embed=True, description="Deactivation reason"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Deactivate user account."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.deactivate_user(user_id, UUID(deps.user_id), reason)


@user_router.post("/{user_id}/suspend", response_model=UserResponseSchema)
@standard_exception_handler
async def suspend_user(
    user_id: UUID = Path(..., description="User ID to suspend"),
    reason: str = Body(..., embed=True, description="Suspension reason"),
    duration_days: int | None = Body(None, embed=True, description="Suspension duration in days"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> UserResponseSchema:
    """Suspend user account."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.suspend_user(user_id, UUID(deps.user_id), reason, duration_days)


# === Bulk Operations ===


@user_router.post("/bulk-operation", response_model=dict[str, Any])
@standard_exception_handler
async def bulk_user_operation(
    operation_data: BulkUserOperation,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Perform bulk operations on users."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.bulk_operation(operation_data, UUID(deps.user_id))


# === User Statistics ===


@user_router.get("/statistics", response_model=dict[str, Any])
@standard_exception_handler
async def get_user_statistics(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get user statistics."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.get_user_statistics()


@user_router.get("/recent", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_recent_users(
    limit: int = Query(10, ge=1, le=50, description="Number of recent users to return"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get recently created users."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.get_recent_users(limit)


# === Health Check ===


@user_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def user_service_health(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Check user service health."""
    service = UserService(deps.db, deps.tenant_id)
    return await service.health_check()


# Export the router
__all__ = ["user_router"]
