"""
Authentication Integration for Unified User Management.

Seamlessly integrates the user management service with the dotmac_shared/auth/
authentication system, providing unified authentication across platforms.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import jwt

try:
    from dotmac_shared.auth.authentication_service import AuthenticationService
    from dotmac_shared.auth.jwt_manager import JWTManager
    from dotmac_shared.auth.mfa_manager import MFAManager
    from dotmac_shared.auth.password_manager import PasswordManager
    from dotmac_shared.auth.schemas import (
        LoginRequest,
        RefreshTokenRequest,
        TokenResponse,
    )
except ImportError:
    # Fallback for development/testing
    AuthenticationService = None
    TokenResponse = dict
    LoginRequest = dict
    RefreshTokenRequest = dict
    JWTManager = None
    PasswordManager = None
    MFAManager = None

from ..schemas.lifecycle_schemas import UserActivation, UserRegistration
from ..schemas.user_schemas import UserResponse, UserStatus, UserType


class AuthIntegration:
    """
    Integration layer between user management and authentication services.

    Provides unified authentication operations that work seamlessly with
    the user lifecycle management system.
    """

    def __init__(
        self,
        auth_service: Optional[AuthenticationService] = None,
        jwt_manager: Optional[JWTManager] = None,
        password_manager: Optional[PasswordManager] = None,
        mfa_manager: Optional[MFAManager] = None,
    ):
        """Initialize authentication integration."""
        self.auth_service = auth_service
        self.jwt_manager = jwt_manager or self._create_default_jwt_manager()
        self.password_manager = (
            password_manager or self._create_default_password_manager()
        )
        self.mfa_manager = mfa_manager

    # Authentication Operations
    async def authenticate_user(
        self, login_request: Dict[str, Any], platform_context: Dict[str, Any] = None
    ) -> Tuple[bool, Optional[UserResponse], Optional[TokenResponse]]:
        """
        Authenticate user and return authentication result.

        Integrates with user lifecycle management to ensure only active,
        verified users can authenticate.
        """

        # Extract login credentials
        identifier = login_request.get("username") or login_request.get("email")
        password = login_request.get("password")

        if not identifier or not password:
            return False, None, None

        # Get user from user management service
        user = await self._get_user_by_identifier(identifier)

        if not user:
            return False, None, None

        # Check user status and eligibility
        if not self._is_user_eligible_for_authentication(user):
            return False, user, None

        # Verify password
        if not await self._verify_password(user.id, password):
            await self._record_failed_login_attempt(
                user.id, login_request, platform_context
            )
            return False, user, None

        # Check MFA if enabled
        if user.mfa_enabled and self.mfa_manager:
            mfa_token = login_request.get("mfa_token")
            if not mfa_token:
                # Return partial authentication - MFA required
                return False, user, {"mfa_required": True, "user_id": str(user.id)}

            if not await self._verify_mfa_token(user.id, mfa_token):
                await self._record_failed_login_attempt(
                    user.id, login_request, platform_context
                )
                return False, user, None

        # Generate authentication tokens
        tokens = await self._generate_auth_tokens(user, platform_context)

        # Update user login information
        await self._update_user_login_info(user.id, platform_context)

        # Record successful authentication
        await self._record_successful_authentication(user, tokens, platform_context)

        return True, user, tokens

    async def refresh_authentication(
        self, refresh_token: str, platform_context: Dict[str, Any] = None
    ) -> Tuple[bool, Optional[UserResponse], Optional[TokenResponse]]:
        """Refresh user authentication tokens."""

        try:
            # Validate refresh token
            token_data = await self.jwt_manager.verify_refresh_token(refresh_token)
            user_id = UUID(token_data.get("user_id"))

            # Get current user
            user = await self._get_user_by_id(user_id)

            if not user or not self._is_user_eligible_for_authentication(user):
                return False, user, None

            # Generate new tokens
            tokens = await self._generate_auth_tokens(user, platform_context)

            # Record token refresh
            await self._record_token_refresh(user, tokens, platform_context)

            return True, user, tokens

        except Exception as e:
            # Log token refresh failure
            await self._record_auth_event(
                "token_refresh_failed",
                {
                    "refresh_token": refresh_token[:20] + "...",
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            return False, None, None

    async def logout_user(
        self,
        user_id: UUID,
        access_token: Optional[str] = None,
        platform_context: Dict[str, Any] = None,
    ) -> bool:
        """Logout user and invalidate tokens."""

        try:
            # Get user
            user = await self._get_user_by_id(user_id)

            if not user:
                return False

            # Invalidate tokens
            if access_token:
                await self.jwt_manager.invalidate_token(access_token)

            # Invalidate all user sessions if requested
            if platform_context and platform_context.get("logout_all_sessions"):
                await self.jwt_manager.invalidate_all_user_tokens(user_id)

            # Record logout event
            await self._record_logout_event(user, platform_context)

            return True

        except Exception as e:
            # Log logout failure
            await self._record_auth_event(
                "logout_failed",
                {
                    "user_id": str(user_id),
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            return False

    # Password Management Integration
    async def create_user_password(
        self, user_id: UUID, password: str, platform_context: Dict[str, Any] = None
    ) -> bool:
        """Create password for new user during registration."""

        try:
            # Hash password
            password_hash = await self.password_manager.hash_password(password)

            # Store password hash (implementation would store in database)
            await self._store_user_password_hash(user_id, password_hash)

            # Record password creation
            await self._record_auth_event(
                "password_created",
                {"user_id": str(user_id), "platform_context": platform_context},
            )

            return True

        except Exception as e:
            await self._record_auth_event(
                "password_creation_failed",
                {
                    "user_id": str(user_id),
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            return False

    async def change_user_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        platform_context: Dict[str, Any] = None,
    ) -> bool:
        """Change user password with current password verification."""

        try:
            # Verify current password
            if not await self._verify_password(user_id, current_password):
                return False

            # Hash new password
            new_password_hash = await self.password_manager.hash_password(new_password)

            # Update password
            await self._store_user_password_hash(user_id, new_password_hash)

            # Invalidate existing sessions
            await self.jwt_manager.invalidate_all_user_tokens(user_id)

            # Record password change
            await self._record_auth_event(
                "password_changed",
                {"user_id": str(user_id), "platform_context": platform_context},
            )

            return True

        except Exception as e:
            await self._record_auth_event(
                "password_change_failed",
                {
                    "user_id": str(user_id),
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            return False

    async def reset_user_password(
        self,
        user_id: UUID,
        new_password: str,
        reset_token: Optional[str] = None,
        platform_context: Dict[str, Any] = None,
    ) -> bool:
        """Reset user password (admin action or token-based reset)."""

        try:
            # Verify reset token if provided
            if reset_token:
                if not await self._verify_password_reset_token(user_id, reset_token):
                    return False

            # Hash new password
            new_password_hash = await self.password_manager.hash_password(new_password)

            # Update password
            await self._store_user_password_hash(user_id, new_password_hash)

            # Invalidate existing sessions
            await self.jwt_manager.invalidate_all_user_tokens(user_id)

            # Clear reset token if used
            if reset_token:
                await self._clear_password_reset_token(user_id, reset_token)

            # Record password reset
            await self._record_auth_event(
                "password_reset",
                {
                    "user_id": str(user_id),
                    "reset_method": "token" if reset_token else "admin",
                    "platform_context": platform_context,
                },
            )

            return True

        except Exception as e:
            await self._record_auth_event(
                "password_reset_failed",
                {
                    "user_id": str(user_id),
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            return False

    # MFA Integration
    async def setup_user_mfa(
        self,
        user_id: UUID,
        mfa_method: str = "totp",
        platform_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Set up MFA for user account."""

        if not self.mfa_manager:
            raise ValueError("MFA manager not available")

        try:
            # Generate MFA setup data
            mfa_setup = await self.mfa_manager.setup_user_mfa(user_id, mfa_method)

            # Record MFA setup initiation
            await self._record_auth_event(
                "mfa_setup_initiated",
                {
                    "user_id": str(user_id),
                    "mfa_method": mfa_method,
                    "platform_context": platform_context,
                },
            )

            return mfa_setup

        except Exception as e:
            await self._record_auth_event(
                "mfa_setup_failed",
                {
                    "user_id": str(user_id),
                    "mfa_method": mfa_method,
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            raise

    async def verify_mfa_setup(
        self,
        user_id: UUID,
        verification_code: str,
        platform_context: Dict[str, Any] = None,
    ) -> bool:
        """Verify MFA setup and enable MFA for user."""

        if not self.mfa_manager:
            return False

        try:
            # Verify MFA setup code
            verified = await self.mfa_manager.verify_mfa_setup(
                user_id, verification_code
            )

            if verified:
                # Enable MFA for user in user management system
                await self._enable_user_mfa(user_id)

                # Record MFA enablement
                await self._record_auth_event(
                    "mfa_enabled",
                    {"user_id": str(user_id), "platform_context": platform_context},
                )

            return verified

        except Exception as e:
            await self._record_auth_event(
                "mfa_verification_failed",
                {
                    "user_id": str(user_id),
                    "error": str(e),
                    "platform_context": platform_context,
                },
            )
            return False

    # Token Generation and Validation
    async def _generate_auth_tokens(
        self, user: UserResponse, platform_context: Dict[str, Any] = None
    ) -> TokenResponse:
        """Generate access and refresh tokens for authenticated user."""

        # Prepare token payload
        token_payload = {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "roles": user.roles,
            "permissions": user.permissions,
            "platform_context": platform_context or {},
        }

        # Generate tokens
        access_token = await self.jwt_manager.generate_access_token(token_payload)
        refresh_token = await self.jwt_manager.generate_refresh_token(token_payload)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.jwt_manager.access_token_expiry,
            "user": user.dict(),
        }

    # User Verification Helpers
    def _is_user_eligible_for_authentication(self, user: UserResponse) -> bool:
        """Check if user is eligible for authentication."""

        # Check user status
        if user.status not in [UserStatus.ACTIVE]:
            return False

        # Check if user is active
        if not user.is_active:
            return False

        # Check if email verification is required
        if not user.is_verified and user.email_verified_at is None:
            # Allow authentication for certain user types without email verification
            if user.user_type not in [UserType.API_USER]:
                return False

        return True

    async def _verify_password(self, user_id: UUID, password: str) -> bool:
        """Verify user password against stored hash."""

        try:
            # Get password hash from database (implementation needed)
            password_hash = await self._get_user_password_hash(user_id)

            if not password_hash:
                return False

            # Verify password
            return await self.password_manager.verify_password(password, password_hash)

        except Exception:
            return False

    async def _verify_mfa_token(self, user_id: UUID, mfa_token: str) -> bool:
        """Verify MFA token for user."""

        if not self.mfa_manager:
            return False

        try:
            return await self.mfa_manager.verify_mfa_token(user_id, mfa_token)
        except Exception:
            return False

    # Database Operations (to be implemented)
    async def _get_user_by_identifier(self, identifier: str) -> Optional[UserResponse]:
        """Get user by username or email."""
        # Implementation would query user management database
        pass

    async def _get_user_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""
        # Implementation would query user management database
        pass

    async def _get_user_password_hash(self, user_id: UUID) -> Optional[str]:
        """Get user password hash from database."""
        # Implementation would query auth database
        pass

    async def _store_user_password_hash(self, user_id: UUID, password_hash: str):
        """Store user password hash in database."""
        # Implementation would store in auth database
        pass

    async def _update_user_login_info(
        self, user_id: UUID, platform_context: Dict[str, Any]
    ):
        """Update user login information."""
        # Implementation would update user management database
        pass

    async def _enable_user_mfa(self, user_id: UUID):
        """Enable MFA for user in user management system."""
        # Implementation would update user management database
        pass

    # Event Recording
    async def _record_successful_authentication(
        self,
        user: UserResponse,
        tokens: TokenResponse,
        platform_context: Dict[str, Any],
    ):
        """Record successful authentication event."""
        await self._record_auth_event(
            "login_success",
            {
                "user_id": str(user.id),
                "username": user.username,
                "user_type": user.user_type,
                "platform_context": platform_context,
            },
        )

    async def _record_failed_login_attempt(
        self,
        user_id: UUID,
        login_request: Dict[str, Any],
        platform_context: Dict[str, Any],
    ):
        """Record failed login attempt."""
        await self._record_auth_event(
            "login_failed",
            {
                "user_id": str(user_id),
                "identifier": login_request.get("username")
                or login_request.get("email"),
                "platform_context": platform_context,
            },
        )

    async def _record_logout_event(
        self, user: UserResponse, platform_context: Dict[str, Any]
    ):
        """Record user logout event."""
        await self._record_auth_event(
            "logout",
            {
                "user_id": str(user.id),
                "username": user.username,
                "platform_context": platform_context,
            },
        )

    async def _record_token_refresh(
        self,
        user: UserResponse,
        tokens: TokenResponse,
        platform_context: Dict[str, Any],
    ):
        """Record token refresh event."""
        await self._record_auth_event(
            "token_refresh",
            {
                "user_id": str(user.id),
                "username": user.username,
                "platform_context": platform_context,
            },
        )

    async def _record_auth_event(self, event_type: str, event_data: Dict[str, Any]):
        """Record authentication event."""
        # Implementation would store in audit/event database
        pass

    # Default Managers
    def _create_default_jwt_manager(self):
        """Create default JWT manager if not provided."""
        if JWTManager:
            return JWTManager()
        return None

    def _create_default_password_manager(self):
        """Create default password manager if not provided."""
        if PasswordManager:
            return PasswordManager()
        return None

    # Password Reset Token Management
    async def _verify_password_reset_token(
        self, user_id: UUID, reset_token: str
    ) -> bool:
        """Verify password reset token."""
        # Implementation would verify token from database
        return True

    async def _clear_password_reset_token(self, user_id: UUID, reset_token: str):
        """Clear password reset token after use."""
        # Implementation would remove token from database
        pass


def create_auth_integration(
    auth_service: Optional[AuthenticationService] = None, config: Dict[str, Any] = None
) -> AuthIntegration:
    """
    Factory function to create authentication integration.

    Args:
        auth_service: Optional authentication service instance
        config: Optional configuration dictionary

    Returns:
        Configured AuthIntegration instance
    """

    # Create managers based on configuration
    jwt_manager = None
    password_manager = None
    mfa_manager = None

    if JWTManager:
        jwt_config = config.get("jwt", {}) if config else {}
        jwt_manager = JWTManager(**jwt_config)

    if PasswordManager:
        password_config = config.get("password", {}) if config else {}
        password_manager = PasswordManager(**password_config)

    if MFAManager and config and config.get("mfa_enabled", False):
        mfa_config = config.get("mfa", {})
        mfa_manager = MFAManager(**mfa_config)

    return AuthIntegration(
        auth_service=auth_service,
        jwt_manager=jwt_manager,
        password_manager=password_manager,
        mfa_manager=mfa_manager,
    )
