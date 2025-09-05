"""
Tenant Isolation Middleware for Multi-Tenant Database Security
Ensures proper tenant context is set for all database operations

SECURITY: This middleware enforces tenant isolation at the application level
and integrates with Row Level Security policies
"""

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .row_level_security import RLSPolicyManager

logger = logging.getLogger(__name__)


class TenantContextManager:
    """
    Manages tenant context for database operations
    """

    def __init__(self):
        self.current_tenant_id: Optional[str] = None
        self.current_user_id: Optional[str] = None
        self.client_ip: Optional[str] = None

    async def set_context(
        self,
        session: Session,
        tenant_id: str,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> bool:
        """Set tenant context for database session"""
        try:
            # Set tenant context
            await session.execute(f"SELECT set_config('app.current_tenant_id', '{tenant_id}', false);")

            if user_id:
                await session.execute(f"SELECT set_config('app.current_user_id', '{user_id}', false);")

            if client_ip:
                await session.execute(f"SELECT set_config('app.client_ip', '{client_ip}', false);")

            self.current_tenant_id = tenant_id
            self.current_user_id = user_id
            self.client_ip = client_ip

            logger.debug(f"Tenant context set: {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set tenant context: {e}")
            return False

    async def clear_context(self, session: Session) -> bool:
        """Clear tenant context"""
        try:
            await session.execute("SELECT set_config('app.current_tenant_id', '', false);")
            await session.execute("SELECT set_config('app.current_user_id', '', false);")
            await session.execute("SELECT set_config('app.client_ip', '', false);")

            self.current_tenant_id = None
            self.current_user_id = None
            self.client_ip = None

            return True
        except Exception as e:
            logger.error(f"Failed to clear tenant context: {e}")
            return False


class TenantIsolationMiddleware:
    """
    FastAPI middleware for tenant isolation validation
    """

    def __init__(
        self,
        app,
        get_tenant_from_request: Callable[[Request], str],
        get_user_from_request: Optional[Callable[[Request], str]] = None,
        exempt_paths: Optional[list] = None,
        strict_mode: bool = True,
    ):
        self.app = app
        self.get_tenant_from_request = get_tenant_from_request
        self.get_user_from_request = get_user_from_request
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/api/auth",
        ]
        self.strict_mode = strict_mode
        self.context_manager = TenantContextManager()

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from tenant isolation"""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    async def extract_tenant_info(self, request: Request) -> dict[str, Optional[str]]:
        """Extract tenant and user information from request"""
        try:
            tenant_id = self.get_tenant_from_request(request)
            user_id = None

            if self.get_user_from_request:
                user_id = self.get_user_from_request(request)

            client_ip = request.client.host if request.client else None

            return {"tenant_id": tenant_id, "user_id": user_id, "client_ip": client_ip}
        except Exception as e:
            logger.error(f"Failed to extract tenant info: {e}")
            return {"tenant_id": None, "user_id": None, "client_ip": None}

    async def validate_tenant_access(self, tenant_id: str, request: Request) -> bool:
        """Validate that the tenant has access to the requested resource"""
        # Check tenant exists and is active
        # This would integrate with your tenant management system

        # For now, basic validation
        if not tenant_id or len(tenant_id) < 10:  # UUID minimum length check
            return False

        return True

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Skip exempt paths
            if self.is_exempt(request.url.path):
                await self.app(scope, receive, send)
                return

            # Extract tenant information
            tenant_info = await self.extract_tenant_info(request)
            tenant_id = tenant_info.get("tenant_id")

            # Validate tenant access
            if not tenant_id:
                if self.strict_mode:
                    error_response = JSONResponse(status_code=400, content={"detail": "Tenant context required"})
                    await error_response(scope, receive, send)
                    return

            if tenant_id and not await self.validate_tenant_access(tenant_id, request):
                error_response = JSONResponse(status_code=403, content={"detail": "Invalid tenant access"})
                await error_response(scope, receive, send)
                return

            # Add tenant info to request state
            request.state.tenant_id = tenant_id
            request.state.user_id = tenant_info.get("user_id")
            request.state.client_ip = tenant_info.get("client_ip")

            # Proceed with request
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class DatabaseTenantMiddleware:
    """
    Database session middleware that automatically sets tenant context
    """

    def __init__(self, rls_manager: RLSPolicyManager):
        self.rls_manager = rls_manager

    @asynccontextmanager
    async def tenant_session(
        self,
        session: Session,
        tenant_id: str,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ):
        """Context manager for tenant-aware database sessions"""
        try:
            # Set tenant context
            await self.rls_manager.set_tenant_context(session, tenant_id)

            if user_id:
                session.execute(f"SELECT set_config('app.current_user_id', '{user_id}', false);")

            if client_ip:
                session.execute(f"SELECT set_config('app.client_ip', '{client_ip}', false);")

            logger.debug(f"Database session configured for tenant: {tenant_id}")
            yield session

        except Exception as e:
            logger.error(f"Tenant session error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database tenant context failed",
            ) from e
        finally:
            # Always clear context
            try:
                await self.rls_manager.clear_tenant_context(session)
            except Exception:
                pass  # Don't fail on cleanup


# Dependency functions for FastAPI
def get_tenant_from_jwt(request: Request) -> Optional[str]:
    """Extract tenant ID from JWT token"""
    try:
        # This would extract tenant from your JWT token
        # For now, return from headers as fallback
        return request.headers.get("x-tenant-id")
    except Exception:
        return None


def get_tenant_from_subdomain(request: Request) -> Optional[str]:
    """Extract tenant ID from subdomain"""
    try:
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            # Validate subdomain format
            if len(subdomain) > 3 and subdomain.replace("-", "").replace("_", "").isalnum():
                return subdomain
    except Exception:
        pass
    return None


def get_tenant_from_header(request: Request) -> Optional[str]:
    """Extract tenant ID from header"""
    return request.headers.get("x-tenant-id")


def get_user_from_jwt(request: Request) -> Optional[str]:
    """Extract user ID from JWT token"""
    try:
        # This would extract user from your JWT token
        # For now, return from headers as fallback
        return request.headers.get("x-user-id")
    except Exception:
        return None


# Factory functions
def create_tenant_isolation_middleware(
    get_tenant_func: Callable[[Request], str],
    get_user_func: Optional[Callable[[Request], str]] = None,
    exempt_paths: Optional[list] = None,
    strict_mode: bool = True,
):
    """Factory for creating tenant isolation middleware"""

    def middleware_factory(app):
        return TenantIsolationMiddleware(
            app=app,
            get_tenant_from_request=get_tenant_func,
            get_user_from_request=get_user_func,
            exempt_paths=exempt_paths,
            strict_mode=strict_mode,
        )

    return middleware_factory


def create_database_tenant_middleware(rls_manager: RLSPolicyManager):
    """Factory for creating database tenant middleware"""
    return DatabaseTenantMiddleware(rls_manager)
