"""
Authentication and authorization middleware components.

This module consolidates authentication implementations from:
- ISP Framework JWT and session handling
- Management Platform auth middleware
- Shared auth service integration

Provides consistent authentication and authorization across applications.
"""

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import jwt
import structlog
from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


@dataclass
class AuthConfig:
    """Configuration for authentication middleware."""

    # JWT Configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    jwt_issuer: str = "dotmac-framework"
    jwt_audience: str = "dotmac-api"

    # Session Configuration
    session_enabled: bool = False
    session_cookie_name: str = "dotmac_session"
    session_timeout_hours: int = 24
    session_secure: bool = True
    session_httponly: bool = True

    # Authentication behavior
    require_authentication: bool = True
    allow_anonymous_paths: list[str] = field(
        default_factory=lambda: [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
        ]
    )

    # Authorization
    enable_rbac: bool = True
    enable_tenant_isolation: bool = True

    # Token extraction
    bearer_token_enabled: bool = True
    query_token_enabled: bool = False  # Less secure, for special cases
    query_token_param: str = "token"

    # Security settings
    validate_token_issuer: bool = True
    validate_token_audience: bool = True
    require_https: bool = True  # In production

    # Cache settings
    token_cache_enabled: bool = True
    token_cache_ttl: int = 300  # 5 minutes


