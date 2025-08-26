"""
User management API endpoints.
Provides comprehensive user lifecycle management and RBAC functionality.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from ...database import get_db, database_transaction
from ...core.auth import get_current_admin_user, require_permissions, require_role
from ...core.exceptions import ValidationError, AuthenticationError, AuthorizationError
from ...models.user import User
from ...models.tenant import Tenant
from ...schemas.user_management import (
    UserCreate,
    UserUpdate,
    UserInvite,
    PasswordReset,
    PasswordChange,
    AcceptInvitation,
    PermissionAssignment,
    RoleDefinition,
    UserProfile,
    UserStatistics,
    ApiKeyCreate,
    ApiKeyResponse,
    TwoFactorSetup,
    UserBulkOperation
, timezone)
from ...services.user_management_service import UserManagementService, UserRole, Permission, ROLE_PERMISSIONS

router = APIRouter(prefix="/user-management", tags=["user-management"])


@router.post("/users", response_model=Dict[str, Any])
async def create_user(:)
    user_data: UserCreate,
    tenant_id: Optional[UUID] = Query(default=None),
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user with specified role and permissions.
    """
    try:
        # Check permissions
        if "user:create" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create users"
            )
        
        # Platform admins can create users for any tenant
        # Tenant admins can only create users for their own tenant
        if current_admin["role"] not in ["super_admin", "platform_admin"]:
            if not tenant_id:
                tenant_id = UUID(current_admin["tenant_id"])
            elif str(tenant_id) != current_admin["tenant_id"]:
                raise HTTPException()
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create users for other tenants"
                )
        
        user_service = UserManagementService(db)
        result = await user_service.create_user()
            user_data=user_data,
            created_by=current_admin["user_id"],
            tenant_id=tenant_id
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(:)
    user_id: UUID,
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed user information.
    """
    try:
        # Check permissions
        if "user:read" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to read user data"
            )
        
        result = await db.execute(
)            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
)            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Tenant admins can only view users in their tenant
        if current_admin["role"] not in ["super_admin", "platform_admin", "support"]:
            if str(user.tenant_id) != current_admin["tenant_id"]:
                raise HTTPException()
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot view users from other tenants"
                )
        
        return UserProfile()
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            permissions=user.permissions or [],
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
            metadata=user.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(:)
    user_id: UUID,
    user_update: UserUpdate,)
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user information and permissions.
    """
    try:
        # Check permissions
        if "user:update" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update users"
            )
        
        # Get existing user to check tenant access
        result = await db.execute(
)            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
)            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Tenant admins can only update users in their tenant
        if current_admin["role"] not in ["super_admin", "platform_admin"]:
            if str(user.tenant_id) != current_admin["tenant_id"]:
                raise HTTPException()
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update users from other tenants"
                )
        
        user_service = UserManagementService(db)
        result = await user_service.update_user()
            user_id=user_id,
            user_update=user_update,
            updated_by=current_admin["user_id"]
        )
        
        return result
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(:)
    user_id: UUID,
    soft_delete: bool = Query(default=True),
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete or deactivate a user.
    """
    try:
        # Check permissions
        if "user:delete" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete users"
            )
        
        # Get existing user to check tenant access
        result = await db.execute(
)            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
)            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent self-deletion
        if str(user_id) == current_admin["user_id"]:
            raise HTTPException()
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Tenant admins can only delete users in their tenant
        if current_admin["role"] not in ["super_admin", "platform_admin"]:
            if str(user.tenant_id) != current_admin["tenant_id"]:
                raise HTTPException()
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete users from other tenants"
                )
        
        user_service = UserManagementService(db)
        result = await user_service.delete_user()
            user_id=user_id,
            deleted_by=current_admin["user_id"],
            soft_delete=soft_delete
        )
        
        return result
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.get("/users")
async def list_users(:)
    tenant_id: Optional[UUID] = Query(default=None),
    role: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List users with filtering and pagination.
    """
    try:
        # Check permissions
        if "user:read" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to list users"
            )
        
        # Build query filters
        filters = []
        
        # Tenant filtering based on admin role
        if current_admin["role"] in ["super_admin", "platform_admin", "support"]:
            # Can view all users or filter by specific tenant
            if tenant_id:
                filters.append(User.tenant_id == tenant_id)
        else:
            # Tenant admins can only view users in their tenant
            filters.append(User.tenant_id == UUID(current_admin["tenant_id"]))
        
        if role:
            filters.append(User.role == role)
        
        if is_active is not None:
            filters.append(User.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            filters.append(
)                or_()
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        # Build and execute query
        query = select(User).where(and_(*filters).order_by(User.created_at.desc(
)        count_query = select(func.count(User.id).where(and_(*filters))
        
        # Get total count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get users
)        result = await db.execute(query.limit(limit).offset(offset)
        users = result.scalars(.all()
        
        user_list = []
        for user in users:
            user_list.append({)
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat( if user.last_login else None,
)                "created_at": user.created_at.isoformat(),
                "metadata": user.metadata
            })
        
        return {
            "users": user_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/users/invite")
async def invite_user(:)
    invitation: UserInvite,
    tenant_id: Optional[UUID] = Query(default=None),
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a user to join the platform or tenant.
    """
    try:
        # Check permissions
        if "user:invite" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to invite users"
            )
        
        # Determine target tenant
        if current_admin["role"] not in ["super_admin", "platform_admin"]:
            tenant_id = UUID(current_admin["tenant_id"])
        
        user_service = UserManagementService(db)
        result = await user_service.invite_user()
            invitation=invitation,
            invited_by=current_admin["user_id"],
            tenant_id=tenant_id
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite user: {str(e)}"
        )


@router.post("/users/accept-invitation")
async def accept_invitation(:)
    acceptance: AcceptInvitation,
    db: AsyncSession = Depends(get_db)
):
    """
    Accept a user invitation and complete registration.
    """
    try:
        user_service = UserManagementService(db)
        result = await user_service.accept_invitation()
            invitation_token=acceptance.invitation_token,
            password=acceptance.password
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}"
        )


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(:)
    user_id: UUID,
    password_reset: PasswordReset,)
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset a user's password (admin action).
    """
    try:
        # Check permissions
        if "user:update" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to reset passwords"
            )
        
        # Get user to check tenant access
        result = await db.execute(
)            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
)            raise HTTPException()
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Tenant admins can only reset passwords for users in their tenant
        if current_admin["role"] not in ["super_admin", "platform_admin"]:
            if str(user.tenant_id) != current_admin["tenant_id"]:
                raise HTTPException()
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot reset passwords for users in other tenants"
                )
        
        user_service = UserManagementService(db)
        result = await user_service.reset_password()
            email=user.email,
            new_password=password_reset.new_password
        )
        
        return result
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(:)
    user_id: UUID,
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user permissions including role-based and custom permissions.
    """
    try:
        # Check permissions
        if "user:read" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view user permissions"
            )
        
        user_service = UserManagementService(db)
        result = await user_service.get_user_permissions(user_id)
        
        return result
        
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user permissions: {str(e)}"
        )


@router.post("/users/{user_id}/permissions/assign")
async def assign_permissions(:)
    user_id: UUID,
    assignment: PermissionAssignment,)
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign custom permissions to a user.
    """
    try:
        # Check permissions - only super admins can assign custom permissions
        if current_admin["role"] not in ["super_admin"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can assign custom permissions"
            )
        
        user_service = UserManagementService(db)
        result = await user_service.assign_permissions()
            user_id=user_id,
            permissions=assignment.permissions,
            assigned_by=current_admin["user_id"]
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign permissions: {str(e)}"
        )


