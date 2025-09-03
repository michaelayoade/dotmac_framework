"""
Tests for secret validators
"""
import pytest
from unittest.mock import patch

from dotmac.secrets import (
    SecretKind,
    SecretPolicy,
    SecretValidationError,
    create_default_validator,
    create_development_validator,
    JWTValidator,
    DatabaseCredentialsValidator,
)
from dotmac.secrets.validators import SecretValidator


class TestSecretValidator:
    """Test SecretValidator functionality"""
    
    @pytest.fixture
    def validator(self):
        """Create default validator"""
        return create_default_validator()
    
    @pytest.fixture
    def lenient_validator(self):
        """Create lenient validator for development"""
        policy = SecretPolicy(
            min_length=8,
            forbidden_patterns=[],
            require_special_chars=False
        )
        return SecretValidator(policy)
    
    def test_validate_jwt_keypair_asymmetric(self, validator):
        """Test JWT asymmetric keypair validation"""
        valid_keypair = {
            "private_pem": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG...\n-----END PRIVATE KEY-----",
            "public_pem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG...\n-----END PUBLIC KEY-----",
            "algorithm": "RS256",
            "kid": "test-key"
        }
        
        assert validator.validate(valid_keypair, SecretKind.JWT_KEYPAIR)
        assert len(validator.get_validation_errors(valid_keypair, SecretKind.JWT_KEYPAIR)) == 0
    
    def test_validate_jwt_keypair_symmetric(self, validator):
        """Test JWT symmetric keypair validation"""
        valid_symmetric = {
            "secret": "this-is-a-very-long-symmetric-secret-key-that-meets-minimum-length",
            "algorithm": "HS256",
            "kid": "symmetric-key"
        }
        
        assert validator.validate(valid_symmetric, SecretKind.JWT_KEYPAIR)
    
    def test_validate_jwt_keypair_missing_fields(self, validator):
        """Test JWT keypair validation with missing fields"""
        invalid_keypair = {
            "algorithm": "RS256"
            # Missing private_pem and public_pem
        }
        
        assert not validator.validate(invalid_keypair, SecretKind.JWT_KEYPAIR)
        errors = validator.get_validation_errors(invalid_keypair, SecretKind.JWT_KEYPAIR)
        assert any("private_pem" in error for error in errors)
    
    def test_validate_jwt_keypair_invalid_algorithm(self, validator):
        """Test JWT keypair with invalid algorithm"""
        invalid_algorithm = {
            "secret": "test-secret-key-that-is-long-enough",
            "algorithm": "INVALID256",
            "kid": "test"
        }
        
        # Should fail if policy restricts algorithms
        policy = SecretPolicy(allowed_algorithms=["RS256", "ES256"])
        restricted_validator = SecretValidator(policy)
        
        assert not restricted_validator.validate(invalid_algorithm, SecretKind.JWT_KEYPAIR)
        errors = restricted_validator.get_validation_errors(invalid_algorithm, SecretKind.JWT_KEYPAIR)
        assert any("not allowed" in error for error in errors)
    
    def test_validate_symmetric_secret(self, validator):
        """Test symmetric secret validation"""
        valid_secret = {
            "secret": "this-is-a-long-enough-symmetric-secret-key-for-validation"
        }
        
        assert validator.validate(valid_secret, SecretKind.SYMMETRIC_SECRET)
    
    def test_validate_symmetric_secret_too_short(self, validator):
        """Test symmetric secret validation failure"""
        short_secret = {
            "secret": "short"
        }
        
        assert not validator.validate(short_secret, SecretKind.SYMMETRIC_SECRET)
        errors = validator.get_validation_errors(short_secret, SecretKind.SYMMETRIC_SECRET)
        assert any("too short" in error for error in errors)
    
    def test_validate_symmetric_secret_weak(self, validator):
        """Test weak symmetric secret detection"""
        weak_secret = {
            "secret": "password"
        }
        
        assert not validator.validate(weak_secret, SecretKind.SYMMETRIC_SECRET)
        errors = validator.get_validation_errors(weak_secret, SecretKind.SYMMETRIC_SECRET)
        assert any("too weak" in error for error in errors)
    
    def test_validate_database_credentials(self, validator):
        """Test database credentials validation"""
        valid_creds = {
            "host": "db.example.com",
            "username": "dbuser",
            "password": "secure-database-password-123!@#",
            "database": "production_db"
        }
        
        assert validator.validate(valid_creds, SecretKind.DATABASE_CREDENTIALS)
    
    def test_validate_database_credentials_missing_fields(self, validator):
        """Test database credentials with missing fields"""
        incomplete_creds = {
            "host": "db.example.com",
            "username": "dbuser"
            # Missing password and database
        }
        
        assert not validator.validate(incomplete_creds, SecretKind.DATABASE_CREDENTIALS)
        errors = validator.get_validation_errors(incomplete_creds, SecretKind.DATABASE_CREDENTIALS)
        assert any("missing" in error for error in errors)
    
    def test_validate_database_credentials_weak_host(self, validator):
        """Test database credentials with weak host"""
        weak_host_creds = {
            "host": "localhost",
            "username": "dbuser",
            "password": "secure-database-password-123!@#",
            "database": "test_db"
        }
        
        assert not validator.validate(weak_host_creds, SecretKind.DATABASE_CREDENTIALS)
        errors = validator.get_validation_errors(weak_host_creds, SecretKind.DATABASE_CREDENTIALS)
        assert any("development/testing" in error for error in errors)
    
    def test_validate_database_credentials_weak_password(self, validator):
        """Test database credentials with weak password"""
        weak_password_creds = {
            "host": "db.example.com",
            "username": "dbuser",
            "password": "admin",
            "database": "prod_db"
        }
        
        assert not validator.validate(weak_password_creds, SecretKind.DATABASE_CREDENTIALS)
        errors = validator.get_validation_errors(weak_password_creds, SecretKind.DATABASE_CREDENTIALS)
        assert any("too weak" in error for error in errors)
    
    def test_validate_encryption_key_string(self, validator):
        """Test encryption key validation (string format)"""
        valid_key = {
            "key": "this-is-a-32-byte-encryption-key-that-should-pass-validation"
        }
        
        assert validator.validate(valid_key, SecretKind.ENCRYPTION_KEY)
    
    def test_validate_encryption_key_base64(self, validator):
        """Test encryption key validation (base64 format)"""
        import base64
        
        # Create a 32-byte key and encode as base64
        key_bytes = b"this-is-exactly-32-bytes-long!!"
        key_base64 = base64.b64encode(key_bytes).decode('ascii')
        
        valid_key = {
            "key": key_base64
        }
        
        assert validator.validate(valid_key, SecretKind.ENCRYPTION_KEY)
    
    def test_validate_encryption_key_too_short(self, validator):
        """Test encryption key validation failure"""
        short_key = {
            "key": "short"
        }
        
        assert not validator.validate(short_key, SecretKind.ENCRYPTION_KEY)
        errors = validator.get_validation_errors(short_key, SecretKind.ENCRYPTION_KEY)
        assert any("too short" in error for error in errors)
    
    def test_validate_webhook_secret(self, validator):
        """Test webhook secret validation"""
        valid_webhook = {
            "secret": "webhook-signing-secret-that-is-long-enough-for-security"
        }
        
        assert validator.validate(valid_webhook, SecretKind.WEBHOOK_SECRET)
    
    def test_validate_custom_secret(self, validator):
        """Test custom secret validation"""
        custom_secret = {
            "api_key": "custom-api-key",
            "endpoint": "https://api.example.com",
            "timeout": 30
        }
        
        assert validator.validate(custom_secret, SecretKind.CUSTOM_SECRET)
    
    def test_validate_custom_secret_empty(self, validator):
        """Test custom secret validation with empty data"""
        empty_secret = {}
        
        assert not validator.validate(empty_secret, SecretKind.CUSTOM_SECRET)
        errors = validator.get_validation_errors(empty_secret, SecretKind.CUSTOM_SECRET)
        assert any("empty" in error for error in errors)
    
    def test_forbidden_patterns(self):
        """Test forbidden pattern validation"""
        policy = SecretPolicy(
            min_length=8,
            forbidden_patterns=[r"password\d+", r"^test"]
        )
        validator = SecretValidator(policy)
        
        # Should fail pattern matching
        invalid_secrets = [
            {"secret": "password123"},
            {"secret": "testpassword"},
        ]
        
        for secret_data in invalid_secrets:
            assert not validator.validate(secret_data, SecretKind.SYMMETRIC_SECRET)
            errors = validator.get_validation_errors(secret_data, SecretKind.SYMMETRIC_SECRET)
            assert any("forbidden pattern" in error for error in errors)
    
    def test_special_characters_requirement(self):
        """Test special characters requirement"""
        policy = SecretPolicy(
            min_length=8,
            require_special_chars=True
        )
        validator = SecretValidator(policy)
        
        # Should pass with special chars
        valid_secret = {"secret": "password123!@#"}
        assert validator.validate(valid_secret, SecretKind.SYMMETRIC_SECRET)
        
        # Should fail without special chars
        invalid_secret = {"secret": "password123"}
        assert not validator.validate(invalid_secret, SecretKind.SYMMETRIC_SECRET)
        errors = validator.get_validation_errors(invalid_secret, SecretKind.SYMMETRIC_SECRET)
        assert any("special characters" in error for error in errors)


