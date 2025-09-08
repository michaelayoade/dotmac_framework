"""
Tenant Module - Compatibility Module

Re-exports tenant functionality from dotmac_shared for backward compatibility.
"""
try:
    from ...dotmac_shared.middleware.dotmac_middleware.tenant import TenantMiddleware
    from ...dotmac_shared.middleware.tenant import TenantMiddleware as SharedTenantMiddleware

    # Create a TenantIdentityResolver compatibility stub
    class TenantIdentityResolver:
        """Compatibility stub for TenantIdentityResolver."""

        def __init__(self) -> None:
            self.patterns = {}

        def configure_patterns(self, patterns) -> None:
            """Configure tenant resolution patterns."""
            self.patterns = patterns

        def resolve_tenant(self, request) -> None:
            """Resolve tenant from request."""
            return

    _tenant_available = True
except ImportError:
    _tenant_available = False

    # Stub implementations when not available
    class TenantMiddleware:
        """Stub TenantMiddleware."""

        def __init__(self, *args, **kwargs) -> None:
            pass

    class TenantIdentityResolver:
        """Stub TenantIdentityResolver."""

        def __init__(self) -> None:
            self.patterns = {}

        def configure_patterns(self, patterns) -> None:
            """Configure tenant resolution patterns."""
            self.patterns = patterns

        def resolve_tenant(self, request) -> None:
            """Resolve tenant from request."""
            return


__all__ = ["TenantIdentityResolver", "TenantMiddleware"]
