"""
Tenant Super Admin Service for multi-app platform management.
Provides comprehensive tenant-level administration across multiple applications.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.application import standard_exception_handler
from dotmac.core.exceptions import (
    AuthorizationError,
    EntityNotFoundError,
    ValidationError,
)

from ..models.rbac_models import RoleModel
from ..models.user_models import UserModel
from ..repositories.rbac_repository import RBACRepository
from ..repositories.user_repository import UserRepository
from ..schemas.tenant_admin_schemas import (
    ApplicationType,
    BulkUserOperationSchema,
    CrossAppRoleCreateSchema,
    CrossAppSearchResultSchema,
    CrossAppSearchSchema,
    CrossAppUserCreateSchema,
    TenantSecurityPolicySchema,
)
from .base_service import BaseService

logger = logging.getLogger(__name__)


class TenantAdminService(BaseService):
    """
    Service for tenant super admin operations across multiple applications.
    Provides unified user management, cross-app permissions, and tenant administration.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: UUID, admin_user_id: UUID):
        super().__init__(db_session, tenant_id)
        self.admin_user_id = admin_user_id
        self.user_repo = UserRepository(db_session, tenant_id)
        self.rbac_repo = RBACRepository(db_session, tenant_id)

        # Cache for tenant subscriptions
        self._tenant_subscriptions: Optional[dict[str, Any]] = None

    @standard_exception_handler
    async def verify_super_admin_access(self) -> bool:
        """Verify that the current user has super admin access."""
        admin_user = await self.user_repo.get_by_id(self.admin_user_id)
        if not admin_user:
            raise EntityNotFoundError(f"Admin user {self.admin_user_id} not found")

        # Check if user has super admin role
        user_roles = await self.rbac_repo.get_user_roles(self.admin_user_id)
        super_admin_roles = [role for role in user_roles if "super_admin" in role.name.lower()]

        if not super_admin_roles:
            raise AuthorizationError("User does not have super admin privileges")

        return True

    @standard_exception_handler
    async def get_tenant_subscriptions(self) -> list[dict[str, Any]]:
        """Get all application subscriptions for the tenant."""
        # In a real implementation, this would query a subscriptions service
        # For now, return mock data
        if self._tenant_subscriptions is None:
            # This would typically query the Management Platform's licensing service
            self._tenant_subscriptions = [
                {
                    "app": "isp",
                    "plan": "professional",
                    "features": ["network_monitoring", "advanced_analytics"],
                    "is_active": True,
                },
                {
                    "app": "crm",
                    "plan": "standard",
                    "features": ["sales_pipeline", "email_automation"],
                    "is_active": True,
                },
                {
                    "app": "ecommerce",
                    "plan": "basic",
                    "features": ["storefront", "inventory"],
                    "is_active": True,
                },
            ]

        return self._tenant_subscriptions

    @standard_exception_handler
    async def create_cross_app_role(self, role_data: CrossAppRoleCreateSchema) -> RoleModel:
        """Create a role that spans multiple applications."""
        await self.verify_super_admin_access()

        # Validate app permissions against tenant subscriptions
        subscriptions = await self.get_tenant_subscriptions()
        active_apps = {sub["app"] for sub in subscriptions if sub["is_active"]}

        for app in role_data.app_permissions:
            if app.value not in active_apps:
                raise ValidationError(f"Tenant is not subscribed to app: {app.value}")

        # Create the role
        role = RoleModel(
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            role_category=role_data.role_category if hasattr(role_data, "role_category") else "custom",
            is_active=True,
            tenant_id=self.tenant_id,
            app_scope=None if role_data.is_tenant_wide else "multi",
            cross_app_permissions=dict(role_data.app_permissions),
            custom_metadata=role_data.custom_metadata,
            created_by=self.admin_user_id,
            updated_by=self.admin_user_id,
        )

        self.db_session.add(role)
        await self.db_session.flush()

        logger.info(f"Created cross-app role: {role.name} for tenant: {self.tenant_id}")
        return role

    @standard_exception_handler
    async def create_cross_app_user(self, user_data: CrossAppUserCreateSchema) -> UserModel:
        """Create a user with access to multiple applications."""
        await self.verify_super_admin_access()

        # Validate app access against tenant subscriptions
        subscriptions = await self.get_tenant_subscriptions()
        active_apps = {sub["app"] for sub in subscriptions if sub["is_active"]}

        for app in user_data.app_access:
            if app.value not in active_apps:
                raise ValidationError(f"Tenant is not subscribed to app: {app.value}")

        # Create the user
        user = UserModel(
            username=user_data.username,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            user_type=user_data.user_type.value,
            is_active=True,
            tenant_id=self.tenant_id,
            created_by=self.admin_user_id,
            updated_by=self.admin_user_id,
        )

        self.db_session.add(user)
        await self.db_session.flush()

        # Assign roles per application
        for app, role_names in user_data.app_roles.items():
            if app.value not in active_apps:
                continue

            for role_name in role_names:
                role = await self.rbac_repo.get_role_by_name(role_name)
                if role:
                    await self.rbac_repo.assign_role_to_user(user.id, role.id, self.admin_user_id)

        logger.info(f"Created cross-app user: {user.username} for tenant: {self.tenant_id}")
        return user

    @standard_exception_handler
    async def search_across_apps(
        self, search_params: CrossAppSearchSchema
    ) -> tuple[list[CrossAppSearchResultSchema], int]:
        """Search across multiple applications."""
        await self.verify_super_admin_access()

        # Get active app subscriptions
        subscriptions = await self.get_tenant_subscriptions()
        active_apps = {sub["app"] for sub in subscriptions if sub["is_active"]}

        # Filter search apps to only subscribed apps
        search_apps = search_params.apps or list(active_apps)
        search_apps = [app for app in search_apps if app.value in active_apps]

        results = []

        # Search in user management (common across all apps)
        if not search_params.resource_types or "users" in search_params.resource_types:
            user_query = select(UserModel).where(
                and_(
                    UserModel.tenant_id == self.tenant_id,
                    or_(
                        UserModel.username.ilike(f"%{search_params.query}%"),
                        UserModel.email.ilike(f"%{search_params.query}%"),
                        UserModel.first_name.ilike(f"%{search_params.query}%"),
                        UserModel.last_name.ilike(f"%{search_params.query}%"),
                    ),
                )
            )

            if not search_params.include_archived:
                user_query = user_query.where(UserModel.is_active is True)

            user_query = user_query.limit(search_params.limit)

            result = await self.db_session.execute(user_query)
            users = result.scalars().all()

            for user in users:
                results.append(
                    CrossAppSearchResultSchema(
                        app=ApplicationType.ISP,  # Default app for user results
                        resource_type="user",
                        resource_id=str(user.id),
                        title=f"{user.first_name} {user.last_name}",
                        description=f"User: {user.username} - {user.email}",
                        url=f"/admin/users/{user.id}",
                        context=f"User type: {user.user_type}",
                        relevance_score=0.8,  # Simple scoring for now
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                    )
                )

        # TODO: Implement app-specific search
        # This would query each subscribed application's data

        return results[: search_params.limit], len(results)

    @standard_exception_handler
    async def bulk_user_operation(self, operation_data: BulkUserOperationSchema) -> dict[str, Any]:
        """Perform bulk operations on multiple users."""
        await self.verify_super_admin_access()

        results = {"success_count": 0, "error_count": 0, "errors": []}

        for user_id in operation_data.user_ids:
            try:
                if operation_data.operation == "assign_role":
                    role_name = operation_data.parameters.get("role_name")
                    operation_data.parameters.get("app")

                    role = await self.rbac_repo.get_role_by_name(role_name)
                    if role:
                        await self.rbac_repo.assign_role_to_user(user_id, role.id, self.admin_user_id)
                        results["success_count"] += 1
                    else:
                        results["errors"].append(f"Role {role_name} not found for user {user_id}")
                        results["error_count"] += 1

                elif operation_data.operation == "remove_role":
                    role_name = operation_data.parameters.get("role_name")
                    role = await self.rbac_repo.get_role_by_name(role_name)
                    if role:
                        await self.rbac_repo.revoke_role_from_user(user_id, role.id)
                        results["success_count"] += 1

                elif operation_data.operation == "deactivate_user":
                    user = await self.user_repo.get_by_id(user_id)
                    if user:
                        user.is_active = False
                        user.updated_by = self.admin_user_id
                        user.updated_at = datetime.now(timezone.utc)
                        results["success_count"] += 1

                elif operation_data.operation == "activate_user":
                    user = await self.user_repo.get_by_id(user_id)
                    if user:
                        user.is_active = True
                        user.updated_by = self.admin_user_id
                        user.updated_at = datetime.now(timezone.utc)
                        results["success_count"] += 1

            except Exception as e:
                results["errors"].append(f"Error processing user {user_id}: {str(e)}")
                results["error_count"] += 1

        await self.db_session.commit()

        logger.info(
            f"Bulk operation {operation_data.operation} completed: {results['success_count']} success, {results['error_count']} errors"
        )
        return results

    @standard_exception_handler
    async def get_tenant_analytics(self, period_start: datetime, period_end: datetime) -> dict[str, Any]:
        """Get comprehensive analytics across all tenant applications."""
        await self.verify_super_admin_access()

        # Get basic user statistics
        user_count_query = select(func.count(UserModel.id)).where(
            and_(UserModel.tenant_id == self.tenant_id, UserModel.is_active is True)
        )
        result = await self.db_session.execute(user_count_query)
        total_users = result.scalar()

        # Get user type breakdown
        user_type_query = (
            select(UserModel.user_type, func.count(UserModel.id))
            .where(and_(UserModel.tenant_id == self.tenant_id, UserModel.is_active is True))
            .group_by(UserModel.user_type)
        )

        result = await self.db_session.execute(user_type_query)
        user_type_counts = {row[0]: row[1] for row in result.fetchall()}

        # Get subscriptions
        subscriptions = await self.get_tenant_subscriptions()

        analytics = {
            "tenant_id": str(self.tenant_id),
            "period_start": period_start,
            "period_end": period_end,
            "total_users": total_users,
            "user_type_breakdown": user_type_counts,
            "subscribed_apps": [sub["app"] for sub in subscriptions if sub["is_active"]],
            "app_usage": {
                # TODO: Implement app-specific usage metrics
                # This would query each application's usage data
                "isp": {"active_customers": 150, "support_tickets": 45},
                "crm": {"leads_created": 89, "deals_closed": 23},
                "ecommerce": {"orders_processed": 156, "revenue": 45680.50},
            },
        }

        return analytics

    @standard_exception_handler
    async def get_cross_app_permissions(self, user_id: UUID) -> dict[str, Any]:
        """Get a user's permissions across all applications."""
        await self.verify_super_admin_access()

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"User {user_id} not found")

        # Get user roles
        user_roles = await self.rbac_repo.get_user_roles(user_id)

        # Build cross-app permissions map
        app_permissions = {}

        for role in user_roles:
            if role.cross_app_permissions:
                for app, permissions in role.cross_app_permissions.items():
                    if app not in app_permissions:
                        app_permissions[app] = set()
                    app_permissions[app].update(permissions)

            # Handle app-scoped roles
            if role.app_scope:
                # Get traditional role permissions
                role_permissions = await self.rbac_repo.get_role_permissions(role.id)
                app_perms = [f"{perm.resource}:{perm.permission_type.value}" for perm in role_permissions]

                if role.app_scope not in app_permissions:
                    app_permissions[role.app_scope] = set()
                app_permissions[role.app_scope].update(app_perms)

        # Convert sets back to lists for JSON serialization
        return {app: list(perms) for app, perms in app_permissions.items()}

    @standard_exception_handler
    async def update_tenant_security_policy(self, policy_data: TenantSecurityPolicySchema) -> dict[str, Any]:
        """Update tenant-wide security policies."""
        await self.verify_super_admin_access()

        # Store security policy (in a real implementation, this would be in a dedicated table)
        policy = {
            "tenant_id": str(self.tenant_id),
            "password_policy": {
                "min_length": policy_data.password_min_length,
                "require_uppercase": policy_data.password_require_uppercase,
                "require_lowercase": policy_data.password_require_lowercase,
                "require_numbers": policy_data.password_require_numbers,
                "require_symbols": policy_data.password_require_symbols,
                "history_count": policy_data.password_history_count,
            },
            "mfa_policy": {
                "require_mfa": policy_data.require_mfa,
                "mfa_apps": [app.value for app in policy_data.mfa_apps],
            },
            "session_policy": {
                "timeout_minutes": policy_data.session_timeout_minutes,
                "concurrent_sessions_limit": policy_data.concurrent_sessions_limit,
            },
            "access_policy": {
                "ip_whitelist": policy_data.ip_whitelist,
                "allowed_countries": policy_data.allowed_countries,
            },
            "audit_policy": {
                "audit_login_attempts": policy_data.audit_login_attempts,
                "audit_permission_changes": policy_data.audit_permission_changes,
                "audit_cross_app_access": policy_data.audit_cross_app_access,
            },
            "updated_at": datetime.now(timezone.utc),
            "updated_by": str(self.admin_user_id),
        }

        logger.info(f"Updated security policy for tenant: {self.tenant_id}")
        return policy

    @standard_exception_handler
    async def get_tenant_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data for tenant super admin."""
        await self.verify_super_admin_access()

        # Get basic stats
        total_users_query = select(func.count(UserModel.id)).where(
            and_(UserModel.tenant_id == self.tenant_id, UserModel.is_active is True)
        )
        result = await self.db_session.execute(total_users_query)
        total_users = result.scalar()

        # Get recent logins (mock data for now)
        recent_logins = [
            {
                "user": "john.smith@abccorp.com",
                "app": "isp",
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=2),
                "ip_address": "192.168.1.100",
            },
            {
                "user": "sarah.jones@abccorp.com",
                "app": "crm",
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=1),
                "ip_address": "192.168.1.101",
            },
        ]

        # Get subscriptions
        subscriptions = await self.get_tenant_subscriptions()

        dashboard_data = {
            "tenant_info": {
                "tenant_id": str(self.tenant_id),
                "name": "ABC Corporation",  # Would come from tenant service
                "plan": "Enterprise",
            },
            "quick_stats": {
                "total_users": total_users,
                "active_sessions": 25,  # Mock data
                "subscribed_apps": [sub["app"] for sub in subscriptions if sub["is_active"]],
            },
            "recent_activity": {
                "recent_logins": recent_logins,
                "recent_user_changes": [],  # Would track user CRUD operations
            },
            "alerts": {"security_alerts": [], "billing_alerts": []},
        }

        return dashboard_data