class TestJWTValidator:
    """Test JWT-specific validator"""
    
    def test_jwt_validator_rsa(self):
        """Test JWT validator with RSA algorithm"""
        validator = JWTValidator(allowed_algorithms=["RS256"])
        
        valid_keypair = {
            "private_pem": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "public_pem": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----", 
            "algorithm": "RS256",
            "kid": "rsa-key"
        }
        
        assert validator.validate(valid_keypair, SecretKind.JWT_KEYPAIR)
    
    def test_jwt_validator_wrong_kind(self):
        """Test JWT validator with wrong secret kind"""
        validator = JWTValidator()
        
        secret = {"secret": "not-a-jwt-secret"}
        
        assert not validator.validate(secret, SecretKind.SYMMETRIC_SECRET)


class TestDatabaseCredentialsValidator:
    """Test database credentials specific validator"""
    
    def test_database_validator_normal(self):
        """Test database validator with normal validation"""
        validator = DatabaseCredentialsValidator(allow_weak_hosts=False)
        
        valid_creds = {
            "host": "prod-db.example.com",
            "username": "dbuser", 
            "password": "secure-password-123!@#",
            "database": "production"
        }
        
        assert validator.validate(valid_creds, SecretKind.DATABASE_CREDENTIALS)
    
    def test_database_validator_allow_weak_hosts(self):
        """Test database validator allowing weak hosts"""
        validator = DatabaseCredentialsValidator(allow_weak_hosts=True)
        
        # This should pass even with localhost
        dev_creds = {
            "host": "localhost",
            "username": "devuser",
            "password": "development-password-that-is-long-enough", 
            "database": "dev_db"
        }
        
        assert validator.validate(dev_creds, SecretKind.DATABASE_CREDENTIALS)


def test_create_default_validator():
    """Test default validator factory"""
    validator = create_default_validator()
    
    assert isinstance(validator, SecretValidator)
    assert validator.policy.min_length == 32
    assert validator.policy.require_special_chars is False
    assert len(validator.policy.forbidden_patterns) > 0


def test_create_development_validator():
    """Test development validator factory"""
    validator = create_development_validator()
    
    assert isinstance(validator, SecretValidator)
    assert validator.policy.min_length == 16  # More lenient
    assert validator.policy.forbidden_patterns == []  # No forbidden patterns
    assert "HS256" in validator.policy.allowed_algorithms  # Allow symmetric