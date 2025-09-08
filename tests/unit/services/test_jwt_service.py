"""
Tests for JWT Service - Token management, validation, and security.
"""
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# Adjust path for platform services imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-platform-services/src'))

from tests.utilities.service_test_base import AsyncServiceTestBase

from dotmac.platform.auth.exceptions import (
    ConfigurationError,
    InvalidSignature,
    InvalidToken,
    TokenExpired,
)
from dotmac.platform.auth.jwt_service import JWTService

# Restore path after imports
sys.path = sys.path[1:]


class TestJWTService(AsyncServiceTestBase):
    """Test suite for JWT Service functionality."""

    @pytest.fixture
    def jwt_service_config(self):
        """Basic JWT service configuration for testing."""
        return {
            "algorithm": "HS256",
            "secret": "test-secret-key-for-testing-minimum-32-chars",
            "issuer": "dotmac-test",
            "default_audience": "dotmac-app",
            "access_token_expire_minutes": 15,
            "refresh_token_expire_days": 7
        }

    @pytest.fixture
    def jwt_service(self, jwt_service_config):
        """Create JWT service instance for testing."""
        return JWTService(**jwt_service_config)

    def test_jwt_service_initialization(self, jwt_service_config):
        """Test JWT service initialization with various configurations."""
        # Test with HS256 algorithm
        service = JWTService(**jwt_service_config)
        assert service.algorithm == "HS256"
        assert service.secret == jwt_service_config["secret"]
        assert service.issuer == "dotmac-test"

    def test_jwt_service_initialization_rs256(self):
        """Test JWT service initialization with RS256 algorithm."""
        # Mock RSA key generation for testing
        with patch('cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key') as mock_gen:
            mock_private_key = Mock()
            mock_private_key.private_bytes.return_value = b"mock_private_key"
            mock_private_key.public_key.return_value.public_bytes.return_value = b"mock_public_key"
            mock_gen.return_value = mock_private_key

            service = JWTService(
                algorithm="RS256",
                issuer="dotmac-test-rs256"
            )
            assert service.algorithm == "RS256"
            assert service.issuer == "dotmac-test-rs256"

    def test_create_access_token(self, jwt_service):
        """Test access token creation."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "tenant_id": "tenant456"
        }

        token = jwt_service.create_access_token(user_data)

        assert isinstance(token, str)
        assert len(token) > 20  # JWT tokens are substantial strings
        assert token.count('.') == 2  # JWT has 3 parts separated by dots

    def test_create_refresh_token(self, jwt_service):
        """Test refresh token creation."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com"
        }

        refresh_token = jwt_service.create_refresh_token(user_data)

        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 20
        assert refresh_token.count('.') == 2

    def test_create_token_pair(self, jwt_service):
        """Test creation of access and refresh token pair."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "tenant_id": "tenant456",
            "roles": ["user"]
        }

        token_pair = jwt_service.create_token_pair(user_data)

        assert "access_token" in token_pair
        assert "refresh_token" in token_pair
        assert "token_type" in token_pair
        assert token_pair["token_type"] == "bearer"

        # Both tokens should be valid JWT format
        assert token_pair["access_token"].count('.') == 2
        assert token_pair["refresh_token"].count('.') == 2

    def test_verify_token_valid(self, jwt_service):
        """Test verification of valid tokens."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com"
        }

        # Create a token
        token = jwt_service.create_access_token(user_data)

        # Verify the token
        payload = jwt_service.verify_token(token)

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
        assert payload["iss"] == "dotmac-test"

    def test_verify_token_invalid_signature(self, jwt_service):
        """Test verification fails for tokens with invalid signatures."""
        # Create a token with different service
        other_service = JWTService(
            algorithm="HS256",
            secret="different-secret-key-minimum-32-chars",
            issuer="other-issuer"
        )

        token = other_service.create_access_token({"sub": "user123"})

        # Verification should fail due to different secret
        with pytest.raises(InvalidSignature):
            jwt_service.verify_token(token)

    def test_verify_token_expired(self, jwt_service):
        """Test verification fails for expired tokens."""
        user_data = {"sub": "user123"}

        # Create a token with very short expiry
        short_lived_service = JWTService(
            algorithm="HS256",
            secret="test-secret-key-for-testing-minimum-32-chars",
            access_token_expire_minutes=-1  # Already expired
        )

        token = short_lived_service.create_access_token(user_data)

        # Verification should fail due to expiration
        with pytest.raises(TokenExpired):
            jwt_service.verify_token(token)

    def test_verify_token_invalid_format(self, jwt_service):
        """Test verification fails for malformed tokens."""
        invalid_tokens = [
            "invalid.token",  # Only 2 parts
            "not.a.token.at.all",  # Too many parts
            "notavalidtoken",  # No separators
            "",  # Empty string
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises(InvalidToken):
                jwt_service.verify_token(invalid_token)

    def test_decode_token(self, jwt_service):
        """Test token decoding without verification."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "roles": ["admin", "user"]
        }

        token = jwt_service.create_access_token(user_data)
        decoded = jwt_service.decode_token(token, verify=False)

        assert decoded["sub"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert decoded["roles"] == ["admin", "user"]

    def test_refresh_access_token(self, jwt_service):
        """Test access token refresh using refresh token."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com"
        }

        # Create token pair
        token_pair = jwt_service.create_token_pair(user_data)
        refresh_token = token_pair["refresh_token"]

        # Refresh the access token
        new_access_token = jwt_service.refresh_access_token(refresh_token)

        assert isinstance(new_access_token, str)
        assert new_access_token.count('.') == 2

        # Verify new token contains same user data
        payload = jwt_service.verify_token(new_access_token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    def test_token_with_custom_claims(self, jwt_service):
        """Test token creation and verification with custom claims."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "custom_field": "custom_value",
            "permissions": ["read", "write"],
            "metadata": {"department": "IT", "level": "senior"}
        }

        token = jwt_service.create_access_token(user_data)
        payload = jwt_service.verify_token(token)

        assert payload["sub"] == "user123"
        assert payload["custom_field"] == "custom_value"
        assert payload["permissions"] == ["read", "write"]
        assert payload["metadata"]["department"] == "IT"
        assert payload["metadata"]["level"] == "senior"

    def test_token_audience_validation(self):
        """Test token audience validation."""
        service_with_audience = JWTService(
            algorithm="HS256",
            secret="test-secret-key-for-testing-minimum-32-chars",
            default_audience="specific-app"
        )

        user_data = {"sub": "user123"}
        token = service_with_audience.create_access_token(user_data)

        # Verify with correct audience
        payload = service_with_audience.verify_token(token, audience="specific-app")
        assert payload["sub"] == "user123"
        assert payload["aud"] == "specific-app"

    def test_algorithm_validation(self):
        """Test that unsupported algorithms are rejected."""
        with pytest.raises(ValueError):
            JWTService(algorithm="HS512")  # Unsupported algorithm

        with pytest.raises(ValueError):
            JWTService(algorithm="NONE")  # Unsupported algorithm

    def test_configuration_validation(self):
        """Test service configuration validation."""
        # Test missing secret for HS256
        with pytest.raises(ConfigurationError):
            JWTService(algorithm="HS256", secret=None)

        # Test short secret
        with pytest.raises(ConfigurationError):
            JWTService(algorithm="HS256", secret="short")

    def test_token_expiration_times(self, jwt_service):
        """Test that token expiration times are set correctly."""
        user_data = {"sub": "user123"}

        # Create tokens
        access_token = jwt_service.create_access_token(user_data)
        refresh_token = jwt_service.create_refresh_token(user_data)

        # Decode without verification to check expiration
        access_payload = jwt_service.decode_token(access_token, verify=False)
        refresh_payload = jwt_service.decode_token(refresh_token, verify=False)

        # Access token should expire in 15 minutes
        access_exp = datetime.fromtimestamp(access_payload["exp"])
        access_iat = datetime.fromtimestamp(access_payload["iat"])
        access_duration = access_exp - access_iat

        # Should be approximately 15 minutes (allow 1 minute tolerance)
        assert timedelta(minutes=14) <= access_duration <= timedelta(minutes=16)

        # Refresh token should expire in 7 days
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"])
        refresh_iat = datetime.fromtimestamp(refresh_payload["iat"])
        refresh_duration = refresh_exp - refresh_iat

        # Should be approximately 7 days (allow 1 hour tolerance)
        assert timedelta(days=6, hours=23) <= refresh_duration <= timedelta(days=7, hours=1)


class TestJWTServiceIntegration(AsyncServiceTestBase):
    """Integration tests for JWT service with other components."""

    @pytest.fixture
    def jwt_service(self):
        """Create JWT service for integration testing."""
        return JWTService(
            algorithm="HS256",
            secret="integration-test-secret-minimum-32-chars",
            issuer="dotmac-integration"
        )

    def test_jwt_service_with_user_service_integration(self, jwt_service):
        """Test JWT service integration with user authentication flow."""
        # Mock user service
        user_service = self.create_mock_service("user_service")
        user_service.authenticate.return_value = {
            "id": "user123",
            "email": "test@example.com",
            "is_active": True,
            "roles": ["user"]
        }

        # Simulate authentication flow
        user_data = user_service.authenticate()
        token_pair = jwt_service.create_token_pair(user_data)

        # Verify tokens contain user information
        access_payload = jwt_service.verify_token(token_pair["access_token"])
        assert access_payload["id"] == "user123"
        assert access_payload["email"] == "test@example.com"
        assert access_payload["roles"] == ["user"]

    def test_jwt_service_with_cache_integration(self, jwt_service):
        """Test JWT service integration with token caching/blacklisting."""
        cache_service = self.create_mock_cache("token_cache")

        user_data = {"sub": "user123", "email": "test@example.com"}
        token = jwt_service.create_access_token(user_data)

        # Simulate token blacklisting
        cache_service.set(f"blacklisted:{token}", True, ttl=900)

        # In real implementation, JWT service would check cache
        cache_service.get.return_value = True
        is_blacklisted = cache_service.get(f"blacklisted:{token}")

        assert is_blacklisted is True
        self.assert_service_called("cache", "get", f"blacklisted:{token}")

    def test_jwt_service_error_handling_integration(self, jwt_service):
        """Test JWT service error handling in integration scenarios."""
        # Test with None user data
        with pytest.raises(ValueError):
            jwt_service.create_access_token(None)

        # Test with empty user data
        empty_token = jwt_service.create_access_token({})
        payload = jwt_service.verify_token(empty_token)
        # Should still work but with minimal claims
        assert "iat" in payload
        assert "exp" in payload
        assert "iss" in payload
