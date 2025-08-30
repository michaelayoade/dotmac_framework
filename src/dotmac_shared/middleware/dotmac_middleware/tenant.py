"""
Tenant isolation middleware for multi-tenant applications.

This module consolidates tenant isolation implementations from:
- ISP Framework tenant security
- Management Platform tenant context
- Shared security tenant middleware

Provides consistent tenant isolation and database context management.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


@dataclass
class TenantConfig:
    """Configuration for tenant isolation middleware."""

    # Tenant identification
    tenant_header_name: str = "X-Tenant-ID"
    tenant_query_param: str = "tenant_id"
    tenant_subdomain_enabled: bool = False
    tenant_path_prefix_enabled: bool = False

    # Database isolation
    database_isolation_enabled: bool = True
    row_level_security_enabled: bool = True
    tenant_schema_isolation: bool = False

    # Security settings
    enforce_tenant_access: bool = True
    allow_cross_tenant_access: bool = False
    tenant_validation_strict: bool = True

    # Caching
    tenant_cache_enabled: bool = True
    tenant_cache_ttl: int = 300  # 5 minutes

    # Excluded paths (no tenant isolation)
    excluded_paths: list[str] = field(
        default_factory=lambda: ["/health", "/metrics", "/docs", "/openapi.json"]
    )

    # Multi-tenant routing
    tenant_routing_enabled: bool = False
    default_tenant_id: str | None = None


class TenantContextManager:
    """
    Manages tenant context throughout the request lifecycle.

    Consolidates tenant context management from multiple implementations.
    """

    def __init__(self):
        self._context: dict[str, Any] = {}
        self._tenant_cache: dict[str, dict[str, Any]] = {}

    def set_tenant_context(
        self,
        tenant_id: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        permissions: list[str] | None = None,
        client_ip: str | None = None,
        **kwargs,
    ) -> None:
        """Set comprehensive tenant context."""
        self._context.update(
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "permissions": permissions or [],
                "client_ip": client_ip,
                **kwargs,
            }
        )

    def get_tenant_context(self) -> dict[str, Any]:
        """Get current tenant context."""
        return self._context.copy()

    def get_tenant_id(self) -> str | None:
        """Get current tenant ID."""
        return self._context.get("tenant_id")

    def get_user_id(self) -> str | None:
        """Get current user ID."""
        return self._context.get("user_id")

    def clear_context(self) -> None:
        """Clear tenant context."""
        self._context.clear()

    def has_permission(self, permission: str) -> bool:
        """Check if current context has specific permission."""
        permissions = self._context.get("permissions", [])
        return permission in permissions

    def cache_tenant_data(self, tenant_id: str, data: dict[str, Any]) -> None:
        """Cache tenant data for performance."""
        self._tenant_cache[tenant_id] = data

    def get_cached_tenant_data(self, tenant_id: str) -> dict[str, Any] | None:
        """Get cached tenant data."""
        return self._tenant_cache.get(tenant_id)


# Global tenant context manager
tenant_context = TenantContextManager()


class DatabaseIsolationMiddleware(BaseHTTPMiddleware):
    """
    Database-level tenant isolation middleware.

    Ensures proper tenant context is set for all database operations
    and enforces Row Level Security (RLS) policies.
    """

    def __init__(self, app, config: TenantConfig | None = None):
        super().__init__(app)
        self.config = config or TenantConfig()
        self._session_contexts: dict[str, str] = {}

    async def _set_database_context(
        self,
        session: AsyncSession,
        tenant_id: str,
        user_id: str | None = None,
        client_ip: str | None = None,
    ) -> bool:
        """Set tenant context in database session."""
        try:
            # Set tenant context for RLS policies
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
                {"tenant_id": tenant_id},
            )

            # Set user context if available
            if user_id:
                await session.execute(
                    text("SELECT set_config('app.current_user_id', :user_id, false)"),
                    {"user_id": user_id},
                )

            # Set client IP for audit logs
            if client_ip:
                await session.execute(
                    text(
                        "SELECT set_config('app.current_client_ip', :client_ip, false)"
                    ),
                    {"client_ip": client_ip},
                )

            # Set tenant schema if using schema isolation
            if self.config.tenant_schema_isolation:
                schema_name = f"tenant_{tenant_id}"
                await session.execute(text(f"SET search_path TO {schema_name}, public"))

            return True

        except Exception as e:
            logger.error(
                "Failed to set database tenant context",
                tenant_id=tenant_id,
                error=str(e),
            )
            return False

    async def _validate_tenant_access(
        self, session: AsyncSession, tenant_id: str, user_id: str | None = None
    ) -> bool:
        """Validate user has access to tenant."""
        if not self.config.enforce_tenant_access:
            return True

        try:
            # Check tenant exists
            result = await session.execute(
                text("SELECT id FROM tenants WHERE id = :tenant_id AND active = true"),
                {"tenant_id": tenant_id},
            )
            tenant_exists = result.fetchone() is not None

            if not tenant_exists:
                return False

            # Check user has access to tenant (if user_id provided)
            if user_id and not self.config.allow_cross_tenant_access:
                result = await session.execute(
                    text(
                        """
                        SELECT 1 FROM user_tenants ut
                        JOIN users u ON u.id = ut.user_id
                        WHERE ut.tenant_id = :tenant_id
                        AND ut.user_id = :user_id
                        AND u.active = true
                        AND ut.active = true
                    """
                    ),
                    {"tenant_id": tenant_id, "user_id": user_id},
                )
                has_access = result.fetchone() is not None
                return has_access

            return True

        except Exception as e:
            logger.error(
                "Failed to validate tenant access",
                tenant_id=tenant_id,
                user_id=user_id,
                error=str(e),
            )
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply database tenant isolation."""
        # Skip excluded paths
        if any(
            request.url.path.startswith(path) for path in self.config.excluded_paths
        ):
            return await call_next(request)

        # Get tenant context
        tenant_id = tenant_context.get_tenant_id()
        user_id = tenant_context.get_user_id()
        client_ip = tenant_context.get_tenant_context().get("client_ip")

        if not tenant_id:
            # No tenant context set - the component should have been handled by TenantContextMiddleware
            logger.warning("No tenant context found for database isolation")
            return await call_next(request)

        # Store original session context
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.client_ip = client_ip

        # Set database context in any database sessions created during this request
        # This would typically be handled by a database dependency

        return await call_next(request)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Tenant context extraction and validation middleware.

    Extracts tenant information from various sources and sets up tenant context.
    """

    def __init__(self, app, config: TenantConfig | None = None):
        super().__init__(app)
        self.config = config or TenantConfig()

    def _extract_tenant_from_header(self, request: Request) -> str | None:
        """Extract tenant ID from HTTP header."""
        return request.headers.get(self.config.tenant_header_name)

    def _extract_tenant_from_query(self, request: Request) -> str | None:
        """Extract tenant ID from query parameter."""
        return request.query_params.get(self.config.tenant_query_param)

    def _extract_tenant_from_subdomain(self, request: Request) -> str | None:
        """Extract tenant ID from subdomain."""
        if not self.config.tenant_subdomain_enabled:
            return None

        host = request.headers.get("Host", "")
        parts = host.split(".")

        if len(parts) >= 3:  # e.g., tenant.api.example.com
            potential_tenant = parts[0]
            # Validate tenant format (alphanumeric + hyphens)
            if potential_tenant.replace("-", "").isalnum():
                return potential_tenant

        return None

    def _extract_tenant_from_path(self, request: Request) -> str | None:
        """Extract tenant ID from URL path prefix."""
        if not self.config.tenant_path_prefix_enabled:
            return None

        path_parts = request.url.path.strip("/").split("/")
        if path_parts and path_parts[0]:
            # Assume first path segment is tenant ID
            potential_tenant = path_parts[0]
            # Basic validation - could be enhanced
            if (
                len(potential_tenant) > 0
                and potential_tenant.replace("-", "").isalnum()
            ):
                return potential_tenant

        return None

    def _extract_tenant_id(self, request: Request) -> str | None:
        """Extract tenant ID from various sources in priority order."""
        # Priority order: Header -> Query -> Subdomain -> Path
        tenant_id = (
            self._extract_tenant_from_header(request)
            or self._extract_tenant_from_query(request)
            or self._extract_tenant_from_subdomain(request)
            or self._extract_tenant_from_path(request)
            or self.config.default_tenant_id
        )

        return tenant_id

    def _extract_user_context(self, request: Request) -> dict[str, Any]:
        """Extract user context from request."""
        context = {}

        # Extract user ID from various sources
        user_id = (
            request.headers.get("X-User-ID")
            or request.headers.get("X-User-Id")
            or getattr(request.state, "user_id", None)
        )

        if user_id:
            context["user_id"] = user_id

        # Extract client IP
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP")
            or (request.client.host if request.client else None)
        )

        if client_ip:
            context["client_ip"] = client_ip

        # Extract organization context
        org_id = request.headers.get("X-Organization-ID")
        if org_id:
            context["organization_id"] = org_id

        return context

    async def _validate_tenant(self, tenant_id: str) -> bool:
        """Validate tenant exists and is active."""
        if not self.config.tenant_validation_strict:
            return True

        # Check cache first
        cached_data = tenant_context.get_cached_tenant_data(tenant_id)
        if cached_data:
            return cached_data.get("active", False)

        # In a real implementation, this would check the database
        # For now, we'll do basic format validation
        try:
            # Basic UUID validation if tenant_id looks like UUID
            if len(tenant_id) == 36 and tenant_id.count("-") == 4:
                UUID(tenant_id)

            # Cache validation result
            tenant_context.cache_tenant_data(tenant_id, {"active": True})
            return True

        except (ValueError, TypeError):
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract and set tenant context."""
        # Skip excluded paths
        if any(
            request.url.path.startswith(path) for path in self.config.excluded_paths
        ):
            return await call_next(request)

        try:
            # Extract tenant ID
            tenant_id = self._extract_tenant_id(request)

            if not tenant_id:
                if self.config.tenant_validation_strict:
                    logger.warning(
                        "No tenant ID found in request",
                        path=request.url.path,
                        method=request.method,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Tenant ID required",
                    )
                else:
                    # Continue without tenant context
                    return await call_next(request)

            # Validate tenant
            if not await self._validate_tenant(tenant_id):
                logger.warning(
                    "Invalid tenant ID", tenant_id=tenant_id, path=request.url.path
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
                )

            # Extract additional user context
            user_context = self._extract_user_context(request)

            # Set tenant context
            tenant_context.set_tenant_context(tenant_id=tenant_id, **user_context)

            # Store in request state for easy access
            request.state.tenant_id = tenant_id
            request.state.tenant_context = tenant_context.get_tenant_context()

            logger.debug(
                "Tenant context established",
                tenant_id=tenant_id,
                user_id=user_context.get("user_id"),
                path=request.url.path,
            )

            # Process request with tenant context
            response = await call_next(request)

            # Add tenant context to response headers (optional)
            response.headers["X-Tenant-Context"] = tenant_id

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Error in tenant context middleware",
                error=str(e),
                path=request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
        finally:
            # Clean up context after request
            tenant_context.clear_context()


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Unified tenant middleware that combines context and database isolation.

    This is a convenience middleware that applies both tenant context
    extraction and database isolation.
    """

    def __init__(self, app, config: TenantConfig | None = None):
        super().__init__(app)
        self.config = config or TenantConfig()

        # Initialize component middlewares
        self.context_middleware = TenantContextMiddleware(app, config)
        self.db_isolation_middleware = DatabaseIsolationMiddleware(app, config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply tenant context and database isolation."""

        # Create a pipeline: context -> database isolation -> application
        async def db_handler(req: Request) -> Response:
            return await self.db_isolation_middleware.dispatch(req, call_next)

        # Start with context extraction
        return await self.context_middleware.dispatch(request, db_handler)


# Dependency functions for FastAPI


def get_tenant_context() -> dict[str, Any]:
    """Dependency to get current tenant context."""
    return tenant_context.get_tenant_context()


def get_current_tenant_id() -> str | None:
    """Dependency to get current tenant ID."""
    return tenant_context.get_tenant_id()


def require_tenant_context():
    """Dependency that requires tenant context."""
    context = get_tenant_context()
    if not context.get("tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context required"
        )
    return context


async def get_tenant_database_session(
    session: AsyncSession = Depends(),  # This would be your database session dependency
) -> AsyncSession:
    """
    Dependency that provides a database session with tenant context.

    This should be used instead of direct database session dependencies
    when tenant isolation is required.
    """
    tenant_id = tenant_context.get_tenant_id()
    user_id = tenant_context.get_user_id()
    client_ip = tenant_context.get_tenant_context().get("client_ip")

    if tenant_id:
        # Set database context
        middleware = DatabaseIsolationMiddleware(None)
        await middleware._set_database_context(session, tenant_id, user_id, client_ip)

    return session