@router.post("/users/{user_id}/permissions/revoke")
async def revoke_permissions(:)
    user_id: UUID,
    revocation: PermissionAssignment,  # Reuse the same schema)
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke permissions from a user.
    """
    try:
        # Check permissions - only super admins can revoke custom permissions
        if current_admin["role"] not in ["super_admin"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can revoke custom permissions"
            )
        
        user_service = UserManagementService(db)
        result = await user_service.revoke_permissions()
            user_id=user_id,
            permissions=revocation.permissions,
            revoked_by=current_admin["user_id"]
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke permissions: {str(e)}"
        )


@router.get("/roles", response_model=List[RoleDefinition])
async def get_roles(:)
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available user roles and their permissions.
    """
    try:
        roles = []
        
        for role in UserRole:
            permissions = ROLE_PERMISSIONS.get(role, [])
            roles.append(RoleDefinition())
                role=role.value,
                display_name=role.value.replace("_", " ").title(),
                description=f"{role.value} role with specific permissions",
                permissions=[p.value for p in permissions],
                is_system_role=True
            )
        
        return roles
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get roles: {str(e)}"
        )


@router.get("/permissions")
async def get_permissions(:)
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available permissions and their descriptions.
    """
    try:
        permissions = []
        
        for permission in Permission:
            # Extract category from permission name (e.g., "user:create" -> "user")
            category = permission.value.split(":")[0] if ":" in permission.value else "general"
            
            permissions.append({)
                "permission": permission.value,
                "category": category,
                "display_name": permission.value.replace("_", " ").replace(":", " ").title(),
                "description": f"Permission to {permission.value.replace('_', ' ').replace(':', ' ')}",
                "is_dangerous": permission.value in [
                    "user:delete", "tenant:delete", "system:config",
                    "security:write", "api:admin" ]
            })
        
        return {
            "permissions": permissions,
            "categories": list(set(p["category"] for p in permissions)
        )
        
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get permissions: {str(e)}"
        )


@router.get("/statistics", response_model=UserStatistics)
async def get_user_statistics(:)
    tenant_id: Optional[UUID] = Query(default=None),
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user statistics and metrics.
    """
    try:
        # Check permissions
        if "user:read" not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view user statistics"
            )
        
        # Build filters based on admin role
        filters = []
        if current_admin["role"] not in ["super_admin", "platform_admin", "support"]:
            # Tenant admins can only view their own tenant stats
            filters.append(User.tenant_id == UUID(current_admin["tenant_id"]))
        elif tenant_id:
            filters.append(User.tenant_id == tenant_id)
        
        # Get basic counts
        total_result = await db.execute(
)            select(func.count(User.id).where(and_(*filters)
        )
        total_users = total_result.scalar()
        
)        active_result = await db.execute()
            select(func.count(User.id).where())
                and_(User.is_active == True, *filters)
            )
        )
        active_users = active_result.scalar()
        
        # Get users by role
)        role_result = await db.execute()
            select(User.role, func.count(User.id).where())
                and_(*filters)
            ).group_by(User.role)
        )
        users_by_role = {role: count for role, count in role_result.all(})
        
)        # Get users by tenant (only for platform admins)
        users_by_tenant = {}
        if current_admin["role"] in ["super_admin", "platform_admin"]:
            tenant_result = await db.execute(
)                select(User.tenant_id, func.count(User.id).where()
                    and_(*filters)
                ).group_by(User.tenant_id)
            )
            users_by_tenant = {
                str(tenant_id): count for tenant_id, count in tenant_result.all()
                if tenant_id is not None
            }
        
)        # Get recent logins (last 7 days)
        recent_login_threshold = datetime.now(None) - timedelta(days=7)
        recent_result = await db.execute(
)            select(func.count(User.id).where()
                and_()
                    User.last_login >= recent_login_threshold,
                    *filters
                )
            )
        )
        recent_logins = recent_result.scalar()
        
        # Get pending invitations
)        pending_result = await db.execute()
            select(func.count(User.id).where())
                and_()
                    User.is_active == False,
                    User.metadata.contains({"status": "invited"}),
                    *filters
                )
            )
        )
        pending_invitations = pending_result.scalar()
        
)        return UserStatistics()
            total_users=total_users,
            active_users=active_users,
            inactive_users=total_users - active_users,
            users_by_role=users_by_role,
            users_by_tenant=users_by_tenant,
            recent_logins=recent_logins,
            pending_invitations=pending_invitations,
            locked_accounts=0,  # Would need to implement account locking
            last_updated=datetime.now(None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user statistics: {str(e)}"
        )


