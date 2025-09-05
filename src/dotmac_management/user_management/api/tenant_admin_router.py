"""
Tenant Admin Router - DRY Migration
Multi-tenant administration endpoints using RouterFactory patterns.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    StandardDependencies,
    get_standard_deps,
)
from fastapi import Depends, Query
from pydantic import BaseModel, Field

from ..schemas.tenant_admin_schemas import (
    ApplicationType,
    BulkUserOperationSchema,
    CrossAppUserCreateSchema,
    CrossAppUserResponseSchema,
    TenantSecurityPolicySchema,
)
from ..services.tenant_admin_service import TenantAdminService

# === Additional Schemas ===


class CrossAppSearchRequest(BaseModel):
    """Cross-application search request."""

    query: str = Field(..., description="Search query")
    applications: list[ApplicationType] = Field(..., description="Applications to search")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional filters")
    limit: int = Field(20, ge=1, le=100, description="Result limit")


# === Tenant Admin Router ===

tenant_admin_router = RouterFactory.create_standard_router(
    prefix="/tenant-admin",
    tags=["tenant-admin"],
)


# === Dashboard ===


@tenant_admin_router.get("/dashboard", response_model=dict[str, Any])
@standard_exception_handler
async def get_tenant_dashboard(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get tenant super admin dashboard data."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    return await service.get_tenant_dashboard_data()


# === Application Subscriptions ===


@tenant_admin_router.get("/subscriptions", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_tenant_subscriptions(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get tenant application subscriptions."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    return await service.get_tenant_subscriptions()


# === Cross-App User Management ===


@tenant_admin_router.post("/users/cross-app", response_model=CrossAppUserResponseSchema)
@standard_exception_handler
async def create_cross_app_user(
    user_data: CrossAppUserCreateSchema,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> CrossAppUserResponseSchema:
    """Create a user with access to multiple applications."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
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
        mfa_enabled=False,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


# === Cross-App Search ===


@tenant_admin_router.post("/search", response_model=dict[str, Any])
@standard_exception_handler
async def search_across_apps(
    search_request: CrossAppSearchRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Search across subscribed applications."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    results, total_count = await service.search_across_apps(search_request)

    return {
        "items": results,
        "total_count": total_count,
        "page": 1,
        "page_size": search_request.limit,
        "total_pages": (total_count // search_request.limit) + (1 if total_count % search_request.limit else 0),
    }


# === Bulk Operations ===


@tenant_admin_router.post("/users/bulk-operation", response_model=dict[str, Any])
@standard_exception_handler
async def bulk_user_operation(
    operation_data: BulkUserOperationSchema,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Perform bulk operations on multiple users."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    return await service.bulk_user_operation(operation_data)


# === Cross-App Permissions ===


@tenant_admin_router.get("/users/{user_id}/permissions", response_model=dict[str, list[str]])
@standard_exception_handler
async def get_user_cross_app_permissions(
    user_id: UUID,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, list[str]]:
    """Get user's permissions across all applications."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    return await service.get_cross_app_permissions(user_id)


# === Analytics ===


@tenant_admin_router.get("/analytics", response_model=dict[str, Any])
@standard_exception_handler
async def get_tenant_analytics(
    period_start: datetime | None = Query(None, description="Start date for analytics period"),
    period_end: datetime | None = Query(None, description="End date for analytics period"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get tenant analytics across all applications."""
    if not period_start:
        from datetime import timedelta

        period_start = datetime.now(timezone.utc) - timedelta(days=30)
    if not period_end:
        period_end = datetime.now(timezone.utc)

    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    return await service.get_tenant_analytics(period_start, period_end)


# === Security Policy ===


@tenant_admin_router.put("/security-policy", response_model=dict[str, Any])
@standard_exception_handler
async def update_security_policy(
    policy_data: TenantSecurityPolicySchema,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Update tenant security policy."""
    service = TenantAdminService(deps.db, deps.tenant_id, deps.user_id)
    return await service.update_tenant_security_policy(policy_data)


# === Application Users ===


@tenant_admin_router.get("/apps/{app_name}/users", response_model=list[CrossAppUserResponseSchema])
@standard_exception_handler
async def get_app_users(
    app_name: ApplicationType,
    include_inactive: bool = Query(False, description="Include inactive users"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[CrossAppUserResponseSchema]:
    """Get all users with access to a specific application."""
    # Mock implementation for DRY migration
    return []


# === Role Templates ===


@tenant_admin_router.get("/roles/templates", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_role_templates(
    app: ApplicationType | None = Query(None, description="Filter by application"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get predefined role templates."""
    templates = [
        {
            "app": "crm",
            "template_name": "support_agent",
            "display_name": "Support Agent",
            "description": "Handle customer inquiries and support tickets",
            "permissions": ["customers:read", "tickets:write", "billing:read"],
            "is_default": True,
        },
        {
            "app": "crm",
            "template_name": "sales_representative",
            "display_name": "Sales Representative",
            "description": "Manage leads and sales opportunities",
            "permissions": ["leads:write", "opportunities:write", "accounts:read"],
            "is_default": True,
        },
    ]

    if app:
        templates = [t for t in templates if t["app"] == app.value]

    return templates


# === Audit Trail ===


@tenant_admin_router.get("/audit/cross-app-access", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_cross_app_access_audit(
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    app: ApplicationType | None = Query(None, description="Filter by application"),
    start_date: datetime | None = Query(None, description="Start date for audit period"),
    end_date: datetime | None = Query(None, description="End date for audit period"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of audit entries"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get audit trail of cross-app access activities."""
    from datetime import timedelta

    # Mock audit entries
    audit_entries = [
        {
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=2),
            "user_id": "user-123",
            "user_email": "john@abccorp.com",
            "action": "cross_app_login",
            "source_app": "crm",
            "target_app": "analytics",
            "resource": "dashboard",
            "details": "User accessed analytics dashboard from CRM customer account view",
            "ip_address": "192.168.1.100",
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
            "ip_address": "192.168.1.101",
        },
    ]

    # Apply filters
    if user_id:
        audit_entries = [e for e in audit_entries if e["user_id"] == str(user_id)]
    if app:
        audit_entries = [e for e in audit_entries if e["source_app"] == app.value or e["target_app"] == app.value]

    return audit_entries[:limit]


# Export the router
__all__ = ["tenant_admin_router"]
