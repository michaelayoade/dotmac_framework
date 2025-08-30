"""
Integration modules for unified user management service.

Provides seamless integration with authentication systems, external services,
and platform-specific components.
"""

from .auth_integration import AuthIntegration, create_auth_integration

__all__ = ["AuthIntegration", "create_auth_integration"]
