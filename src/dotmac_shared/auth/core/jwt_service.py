"""JWT token management service for DotMac Framework.

This module provides comprehensive JWT token management with RS256 signing,
token validation, and secure token lifecycle management.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel, Field, validator

from .permissions import Permission, Role, UserPermissions

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str = Field(..., description="Subject (user ID)")
    iss: str = Field(default="dotmac-auth", description="Issuer")
    aud: str = Field(default="dotmac-framework", description="Audience")
    iat: int = Field(..., description="Issued at")
    exp: int = Field(..., description="Expiration time")
    nbf: int = Field(..., description="Not before")
    jti: str = Field(..., description="JWT ID")

    # DotMac specific claims
    tenant_id: str = Field(..., description="Tenant ID")
    user_type: str = Field(default="user", description="User type")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    roles: List[str] = Field(default_factory=list, description="User roles")
    session_id: Optional[str] = Field(None, description="Session ID")
    portal_type: Optional[str] = Field(
        None, description="Portal type (admin, customer, technician)"
    )

    @validator("permissions", pre=True)
    def validate_permissions(cls, v):
        """Validate permission strings."""
        if isinstance(v, list):
            return [str(p) for p in v]
        return v

    @validator("roles", pre=True)
    def validate_roles(cls, v):
        """Validate role strings."""
        if isinstance(v, list):
            return [str(r) for r in v]
        return v


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token expiry in seconds")


class JWTConfig(BaseModel):
    """JWT configuration."""

    algorithm: str = Field(default="RS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=15, description="Access token expiry"
    )
    refresh_token_expire_days: int = Field(
        default=30, description="Refresh token expiry"
    )
    issuer: str = Field(default="dotmac-auth-service", description="Token issuer")
    audience: str = Field(default="dotmac-framework", description="Token audience")
    key_size: int = Field(default=2048, description="RSA key size")

    # Security settings
    require_exp: bool = Field(default=True, description="Require expiration claim")
    require_iat: bool = Field(default=True, description="Require issued at claim")
    require_nbf: bool = Field(default=True, description="Require not before claim")
    leeway: int = Field(default=0, description="Time leeway for validation")


class JWTService:
    """JWT token management service.

    Provides secure JWT token generation, validation, and management
    using RS256 algorithm with automatic key rotation support.
    """

    def __init__(
        self,
        config: Optional[JWTConfig] = None,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
    ):
        """Initialize JWT service.

        Args:
            config: JWT configuration
            private_key: RSA private key for signing (PEM format)
            public_key: RSA public key for validation (PEM format)
        """
        self.config = config or JWTConfig()

        # Initialize keys
        if private_key and public_key:
            self._private_key = private_key
            self._public_key = public_key
        else:
            self._private_key, self._public_key = self._generate_key_pair()

        # Token blacklist for revoked tokens
        self._blacklist: set = set()

        logger.info(
            f"JWT service initialized with {self.config.algorithm} algorithm, "
            f"{self.config.access_token_expire_minutes}min access token expiry"
        )

    def _generate_key_pair(self) -> tuple[str, str]:
        """Generate RSA key pair.

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=self.config.key_size
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        return private_pem, public_pem

    def generate_access_token(
        self,
        user_id: Union[str, UUID],
        tenant_id: Union[str, UUID],
        permissions: Optional[List[Union[Permission, str]]] = None,
        roles: Optional[List[Union[Role, str]]] = None,
        session_id: Optional[str] = None,
        portal_type: Optional[str] = None,
        user_type: str = "user",
        custom_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate access token.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            permissions: User permissions
            roles: User roles
            session_id: Session identifier
            portal_type: Portal type (admin, customer, technician)
            user_type: User type
            custom_claims: Additional custom claims

        Returns:
            Encoded JWT access token
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = TokenPayload(
            sub=str(user_id),
            iss=self.config.issuer,
            aud=self.config.audience,
            iat=int(now.timestamp()),
            exp=int(exp.timestamp()),
            nbf=int(now.timestamp()),
            jti=str(uuid4()),
            tenant_id=str(tenant_id),
            user_type=user_type,
            permissions=[str(p) for p in (permissions or [])],
            roles=[str(r) for r in (roles or [])],
            session_id=session_id,
            portal_type=portal_type,
        )

        # Add custom claims
        payload_dict = payload.dict()
        if custom_claims:
            payload_dict.update(custom_claims)

        return jwt.encode(
            payload_dict, self._private_key, algorithm=self.config.algorithm
        )

    def generate_refresh_token(
        self,
        user_id: Union[str, UUID],
        tenant_id: Union[str, UUID],
        session_id: Optional[str] = None,
    ) -> str:
        """Generate refresh token.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            session_id: Session identifier

        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "iss": self.config.issuer,
            "aud": f"{self.config.audience}-refresh",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": str(uuid4()),
            "tenant_id": str(tenant_id),
            "token_type": "refresh",
            "session_id": session_id,
        }

        return jwt.encode(payload, self._private_key, algorithm=self.config.algorithm)

    def generate_token_pair(
        self,
        user_id: Union[str, UUID],
        tenant_id: Union[str, UUID],
        permissions: Optional[List[Union[Permission, str]]] = None,
        roles: Optional[List[Union[Role, str]]] = None,
        session_id: Optional[str] = None,
        portal_type: Optional[str] = None,
        user_type: str = "user",
    ) -> TokenPair:
        """Generate access and refresh token pair.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            permissions: User permissions
            roles: User roles
            session_id: Session identifier
            portal_type: Portal type
            user_type: User type

        Returns:
            Token pair with access and refresh tokens
        """
        access_token = self.generate_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            permissions=permissions,
            roles=roles,
            session_id=session_id,
            portal_type=portal_type,
            user_type=user_type,
        )

        refresh_token = self.generate_refresh_token(
            user_id=user_id, tenant_id=tenant_id, session_id=session_id
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60,
            refresh_expires_in=self.config.refresh_token_expire_days * 24 * 60 * 60,
        )

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token.

        Args:
            token: JWT token to validate

        Returns:
            Decoded token payload

        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
        """
        # Check if token is blacklisted
        if token in self._blacklist:
            raise jwt.InvalidTokenError("Token has been revoked")

        payload = jwt.decode(
            token,
            self._public_key,
            algorithms=[self.config.algorithm],
            issuer=self.config.issuer,
            require=(
                ["exp", "iat", "nbf"]
                if all(
                    [
                        self.config.require_exp,
                        self.config.require_iat,
                        self.config.require_nbf,
                    ]
                )
                else None
            ),
            leeway=self.config.leeway,
            options={
                "require_exp": self.config.require_exp,
                "require_iat": self.config.require_iat,
                "require_nbf": self.config.require_nbf,
            },
        )

        return payload

    def refresh_access_token(
        self,
        refresh_token: str,
        permissions: Optional[List[Union[Permission, str]]] = None,
        roles: Optional[List[Union[Role, str]]] = None,
        portal_type: Optional[str] = None,
    ) -> str:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token
            permissions: Updated user permissions
            roles: Updated user roles
            portal_type: Portal type

        Returns:
            New access token
        """
        # Validate refresh token
        payload = self.validate_token(refresh_token)

        # Verify it's a refresh token
        if payload.get("token_type") != "refresh":
            raise jwt.InvalidTokenError("Invalid refresh token")

        # Generate new access token
        return self.generate_access_token(
            user_id=payload["sub"],
            tenant_id=payload["tenant_id"],
            permissions=permissions,
            roles=roles,
            session_id=payload.get("session_id"),
            portal_type=portal_type,
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke (blacklist) a token.

        Args:
            token: Token to revoke

        Returns:
            True if token was revoked successfully
        """
        # Validate token to ensure it's well-formed
        payload = jwt.decode(
            token,
            self._public_key,
            algorithms=[self.config.algorithm],
            options={"verify_exp": False},  # Don't check expiry for revocation
        )

        self._blacklist.add(token)
        logger.info(f"Token revoked for user {payload.get('sub')}")
        return True

    def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked.

        Args:
            token: Token to check

        Returns:
            True if token is revoked
        """
        return token in self._blacklist

    def get_token_claims(self, token: str) -> Dict[str, Any]:
        """Extract claims from token without validation.

        Args:
            token: JWT token

        Returns:
            Token claims
        """
        return jwt.decode(token, options={"verify_signature": False})

    def create_user_permissions(self, payload: Dict[str, Any]) -> UserPermissions:
        """Create UserPermissions object from token payload.

        Args:
            payload: Decoded token payload

        Returns:
            UserPermissions object
        """
        return UserPermissions(
            user_id=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            roles=[Role(r) for r in payload.get("roles", [])],
            explicit_permissions={
                Permission(p) for p in payload.get("permissions", [])
            },
        )

    def get_public_key(self) -> str:
        """Get public key for token validation.

        Returns:
            RSA public key in PEM format
        """
        return self._public_key

    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set (JWKS) for public key distribution.

        Returns:
            JWKS compatible dictionary
        """
        import base64

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        public_key_obj = load_pem_public_key(self._public_key.encode())
        public_numbers = public_key_obj.public_numbers()

        # Convert to base64url encoding
        def int_to_base64url_uint(val):
            """int_to_base64url_uint service method."""
            val_bytes = val.to_bytes((val.bit_length() + 7) // 8, "big")
            return base64.urlsafe_b64encode(val_bytes).rstrip(b"=").decode("ascii")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "alg": self.config.algorithm,
                    "use": "sig",
                    "kid": str(uuid4()),
                    "n": int_to_base64url_uint(public_numbers.n),
                    "e": int_to_base64url_uint(public_numbers.e),
                }
            ]
        }

    def cleanup_blacklist(self) -> int:
        """Clean up expired tokens from blacklist.

        Returns:
            Number of tokens removed
        """
        original_count = len(self._blacklist)
        current_blacklist = self._blacklist.copy()

        for token in current_blacklist:
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(
                timezone.utc
            ):
                self._blacklist.discard(token)

        removed_count = original_count - len(self._blacklist)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired tokens from blacklist")

        return removed_count
