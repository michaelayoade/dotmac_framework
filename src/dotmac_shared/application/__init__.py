"""
DEPRECATED: Shared application factory for all DotMac platforms.

This module is deprecated. Use `dotmac.application` instead.

Migration:
    Before: from dotmac_shared.application import create_management_platform_app
    After:  from dotmac.application import create_management_platform_app
"""

import warnings

warnings.warn(
    "dotmac_shared.application is deprecated and will be removed in a future version. "
    "Use 'dotmac.application' instead. "
    "Example: from dotmac.application import create_app, create_management_platform_app",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the public API from the new package for backward compatibility
try:
    from dotmac.application import (  # Configuration types; Provider protocols; Components; Middleware; Factory functions
        DeploymentAwareApplicationFactory,
        DeploymentContext,
        DeploymentMode,
        DotMacApplicationFactory,
        IsolationLevel,
        ObservabilityProvider,
        PlatformConfig,
        Providers,
        ResourceLimits,
        RouterConfig,
        RouterRegistry,
        SafeRouterLoader,
        SecurityProvider,
        StandardEndpoints,
        StandardLifecycleManager,
        StandardMiddlewareStack,
        TenantBoundaryProvider,
        TenantConfig,
        apply_standard_middleware,
        create_app,
        create_isp_framework_app,
        create_management_platform_app,
    )

    # Legacy aliases for backward compatibility
    def create_management_platform_app_legacy(config=None):
        """Legacy wrapper for create_management_platform_app."""
        warnings.warn(
            "Use dotmac.application.create_management_platform_app directly",
            DeprecationWarning,
            stacklevel=2,
        )
        return create_management_platform_app(config)

    def create_isp_framework_app_legacy(tenant_config=None, base_config=None):
        """Legacy wrapper for create_isp_framework_app."""
        warnings.warn(
            "Use dotmac.application.create_isp_framework_app directly",
            DeprecationWarning,
            stacklevel=2,
        )
        return create_isp_framework_app(tenant_config, base_config)

except ImportError as e:
    warnings.warn(
        f"Could not import from dotmac.application: {e}. "
        "Please install the dotmac-application package.",
        ImportWarning,
        stacklevel=2,
    )

    # Fallback to original implementations if new package not available
    from .config import (
        DeploymentContext,
        DeploymentMode,
        IsolationLevel,
        PlatformConfig,
        ResourceLimits,
        RouterConfig,
        TenantConfig,
    )
    from .endpoints import StandardEndpoints
    from .factory import (
        DeploymentAwareApplicationFactory,
        DotMacApplicationFactory,
        create_isp_framework_app,
        create_management_platform_app,
    )
    from .lifecycle import StandardLifecycleManager
    from .middleware import StandardMiddlewareStack
    from .routing import RouterRegistry, SafeRouterLoader

    # Define placeholders for new concepts not in legacy
    Providers = None
    SecurityProvider = None
    TenantBoundaryProvider = None
    ObservabilityProvider = None
    create_app = create_management_platform_app  # Fallback
    apply_standard_middleware = None

__all__ = [
    # Factory functions (main public API)
    "create_app",
    "create_management_platform_app",
    "create_isp_framework_app",
    # Legacy wrappers
    "create_management_platform_app_legacy",
    "create_isp_framework_app_legacy",
    # Configuration types
    "PlatformConfig",
    "DeploymentContext",
    "TenantConfig",
    "RouterConfig",
    "DeploymentMode",
    "IsolationLevel",
    "ResourceLimits",
    "Providers",
    # Provider protocols
    "SecurityProvider",
    "TenantBoundaryProvider",
    "ObservabilityProvider",
    # Middleware
    "apply_standard_middleware",
    "StandardMiddlewareStack",
    # Factory classes
    "DotMacApplicationFactory",
    "DeploymentAwareApplicationFactory",
    # Components
    "StandardLifecycleManager",
    "RouterRegistry",
    "SafeRouterLoader",
    "StandardEndpoints",
]
