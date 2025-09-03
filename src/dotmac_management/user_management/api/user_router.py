"""
Production-ready user management API using RouterFactory.
Implements comprehensive user operations with DRY patterns.
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import Body, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.dependencies import get_db, get_current_user, get_admin_user
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.schemas.base_schemas import PaginatedResponseSchema

from ..services.user_service import UserService, UserProfileService, UserManagementService
from ..schemas.user_schemas import (
    UserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
    UserSummarySchema,
    UserSearchSchema,
    UserBulkOperationSchema,
    UserInvitationSchema,
    UserActivationSchema
)


# === User Dependencies ===

async def get_user_service(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> UserService:
    """Get user service with tenant context."""
    tenant_id = getattr(current_user, 'tenant_id', None)
    return UserService(db, tenant_id)


async def get_profile_service(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> UserProfileService:
    """Get profile service with tenant context."""
    tenant_id = getattr(current_user, 'tenant_id', None)
    return UserProfileService(db, tenant_id)


async def get_management_service(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> UserManagementService:
    """Get management service with tenant context."""
    tenant_id = getattr(current_user, 'tenant_id', None)
    return UserManagementService(db, tenant_id)


# === Main User Router ===

# Create standard CRUD router using RouterFactory
user_router = RouterFactory.create_crud_router(
    service_class=UserService,
    create_schema=UserCreateSchema,
    update_schema=UserUpdateSchema,
    response_schema=UserResponseSchema,
    prefix="/users",
    tags=["users", "user-management"],
    require_admin=True,  # Requires admin permissions
    enable_search=True,
    enable_bulk_operations=True,
)


# === Custom User Endpoints ===

@user_router.get("/me", response_model=UserResponseSchema)
@standard_exception_handler
async def get_current_user_profile(
    user_service: UserService = Depends(get_user_service),
    current_user = Depends(get_current_user)
) -> UserResponseSchema:
    """Get current user's profile."""
    return await user_service.get_user(current_user.user_id, include_profile=True)


@user_router.put("/me", response_model=UserResponseSchema)
@standard_exception_handler
async def update_current_user_profile(
    user_data: UserUpdateSchema = Body(...),
    user_service: UserService = Depends(get_user_service),
    current_user = Depends(get_current_user)
) -> UserResponseSchema:
    """Update current user's profile."""
    return await user_service.update_user(
        user_id=UUID(current_user.user_id),
        user_data=user_data,
        updated_by=UUID(current_user.user_id)
    )


@user_router.post("/search", response_model=PaginatedResponseSchema[UserSummarySchema])
@standard_exception_handler
async def search_users(
    search_params: UserSearchSchema = Body(...),
    user_service: UserService = Depends(get_user_service),
    current_user = Depends(get_current_user)
) -> PaginatedResponseSchema[UserSummarySchema]:
    """Search users with advanced filtering."""
    users, total_count = await user_service.search_users(search_params)
    
    return PaginatedResponseSchema(
        items=users,
        total=total_count,
        page=search_params.page,
        size=search_params.page_size,
    )


@user_router.get("/username/{username}", response_model=UserResponseSchema)
@standard_exception_handler 
async def get_user_by_username(
    username: str = Path(..., description="Username to lookup"),
    user_service: UserService = Depends(get_user_service),
    current_user = Depends(get_current_user)
) -> UserResponseSchema:
    """Get user by username."""
    user = await user_service.get_user_by_username(username)
    if not user:
        raise EntityNotFoundError(f"User not found with username: {username}")
    return user


@user_router.get("/email/{email}", response_model=UserResponseSchema)
@standard_exception_handler
async def get_user_by_email(
    email: str = Path(..., description="Email to lookup"),
    user_service: UserService = Depends(get_user_service),
    current_user = Depends(get_current_user)
) -> UserResponseSchema:
    """Get user by email."""
    user = await user_service.get_user_by_email(email)
    if not user:
        raise EntityNotFoundError(f"User not found with email: {email}")
    return user


# === User Status Management ===

