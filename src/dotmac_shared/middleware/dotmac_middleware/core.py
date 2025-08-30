"""
Core middleware stack management and configuration.

This module provides the central MiddlewareStack that orchestrates all middleware
components with proper ordering and dependency management.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

import structlog
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class MiddlewareType(Enum):
    """Middleware categories for proper ordering."""

    # Security middleware (highest priority)
    SECURITY_HEADERS = "security_headers"
    CORS = "cors"
    CSRF = "csrf"
    RATE_LIMITING = "rate_limiting"
    INPUT_VALIDATION = "input_validation"

    # Authentication and authorization
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    JWT = "jwt"
    SESSION = "session"

    # Tenant isolation
    TENANT_CONTEXT = "tenant_context"
    DATABASE_ISOLATION = "database_isolation"

    # Request processing
    REQUEST_LOGGING = "request_logging"
    METRICS = "metrics"
    TRACING = "tracing"
    PERFORMANCE = "performance"

    # Custom plugins (lowest priority)
    PLUGIN = "plugin"


@dataclass
class MiddlewareConfig:
    """Configuration for middleware components."""

    # Security settings
    security_enabled: bool = True
    csrf_enabled: bool = True
    rate_limiting_enabled: bool = True
    security_headers_enabled: bool = True
    input_validation_enabled: bool = True

    # Authentication settings
    auth_enabled: bool = True
    jwt_enabled: bool = True
    session_enabled: bool = False

    # Tenant settings
    tenant_isolation_enabled: bool = True
    database_isolation_enabled: bool = True

    # Processing settings
    logging_enabled: bool = True
    metrics_enabled: bool = True
    tracing_enabled: bool = False
    performance_monitoring_enabled: bool = True

    # Plugin settings
    plugins_enabled: bool = True

    # Advanced configuration
    middleware_order: list[MiddlewareType] | None = None
    custom_middlewares: dict[str, type[BaseHTTPMiddleware]] = field(
        default_factory=dict
    )
    excluded_paths: list[str] = field(default_factory=list)

    # Environment-specific overrides
    environment: str = "development"
    debug: bool = False


class MiddlewareManager:
    """Manages middleware lifecycle and dependencies."""

    def __init__(self, config: MiddlewareConfig):
        self.config = config
        self._middlewares: dict[MiddlewareType, BaseHTTPMiddleware] = {}
        self._dependencies: dict[MiddlewareType, list[MiddlewareType]] = {}
        self._initialized = False

    def register_middleware(
        self,
        middleware_type: MiddlewareType,
        middleware_class: type[BaseHTTPMiddleware],
        dependencies: list[MiddlewareType] | None = None,
        **kwargs,
    ) -> None:
        """Register a middleware component with dependencies."""
        if self._initialized:
            raise RuntimeError("Cannot register middleware after initialization")

        self._middlewares[middleware_type] = middleware_class(**kwargs)
        self._dependencies[middleware_type] = dependencies or []

    def get_middleware_order(self) -> list[MiddlewareType]:
        """Get the proper middleware execution order."""
        if self.config.middleware_order:
            return self.config.middleware_order

        # Default ordering based on middleware priorities
        default_order = [
            # Security first (outermost layer)
            MiddlewareType.SECURITY_HEADERS,
            MiddlewareType.CORS,
            MiddlewareType.CSRF,
            MiddlewareType.RATE_LIMITING,
            MiddlewareType.INPUT_VALIDATION,
            # Authentication and authorization
            MiddlewareType.AUTHENTICATION,
            MiddlewareType.AUTHORIZATION,
            MiddlewareType.JWT,
            MiddlewareType.SESSION,
            # Tenant isolation
            MiddlewareType.TENANT_CONTEXT,
            MiddlewareType.DATABASE_ISOLATION,
            # Request processing (innermost layer)
            MiddlewareType.REQUEST_LOGGING,
            MiddlewareType.METRICS,
            MiddlewareType.TRACING,
            MiddlewareType.PERFORMANCE,
            # Custom plugins
            MiddlewareType.PLUGIN,
        ]

        # Filter based on enabled components
        return [m for m in default_order if m in self._middlewares]

    def initialize(self) -> None:
        """Initialize all middleware components."""
        if self._initialized:
            return

        # Validate dependencies
        for middleware_type, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._middlewares:
                    raise ValueError(f"Missing dependency {dep} for {middleware_type}")

        # Initialize middleware components
        for middleware_type, middleware in self._middlewares.items():
            if hasattr(middleware, "initialize"):
                middleware.initialize()

        self._initialized = True
        logger.info(
            "Middleware manager initialized", middleware_count=len(self._middlewares)
        )

    def get_ordered_middlewares(self) -> list[BaseHTTPMiddleware]:
        """Get middlewares in proper execution order."""
        if not self._initialized:
            self.initialize()

        order = self.get_middleware_order()
        return [
            self._middlewares[mtype] for mtype in order if mtype in self._middlewares
        ]


class MiddlewareStack:
    """
    Unified middleware stack that consolidates all DotMac Framework middleware.

    This class replaces 15+ scattered middleware implementations with a single,
    configurable, and consistent middleware stack.
    """

    def __init__(self, config: MiddlewareConfig | None = None):
        self.config = config or MiddlewareConfig()
        self.manager = MiddlewareManager(self.config)
        self._app: FastAPI | None = None
        self._applied = False

    def register_security_middlewares(self) -> None:
        """Register security middleware components."""
        from .security import (
            CSRFMiddleware,
            InputValidationMiddleware,
            RateLimitingMiddleware,
            SecurityHeadersMiddleware,
        )

        if self.config.security_headers_enabled:
            self.manager.register_middleware(
                MiddlewareType.SECURITY_HEADERS,
                SecurityHeadersMiddleware,
                environment=self.config.environment,
            )

        if self.config.csrf_enabled:
            self.manager.register_middleware(
                MiddlewareType.CSRF,
                CSRFMiddleware,
                excluded_paths=self.config.excluded_paths,
            )

        if self.config.rate_limiting_enabled:
            self.manager.register_middleware(
                MiddlewareType.RATE_LIMITING, RateLimitingMiddleware
            )

        if self.config.input_validation_enabled:
            self.manager.register_middleware(
                MiddlewareType.INPUT_VALIDATION, InputValidationMiddleware
            )

    def register_auth_middlewares(self) -> None:
        """Register authentication middleware components."""
        from .auth import AuthenticationMiddleware, JWTMiddleware, SessionMiddleware

        if self.config.auth_enabled:
            self.manager.register_middleware(
                MiddlewareType.AUTHENTICATION, AuthenticationMiddleware
            )

        if self.config.jwt_enabled:
            self.manager.register_middleware(
                MiddlewareType.JWT,
                JWTMiddleware,
                dependencies=[MiddlewareType.AUTHENTICATION],
            )

        if self.config.session_enabled:
            self.manager.register_middleware(MiddlewareType.SESSION, SessionMiddleware)

    def register_tenant_middlewares(self) -> None:
        """Register tenant isolation middleware components."""
        from .tenant import DatabaseIsolationMiddleware, TenantContextMiddleware

        if self.config.tenant_isolation_enabled:
            self.manager.register_middleware(
                MiddlewareType.TENANT_CONTEXT, TenantContextMiddleware
            )

        if self.config.database_isolation_enabled:
            self.manager.register_middleware(
                MiddlewareType.DATABASE_ISOLATION,
                DatabaseIsolationMiddleware,
                dependencies=[MiddlewareType.TENANT_CONTEXT],
            )

    def register_processing_middlewares(self) -> None:
        """Register request processing middleware components."""
        from .processing import (
            MetricsMiddleware,
            PerformanceMiddleware,
            RequestLoggingMiddleware,
            TracingMiddleware,
        )

        if self.config.logging_enabled:
            self.manager.register_middleware(
                MiddlewareType.REQUEST_LOGGING, RequestLoggingMiddleware
            )

        if self.config.metrics_enabled:
            self.manager.register_middleware(MiddlewareType.METRICS, MetricsMiddleware)

        if self.config.tracing_enabled:
            self.manager.register_middleware(MiddlewareType.TRACING, TracingMiddleware)

        if self.config.performance_monitoring_enabled:
            self.manager.register_middleware(
                MiddlewareType.PERFORMANCE, PerformanceMiddleware
            )

    def register_custom_middlewares(self) -> None:
        """Register custom middleware components."""
        for name, middleware_class in self.config.custom_middlewares.items():
            self.manager.register_middleware(MiddlewareType.PLUGIN, middleware_class)

    def apply(self, app: FastAPI) -> None:
        """Apply the middleware stack to a FastAPI application."""
        if self._applied:
            raise RuntimeError("Middleware stack already applied")

        self._app = app

        # Register all middleware components
        self.register_security_middlewares()
        self.register_auth_middlewares()
        self.register_tenant_middlewares()
        self.register_processing_middlewares()
        self.register_custom_middlewares()

        # Apply middlewares in proper order
        middlewares = self.manager.get_ordered_middlewares()

        for middleware in reversed(middlewares):  # Reverse for proper ASGI layering
            app.add_middleware(type(middleware))

        self._applied = True

        logger.info(
            "Middleware stack applied to FastAPI app",
            middleware_count=len(middlewares),
            environment=self.config.environment,
        )

    @asynccontextmanager
    async def lifespan_context(self):
        """Lifecycle context manager for middleware components."""
        # Initialize components that need startup
        for middleware in self.manager.get_ordered_middlewares():
            if hasattr(middleware, "startup"):
                await middleware.startup()

        try:
            yield
        finally:
            # Cleanup components that need shutdown
            for middleware in reversed(self.manager.get_ordered_middlewares()):
                if hasattr(middleware, "shutdown"):
                    await middleware.shutdown()


# Convenience functions for common configurations


def create_production_stack() -> MiddlewareStack:
    """Create a production-ready middleware stack."""
    config = MiddlewareConfig(
        environment="production",
        security_enabled=True,
        csrf_enabled=True,
        rate_limiting_enabled=True,
        tenant_isolation_enabled=True,
        metrics_enabled=True,
        tracing_enabled=True,
        debug=False,
    )
    return MiddlewareStack(config)


def create_development_stack() -> MiddlewareStack:
    """Create a development-friendly middleware stack."""
    config = MiddlewareConfig(
        environment="development",
        security_enabled=True,
        csrf_enabled=False,  # Easier for dev
        rate_limiting_enabled=False,  # Easier for dev
        tenant_isolation_enabled=True,
        metrics_enabled=True,
        tracing_enabled=False,
        debug=True,
    )
    return MiddlewareStack(config)


def create_minimal_stack() -> MiddlewareStack:
    """Create a minimal middleware stack for testing."""
    config = MiddlewareConfig(
        environment="test",
        security_enabled=False,
        auth_enabled=False,
        tenant_isolation_enabled=False,
        logging_enabled=True,
        metrics_enabled=False,
        debug=True,
    )
    return MiddlewareStack(config)
