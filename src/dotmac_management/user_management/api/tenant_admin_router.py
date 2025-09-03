"""
Tenant Super Admin API Router for multi-app platform management.
Provides API endpoints for tenant-level administration across multiple applications.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.dependencies import get_db, get_current_user, get_admin_user
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.schemas.base_schemas import PaginatedResponseSchema

from ..services.tenant_admin_service import TenantAdminService
from ..schemas.tenant_admin_schemas import (
    CrossAppRoleCreateSchema,
    CrossAppUserCreateSchema,
    CrossAppUserResponseSchema,
    TenantUserManagementSchema,
    CrossAppSearchSchema,
    CrossAppSearchResultSchema,
    BulkUserOperationSchema,
    TenantSecurityPolicySchema,
    TenantDashboardSchema,
    ApplicationType
)

logger = logging.getLogger(__name__)

# Create router with tenant admin prefix
router = RouterFactory.create_router(
    prefix="/tenant-admin",
    tags=["tenant-admin"],
    dependencies=[]
)

async def get_tenant_admin_service(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_admin_user)
) -> TenantAdminService:
    """Get tenant admin service with super admin verification."""
    # Extract tenant_id from current_user (implementation depends on your auth system)
    tenant_id = getattr(current_user, 'tenant_id', None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a tenant"
        )
    
    return TenantAdminService(db, tenant_id, current_user.id)

@router.get(
    "/dashboard",
    response_model=Dict[str, Any],
    summary="Get Tenant Dashboard",
    description="Get comprehensive dashboard data for tenant super admin"
)
@standard_exception_handler
async def get_tenant_dashboard(
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> Dict[str, Any]:
    """Get tenant super admin dashboard data."""
    return await service.get_tenant_dashboard_data()

@router.get(
    "/subscriptions",
    response_model=List[Dict[str, Any]],
    summary="Get Tenant Subscriptions",
    description="Get all application subscriptions for the tenant"
)
@standard_exception_handler
async def get_tenant_subscriptions(
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> List[Dict[str, Any]]:
    """Get tenant application subscriptions."""
    return await service.get_tenant_subscriptions()

@router.post(
    "/roles/cross-app",
    response_model=Dict[str, Any],
    summary="Create Cross-App Role",
    description="Create a role that spans multiple applications"
)
@standard_exception_handler
async def create_cross_app_role(
    role_data: CrossAppRoleCreateSchema,
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> Dict[str, Any]:
    """Create a role with permissions across multiple applications."""
    role = await service.create_cross_app_role(role_data)
    return {
        "id": str(role.id),
        "name": role.name,
        "display_name": role.display_name,
        "app_scope": role.app_scope,
        "cross_app_permissions": role.cross_app_permissions,
        "created_at": role.created_at
    }

@router.post(
    "/users/cross-app",
    response_model=CrossAppUserResponseSchema,
    summary="Create Cross-App User",
    description="Create a user with access to multiple applications"
)
@standard_exception_handler
async def create_cross_app_user(
    user_data: CrossAppUserCreateSchema,
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> CrossAppUserResponseSchema:
    """Create a user with access to multiple applications."""
    user = await service.create_cross_app_user(user_data)
    
    return CrossAppUserResponseSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        user_type=user.user_type,
        is_active=user.is_active,
        app_access=user_data.app_access,
        app_roles=user_data.app_roles,
        preferred_app=user_data.preferred_app,
        last_login=user.last_login,
        mfa_enabled=False,  # Would check MFA status
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.post(
    "/search",
    response_model=PaginatedResponseSchema[CrossAppSearchResultSchema],
    summary="Cross-App Search",
    description="Search across multiple applications"
)
@standard_exception_handler
async def search_across_apps(
    search_params: CrossAppSearchSchema,
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> PaginatedResponseSchema[CrossAppSearchResultSchema]:
    """Search across subscribed applications."""
    results, total_count = await service.search_across_apps(search_params)
    
    return PaginatedResponseSchema(
        items=results,
        total_count=total_count,
        page=1,  # Simple pagination for now
        page_size=search_params.limit,
        total_pages=(total_count // search_params.limit) + (1 if total_count % search_params.limit else 0)
    )

@router.post(
    "/users/bulk-operation",
    response_model=Dict[str, Any],
    summary="Bulk User Operations",
    description="Perform bulk operations on multiple users"
)
@standard_exception_handler
async def bulk_user_operation(
    operation_data: BulkUserOperationSchema,
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> Dict[str, Any]:
    """Perform bulk operations on multiple users."""
    return await service.bulk_user_operation(operation_data)

@router.get(
    "/users/{user_id}/permissions",
    response_model=Dict[str, List[str]],
    summary="Get User Cross-App Permissions",
    description="Get a user's permissions across all applications"
)
@standard_exception_handler
async def get_user_cross_app_permissions(
    user_id: UUID,
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> Dict[str, List[str]]:
    """Get user's permissions across all subscribed applications."""
    return await service.get_cross_app_permissions(user_id)

