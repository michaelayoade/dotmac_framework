"""
JWT Token Management with RS256 Security

Implements secure JWT token generation, validation, and management following
2024 security best practices including:
- RS256 algorithm with proper key management
- Automatic key rotation support
- Token blacklisting for secure logout
- Refresh token mechanism with rotation
- Comprehensive token validation
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Token is invalid."""

    pass


class TokenRevokedError(TokenError):
    """Token has been revoked."""

    pass


@dataclass
class TokenPair:
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "Bearer"


@dataclass
class RSAKeyPair:
    """RSA key pair for JWT signing."""

    private_key: bytes
    public_key: bytes
    key_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class JWTTokenManager:
    """
    Secure JWT token manager using RS256 algorithm.

    Features:
    - RS256 signing with 2048-bit RSA keys
    - Automatic key rotation support
    - Token blacklisting for revocation
    - Refresh token rotation
    - JWKS endpoint support
    - Comprehensive security validation
    """

    def __init__(
        self,
        private_key: Optional[Union[str, bytes]] = None,
        public_key: Optional[Union[str, bytes]] = None,
        key_id: Optional[str] = None,
        issuer: str = "dotmac-auth-service",
        audience: Optional[str] = None,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
        key_rotation_days: int = 90,
        blacklist_provider: Optional[Any] = None,
    ):
        """
        Initialize JWT token manager.

        Args:
            private_key: RSA private key for signing (PEM format)
            public_key: RSA public key for verification (PEM format)
            key_id: Key identifier for JWKS
            issuer: Token issuer identifier
            audience: Token audience identifier
            access_token_expire_minutes: Access token expiry in minutes
            refresh_token_expire_days: Refresh token expiry in days
            key_rotation_days: Key rotation period in days
            blacklist_provider: Provider for token blacklisting (Redis, etc.)
        """
        self.issuer = issuer
        self.audience = audience
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.key_rotation_days = key_rotation_days
        self.blacklist_provider = blacklist_provider

        # Algorithm configuration (following 2024 best practices)
        self.algorithm = "RS256"  # RS256 recommended over HS256
        self.key_size = 2048  # 2048-bit RSA keys (current standard)

        # Load or generate keys
        if private_key and public_key:
            self._load_keys(private_key, public_key, key_id)
        else:
            self._generate_keys()

        # Token tracking
        self._revoked_tokens: set = set()

        logger.info(f"JWT Token Manager initialized with issuer: {self.issuer}")

    def _load_keys(
        self,
        private_key: Union[str, bytes],
        public_key: Union[str, bytes],
        key_id: Optional[str],
    ):
        """Load RSA keys from provided data."""
        try:
            # Convert string paths to bytes if needed
            if isinstance(private_key, str):
                if private_key.startswith("-----BEGIN"):
                    private_key_bytes = private_key.encode("utf-8")
                else:
                    # Assume it's a file path
                    with open(private_key, "rb") as f:
                        private_key_bytes = f.read()
            else:
                private_key_bytes = private_key

            if isinstance(public_key, str):
                if public_key.startswith("-----BEGIN"):
                    public_key_bytes = public_key.encode("utf-8")
                else:
                    # Assume it's a file path
                    with open(public_key, "rb") as f:
                        public_key_bytes = f.read()
            else:
                public_key_bytes = public_key

            # Load and validate keys
            self._private_key = serialization.load_pem_private_key(
                private_key_bytes, password=None, backend=default_backend()
            )

            self._public_key = serialization.load_pem_public_key(
                public_key_bytes, backend=default_backend()
            )

            # Validate key size
            key_size = self._private_key.key_size
            if key_size < 2048:
                logger.warning(
                    f"RSA key size {key_size} is below recommended 2048 bits"
                )

            self.key_id = key_id or self._generate_key_id()
            self.key_created_at = datetime.now(timezone.utc)

            logger.info(
                f"Loaded RSA keys (size: {key_size} bits, key_id: {self.key_id})"
            )

        except Exception as e:
            logger.error(f"Failed to load RSA keys: {e}")
            raise TokenError(f"Invalid RSA keys: {e}")

    def _generate_keys(self):
        """Generate new RSA key pair."""
        try:
            # Generate 2048-bit RSA key pair (current security standard)
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=self.key_size, backend=default_backend()
            )

            public_key = private_key.public_key()

            self._private_key = private_key
            self._public_key = public_key
            self.key_id = self._generate_key_id()
            self.key_created_at = datetime.now(timezone.utc)

            logger.info(f"Generated new RSA key pair (key_id: {self.key_id})")

        except Exception as e:
            logger.error(f"Failed to generate RSA keys: {e}")
            raise TokenError(f"Key generation failed: {e}")

    def _generate_key_id(self) -> str:
        """Generate unique key identifier."""
        import hashlib
        import uuid

        # Create key ID from timestamp and random component
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        random_component = str(uuid.uuid4())[:8]

        key_string = f"{timestamp}-{random_component}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def generate_access_token(
        self,
        user_id: str,
        tenant_id: str,
        permissions: List[str],
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_in: Optional[timedelta] = None,
    ) -> str:
        """
        Generate JWT access token with user claims.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            permissions: List of user permissions
            additional_claims: Additional JWT claims
            expires_in: Custom expiration time

        Returns:
            Signed JWT access token
        """
        now = datetime.now(timezone.utc)
        expires_delta = expires_in or timedelta(
            minutes=self.access_token_expire_minutes
        )
        expires_at = now + expires_delta

        # Build JWT claims following security best practices
        claims = {
            # Standard claims
            "iss": self.issuer,  # Issuer
            "sub": user_id,  # Subject (user ID)
            "aud": self.audience,  # Audience
            "exp": int(expires_at.timestamp()),  # Expiration time
            "iat": int(now.timestamp()),  # Issued at
            "nbf": int(now.timestamp()),  # Not before
            "jti": self._generate_jti(),  # JWT ID (unique)
            # Custom claims
            "type": TokenType.ACCESS.value,
            "tenant_id": tenant_id,
            "permissions": permissions,
            "key_id": self.key_id,
        }

        # Add additional claims if provided
        if additional_claims:
            claims.update(additional_claims)

        try:
            # Sign token with RS256
            token = jwt.encode(
                claims,
                self._private_key,
                algorithm=self.algorithm,
                headers={"kid": self.key_id},
            )

            logger.debug(
                f"Generated access token for user {user_id} (tenant: {tenant_id})"
            )
            return token

        except Exception as e:
            logger.error(f"Failed to generate access token: {e}")
            raise TokenError(f"Token generation failed: {e}")

    def generate_refresh_token(
        self, user_id: str, tenant_id: str, expires_in: Optional[timedelta] = None
    ) -> str:
        """
        Generate JWT refresh token.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            expires_in: Custom expiration time

        Returns:
            Signed JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expires_delta = expires_in or timedelta(days=self.refresh_token_expire_days)
        expires_at = now + expires_delta

        claims = {
            "iss": self.issuer,
            "sub": user_id,
            "aud": self.audience,
            "exp": int(expires_at.timestamp()),
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": self._generate_jti(),
            "type": TokenType.REFRESH.value,
            "tenant_id": tenant_id,
            "key_id": self.key_id,
        }

        try:
            token = jwt.encode(
                claims,
                self._private_key,
                algorithm=self.algorithm,
                headers={"kid": self.key_id},
            )

            logger.debug(f"Generated refresh token for user {user_id}")
            return token

        except Exception as e:
            logger.error(f"Failed to generate refresh token: {e}")
            raise TokenError(f"Refresh token generation failed: {e}")

    def generate_token_pair(
        self,
        user_id: str,
        tenant_id: str,
        permissions: List[str],
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> TokenPair:
        """
        Generate access and refresh token pair.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            permissions: List of user permissions
            additional_claims: Additional claims for access token

        Returns:
            TokenPair with access and refresh tokens
        """
        access_token = self.generate_access_token(
            user_id, tenant_id, permissions, additional_claims
        )
        refresh_token = self.generate_refresh_token(user_id, tenant_id)

        now = datetime.now(timezone.utc)
        access_expires_at = now + timedelta(minutes=self.access_token_expire_minutes)
        refresh_expires_at = now + timedelta(days=self.refresh_token_expire_days)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
        )

    def validate_token(
        self, token: str, expected_type: Optional[TokenType] = None
    ) -> Dict[str, Any]:
        """
        Validate JWT token and return claims.

        Args:
            token: JWT token to validate
            expected_type: Expected token type (access/refresh)

        Returns:
            Token claims dictionary

        Raises:
            TokenExpiredError: Token has expired
            TokenInvalidError: Token is invalid
            TokenRevokedError: Token has been revoked
        """
        try:
            # Check if token is blacklisted
            if self._is_token_revoked(token):
                raise TokenRevokedError("Token has been revoked")

            # Decode and validate token
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "jti"]},
            )

            # Validate token type if specified
            if expected_type:
                token_type = payload.get("type")
                if token_type != expected_type.value:
                    raise TokenInvalidError(
                        f"Expected {expected_type.value} token, got {token_type}"
                    )

            # Additional security validations
            self._validate_token_claims(payload)

            logger.debug(f"Successfully validated token (jti: {payload.get('jti')})")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: expired")
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise TokenInvalidError(f"Invalid token: {e}")
        except (TokenRevokedError, TokenInvalidError):
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise TokenInvalidError(f"Token validation failed: {e}")

    def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """
        Generate new access token from refresh token.
        Implements refresh token rotation for enhanced security.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New TokenPair with rotated refresh token
        """
        # Validate refresh token
        claims = self.validate_token(refresh_token, TokenType.REFRESH)

        user_id = claims["sub"]
        tenant_id = claims["tenant_id"]

        # Revoke old refresh token (rotation)
        self.revoke_token(refresh_token)

        # Generate new token pair
        # Note: Permissions need to be fetched from user service/database
        # This is a placeholder - actual implementation should fetch current permissions
        permissions = claims.get("permissions", [])

        new_tokens = self.generate_token_pair(user_id, tenant_id, permissions)

        logger.info(f"Refreshed tokens for user {user_id} (old refresh token revoked)")
        return new_tokens

    def revoke_token(self, token: str):
        """
        Revoke a token by adding it to blacklist.

        Args:
            token: Token to revoke
        """
        try:
            # Extract JWT ID for blacklisting
            unverified_claims = jwt.decode(token, options={"verify_signature": False})
            jti = unverified_claims.get("jti")
            exp = unverified_claims.get("exp")

            if jti and exp:
                # Add to blacklist with expiration
                if self.blacklist_provider:
                    expiry_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                    ttl = max(
                        0,
                        int((expiry_time - datetime.now(timezone.utc)).total_seconds()),
                    )
                    self.blacklist_provider.add_to_blacklist(jti, ttl)
                else:
                    # Fallback to in-memory storage (not recommended for production)
                    self._revoked_tokens.add(jti)

                logger.info(f"Revoked token (jti: {jti})")
            else:
                logger.warning("Cannot revoke token: missing jti or exp claims")

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            raise TokenError(f"Token revocation failed: {e}")

    def _is_token_revoked(self, token: str) -> bool:
        """Check if token is in blacklist."""
        try:
            unverified_claims = jwt.decode(token, options={"verify_signature": False})
            jti = unverified_claims.get("jti")

            if not jti:
                return False

            if self.blacklist_provider:
                return self.blacklist_provider.is_blacklisted(jti)
            else:
                return jti in self._revoked_tokens

        except Exception:
            return False

    def _validate_token_claims(self, claims: Dict[str, Any]):
        """Perform additional claim validations."""
        # Validate required custom claims
        required_claims = ["type", "tenant_id", "key_id"]
        for claim in required_claims:
            if claim not in claims:
                raise TokenInvalidError(f"Missing required claim: {claim}")

        # Validate key ID matches current key
        if claims.get("key_id") != self.key_id:
            logger.warning(
                f"Token signed with different key: {claims.get('key_id')} != {self.key_id}"
            )
            # Note: In production, the component should check against all valid keys (for rotation)

    def _generate_jti(self) -> str:
        """Generate unique JWT ID."""
        import uuid

        return str(uuid.uuid4())

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get JSON Web Key Set (JWKS) for public key distribution.
        Used by clients to verify JWT signatures.

        Returns:
            JWKS dictionary
        """
        try:
            # Extract public key components
            public_key_pem = self._public_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            # Create JWKS format
            jwks = {
                "keys": [
                    {
                        "kty": "RSA",
                        "kid": self.key_id,
                        "use": "sig",
                        "alg": self.algorithm,
                        "x5c": [public_key_pem.decode("utf-8")],
                    }
                ]
            }

            return jwks

        except Exception as e:
            logger.error(f"Failed to generate JWKS: {e}")
            raise TokenError(f"JWKS generation failed: {e}")

    def needs_key_rotation(self) -> bool:
        """Check if keys need rotation based on age."""
        if not hasattr(self, "key_created_at"):
            return True

        age = datetime.now(timezone.utc) - self.key_created_at
        return age.days >= self.key_rotation_days

    def export_keys(self) -> Dict[str, str]:
        """
        Export keys for backup or rotation.

        Returns:
            Dictionary with PEM-encoded keys
        """
        try:
            private_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            public_pem = self._public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            return {
                "private_key": private_pem.decode("utf-8"),
                "public_key": public_pem.decode("utf-8"),
                "key_id": self.key_id,
                "created_at": self.key_created_at.isoformat(),
                "algorithm": self.algorithm,
            }

        except Exception as e:
            logger.error(f"Failed to export keys: {e}")
            raise TokenError(f"Key export failed: {e}")
