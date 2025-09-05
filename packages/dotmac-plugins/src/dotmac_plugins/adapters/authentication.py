"""
Authentication domain adapter for the plugin system.

Provides specialized interfaces for authentication plugins like OAuth, LDAP, JWT, and MFA.
"""

import logging
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ..core.exceptions import PluginError
from ..core.plugin_base import BasePlugin


class AuthMethod(Enum):
    """Authentication methods."""

    PASSWORD = "password"
    TOKEN = "token"
    OAUTH = "oauth"
    LDAP = "ldap"
    SAML = "saml"
    MFA = "mfa"


@dataclass
class AuthRequest:
    """Authentication request."""

    username: str
    credentials: dict[str, Any]
    method: AuthMethod
    context: dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class AuthResult:
    """Authentication result."""

    success: bool
    user_id: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[str] = None
    permissions: list[str] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}


class AuthenticationPlugin(BasePlugin):
    """Base class for authentication plugins."""

    @abstractmethod
    async def authenticate(self, request: AuthRequest) -> AuthResult:
        """Authenticate a user."""
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> AuthResult:
        """Validate an authentication token."""
        pass

    def get_supported_methods(self) -> list[AuthMethod]:
        """Get supported authentication methods."""
        return [AuthMethod.PASSWORD]  # Override in subclasses


class AuthenticationAdapter:
    """Domain adapter for authentication plugins."""

    def __init__(self):
        self._plugins: dict[str, AuthenticationPlugin] = {}
        self._method_providers: dict[AuthMethod, str] = {}
        self._logger = logging.getLogger("plugins.authentication_adapter")

    def register_plugin(self, plugin_name: str, plugin: AuthenticationPlugin) -> None:
        """Register an authentication plugin."""
        if not isinstance(plugin, AuthenticationPlugin):
            raise PluginError(f"Plugin {plugin_name} is not an AuthenticationPlugin")

        self._plugins[plugin_name] = plugin

        # Register as provider for supported methods
        for method in plugin.get_supported_methods():
            if method not in self._method_providers:
                self._method_providers[method] = plugin_name

        self._logger.info(f"Registered authentication plugin: {plugin_name}")

    async def authenticate(self, request: AuthRequest, provider: Optional[str] = None) -> AuthResult:
        """Authenticate using specified or default provider."""
        if provider:
            if provider not in self._plugins:
                raise PluginError(f"Authentication provider {provider} not found")
            plugin = self._plugins[provider]
        else:
            provider_name = self._method_providers.get(request.method)
            if not provider_name:
                raise PluginError(f"No provider available for method: {request.method}")
            plugin = self._plugins[provider_name]

        return await plugin.authenticate(request)

    async def validate_token(self, token: str, provider: Optional[str] = None) -> AuthResult:
        """Validate token using specified or default provider."""
        # Implementation would select appropriate provider
        if not self._plugins:
            raise PluginError("No authentication providers available")

        plugin = list(self._plugins.values())[0]  # Use first available
        return await plugin.validate_token(token)
