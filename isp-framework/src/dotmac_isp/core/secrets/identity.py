"""
Identity Provider and Token Management

Comprehensive identity management with JWT tokens, session management,
and multi-factor authentication support.
"""

try:
    import jwt
except ImportError:
    import PyJWT as jwt
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ..utils.datetime_compat import utcnow
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from enum import Enum
from typing import Any

import structlog
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = structlog.get_logger(__name__)


class TokenType(Enum):
    """Types of tokens issued"""

    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    ID_TOKEN = "id_token"
    API_KEY = "api_key"


@dataclass
class TokenClaims:
    """JWT token claims"""

    sub: str  # Subject (user ID)
    iss: str  # Issuer
    aud: str  # Audience
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: str  # JWT ID
    scope: str = ""  # Token scope
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    tenant_id: str | None = None
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JWT encoding"""
        return {
            "sub": self.sub,
            "iss": self.iss,
            "aud": self.aud,
            "exp": self.exp,
            "iat": self.iat,
            "jti": self.jti,
            "scope": self.scope,
            "roles": self.roles,
            "permissions": self.permissions,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenClaims":
        """Create from dictionary"""
        return cls(
            sub=data["sub"],
            iss=data["iss"],
            aud=data["aud"],
            exp=data["exp"],
            iat=data["iat"],
            jti=data["jti"],
            scope=data.get("scope", ""),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            tenant_id=data.get("tenant_id"),
            session_id=data.get("session_id"),
        )


class SessionStatus(Enum):
    """Session status"""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class Session:
    """User session information"""

    session_id: str
    user_id: str
    device_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    mfa_verified: bool = False
    device_trusted: bool = False
    location_verified: bool = False
    refresh_token_hash: str | None = None

    def is_expired(self) -> bool:
        """Check if session has expired"""
        return utcnow() > self.expires_at

    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == SessionStatus.ACTIVE and not self.is_expired()

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = utcnow()


class TokenValidator:
    """JWT token validation service"""

    def __init__(
        """  Init   operation."""
        self,
        public_key: bytes | None = None,
        issuer: str = "dotmac-platform",
        audience: str = "dotmac-services",
    ):
        self.issuer = issuer
        self.audience = audience
        self.public_key = public_key
        self.revoked_tokens: set = set()

    def validate_token(self, token: str) -> TokenClaims | None:
        """Validate JWT token"""
        try:
            # Check if token is revoked
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if token_hash in self.revoked_tokens:
                logger.warning("Revoked token used", token_hash=token_hash[:16])
                return None

            # Decode and validate JWT
            if self.public_key:
                # Verify with public key
                payload = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=["RS256"],
                    audience=self.audience,
                    issuer=self.issuer,
                )
            else:
                # Decode without verification (for development only)
                payload = jwt.decode(token, options={"verify_signature": False})

            # Create claims object
            claims = TokenClaims.from_dict(payload)

            # Additional validation
            if claims.exp < int(time.time()):
                logger.warning("Expired token used", sub=claims.sub)
                return None

            return claims

        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            return None
        except Exception as e:
            logger.error("Token validation error", error=str(e))
            return None

    def revoke_token(self, token: str) -> None:
        """Revoke a token"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.revoked_tokens.add(token_hash)
        logger.info("Token revoked", token_hash=token_hash[:16])


class SessionManager:
    """User session management"""

    def __init__(
        """  Init   operation."""
        self, session_timeout_minutes: int = 60, max_sessions_per_user: int = 5
    ):
        self.sessions: dict[str, Session] = {}
        self.user_sessions: dict[str, list[str]] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_sessions_per_user = max_sessions_per_user

    def create_session(
        self, user_id: str, device_id: str, ip_address: str, user_agent: str
    ) -> Session:
        """Create new user session"""
        session_id = self._generate_session_id()
        now = utcnow()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_activity=now,
            expires_at=now + self.session_timeout,
        )

        # Store session
        self.sessions[session_id] = session

        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)

        # Enforce session limit
        self._enforce_session_limit(user_id)

        logger.info(
            "Session created",
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
        )

        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session and session.is_active():
            session.update_activity()
            return session
        return None

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.REVOKED
            logger.info(
                "Session revoked", session_id=session_id, user_id=session.user_id
            )
            return True
        return False

    def revoke_user_sessions(
        self, user_id: str, except_session: str | None = None
    ) -> int:
        """Revoke all sessions for a user"""
        user_session_ids = self.user_sessions.get(user_id, [])
        revoked_count = 0

        for session_id in user_session_ids:
            if session_id != except_session:
                if self.revoke_session(session_id):
                    revoked_count += 1

        logger.info(
            "User sessions revoked", user_id=user_id, revoked_count=revoked_count
        )

        return revoked_count

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            session = self.sessions[session_id]
            session.status = SessionStatus.EXPIRED

            # Remove from user sessions
            user_sessions = self.user_sessions.get(session.user_id, [])
            if session_id in user_sessions:
                user_sessions.remove(session_id)

        logger.info("Expired sessions cleaned up", count=len(expired_sessions))
        return len(expired_sessions)

    def _generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(32)

    def _enforce_session_limit(self, user_id: str) -> None:
        """Enforce maximum sessions per user"""
        user_session_ids = self.user_sessions.get(user_id, [])

        if len(user_session_ids) > self.max_sessions_per_user:
            # Get sessions with activity timestamps
            sessions_with_activity = []
            for session_id in user_session_ids:
                session = self.sessions.get(session_id)
                if session and session.is_active():
                    sessions_with_activity.append((session_id, session.last_activity))

            # Sort by last activity (oldest first)
            sessions_with_activity.sort(key=lambda x: x[1])

            # Revoke oldest sessions
            excess_count = len(sessions_with_activity) - self.max_sessions_per_user
            for i in range(excess_count):
                session_id = sessions_with_activity[i][0]
                self.revoke_session(session_id)
                logger.info(
                    "Session revoked due to limit",
                    session_id=session_id,
                    user_id=user_id,
                )