@router.get(
    "/analytics",
    response_model=Dict[str, Any],
    summary="Get Tenant Analytics",
    description="Get comprehensive analytics across all tenant applications"
)
@standard_exception_handler
async def get_tenant_analytics(
    period_start: Optional[datetime] = Query(
        default=None,
        description="Start date for analytics period (defaults to 30 days ago)"
    ),
    period_end: Optional[datetime] = Query(
        default=None,
        description="End date for analytics period (defaults to now)"
    ),
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> Dict[str, Any]:
    """Get tenant analytics across all applications."""
    if not period_start:
        period_start = datetime.now(timezone.utc) - timedelta(days=30)
    if not period_end:
        period_end = datetime.now(timezone.utc)
    
    return await service.get_tenant_analytics(period_start, period_end)

@router.put(
    "/security-policy",
    response_model=Dict[str, Any],
    summary="Update Security Policy",
    description="Update tenant-wide security policies"
)
@standard_exception_handler
async def update_security_policy(
    policy_data: TenantSecurityPolicySchema,
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> Dict[str, Any]:
    """Update tenant security policy."""
    return await service.update_tenant_security_policy(policy_data)

@router.get(
    "/apps/{app_name}/users",
    response_model=List[CrossAppUserResponseSchema],
    summary="Get App Users",
    description="Get all users with access to a specific application"
)
@standard_exception_handler
async def get_app_users(
    app_name: ApplicationType,
    include_inactive: bool = Query(default=False, description="Include inactive users"),
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> List[CrossAppUserResponseSchema]:
    """Get all users with access to a specific application."""
    # This would query users with roles in the specified app
    # For now, return empty list as placeholder
    return []

@router.get(
    "/roles/templates",
    response_model=List[Dict[str, Any]],
    summary="Get Role Templates",
    description="Get predefined role templates for different applications"
)
@standard_exception_handler
async def get_role_templates(
    app: Optional[ApplicationType] = Query(default=None, description="Filter by application"),
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> List[Dict[str, Any]]:
    """Get predefined role templates."""
    # Return predefined role templates
    templates = [
        {
            "app": "isp",
            "template_name": "customer_service_rep",
            "display_name": "Customer Service Representative",
            "description": "Handle customer inquiries and support tickets",
            "permissions": ["customers:read", "tickets:write", "billing:read"],
            "is_default": True
        },
        {
            "app": "crm",
            "template_name": "sales_representative",
            "display_name": "Sales Representative",
            "description": "Manage leads and sales opportunities",
            "permissions": ["leads:write", "opportunities:write", "accounts:read"],
            "is_default": True
        },
        {
            "app": "ecommerce",
            "template_name": "store_manager",
            "display_name": "Store Manager", 
            "description": "Manage inventory and orders",
            "permissions": ["products:write", "orders:read", "inventory:write"],
            "is_default": True
        }
    ]
    
    if app:
        templates = [t for t in templates if t["app"] == app.value]
    
    return templates

@router.get(
    "/audit/cross-app-access",
    response_model=List[Dict[str, Any]],
    summary="Get Cross-App Access Audit",
    description="Get audit trail of cross-app access activities"
)
@standard_exception_handler
async def get_cross_app_access_audit(
    user_id: Optional[UUID] = Query(default=None, description="Filter by user ID"),
    app: Optional[ApplicationType] = Query(default=None, description="Filter by application"),
    start_date: Optional[datetime] = Query(
        default=None,
        description="Start date for audit period (defaults to 7 days ago)"
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="End date for audit period (defaults to now)"
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of audit entries"),
    service: TenantAdminService = Depends(get_tenant_admin_service)
) -> List[Dict[str, Any]]:
    """Get cross-app access audit trail."""
    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
    if not end_date:
        end_date = datetime.now(timezone.utc)
    
    # Mock audit data for now
    audit_entries = [
        {
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=2),
            "user_id": "user-123",
            "user_email": "john@abccorp.com",
            "action": "cross_app_access",
            "source_app": "crm",
            "target_app": "isp",
            "resource": "customer_profile",
            "details": "Accessed ISP customer data from CRM account view",
            "ip_address": "192.168.1.100"
        },
        {
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=1),
            "user_id": "user-456", 
            "user_email": "sarah@abccorp.com",
            "action": "role_assignment",
            "source_app": None,
            "target_app": "ecommerce",
            "resource": "user_role",
            "details": "Assigned store_manager role to user in ecommerce app",
            "ip_address": "192.168.1.101"
        }
    ]
    
    # Apply filters
    if user_id:
        audit_entries = [e for e in audit_entries if e["user_id"] == str(user_id)]
    if app:
        audit_entries = [e for e in audit_entries if e["source_app"] == app.value or e["target_app"] == app.value]
    
    return audit_entries[:limit]

# Add router to the main application
def setup_tenant_admin_router(app):
    """Setup tenant admin router in the main application."""
    app.include_router(router)