"""
FastAPI middleware integration for authentication service.

Production implementation for platform integration authentication.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

import jwt
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    """FastAPI authentication middleware with JWT and session support."""

    def __init__(
        self,
        app: FastAPI,
        exclude_paths: Optional[list] = None,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        session_timeout: int = 3600,
    ):
        """Initialize middleware with FastAPI app."""
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
        ]
        self.jwt_secret = jwt_secret or "development-secret-change-in-production"
        self.jwt_algorithm = jwt_algorithm
        self.session_timeout = session_timeout

    def is_excluded_path(self, path: str) -> bool:
        """Check if path should bypass authentication."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)

    def extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers or cookies."""
        # Check Authorization header first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1]

        # Check cookies as fallback
        return request.cookies.get("access_token")

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload."""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            # Check expiration
            if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
                return None

            return payload

        except jwt.InvalidTokenError:
            return None

    async def create_auth_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create authentication context from token payload."""
        return {
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "permissions": payload.get("permissions", []),
            "roles": payload.get("roles", []),
            "session_id": payload.get("session_id"),
            "expires_at": payload.get("exp"),
        }

    async def handle_auth_failure(
        self, reason: str = "Authentication required"
    ) -> Response:
        """Handle authentication failure with appropriate response."""
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_failed",
                "message": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation with full authentication flow."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request to check path and extract token
        request = Request(scope, receive)

        # Skip authentication for excluded paths
        if self.is_excluded_path(request.url.path):
            await self.app(scope, receive, send)
            return

        try:
            # Extract authentication token
            token = self.extract_token(request)
            if not token:
                response = await self.handle_auth_failure(
                    "Missing authentication token"
                )
                await response(scope, receive, send)
                return

            # Validate token
            payload = self.validate_token(token)
            if not payload:
                response = await self.handle_auth_failure("Invalid or expired token")
                await response(scope, receive, send)
                return

            # Create auth context
            auth_context = await self.create_auth_context(payload)

            # Add authentication context to request state
            scope["auth_context"] = auth_context
            scope["user_id"] = auth_context["user_id"]
            scope["tenant_id"] = auth_context["tenant_id"]

            # Log successful authentication
            logger.debug(
                f"Authenticated request: {request.method} {request.url.path}",
                extra={
                    "user_id": auth_context["user_id"],
                    "tenant_id": auth_context["tenant_id"],
                    "path": request.url.path,
                },
            )

            # Continue with authenticated request
            await self.app(scope, receive, send)

        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            response = await self.handle_auth_failure("Authentication system error")
            await response(scope, receive, send)


def create_auth_middleware(
    app: FastAPI,
    jwt_secret: Optional[str] = None,
    exclude_paths: Optional[list] = None,
    **kwargs,
) -> AuthenticationMiddleware:
    """Factory function to create authentication middleware."""
    return AuthenticationMiddleware(
        app=app, jwt_secret=jwt_secret, exclude_paths=exclude_paths, **kwargs
    )
