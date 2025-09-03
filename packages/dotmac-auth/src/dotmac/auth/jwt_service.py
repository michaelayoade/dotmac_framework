"""
JWT Service

Comprehensive JWT token management with RS256/HS256 support, access/refresh tokens,
and integration with secrets providers.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .exceptions import (
    ConfigurationError,
    InvalidAlgorithm,
    InvalidAudience,
    InvalidIssuer,
    InvalidSignature,
    InvalidToken,
    TokenExpired,
)


class JWTService:
    """
    JWT token management service supporting RS256 and HS256 algorithms.
    
    Features:
    - Access and refresh token generation
    - Token verification with configurable validation
    - Support for both asymmetric (RS256) and symmetric (HS256) algorithms
    - Integration with secrets providers
    - Comprehensive claims management
    """
    
    SUPPORTED_ALGORITHMS = {"RS256", "HS256"}
    
    def __init__(
        self,
        algorithm: str = "RS256",
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
        secret: Optional[str] = None,
        issuer: Optional[str] = None,
        default_audience: Optional[str] = None,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        leeway: int = 0,
        secrets_provider=None
    ):
        """
        Initialize JWT service.
        
        Args:
            algorithm: JWT algorithm ("RS256" or "HS256")
            private_key: Private key for RS256 (PEM format)
            public_key: Public key for RS256 (PEM format)
            secret: Shared secret for HS256
            issuer: Default token issuer
            default_audience: Default token audience
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
            leeway: Clock skew tolerance in seconds
            secrets_provider: Optional secrets provider instance
        """
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise InvalidAlgorithm(f"Unsupported algorithm: {algorithm}")
        
        self.algorithm = algorithm
        self.issuer = issuer
        self.default_audience = default_audience
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.leeway = leeway
        self.secrets_provider = secrets_provider
        
        # Initialize keys/secrets
        if algorithm == "RS256":
            self._init_rsa_keys(private_key, public_key)
        else:  # HS256
            self._init_symmetric_secret(secret)
    
    def _init_rsa_keys(self, private_key: Optional[str], public_key: Optional[str]):
        """Initialize RSA keys for RS256"""
        # Try to get keys from secrets provider first
        if self.secrets_provider:
            try:
                if not private_key:
                    private_key = self.secrets_provider.get_jwt_private_key()
                if not public_key:
                    public_key = self.secrets_provider.get_jwt_public_key()
            except Exception:
                pass  # Fall back to provided keys
        
        if not private_key and not public_key:
            raise ConfigurationError(
                "RS256 requires either private_key (for signing) or public_key (for verification)"
            )
        
        # Load private key
        if private_key:
            try:
                self.private_key = serialization.load_pem_private_key(
                    private_key.encode() if isinstance(private_key, str) else private_key,
                    password=None
                )
            except Exception as e:
                raise ConfigurationError(f"Invalid private key: {e}")
        else:
            self.private_key = None
        
        # Load public key
        if public_key:
            try:
                self.public_key = serialization.load_pem_public_key(
                    public_key.encode() if isinstance(public_key, str) else public_key
                )
            except Exception as e:
                raise ConfigurationError(f"Invalid public key: {e}")
        else:
            # Extract public key from private key if available
            if self.private_key:
                self.public_key = self.private_key.public_key()
            else:
                self.public_key = None
    
    def _init_symmetric_secret(self, secret: Optional[str]):
        """Initialize symmetric secret for HS256"""
        # Try to get secret from secrets provider first
        if self.secrets_provider and not secret:
            try:
                secret = self.secrets_provider.get_symmetric_secret()
            except Exception:
                pass  # Fall back to provided secret
        
        if not secret:
            raise ConfigurationError("HS256 requires a symmetric secret")
        
        self.secret = secret
    
    def _get_signing_key(self) -> Union[str, rsa.RSAPrivateKey]:
        """Get the appropriate signing key for the algorithm"""
        if self.algorithm == "RS256":
            if not self.private_key:
                raise ConfigurationError("Private key required for token signing")
            return self.private_key
        else:  # HS256
            return self.secret
    
    def _get_verification_key(self) -> Union[str, rsa.RSAPublicKey]:
        """Get the appropriate verification key for the algorithm"""
        if self.algorithm == "RS256":
            if not self.public_key:
                raise ConfigurationError("Public key required for token verification")
            return self.public_key
        else:  # HS256
            return self.secret
    
    def issue_access_token(
        self,
        sub: str,
        scopes: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        expires_in: Optional[int] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
        audience: Optional[str] = None,
        issuer: Optional[str] = None
    ) -> str:
        """
        Issue an access token.
        
        Args:
            sub: Subject (user ID)
            scopes: List of permission scopes
            tenant_id: Tenant identifier
            expires_in: Custom expiration in minutes
            extra_claims: Additional claims to include
            audience: Token audience
            issuer: Token issuer
            
        Returns:
            Encoded JWT access token
        """
        now = datetime.now(timezone.utc)
        expires_in = expires_in or self.access_token_expire_minutes
        exp = now + timedelta(minutes=expires_in)
        
        claims = {
            "sub": sub,
            "iat": now,
            "exp": exp,
            "jti": str(uuid.uuid4()),
            "type": "access",
            "iss": issuer or self.issuer,
            "aud": audience or self.default_audience,
        }
        
        # Add optional claims
        if scopes:
            claims["scope"] = " ".join(scopes)
            claims["scopes"] = scopes
        
        if tenant_id:
            claims["tenant_id"] = tenant_id
        
        if extra_claims:
            claims.update(extra_claims)
        
        # Remove None values
        claims = {k: v for k, v in claims.items() if v is not None}
        
        try:
            return jwt.encode(
                claims,
                self._get_signing_key(),
                algorithm=self.algorithm
            )
        except Exception as e:
            raise InvalidToken(f"Failed to encode token: {e}")
    
    def issue_refresh_token(
        self,
        sub: str,
        tenant_id: Optional[str] = None,
        expires_in: Optional[int] = None,
        audience: Optional[str] = None,
        issuer: Optional[str] = None
    ) -> str:
        """
        Issue a refresh token.
        
        Args:
            sub: Subject (user ID)
            tenant_id: Tenant identifier
            expires_in: Custom expiration in days
            audience: Token audience
            issuer: Token issuer
            
        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expires_in = expires_in or self.refresh_token_expire_days
        exp = now + timedelta(days=expires_in)
        
        claims = {
            "sub": sub,
            "iat": now,
            "exp": exp,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "iss": issuer or self.issuer,
            "aud": audience or self.default_audience,
        }
        
        if tenant_id:
            claims["tenant_id"] = tenant_id
        
        # Remove None values
        claims = {k: v for k, v in claims.items() if v is not None}
        
        try:
            return jwt.encode(
                claims,
                self._get_signing_key(),
                algorithm=self.algorithm
            )
        except Exception as e:
            raise InvalidToken(f"Failed to encode refresh token: {e}")
    
    def verify_token(
        self,
        token: str,
        expected_type: Optional[str] = None,
        expected_audience: Optional[str] = None,
        expected_issuer: Optional[str] = None,
        verify_exp: bool = True,
        verify_signature: bool = True
    ) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            expected_type: Expected token type ("access" or "refresh")
            expected_audience: Expected audience claim
            expected_issuer: Expected issuer claim
            verify_exp: Whether to verify expiration
            verify_signature: Whether to verify signature
            
        Returns:
            Decoded token claims
            
        Raises:
            Various token validation exceptions
        """
        try:
            # Decode without verification first to check algorithm
            unverified = jwt.decode(token, options={"verify_signature": False})
            
            # Verify algorithm matches our configuration
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self.algorithm:
                raise InvalidAlgorithm(f"Token algorithm {header.get('alg')} does not match expected {self.algorithm}")
            
            # Configure verification options
            options = {
                "verify_signature": verify_signature,
                "verify_exp": verify_exp,
                "verify_aud": bool(expected_audience),
                "verify_iss": bool(expected_issuer)
            }
            
            # Decode and verify
            claims = jwt.decode(
                token,
                self._get_verification_key() if verify_signature else None,
                algorithms=[self.algorithm],
                audience=expected_audience,
                issuer=expected_issuer,
                leeway=self.leeway,
                options=options
            )
            
            # Verify token type if specified
            if expected_type and claims.get("type") != expected_type:
                raise InvalidToken(f"Expected token type '{expected_type}', got '{claims.get('type')}'")
            
            return claims
            
        except jwt.ExpiredSignatureError:
            exp_time = unverified.get("exp")
            expired_at = datetime.fromtimestamp(exp_time, tz=timezone.utc).isoformat() if exp_time else None
            raise TokenExpired(expired_at=expired_at)
        
        except jwt.InvalidSignatureError:
            raise InvalidSignature()
        
        except jwt.InvalidAudienceError:
            raise InvalidAudience(
                expected=expected_audience,
                actual=unverified.get("aud")
            )
        
        except jwt.InvalidIssuerError:
            raise InvalidIssuer(
                expected=expected_issuer,
                actual=unverified.get("iss")
            )
        
        except jwt.InvalidTokenError as e:
            raise InvalidToken(f"Token validation failed: {str(e)}")
        
        except Exception as e:
            raise InvalidToken(f"Unexpected token validation error: {str(e)}")
    
    def refresh_access_token(
        self,
        refresh_token: str,
        scopes: Optional[List[str]] = None,
        expires_in: Optional[int] = None,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Issue a new access token using a refresh token.
        
        Args:
            refresh_token: Valid refresh token
            scopes: Scopes for the new access token
            expires_in: Custom expiration in minutes
            extra_claims: Additional claims to include
            
        Returns:
            New access token
        """
        # Verify refresh token
        refresh_claims = self.verify_token(
            refresh_token,
            expected_type="refresh"
        )
        
        # Issue new access token with same subject and tenant
        return self.issue_access_token(
            sub=refresh_claims["sub"],
            scopes=scopes,
            tenant_id=refresh_claims.get("tenant_id"),
            expires_in=expires_in,
            extra_claims=extra_claims,
            audience=refresh_claims.get("aud"),
            issuer=refresh_claims.get("iss")
        )
    
    def decode_token_unsafe(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging/logging).
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded claims (unverified)
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            raise InvalidToken(f"Failed to decode token: {e}")
    
    def get_token_header(self, token: str) -> Dict[str, Any]:
        """
        Get token header without verification.
        
        Args:
            token: JWT token
            
        Returns:
            Token header
        """
        try:
            return jwt.get_unverified_header(token)
        except Exception as e:
            raise InvalidToken(f"Failed to get token header: {e}")
    
    @staticmethod
    def generate_rsa_keypair(key_size: int = 2048) -> tuple[str, str]:
        """
        Generate RSA keypair for development/testing.
        
        Args:
            key_size: RSA key size in bits
            
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        return private_pem, public_pem
    
    @staticmethod
    def generate_hs256_secret(length: int = 32) -> str:
        """
        Generate a random secret for HS256.
        
        Args:
            length: Secret length in bytes
            
        Returns:
            Random secret string
        """
        import secrets
        return secrets.token_urlsafe(length)


def create_jwt_service_from_config(config: Dict[str, Any]) -> JWTService:
    """
    Create JWT service from configuration dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured JWTService instance
    """
    return JWTService(
        algorithm=config.get("algorithm", "RS256"),
        private_key=config.get("private_key"),
        public_key=config.get("public_key"),
        secret=config.get("secret"),
        issuer=config.get("issuer"),
        default_audience=config.get("default_audience"),
        access_token_expire_minutes=config.get("access_token_expire_minutes", 15),
        refresh_token_expire_days=config.get("refresh_token_expire_days", 7),
        leeway=config.get("leeway", 0)
    )