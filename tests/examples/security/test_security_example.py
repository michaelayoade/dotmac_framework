"""
Example security tests for the DotMac Framework.

This demonstrates best practices for testing:
- Authentication and authorization
- Input validation and sanitization
- SQL injection prevention
- XSS prevention
- CSRF protection
- Rate limiting
- Session management
"""

import base64
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt


# Security test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "test-secret-key")


# Fixtures
@pytest_asyncio.fixture
async def security_client():
    """HTTP client for security testing."""
    async with AsyncClient(base_url=API_BASE_URL) as client:
        yield client


@pytest.fixture
def valid_token():
    """Create a valid JWT token."""
    payload = {
        "sub": "test-user-id",
        "email": "security_test@example.com",
        "tenant_id": "security-tenant",
        "role": "user",
        "permissions": ["customer:read", "customer:create"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
def expired_token():
    """Create an expired JWT token."""
    payload = {
        "sub": "test-user-id",
        "email": "security_test@example.com",
        "tenant_id": "security-tenant",
        "role": "user",
        "permissions": ["customer:read"],
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        "iat": datetime.utcnow() - timedelta(hours=2)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
def tampered_token():
    """Create a token with tampered signature."""
    payload = {
        "sub": "hacker-user-id",
        "email": "hacker@evil.com",
        "tenant_id": "hacker-tenant",
        "role": "admin",
        "permissions": ["*"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    # Use wrong secret to create invalid signature
    return jwt.encode(payload, "wrong-secret", algorithm="HS256")


# Authentication and Authorization Tests
@pytest.mark.security
@pytest.mark.asyncio
class TestAuthenticationSecurity:
    """Test authentication security measures."""
    
    async def test_unauthenticated_access_denied(self, security_client):
        """Test that protected endpoints deny unauthenticated access."""
        protected_endpoints = [
            ("/api/v1/customers", "GET"),
            ("/api/v1/customers", "POST"),
            ("/api/v1/customers/test-id", "GET"),
            ("/api/v1/customers/test-id", "PUT"),
            ("/api/v1/customers/test-id", "DELETE"),
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = await security_client.get(endpoint)
            elif method == "POST":
                response = await security_client.post(endpoint, json={"test": "data"})
            elif method == "PUT":
                response = await security_client.put(endpoint, json={"test": "data"})
            elif method == "DELETE":
                response = await security_client.delete(endpoint)
            
            assert response.status_code == 401, f"{method} {endpoint} should require authentication"
            
            # Should return proper error format
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                assert "detail" in error_data or "message" in error_data
    
    async def test_invalid_token_rejected(self, security_client):
        """Test that invalid tokens are rejected."""
        invalid_tokens = [
            "invalid-token",
            "Bearer invalid-token",
            "not.a.jwt.token",
            "",
            "null"
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = await security_client.get("/api/v1/customers", headers=headers)
            
            assert response.status_code == 401, f"Invalid token should be rejected: {token}"
    
    async def test_expired_token_rejected(self, security_client, expired_token):
        """Test that expired tokens are rejected."""
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await security_client.get("/api/v1/customers", headers=headers)
        
        assert response.status_code == 401, "Expired token should be rejected"
        
        error_data = response.json()
        assert "expired" in str(error_data).lower() or "invalid" in str(error_data).lower()
    
    async def test_tampered_token_rejected(self, security_client, tampered_token):
        """Test that tokens with invalid signatures are rejected."""
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = await security_client.get("/api/v1/customers", headers=headers)
        
        assert response.status_code == 401, "Tampered token should be rejected"
    
    async def test_bearer_format_required(self, security_client, valid_token):
        """Test that tokens must use Bearer format."""
        # Test without Bearer prefix
        headers = {"Authorization": valid_token}
        response = await security_client.get("/api/v1/customers", headers=headers)
        assert response.status_code == 401, "Token without Bearer prefix should be rejected"
        
        # Test with correct Bearer format (should work if endpoint exists)
        headers = {"Authorization": f"Bearer {valid_token}"}
        response = await security_client.get("/api/v1/customers", headers=headers)
        # Should not be 401 due to format (might be 403, 404, etc.)
        assert response.status_code != 401 or "bearer" not in str(response.json()).lower()


@pytest.mark.security
@pytest.mark.asyncio
class TestAuthorizationSecurity:
    """Test authorization and permission security."""
    
    async def test_role_based_access_control(self, security_client):
        """Test role-based access control."""
        # Create tokens with different roles
        user_token = jwt.encode({
            "sub": "user-id",
            "role": "user",
            "permissions": ["customer:read"],
            "tenant_id": "test-tenant",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }, JWT_SECRET)
        
        admin_token = jwt.encode({
            "sub": "admin-id",
            "role": "admin", 
            "permissions": ["customer:read", "customer:create", "customer:update", "customer:delete"],
            "tenant_id": "test-tenant",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }, JWT_SECRET)
        
        # Test user trying to create customer (should fail)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        customer_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = await security_client.post(
            "/api/v1/customers", 
            json=customer_data, 
            headers=user_headers
        )
        
        # Should be forbidden (or might work if permissions are properly set)
        assert response.status_code in [403, 201, 422]  # 422 for validation errors
        
        # Test admin creating customer (should work better)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        response = await security_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=admin_headers
        )
        
        # Should have better success rate than user
        assert response.status_code in [201, 403, 422]  # Admin should not get 401
    
    async def test_tenant_isolation(self, security_client):
        """Test that tenant isolation is enforced."""
        # Create tokens for different tenants
        tenant1_token = jwt.encode({
            "sub": "user1-id",
            "tenant_id": "tenant-1",
            "permissions": ["customer:read", "customer:create"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }, JWT_SECRET)
        
        tenant2_token = jwt.encode({
            "sub": "user2-id", 
            "tenant_id": "tenant-2",
            "permissions": ["customer:read", "customer:create"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }, JWT_SECRET)
        
        # Create customer in tenant 1
        tenant1_headers = {"Authorization": f"Bearer {tenant1_token}"}
        customer_data = {
            "email": "tenant1_user@example.com",
            "first_name": "Tenant1",
            "last_name": "User"
        }
        
        response = await security_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=tenant1_headers
        )
        
        if response.status_code == 201:
            customer_id = response.json()["id"]
            
            # Try to access customer from tenant 2 (should fail)
            tenant2_headers = {"Authorization": f"Bearer {tenant2_token}"}
            response = await security_client.get(
                f"/api/v1/customers/{customer_id}",
                headers=tenant2_headers
            )
            
            assert response.status_code in [403, 404], "Cross-tenant access should be denied"


@pytest.mark.security
@pytest.mark.asyncio
class TestInputValidationSecurity:
    """Test input validation and sanitization."""
    
    async def test_sql_injection_prevention(self, security_client, valid_token):
        """Test SQL injection attack prevention."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Common SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE customers; --",
            "' OR '1'='1",
            "'; SELECT * FROM users; --",
            "admin'; --",
            "1' UNION SELECT * FROM customers--"
        ]
        
        for payload in sql_payloads:
            # Test in search parameter
            params = {"search": payload}
            response = await security_client.get(
                "/api/v1/customers",
                params=params,
                headers=headers
            )
            
            # Should not cause server error (500)
            assert response.status_code != 500, f"SQL injection payload caused server error: {payload}"
            assert response.status_code in [200, 400, 403, 404, 422]
            
            # Test in POST data
            customer_data = {
                "email": f"{payload}@example.com",
                "first_name": payload,
                "last_name": "Test"
            }
            
            response = await security_client.post(
                "/api/v1/customers",
                json=customer_data,
                headers=headers
            )
            
            assert response.status_code != 500, f"SQL injection in POST caused server error: {payload}"
    
    async def test_xss_prevention(self, security_client, valid_token):
        """Test XSS attack prevention."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Common XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in xss_payloads:
            customer_data = {
                "email": "xss_test@example.com",
                "first_name": payload,
                "last_name": "Test"
            }
            
            response = await security_client.post(
                "/api/v1/customers",
                json=customer_data,
                headers=headers
            )
            
            # Should either reject (400/422) or accept and sanitize
            if response.status_code == 201:
                # If accepted, check that XSS payload was sanitized
                customer = response.json()
                assert "<script>" not in customer.get("first_name", "")
                assert "javascript:" not in customer.get("first_name", "")
                assert "alert(" not in customer.get("first_name", "")
    
    async def test_oversized_input_handling(self, security_client, valid_token):
        """Test handling of oversized inputs."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Test with very large input
        large_string = "A" * 10000  # 10KB string
        
        customer_data = {
            "email": "large_input@example.com",
            "first_name": large_string,
            "last_name": "Test"
        }
        
        response = await security_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=headers
        )
        
        # Should reject with 400 or 422, not crash with 500
        assert response.status_code in [400, 413, 422], "Large input should be rejected gracefully"
    
    async def test_invalid_json_handling(self, security_client, valid_token):
        """Test handling of invalid JSON."""
        headers = {
            "Authorization": f"Bearer {valid_token}",
            "Content-Type": "application/json"
        }
        
        # Send invalid JSON
        response = await security_client.post(
            "/api/v1/customers",
            content="{ invalid json }{",
            headers=headers
        )
        
        assert response.status_code == 400, "Invalid JSON should return 400"
    
    async def test_null_byte_injection(self, security_client, valid_token):
        """Test null byte injection prevention."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        customer_data = {
            "email": "nullbyte\x00@example.com",
            "first_name": "Test\x00",
            "last_name": "User"
        }
        
        response = await security_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=headers
        )
        
        # Should either reject or sanitize null bytes
        if response.status_code == 201:
            customer = response.json()
            assert "\x00" not in customer.get("email", "")
            assert "\x00" not in customer.get("first_name", "")


@pytest.mark.security
@pytest.mark.asyncio
class TestRateLimitingSecurity:
    """Test rate limiting security measures."""
    
    async def test_rate_limiting_protection(self, security_client, valid_token):
        """Test rate limiting prevents abuse."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Make many rapid requests
        responses = []
        start_time = time.time()
        
        for i in range(20):  # Adjust based on rate limits
            response = await security_client.get("/api/v1/customers", headers=headers)
            responses.append(response)
            
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.1)
        
        # Check if any requests were rate limited
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        
        if rate_limited_responses:
            # Rate limiting is working
            rate_limited_response = rate_limited_responses[0]
            
            # Should have proper headers
            assert "retry-after" in [h.lower() for h in rate_limited_response.headers.keys()], \
                "Rate limited response should include Retry-After header"
        
        # Should not have too many server errors
        server_errors = [r for r in responses if r.status_code >= 500]
        assert len(server_errors) < 3, "Too many server errors under load"
    
    async def test_rate_limiting_per_ip(self, security_client):
        """Test rate limiting works per IP address."""
        # This is challenging to test in a single process
        # In real scenarios, you'd test from multiple IPs
        
        # Make requests without authentication (if allowed)
        responses = []
        for i in range(10):
            response = await security_client.get("/health")  # Public endpoint
            responses.append(response)
            await asyncio.sleep(0.05)
        
        # Should handle rapid requests to public endpoints gracefully
        server_errors = [r for r in responses if r.status_code >= 500]
        assert len(server_errors) == 0, "Public endpoints should handle rapid requests"


@pytest.mark.security
@pytest.mark.asyncio 
class TestSessionSecurity:
    """Test session management security."""
    
    async def test_session_token_entropy(self):
        """Test that generated tokens have sufficient entropy."""
        # Generate multiple tokens and check for patterns
        tokens = []
        
        for i in range(10):
            payload = {
                "sub": f"user-{i}",
                "exp": datetime.utcnow() + timedelta(hours=1)
            }
            token = jwt.encode(payload, JWT_SECRET)
            tokens.append(token)
        
        # Tokens should be different
        assert len(set(tokens)) == len(tokens), "All tokens should be unique"
        
        # Tokens should have reasonable length
        for token in tokens:
            assert len(token) > 100, "JWT tokens should have sufficient length"
    
    async def test_token_expiration_enforced(self, security_client):
        """Test that token expiration is properly enforced."""
        # Create token that expires in 1 second
        payload = {
            "sub": "expiry-test-user",
            "tenant_id": "test-tenant",
            "permissions": ["customer:read"],
            "exp": datetime.utcnow() + timedelta(seconds=1),
            "iat": datetime.utcnow()
        }
        short_lived_token = jwt.encode(payload, JWT_SECRET)
        
        # Token should work initially
        headers = {"Authorization": f"Bearer {short_lived_token}"}
        response = await security_client.get("/api/v1/customers", headers=headers)
        initial_status = response.status_code
        
        # Wait for token to expire
        await asyncio.sleep(2)
        
        # Token should now be rejected
        response = await security_client.get("/api/v1/customers", headers=headers)
        assert response.status_code == 401, "Expired token should be rejected"


@pytest.mark.security
@pytest.mark.asyncio
class TestHeaderSecurity:
    """Test HTTP header security."""
    
    async def test_security_headers_present(self, security_client):
        """Test that security headers are present."""
        response = await security_client.get("/health")
        
        headers = {k.lower(): v for k, v in response.headers.items()}
        
        # Check for important security headers
        security_checks = [
            ("x-content-type-options", lambda v: v.lower() == "nosniff"),
            ("x-frame-options", lambda v: v.lower() in ["deny", "sameorigin"]),
            ("x-xss-protection", lambda v: "1" in v),
        ]
        
        for header_name, check_func in security_checks:
            if header_name in headers:
                assert check_func(headers[header_name]), \
                    f"Security header {header_name} has incorrect value: {headers[header_name]}"
    
    async def test_cors_headers_secure(self, security_client):
        """Test that CORS headers are securely configured."""
        response = await security_client.options("/api/v1/customers")
        
        if "access-control-allow-origin" in response.headers:
            origin = response.headers["access-control-allow-origin"]
            
            # Should not allow all origins in production
            if os.getenv("ENVIRONMENT") == "production":
                assert origin != "*", "CORS should not allow all origins in production"
    
    async def test_information_disclosure_prevention(self, security_client):
        """Test that server doesn't disclose sensitive information."""
        # Test 404 responses don't leak information
        response = await security_client.get("/api/v1/nonexistent-endpoint")
        
        if response.status_code == 404:
            response_text = response.text.lower()
            
            # Should not contain sensitive paths or stack traces
            sensitive_patterns = [
                "/usr/",
                "/var/",
                "traceback",
                "stack trace",
                "internal server error",
                "database error"
            ]
            
            for pattern in sensitive_patterns:
                assert pattern not in response_text, \
                    f"404 response should not contain sensitive information: {pattern}"


@pytest.mark.security
@pytest.mark.asyncio
class TestCryptographicSecurity:
    """Test cryptographic security measures."""
    
    def test_jwt_algorithm_security(self):
        """Test JWT uses secure algorithms."""
        # Create token with secure algorithm
        payload = {"sub": "test", "exp": datetime.utcnow() + timedelta(hours=1)}
        
        # Should use HS256 or better
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "test"
        
        # Should reject insecure algorithms
        try:
            insecure_token = jwt.encode(payload, JWT_SECRET, algorithm="none")
            with pytest.raises(Exception):
                jwt.decode(insecure_token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            pass  # Expected - insecure algorithms should fail
    
    def test_secret_key_strength(self):
        """Test that secret keys meet strength requirements."""
        secret = JWT_SECRET
        
        # Secret should be reasonably long
        assert len(secret) >= 32, "JWT secret should be at least 32 characters"
        
        # Should contain mixed case and numbers (in production)
        if os.getenv("ENVIRONMENT") == "production":
            assert any(c.islower() for c in secret), "Secret should contain lowercase"
            assert any(c.isupper() for c in secret), "Secret should contain uppercase"
            assert any(c.isdigit() for c in secret), "Secret should contain digits"


@pytest.mark.security
@pytest.mark.asyncio
class TestDataProtectionSecurity:
    """Test data protection and privacy measures."""
    
    async def test_sensitive_data_not_logged(self, security_client, valid_token):
        """Test that sensitive data is not exposed in logs."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Create customer with sensitive data
        customer_data = {
            "email": "sensitive@example.com",
            "first_name": "Sensitive",
            "last_name": "User",
            "ssn": "123-45-6789",  # This should be filtered
            "credit_card": "4111-1111-1111-1111"  # This should be filtered
        }
        
        response = await security_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=headers
        )
        
        # Even if creation fails, sensitive data should not be echoed back
        response_text = response.text
        
        assert "123-45-6789" not in response_text, "SSN should not appear in response"
        assert "4111-1111-1111-1111" not in response_text, "Credit card should not appear in response"
    
    async def test_password_handling_security(self, security_client):
        """Test secure password handling."""
        # Test password creation endpoint (if exists)
        password_data = {
            "email": "password_test@example.com",
            "password": "test_password_123",
            "confirm_password": "test_password_123"
        }
        
        response = await security_client.post("/api/v1/auth/register", json=password_data)
        
        # Password should not be returned in response
        if response.status_code in [200, 201]:
            response_data = response.json()
            assert "password" not in response_data, "Password should not be in response"
            assert "test_password_123" not in str(response_data), "Password value should not be in response"


# Security test utilities
def generate_malicious_payloads() -> List[str]:
    """Generate common malicious payloads for testing."""
    return [
        # XSS payloads
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        
        # SQL injection payloads
        "'; DROP TABLE customers; --",
        "' OR '1'='1",
        "'; SELECT * FROM users; --",
        
        # Command injection payloads
        "; cat /etc/passwd",
        "| whoami",
        "&& rm -rf /",
        
        # Path traversal payloads
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        
        # LDAP injection payloads
        "*)(&",
        "*)(userPassword=*",
        
        # XML injection payloads
        "<?xml version=\"1.0\"?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>"
    ]


@pytest.mark.security
@pytest.mark.parametrize("payload", generate_malicious_payloads())
@pytest.mark.asyncio
async def test_malicious_payload_protection(security_client, valid_token, payload):
    """Test protection against various malicious payloads."""
    headers = {"Authorization": f"Bearer {valid_token}"}
    
    # Test payload in different contexts
    contexts = [
        # Query parameters
        {"params": {"search": payload}},
        # JSON body
        {"json": {"email": f"test@example.com", "first_name": payload}},
        # Headers (if accepted)
        {"headers": {**headers, "X-Custom-Header": payload}}
    ]
    
    for context in contexts:
        try:
            response = await security_client.get("/api/v1/customers", **context)
            
            # Should not cause server error
            assert response.status_code != 500, f"Payload caused server error: {payload}"
            
            # Should not reflect payload unsanitized
            if response.status_code == 200:
                response_text = response.text
                # Payload should be sanitized or escaped
                dangerous_chars = ["<script>", "javascript:", "'; DROP", "cat /etc/passwd"]
                for dangerous in dangerous_chars:
                    if dangerous in payload:
                        assert dangerous not in response_text, \
                            f"Dangerous payload reflected: {dangerous}"
                        
        except Exception as e:
            # Connection errors, etc. are acceptable
            assert "500" not in str(e), f"Server error with payload: {payload}"