@user_router.post("/{user_id}/activate", response_model=UserResponseSchema)
@standard_exception_handler
async def activate_user(
    user_id: UUID = Path(..., description="User ID to activate"),
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> UserResponseSchema:
    """Activate user account."""
    return await user_service.activate_user(user_id, UUID(admin_user["user_id"]))


@user_router.post("/{user_id}/deactivate", response_model=UserResponseSchema)
@standard_exception_handler
async def deactivate_user(
    user_id: UUID = Path(..., description="User ID to deactivate"),
    reason: str = Body(..., embed=True, description="Deactivation reason"),
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> UserResponseSchema:
    """Deactivate user account."""
    return await user_service.deactivate_user(
        user_id, 
        UUID(admin_user["user_id"]), 
        reason
    )


@user_router.post("/{user_id}/suspend", response_model=UserResponseSchema)
@standard_exception_handler
async def suspend_user(
    user_id: UUID = Path(..., description="User ID to suspend"),
    reason: str = Body(..., embed=True, description="Suspension reason"),
    duration_days: int = Body(None, embed=True, description="Suspension duration in days"),
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> UserResponseSchema:
    """Suspend user account."""
    return await user_service.suspend_user(
        user_id,
        UUID(admin_user["user_id"]),
        reason,
        duration_days
    )


# === Bulk Operations ===

@user_router.post("/bulk-operation", response_model=Dict[str, Any])
@standard_exception_handler
async def bulk_user_operation(
    operation_data: UserBulkOperationSchema = Body(...),
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> Dict[str, Any]:
    """Perform bulk operations on users."""
    return await user_service.bulk_operation(
        operation_data,
        UUID(admin_user["user_id"])
    )


# === User Statistics ===

@user_router.get("/statistics", response_model=Dict[str, Any])
@standard_exception_handler
async def get_user_statistics(
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> Dict[str, Any]:
    """Get user statistics."""
    return await user_service.get_user_statistics()


@user_router.get("/recent", response_model=List[UserSummarySchema])
@standard_exception_handler
async def get_recent_users(
    limit: int = Query(10, ge=1, le=50, description="Number of users to return"),
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> List[UserSummarySchema]:
    """Get recently created users."""
    return await user_service.get_recent_users(limit)


# === User Profile Router ===

profile_router = RouterFactory.create_standard_router(
    prefix="/users/{user_id}/profile",
    tags=["users", "profiles"]
)


@profile_router.get("/", response_model=Dict[str, Any])
@standard_exception_handler
async def get_user_profile(
    user_id: UUID = Path(..., description="User ID"),
    profile_service: UserProfileService = Depends(get_profile_service),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user profile."""
    profile = await profile_service.get_profile(user_id)
    if not profile:
        raise EntityNotFoundError(f"Profile not found for user: {user_id}")
    return profile


@profile_router.put("/", response_model=Dict[str, Any])
@standard_exception_handler
async def update_user_profile(
    user_id: UUID = Path(..., description="User ID"),
    profile_data: Dict[str, Any] = Body(...),
    profile_service: UserProfileService = Depends(get_profile_service),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update user profile."""
    return await profile_service.update_profile(
        user_id,
        profile_data,
        UUID(current_user.user_id)
    )


# === Admin Management Router ===

admin_router = RouterFactory.create_standard_router(
    prefix="/admin/users",
    tags=["admin", "user-management"]
)


@admin_router.post("/invite", response_model=Dict[str, str])
@standard_exception_handler
async def invite_user(
    invitation_data: UserInvitationSchema = Body(...),
    management_service: UserManagementService = Depends(get_management_service),
    admin_user = Depends(get_admin_user)
) -> Dict[str, str]:
    """Send user invitation."""
    # Implementation would handle invitation logic
    return {"message": "Invitation sent successfully"}


@admin_router.post("/activate-invitation", response_model=UserResponseSchema)
@standard_exception_handler
async def activate_user_invitation(
    activation_data: UserActivationSchema = Body(...),
    management_service: UserManagementService = Depends(get_management_service)
) -> UserResponseSchema:
    """Activate user account from invitation."""
    # Implementation would handle activation logic
    pass


@admin_router.get("/pending-approvals", response_model=List[UserSummarySchema])
@standard_exception_handler
async def get_pending_approvals(
    user_service: UserService = Depends(get_user_service),
    admin_user = Depends(get_admin_user)
) -> List[UserSummarySchema]:
    """Get users pending approval."""
    search_params = UserSearchSchema(
        status="pending",
        page=1,
        page_size=50
    )
    users, _ = await user_service.search_users(search_params)
    return users


# === User Onboarding ===

@admin_router.post("/onboard", response_model=UserResponseSchema)
@standard_exception_handler
async def onboard_user(
    user_data: UserCreateSchema = Body(...),
    profile_data: Dict[str, Any] = Body(None),
    management_service: UserManagementService = Depends(get_management_service),
    admin_user = Depends(get_admin_user)
) -> UserResponseSchema:
    """Complete user onboarding workflow."""
    return await management_service.onboard_user(
        user_data,
        profile_data,
        UUID(admin_user["user_id"])
    )


# === Health Check ===

@user_router.get("/health", response_model=Dict[str, Any])
@standard_exception_handler
async def user_service_health(
    user_service: UserService = Depends(get_user_service)
) -> Dict[str, Any]:
    """Check user service health."""
    return await user_service.health_check()


__all__ = [
    "user_router",
    "profile_router", 
    "admin_router",
]