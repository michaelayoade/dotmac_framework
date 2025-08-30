"""
Core User Lifecycle Management Service.

Provides comprehensive user lifecycle operations including registration, activation,
profile management, and deactivation. Works with platform adapters to provide
consistent user management across ISP Framework and Management Platform.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from passlib.context import CryptContext
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..integrations.audit_integration import AuditIntegration
from ..integrations.auth_integration import AuthServiceIntegration
from ..integrations.notification_integration import NotificationIntegration
from ..schemas.lifecycle_schemas import (
    LifecycleEventType,
    UserActivation,
    UserDeactivation,
    UserDeletion,
    UserLifecycleEvent,
    UserRegistration,
)
from ..schemas.user_schemas import (
    UserBase,
    UserCreate,
    UserProfile,
    UserResponse,
    UserSearchQuery,
    UserSearchResult,
    UserStatus,
    UserSummary,
    UserType,
    UserUpdate,
)
from .permission_manager import PermissionManager
from .profile_manager import ProfileManager
from .user_repository import UserRepository

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserLifecycleService:
    """
    Core service for managing user lifecycle operations.

    Provides unified user operations that work across all platforms through
    adapter patterns while maintaining consistent behavior and security.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        config: Optional[Dict[str, Any]] = None,
        auth_integration: Optional[AuthServiceIntegration] = None,
        notification_integration: Optional[NotificationIntegration] = None,
        audit_integration: Optional[AuditIntegration] = None,
    ):
        """Initialize user lifecycle service."""
        self.db = db_session
        self.config = config or {}

        # Core components
        self.user_repo = UserRepository(db_session)
        self.profile_manager = ProfileManager(db_session)
        self.permission_manager = PermissionManager(db_session)

        # External integrations
        self.auth_integration = auth_integration or AuthServiceIntegration()
        self.notification_integration = (
            notification_integration or NotificationIntegration()
        )
        self.audit_integration = audit_integration or AuditIntegration()

    # User Registration
    async def register_user(self, registration: UserRegistration) -> UserResponse:
        """
        Register a new user account.

        Handles the complete user registration process including validation,
        password hashing, profile creation, and notification sending.
        """

        # Validate registration data
        await self._validate_user_registration(registration)

        # Hash password
        password_hash = pwd_context.hash(registration.password)

        # Prepare user data
        user_data = {
            "id": uuid4(),
            "username": registration.username.lower(),
            "email": registration.email.lower(),
            "first_name": registration.first_name,
            "last_name": registration.last_name,
            "user_type": registration.user_type.value,
            "password_hash": password_hash,
            "status": UserStatus.PENDING.value,
            "is_active": False,
            "is_verified": False,
            "tenant_id": registration.tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "platform_specific": registration.platform_specific or {},
        }

        # Create user record
        user = await self.user_repo.create(user_data)

        # Create initial profile
        if registration.initial_profile:
            await self.profile_manager.create_profile(
                user.id, registration.initial_profile
            )

        # Assign initial roles and permissions
        if registration.roles:
            await self.permission_manager.assign_roles(user.id, registration.roles)

        if registration.permissions:
            await self.permission_manager.assign_permissions(
                user.id, registration.permissions
            )

        # Create auth service user (if needed)
        if self.auth_integration:
            await self.auth_integration.create_user(
                user.id,
                registration.username,
                registration.email,
                registration.user_type,
                registration.tenant_id,
            )

        # Send verification email/SMS
        if self._requires_verification(registration):
            verification_code = await self._generate_verification_code(user.id)
            await self._send_verification_notification(user, verification_code)

        # Log lifecycle event
        await self._log_lifecycle_event(
            user.id,
            LifecycleEventType.REGISTERED,
            {"registration_source": registration.registration_source},
        )

        # Convert to response format
        return await self._user_to_response(user)

    # User Activation
    async def activate_user(self, activation: UserActivation) -> UserResponse:
        """
        Activate a user account.

        Handles email/SMS verification, approval processes, and account activation.
        """

        # Get user
        user = await self.user_repo.get(activation.user_id)
        if not user:
            raise ValueError(f"User not found: {activation.user_id}")

        if user.status != UserStatus.PENDING.value:
            raise ValueError(f"User is not pending activation: {user.status}")

        # Validate activation
        await self._validate_user_activation(user, activation)

        # Update user status
        updates = {
            "status": UserStatus.ACTIVE.value,
            "is_active": True,
            "is_verified": True,
            "activated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Add verification timestamps
        if activation.activation_type == "email_verification":
            updates["email_verified_at"] = datetime.utcnow()
        elif activation.activation_type == "phone_verification":
            updates["phone_verified_at"] = datetime.utcnow()

        user = await self.user_repo.update(activation.user_id, updates)

        # Update auth service
        if self.auth_integration:
            await self.auth_integration.activate_user(activation.user_id)

        # Clean up verification codes
        await self._cleanup_verification_codes(activation.user_id)

        # Send welcome notification
        await self._send_welcome_notification(user, activation.platform_context)

        # Log lifecycle event
        await self._log_lifecycle_event(
            activation.user_id,
            LifecycleEventType.ACTIVATED,
            {
                "activation_type": activation.activation_type,
                "platform_context": activation.platform_context,
            },
        )

        return await self._user_to_response(user)

    # User Profile Management
    async def update_user(self, user_id: UUID, updates: UserUpdate) -> UserResponse:
        """Update user information and profile."""

        # Get current user
        user = await self.user_repo.get(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Prepare updates
        user_updates = {}

        # Basic field updates
        if updates.first_name is not None:
            user_updates["first_name"] = updates.first_name
        if updates.last_name is not None:
            user_updates["last_name"] = updates.last_name
        if updates.email is not None:
            # Validate email uniqueness
            await self._validate_email_uniqueness(updates.email, user_id)
            user_updates["email"] = updates.email.lower()
            user_updates["email_verified_at"] = None  # Require re-verification

        # Status updates
        if updates.is_active is not None:
            user_updates["is_active"] = updates.is_active
        if updates.is_verified is not None:
            user_updates["is_verified"] = updates.is_verified
        if updates.status is not None:
            user_updates["status"] = updates.status.value

        # Platform-specific updates
        if updates.platform_specific is not None:
            current_platform_data = user.platform_specific or {}
            current_platform_data.update(updates.platform_specific)
            user_updates["platform_specific"] = current_platform_data

        # Apply updates
        if user_updates:
            user_updates["updated_at"] = datetime.utcnow()
            user = await self.user_repo.update(user_id, user_updates)

        # Update profile
        if updates.profile:
            await self.profile_manager.update_profile(user_id, updates.profile)

        # Update roles and permissions
        if updates.roles is not None:
            await self.permission_manager.assign_roles(user_id, updates.roles)

        if updates.permissions is not None:
            await self.permission_manager.assign_permissions(
                user_id, updates.permissions
            )

        # Update auth service
        if self.auth_integration and user_updates:
            await self.auth_integration.update_user(user_id, user_updates)

        # Log lifecycle event
        await self._log_lifecycle_event(
            user_id,
            LifecycleEventType.UPDATED,
            {"updated_fields": list(user_updates.keys())},
        )

        return await self._user_to_response(user)

    async def update_user_profile(
        self, user_id: UUID, profile_updates: Dict[str, Any]
    ) -> UserResponse:
        """Update user profile information."""

        # Update profile through profile manager
        await self.profile_manager.update_profile(user_id, profile_updates)

        # Get updated user
        user = await self.user_repo.get(user_id)

        # Log event
        await self._log_lifecycle_event(
            user_id,
            LifecycleEventType.PROFILE_UPDATED,
            {"updated_fields": list(profile_updates.keys())},
        )

        return await self._user_to_response(user)

    # User Deactivation
    async def deactivate_user(self, deactivation: UserDeactivation) -> UserResponse:
        """
        Deactivate a user account.

        Handles account suspension, session termination, and cleanup operations.
        """

        # Get user
        user = await self.user_repo.get(deactivation.user_id)
        if not user:
            raise ValueError(f"User not found: {deactivation.user_id}")

        # Update user status
        updates = {
            "status": UserStatus.INACTIVE.value,
            "is_active": False,
            "deactivated_at": datetime.utcnow(),
            "deactivation_reason": deactivation.reason,
            "deactivated_by": deactivation.deactivated_by,
            "updated_at": datetime.utcnow(),
        }

        user = await self.user_repo.update(deactivation.user_id, updates)

        # Deactivate in auth service (terminates sessions)
        if self.auth_integration:
            await self.auth_integration.deactivate_user(deactivation.user_id)

        # Send deactivation notification
        if deactivation.notify_user:
            await self._send_deactivation_notification(user, deactivation)

        # Log lifecycle event
        await self._log_lifecycle_event(
            deactivation.user_id,
            LifecycleEventType.DEACTIVATED,
            {
                "reason": deactivation.reason,
                "deactivated_by": (
                    str(deactivation.deactivated_by)
                    if deactivation.deactivated_by
                    else None
                ),
                "temporary": deactivation.temporary,
            },
        )

        return await self._user_to_response(user)

    async def reactivate_user(
        self,
        user_id: UUID,
        reactivated_by: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> UserResponse:
        """Reactivate a deactivated user account."""

        # Get user
        user = await self.user_repo.get(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        if user.status != UserStatus.INACTIVE.value:
            raise ValueError(f"User is not inactive: {user.status}")

        # Update user status
        updates = {
            "status": UserStatus.ACTIVE.value,
            "is_active": True,
            "reactivated_at": datetime.utcnow(),
            "reactivated_by": reactivated_by,
            "reactivation_reason": reason,
            "updated_at": datetime.utcnow(),
        }

        user = await self.user_repo.update(user_id, updates)

        # Reactivate in auth service
        if self.auth_integration:
            await self.auth_integration.activate_user(user_id)

        # Send reactivation notification
        await self._send_reactivation_notification(user)

        # Log lifecycle event
        await self._log_lifecycle_event(
            user_id,
            LifecycleEventType.REACTIVATED,
            {
                "reactivated_by": str(reactivated_by) if reactivated_by else None,
                "reason": reason,
            },
        )

        return await self._user_to_response(user)

    # User Deletion
    async def delete_user(self, deletion: UserDeletion) -> bool:
        """
        Delete a user account.

        Handles GDPR-compliant user data deletion with audit trail preservation.
        """

        # Get user
        user = await self.user_repo.get(deletion.user_id)
        if not user:
            raise ValueError(f"User not found: {deletion.user_id}")

        # Validate deletion permissions
        await self._validate_user_deletion(user, deletion)

        # Mark user as deleted (soft delete)
        if deletion.soft_delete:
            updates = {
                "status": UserStatus.DELETED.value,
                "is_active": False,
                "deleted_at": datetime.utcnow(),
                "deleted_by": deletion.deleted_by,
                "deletion_reason": deletion.reason,
                "updated_at": datetime.utcnow(),
            }

            await self.user_repo.update(deletion.user_id, updates)
        else:
            # Hard delete (GDPR compliance)
            await self._perform_hard_delete(deletion.user_id, deletion)

        # Delete from auth service
        if self.auth_integration:
            await self.auth_integration.delete_user(deletion.user_id)

        # Delete profile data
        await self.profile_manager.delete_profile(
            deletion.user_id, preserve_audit=deletion.preserve_audit
        )

        # Delete permissions
        await self.permission_manager.delete_user_permissions(deletion.user_id)

        # Send deletion notification
        if deletion.notify_user and not deletion.preserve_audit:
            await self._send_deletion_notification(user, deletion)

        # Log lifecycle event (before potential hard delete)
        await self._log_lifecycle_event(
            deletion.user_id,
            LifecycleEventType.DELETED,
            {
                "soft_delete": deletion.soft_delete,
                "reason": deletion.reason,
                "deleted_by": str(deletion.deleted_by) if deletion.deleted_by else None,
                "preserve_audit": deletion.preserve_audit,
            },
        )

        return True

    # User Search and Retrieval
    async def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""
        user = await self.user_repo.get(user_id)
        return await self._user_to_response(user) if user else None

    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username."""
        user = await self.user_repo.get_by_username(username.lower())
        return await self._user_to_response(user) if user else None

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email."""
        user = await self.user_repo.get_by_email(email.lower())
        return await self._user_to_response(user) if user else None

    async def search_users(self, search_query: UserSearchQuery) -> UserSearchResult:
        """Search users with filters and pagination."""

        # Perform search
        users, total_count = await self.user_repo.search(search_query)

        # Convert to summary format
        user_summaries = [await self._user_to_summary(user) for user in users]

        # Calculate pagination info
        total_pages = (
            total_count + search_query.page_size - 1
        ) // search_query.page_size

        return UserSearchResult(
            users=user_summaries,
            total_count=total_count,
            page=search_query.page,
            page_size=search_query.page_size,
            total_pages=total_pages,
        )

    # Audit and Reporting
    async def get_user_audit_trail(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get user audit trail."""

        return await self.audit_integration.get_user_audit_trail(
            user_id, start_date, end_date
        )

    # Helper Methods
    async def _validate_user_registration(self, registration: UserRegistration):
        """Validate user registration data."""

        # Check username uniqueness
        existing_user = await self.user_repo.get_by_username(
            registration.username.lower()
        )
        if existing_user:
            raise ValueError(f"Username already exists: {registration.username}")

        # Check email uniqueness
        existing_user = await self.user_repo.get_by_email(registration.email.lower())
        if existing_user:
            raise ValueError(f"Email already exists: {registration.email}")

        # Validate password requirements
        self._validate_password_requirements(registration.password)

    async def _validate_email_uniqueness(self, email: str, exclude_user_id: UUID):
        """Validate email uniqueness excluding specific user."""
        existing_user = await self.user_repo.get_by_email(email.lower())
        if existing_user and existing_user.id != exclude_user_id:
            raise ValueError(f"Email already exists: {email}")

    def _validate_password_requirements(self, password: str):
        """Validate password meets requirements."""
        config = self.config.get("registration", {}).get("password_requirements", {})

        min_length = config.get("min_length", 8)
        if len(password) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")

        if config.get("require_uppercase", True) and not any(
            c.isupper() for c in password
        ):
            raise ValueError("Password must contain at least one uppercase letter")

        if config.get("require_numbers", True) and not any(
            c.isdigit() for c in password
        ):
            raise ValueError("Password must contain at least one number")

        if config.get("require_symbols", True):
            symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in symbols for c in password):
                raise ValueError("Password must contain at least one symbol")

    async def _user_to_response(self, user) -> UserResponse:
        """Convert user model to response format."""
        # Get profile
        profile = await self.profile_manager.get_profile(user.id)

        # Get roles and permissions
        roles = await self.permission_manager.get_user_roles(user.id)
        permissions = await self.permission_manager.get_user_permissions(user.id)

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            user_type=UserType(user.user_type),
            status=UserStatus(user.status),
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=getattr(user, "last_login", None),
            profile=profile,
            email_verified_at=getattr(user, "email_verified_at", None),
            phone_verified_at=getattr(user, "phone_verified_at", None),
            tenant_id=user.tenant_id,
            roles=roles,
            permissions=permissions,
            platform_specific=user.platform_specific or {},
            login_count=getattr(user, "login_count", 0),
            failed_login_count=getattr(user, "failed_login_count", 0),
            last_failed_login=getattr(user, "last_failed_login", None),
            password_changed_at=getattr(user, "password_changed_at", None),
        )

    async def _log_lifecycle_event(
        self, user_id: UUID, event_type: LifecycleEventType, event_data: Dict[str, Any]
    ):
        """Log user lifecycle event."""
        event = UserLifecycleEvent(
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            timestamp=datetime.utcnow(),
        )

        await self.audit_integration.log_lifecycle_event(event)