class JWTMiddleware(BaseHTTPMiddleware):
    """
    JWT token validation middleware.

    Handles JWT token extraction, validation, and user context setup.
    """

    def __init__(self, app, config: AuthConfig | None = None):
        super().__init__(app)
        self.config = config or AuthConfig()
        self.bearer_scheme = HTTPBearer(auto_error=False)
        self._token_cache: dict[str, dict[str, Any]] = {}

    def _extract_token_from_header(self, request: Request) -> str | None:
        """Extract JWT token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        return auth_header.split(" ", 1)[1]

    def _extract_token_from_query(self, request: Request) -> str | None:
        """Extract JWT token from query parameter."""
        if not self.config.query_token_enabled:
            return None

        return request.query_params.get(self.config.query_token_param)

    def _extract_token(self, request: Request) -> str | None:
        """Extract JWT token from request."""
        # Priority: Bearer token -> Query parameter
        return self._extract_token_from_header(
            request
        ) or self._extract_token_from_query(request)

    def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token and return payload."""
        try:
            # Check cache first
            if self.config.token_cache_enabled:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                cached_payload = self._token_cache.get(token_hash)
                if cached_payload and cached_payload.get("exp", 0) > time.time():
                    return cached_payload["payload"]

            # Validate token
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
                issuer=(
                    self.config.jwt_issuer
                    if self.config.validate_token_issuer
                    else None
                ),
                audience=(
                    self.config.jwt_audience
                    if self.config.validate_token_audience
                    else None
                ),
            )

            # Cache valid payload
            if self.config.token_cache_enabled:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                self._token_cache[token_hash] = {
                    "payload": payload,
                    "exp": payload.get(
                        "exp", time.time() + self.config.token_cache_ttl
                    ),
                }

            return payload

        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            ) from e
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            ) from e

    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed without authentication."""
        return any(
            path.startswith(allowed_path)
            for allowed_path in self.config.allow_anonymous_paths
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with JWT validation."""
        # Check if path requires authentication
        if self._is_path_allowed(request.url.path):
            return await call_next(request)

        # Extract token
        token = self._extract_token(request)

        if not token:
            if self.config.require_authentication:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                # Continue without authentication
                return await call_next(request)

        # Validate token and set user context
        try:
            payload = self._validate_token(token)

            # Set user context in request
            request.state.authenticated = True
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.user_roles = payload.get("roles", [])
            request.state.tenant_id = payload.get("tenant_id")
            request.state.permissions = payload.get("permissions", [])
            request.state.token_payload = payload

            logger.debug(
                "User authenticated via JWT",
                user_id=request.state.user_id,
                tenant_id=request.state.tenant_id,
                roles=request.state.user_roles,
            )

            return await call_next(request)

        except HTTPException:
            raise
        except Exception as e:
            logger.error("JWT validation error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            ) from e


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Session-based authentication middleware.

    Handles session cookies and validation.
    """

    def __init__(self, app, config: AuthConfig | None = None):
        super().__init__(app)
        self.config = config or AuthConfig()
        self._sessions: dict[str, dict[str, Any]] = {}

    def _extract_session_id(self, request: Request) -> str | None:
        """Extract session ID from cookies."""
        return request.cookies.get(self.config.session_cookie_name)

    def _validate_session(self, session_id: str) -> dict[str, Any] | None:
        """Validate session and return session data."""
        session_data = self._sessions.get(session_id)

        if not session_data:
            return None

        # Check expiration
        if session_data.get("expires", 0) < time.time():
            del self._sessions[session_id]
            return None

        return session_data

    def _create_session(self, user_data: dict[str, Any]) -> str:
        """Create a new session."""
        import uuid

        session_id = str(uuid.uuid4())

        session_data = {
            **user_data,
            "created": time.time(),
            "expires": time.time() + (self.config.session_timeout_hours * 3600),
            "last_accessed": time.time(),
        }

        self._sessions[session_id] = session_data
        return session_id

    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is allowed without authentication."""
        return any(
            path.startswith(allowed_path)
            for allowed_path in self.config.allow_anonymous_paths
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with session validation."""
        if not self.config.session_enabled:
            return await call_next(request)

        # Check if path requires authentication
        if self._is_path_allowed(request.url.path):
            return await call_next(request)

        # Extract session ID
        session_id = self._extract_session_id(request)

        if session_id:
            # Validate session
            session_data = self._validate_session(session_id)

            if session_data:
                # Update last accessed time
                session_data["last_accessed"] = time.time()

                # Set user context
                request.state.authenticated = True
                request.state.user_id = session_data.get("user_id")
                request.state.user_email = session_data.get("user_email")
                request.state.user_roles = session_data.get("user_roles", [])
                request.state.tenant_id = session_data.get("tenant_id")
                request.state.session_id = session_id
                request.state.session_data = session_data

                logger.debug(
                    "User authenticated via session",
                    user_id=request.state.user_id,
                    session_id=session_id,
                )

                return await call_next(request)

        # No valid session
        if self.config.require_authentication:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session authentication required",
            )

        return await call_next(request)


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Role-based access control (RBAC) middleware.

    Handles permission checking and tenant isolation.
    """

    def __init__(self, app, config: AuthConfig | None = None):
        super().__init__(app)
        self.config = config or AuthConfig()

        # Define role hierarchy
        self.role_hierarchy = {
            "super_admin": ["admin", "manager", "user"],
            "admin": ["manager", "user"],
            "manager": ["user"],
            "user": [],
        }

    def _has_role(self, user_roles: list[str], required_role: str) -> bool:
        """Check if user has required role (with hierarchy)."""
        if required_role in user_roles:
            return True

        # Check role hierarchy
        for role in user_roles:
            if required_role in self.role_hierarchy.get(role, []):
                return True

        return False

    def _has_permission(
        self, user_permissions: list[str], required_permission: str
    ) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions

    def _check_tenant_access(
        self, user_tenant_id: str | None, resource_tenant_id: str | None
    ) -> bool:
        """Check if user can access resource in specified tenant."""
        if not self.config.enable_tenant_isolation:
            return True

        if not user_tenant_id:
            return False

        if not resource_tenant_id:
            return True  # Global resource

        return user_tenant_id == resource_tenant_id

    def _extract_authorization_requirements(self, request: Request) -> dict[str, Any]:
        """Extract authorization requirements from request."""
        # This would typically be configured per endpoint
        # For now, we'll use some basic heuristics

        method = request.method
        path = request.url.path

        requirements = {}

        # Basic method-based permissions
        if method in ["POST", "PUT", "PATCH"]:
            requirements["permissions"] = ["write"]
        elif method == "DELETE":
            requirements["permissions"] = ["delete"]
        else:
            requirements["permissions"] = ["read"]

        # Path-based role requirements
        if "/admin" in path:
            requirements["roles"] = ["admin"]
        elif "/manager" in path:
            requirements["roles"] = ["manager"]

        # Extract tenant context from path or headers
        tenant_id = request.headers.get("X-Tenant-ID") or getattr(
            request.state, "tenant_id", None
        )

        if tenant_id:
            requirements["tenant_id"] = tenant_id

        return requirements

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authorization checks."""
        if not self.config.enable_rbac:
            return await call_next(request)

        # Skip if not authenticated
        if not getattr(request.state, "authenticated", False):
            return await call_next(request)

        # Extract user context
        user_roles = getattr(request.state, "user_roles", [])
        user_permissions = getattr(request.state, "permissions", [])
        user_tenant_id = getattr(request.state, "tenant_id", None)

        # Extract authorization requirements
        requirements = self._extract_authorization_requirements(request)

        # Check role requirements
        required_roles = requirements.get("roles", [])
        if required_roles:
            has_required_role = any(
                self._has_role(user_roles, role) for role in required_roles
            )
            if not has_required_role:
                logger.warning(
                    "Access denied - insufficient roles",
                    user_id=getattr(request.state, "user_id", None),
                    user_roles=user_roles,
                    required_roles=required_roles,
                    path=request.url.path,
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

        # Check permission requirements
        required_permissions = requirements.get("permissions", [])
        if required_permissions:
            has_required_permission = any(
                self._has_permission(user_permissions, perm)
                for perm in required_permissions
            )
            if not has_required_permission:
                logger.warning(
                    "Access denied - insufficient permissions",
                    user_id=getattr(request.state, "user_id", None),
                    user_permissions=user_permissions,
                    required_permissions=required_permissions,
                    path=request.url.path,
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

        # Check tenant access
        resource_tenant_id = requirements.get("tenant_id")
        if not self._check_tenant_access(user_tenant_id, resource_tenant_id):
            logger.warning(
                "Access denied - tenant isolation violation",
                user_id=getattr(request.state, "user_id", None),
                user_tenant_id=user_tenant_id,
                resource_tenant_id=resource_tenant_id,
                path=request.url.path,
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found",  # Don't reveal tenant isolation
            )

        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Unified authentication middleware.

    Combines JWT and session authentication with proper fallback.
    """

    def __init__(self, app, config: AuthConfig | None = None):
        super().__init__(app)
        self.config = config or AuthConfig()

        # Initialize component middlewares
        self.jwt_middleware = JWTMiddleware(app, config)
        self.session_middleware = SessionMiddleware(app, config)
        self.authz_middleware = AuthorizationMiddleware(app, config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply authentication and authorization pipeline."""

        # Create authentication pipeline
        async def authz_handler(req: Request) -> Response:
            return await self.authz_middleware.dispatch(req, call_next)

        async def session_handler(req: Request) -> Response:
            return await self.session_middleware.dispatch(req, authz_handler)

        # Start with JWT authentication (primary)
        try:
            return await self.jwt_middleware.dispatch(request, session_handler)
        except HTTPException as jwt_error:
            # If JWT fails and sessions are enabled, try session authentication
            if self.config.session_enabled:
                try:
                    return await self.session_middleware.dispatch(
                        request, authz_handler
                    )
                except HTTPException as session_error:
                    # If both fail, return the JWT error (primary auth method)
                    raise jwt_error from session_error
            else:
                raise jwt_error


# FastAPI Dependencies


def get_current_user(request: Request) -> dict[str, Any] | None:
    """Dependency to get current authenticated user."""
    if not getattr(request.state, "authenticated", False):
        return None

    return {
        "user_id": getattr(request.state, "user_id", None),
        "email": getattr(request.state, "user_email", None),
        "roles": getattr(request.state, "user_roles", []),
        "permissions": getattr(request.state, "permissions", []),
        "tenant_id": getattr(request.state, "tenant_id", None),
    }


def require_authentication(request: Request) -> dict[str, Any]:
    """Dependency that requires authentication."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return user


def require_role(required_role: str):
    """Dependency factory that requires specific role."""

    def role_dependency(request: Request) -> dict[str, Any]:
        user = require_authentication(request)
        user_roles = user.get("roles", [])

        # Check role hierarchy
        authz_middleware = AuthorizationMiddleware(None)
        if not authz_middleware._has_role(user_roles, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )

        return user

    return role_dependency


def require_permission(required_permission: str):
    """Dependency factory that requires specific permission."""

    def permission_dependency(request: Request) -> dict[str, Any]:
        user = require_authentication(request)
        user_permissions = user.get("permissions", [])

        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )

        return user

    return permission_dependency
