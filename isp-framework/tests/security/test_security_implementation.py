"""Security tests for DotMac ISP Framework.

Tests comprehensive security features including:
- Authentication and authorization
- Input validation and sanitization  
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Data encryption
- Audit logging
- Multi-tenant security isolation
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import jwt
import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.testclient import TestClient

from dotmac_isp.core.security import (
    SecurityManager, AuthenticationService, AuthorizationService,
    RateLimiter, InputSanitizer, AuditLogger
)
from dotmac_isp.core.encryption import EncryptionService
from dotmac_isp.modules.identity.models import User, UserRole, UserSession
from dotmac_isp.core.exceptions import (
    AuthenticationError, AuthorizationError, SecurityViolationError,
    RateLimitExceededError
)


@pytest.mark.security
@pytest.mark.authentication
class TestAuthenticationSecurity:
    """Test authentication security measures."""
    
    async def test_password_hashing_strength(self, db_session: AsyncSession):
        """Test password hashing uses strong algorithms."""
        auth_service = AuthenticationService(db_session)
        
        test_password = "TestPassword123!"
        
        # Hash password
        hashed_password = await auth_service.hash_password(test_password)
        
        # Verify hash properties
        assert len(hashed_password) >= 60  # bcrypt produces 60-char hashes
        assert hashed_password.startswith('$2b$') or hashed_password.startswith('$2a$')  # bcrypt identifier
        assert test_password not in hashed_password  # Plain password not in hash
        
        # Verify password verification works
        is_valid = await auth_service.verify_password(test_password, hashed_password)
        assert is_valid is True
        
        # Verify wrong password fails
        wrong_password = "WrongPassword123!"
        is_invalid = await auth_service.verify_password(wrong_password, hashed_password)
        assert is_invalid is False
        
        # Test hash is different each time (salt variations)
        hash2 = await auth_service.hash_password(test_password)
        assert hashed_password != hash2  # Different salts produce different hashes
    
    async def test_jwt_token_security(self, db_session: AsyncSession):
        """Test JWT token generation and validation security."""
        auth_service = AuthenticationService(db_session)
        
        user_data = {
            "user_id": "user_123",
            "username": "testuser",
            "email": "test@example.com", 
            "role": "customer",
            "tenant_id": "tenant_001"
        }
        
        # Generate JWT token
        token = await auth_service.generate_jwt_token(user_data, expires_in=3600)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
        
        # Decode and verify token
        decoded_payload = await auth_service.verify_jwt_token(token)
        
        assert decoded_payload["user_id"] == "user_123"
        assert decoded_payload["username"] == "testuser"
        assert decoded_payload["role"] == "customer"
        assert decoded_payload["tenant_id"] == "tenant_001"
        assert "exp" in decoded_payload  # Expiration time
        assert "iat" in decoded_payload  # Issued at time
        
        # Test token expiration
        expired_token = await auth_service.generate_jwt_token(user_data, expires_in=1)
        await asyncio.sleep(2)  # Wait for token to expire
        
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.verify_jwt_token(expired_token)
        
        assert "expired" in str(exc_info.value).lower()
        
        # Test malformed token
        malformed_token = "invalid.jwt.token"
        
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.verify_jwt_token(malformed_token)
        
        assert "invalid token" in str(exc_info.value).lower()
    
    async def test_session_security_measures(self, db_session: AsyncSession):
        """Test session security and management."""
        auth_service = AuthenticationService(db_session)
        
        user_id = "test_user_001"
        
        # Create session
        session = await auth_service.create_session(
            user_id=user_id,
            user_agent="Test Browser/1.0",
            ip_address="192.168.1.100",
            expires_in=3600
        )
        
        # Verify session properties
        assert session.user_id == user_id
        assert session.ip_address == "192.168.1.100"
        assert session.user_agent == "Test Browser/1.0"
        assert session.expires_at > datetime.utcnow()
        assert len(session.session_token) >= 32  # Secure session token
        
        # Test session validation
        is_valid = await auth_service.validate_session(session.session_token, "192.168.1.100")
        assert is_valid is True
        
        # Test IP address validation (session hijacking prevention)
        different_ip = await auth_service.validate_session(session.session_token, "192.168.1.200")
        assert different_ip is False  # Should fail IP validation
        
        # Test session expiration
        expired_session = await auth_service.create_session(
            user_id=user_id,
            user_agent="Test Browser/1.0",
            ip_address="192.168.1.100",
            expires_in=1  # 1 second
        )
        
        await asyncio.sleep(2)
        
        is_expired = await auth_service.validate_session(expired_session.session_token, "192.168.1.100")
        assert is_expired is False
        
        # Test session revocation
        await auth_service.revoke_session(session.session_token)
        
        is_revoked = await auth_service.validate_session(session.session_token, "192.168.1.100")
        assert is_revoked is False
    
    async def test_brute_force_protection(self, async_client, db_session: AsyncSession):
        """Test brute force attack protection."""
        auth_service = AuthenticationService(db_session)
        
        username = "bruteforce_target"
        wrong_password = "wrong_password"
        
        # Mock user for brute force testing
        with patch.object(auth_service, '_get_user_by_username') as mock_get_user:
            mock_user = MagicMock()
            mock_user.id = "user_123"
            mock_user.username = username
            mock_user.is_locked = False
            mock_user.failed_login_attempts = 0
            mock_get_user.return_value = mock_user
            
            # Simulate multiple failed login attempts
            max_attempts = 5
            for attempt in range(max_attempts + 1):
                login_data = {
                    "username": username,
                    "password": wrong_password,
                    "ip_address": "192.168.1.100"
                }
                
                if attempt < max_attempts:
                    # First few attempts should fail but not lock
                    with pytest.raises(AuthenticationError) as exc_info:
                        await auth_service.authenticate_user(login_data)
                    
                    if attempt < max_attempts - 1:
                        assert "invalid credentials" in str(exc_info.value).lower()
                        assert mock_user.failed_login_attempts == attempt + 1
                else:
                    # Final attempt should trigger account lock
                    with pytest.raises(AuthenticationError) as exc_info:
                        await auth_service.authenticate_user(login_data)
                    
                    assert "account locked" in str(exc_info.value).lower()
                    assert mock_user.is_locked is True


@pytest.mark.security
@pytest.mark.authorization
class TestAuthorizationSecurity:
    """Test authorization and access control security."""
    
    async def test_role_based_access_control(self, db_session: AsyncSession):
        """Test role-based access control enforcement."""
        auth_service = AuthorizationService(db_session)
        
        # Define test scenarios
        access_tests = [
            {
                'user_role': UserRole.CUSTOMER,
                'resource': 'customer_data',
                'action': 'read',
                'resource_owner': 'user_123',
                'user_id': 'user_123',
                'expected': True  # Customer can read own data
            },
            {
                'user_role': UserRole.CUSTOMER,
                'resource': 'customer_data',
                'action': 'read',
                'resource_owner': 'user_456',  # Different user
                'user_id': 'user_123',
                'expected': False  # Customer cannot read other's data
            },
            {
                'user_role': UserRole.ADMIN,
                'resource': 'customer_data',
                'action': 'read',
                'resource_owner': 'user_456',
                'user_id': 'user_admin',
                'expected': True  # Admin can read all data
            },
            {
                'user_role': UserRole.SUPPORT,
                'resource': 'support_tickets',
                'action': 'update',
                'resource_owner': None,
                'user_id': 'user_support',
                'expected': True  # Support can update tickets
            },
            {
                'user_role': UserRole.CUSTOMER,
                'resource': 'admin_panel',
                'action': 'access',
                'resource_owner': None,
                'user_id': 'user_123',
                'expected': False  # Customer cannot access admin panel
            }
        ]
        
        for test_case in access_tests:
            user_context = {
                'user_id': test_case['user_id'],
                'role': test_case['user_role'],
                'tenant_id': 'tenant_001'
            }
            
            resource_context = {
                'resource_type': test_case['resource'],
                'action': test_case['action'],
                'resource_owner': test_case['resource_owner'],
                'tenant_id': 'tenant_001'
            }
            
            has_access = await auth_service.check_permission(user_context, resource_context)
            
            assert has_access == test_case['expected'], \
                f"Access test failed for {test_case['user_role']} accessing {test_case['resource']}"
    
    async def test_multi_tenant_access_isolation(self, db_session: AsyncSession):
        """Test multi-tenant access isolation."""
        auth_service = AuthorizationService(db_session)
        
        # User from tenant_001
        tenant1_user = {
            'user_id': 'user_t1_001',
            'role': UserRole.ADMIN,
            'tenant_id': 'tenant_001'
        }
        
        # Resource from tenant_002
        tenant2_resource = {
            'resource_type': 'customer_data',
            'action': 'read',
            'resource_owner': 'customer_t2_001',
            'tenant_id': 'tenant_002'
        }
        
        # Even admin should not access cross-tenant resources
        has_cross_tenant_access = await auth_service.check_permission(tenant1_user, tenant2_resource)
        assert has_cross_tenant_access is False
        
        # Same resource in same tenant should be accessible
        tenant1_resource = {
            **tenant2_resource,
            'tenant_id': 'tenant_001',
            'resource_owner': 'customer_t1_001'
        }
        
        has_same_tenant_access = await auth_service.check_permission(tenant1_user, tenant1_resource)
        assert has_same_tenant_access is True
    
    async def test_api_endpoint_authorization(self, async_client, auth_headers):
        """Test API endpoint authorization enforcement."""
        
        # Test unauthorized access (no auth header)
        no_auth_response = await async_client.get("/api/v1/admin/users")
        assert no_auth_response.status_code == 401
        
        # Test insufficient privileges
        customer_headers = {"Authorization": "Bearer customer_token_mock"}
        
        with patch('dotmac_isp.core.security.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                'user_id': 'customer_123',
                'role': 'customer',
                'tenant_id': 'tenant_001'
            }
            
            insufficient_response = await async_client.get(
                "/api/v1/admin/users", 
                headers=customer_headers
            )
            assert insufficient_response.status_code == 403
        
        # Test sufficient privileges
        admin_headers = {"Authorization": "Bearer admin_token_mock"}
        
        with patch('dotmac_isp.core.security.verify_jwt_token') as mock_verify:
            mock_verify.return_value = {
                'user_id': 'admin_123',
                'role': 'admin',
                'tenant_id': 'tenant_001'
            }
            
            with patch('dotmac_isp.modules.identity.services.UserService.list_users') as mock_list:
                mock_list.return_value = []
                
                authorized_response = await async_client.get(
                    "/api/v1/admin/users",
                    headers=admin_headers
                )
                assert authorized_response.status_code == 200


@pytest.mark.security
@pytest.mark.input_validation
class TestInputValidationSecurity:
    """Test input validation and sanitization security."""
    
    async def test_sql_injection_prevention(self, db_session: AsyncSession):
        """Test SQL injection attack prevention."""
        
        # Malicious SQL injection payloads
        injection_payloads = [
            "'; DROP TABLE customers; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users WHERE '1'='1",
            "'; INSERT INTO users (username) VALUES ('hacker'); --",
            "1'; UPDATE customers SET email='hacked@evil.com'; --"
        ]
        
        for payload in injection_payloads:
            # Test parameterized query (safe)
            safe_query = text("SELECT * FROM customers WHERE customer_number = :customer_number")
            
            try:
                # This should not execute any malicious SQL
                result = await db_session.execute(safe_query, {"customer_number": payload})
                rows = result.fetchall()
                # Should return empty result, not execute injection
                assert len(rows) == 0
            except Exception as e:
                # If any database error occurs, it should be a parameter error, not SQL execution
                assert "syntax error" not in str(e).lower()
                assert "drop table" not in str(e).lower()
    
    async def test_xss_payload_sanitization(self, async_client):
        """Test XSS payload sanitization in API inputs."""
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "<svg onload=alert('XSS')>",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;"
        ]
        
        for payload in xss_payloads:
            # Test customer creation with XSS payload
            customer_data = {
                "first_name": payload,  # XSS in first name
                "last_name": "Test",
                "email_primary": "test@example.com",
                "phone_primary": "555-0123"
            }
            
            # Should either sanitize the input or reject it
            response = await async_client.post(
                "/api/v1/customers",
                json=customer_data,
                headers={"Authorization": "Bearer mock_admin_token"}
            )
            
            if response.status_code == 201:
                # If accepted, verify XSS was sanitized
                created_customer = response.json()
                sanitized_name = created_customer["first_name"]
                
                # Should not contain script tags or javascript
                assert "<script>" not in sanitized_name.lower()
                assert "javascript:" not in sanitized_name.lower()
                assert "alert(" not in sanitized_name
                assert "<img" not in sanitized_name.lower()
                assert "<svg" not in sanitized_name.lower()
            else:
                # If rejected, should be 400 Bad Request due to validation
                assert response.status_code == 400
    
    async def test_command_injection_prevention(self, async_client, auth_headers):
        """Test command injection prevention in system operations."""
        
        command_injection_payloads = [
            "; cat /etc/passwd",
            "| ls -la /",
            "&& rm -rf /tmp/*",
            "`whoami`",
            "$(id)",
            "; ping -c 10 evil.com",
        ]
        
        for payload in command_injection_payloads:
            # Test network device configuration (potential command injection point)
            device_config = {
                "device_name": f"Router{payload}",  # Injection in device name
                "ip_address": "192.168.1.1",
                "snmp_community": f"public{payload}",  # Injection in SNMP community
                "location": "Test Lab"
            }
            
            response = await async_client.post(
                "/api/v1/network/devices",
                json=device_config,
                headers=auth_headers
            )
            
            # Should reject dangerous input or sanitize it
            if response.status_code == 201:
                created_device = response.json()
                
                # Verify command injection characters were removed/escaped
                assert "; cat" not in created_device["device_name"]
                assert "| ls" not in created_device["device_name"]
                assert "&& rm" not in created_device["device_name"]
                assert "`whoami`" not in created_device["snmp_community"]
                assert "$(id)" not in created_device["snmp_community"]
            else:
                # Should be validation error
                assert response.status_code in [400, 422]
    
    async def test_file_upload_security(self, async_client, auth_headers):
        """Test file upload security validation."""
        
        # Test malicious file uploads
        malicious_files = [
            {
                'filename': 'malicious.exe',
                'content': b'MZ\x90\x00\x03\x00\x00\x00',  # PE header (Windows executable)
                'content_type': 'application/octet-stream'
            },
            {
                'filename': 'script.php',
                'content': b'<?php system($_GET["cmd"]); ?>',
                'content_type': 'application/x-httpd-php'
            },
            {
                'filename': 'config.yaml',
                'content': b'malicious: !!python/object/apply:os.system ["rm -rf /"]',
                'content_type': 'text/yaml'
            },
            {
                'filename': '../../../etc/passwd',  # Directory traversal
                'content': b'root:x:0:0:root:/root:/bin/bash',
                'content_type': 'text/plain'
            }
        ]
        
        for malicious_file in malicious_files:
            # Simulate file upload for configuration import
            files = {
                'config_file': (
                    malicious_file['filename'], 
                    malicious_file['content'], 
                    malicious_file['content_type']
                )
            }
            
            response = await async_client.post(
                "/api/v1/admin/import-config",
                files=files,
                headers=auth_headers
            )
            
            # Should reject malicious file types
            assert response.status_code in [400, 422, 415]  # Bad request or unsupported media type
            
            error_response = response.json()
            error_message = str(error_response).lower()
            
            # Should indicate file type or security issue
            security_keywords = ['file type', 'not allowed', 'security', 'invalid', 'dangerous']
            assert any(keyword in error_message for keyword in security_keywords)


@pytest.mark.security
@pytest.mark.rate_limiting
class TestRateLimitingSecurity:
    """Test rate limiting and DoS protection."""
    
    async def test_api_rate_limiting(self, async_client, auth_headers):
        """Test API endpoint rate limiting."""
        
        rate_limiter = RateLimiter()
        
        # Configure rate limit: 10 requests per minute
        endpoint = "/api/v1/customers"
        client_ip = "192.168.1.100"
        rate_limit = 10
        time_window = 60  # seconds
        
        # Make requests up to the limit
        for i in range(rate_limit):
            allowed = await rate_limiter.is_allowed(
                key=f"{client_ip}:{endpoint}",
                limit=rate_limit,
                window=time_window
            )
            assert allowed is True, f"Request {i+1} should be allowed"
        
        # Next request should be rate limited
        rate_limited = await rate_limiter.is_allowed(
            key=f"{client_ip}:{endpoint}",
            limit=rate_limit,
            window=time_window
        )
        assert rate_limited is False, "Request should be rate limited"
        
        # Verify rate limit exception is raised
        with pytest.raises(RateLimitExceededError) as exc_info:
            await rate_limiter.check_rate_limit(
                key=f"{client_ip}:{endpoint}",
                limit=rate_limit,
                window=time_window
            )
        
        assert "rate limit exceeded" in str(exc_info.value).lower()
    
    async def test_login_attempt_rate_limiting(self, async_client):
        """Test login attempt rate limiting."""
        
        username = "ratelimit_test"
        client_ip = "192.168.1.200"
        
        # Simulate rapid login attempts
        login_data = {
            "username": username,
            "password": "wrong_password",
            "ip_address": client_ip
        }
        
        # Allow 3 failed attempts per minute
        max_attempts = 3
        successful_attempts = 0
        rate_limited_attempts = 0
        
        for attempt in range(10):  # Try 10 attempts
            response = await async_client.post(
                "/api/v1/auth/login",
                json=login_data
            )
            
            if response.status_code == 401:
                # Normal authentication failure
                successful_attempts += 1
            elif response.status_code == 429:
                # Rate limited
                rate_limited_attempts += 1
                
                error_data = response.json()
                assert "rate limit" in error_data["detail"].lower()
                assert "retry after" in str(error_data).lower()
            else:
                pytest.fail(f"Unexpected status code: {response.status_code}")
        
        # Should have limited attempts after initial failures
        assert successful_attempts <= max_attempts
        assert rate_limited_attempts > 0
    
    async def test_concurrent_request_limiting(self, async_client, auth_headers):
        """Test concurrent request limiting per user."""
        
        user_id = "concurrent_test_user"
        max_concurrent = 5
        
        async def make_request(request_id):
            """Simulate long-running request."""
            response = await async_client.get(
                f"/api/v1/customers?request_id={request_id}&delay=2",  # Simulate 2-second delay
                headers=auth_headers
            )
            return response.status_code
        
        # Start multiple concurrent requests
        tasks = []
        for i in range(max_concurrent + 3):  # Try more than allowed
            task = asyncio.create_task(make_request(i))
            tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful vs rejected requests
        successful_requests = sum(1 for result in results if result == 200)
        rejected_requests = sum(1 for result in results if result == 429)
        
        # Should limit concurrent requests
        assert successful_requests <= max_concurrent
        assert rejected_requests >= 3  # Excess requests should be rejected


@pytest.mark.security
@pytest.mark.encryption
class TestDataEncryptionSecurity:
    """Test data encryption and protection security."""
    
    async def test_sensitive_data_encryption(self, db_session: AsyncSession):
        """Test encryption of sensitive data fields."""
        
        encryption_service = EncryptionService()
        
        # Test encrypting sensitive customer data
        sensitive_data = {
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "bank_account": "987654321",
            "phone_number": "+1-555-123-4567"
        }
        
        encrypted_data = {}
        
        for field, value in sensitive_data.items():
            encrypted_value = await encryption_service.encrypt(value)
            encrypted_data[field] = encrypted_value
            
            # Verify encryption worked
            assert encrypted_value != value  # Should be different
            assert len(encrypted_value) > len(value)  # Should be longer due to encryption
            assert not value.encode() in encrypted_value  # Original value not visible
        
        # Test decryption
        for field, original_value in sensitive_data.items():
            encrypted_value = encrypted_data[field]
            decrypted_value = await encryption_service.decrypt(encrypted_value)
            
            assert decrypted_value == original_value
    
    async def test_data_at_rest_encryption(self, db_session: AsyncSession):
        """Test database data-at-rest encryption."""
        
        from dotmac_isp.modules.identity.models import Customer
        
        tenant_id = "encryption_test_tenant"
        
        # Create customer with sensitive data
        customer_data = {
            "id": "enc_test_customer",
            "customer_number": "ENC_CUST001",
            "first_name": "Encryption",
            "last_name": "Test",
            "email_primary": "encryption.test@example.com",
            "phone_primary": "+1-555-ENCRYPT",  # Sensitive data
            "ssn_encrypted": "123-45-6789",       # Should be encrypted
            "tenant_id": tenant_id,
            "created_by": "test_system"
        }
        
        # Mock encryption service for database integration
        with patch('dotmac_isp.core.encryption.EncryptionService.encrypt') as mock_encrypt:
            mock_encrypt.return_value = "encrypted_phone_data"
            
            customer = Customer(**customer_data)
            db_session.add(customer)
            await db_session.commit()
            
            # Verify encryption was called for sensitive fields
            mock_encrypt.assert_called()
        
        # Verify data is encrypted in database
        raw_query = text("SELECT phone_primary FROM customers WHERE id = :customer_id")
        result = await db_session.execute(raw_query, {"customer_id": customer_data["id"]})
        raw_phone = result.scalar()
        
        # Should not contain original phone number
        assert "+1-555-ENCRYPT" != raw_phone
    
    async def test_data_in_transit_encryption(self, async_client):
        """Test HTTPS/TLS enforcement for data in transit."""
        
        # Test that sensitive operations require HTTPS
        sensitive_endpoints = [
            "/api/v1/auth/login",
            "/api/v1/auth/register", 
            "/api/v1/customers",
            "/api/v1/billing/payments"
        ]
        
        for endpoint in sensitive_endpoints:
            # Simulate non-HTTPS request (HTTP only)
            with patch('fastapi.Request.url') as mock_url:
                mock_url.scheme = 'http'  # Non-secure HTTP
                
                response = await async_client.post(
                    endpoint,
                    json={"test": "data"},
                    headers={"X-Forwarded-Proto": "http"}
                )
                
                # Should redirect to HTTPS or reject non-secure requests
                assert response.status_code in [301, 302, 400, 426]  # Redirect or upgrade required


@pytest.mark.security
@pytest.mark.audit_logging
class TestAuditLoggingSecurity:
    """Test audit logging and security monitoring."""
    
    async def test_security_event_logging(self, db_session: AsyncSession):
        """Test logging of security-relevant events."""
        
        audit_logger = AuditLogger(db_session)
        
        # Test different types of security events
        security_events = [
            {
                "event_type": "authentication_failure",
                "user_id": "user_123",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "details": {"reason": "invalid_password", "username": "testuser"}
            },
            {
                "event_type": "authorization_violation", 
                "user_id": "user_456",
                "ip_address": "10.0.0.50",
                "user_agent": "curl/7.68.0",
                "details": {"resource": "admin_panel", "action": "access", "role": "customer"}
            },
            {
                "event_type": "data_access",
                "user_id": "user_789",
                "ip_address": "172.16.0.10",
                "user_agent": "Python/requests",
                "details": {"resource": "customer_data", "customer_id": "cust_001", "fields": ["ssn", "credit_card"]}
            },
            {
                "event_type": "account_lockout",
                "user_id": "user_000",
                "ip_address": "203.0.113.100",
                "user_agent": "AttackBot/1.0",
                "details": {"failed_attempts": 5, "lockout_duration": 3600}
            }
        ]
        
        for event in security_events:
            # Log security event
            log_entry = await audit_logger.log_security_event(
                event_type=event["event_type"],
                user_id=event["user_id"],
                ip_address=event["ip_address"],
                user_agent=event["user_agent"],
                details=event["details"]
            )
            
            # Verify log entry was created
            assert log_entry.event_type == event["event_type"]
            assert log_entry.user_id == event["user_id"]
            assert log_entry.ip_address == event["ip_address"]
            assert log_entry.details == event["details"]
            assert log_entry.timestamp is not None
    
    async def test_data_modification_audit_trail(self, db_session: AsyncSession):
        """Test audit trail for data modifications."""
        
        audit_logger = AuditLogger(db_session)
        
        # Simulate customer data modification
        modification_event = {
            "event_type": "data_modification",
            "user_id": "admin_001",
            "resource_type": "customer",
            "resource_id": "cust_001",
            "action": "update",
            "changes": {
                "before": {"email": "old@example.com", "phone": "555-0123"},
                "after": {"email": "new@example.com", "phone": "555-9876"}
            },
            "ip_address": "192.168.1.50",
            "timestamp": datetime.utcnow()
        }
        
        # Log data modification
        audit_entry = await audit_logger.log_data_modification(
            user_id=modification_event["user_id"],
            resource_type=modification_event["resource_type"],
            resource_id=modification_event["resource_id"],
            action=modification_event["action"],
            changes=modification_event["changes"],
            ip_address=modification_event["ip_address"]
        )
        
        # Verify audit trail
        assert audit_entry.user_id == "admin_001"
        assert audit_entry.resource_type == "customer"
        assert audit_entry.resource_id == "cust_001"
        assert audit_entry.action == "update"
        assert "email" in audit_entry.changes["before"]
        assert "email" in audit_entry.changes["after"]
        assert audit_entry.changes["before"]["email"] != audit_entry.changes["after"]["email"]
    
    async def test_audit_log_integrity(self, db_session: AsyncSession):
        """Test audit log integrity and tamper detection."""
        
        audit_logger = AuditLogger(db_session)
        
        # Create audit log entry
        log_entry = await audit_logger.log_security_event(
            event_type="test_integrity",
            user_id="integrity_test",
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            details={"test": "integrity_check"}
        )
        
        # Generate integrity hash for the log entry
        original_hash = await audit_logger.generate_integrity_hash(log_entry)
        assert len(original_hash) >= 64  # SHA-256 or stronger
        
        # Simulate tampering attempt
        tampered_entry = log_entry.copy()
        tampered_entry.details = {"test": "tampered_data"}
        
        tampered_hash = await audit_logger.generate_integrity_hash(tampered_entry)
        
        # Verify integrity check detects tampering
        assert original_hash != tampered_hash
        
        # Verify original entry integrity
        is_valid = await audit_logger.verify_integrity(log_entry, original_hash)
        assert is_valid is True
        
        # Verify tampered entry fails integrity check
        is_tampered = await audit_logger.verify_integrity(tampered_entry, original_hash)
        assert is_tampered is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])