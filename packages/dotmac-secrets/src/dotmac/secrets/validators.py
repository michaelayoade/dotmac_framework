"""
Validators for different types of secrets
Includes policy validation and security checks
"""
from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from .interfaces import BaseValidator, SecretValidationError
from .types import SecretData, SecretKind, SecretPolicy

logger = logging.getLogger(__name__)

# Try to import cryptography for key validation
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.exceptions import InvalidSignature
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography not available - key validation will be limited")


class SecretValidator(BaseValidator):
    """
    Comprehensive secret validator with policy enforcement
    """
    
    def __init__(self, policy: Optional[SecretPolicy] = None) -> None:
        super().__init__()
        self.policy = policy or SecretPolicy()
        
        # Known weak passwords and secrets
        self.weak_secrets = {
            "password", "secret", "changeme", "admin", "root", "test",
            "12345", "123456", "password123", "admin123", "secret123",
            "default", "guest", "user", "qwerty", "letmein"
        }
        
        # Common database URLs that shouldn't be used in production
        self.weak_db_patterns = {
            "localhost", "127.0.0.1", "example.com", "test.db", "demo.db"
        }
    
    def validate(self, secret_data: SecretData, kind: SecretKind) -> bool:
        """
        Validate secret data according to type and policy
        
        Args:
            secret_data: Secret data to validate
            kind: Type of secret being validated
            
        Returns:
            True if valid
            
        Raises:
            SecretValidationError: If validation fails
        """
        self._clear_errors()
        
        try:
            if kind == SecretKind.JWT_KEYPAIR:
                return self._validate_jwt_keypair(secret_data)
            elif kind == SecretKind.SYMMETRIC_SECRET:
                return self._validate_symmetric_secret(secret_data)
            elif kind == SecretKind.SERVICE_SIGNING_SECRET:
                return self._validate_service_signing_secret(secret_data)
            elif kind == SecretKind.DATABASE_CREDENTIALS:
                return self._validate_database_credentials(secret_data)
            elif kind == SecretKind.ENCRYPTION_KEY:
                return self._validate_encryption_key(secret_data)
            elif kind == SecretKind.WEBHOOK_SECRET:
                return self._validate_webhook_secret(secret_data)
            else:
                return self._validate_custom_secret(secret_data)
                
        except Exception as e:
            self._add_error(f"Validation error: {e}")
            return False
    
    def _validate_jwt_keypair(self, secret_data: SecretData) -> bool:
        """Validate JWT keypair data"""
        valid = True
        
        # Check for required fields
        if "algorithm" not in secret_data:
            self._add_error("JWT keypair missing algorithm")
            valid = False
        else:
            algorithm = secret_data["algorithm"]
            
            # Validate algorithm
            if algorithm not in self.policy.allowed_algorithms and self.policy.allowed_algorithms:
                self._add_error(f"Algorithm {algorithm} not allowed by policy")
                valid = False
            
            # Check for symmetric vs asymmetric algorithms
            if algorithm.startswith(("HS", "A")):
                # Symmetric algorithm
                if "secret" not in secret_data:
                    self._add_error("Symmetric JWT algorithm requires 'secret' field")
                    valid = False
                else:
                    secret = secret_data["secret"]
                    if not self._validate_secret_strength(secret):
                        valid = False
                        
            else:
                # Asymmetric algorithm
                if "private_pem" not in secret_data or "public_pem" not in secret_data:
                    self._add_error("Asymmetric JWT algorithm requires 'private_pem' and 'public_pem' fields")
                    valid = False
                else:
                    if not self._validate_pem_keypair(
                        secret_data["private_pem"], 
                        secret_data["public_pem"], 
                        algorithm
                    ):
                        valid = False
        
        # Check kid (key ID)
        if "kid" in secret_data:
            kid = secret_data["kid"]
            if not isinstance(kid, str) or not kid.strip():
                self._add_error("Key ID (kid) must be a non-empty string")
                valid = False
        
        return valid
    
    def _validate_pem_keypair(self, private_pem: str, public_pem: str, algorithm: str) -> bool:
        """Validate PEM keypair format and strength"""
        if not HAS_CRYPTOGRAPHY:
            logger.warning("Cannot validate PEM keys without cryptography library")
            return True
        
        valid = True
        
        try:
            # Parse private key
            private_key = serialization.load_pem_private_key(
                private_pem.encode('utf-8'),
                password=None
            )
            
            # Parse public key
            public_key = serialization.load_pem_public_key(
                public_pem.encode('utf-8')
            )
            
            # Validate key types match algorithm
            if algorithm.startswith("RS"):
                if not isinstance(private_key, rsa.RSAPrivateKey):
                    self._add_error(f"Algorithm {algorithm} requires RSA keys")
                    valid = False
                else:
                    key_size = private_key.key_size
                    if key_size < 2048:
                        self._add_error(f"RSA key size {key_size} is too small (minimum 2048)")
                        valid = False
                        
            elif algorithm.startswith("ES"):
                if not isinstance(private_key, ec.EllipticCurvePrivateKey):
                    self._add_error(f"Algorithm {algorithm} requires EC keys")
                    valid = False
            
            # Verify keypair matches
            private_public_key = private_key.public_key()
            
            # Compare key parameters (simplified check)
            if isinstance(private_key, rsa.RSAPrivateKey):
                private_n = private_public_key.public_numbers().n
                public_n = public_key.public_numbers().n
                if private_n != public_n:
                    self._add_error("Private and public keys do not match")
                    valid = False
            
        except Exception as e:
            self._add_error(f"Invalid PEM format: {e}")
            valid = False
        
        return valid
    
    def _validate_symmetric_secret(self, secret_data: SecretData) -> bool:
        """Validate symmetric secret"""
        valid = True
        
        if "secret" not in secret_data:
            self._add_error("Symmetric secret missing 'secret' field")
            return False
        
        secret = secret_data["secret"]
        
        if not self._validate_secret_strength(secret):
            valid = False
        
        return valid
    
    def _validate_service_signing_secret(self, secret_data: SecretData) -> bool:
        """Validate service signing secret"""
        valid = True
        
        if "secret" not in secret_data:
            self._add_error("Service signing secret missing 'secret' field")
            return False
        
        secret = secret_data["secret"]
        
        if not self._validate_secret_strength(secret):
            valid = False
        
        return valid
    
    def _validate_database_credentials(self, secret_data: SecretData) -> bool:
        """Validate database credentials"""
        valid = True
        
        # Check required fields
        required_fields = ["host", "username", "password", "database"]
        for field in required_fields:
            if field not in secret_data:
                self._add_error(f"Database credentials missing '{field}' field")
                valid = False
        
        if not valid:
            return False
        
        # Validate individual fields
        host = secret_data["host"]
        username = secret_data["username"]
        password = secret_data["password"]
        database = secret_data["database"]
        
        # Check for weak hostnames
        if any(weak in host.lower() for weak in self.weak_db_patterns):
            self._add_error(f"Database host appears to be for development/testing: {host}")
            valid = False
        
        # Check for weak usernames
        if username.lower() in self.weak_secrets:
            self._add_error(f"Database username is too weak: {username}")
            valid = False
        
        # Validate password strength
        if not self._validate_secret_strength(password, "database password"):
            valid = False
        
        # Check port if specified
        if "port" in secret_data:
            port = secret_data["port"]
            if not isinstance(port, int) or not (1 <= port <= 65535):
                self._add_error(f"Invalid database port: {port}")
                valid = False
        
        # Validate driver if specified
        if "driver" in secret_data:
            driver = secret_data["driver"]
            supported_drivers = ["postgresql", "mysql", "sqlite", "mariadb", "oracle", "mssql"]
            if driver not in supported_drivers:
                logger.warning(f"Unknown database driver: {driver}")
        
        return valid
    
    def _validate_encryption_key(self, secret_data: SecretData) -> bool:
        """Validate encryption key"""
        valid = True
        
        if "key" not in secret_data:
            self._add_error("Encryption key missing 'key' field")
            return False
        
        key = secret_data["key"]
        
        # For encryption keys, we might have binary data encoded as base64 or hex
        if isinstance(key, str):
            # Check if it looks like base64 or hex
            if self._is_base64(key):
                try:
                    import base64
                    decoded = base64.b64decode(key)
                    key_bytes = len(decoded)
                except Exception:
                    self._add_error("Invalid base64 encoding for encryption key")
                    valid = False
                    key_bytes = 0
            elif self._is_hex(key):
                key_bytes = len(key) // 2
            else:
                key_bytes = len(key.encode('utf-8'))
        elif isinstance(key, bytes):
            key_bytes = len(key)
        else:
            self._add_error("Encryption key must be string or bytes")
            return False
        
        # Check minimum length
        if key_bytes < self.policy.min_length:
            self._add_error(
                f"Encryption key too short: {key_bytes} bytes "
                f"(minimum {self.policy.min_length})"
            )
            valid = False
        
        return valid
    
    def _validate_webhook_secret(self, secret_data: SecretData) -> bool:
        """Validate webhook secret"""
        valid = True
        
        if "secret" not in secret_data:
            self._add_error("Webhook secret missing 'secret' field")
            return False
        
        secret = secret_data["secret"]
        
        if not self._validate_secret_strength(secret, "webhook secret"):
            valid = False
        
        return valid
    
    def _validate_custom_secret(self, secret_data: SecretData) -> bool:
        """Validate custom secret (basic checks only)"""
        if not secret_data:
            self._add_error("Custom secret data is empty")
            return False
        
        # Just check that we have some data
        return True
    
    def _validate_secret_strength(self, secret: str, secret_type: str = "secret") -> bool:
        """
        Validate secret strength according to policy
        
        Args:
            secret: Secret string to validate
            secret_type: Type of secret for error messages
            
        Returns:
            True if secret meets policy requirements
        """
        valid = True
        
        if not isinstance(secret, str):
            self._add_error(f"{secret_type.title()} must be a string")
            return False
        
        # Check minimum length
        if len(secret) < self.policy.min_length:
            self._add_error(
                f"{secret_type.title()} too short: {len(secret)} characters "
                f"(minimum {self.policy.min_length})"
            )
            valid = False
        
        # Check for weak secrets
        if secret.lower() in self.weak_secrets:
            self._add_error(f"{secret_type.title()} is too weak: {secret}")
            valid = False
        
        # Check forbidden patterns
        for pattern in self.policy.forbidden_patterns:
            if re.search(pattern.lower(), secret.lower()):
                self._add_error(f"{secret_type.title()} matches forbidden pattern: {pattern}")
                valid = False
        
        # Check special character requirement
        if self.policy.require_special_chars:
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', secret):
                self._add_error(f"{secret_type.title()} must contain special characters")
                valid = False
        
        return valid
    
    def _is_base64(self, s: str) -> bool:
        """Check if string looks like base64"""
        try:
            import base64
            if len(s) % 4 != 0:
                return False
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False
    
    def _is_hex(self, s: str) -> bool:
        """Check if string looks like hex"""
        try:
            int(s, 16)
            return len(s) % 2 == 0
        except ValueError:
            return False


