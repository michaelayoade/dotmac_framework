"""
Authentication components for captive portal systems.

Provides multiple authentication methods including email, SMS, social,
vouchers, and RADIUS integration with comprehensive validation and security.
"""

import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuthMethodType, Voucher

logger = structlog.get_logger(__name__)

# Constants
MAX_VERIFICATION_ATTEMPTS = 3
MIN_VOUCHER_CODE_LENGTH = 4


@dataclass
class AuthenticationResult:
    """Result of authentication attempt."""

    success: bool
    user_id: str | None = None
    session_data: dict[str, Any] | None = None
    error_message: str | None = None
    requires_verification: bool = False
    verification_method: str | None = None
    additional_data: dict[str, Any] | None = None


@dataclass
class SocialAuthConfig:
    """Configuration for social authentication providers."""

    provider_name: str  # google, facebook, twitter, etc.
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: list[str]
    auth_url: str
    token_url: str
    user_info_url: str
    enabled: bool = True


class BaseAuthMethod(ABC):
    """Base class for authentication methods."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.method_type: AuthMethodType = AuthMethodType.EMAIL

    @abstractmethod
    async def authenticate(
        self,
        credentials: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> AuthenticationResult:
        """Authenticate user with provided credentials."""

    @abstractmethod
    async def prepare_authentication(
        self,
        user_data: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare authentication (e.g., send verification code)."""

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate credential format and requirements."""
        return True

    def generate_verification_code(self, length: int = 6) -> str:
        """Generate numeric verification code."""
        return "".join(secrets.choice("0123456789") for _ in range(length))


class SocialAuth(BaseAuthMethod):
    """Social media authentication (OAuth)."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.method_type = AuthMethodType.SOCIAL
        self.providers = {
            name: SocialAuthConfig(**provider_config) for name, provider_config in config.get("providers", {}).items()
        }
        self._oauth_states: dict[str, dict[str, Any]] = {}

    async def prepare_authentication(
        self,
        user_data: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare OAuth authentication flow."""
        provider = user_data.get("provider")
        if not provider or provider not in self.providers:
            return {"error": f"Unsupported provider: {provider}"}

        provider_config = self.providers[provider]
        if not provider_config.enabled:
            return {"error": f"Provider {provider} is disabled"}

        # Generate OAuth state
        oauth_state = secrets.token_urlsafe(32)

        # Store OAuth session
        self._oauth_states[oauth_state] = {
            "provider": provider,
            "portal_id": portal_id,
            "user_data": user_data,
            "created_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + timedelta(minutes=10),
        }

        # Build authorization URL
        auth_params = {
            "client_id": provider_config.client_id,
            "redirect_uri": provider_config.redirect_uri,
            "scope": " ".join(provider_config.scope),
            "state": oauth_state,
            "response_type": "code",
        }

        auth_url = provider_config.auth_url + "?" + "&".join(f"{key}={value}" for key, value in auth_params.items())

        logger.info(
            "Social auth prepared",
            provider=provider,
            portal_id=portal_id,
            state=oauth_state,
        )

        return {
            "method": "social",
            "provider": provider,
            "auth_url": auth_url,
            "state": oauth_state,
        }

    async def authenticate(
        self,
        credentials: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> AuthenticationResult:
        """Complete OAuth authentication flow."""
        oauth_code = credentials.get("code")
        oauth_state = credentials.get("state")

        if not oauth_code or not oauth_state:
            return AuthenticationResult(
                success=False,
                error_message="OAuth code and state required",
            )

        # Validate OAuth state
        if oauth_state not in self._oauth_states:
            return AuthenticationResult(
                success=False,
                error_message="Invalid or expired OAuth state",
            )

        oauth_session = self._oauth_states[oauth_state]

        # Check expiration
        if datetime.now(UTC) > oauth_session["expires_at"]:
            del self._oauth_states[oauth_state]
            return AuthenticationResult(
                success=False,
                error_message="OAuth session expired",
            )

        provider = oauth_session["provider"]
        provider_config = self.providers[provider]

        # Exchange code for access token
        try:
            token_data = await self._exchange_oauth_code(provider_config, oauth_code)
            user_info = await self._get_user_info(provider_config, token_data["access_token"])

            # Clean up OAuth state
            del self._oauth_states[oauth_state]

            logger.info(
                "Social authentication successful",
                provider=provider,
                user_id=user_info.get("id"),
                portal_id=portal_id,
            )

            return AuthenticationResult(
                success=True,
                session_data={
                    "social_provider": provider,
                    "social_id": user_info.get("id"),
                    "email": user_info.get("email"),
                    "first_name": user_info.get("first_name", user_info.get("given_name")),
                    "last_name": user_info.get("last_name", user_info.get("family_name")),
                    "profile_picture": user_info.get("picture"),
                    "auth_method": "social",
                    "verified_at": datetime.now(UTC).isoformat(),
                    "provider_data": user_info,
                },
            )

        except Exception as e:
            logger.exception(
                "Social authentication failed",
                provider=provider,
                error=str(e),
                portal_id=portal_id,
            )

            return AuthenticationResult(
                success=False,
                error_message=f"Authentication with {provider} failed",
            )

    async def _exchange_oauth_code(
        self,
        provider_config: SocialAuthConfig,
        oauth_code: str,
    ) -> dict[str, Any]:
        """Exchange OAuth code for access token (implementation placeholder)."""
        # In real implementation, make HTTP request to provider's token endpoint
        return {
            "access_token": "mock_access_token",
            "token_type": "bearer",
            "expires_in": 3600,
        }

    async def _get_user_info(
        self,
        provider_config: SocialAuthConfig,
        access_token: str,
    ) -> dict[str, Any]:
        """Get user information from provider (implementation placeholder)."""
        # In real implementation, make HTTP request to provider's user info endpoint
        return {
            "id": "mock_user_id",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "picture": "https://example.com/avatar.jpg",
        }


class VoucherAuth(BaseAuthMethod):
    """Voucher-based authentication."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.method_type = AuthMethodType.VOUCHER
        self.allow_multi_use = config.get("allow_multi_use", False)
        self.db_session: AsyncSession | None = None

    def set_database_session(self, db_session: AsyncSession):
        """Set database session for voucher operations."""
        self.db_session = db_session

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate voucher code format."""
        voucher_code = credentials.get("voucher_code", "")
        return len(voucher_code) >= 4 and voucher_code.isalnum()

    async def prepare_authentication(
        self,
        user_data: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Voucher auth doesn't require preparation."""
        return {
            "method": "voucher",
            "message": "Enter your voucher code to access the network",
        }

    async def authenticate(
        self,
        credentials: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> AuthenticationResult:
        """Authenticate using voucher code."""
        # Validate preconditions
        validation_error = self._validate_voucher_preconditions(credentials)
        if validation_error:
            return validation_error

        voucher_code = credentials.get("voucher_code", "").strip().upper()

        # Find and validate voucher
        voucher = await self._find_voucher(voucher_code, portal_id)
        voucher_validation = self._validate_voucher_usage(voucher)
        if voucher_validation:
            return voucher_validation

        # Process successful authentication
        return await self._process_voucher_success(voucher, voucher_code, portal_id)

    def _validate_voucher_preconditions(self, credentials: dict[str, Any]) -> AuthenticationResult | None:
        """Validate basic preconditions for voucher authentication."""
        if not self.db_session:
            return AuthenticationResult(success=False, error_message="Database not configured")

        if not self.validate_credentials(credentials):
            return AuthenticationResult(success=False, error_message="Invalid voucher code format")

        return None

    async def _find_voucher(self, voucher_code: str, portal_id: str) -> Voucher | None:
        """Find voucher by code and portal."""
        query = self.db_session.query(Voucher).filter(
            Voucher.code == voucher_code,
            Voucher.portal_id == uuid.UUID(portal_id),
            Voucher.is_active is True,
        )
        return await query.first()

    def _validate_voucher_usage(self, voucher: Voucher | None) -> AuthenticationResult | None:
        """Validate voucher exists and can be used."""
        if not voucher:
            return AuthenticationResult(success=False, error_message="Invalid voucher code")

        if not voucher.is_valid:
            error_msg = "Voucher expired" if voucher.is_expired else "Voucher not valid"
            return AuthenticationResult(success=False, error_message=error_msg)

        if voucher.is_redeemed and not self.allow_multi_use:
            return AuthenticationResult(success=False, error_message="Voucher already used")

        if voucher.max_devices and voucher.redemption_count >= voucher.max_devices:
            return AuthenticationResult(success=False, error_message="Voucher device limit reached")

        return None

    async def _process_voucher_success(
        self, voucher: Voucher, voucher_code: str, portal_id: str
    ) -> AuthenticationResult:
        """Process successful voucher authentication."""
        # Mark voucher as redeemed
        if not voucher.is_redeemed:
            voucher.is_redeemed = True
            voucher.redeemed_at = datetime.now(UTC)

        voucher.redemption_count += 1
        await self.db_session.commit()

        logger.info(
            "Voucher authentication successful",
            voucher_code=voucher_code,
            voucher_id=str(voucher.id),
            portal_id=portal_id,
        )

        return AuthenticationResult(
            success=True,
            session_data={
                "voucher_code": voucher_code,
                "voucher_id": str(voucher.id),
                "auth_method": "voucher",
                "duration_minutes": voucher.duration_minutes,
                "data_limit_mb": voucher.data_limit_mb,
                "bandwidth_limit_down": voucher.bandwidth_limit_down,
                "bandwidth_limit_up": voucher.bandwidth_limit_up,
                "verified_at": datetime.now(UTC).isoformat(),
            },
        )


class RADIUSAuth(BaseAuthMethod):
    """RADIUS authentication integration."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.method_type = AuthMethodType.RADIUS
        self.radius_server = config.get("server", "localhost")
        self.radius_port = config.get("port", 1812)
        self.radius_secret = config.get("secret", "testing123")
        self.timeout = config.get("timeout", 5)
        self.retries = config.get("retries", 3)

    def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        """Validate username/password format."""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        return len(username) > 0 and len(password) > 0

    async def prepare_authentication(
        self,
        user_data: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """RADIUS auth requires username/password directly."""
        return {
            "method": "radius",
            "message": "Enter your network credentials",
            "fields": ["username", "password"],
        }

    async def authenticate(
        self,
        credentials: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> AuthenticationResult:
        """Authenticate against RADIUS server."""
        username = credentials.get("username")
        password = credentials.get("password")
        client_ip = kwargs.get("client_ip", "127.0.0.1")

        if not self.validate_credentials(credentials):
            return AuthenticationResult(
                success=False,
                error_message="Username and password required",
            )

        # Perform RADIUS authentication
        try:
            auth_result = await self._radius_authenticate(
                username,
                password,
                client_ip,
            )

            if auth_result["success"]:
                logger.info(
                    "RADIUS authentication successful",
                    username=username,
                    portal_id=portal_id,
                    client_ip=client_ip,
                )

                return AuthenticationResult(
                    success=True,
                    session_data={
                        "username": username,
                        "auth_method": "radius",
                        "radius_attributes": auth_result.get("attributes", {}),
                        "verified_at": datetime.now(UTC).isoformat(),
                    },
                )
            return AuthenticationResult(
                success=False,
                error_message="Invalid network credentials",
            )

        except Exception as e:
            logger.exception(
                "RADIUS authentication error",
                username=username,
                error=str(e),
                portal_id=portal_id,
            )

            return AuthenticationResult(
                success=False,
                error_message="Network authentication service unavailable",
            )

    async def _radius_authenticate(
        self,
        username: str,
        password: str,
        client_ip: str,
    ) -> dict[str, Any]:
        """Perform RADIUS authentication (implementation placeholder)."""
        # In real implementation, use pyrad library
        try:
            # Mock successful authentication
            return {
                "success": True,
                "attributes": {
                    "Session-Timeout": 3600,
                    "Idle-Timeout": 1800,
                    "Acct-Interim-Interval": 60,
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


class AuthenticationManager:
    """Manages multiple authentication methods for captive portals."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.auth_methods: dict[str, BaseAuthMethod] = {}
        self._default_method = "email"

    def register_auth_method(
        self,
        method_name: str,
        auth_method: BaseAuthMethod,
    ):
        """Register an authentication method."""
        self.auth_methods[method_name] = auth_method

        # Set database session for methods that need it
        if hasattr(auth_method, "set_database_session"):
            auth_method.set_database_session(self.db)

        logger.info("Authentication method registered", method=method_name)

    def get_auth_method(self, method_name: str) -> BaseAuthMethod | None:
        """Get authentication method by name."""
        return self.auth_methods.get(method_name)

    def list_auth_methods(self) -> list[str]:
        """List available authentication method names."""
        return list(self.auth_methods.keys())

    async def prepare_authentication(
        self,
        method_name: str,
        user_data: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare authentication for specified method."""
        auth_method = self.get_auth_method(method_name)
        if not auth_method:
            return {"error": f"Authentication method '{method_name}' not available"}

        try:
            return await auth_method.prepare_authentication(user_data, portal_id, **kwargs)
        except Exception as e:
            logger.exception(
                "Authentication preparation failed",
                method=method_name,
                error=str(e),
                portal_id=portal_id,
            )
            return {"error": "Authentication preparation failed"}

    async def authenticate(
        self,
        method_name: str,
        credentials: dict[str, Any],
        portal_id: str,
        **kwargs,
    ) -> AuthenticationResult:
        """Authenticate user with specified method."""
        auth_method = self.get_auth_method(method_name)
        if not auth_method:
            return AuthenticationResult(
                success=False,
                error_message=f"Authentication method '{method_name}' not available",
            )

        try:
            return await auth_method.authenticate(credentials, portal_id, **kwargs)
        except Exception as e:
            logger.exception(
                "Authentication failed",
                method=method_name,
                error=str(e),
                portal_id=portal_id,
            )
            return AuthenticationResult(
                success=False,
                error_message="Authentication service error",
            )

    def set_default_method(self, method_name: str):
        """Set default authentication method."""
        if method_name in self.auth_methods:
            self._default_method = method_name
            logger.info("Default auth method set", method=method_name)

    def get_default_method(self) -> str:
        """Get default authentication method name."""
        return self._default_method
