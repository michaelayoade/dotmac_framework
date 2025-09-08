"""Authentication manager for coordinating captive portal auth providers."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from dotmac.core.exceptions import ServiceError

from ..models import AuthMethodType
from ..schemas import AuthenticationRequest
from .base import AuthenticationResult, BaseAuthProvider
from .email import EmailAuthProvider
from .social import SocialAuthProvider
from .voucher import VoucherAuthProvider

logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Manages multiple authentication providers for captive portal."""

    def __init__(self, db_session, tenant_id: str):
        """Initialize authentication manager."""
        self.db = db_session
        self.tenant_id = tenant_id
        self._providers: dict[AuthMethodType, BaseAuthProvider] = {}
        self._provider_configs: dict[AuthMethodType, dict[str, Any]] = {}

        # Initialize default provider configurations
        self._init_default_configs()

    def register_provider(
        self,
        auth_method: AuthMethodType,
        provider_class: type[BaseAuthProvider],
        config: dict[str, Any],
    ):
        """Register an authentication provider."""
        try:
            provider = provider_class(self.db, self.tenant_id, config)
            self._providers[auth_method] = provider
            self._provider_configs[auth_method] = config

            logger.info(f"Registered {auth_method.value} authentication provider")

        except Exception as e:
            logger.error(f"Failed to register {auth_method.value} provider: {e}")
            raise ServiceError(f"Failed to register authentication provider: {str(e)}") from e

    async def authenticate(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate user using appropriate provider."""
        try:
            # Get the provider for this auth method
            provider = self._get_provider(request.auth_method)

            if not provider:
                return AuthenticationResult(
                    success=False,
                    error_message=f"Authentication method {request.auth_method.value} not available",
                )
            # Validate request format
            if not provider.validate_request(request):
                return AuthenticationResult(success=False, error_message="Invalid authentication request format")
            # Perform authentication
            result = await provider.authenticate(request)

            # Log authentication attempt
            await self._log_authentication_attempt(request, result)

            return result

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return AuthenticationResult(success=False, error_message="Authentication failed")

    async def prepare_authentication(
        self, auth_method: AuthMethodType, request: AuthenticationRequest
    ) -> dict[str, Any]:
        """Prepare authentication (e.g., send verification code, generate OAuth URL)."""
        try:
            provider = self._get_provider(auth_method)

            if not provider:
                raise ServiceError(f"Authentication method {auth_method.value} not available")

            return await provider.prepare_authentication(request)

        except Exception as e:
            logger.error(f"Failed to prepare authentication: {e}")
            raise ServiceError(f"Failed to prepare authentication: {str(e)}") from e

    def get_available_methods(self, portal_id: str) -> dict[AuthMethodType, dict[str, Any]]:
        """Get available authentication methods for a portal."""
        available_methods = {}

        for auth_method, provider in self._providers.items():
            try:
                # Get provider configuration and status
                config = self._provider_configs.get(auth_method, {})

                available_methods[auth_method] = {
                    "available": True,
                    "display_name": self._get_display_name(auth_method),
                    "description": self._get_description(auth_method),
                    "configuration_required": self._requires_configuration(auth_method),
                    "supports_preparation": hasattr(provider, "prepare_authentication"),
                    "config": {
                        key: value
                        for key, value in config.items()
                        if key
                        not in [
                            "client_secret",
                            "app_secret",
                            "private_key",
                        ]  # Hide sensitive data
                    },
                }

            except Exception as e:
                logger.warning(f"Error checking {auth_method.value} provider: {e}")
                available_methods[auth_method] = {"available": False, "error": str(e)}

        return available_methods

    def _get_provider(self, auth_method: AuthMethodType) -> Optional[BaseAuthProvider]:
        """Get provider for authentication method."""
        return self._providers.get(auth_method)

    def _init_default_configs(self):
        """Initialize default provider configurations."""
        # Email authentication
        email_config = {
            "require_verification": True,
            "verification_code_length": 6,
            "verification_expires_minutes": 15,
        }

        # Social authentication
        social_config = {
            "providers": ["google", "facebook"],
            "google": {
                "client_id": "",  # Should be configured per deployment
                "client_secret": "",  # Should be configured per deployment
            },
            "facebook": {
                "app_id": "",  # Should be configured per deployment
                "app_secret": "",  # Should be configured per deployment
            },
            "redirect_uri": "http://localhost:8000/auth/callback",
        }

        # Voucher authentication
        voucher_config = {"allow_multi_device": True, "create_user_account": False}

        # Register default providers
        try:
            self.register_provider(AuthMethodType.EMAIL, EmailAuthProvider, email_config)
            self.register_provider(AuthMethodType.SOCIAL, SocialAuthProvider, social_config)
            self.register_provider(AuthMethodType.VOUCHER, VoucherAuthProvider, voucher_config)
        except Exception as e:
            logger.error(f"Failed to register default providers: {e}")

    def _get_display_name(self, auth_method: AuthMethodType) -> str:
        """Get display name for authentication method."""
        display_names = {
            AuthMethodType.EMAIL: "Email Verification",
            AuthMethodType.SMS: "SMS Verification",
            AuthMethodType.SOCIAL: "Social Media Login",
            AuthMethodType.VOUCHER: "Access Code",
            AuthMethodType.RADIUS: "Username & Password",
            AuthMethodType.FREE: "Free Access",
            AuthMethodType.PAYMENT: "Pay for Access",
        }
        return display_names.get(auth_method, auth_method.value.title())

    def _get_description(self, auth_method: AuthMethodType) -> str:
        """Get description for authentication method."""
        descriptions = {
            AuthMethodType.EMAIL: "Verify your email address to get internet access",
            AuthMethodType.SMS: "Verify your phone number via SMS code",
            AuthMethodType.SOCIAL: "Sign in with your Google, Facebook, or other social account",
            AuthMethodType.VOUCHER: "Enter your prepaid access code",
            AuthMethodType.RADIUS: "Login with your existing username and password",
            AuthMethodType.FREE: "Get free internet access",
            AuthMethodType.PAYMENT: "Purchase internet access with credit card",
        }
        return descriptions.get(auth_method, "Authentication method")

    def _requires_configuration(self, auth_method: AuthMethodType) -> bool:
        """Check if authentication method requires additional configuration."""
        config_required = {
            AuthMethodType.EMAIL: False,  # Basic email works out of the box
            AuthMethodType.SMS: True,  # Requires SMS provider configuration
            AuthMethodType.SOCIAL: True,  # Requires OAuth app configuration
            AuthMethodType.VOUCHER: False,  # Works with basic configuration
            AuthMethodType.RADIUS: True,  # Requires RADIUS server configuration
            AuthMethodType.FREE: False,  # No configuration needed
            AuthMethodType.PAYMENT: True,  # Requires payment processor configuration
        }
        return config_required.get(auth_method, True)

    async def _log_authentication_attempt(self, request: AuthenticationRequest, result: AuthenticationResult):
        """Log authentication attempt for analytics and security."""
        try:
            log_data = {
                "timestamp": datetime.now(timezone.utc),
                "auth_method": request.auth_method.value,
                "portal_id": request.portal_id,
                "client_ip": request.client_ip,
                "client_mac": request.client_mac,
                "success": result.success,
                "user_id": result.user_id,
                "error_message": result.error_message,
                "tenant_id": self.tenant_id,
            }

            # In production, store this in analytics database or send to analytics service
            logger.info(f"Auth attempt: {log_data}")

            # Future integration point with analytics service
            # from dotmac_isp.modules.analytics.service import AnalyticsService
            # analytics = AnalyticsService(self.db, self.tenant_id)
            # await analytics.track_event("captive_portal_auth_attempt", log_data)

        except Exception as e:
            logger.warning(f"Failed to log authentication attempt: {e}")

    def update_provider_config(self, auth_method: AuthMethodType, config: dict[str, Any]):
        """Update provider configuration."""
        try:
            if auth_method in self._providers:
                # Re-register provider with new config
                provider_class = type(self._providers[auth_method])
                self.register_provider(auth_method, provider_class, config)
                logger.info(f"Updated configuration for {auth_method.value} provider")
            else:
                logger.warning(f"Cannot update config for unregistered provider: {auth_method.value}")

        except Exception as e:
            logger.error(f"Failed to update provider config: {e}")
            raise ServiceError(f"Failed to update provider configuration: {str(e)}") from e

    def get_provider_status(self, auth_method: AuthMethodType) -> dict[str, Any]:
        """Get detailed status of a specific provider."""
        provider = self._get_provider(auth_method)

        if not provider:
            return {
                "registered": False,
                "available": False,
                "error": "Provider not registered",
            }

        try:
            # Basic health check - could be extended with provider-specific checks
            status = {
                "registered": True,
                "available": True,
                "provider_class": type(provider).__name__,
                "configuration": {
                    key: value
                    for key, value in self._provider_configs.get(auth_method, {}).items()
                    if key
                    not in [
                        "client_secret",
                        "app_secret",
                        "private_key",
                    ]  # Hide secrets
                },
            }

            return status

        except Exception as e:
            return {"registered": True, "available": False, "error": str(e)}