class JWTValidator(BaseValidator):
    """Specialized validator for JWT keypairs"""
    
    def __init__(self, allowed_algorithms: Optional[List[str]] = None) -> None:
        super().__init__()
        self.allowed_algorithms = allowed_algorithms or [
            "RS256", "RS384", "RS512", 
            "ES256", "ES384", "ES512",
            "HS256", "HS384", "HS512"
        ]
    
    def validate(self, secret_data: SecretData, kind: SecretKind) -> bool:
        """Validate JWT keypair specifically"""
        self._clear_errors()
        
        if kind != SecretKind.JWT_KEYPAIR:
            self._add_error("JWTValidator only validates JWT keypairs")
            return False
        
        validator = SecretValidator(SecretPolicy(allowed_algorithms=self.allowed_algorithms))
        return validator._validate_jwt_keypair(secret_data)


class DatabaseCredentialsValidator(BaseValidator):
    """Specialized validator for database credentials"""
    
    def __init__(self, allow_weak_hosts: bool = False) -> None:
        super().__init__()
        self.allow_weak_hosts = allow_weak_hosts
    
    def validate(self, secret_data: SecretData, kind: SecretKind) -> bool:
        """Validate database credentials specifically"""
        self._clear_errors()
        
        if kind != SecretKind.DATABASE_CREDENTIALS:
            self._add_error("DatabaseCredentialsValidator only validates database credentials")
            return False
        
        validator = SecretValidator()
        if self.allow_weak_hosts:
            # Temporarily clear weak patterns for validation
            original_patterns = validator.weak_db_patterns
            validator.weak_db_patterns = set()
        
        try:
            return validator._validate_database_credentials(secret_data)
        finally:
            if self.allow_weak_hosts:
                validator.weak_db_patterns = original_patterns