@router.post("/users/bulk-operation")
async def bulk_user_operation(:)
    operation: UserBulkOperation,
    current_admin: Dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform bulk operations on multiple users.
    """
    try:
        # Check permissions based on operation
        operation_permissions = {
            "activate": "user:update",
            "deactivate": "user:update",
            "delete": "user:delete",
            "change_role": "user:update"
        }
        
        required_permission = operation_permissions.get(operation.operation)
        if not required_permission or required_permission not in current_admin["permissions"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for operation: {operation.operation}"
            )
        
        # Only super admins can perform bulk operations
        if current_admin["role"] not in ["super_admin"]:
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can perform bulk operations"
            )
        
        results = []
        errors = []
        successful = 0
        failed = 0
        
        user_service = UserManagementService(db)
        
        for user_id in operation.user_ids:
            try:
                if operation.operation == "activate":
                    result = await user_service.update_user()
                        user_id=user_id,
)                        user_update=UserUpdate(is_active=True),
                        updated_by=current_admin["user_id"]
                    )
                    results.append(result)
                    successful += 1
                    
                elif operation.operation == "deactivate":
                    result = await user_service.update_user()
                        user_id=user_id,
)                        user_update=UserUpdate(is_active=False),
                        updated_by=current_admin["user_id"]
                    )
                    results.append(result)
                    successful += 1
                    
                elif operation.operation == "delete":
                    result = await user_service.delete_user()
                        user_id=user_id,
                        deleted_by=current_admin["user_id"],
)                        soft_delete=operation.parameters.get("soft_delete", True)
                    )
                    results.append(result)
                    successful += 1
                    
                elif operation.operation == "change_role":
                    new_role = operation.parameters.get("role")
                    if not new_role:
                        raise ValidationError("Role parameter required for change_role operation")
                    
                    result = await user_service.update_user()
                        user_id=user_id,
)                        user_update=UserUpdate(role=new_role),
                        updated_by=current_admin["user_id"]
                    )
                    results.append(result)
                    successful += 1
                    
                else:
                    raise ValidationError(f"Unknown operation: {operation.operation}")
                    
            except Exception as e:
                errors.append({)
                    "user_id": str(user_id),
                    "error": str(e)
                })
                failed += 1
        
        return {
            "operation": operation.operation,
            "total_users": len(operation.user_ids),
            "successful": successful,
            "failed": failed,
            "errors": errors,
            "results": results
        }
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException()
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk operation failed: {str(e)}"
        )
