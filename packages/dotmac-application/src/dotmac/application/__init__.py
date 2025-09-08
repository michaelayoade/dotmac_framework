"""
DotMac Application Factory and API Framework

This package provides a unified way to create FastAPI applications with:
- Consistent startup/shutdown procedures
- Standardized middleware stacks via provider composition
- Deployment-aware configuration
- Router registration and standard endpoints
- Lifecycle orchestration

PLUS comprehensive API utilities:
- Exception handlers with standard formatting
- Router factory with CRUD generation
- Dependency injection utilities
- Rate limiting middleware

Example usage:

    from dotmac.application import (
        create_app,
        create_management_platform_app,
        create_isp_framework_app,
        PlatformConfig,
        # API Framework components
        RouterFactory,
        standard_exception_handler,
        StandardDependencies,
        rate_limit
    )

    # Create a basic app
    config = PlatformConfig(
        platform_name="my_platform",
        title="My Platform",
        description="Platform description"
    )
    app = create_app(config)

    # Use API framework components
    router = RouterFactory.create_crud_router(MyModel, MyService)
    app.include_router(router)
"""

from .api.exception_handlers import (
    DotMacHTTPException,
    ValidationHTTPException,
    standard_exception_handler,
)
from .api.router_factory import RouterFactory, create_crud_router, create_router
from .config import (
    DeploymentContext,
    DeploymentMode,
    IsolationLevel,
    ObservabilityProvider,
    PlatformConfig,
    ResourceLimits,
    RouterConfig,
    SecurityProvider,
    TenantBoundaryProvider,
    TenantConfig,
)
from .dependencies.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_current_user,
    get_paginated_deps,
    get_standard_deps,
)

# Standard endpoints
from .endpoints import (
    StandardEndpoints,
    add_standard_endpoints,
    create_endpoints_manager,
)

# Application factory functions
from .factory import (
    DeploymentAwareApplicationFactory,
    DotMacApplicationFactory,
    create_app,
    create_isp_framework_app,
    create_management_platform_app,
)

# Lifecycle management
from .lifecycle import (
    StandardLifecycleManager,
    create_lifespan_manager,
)

# Middleware composition
from .middleware import (
    StandardMiddlewareStack,
    apply_standard_middleware,
)
from .middleware.rate_limiting_decorators import (
    RateLimitMiddleware,
    create_rate_limiter,
    rate_limit,
    rate_limit_auth,
    rate_limit_strict,
    rate_limit_user,
)
from .providers import Providers

# Router registration
from .routing import (
    RouterRegistry,
    SafeRouterLoader,
    create_router_registry,
    register_routers,
)
from .security import (
    SENSITIVE_ENDPOINTS,
    APIKeyValidator,
    InputSanitizer,
    SecurityDecorators,
    SecurityHeaders,
    apply_security_middleware,
    require_active_user,
    require_admin,
    require_tenant_access,
    validate_entity_ownership,
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
    # Provider protocols
    "Providers",
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
    # API Framework Components
    "standard_exception_handler",
    "DotMacHTTPException",
    "ValidationHTTPException",
    "RouterFactory",
    "create_router",
    "create_crud_router",
    "StandardDependencies",
    "PaginatedDependencies",
    "get_standard_deps",
    "get_paginated_deps",
    "get_current_user",
    # Rate limiting
    "rate_limit",
    "rate_limit_strict",
    "rate_limit_auth",
    "rate_limit_user",
    "RateLimitMiddleware",
    "create_rate_limiter",
    # Security
    "SecurityDecorators",
    "SecurityHeaders",
    "InputSanitizer",
    "APIKeyValidator",
    "apply_security_middleware",
    "require_admin",
    "require_active_user",
    "require_tenant_access",
    "validate_entity_ownership",
    "SENSITIVE_ENDPOINTS",
    # Package metadata
    "__version__",
]
