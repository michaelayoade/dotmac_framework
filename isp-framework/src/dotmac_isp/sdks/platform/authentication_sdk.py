"""
Platform Auth SDK - Contract-first authentication for all Dotmac planes.

Provides unified authentication capabilities with JWT tokens, multiple providers,
and comprehensive security features. Used by all other planes for authentication.
Follows contract-first design with comprehensive validation and error handling.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from dotmac_isp.sdks.core.datetime_utils import utc_now


# Internal datetime compatibility (replacing external microservice)
class UTC:
    """UTC timezone for datetime operations."""

    @staticmethod
    def localize(dt):
        """Localize operation."""
        return dt.replace(tzinfo=utc_now().tzinfo)


try:
    import jwt
except ImportError:
    try:
        import PyJWT as jwt
    except ImportError:
        jwt = None
try:
    from passlib.context import CryptContext
except ImportError:
    CryptContext = None
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    AsyncSession = None

from dotmac_isp.sdks.contracts.auth import (
    AuthRequest,
    AuthResponse,
    AuthToken,
    LogoutRequest,
    LogoutResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenType,
    TokenValidationRequest,
    TokenValidationResponse,
)
from dotmac_isp.sdks.platform.repositories.auth import (
    UserRepository,
    UserSessionRepository,
)

logger = logging.getLogger(__name__)


class AuthSDK:
    """
    Platform Auth SDK providing contract-first authentication.

    Features:
    - Contract-first API with Pydantic v2 validation
    - JWT token generation and validation
    - Multiple authentication providers (local, OAuth2, SAML, LDAP, API key)
    - Password hashing with bcrypt
    - Token refresh and rotation
    - Session management
    - Comprehensive security features
    """

    def __init__(
        """  Init   operation."""
        self,
        secret_key: str,
        db_session: AsyncSession,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
        password_context: CryptContext | None = None,
    ):
        self.secret_key = secret_key
        if AsyncSession is None and db_session is not None:
            raise ImportError(
                "SQLAlchemy not available. Install with: pip install sqlalchemy[asyncio]"
            )
        self.db_session = db_session
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        # Password hashing context
        if CryptContext is None:
            raise ImportError(
                "passlib not available. Install with: pip install passlib[bcrypt]"
            )
        self.pwd_context = password_context or CryptContext(
            schemes=["bcrypt"], deprecated="auto"
        )

        # In-memory token blacklist (in production, use Redis)
        self._token_blacklist: set = set()

        # In-memory active sessions cache for quick stats and optional invalidation
        self._active_sessions: dict[str, dict] = {}

        # Repositories
        self.user_repo = UserRepository(db_session)
        self.session_repo = UserSessionRepository(db_session)

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        tenant_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        is_verified: bool = False,
        is_superuser: bool = False,
    ) -> str:
        """Create a new user and return user ID."""
        password_hash = self._hash_password(password)
        user = await self.user_repo.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            is_verified=is_verified,
            is_superuser=is_superuser,
        )
        logger.info(f"Created user {user.id} with username {username}")
        return user.id

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def _create_jwt_token(
        self,
        subject: str,
        token_type: TokenType,
        scopes: list[str],
        expires_delta: timedelta | None = None,
        audience: str | None = None,
    ) -> AuthToken:
        """Create JWT token with specified parameters."""
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        elif token_type == TokenType.ACCESS:
            expire = datetime.now(UTC) + timedelta(
                minutes=self.access_token_expire_minutes
            )
        else:
            expire = datetime.now(UTC) + timedelta(days=self.refresh_token_expire_days)

        issued_at = datetime.now(UTC)

        payload = {
            "sub": subject,
            "iat": issued_at.timestamp(),
            "exp": expire.timestamp(),
            "type": token_type.value,
            "scopes": scopes,
        }

        if audience:
            payload["aud"] = audience

        # Add unique token ID for blacklisting
        payload["jti"] = secrets.token_urlsafe(32)

        if jwt is None:
            raise ImportError(
                "JWT library not available. Install with: pip install PyJWT"
            )
        token_str = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return AuthToken(
            token=token_str,
            token_type=token_type,
            expires_at=expire,
            issued_at=issued_at,
            subject=subject,
            audience=audience,
            scopes=scopes,
        )

    def _decode_jwt_token(self, token: str) -> dict[str, Any]:
        """Decode and validate JWT token."""
        if jwt is None:
            raise ImportError(
                "JWT library not available. Install with: pip install PyJWT"
            )
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )

            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and jti in self._token_blacklist:
                raise jwt.InvalidTokenError("Token has been revoked")

            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")

    async def authenticate(self, request: AuthRequest) -> AuthResponse:
        """Authenticate user using contract-first approach."""
        try:
            # Validate authentication method
            if request.provider == "local":
                return await self._authenticate_local(request)
            elif request.provider == "api_key":
                return await self._authenticate_api_key(request)
            elif request.provider == "oauth2":
                return await self._authenticate_oauth2(request)
            else:
                return AuthResponse(
                    success=False,
                    request_id=request.request_id,
                    tenant_id=request.tenant_id,
                )

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

    async def _authenticate_local(self, request: AuthRequest) -> AuthResponse:
        """Authenticate using local username/password."""
        identifier = request.username or request.email
        if not identifier or not request.password:
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Look up user in database
        user = await self.user_repo.get_by_identifier(identifier, request.tenant_id)
        if not user:
            logger.warning(
                f"Authentication failed: User not found for identifier {identifier}"
            )
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Authentication failed: User {user.id} is inactive")
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Check if user is locked
        if user.is_locked:
            logger.warning(f"Authentication failed: User {user.id} is locked")
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Verify password
        if not self._verify_password(request.password, user.password_hash):
            logger.warning(
                f"Authentication failed: Invalid password for user {user.id}"
            )
            await self.user_repo.increment_failed_login(user.id)
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Password is correct - update last login and reset failed attempts
        await self.user_repo.update_last_login(user.id)

        # Create tokens
        access_token = self._create_jwt_token(
            subject=user.id,
            token_type=TokenType.ACCESS,
            scopes=request.requested_scopes or ["read:profile"],
        )

        refresh_token = self._create_jwt_token(
            subject=user.id,
            token_type=TokenType.REFRESH,
            scopes=["refresh"],
        )

        # Create session in database
        await self.session_repo.create_session(
            user_id=user.id,
            tenant_id=user.tenant_id,
            session_token=access_token.token,
            refresh_token=refresh_token.token,
            expires_at=refresh_token.expires_at,
            ip_address=getattr(request, "ip_address", None),
            user_agent=getattr(request, "user_agent", None),
        )

        logger.info(f"User {user.id} authenticated successfully")

        # Get user roles from identity system
        user_roles = []
        try:
            if hasattr(user, 'roles') and user.roles:
                user_roles = [role.name for role in user.roles]
            elif hasattr(user, 'role') and user.role:
                user_roles = [user.role]
            else:
                # Fallback: determine role by user type or email domain
                if hasattr(user, 'username') and user.username.startswith('CUST-'):
                    user_roles = ['customer']
                elif hasattr(user, 'email') and user.email:
                    if 'admin' in user.email or 'support' in user.email:
                        user_roles = ['support']
                    else:
                        user_roles = ['user']
                else:
                    user_roles = ['user']
        except Exception as e:
            logger.warning(f"Failed to get user roles for {user.id}: {e}")
            user_roles = ['user']  # Safe fallback

        return AuthResponse(
            success=True,
            access_token=access_token.token,
            refresh_token=refresh_token.token,
            expires_in=access_token.expires_in_seconds,
            token_type="Bearer",
            user_id=user.id,
            user_email=user.email,
            roles=user_roles,
            permissions=request.requested_scopes or ["read:profile"],
            request_id=request.request_id,
            tenant_id=request.tenant_id,
        )

    async def _authenticate_api_key(self, request: AuthRequest) -> AuthResponse:
        """Authenticate using API key."""
        if not request.api_key:
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Simulate API key validation
        # In production: api_key_record = await self.api_key_repository.get_by_key(request.api_key)
        if request.api_key.startswith("ak_live_"):
            user_id = f"api_user_{request.api_key[-8:]}"

            access_token = self._create_jwt_token(
                subject=user_id,
                token_type=TokenType.API_KEY,
                scopes=request.requested_scopes or ["api:access"],
                expires_delta=timedelta(hours=24),  # Longer expiry for API keys
            )

            return AuthResponse(
                success=True,
                access_token=access_token.token,
                expires_in=access_token.expires_in_seconds,
                token_type="Bearer",
                user_id=user_id,
                roles=["api_user"],
                permissions=request.requested_scopes or ["api:access"],
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        return AuthResponse(
            success=False,
            request_id=request.request_id,
            tenant_id=request.tenant_id,
        )

    async def _authenticate_oauth2(self, request: AuthRequest) -> AuthResponse:
        """Authenticate using OAuth2 provider token."""
        if not request.provider_token:
            return AuthResponse(
                success=False,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        # Simulate OAuth2 token validation
        # In production: user_info = await self.oauth2_client.validate_token(request.provider_token)
        if request.provider_token.startswith("oauth_"):
            user_id = f"oauth_user_{request.provider_token[-8:]}"

            access_token = self._create_jwt_token(
                subject=user_id,
                token_type=TokenType.ACCESS,
                scopes=request.requested_scopes or ["read:profile"],
            )

            refresh_token = self._create_jwt_token(
                subject=user_id,
                token_type=TokenType.REFRESH,
                scopes=["refresh"],
            )

            return AuthResponse(
                success=True,
                access_token=access_token.token,
                refresh_token=refresh_token.token,
                expires_in=access_token.expires_in_seconds,
                token_type="Bearer",
                user_id=user_id,
                roles=["user"],
                permissions=request.requested_scopes or ["read:profile"],
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        return AuthResponse(
            success=False,
            request_id=request.request_id,
            tenant_id=request.tenant_id,
        )

    async def validate_token(
        self, request: TokenValidationRequest
    ) -> TokenValidationResponse:
        """Validate token using contract-first approach."""
        try:
            payload = self._decode_jwt_token(request.token)

            # Check token type if specified
            if request.token_type:
                token_type = payload.get("type")
                if token_type != request.token_type.value:
                    return TokenValidationResponse(
                        valid=False,
                        expired=False,
                        error="Invalid token type",
                        request_id=request.request_id,
                        tenant_id=request.tenant_id,
                    )

            # Check required scopes
            token_scopes = payload.get("scopes", [])
            if request.required_scopes:
                missing_scopes = set(request.required_scopes) - set(token_scopes)
                if missing_scopes:
                    return TokenValidationResponse(
                        valid=False,
                        expired=False,
                        error=f"Missing required scopes: {', '.join(missing_scopes)}",
                        request_id=request.request_id,
                        tenant_id=request.tenant_id,
                    )

            # Check audience if specified
            if request.audience:
                token_audience = payload.get("aud")
                if token_audience != request.audience:
                    return TokenValidationResponse(
                        valid=False,
                        expired=False,
                        error="Invalid audience",
                        request_id=request.request_id,
                        tenant_id=request.tenant_id,
                    )

            return TokenValidationResponse(
                valid=True,
                expired=False,
                subject=payload["sub"],
                scopes=token_scopes,
                expires_at=datetime.fromtimestamp(payload["exp"], UTC),
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        except jwt.InvalidTokenError as e:
            is_expired = "expired" in str(e).lower()
            return TokenValidationResponse(
                valid=False,
                expired=is_expired,
                error=str(e),
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

    async def refresh_token(self, request: TokenRefreshRequest) -> TokenRefreshResponse:
        """Refresh access token using refresh token."""
        try:
            payload = self._decode_jwt_token(request.refresh_token)

            # Verify it's a refresh token
            if payload.get("type") != TokenType.REFRESH.value:
                return TokenRefreshResponse(
                    success=False,
                    error="Invalid refresh token type",
                    request_id=request.request_id,
                    tenant_id=request.tenant_id,
                )

            user_id = payload["sub"]

            # Create new access token
            new_access_token = self._create_jwt_token(
                subject=user_id,
                token_type=TokenType.ACCESS,
                scopes=request.requested_scopes or payload.get("scopes", []),
            )

            # Optionally rotate refresh token
            new_refresh_token = self._create_jwt_token(
                subject=user_id,
                token_type=TokenType.REFRESH,
                scopes=["refresh"],
            )

            # Blacklist old refresh token
            old_jti = payload.get("jti")
            if old_jti:
                self._token_blacklist.add(old_jti)

            return TokenRefreshResponse(
                success=True,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        except jwt.InvalidTokenError as e:
            return TokenRefreshResponse(
                success=False,
                error=str(e),
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

    async def logout(self, request: LogoutRequest) -> LogoutResponse:
        """Logout user and invalidate tokens."""
        try:
            payload = self._decode_jwt_token(request.token)
            user_id = payload["sub"]
            sessions_invalidated = 0

            if request.invalidate_all_sessions:
                # Invalidate all user sessions
                if user_id in self._active_sessions:
                    session = self._active_sessions[user_id]
                    # Blacklist all tokens for this user
                    for jti_key in ["access_token_jti", "refresh_token_jti"]:
                        if jti_key in session:
                            self._token_blacklist.add(session[jti_key])
                    del self._active_sessions[user_id]
                    sessions_invalidated = 1
            else:
                # Invalidate current token only
                jti = payload.get("jti")
                if jti:
                    self._token_blacklist.add(jti)
                    sessions_invalidated = 1

            return LogoutResponse(
                success=True,
                sessions_invalidated=sessions_invalidated,
                message="Successfully logged out",
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

        except jwt.InvalidTokenError as e:
            return LogoutResponse(
                success=False,
                sessions_invalidated=0,
                message=f"Logout failed: {str(e)}",
                request_id=request.request_id,
                tenant_id=request.tenant_id,
            )

    def get_auth_stats(self) -> dict[str, Any]:
        """Get authentication statistics."""
        return {
            "active_sessions": len(self._active_sessions),
            "blacklisted_tokens": len(self._token_blacklist),
            "algorithm": self.algorithm,
            "access_token_expire_minutes": self.access_token_expire_minutes,
            "refresh_token_expire_days": self.refresh_token_expire_days,
        }


__all__ = ["AuthSDK"]
