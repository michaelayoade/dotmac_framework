"""
Base User Management Adapter.

Provides common functionality for platform-specific user management adapters.
Defines the interface and shared operations for ISP and Management Platform adapters.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.permission_manager import PermissionManager
from ..core.profile_manager import ProfileManager
from ..core.user_lifecycle_service import UserLifecycleService
from ..core.user_repository import UserRepository
from ..integrations.auth_integration import AuthIntegration
from ..integrations.service_integration import UserManagementServiceIntegration
from ..schemas.lifecycle_schemas import (
    UserActivation,
    UserDeactivation,
    UserRegistration,
)
from ..schemas.user_schemas import UserResponse, UserSearchQuery, UserUpdate


class BaseUserAdapter(ABC):
    """
    Abstract base class for platform-specific user management adapters.

    Provides common functionality and defines the interface that platform
    adapters must implement for consistent user management operations.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        user_service: Optional[UserLifecycleService] = None,
        config: Dict[str, Any] = None,
    ):
        """Initialize base user adapter."""
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.config = config or {}

        # Initialize core services
        self.user_repository = UserRepository(db_session)
        self.user_service = user_service or UserLifecycleService(
            db_session=db_session,
            user_repository=self.user_repository,
            config=self.config,
        )
        self.profile_manager = ProfileManager(
            db_session=db_session,
            user_repository=self.user_repository,
            config=self.config.get("profile", {}),
        )
        self.permission_manager = PermissionManager(
            db_session=db_session,
            user_repository=self.user_repository,
            config=self.config.get("permissions", {}),
        )

        # Initialize authentication integration if configured
        self.auth_integration = None
        if self.config.get("auth_integration_enabled", True):
            self.auth_integration = AuthIntegration(config=self.config.get("auth", {}))

        # Initialize service integration for shared services
        self.service_integration = UserManagementServiceIntegration(
            config=self.config, tenant_id=self.tenant_id
        )

        # Platform identifier (to be set by subclasses)
        self.platform_type: str = "base"

    # Core User Operations (Delegated to UserLifecycleService)
    async def register_user(self, registration: UserRegistration) -> UserResponse:
        """Register a new user through the unified service."""
        return await self.user_service.register_user(registration)

    async def activate_user(self, activation: UserActivation) -> UserResponse:
        """Activate user account through the unified service."""
        return await self.user_service.activate_user(activation)

    async def deactivate_user(self, deactivation: UserDeactivation) -> UserResponse:
        """Deactivate user account through the unified service."""
        return await self.user_service.deactivate_user(deactivation)

    async def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""
        return await self.user_service.get_user(user_id)

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email address."""
        return await self.user_service.get_user_by_email(email)

    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username."""
        return await self.user_service.get_user_by_username(username)

    async def update_user(
        self, user_id: UUID, updates: UserUpdate
    ) -> Optional[UserResponse]:
        """Update user information."""
        return await self.user_service.update_user(user_id, updates)

    async def search_users(self, search_query: UserSearchQuery) -> Dict[str, Any]:
        """Search users with filters and pagination."""
        return await self.user_service.search_users(search_query)

    # Profile Management (Delegated to ProfileManager)
    async def get_user_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user profile information."""
        profile = await self.profile_manager.get_user_profile(user_id)
        return profile.dict() if profile else None

    async def update_user_profile(
        self,
        user_id: UUID,
        profile_updates: Dict[str, Any],
        updated_by: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update user profile."""
        updated_profile = await self.profile_manager.update_user_profile(
            user_id, profile_updates, updated_by
        )
        return updated_profile.dict() if updated_profile else None

    async def upload_user_avatar(
        self, user_id: UUID, avatar_data: bytes, filename: str, content_type: str
    ) -> Optional[str]:
        """Upload user avatar."""
        return await self.profile_manager.upload_user_avatar(
            user_id, avatar_data, filename, content_type
        )

    # Permission Management (Delegated to PermissionManager)
    async def assign_user_roles(
        self,
        user_id: UUID,
        roles: List[str],
        assigned_by: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """Assign roles to user."""
        return await self.permission_manager.assign_roles_to_user(
            user_id, roles, assigned_by, tenant_id or self.tenant_id
        )

    async def check_user_permission(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: Optional[UUID] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has specific permission."""
        return await self.permission_manager.user_has_permission(
            user_id, permission, tenant_id or self.tenant_id, resource_id
        )

    async def get_user_permissions(
        self, user_id: UUID, tenant_id: Optional[UUID] = None
    ) -> List[str]:
        """Get all user permissions."""
        permissions = await self.permission_manager.get_user_permissions(
            user_id, tenant_id or self.tenant_id
        )
        return list(permissions)

    async def get_user_roles(
        self, user_id: UUID, tenant_id: Optional[UUID] = None
    ) -> List[str]:
        """Get all user roles."""
        roles = await self.permission_manager.get_user_roles(
            user_id, tenant_id or self.tenant_id
        )
        return list(roles)

    # Authentication Integration
    async def authenticate_user(
        self, login_request: Dict[str, Any], platform_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Authenticate user and return auth result."""

        if not self.auth_integration:
            raise ValueError("Authentication integration not configured")

        # Add platform context
        context = platform_context or {}
        context.update(
            {
                "platform": self.platform_type,
                "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            }
        )

        success, user, tokens = await self.auth_integration.authenticate_user(
            login_request, context
        )

        return {
            "success": success,
            "user": user.dict() if user else None,
            "tokens": tokens,
        }

    async def logout_user(
        self, user_id: UUID, access_token: Optional[str] = None
    ) -> bool:
        """Logout user."""

        if not self.auth_integration:
            return True  # No-op if auth integration not configured

        context = {
            "platform": self.platform_type,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
        }

        return await self.auth_integration.logout_user(user_id, access_token, context)

    # Common Helper Methods
    def _map_platform_data_to_user_registration(
        self, platform_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map platform-specific data to unified user registration format."""

        # Base mapping - subclasses should override for platform-specific mappings
        return {
            "username": platform_data.get("username")
            or platform_data.get("email", "").split("@")[0],
            "email": platform_data["email"],
            "first_name": platform_data["first_name"],
            "last_name": platform_data["last_name"],
            "password": platform_data.get("password"),
            "phone": platform_data.get("phone"),
            "tenant_id": self.tenant_id,
            "platform_specific": {
                "platform": self.platform_type,
                "original_data": platform_data,
            },
        }

    def _enhance_user_response_with_platform_data(
        self, user: UserResponse, platform_data: Dict[str, Any]
    ) -> UserResponse:
        """Enhance user response with platform-specific data."""

        # Create enhanced user response
        user_dict = user.dict()

        # Add platform-specific enhancements
        current_platform_data = user_dict.get("platform_specific", {})
        current_platform_data.update(platform_data)
        user_dict["platform_specific"] = current_platform_data

        return UserResponse(**user_dict)

    async def _record_platform_event(
        self, user_id: UUID, event_type: str, event_data: Dict[str, Any]
    ):
        """Record platform-specific user event."""

        enhanced_event_data = {
            **event_data,
            "platform": self.platform_type,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
        }

        await self.user_service.record_user_event(
            user_id, event_type, enhanced_event_data
        )

    # Abstract Methods (Platform-Specific Implementation Required)
    @abstractmethod
    async def _create_platform_specific_record(
        self, user: UserResponse, platform_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create platform-specific user record."""
        pass

    @abstractmethod
    async def _update_platform_specific_record(
        self, user_id: UUID, platform_updates: Dict[str, Any]
    ) -> bool:
        """Update platform-specific user record."""
        pass

    @abstractmethod
    async def _delete_platform_specific_record(
        self, user_id: UUID, soft_delete: bool = True
    ) -> bool:
        """Delete platform-specific user record."""
        pass

    @abstractmethod
    async def _get_platform_specific_data(
        self, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get platform-specific user data."""
        pass

    # Context Manager Support
    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self.db_session, "close"):
            await self.db_session.close()

    # Configuration
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value

    # Validation Helpers
    def _validate_tenant_access(
        self, user: UserResponse, required_tenant_id: Optional[UUID] = None
    ) -> bool:
        """Validate user has access to tenant."""

        target_tenant = required_tenant_id or self.tenant_id
        if not target_tenant:
            return True  # No tenant restriction

        # Check if user belongs to the tenant
        if user.tenant_id == target_tenant:
            return True

        # Check tenant memberships in platform data
        platform_data = user.platform_specific or {}
        tenant_memberships = platform_data.get("tenant_memberships", [])

        for membership in tenant_memberships:
            if membership.get("tenant_id") == str(target_tenant):
                return True

        return False

    # Bulk Operations Support
    async def bulk_create_users(
        self,
        user_registrations: List[Dict[str, Any]],
        created_by: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create multiple users in bulk."""

        results = {
            "total": len(user_registrations),
            "successful": 0,
            "failed": 0,
            "results": [],
            "errors": [],
        }

        for i, registration_data in enumerate(user_registrations):
            try:
                # Convert to UserRegistration
                unified_data = self._map_platform_data_to_user_registration(
                    registration_data
                )
                registration = UserRegistration(**unified_data)

                # Register user
                user = await self.register_user(registration)

                results["results"].append(
                    {"index": i, "success": True, "user": user.dict()}
                )
                results["successful"] += 1

            except Exception as e:
                results["results"].append(
                    {"index": i, "success": False, "error": str(e)}
                )
                results["errors"].append(
                    {
                        "index": i,
                        "registration_data": registration_data,
                        "error": str(e),
                    }
                )
                results["failed"] += 1

        # Record bulk operation event
        await self._record_platform_event(
            created_by or UUID("00000000-0000-0000-0000-000000000000"),
            "bulk_user_creation",
            {
                "total_users": results["total"],
                "successful": results["successful"],
                "failed": results["failed"],
                "created_by": str(created_by) if created_by else None,
            },
        )

        return results
