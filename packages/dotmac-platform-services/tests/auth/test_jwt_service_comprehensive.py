"""
Comprehensive JWT Service Testing
Implementation of AUTH-001: JWT Service security and functionality testing.
"""

import pytest
import asyncio
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import time

from dotmac.platform.auth.jwt_service import JWTService


class TestJWTServiceComprehensive:
    """Comprehensive JWT service testing"""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service instance for testing"""
        # Use HS256 for testing simplicity
        return JWTService(
            algorithm="HS256",
            secret="test-secret-key-for-comprehensive-testing",
            issuer="test-issuer",
            default_audience="test-audience"
        )
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for JWT service"""
        return {
            'jwt_secret': 'test-secret-key-for-testing',
            'jwt_algorithm': 'HS256',
            'jwt_expiry_minutes': 30
        }
    
    # Token Generation Tests
    
    def test_jwt_token_generation_basic(self, jwt_service):
        """Test basic JWT token generation"""
        token = jwt_service.issue_access_token("user123")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_jwt_token_generation_with_custom_claims(self, jwt_service):
        """Test JWT token generation with custom claims"""
        custom_claims = {"role": "admin", "permissions": ["read", "write"]}
        token = jwt_service.issue_access_token("user123", extra_claims=custom_claims, tenant_id="test_tenant")
        
        # Decode without verification for testing
        decoded = jwt_service.decode_token_unsafe(token)
        
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "admin"
        assert decoded["tenant_id"] == "test_tenant"
        assert decoded["permissions"] == ["read", "write"]
    
    def test_jwt_token_generation_with_custom_expiry(self, jwt_service):
        """Test JWT token generation with custom expiry time"""
        # Generate token with 1 hour expiry
        token = jwt_service.issue_access_token("user123", expires_in=60)
        decoded = jwt_service.decode_token_unsafe(token)
        
        # Check expiry is approximately 1 hour from now
        exp_time = datetime.fromtimestamp(decoded["exp"], timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=60)
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_jwt_token_contains_standard_claims(self, jwt_service):
        """Test that JWT tokens contain standard claims"""
        token = jwt_service.issue_access_token("user123")
        decoded = jwt_service.decode_token_unsafe(token)
        
        # Standard JWT claims
        assert "sub" in decoded  # Subject
        assert "iat" in decoded  # Issued at
        assert "exp" in decoded  # Expiry
        assert "jti" in decoded  # JWT ID (should be unique)
        
        assert decoded["sub"] == "user123"
    
    # Token Validation Tests
    
    def test_jwt_token_validation_success(self, jwt_service):
        """Test successful JWT token validation"""
        token = jwt_service.issue_access_token("user123")
        
        # Should validate successfully
        decoded = jwt_service.verify_token(token)
        assert decoded["sub"] == "user123"
    
    def test_jwt_token_validation_with_claims(self, jwt_service):
        """Test JWT token validation preserves custom claims"""
        claims = {"role": "admin", "department": "engineering"}
        token = jwt_service.issue_access_token("user123", extra_claims=claims)
        
        decoded = jwt_service.verify_token(token)
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "admin"
        assert decoded["department"] == "engineering"
    
    @pytest.mark.asyncio
    async def test_jwt_token_expiration_handling(self, jwt_service):
        """Test JWT token expiration detection"""
        from dotmac.platform.auth.exceptions import TokenExpired
        
        # Generate token with very short expiry (1 second = 1/60 minutes)
        token = jwt_service.issue_access_token("user123", expires_in=1/60)
        
        # Wait for token to expire
        await asyncio.sleep(2)
        
        # Should raise TokenExpired
        with pytest.raises(TokenExpired):
            jwt_service.verify_token(token)
    
    def test_jwt_invalid_signature_detection(self, jwt_service):
        """Test detection of tokens with invalid signatures"""
        from dotmac.platform.auth.exceptions import InvalidSignature
        
        token = jwt_service.issue_access_token("user123")
        
        # Tamper with the token (change last character)
        tampered_token = token[:-1] + "X"
        
        with pytest.raises(InvalidSignature):
            jwt_service.verify_token(tampered_token)
    
    def test_jwt_malformed_token_rejection(self, jwt_service):
        """Test rejection of malformed JWT tokens"""
        from dotmac.platform.auth.exceptions import InvalidToken
        
        malformed_tokens = [
            "not.a.jwt",
            "invalid-token-format",
            "",
            "a.b",  # Too few segments
            "a.b.c.d.e"  # Too many segments
        ]
        
        for malformed_token in malformed_tokens:
            with pytest.raises(InvalidToken):
                jwt_service.verify_token(malformed_token)
    
    def test_jwt_token_without_required_claims(self, jwt_service):
        """Test handling of tokens missing required claims"""
        from dotmac.platform.auth.exceptions import InvalidToken
        
        # Create token without subject claim using the same secret
        payload = {"iat": int(time.time()), "exp": int(time.time()) + 3600}
        
        # Use the same secret as the JWT service
        token = jwt.encode(payload, jwt_service.secret, algorithm='HS256')
        
        with pytest.raises(InvalidToken):
            jwt_service.verify_token(token)
    
    # Key Rotation and Security Tests
    
    def test_jwt_key_rotation_scenario(self, jwt_service):
        """Test JWT behavior during key rotation"""
        from dotmac.platform.auth.exceptions import InvalidSignature
        
        # Generate token with original key
        token1 = jwt_service.issue_access_token("user123")
        
        # Simulate key rotation
        with patch.object(jwt_service, '_get_signing_key', return_value='new-secret-key'):
            with patch.object(jwt_service, '_get_verification_key', return_value='new-secret-key'):
                # Old token should fail with new key
                with pytest.raises(InvalidSignature):
                    jwt_service.verify_token(token1)
                
                # New token should work with new key
                token2 = jwt_service.issue_access_token("user456")
                decoded = jwt_service.verify_token(token2)
                assert decoded["sub"] == "user456"
    
    def test_jwt_algorithm_consistency(self, jwt_service):
        """Test JWT algorithm consistency"""
        from dotmac.platform.auth.exceptions import InvalidAlgorithm
        
        token = jwt_service.issue_access_token("user123")
        
        # Decode with different algorithm should fail
        with patch.object(jwt_service, 'algorithm', 'RS256'):
            with pytest.raises((InvalidAlgorithm, InvalidSignature)):
                jwt_service.verify_token(token)
    
    # Performance and Load Tests
    
    def test_jwt_generation_performance(self, jwt_service):
        """Test JWT generation performance under load"""
        start_time = time.time()
        
        # Generate 1000 tokens
        tokens = []
        for i in range(1000):
            token = jwt_service.issue_access_token(f"user{i}")
            tokens.append(token)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should generate 1000 tokens in reasonable time (< 5 seconds)
        assert generation_time < 5.0
        assert len(tokens) == 1000
        
        # All tokens should be unique
        assert len(set(tokens)) == 1000
    
    def test_jwt_validation_performance(self, jwt_service):
        """Test JWT validation performance under load"""
        # Pre-generate tokens
        tokens = [jwt_service.issue_access_token(f"user{i}") for i in range(1000)]
        
        start_time = time.time()
        
        # Validate all tokens
        for token in tokens:
            decoded = jwt_service.verify_token(token)
            assert decoded["sub"].startswith("user")
        
        end_time = time.time()
        validation_time = end_time - start_time
        
        # Should validate 1000 tokens in reasonable time (< 3 seconds)
        assert validation_time < 3.0
    
    def test_jwt_concurrent_operations(self, jwt_service):
        """Test JWT operations under concurrent access"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def worker(worker_id):
            try:
                # Each worker generates and validates tokens
                for i in range(100):
                    token = jwt_service.issue_access_token(f"worker{worker_id}_user{i}")
                    decoded = jwt_service.verify_token(token)
                    assert decoded["sub"] == f"worker{worker_id}_user{i}"
                
                results.put(f"worker{worker_id}_success")
            except Exception as e:
                errors.put(f"worker{worker_id}_error: {e}")
        
        # Start 10 concurrent workers
        threads = []
        for worker_id in range(10):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert results.qsize() == 10  # All workers succeeded
        assert errors.empty()  # No errors occurred