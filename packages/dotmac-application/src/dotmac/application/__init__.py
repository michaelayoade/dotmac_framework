"""
DotMac Application Factory and Lifecycle Management

This package provides a unified way to create FastAPI applications with:
- Consistent startup/shutdown procedures
- Standardized middleware stacks via provider composition
- Deployment-aware configuration
- Router registration and standard endpoints
- Lifecycle orchestration

Example usage:

    from dotmac.application import (
        create_app, 
        create_management_platform_app,
        create_isp_framework_app,
        PlatformConfig
    )
    
    # Create a basic app
    config = PlatformConfig(
        platform_name="my_platform",
        title="My Platform",
        description="Platform description"
    )
    app = create_app(config)
    
    # Create platform-specific apps
    management_app = create_management_platform_app()
    isp_app = create_isp_framework_app()
"""

# Core configuration types
from .config import (
    DeploymentContext,
    DeploymentMode,
    IsolationLevel,
    PlatformConfig,
    Providers,
    ResourceLimits,
    RouterConfig,
    TenantConfig,
    SecurityProvider,
    TenantBoundaryProvider,
    ObservabilityProvider,
)

# Application factory functions
from .factory import (
    create_app,
    create_management_platform_app,
    create_isp_framework_app,
    DotMacApplicationFactory,
    DeploymentAwareApplicationFactory,
)

# Middleware composition
from .middleware import (
    apply_standard_middleware,
    StandardMiddlewareStack,
)

# Lifecycle management
from .lifecycle import (
    StandardLifecycleManager,
    create_lifespan_manager,
)

# Router registration
from .routing import (
    RouterRegistry,
    SafeRouterLoader,
    register_routers,
    create_router_registry,
)

# Standard endpoints
from .endpoints import (
    StandardEndpoints,
    add_standard_endpoints,
    create_endpoints_manager,
)

__version__ = "1.0.0"

__all__ = [
    # Factory functions (main public API)
    "create_app",
    "create_management_platform_app", 
    "create_isp_framework_app",
    
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
    
    # Middleware composition
    "apply_standard_middleware",
    "StandardMiddlewareStack",
    
    # Advanced factory classes
    "DotMacApplicationFactory",
    "DeploymentAwareApplicationFactory",
    
    # Lifecycle management
    "StandardLifecycleManager",
    "create_lifespan_manager",
    
    # Router management
    "RouterRegistry",
    "SafeRouterLoader",
    "register_routers",
    "create_router_registry",
    
    # Endpoints
    "StandardEndpoints", 
    "add_standard_endpoints",
    "create_endpoints_manager",
    
    # Package metadata
    "__version__",
]