"""
DotMac Middleware Suite - Unified Request Processing and Security Middleware

This package consolidates 15+ middleware implementations across the DotMac Framework,
providing consistent security posture and reusable middleware plugins.

Key Components:
- Core middleware stack for FastAPI applications
- Security middleware (CSRF, headers, input validation)
- Tenant isolation and multi-tenant database context
- Request processing (logging, metrics, tracing)
- Authentication integration middleware
- Pluggable middleware system for extensions

Usage:
    from dotmac_middleware import MiddlewareStack, SecurityConfig

    app = FastAPI()

    # Apply unified middleware stack
    middleware_stack = MiddlewareStack(
        security=SecurityConfig(
            csrf_enabled=True,
            rate_limiting=True,
            tenant_isolation=True
        )
    )
    middleware_stack.apply(app)
"""

from .auth import (
    AuthenticationMiddleware,
    AuthorizationMiddleware,
    JWTMiddleware,
    SessionMiddleware,
)
from .core import MiddlewareConfig, MiddlewareManager, MiddlewareStack
from .plugins import MiddlewarePlugin, MiddlewareRegistry, PluginManager
from .processing import (
    MetricsMiddleware,
    PerformanceMiddleware,
    RequestLoggingMiddleware,
    TracingMiddleware,
)
from .security import (
    CSRFMiddleware,
    InputValidationMiddleware,
    RateLimitingMiddleware,
    SecurityConfig,
    SecurityHeadersMiddleware,
    SecurityMiddleware,
)
from .tenant import (
    DatabaseIsolationMiddleware,
    TenantConfig,
    TenantContextMiddleware,
    TenantMiddleware,
)

__version__ = "1.0.0"
__all__ = [
    "MiddlewareStack",
    "MiddlewareConfig",
    "MiddlewareManager",
    # Security
    "SecurityMiddleware",
    "SecurityConfig",
    "CSRFMiddleware",
    "RateLimitingMiddleware",
    "SecurityHeadersMiddleware",
    "InputValidationMiddleware",
    # Tenant
    "TenantMiddleware",
    "TenantConfig",
    "TenantContextMiddleware",
    "DatabaseIsolationMiddleware",
    # Processing
    "RequestLoggingMiddleware",
    "MetricsMiddleware",
    "TracingMiddleware",
    "PerformanceMiddleware",
    "AuthenticationMiddleware",
    "AuthorizationMiddleware",
    "JWTMiddleware",
    "SessionMiddleware",
    # Plugins
    "MiddlewarePlugin",
    "PluginManager",
    "MiddlewareRegistry",
]
