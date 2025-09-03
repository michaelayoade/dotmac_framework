"""
Tests for JWT Service

Comprehensive tests for JWT token issuance, verification, and refresh functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from dotmac.auth import (
    JWTService,
    InvalidToken,
    TokenExpired,
    InvalidSignature,
    InvalidAudience,
    InvalidIssuer,
    InvalidAlgorithm,
    ConfigurationError,
    create_jwt_service_from_config,
)


class TestJWTServiceHS256:
    """Test JWT service with HS256 algorithm"""
    
    @pytest.fixture
    def jwt_service(self):
        return JWTService(
            algorithm="HS256",
            secret="test-secret-key-256-bits-long-enough-for-hs256",
            issuer="test-issuer",
            default_audience="test-audience"
        )
    
    def test_initialization_hs256(self):
        """Test HS256 service initialization"""
        service = JWTService(
            algorithm="HS256",
            secret="test-secret"
        )
        assert service.algorithm == "HS256"
        assert service.secret == "test-secret"
    
    def test_missing_secret_raises_error(self):
        """Test that missing secret raises configuration error"""
        with pytest.raises(ConfigurationError):
            JWTService(algorithm="HS256")
    
    def test_issue_access_token(self, jwt_service):
        """Test access token issuance"""
        token = jwt_service.issue_access_token(
            sub="user123",
            scopes=["read", "write"],
            tenant_id="tenant1",
            expires_in=30,
            extra_claims={"custom": "value"}
        )
        
        assert isinstance(token, str)
        
        # Verify token contents
        claims = jwt_service.verify_token(token)
        assert claims["sub"] == "user123"
        assert claims["scopes"] == ["read", "write"]
        assert claims["scope"] == "read write"
        assert claims["tenant_id"] == "tenant1"
        assert claims["type"] == "access"
        assert claims["custom"] == "value"
        assert claims["iss"] == "test-issuer"
        assert claims["aud"] == "test-audience"
        assert "jti" in claims
        assert "iat" in claims
        assert "exp" in claims
    
    def test_issue_refresh_token(self, jwt_service):
        """Test refresh token issuance"""
        token = jwt_service.issue_refresh_token(
            sub="user123",
            tenant_id="tenant1",
            expires_in=1  # 1 day
        )
        
        assert isinstance(token, str)
        
        # Verify token contents
        claims = jwt_service.verify_token(token)
        assert claims["sub"] == "user123"
        assert claims["tenant_id"] == "tenant1"
        assert claims["type"] == "refresh"
        assert "scopes" not in claims  # Refresh tokens don't have scopes
    
    def test_token_verification(self, jwt_service):
        """Test token verification"""
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        
        # Valid verification
        claims = jwt_service.verify_token(token)
        assert claims["sub"] == "user123"
        
        # Verify with expected type
        claims = jwt_service.verify_token(token, expected_type="access")
        assert claims["type"] == "access"
        
        # Wrong type should raise error
        with pytest.raises(InvalidToken):
            jwt_service.verify_token(token, expected_type="refresh")
    
    def test_token_expiration(self, jwt_service):
        """Test token expiration validation"""
        # Create token with very short expiration
        token = jwt_service.issue_access_token("user123", expires_in=-1)  # Already expired
        
        with pytest.raises(TokenExpired):
            jwt_service.verify_token(token)
    
    def test_audience_validation(self, jwt_service):
        """Test audience validation"""
        token = jwt_service.issue_access_token("user123")
        
        # Valid audience
        claims = jwt_service.verify_token(token, expected_audience="test-audience")
        assert claims["aud"] == "test-audience"
        
        # Invalid audience
        with pytest.raises(InvalidAudience):
            jwt_service.verify_token(token, expected_audience="wrong-audience")
    
    def test_issuer_validation(self, jwt_service):
        """Test issuer validation"""
        token = jwt_service.issue_access_token("user123")
        
        # Valid issuer
        claims = jwt_service.verify_token(token, expected_issuer="test-issuer")
        assert claims["iss"] == "test-issuer"
        
        # Invalid issuer
        with pytest.raises(InvalidIssuer):
            jwt_service.verify_token(token, expected_issuer="wrong-issuer")
    
    def test_refresh_access_token(self, jwt_service):
        """Test access token refresh"""
        refresh_token = jwt_service.issue_refresh_token("user123", tenant_id="tenant1")
        
        new_access_token = jwt_service.refresh_access_token(
            refresh_token,
            scopes=["read", "write"],
            extra_claims={"refreshed": True}
        )
        
        # Verify new access token
        claims = jwt_service.verify_token(new_access_token)
        assert claims["sub"] == "user123"
        assert claims["tenant_id"] == "tenant1"
        assert claims["type"] == "access"
        assert claims["scopes"] == ["read", "write"]
        assert claims["refreshed"] is True
    
    def test_decode_unsafe(self, jwt_service):
        """Test unsafe token decoding"""
        token = jwt_service.issue_access_token("user123")
        claims = jwt_service.decode_token_unsafe(token)
        
        assert claims["sub"] == "user123"
        # Should work even with invalid tokens (for debugging)
    
    def test_get_token_header(self, jwt_service):
        """Test token header extraction"""
        token = jwt_service.issue_access_token("user123")
        header = jwt_service.get_token_header(token)
        
        assert header["alg"] == "HS256"
        assert header["typ"] == "JWT"
    
    def test_invalid_signature_detection(self):
        """Test invalid signature detection"""
        service1 = JWTService(algorithm="HS256", secret="secret1")
        service2 = JWTService(algorithm="HS256", secret="secret2")
        
        token = service1.issue_access_token("user123")
        
        with pytest.raises(InvalidSignature):
            service2.verify_token(token)
    
    def test_leeway_handling(self):
        """Test clock skew tolerance"""
        service = JWTService(
            algorithm="HS256", 
            secret="test-secret",
            leeway=5  # 5 seconds leeway
        )
        
        # This test would need more complex timing logic
        # For now, just verify leeway is set
        assert service.leeway == 5


class TestJWTServiceRS256:
    """Test JWT service with RS256 algorithm"""
    
    @pytest.fixture
    def rsa_keypair(self):
        return JWTService.generate_rsa_keypair()
    
    @pytest.fixture
    def jwt_service(self, rsa_keypair):
        private_key, public_key = rsa_keypair
        return JWTService(
            algorithm="RS256",
            private_key=private_key,
            public_key=public_key,
            issuer="test-issuer"
        )
    
    def test_initialization_rs256(self, rsa_keypair):
        """Test RS256 service initialization"""
        private_key, public_key = rsa_keypair
        service = JWTService(
            algorithm="RS256",
            private_key=private_key,
            public_key=public_key
        )
        assert service.algorithm == "RS256"
        assert service.private_key is not None
        assert service.public_key is not None
    
    def test_missing_keys_raises_error(self):
        """Test that missing keys raise configuration error"""
        with pytest.raises(ConfigurationError):
            JWTService(algorithm="RS256")
    
    def test_public_key_only_for_verification(self, rsa_keypair):
        """Test service with public key only (verification only)"""
        _, public_key = rsa_keypair
        service = JWTService(algorithm="RS256", public_key=public_key)
        
        # Should not be able to sign
        with pytest.raises(InvalidToken):
            service.issue_access_token("user123")
    
    def test_private_key_only_derives_public(self, rsa_keypair):
        """Test that public key is derived from private key"""
        private_key, _ = rsa_keypair
        service = JWTService(algorithm="RS256", private_key=private_key)
        
        # Should have both keys
        assert service.private_key is not None
        assert service.public_key is not None
    
    def test_token_signing_and_verification(self, jwt_service):
        """Test RS256 token signing and verification"""
        token = jwt_service.issue_access_token("user123", scopes=["read"])
        
        claims = jwt_service.verify_token(token)
        assert claims["sub"] == "user123"
        assert claims["scopes"] == ["read"]
    
    def test_key_generation(self):
        """Test RSA key pair generation"""
        private_key, public_key = JWTService.generate_rsa_keypair(key_size=2048)
        
        assert "BEGIN PRIVATE KEY" in private_key
        assert "BEGIN PUBLIC KEY" in public_key
        assert isinstance(private_key, str)
        assert isinstance(public_key, str)


class TestJWTServiceWithSecretsProvider:
    """Test JWT service with secrets provider"""
    
    def test_secrets_provider_integration(self):
        """Test secrets provider integration"""
        # Mock secrets provider
        mock_provider = Mock()
        mock_provider.get_symmetric_secret.return_value = "provider-secret"
        
        service = JWTService(
            algorithm="HS256",
            secrets_provider=mock_provider
        )
        
        assert service.secret == "provider-secret"
        mock_provider.get_symmetric_secret.assert_called_once()
    
    def test_secrets_provider_fallback(self):
        """Test fallback to provided secret when provider fails"""
        # Mock failing provider
        mock_provider = Mock()
        mock_provider.get_symmetric_secret.side_effect = Exception("Provider failed")
        
        service = JWTService(
            algorithm="HS256",
            secret="fallback-secret",
            secrets_provider=mock_provider
        )
        
        assert service.secret == "fallback-secret"


class TestJWTUtilities:
    """Test utility functions"""
    
    def test_hs256_secret_generation(self):
        """Test HS256 secret generation"""
        secret = JWTService.generate_hs256_secret(32)
        
        assert isinstance(secret, str)
        assert len(secret) > 20  # URL-safe base64 encoding
    
    def test_create_from_config(self):
        """Test service creation from configuration"""
        config = {
            "algorithm": "HS256",
            "secret": "config-secret",
            "issuer": "config-issuer",
            "access_token_expire_minutes": 30,
            "leeway": 10
        }
        
        service = create_jwt_service_from_config(config)
        
        assert service.algorithm == "HS256"
        assert service.secret == "config-secret"
        assert service.issuer == "config-issuer"
        assert service.access_token_expire_minutes == 30
        assert service.leeway == 10


class TestJWTEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_algorithm(self):
        """Test invalid algorithm raises error"""
        with pytest.raises(InvalidAlgorithm):
            JWTService(algorithm="INVALID", secret="test")
    
    def test_malformed_token(self):
        """Test handling of malformed tokens"""
        service = JWTService(algorithm="HS256", secret="test")
        
        with pytest.raises(InvalidToken):
            service.verify_token("not.a.jwt.token")
        
        with pytest.raises(InvalidToken):
            service.verify_token("malformed")
    
    def test_none_values_filtered(self):
        """Test that None values are filtered from claims"""
        service = JWTService(algorithm="HS256", secret="test")
        
        token = service.issue_access_token(
            "user123",
            tenant_id=None,  # Should be filtered out
            extra_claims={"valid": "value", "invalid": None}
        )
        
        claims = service.verify_token(token)
        assert "tenant_id" not in claims
        assert claims["valid"] == "value"
        assert "invalid" not in claims
    
    def test_algorithm_mismatch(self):
        """Test algorithm mismatch detection"""
        service = JWTService(algorithm="HS256", secret="test")
        
        # Create a token with different algorithm header (would need mocking JWT library)
        # For now, just test the service validates algorithm correctly
        token = service.issue_access_token("user123")
        header = service.get_token_header(token)
        assert header["alg"] == "HS256"


# Integration tests
class TestJWTIntegration:
    """Integration tests for complete JWT workflows"""
    
    def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        service = JWTService(
            algorithm="HS256",
            secret="integration-test-secret",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7
        )
        
        # 1. Issue initial tokens
        access_token = service.issue_access_token(
            "user123",
            scopes=["read", "write"],
            tenant_id="tenant1"
        )
        refresh_token = service.issue_refresh_token("user123", tenant_id="tenant1")
        
        # 2. Verify access token
        access_claims = service.verify_token(access_token, expected_type="access")
        assert access_claims["sub"] == "user123"
        assert access_claims["scopes"] == ["read", "write"]
        
        # 3. Verify refresh token
        refresh_claims = service.verify_token(refresh_token, expected_type="refresh")
        assert refresh_claims["sub"] == "user123"
        assert refresh_claims["type"] == "refresh"
        
        # 4. Refresh access token
        new_access_token = service.refresh_access_token(
            refresh_token,
            scopes=["read", "write", "admin"]
        )
        
        # 5. Verify new access token
        new_claims = service.verify_token(new_access_token)
        assert new_claims["sub"] == "user123"
        assert new_claims["tenant_id"] == "tenant1"
        assert "admin" in new_claims["scopes"]
    
    def test_multi_service_scenario(self):
        """Test scenario with multiple services sharing keys"""
        private_key, public_key = JWTService.generate_rsa_keypair()
        
        # Service that issues tokens (has private key)
        issuer_service = JWTService(
            algorithm="RS256",
            private_key=private_key,
            issuer="auth-service"
        )
        
        # Service that only verifies tokens (public key only)
        verifier_service = JWTService(
            algorithm="RS256",
            public_key=public_key
        )
        
        # Issue token with issuer service
        token = issuer_service.issue_access_token("user123", scopes=["api:read"])
        
        # Verify token with verifier service
        claims = verifier_service.verify_token(token)
        assert claims["sub"] == "user123"
        assert claims["iss"] == "auth-service"