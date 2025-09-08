"""
Current User - Compatibility Module

Re-exports platform.auth.current_user for backward compatibility.
"""

from __future__ import annotations

from typing import Any

try:
    from dotmac.platform.auth.current_user import (
        ServiceClaims,
        UserClaims,
        get_current_service,
    )
    from dotmac.platform.auth.current_user import (
        get_current_tenant as _get_current_tenant,
    )
    from dotmac.platform.auth.current_user import get_current_user as _get_current_user

    # Re-export with compatibility wrappers
    def get_current_user(*args: Any, **kwargs: Any) -> dict[str, Any] | UserClaims:
        """Get current user - returns UserClaims or dict for compatibility."""
        return _get_current_user(*args, **kwargs)

    def get_current_tenant(*args: Any, **kwargs: Any) -> str:
        """Get current tenant ID."""
        return _get_current_tenant(*args, **kwargs)

except ImportError:
    # Fallback for development/testing when platform services not available
    def get_current_tenant(*args: Any, **kwargs: Any) -> str:
        """Stub function for development."""
        return "tenant-test"

    def get_current_user(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Stub function for development."""
        return {"user_id": "user-test", "tenant_id": "tenant-test"}

    def get_current_service(*args: Any, **kwargs: Any) -> dict[str, Any]:
        """Stub function for development."""
        return {"service_name": "service-test", "tenant_id": "tenant-test"}

    class UserClaims:
        """Stub UserClaims for development."""

        def __init__(self, **kwargs):
            self.user_id = kwargs.get("user_id", "dev-user")
            self.tenant_id = kwargs.get("tenant_id", "dev-tenant")

    class ServiceClaims:
        """Stub ServiceClaims for development."""

        def __init__(self, **kwargs):
            self.service_name = kwargs.get("service_name", "dev-service")
            self.tenant_id = kwargs.get("tenant_id", "dev-tenant")


__all__ = ["get_current_tenant", "get_current_user", "get_current_service", "UserClaims", "ServiceClaims"]