class PolicyValidator(BaseValidator):
    """Validator that enforces custom policies"""
    
    def __init__(self, policies: Dict[SecretKind, SecretPolicy]) -> None:
        super().__init__()
        self.policies = policies
    
    def validate(self, secret_data: SecretData, kind: SecretKind) -> bool:
        """Validate secret according to kind-specific policy"""
        self._clear_errors()
        
        policy = self.policies.get(kind)
        if not policy:
            # No specific policy, use default validation
            validator = SecretValidator()
            return validator.validate(secret_data, kind)
        
        validator = SecretValidator(policy)
        return validator.validate(secret_data, kind)


def create_default_validator() -> SecretValidator:
    """Create validator with secure default policies"""
    policy = SecretPolicy(
        min_length=32,
        require_special_chars=False,  # Don't require for all secret types
        forbidden_patterns=[
            r"(password|secret|key)\d{1,3}$",  # password123, secret1, etc.
            r"^(test|demo|sample)",  # test*, demo*, sample*
            r"(admin|root)$",  # admin, root
        ],
        allowed_algorithms=[
            "RS256", "RS384", "RS512",
            "ES256", "ES384", "ES512"
        ]
    )
    
    return SecretValidator(policy)


def create_development_validator() -> SecretValidator:
    """Create validator with relaxed policies for development"""
    policy = SecretPolicy(
        min_length=16,  # Shorter minimum for development
        require_special_chars=False,
        forbidden_patterns=[],  # No forbidden patterns in development
        allowed_algorithms=[
            "RS256", "RS384", "RS512",
            "ES256", "ES384", "ES512",
            "HS256", "HS384", "HS512"  # Allow symmetric algorithms in dev
        ]
    )
    
    return SecretValidator(policy)