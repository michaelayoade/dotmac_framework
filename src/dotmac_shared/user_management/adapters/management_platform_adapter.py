"""
Management Platform User Management Adapter.

Integrates the unified user management service with the Management Platform,
handling tenant administrators, platform users, and SaaS-specific user operations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.user_lifecycle_service import UserLifecycleService
from ..schemas.lifecycle_schemas import (
    UserActivation,
    UserDeactivation,
    UserRegistration,
)
from ..schemas.user_schemas import (
    UserCreate,
    UserProfile,
    UserResponse,
    UserStatus,
    UserSummary,
    UserType,
    UserUpdate,
)
from .base_adapter import BaseUserAdapter

# Management Platform imports (these would be the actual imports in practice)
try:
    from dotmac_management.models.tenant import Tenant, TenantRole, TenantUser
    from dotmac_management.models.user import User as PlatformUser
    from dotmac_management.schemas.user_management import (
        PermissionAssignment,
        RoleAssignment,
    )
    from dotmac_management.schemas.user_management import (
        UserCreate as PlatformUserCreate,
    )
    from dotmac_management.schemas.user_management import UserInvite
    from dotmac_management.schemas.user_management import (
        UserUpdate as PlatformUserUpdate,
    )
    from dotmac_management.services.auth_service import AuthService
    from dotmac_management.workers.tasks.user_tasks import (
        cleanup_user_data,
        send_user_invitation,
        setup_tenant_access,
    )
except ImportError:
    # Fallback types for development/testing
    PlatformUser = Dict[str, Any]
    Tenant = Dict[str, Any]
    TenantUser = Dict[str, Any]
    TenantRole = Dict[str, Any]


class ManagementPlatformUserAdapter(BaseUserAdapter):
    """
    Adapter that integrates unified user management with Management Platform.

    Handles platform administrators, tenant users, and SaaS-specific user
    operations while leveraging unified user management for core functionality.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        user_service: Optional[UserLifecycleService] = None,
    ):
        """Initialize Management Platform user adapter."""
        super().__init__(db_session, tenant_id, user_service)
        self.platform_type = "management_platform"

    # Platform User Management
    async def register_platform_admin(
        self, admin_data: Dict[str, Any], permissions: List[str], created_by: UUID
    ) -> UserResponse:
        """Register a new platform administrator."""

        # Map admin data to unified user format
        user_registration = self._map_admin_to_user_registration(
            admin_data, permissions
        )

        # Add platform-specific context
        user_registration.platform_specific.update(
            {
                "platform": self.platform_type,
                "user_type": admin_data.get("user_type", "platform_admin"),
                "permissions": permissions,
                "created_by": str(created_by),
                "requires_approval": True,
                "approval_level": "super_admin",
                "security_clearance": "high",
            }
        )

        # Register user through unified service
        user = await self.user_service.register_user(user_registration)

        # Create platform admin record
        admin = await self._create_platform_admin_record(user, admin_data, permissions)

        # Set up admin access permissions
        await self._setup_admin_permissions(user.id, permissions)

        # Enhance user response with platform-specific data
        user = await self._enhance_user_with_platform_data(user, admin)

        # Trigger admin registration tasks
        await self._trigger_admin_registration_tasks(user, created_by)

        return user

    async def register_tenant_admin(
        self,
        tenant: Tenant,
        admin_data: Dict[str, Any],
        role_assignments: List[Dict[str, Any]] = None,
    ) -> UserResponse:
        """Register a new tenant administrator."""

        # Map tenant admin data to unified format
        user_registration = self._map_tenant_admin_to_user_registration(
            admin_data, tenant, role_assignments
        )

        # Add tenant-specific context
        user_registration.platform_specific.update(
            {
                "platform": self.platform_type,
                "user_type": "tenant_admin",
                "tenant_id": str(tenant.id),
                "tenant_name": getattr(tenant, "name", "Unknown"),
                "role_assignments": role_assignments or [],
                "requires_tenant_onboarding": True,
                "billing_contact": admin_data.get("is_billing_contact", False),
            }
        )

        # Register user
        user = await self.user_service.register_user(user_registration)

        # Create tenant admin record
        tenant_admin = await self._create_tenant_admin_record(
            user, tenant, admin_data, role_assignments
        )

        # Set up tenant access
        await self._setup_tenant_access(user.id, tenant.id, role_assignments)

        # Enhance response
        user = await self._enhance_user_with_tenant_data(user, tenant, tenant_admin)

        # Trigger tenant admin setup tasks
        await self._trigger_tenant_admin_setup_tasks(user, tenant)

        return user

    async def invite_tenant_user(
        self,
        tenant_id: UUID,
        invitation_data: Dict[str, Any],
        invited_by: UUID,
        role_assignments: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send invitation to join a tenant."""

        # Create user invitation record
        invitation = await self._create_user_invitation(
            tenant_id, invitation_data, invited_by, role_assignments
        )

        # Generate invitation token
        invitation_token = await self._generate_invitation_token(invitation)

        # Prepare invitation context
        invitation_context = {
            "tenant_id": str(tenant_id),
            "invited_by": str(invited_by),
            "roles": role_assignments or [],
            "invitation_token": invitation_token,
            "expires_at": invitation["expires_at"].isoformat(),
            "platform": self.platform_type,
        }

        # Send invitation through unified notification system
        await self._send_user_invitation(invitation_data["email"], invitation_context)

        return {
            "invitation_id": invitation["id"],
            "email": invitation_data["email"],
            "status": "sent",
            "expires_at": invitation["expires_at"],
            "roles": role_assignments or [],
        }

    async def accept_invitation(
        self, invitation_token: str, user_registration_data: Dict[str, Any]
    ) -> UserResponse:
        """Accept user invitation and complete registration."""

        # Validate invitation token
        invitation = await self._validate_invitation_token(invitation_token)

        if not invitation:
            raise ValueError("Invalid or expired invitation token")

        # Map invitation data to user registration
        user_registration = self._map_invitation_to_user_registration(
            invitation, user_registration_data
        )

        # Add invitation context
        user_registration.platform_specific.update(
            {
                "platform": self.platform_type,
                "invitation_id": invitation["id"],
                "tenant_id": invitation["tenant_id"],
                "invited_by": invitation["invited_by"],
                "role_assignments": invitation["role_assignments"],
                "registration_source": "invitation",
            }
        )

        # Register user
        user = await self.user_service.register_user(user_registration)

        # Set up tenant access based on invitation
        await self._setup_tenant_access(
            user.id, UUID(invitation["tenant_id"]), invitation["role_assignments"]
        )

        # Mark invitation as accepted
        await self._mark_invitation_accepted(invitation["id"], user.id)

        # Trigger post-invitation acceptance tasks
        await self._trigger_invitation_acceptance_tasks(user, invitation)

        return user

    # Tenant User Management
    async def assign_user_to_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
        roles: List[str],
        permissions: List[str] = None,
        assigned_by: UUID = None,
    ) -> bool:
        """Assign existing user to a tenant with roles."""

        # Create tenant user relationship
        tenant_assignment = await self._create_tenant_user_assignment(
            user_id, tenant_id, roles, permissions, assigned_by
        )

        # Update user platform data
        user = await self.user_service.get_user(user_id)
        platform_updates = user.platform_specific.copy()

        tenant_memberships = platform_updates.get("tenant_memberships", [])
        tenant_memberships.append(
            {
                "tenant_id": str(tenant_id),
                "roles": roles,
                "permissions": permissions or [],
                "assigned_at": datetime.utcnow().isoformat(),
                "assigned_by": str(assigned_by) if assigned_by else None,
            }
        )
        platform_updates["tenant_memberships"] = tenant_memberships

        await self.user_service.update_user(
            user_id, UserUpdate(platform_specific=platform_updates)
        )

        # Trigger tenant assignment tasks
        await self._trigger_tenant_assignment_tasks(user_id, tenant_id, roles)

        return True

    async def remove_user_from_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
        removed_by: UUID = None,
        reason: str = None,
    ) -> bool:
        """Remove user from tenant access."""

        # Remove tenant user relationship
        await self._remove_tenant_user_assignment(
            user_id, tenant_id, removed_by, reason
        )

        # Update user platform data
        user = await self.user_service.get_user(user_id)
        platform_updates = user.platform_specific.copy()

        tenant_memberships = platform_updates.get("tenant_memberships", [])
        tenant_memberships = [
            tm for tm in tenant_memberships if tm["tenant_id"] != str(tenant_id)
        ]
        platform_updates["tenant_memberships"] = tenant_memberships

        await self.user_service.update_user(
            user_id, UserUpdate(platform_specific=platform_updates)
        )

        # Trigger removal tasks
        await self._trigger_tenant_removal_tasks(user_id, tenant_id, reason)

        return True

    async def update_user_permissions(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID],
        permissions: List[str],
        updated_by: UUID,
    ) -> UserResponse:
        """Update user permissions for a tenant or globally."""

        # Update permissions in platform database
        await self._update_user_permissions_db(
            user_id, tenant_id, permissions, updated_by
        )

        # Update unified user record
        user = await self.user_service.get_user(user_id)
        platform_updates = user.platform_specific.copy()

        if tenant_id:
            # Update tenant-specific permissions
            tenant_memberships = platform_updates.get("tenant_memberships", [])
            for membership in tenant_memberships:
                if membership["tenant_id"] == str(tenant_id):
                    membership["permissions"] = permissions
                    membership["permissions_updated_at"] = datetime.utcnow().isoformat()
                    membership["permissions_updated_by"] = str(updated_by)
                    break
            platform_updates["tenant_memberships"] = tenant_memberships
        else:
            # Update global permissions
            platform_updates["global_permissions"] = permissions
            platform_updates["global_permissions_updated_at"] = (
                datetime.utcnow().isoformat()
            )
            platform_updates["global_permissions_updated_by"] = str(updated_by)

        updated_user = await self.user_service.update_user(
            user_id, UserUpdate(platform_specific=platform_updates)
        )

        # Trigger permission update tasks
        await self._trigger_permission_update_tasks(user_id, tenant_id, permissions)

        return updated_user

    # Platform-Specific User Operations
    async def search_platform_users(
        self,
        search_params: Dict[str, Any],
        include_tenant_info: bool = True,
        requesting_user_id: UUID = None,
    ) -> Dict[str, Any]:
        """Search platform users with tenant information."""

        # Add platform-specific filters
        if "user_types" not in search_params:
            search_params["user_types"] = [
                UserType.SUPER_ADMIN,
                UserType.PLATFORM_ADMIN,
                UserType.TENANT_ADMIN,
                UserType.TENANT_USER,
            ]

        # Apply access control based on requesting user
        if requesting_user_id:
            search_params = await self._apply_user_search_access_control(
                search_params, requesting_user_id
            )

        # Search through unified service
        search_result = await self.user_service.search_users(search_params)

        # Enhance results with platform-specific data
        if include_tenant_info:
            enhanced_users = []
            for user in search_result.users:
                tenant_info = await self._get_user_tenant_info(user.id)
                enhanced_user = user.model_dump()
                enhanced_user["tenant_memberships"] = tenant_info
                enhanced_users.append(enhanced_user)

            search_result.users = enhanced_users

        return search_result.model_dump()

    async def get_user_audit_trail(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get comprehensive audit trail for a user."""

        # Get unified user audit events
        unified_events = await self.user_service.get_user_audit_trail(
            user_id, start_date, end_date
        )

        # Get platform-specific audit events
        platform_events = await self._get_platform_user_audit_events(
            user_id, start_date, end_date, event_types
        )

        # Merge and sort events
        all_events = unified_events + platform_events
        all_events.sort(key=lambda x: x["timestamp"], reverse=True)

        return all_events

    # Helper Methods
    def _map_admin_to_user_registration(
        self, admin_data: Dict[str, Any], permissions: List[str]
    ) -> UserRegistration:
        """Map platform admin data to unified user registration."""
        return UserRegistration(
            username=admin_data.get("username", admin_data["email"].split("@")[0]),
            email=admin_data["email"],
            first_name=admin_data["first_name"],
            last_name=admin_data["last_name"],
            user_type=UserType(admin_data.get("user_type", "platform_admin")),
            password=admin_data["password"],
            phone=admin_data.get("phone"),
            registration_source="platform_admin_portal",
            requires_approval=True,
        )

    async def _trigger_admin_registration_tasks(
        self, user: UserResponse, created_by: UUID
    ):
        """Trigger platform admin registration tasks."""
        try:
            # Send admin welcome email
            send_user_invitation.delay(
                str(user.id), "admin_welcome", {"created_by": str(created_by)}
            )

            # Set up admin dashboard access
            setup_tenant_access.delay(
                str(user.id), "platform_admin", {"full_access": True}
            )

        except Exception as e:
            # Log error but don't fail user registration
            pass

    async def _trigger_tenant_admin_setup_tasks(
        self, user: UserResponse, tenant: Tenant
    ):
        """Trigger tenant admin setup tasks."""
        try:
            # Send tenant admin welcome
            send_user_invitation.delay(
                str(user.id),
                "tenant_admin_welcome",
                {"tenant_id": str(tenant.id), "tenant_name": tenant.name},
            )

            # Set up tenant dashboard
            setup_tenant_access.delay(
                str(user.id), str(tenant.id), {"admin_access": True}
            )

        except Exception:
            pass


# Factory functions for easy integration
def create_management_user_adapter(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None, **config_options
) -> ManagementPlatformUserAdapter:
    """Create Management Platform user adapter with standard configuration."""
    return ManagementPlatformUserAdapter(db_session=db_session, tenant_id=tenant_id)


def create_management_user_service(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None
) -> ManagementPlatformUserAdapter:
    """Create Management Platform user service."""
    return ManagementPlatformUserAdapter(db_session, tenant_id)