class IdentityProvider:
    """Main identity provider service"""

    def __init__(
        """  Init   operation."""
        self,
        private_key: bytes | None = None,
        session_manager: SessionManager | None = None,
        token_validator: TokenValidator | None = None,
    ):

        # Generate RSA key pair if not provided
        if private_key:
            self.private_key = private_key
        else:
            self.private_key = self._generate_private_key()

        self.public_key = self._extract_public_key()

        # Initialize components
        self.session_manager = session_manager or SessionManager()
        self.token_validator = token_validator or TokenValidator(
            public_key=self.public_key
        )

        # Token settings
        self.access_token_lifetime = timedelta(minutes=15)
        self.refresh_token_lifetime = timedelta(days=30)
        self.issuer = "dotmac-platform"
        self.audience = "dotmac-services"

    def _generate_private_key(self) -> bytes:
        """Generate RSA private key"""
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def _extract_public_key(self) -> bytes:
        """Extract public key from private key"""
        private_key = serialization.load_pem_private_key(
            self.private_key, password=None, backend=default_backend()
        )

        public_key = private_key.public_key()

        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def authenticate(
        self,
        user_id: str,
        device_id: str,
        ip_address: str,
        user_agent: str,
        roles: list[str] = None,
        permissions: list[str] = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate user and issue tokens"""

        # Create session
        session = self.session_manager.create_session(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Generate tokens
        access_token = self._generate_access_token(
            user_id=user_id,
            session_id=session.session_id,
            roles=roles or [],
            permissions=permissions or [],
            tenant_id=tenant_id,
        )

        refresh_token = self._generate_refresh_token(
            user_id=user_id, session_id=session.session_id
        )

        # Store refresh token hash in session
        session.refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        logger.info(
            "User authenticated",
            user_id=user_id,
            session_id=session.session_id,
            device_id=device_id,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(self.access_token_lifetime.total_seconds()),
            "session_id": session.session_id,
        }

    def _generate_access_token(
        self,
        user_id: str,
        session_id: str,
        roles: list[str],
        permissions: list[str],
        tenant_id: str | None = None,
    ) -> str:
        """Generate JWT access token"""
        now = int(time.time())

        claims = TokenClaims(
            sub=user_id,
            iss=self.issuer,
            aud=self.audience,
            exp=now + int(self.access_token_lifetime.total_seconds()),
            iat=now,
            jti=secrets.token_urlsafe(16),
            scope="read write",
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            session_id=session_id,
        )

        # Load private key for signing
        private_key = serialization.load_pem_private_key(
            self.private_key, password=None, backend=default_backend()
        )

        # Generate JWT
        token = jwt.encode(claims.to_dict(), private_key, algorithm="RS256")

        return token

    def _generate_refresh_token(self, user_id: str, session_id: str) -> str:
        """Generate refresh token"""
        now = int(time.time())

        claims = TokenClaims(
            sub=user_id,
            iss=self.issuer,
            aud=self.audience,
            exp=now + int(self.refresh_token_lifetime.total_seconds()),
            iat=now,
            jti=secrets.token_urlsafe(16),
            scope="refresh",
            session_id=session_id,
        )

        # Load private key for signing
        private_key = serialization.load_pem_private_key(
            self.private_key, password=None, backend=default_backend()
        )

        # Generate JWT
        token = jwt.encode(claims.to_dict(), private_key, algorithm="RS256")

        return token

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any] | None:
        """Refresh access token using refresh token"""
        # Validate refresh token
        claims = self.token_validator.validate_token(refresh_token)
        if not claims or claims.scope != "refresh":
            logger.warning("Invalid refresh token used")
            return None

        # Get session
        session = self.session_manager.get_session(claims.session_id)
        if not session:
            logger.warning(
                "Session not found for refresh token", session_id=claims.session_id
            )
            return None

        # Verify refresh token hash
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        if session.refresh_token_hash != refresh_token_hash:
            logger.warning("Refresh token hash mismatch", session_id=claims.session_id)
            return None

        # Generate new access token (roles/permissions would be fetched from user store)
        access_token = self._generate_access_token(
            user_id=claims.sub,
            session_id=claims.session_id,
            roles=[],  # Would fetch from user store
            permissions=[],  # Would fetch from user store
            tenant_id=claims.tenant_id,
        )

        logger.info(
            "Access token refreshed", user_id=claims.sub, session_id=claims.session_id
        )

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int(self.access_token_lifetime.total_seconds()),
        }

    def logout(self, session_id: str) -> bool:
        """Logout user by revoking session"""
        session = self.session_manager.get_session(session_id)
        if session:
            self.session_manager.revoke_session(session_id)
            logger.info(
                "User logged out", user_id=session.user_id, session_id=session_id
            )
            return True
        return False

    def verify_token(self, token: str) -> TokenClaims | None:
        """Verify and decode token"""
        claims = self.token_validator.validate_token(token)
        if claims and claims.session_id:
            # Verify session is still active
            session = self.session_manager.get_session(claims.session_id)
            if not session:
                logger.warning(
                    "Token has invalid session", session_id=claims.session_id
                )
                return None

        return claims

    def revoke_token(self, token: str) -> None:
        """Revoke a specific token"""
        self.token_validator.revoke_token(token)

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get session information"""
        session = self.session_manager.get_session(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "device_id": session.device_id,
                "ip_address": session.ip_address,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "status": session.status.value,
                "mfa_verified": session.mfa_verified,
                "device_trusted": session.device_trusted,
                "location_verified": session.location_verified,
            }
        return None
