"""
JWT Authentication middleware for user management v2 system.
Provides secure JWT token validation and user context injection.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from dotmac.database.session import get_db_session
from dotmac.platform.observability.logging import get_logger
from dotmac_shared.auth.services import AuthService

from ..schemas.user_schemas import UserResponseSchema
from ..services.user_service import UserService

logger = get_logger(__name__)


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication middleware for user management v2.

    Validates JWT tokens and injects user context into request state.
    """

    def __init__(self, app, jwt_secret: str = "your-jwt-secret-key", jwt_algorithm: str = "HS256"):
        super().__init__(app)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.security = HTTPBearer(auto_error=False)

        # Paths that don't require authentication
        self.public_paths = {
            "/api/v2/auth/login",
            "/api/v2/auth/refresh",
            "/api/v2/auth/mfa/verify",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
        }

        # Paths that support optional authentication
        self.optional_auth_paths = {
            "/api/v1",  # Legacy API paths
        }

    async def dispatch(self, request: Request, call_next):
        """Process request through JWT authentication."""
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Check if authentication is optional for this path
        is_optional_auth = self._is_optional_auth_path(request.url.path)

        # Extract and validate JWT token
        try:
            user, session_id = await self._authenticate_request(request)

            if user:
                # Inject user context into request state
                request.state.current_user = user
                request.state.session_id = session_id
                request.state.tenant_id = user.tenant_id

                logger.debug(f"Authenticated user {user.id} for path {request.url.path}")

            elif not is_optional_auth:
                # Authentication required but not provided
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                )

        except HTTPException as e:
            if not is_optional_auth:
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
            else:
                # Continue without authentication for optional auth paths
                logger.debug(f"Optional auth failed for {request.url.path}: {e.detail}")

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no authentication required)."""
        return any(path.startswith(public_path) for public_path in self.public_paths)

    def _is_optional_auth_path(self, path: str) -> bool:
        """Check if path supports optional authentication."""
        return any(path.startswith(optional_path) for optional_path in self.optional_auth_paths)

    async def _authenticate_request(self, request: Request) -> tuple[Optional[UserResponseSchema], Optional[UUID]]:
        """
        Authenticate request and return user information.

        Returns:
            Tuple of (user, session_id) or (None, None) if not authenticated
        """
        # Extract authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None, None

        # Extract token
        token = auth_header.split(" ")[1]
        if not token:
            return None, None

        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            user_id = payload.get("user_id")
            session_id = payload.get("session_id")
            token_type = payload.get("type")  # noqa: S105 - token classification, not a secret

            if not user_id or not session_id or token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format",
                )

            user_id = UUID(user_id)
            session_id = UUID(session_id)

            # Get database session and validate user/session
            async with get_db_session() as db:
                # Determine tenant ID from token or request
                tenant_id = payload.get("tenant_id")
                if tenant_id:
                    tenant_id = UUID(tenant_id)

                # Validate session is still active
                auth_service = AuthService(db, tenant_id)
                session = await auth_service.session_repo.get_active_session(session_id)

                if not session or session.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired or invalid",
                    )

                # Get user information
                user_service = UserService(db, tenant_id)
                user = await user_service.get_user(user_id)

                if not user or user.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User account is not active",
                    )

                # Update session last activity
                await auth_service.session_repo.update_last_activity(session_id)

                return user, session_id

        except JWTError as e:
            logger.debug(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from e
        except ValueError as e:
            logger.debug(f"UUID parse error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format") from e
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error",
            ) from e


class APIKeyAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    API Key authentication middleware for programmatic access.

    Validates API keys for machine-to-machine communication.
    """

    def __init__(self, app):
        super().__init__(app)

        # Paths that support API key authentication
        self.api_key_paths = {
            "/api/v2/",  # All v2 API endpoints support API keys
        }

    async def dispatch(self, request: Request, call_next):
        """Process request through API key authentication."""
        # Check if this path supports API key auth
        if not self._supports_api_key_auth(request.url.path):
            return await call_next(request)

        # Skip if already authenticated via JWT
        if hasattr(request.state, "current_user") and request.state.current_user:
            return await call_next(request)

        # Extract and validate API key
        try:
            user = await self._authenticate_api_key(request)

            if user:
                # Inject user context into request state
                request.state.current_user = user
                request.state.session_id = None  # API keys don't have sessions
                request.state.tenant_id = user.tenant_id
                request.state.auth_method = "api_key"

                logger.debug(f"Authenticated API key for user {user.id}")

        except HTTPException:
            # API key authentication failed, but don't block request
            # Let JWT middleware or endpoint handle authentication
            pass

        return await call_next(request)

    def _supports_api_key_auth(self, path: str) -> bool:
        """Check if path supports API key authentication."""
        return any(path.startswith(api_path) for api_path in self.api_key_paths)

    async def _authenticate_api_key(self, request: Request) -> Optional[UserResponseSchema]:
        """
        Authenticate request using API key.

        Returns:
            User information if API key is valid, None otherwise
        """
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key or not api_key.startswith("dmac_"):
            return None

        try:
            # Get database session and validate API key
            async with get_db_session() as db:
                # API keys are global, so no tenant isolation for lookup
                auth_service = AuthService(db, None)

                # Validate API key
                api_key_record = await auth_service.api_key_repo.get_by_key_hash(api_key)

                if not api_key_record or not api_key_record.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid API key",
                    )

                # Check expiry
                if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="API key has expired",
                    )

                # Get user information
                user_service = UserService(db, api_key_record.tenant_id)
                user = await user_service.get_user(api_key_record.user_id)

                if not user or user.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Associated user account is not active",
                    )

                # Update API key last used
                await auth_service.api_key_repo.update_last_used(api_key_record.id)

                return user

        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return None


def add_jwt_authentication_middleware(app, jwt_secret: Optional[str] = None, jwt_algorithm: str = "HS256"):
    """
    Add JWT authentication middleware to FastAPI application.

    Args:
        app: FastAPI application instance
        jwt_secret: JWT secret key (defaults to config value)
        jwt_algorithm: JWT algorithm (defaults to HS256)
    """
    # Use secure configuration manager to get JWT secret from OpenBao or environment
    if jwt_secret is None:
        try:
            from dotmac_shared.config.secure_config import get_jwt_secret_sync

            jwt_secret = get_jwt_secret_sync()
        except Exception as e:
            # Fallback only for development/testing when OpenBao is not available
            import os

            jwt_secret = os.getenv("JWT_SECRET_KEY")
            if not jwt_secret:
                raise ValueError(
                    "JWT secret not available. Please set JWT_SECRET_KEY environment variable "
                    "or configure OpenBao with auth/jwt_secret_key"
                ) from e

    # Add API key middleware first (optional authentication)
    app.add_middleware(APIKeyAuthenticationMiddleware)

    # Add JWT middleware (primary authentication)
    app.add_middleware(JWTAuthenticationMiddleware, jwt_secret=jwt_secret, jwt_algorithm=jwt_algorithm)

    logger.info("Added JWT and API key authentication middleware")
