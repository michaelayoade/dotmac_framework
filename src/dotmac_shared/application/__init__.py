"""
Shared application factory for all DotMac platforms.

This module provides a unified way to create FastAPI applications with:
- Consistent startup/shutdown procedures
- Standardized middleware stacks
- Deployment-aware configuration
- Container optimization
- Multi-tenant isolation
"""

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

__all__ = [
    "DotMacApplicationFactory",
    "DeploymentAwareApplicationFactory",
    "create_isp_framework_app",
    "create_management_platform_app",
    "PlatformConfig",
    "DeploymentContext",
    "TenantConfig",
    "RouterConfig",
    "DeploymentMode",
    "IsolationLevel",
    "ResourceLimits",
    "RouterRegistry",
    "SafeRouterLoader",
    "StandardMiddlewareStack",
    "StandardLifecycleManager",
    "StandardEndpoints",
]
