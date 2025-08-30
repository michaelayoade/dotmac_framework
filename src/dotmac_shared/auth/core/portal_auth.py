"""Portal authentication service for DotMac Framework.

This module provides portal-specific authentication with different access patterns
for admin, customer, technician, and reseller portals.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from .jwt_service import JWTService, TokenPair
from .permissions import Permission, Role, UserPermissions
from .rbac_engine import RBACEngine

logger = logging.getLogger(__name__)


class PortalType(str, Enum):
    """Portal types."""

    ADMIN = "admin"
    CUSTOMER = "customer"
    TECHNICIAN = "technician"
    RESELLER = "reseller"
    MANAGEMENT = "management"  # Management platform


class AuthenticationMethod(str, Enum):
    """Authentication methods."""

    PASSWORD = "password"
    MFA_TOTP = "mfa_totp"
    MFA_SMS = "mfa_sms"
    API_KEY = "api_key"
    SSO = "sso"
    OAUTH = "oauth"


@dataclass
class PortalConfig:
    """Portal-specific configuration."""

    portal_type: PortalType
    allowed_roles: List[Role]
    required_permissions: List[Permission]
    session_timeout_minutes: int = 480  # 8 hours
    require_mfa: bool = False
    allowed_auth_methods: List[AuthenticationMethod] = None
    max_concurrent_sessions: int = 5
    password_policy: Dict[str, Any] = None

    def __post_init__(self):
        if self.allowed_auth_methods is None:
            self.allowed_auth_methods = [AuthenticationMethod.PASSWORD]
        if self.password_policy is None:
            self.password_policy = {
                "min_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digits": True,
                "require_special": True,
            }


@dataclass
class AuthenticationContext:
    """Authentication context for portal access."""

    user_id: str
    tenant_id: str
    portal_type: PortalType
    ip_address: str
    user_agent: str
    session_id: Optional[str] = None
    device_fingerprint: Optional[str] = None
    auth_method: Optional[AuthenticationMethod] = None
    mfa_verified: bool = False
    additional_claims: Dict[str, Any] = None


@dataclass
class PortalSession:
    """Portal session information."""

    session_id: str
    user_id: str
    tenant_id: str
    portal_type: PortalType
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    device_fingerprint: Optional[str]
    auth_method: AuthenticationMethod
    mfa_verified: bool
    is_active: bool = True


class PortalAuthService:
    """Portal-specific authentication service.

    Manages authentication across different portals with specific
    access controls and session management for each portal type.
    """

    def __init__(self, jwt_service: JWTService, rbac_engine: RBACEngine):
        """Initialize portal authentication service.

        Args:
            jwt_service: JWT token service
            rbac_engine: RBAC engine
        """
        self.jwt_service = jwt_service
        self.rbac_engine = rbac_engine

        # Portal configurations
        self.portal_configs = self._initialize_portal_configs()

        # Active sessions
        self.active_sessions: Dict[str, PortalSession] = {}

        logger.info("Portal authentication service initialized")

    def _initialize_portal_configs(self) -> Dict[PortalType, PortalConfig]:
        """Initialize default portal configurations."""
        return {
            PortalType.ADMIN: PortalConfig(
                portal_type=PortalType.ADMIN,
                allowed_roles=[
                    Role.SUPER_ADMIN,
                    Role.PLATFORM_ADMIN,
                    Role.TENANT_ADMIN,
                    Role.TENANT_MANAGER,
                    Role.BILLING_MANAGER,
                    Role.NETWORK_ADMIN,
                ],
                required_permissions=[Permission.SYSTEM_READ],
                session_timeout_minutes=480,  # 8 hours
                require_mfa=True,
                allowed_auth_methods=[
                    AuthenticationMethod.PASSWORD,
                    AuthenticationMethod.MFA_TOTP,
                    AuthenticationMethod.SSO,
                ],
                max_concurrent_sessions=3,
            ),
            PortalType.CUSTOMER: PortalConfig(
                portal_type=PortalType.CUSTOMER,
                allowed_roles=[Role.CUSTOMER_USER, Role.CUSTOMER_ADMIN],
                required_permissions=[Permission.CUSTOMER_READ],
                session_timeout_minutes=1440,  # 24 hours
                require_mfa=False,
                allowed_auth_methods=[
                    AuthenticationMethod.PASSWORD,
                    AuthenticationMethod.MFA_TOTP,
                    AuthenticationMethod.MFA_SMS,
                ],
                max_concurrent_sessions=5,
            ),
            PortalType.TECHNICIAN: PortalConfig(
                portal_type=PortalType.TECHNICIAN,
                allowed_roles=[
                    Role.FIELD_TECHNICIAN,
                    Role.NETWORK_TECHNICIAN,
                    Role.SUPPORT_TECHNICIAN,
                ],
                required_permissions=[Permission.FIELD_OPS_READ],
                session_timeout_minutes=720,  # 12 hours
                require_mfa=False,
                allowed_auth_methods=[
                    AuthenticationMethod.PASSWORD,
                    AuthenticationMethod.API_KEY,
                ],
                max_concurrent_sessions=2,
            ),
            PortalType.RESELLER: PortalConfig(
                portal_type=PortalType.RESELLER,
                allowed_roles=[Role.RESELLER_ADMIN, Role.RESELLER_AGENT],
                required_permissions=[Permission.RESELLER_READ],
                session_timeout_minutes=480,  # 8 hours
                require_mfa=False,
                allowed_auth_methods=[
                    AuthenticationMethod.PASSWORD,
                    AuthenticationMethod.API_KEY,
                ],
                max_concurrent_sessions=3,
            ),
            PortalType.MANAGEMENT: PortalConfig(
                portal_type=PortalType.MANAGEMENT,
                allowed_roles=[
                    Role.SUPER_ADMIN,
                    Role.PLATFORM_ADMIN,
                    Role.PLATFORM_SUPPORT,
                ],
                required_permissions=[Permission.SYSTEM_ADMIN],
                session_timeout_minutes=240,  # 4 hours
                require_mfa=True,
                allowed_auth_methods=[
                    AuthenticationMethod.PASSWORD,
                    AuthenticationMethod.MFA_TOTP,
                    AuthenticationMethod.SSO,
                ],
                max_concurrent_sessions=2,
            ),
        }

    def authenticate_portal_user(
        self,
        user_id: Union[str, UUID],
        tenant_id: Union[str, UUID],
        portal_type: PortalType,
        user_permissions: UserPermissions,
        auth_context: AuthenticationContext,
    ) -> TokenPair:
        """Authenticate user for specific portal.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            portal_type: Target portal type
            user_permissions: User permissions
            auth_context: Authentication context

        Returns:
            JWT token pair for portal access

        Raises:
            ValueError: If user cannot access portal
            PermissionError: If user lacks required permissions
        """
        config = self.portal_configs.get(portal_type)
        if not config:
            raise ValueError(f"Unknown portal type: {portal_type}")

        # Check if user has allowed roles for this portal
        if not any(role in config.allowed_roles for role in user_permissions.roles):
            raise PermissionError(
                f"User does not have required roles for {portal_type} portal. "
                f"Required: {[str(r) for r in config.allowed_roles]}, "
                f"User has: {[str(r) for r in user_permissions.roles]}"
            )

        # Check required permissions
        for permission in config.required_permissions:
            if not self.rbac_engine.has_permission(user_permissions, permission):
                raise PermissionError(
                    f"User lacks required permission for {portal_type} portal: {permission}"
                )

        # Check MFA requirement
        if config.require_mfa and not auth_context.mfa_verified:
            raise ValueError(f"MFA required for {portal_type} portal access")

        # Check authentication method
        if auth_context.auth_method not in config.allowed_auth_methods:
            raise ValueError(
                f"Authentication method {auth_context.auth_method} not allowed for {portal_type} portal"
            )

        # Check concurrent session limit
        active_sessions = self._get_user_active_sessions(
            str(user_id), str(tenant_id), portal_type
        )
        if len(active_sessions) >= config.max_concurrent_sessions:
            # Remove oldest session
            oldest_session = min(active_sessions, key=lambda s: s.last_accessed)
            self._terminate_session(oldest_session.session_id)
            logger.info(
                f"Terminated oldest session for user {user_id} in {portal_type} portal"
            )

        # Create portal session
        session = self._create_portal_session(
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            portal_type=portal_type,
            auth_context=auth_context,
            config=config,
        )

        # Generate tokens with portal context
        permissions_list = self._get_portal_permissions(user_permissions, portal_type)
        roles_list = [
            str(role) for role in user_permissions.roles if role in config.allowed_roles
        ]

        token_pair = self.jwt_service.generate_token_pair(
            user_id=user_id,
            tenant_id=tenant_id,
            permissions=permissions_list,
            roles=roles_list,
            session_id=session.session_id,
            portal_type=portal_type.value,
        )

        logger.info(
            f"Portal authentication successful: user={user_id}, "
            f"portal={portal_type}, tenant={tenant_id}"
        )

        return token_pair

    def validate_portal_access(
        self,
        token: str,
        portal_type: PortalType,
        required_permission: Optional[Union[Permission, str]] = None,
    ) -> UserPermissions:
        """Validate portal access token.

        Args:
            token: JWT access token
            portal_type: Expected portal type
            required_permission: Required permission for operation

        Returns:
            User permissions if valid

        Raises:
            ValueError: If token is invalid or portal access denied
        """
        # Validate JWT token
        payload = self.jwt_service.validate_token(token)

        # Check portal type match
        token_portal = payload.get("portal_type")
        if token_portal != portal_type.value:
            raise ValueError(
                f"Token portal mismatch. Expected: {portal_type}, Got: {token_portal}"
            )

        # Check session validity
        session_id = payload.get("session_id")
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if not session.is_active or datetime.now(timezone.utc) > session.expires_at:
                raise ValueError("Session expired or inactive")

            # Update last accessed time
            session.last_accessed = datetime.now(timezone.utc)

        # Create user permissions from token
        user_permissions = self.jwt_service.create_user_permissions(payload)

        # Check specific permission if required
        if required_permission and not self.rbac_engine.has_permission(
            user_permissions, required_permission
        ):
            raise PermissionError(
                f"User lacks required permission: {required_permission}"
            )

        return user_permissions

    def refresh_portal_session(
        self, refresh_token: str, portal_type: PortalType
    ) -> TokenPair:
        """Refresh portal access token.

        Args:
            refresh_token: Valid refresh token
            portal_type: Portal type

        Returns:
            New token pair
        """
        # Validate refresh token
        payload = self.jwt_service.validate_token(refresh_token)

        # Check session
        session_id = payload.get("session_id")
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if not session.is_active:
                raise ValueError("Session is inactive")

            # Update session
            session.last_accessed = datetime.now(timezone.utc)

            # Get current user permissions (may have changed)
            user_permissions = UserPermissions(
                user_id=payload["sub"],
                tenant_id=payload["tenant_id"],
                roles=[Role(r) for r in payload.get("roles", [])],
                explicit_permissions={
                    Permission(p) for p in payload.get("permissions", [])
                },
            )

            # Generate new access token
            permissions_list = self._get_portal_permissions(
                user_permissions, portal_type
            )
            roles_list = [str(role) for role in user_permissions.roles]

            access_token = self.jwt_service.refresh_access_token(
                refresh_token=refresh_token,
                permissions=permissions_list,
                roles=roles_list,
                portal_type=portal_type.value,
            )

            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,  # Keep same refresh token
                expires_in=self.jwt_service.config.access_token_expire_minutes * 60,
                refresh_expires_in=self.jwt_service.config.refresh_token_expire_days
                * 24
                * 60
                * 60,
            )

        raise ValueError("Invalid session for token refresh")

    def logout_portal_user(self, session_id: str) -> bool:
        """Logout user from portal.

        Args:
            session_id: Session identifier

        Returns:
            True if logout successful
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.is_active = False

            logger.info(
                f"Portal logout: user={session.user_id}, "
                f"portal={session.portal_type}, tenant={session.tenant_id}"
            )

            return True

        return False

    def get_portal_permissions_for_user(
        self, user_permissions: UserPermissions, portal_type: PortalType
    ) -> List[str]:
        """Get portal-specific permissions for user.

        Args:
            user_permissions: User permissions
            portal_type: Portal type

        Returns:
            List of permission strings available in portal
        """
        return self._get_portal_permissions(user_permissions, portal_type)

    def get_active_portal_sessions(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        portal_type: Optional[PortalType] = None,
    ) -> List[PortalSession]:
        """Get active portal sessions.

        Args:
            user_id: Filter by user ID
            tenant_id: Filter by tenant ID
            portal_type: Filter by portal type

        Returns:
            List of matching active sessions
        """
        sessions = []

        for session in self.active_sessions.values():
            if not session.is_active:
                continue

            if user_id and session.user_id != user_id:
                continue

            if tenant_id and session.tenant_id != tenant_id:
                continue

            if portal_type and session.portal_type != portal_type:
                continue

            sessions.append(session)

        return sessions

    def update_portal_config(self, portal_type: PortalType, config: PortalConfig):
        """Update portal configuration.

        Args:
            portal_type: Portal type
            config: New configuration
        """
        self.portal_configs[portal_type] = config
        logger.info(f"Updated configuration for {portal_type} portal")

    def get_portal_config(self, portal_type: PortalType) -> Optional[PortalConfig]:
        """Get portal configuration.

        Args:
            portal_type: Portal type

        Returns:
            Portal configuration
        """
        return self.portal_configs.get(portal_type)

    def _create_portal_session(
        self,
        user_id: str,
        tenant_id: str,
        portal_type: PortalType,
        auth_context: AuthenticationContext,
        config: PortalConfig,
    ) -> PortalSession:
        """Create new portal session."""
        now = datetime.now(timezone.utc)
        session_id = (
            auth_context.session_id
            or f"portal_{portal_type}_{user_id}_{int(now.timestamp())}"
        )

        session = PortalSession(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            portal_type=portal_type,
            created_at=now,
            last_accessed=now,
            expires_at=now + timedelta(minutes=config.session_timeout_minutes),
            ip_address=auth_context.ip_address,
            user_agent=auth_context.user_agent,
            device_fingerprint=auth_context.device_fingerprint,
            auth_method=auth_context.auth_method or AuthenticationMethod.PASSWORD,
            mfa_verified=auth_context.mfa_verified,
        )

        self.active_sessions[session_id] = session
        return session

    def _get_user_active_sessions(
        self, user_id: str, tenant_id: str, portal_type: PortalType
    ) -> List[PortalSession]:
        """Get active sessions for user in specific portal."""
        return [
            session
            for session in self.active_sessions.values()
            if (
                session.user_id == user_id
                and session.tenant_id == tenant_id
                and session.portal_type == portal_type
                and session.is_active
                and datetime.now(timezone.utc) <= session.expires_at
            )
        ]

    def _terminate_session(self, session_id: str):
        """Terminate specific session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].is_active = False

    def _get_portal_permissions(
        self, user_permissions: UserPermissions, portal_type: PortalType
    ) -> List[str]:
        """Get permissions relevant to specific portal."""
        all_permissions = self.rbac_engine.get_user_permissions_list(user_permissions)
        config = self.portal_configs.get(portal_type)

        if not config:
            return all_permissions

        # Filter permissions based on portal context
        portal_permissions = []

        for permission_str in all_permissions:
            try:
                permission = Permission(permission_str)

                # Include permission if it's relevant to this portal
                if self._is_permission_relevant_to_portal(permission, portal_type):
                    portal_permissions.append(permission_str)

            except ValueError:
                # Include custom permissions
                portal_permissions.append(permission_str)

        return portal_permissions

    def _is_permission_relevant_to_portal(
        self, permission: Permission, portal_type: PortalType
    ) -> bool:
        """Check if permission is relevant to portal type."""
        # Define portal-specific permission relevance
        portal_permission_mapping = {
            PortalType.ADMIN: {
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_READ,
                Permission.SYSTEM_MONITOR,
                Permission.TENANT_ADMIN,
                Permission.TENANT_CREATE,
                Permission.TENANT_UPDATE,
                Permission.USER_ADMIN,
                Permission.USER_CREATE,
                Permission.USER_UPDATE,
                Permission.BILLING_ADMIN,
                Permission.BILLING_INVOICE,
                Permission.BILLING_PAYMENT,
                Permission.NETWORK_ADMIN,
                Permission.NETWORK_CONFIG,
                Permission.NETWORK_PROVISION,
                Permission.ANALYTICS_ADMIN,
                Permission.ANALYTICS_READ,
            },
            PortalType.CUSTOMER: {
                Permission.CUSTOMER_READ,
                Permission.CUSTOMER_UPDATE,
                Permission.CUSTOMER_BILLING,
                Permission.SERVICE_READ,
                Permission.BILLING_READ,
                Permission.SUPPORT_CREATE,
            },
            PortalType.TECHNICIAN: {
                Permission.FIELD_OPS_READ,
                Permission.FIELD_OPS_UPDATE,
                Permission.NETWORK_READ,
                Permission.NETWORK_MONITOR,
                Permission.SUPPORT_READ,
                Permission.SUPPORT_UPDATE,
            },
            PortalType.RESELLER: {
                Permission.RESELLER_READ,
                Permission.RESELLER_UPDATE,
                Permission.CUSTOMER_CREATE,
                Permission.CUSTOMER_UPDATE,
                Permission.SERVICE_PROVISION,
                Permission.BILLING_READ,
            },
            PortalType.MANAGEMENT: {
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_READ,
                Permission.PLATFORM_ADMIN,
                Permission.TENANT_ADMIN,
                Permission.ANALYTICS_ADMIN,
            },
        }

        relevant_permissions = portal_permission_mapping.get(portal_type, set())
        return permission in relevant_permissions

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired portal sessions.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)
        expired_sessions = [
            session_id
            for session_id, session in self.active_sessions.items()
            if now > session.expires_at or not session.is_active
        ]

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired portal sessions")

        return len(expired_sessions)
