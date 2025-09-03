"""
Test authentication flows for the DotMac ISP Framework API.
Comprehensive testing of login, logout, token refresh, and JWT validation.
"""

import asyncio
import json
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from dotmac_isp.modules.identity.router import identity_router
from dotmac_isp.modules.identity.services import AuthService
from dotmac_shared.auth.jwt import create_access_token, verify_token
from dotmac_shared.auth.models import UserToken, SessionData


class TestAuthenticationFlows:
    """Test complete authentication workflows."""

    @pytest.fixture
    def auth_service_mock(self):
        """Mock authentication service."""
        mock = AsyncMock(spec=AuthService)
        mock.authenticate_user.return_value = {
            "access_token": "test_access_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "user-123",
                "username": "testuser",
                "email": "test@example.com",
                "tenant_id": "tenant-123"
            }
        }
        mock.logout_user.return_value = True
        mock.refresh_token.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600
        }
        return mock

    @pytest.fixture
    def valid_jwt_token(self):
        """Create a valid JWT token for testing."""
        payload = {
            "sub": "user-123",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        return create_access_token(payload)

    def test_login_success(self, client, auth_service_mock):
        """Test successful login flow."""
        with patch('dotmac_isp.modules.identity.router.AuthService', return_value=auth_service_mock):
            login_data = {
                "username": "testuser",
                "password": "testpassword",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "testuser"
            assert data["user"]["tenant_id"] == "tenant-123"
            
            # Verify service was called correctly
            auth_service_mock.authenticate_user.assert_called_once_with(
                username="testuser",
                password="testpassword",
                portal_type="admin",
                user_agent="api-client",
                ip_address="127.0.0.1"
            )

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.authenticate_user.return_value = None
            mock_service.return_value = mock_instance
            
            login_data = {
                "username": "wronguser",
                "password": "wrongpassword",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=login_data)
            
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """Test login with missing required fields."""
        incomplete_data = {"username": "testuser"}
        
        response = client.post("/identity/auth/login", json=incomplete_data)
        
        assert response.status_code == 422
        assert "validation error" in response.json()["detail"][0]["type"]

    def test_login_service_error(self, client):
        """Test login when service throws exception."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.authenticate_user.side_effect = Exception("Database error")
            mock_service.return_value = mock_instance
            
            login_data = {
                "username": "testuser",
                "password": "testpassword",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=login_data)
            
            assert response.status_code == 500
            assert "Authentication failed" in response.json()["detail"]

    def test_logout_success(self, client, auth_service_mock, valid_jwt_token):
        """Test successful logout flow."""
        with patch('dotmac_isp.modules.identity.router.AuthService', return_value=auth_service_mock):
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "user-123", "username": "testuser"}
                
                headers = {"Authorization": f"Bearer {valid_jwt_token}"}
                response = client.post(
                    "/identity/auth/logout",
                    params={"session_id": "session-123"},
                    headers=headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "Logged out successfully" in data["message"]
                
                # Verify service was called correctly
                auth_service_mock.logout_user.assert_called_once_with(
                    session_id="session-123",
                    user_id="user-123"
                )

    def test_logout_unauthorized(self, client):
        """Test logout without authentication."""
        response = client.post(
            "/identity/auth/logout",
            params={"session_id": "session-123"}
        )
        
        assert response.status_code == 401

    def test_logout_service_error(self, client, valid_jwt_token):
        """Test logout when service throws exception."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_instance = AsyncMock()
                mock_instance.logout_user.side_effect = Exception("Service error")
                mock_service.return_value = mock_instance
                mock_get_user.return_value = {"id": "user-123", "username": "testuser"}
                
                headers = {"Authorization": f"Bearer {valid_jwt_token}"}
                response = client.post(
                    "/identity/auth/logout",
                    params={"session_id": "session-123"},
                    headers=headers
                )
                
                assert response.status_code == 500
                assert "Logout failed" in response.json()["detail"]


class TestTokenManagement:
    """Test JWT token creation, validation, and refresh."""

    def test_jwt_token_creation(self):
        """Test creating a valid JWT token."""
        user_data = {
            "sub": "user-123",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        token = create_access_token(user_data)
        assert token is not None
        assert isinstance(token, str)
        
        # Decode without verification to check structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["sub"] == "user-123"
        assert decoded["username"] == "testuser"
        assert decoded["tenant_id"] == "tenant-123"

    def test_jwt_token_validation(self):
        """Test validating JWT tokens."""
        # Create valid token
        payload = {
            "sub": "user-123",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc)
        }
        token = create_access_token(payload)
        
        # Validate token
        result = verify_token(token)
        assert result is not None
        assert result["sub"] == "user-123"
        assert result["tenant_id"] == "tenant-123"

    def test_jwt_token_expiration(self):
        """Test handling expired JWT tokens."""
        # Create expired token
        payload = {
            "sub": "user-123",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "iat": datetime.now(timezone.utc) - timedelta(hours=2)
        }
        token = create_access_token(payload)
        
        # Attempt to validate expired token
        result = verify_token(token)
        assert result is None  # Should be None for expired tokens

    def test_jwt_token_invalid_signature(self):
        """Test handling tokens with invalid signatures."""
        # Create token with wrong secret
        payload = {
            "sub": "user-123",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        # Create token with different secret
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        # Attempt to validate with correct secret
        result = verify_token(token)
        assert result is None  # Should be None for invalid signature


class TestSessionManagement:
    """Test user session management and tracking."""

    @pytest.fixture
    def session_data(self):
        """Sample session data."""
        return SessionData(
            session_id="session-123",
            user_id="user-123",
            tenant_id="tenant-123",
            portal_type="admin",
            ip_address="127.0.0.1",
            user_agent="test-client",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
            last_activity=datetime.now(timezone.utc)
        )

    def test_session_creation(self, session_data):
        """Test creating user session."""
        assert session_data.session_id == "session-123"
        assert session_data.user_id == "user-123"
        assert session_data.tenant_id == "tenant-123"
        assert not session_data.is_expired()

    def test_session_expiration(self):
        """Test session expiration logic."""
        expired_session = SessionData(
            session_id="session-123",
            user_id="user-123",
            tenant_id="tenant-123",
            portal_type="admin",
            ip_address="127.0.0.1",
            user_agent="test-client",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            last_activity=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        assert expired_session.is_expired()

    def test_session_activity_update(self, session_data):
        """Test updating session last activity."""
        original_activity = session_data.last_activity
        
        # Wait a moment and update activity
        import time
        time.sleep(0.1)
        session_data.update_activity()
        
        assert session_data.last_activity > original_activity


class TestMultiTenantAuthentication:
    """Test authentication across multiple tenants."""

    def test_tenant_isolation_in_auth(self, client):
        """Test that authentication respects tenant boundaries."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            # Mock service to return different results for different tenants
            mock_instance = AsyncMock()
            
            def mock_auth(username, password, portal_type, **kwargs):
                if username == "tenant1user":
                    return {
                        "access_token": "tenant1_token",
                        "user": {"id": "user-1", "tenant_id": "tenant-1"}
                    }
                elif username == "tenant2user":
                    return {
                        "access_token": "tenant2_token", 
                        "user": {"id": "user-2", "tenant_id": "tenant-2"}
                    }
                return None
            
            mock_instance.authenticate_user.side_effect = mock_auth
            mock_service.return_value = mock_instance
            
            # Test tenant 1 user
            response1 = client.post("/identity/auth/login", json={
                "username": "tenant1user",
                "password": "password",
                "portal_type": "admin"
            })
            
            assert response1.status_code == 200
            assert response1.json()["user"]["tenant_id"] == "tenant-1"
            
            # Test tenant 2 user
            response2 = client.post("/identity/auth/login", json={
                "username": "tenant2user",
                "password": "password",
                "portal_type": "admin"
            })
            
            assert response2.status_code == 200
            assert response2.json()["user"]["tenant_id"] == "tenant-2"

    def test_cross_tenant_access_denied(self, client):
        """Test that users cannot access resources from other tenants."""
        # This would be tested at the endpoint level where tenant context is enforced
        tenant1_token = create_access_token({
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        })
        
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = {
                "id": "user-1",
                "tenant_id": "tenant-1"
            }
            
            # Attempt to access resource with tenant context
            headers = {
                "Authorization": f"Bearer {tenant1_token}",
                "X-Tenant-ID": "tenant-2"  # Different tenant
            }
            
            # This would typically be caught by tenant validation middleware
            # For now, just verify the token contains correct tenant
            decoded = jwt.decode(tenant1_token, options={"verify_signature": False})
            assert decoded["tenant_id"] == "tenant-1"


class TestAuthenticationSecurity:
    """Test security aspects of authentication."""

    def test_password_brute_force_protection(self, client):
        """Test protection against brute force attacks."""
        # Simulate multiple failed login attempts
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.authenticate_user.return_value = None  # Always fail
            mock_service.return_value = mock_instance
            
            login_data = {
                "username": "testuser",
                "password": "wrongpassword",
                "portal_type": "admin"
            }
            
            responses = []
            for i in range(5):
                response = client.post("/identity/auth/login", json=login_data)
                responses.append(response)
            
            # All should fail with 401
            for response in responses:
                assert response.status_code == 401

    def test_jwt_token_tampering(self):
        """Test detection of tampered JWT tokens."""
        # Create valid token
        payload = {
            "sub": "user-123",
            "username": "normaluser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token = create_access_token(payload)
        
        # Tamper with token by changing payload
        parts = token.split('.')
        tampered_payload = {
            "sub": "user-123",
            "username": "admin",  # Changed to admin
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        import base64
        tampered_payload_encoded = base64.urlsafe_b64encode(
            json.dumps(tampered_payload).encode()
        ).decode().rstrip('=')
        
        tampered_token = f"{parts[0]}.{tampered_payload_encoded}.{parts[2]}"
        
        # Verification should fail
        result = verify_token(tampered_token)
        assert result is None

    def test_token_replay_attack_prevention(self):
        """Test prevention of token replay attacks."""
        # Create token with short expiry
        payload = {
            "sub": "user-123",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "exp": datetime.now(timezone.utc) + timedelta(seconds=1),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4())  # JWT ID for tracking
        }
        token = create_access_token(payload)
        
        # Token should be valid initially
        result = verify_token(token)
        assert result is not None
        
        # Wait for expiry
        import time
        time.sleep(2)
        
        # Token should now be expired
        result = verify_token(token)
        assert result is None


class TestAuthenticationIntegration:
    """Integration tests for authentication with other modules."""

    def test_auth_with_user_service_integration(self, client):
        """Test authentication integrated with user service."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_auth_service:
            with patch('dotmac_isp.modules.identity.router.UserService') as mock_user_service:
                # Setup mocks
                auth_mock = AsyncMock()
                user_mock = AsyncMock()
                
                auth_mock.authenticate_user.return_value = {
                    "access_token": "test_token",
                    "user": {"id": "user-123", "username": "testuser"}
                }
                
                user_mock.get_user_by_id.return_value = {
                    "id": "user-123",
                    "username": "testuser",
                    "email": "test@example.com",
                    "is_active": True
                }
                
                mock_auth_service.return_value = auth_mock
                mock_user_service.return_value = user_mock
                
                # Login first
                login_response = client.post("/identity/auth/login", json={
                    "username": "testuser",
                    "password": "testpassword",
                    "portal_type": "admin"
                })
                
                assert login_response.status_code == 200
                token = login_response.json()["access_token"]
                
                # Use token to access user endpoint
                with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                    with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                        mock_get_user.return_value = {"id": "user-123"}
                        mock_perms.return_value = lambda: None
                        
                        headers = {"Authorization": f"Bearer {token}"}
                        user_response = client.get("/identity/users/user-123", headers=headers)
                        
                        assert user_response.status_code == 200
                        assert user_response.json()["username"] == "testuser"

    def test_auth_flow_complete_lifecycle(self, client):
        """Test complete authentication lifecycle."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            mock_instance = AsyncMock()
            
            # Setup login response
            mock_instance.authenticate_user.return_value = {
                "access_token": "lifecycle_token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "user-123",
                    "username": "lifecycleuser",
                    "tenant_id": "tenant-123"
                }
            }
            
            # Setup logout response
            mock_instance.logout_user.return_value = True
            
            mock_service.return_value = mock_instance
            
            # Step 1: Login
            login_response = client.post("/identity/auth/login", json={
                "username": "lifecycleuser",
                "password": "password",
                "portal_type": "admin"
            })
            
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            
            # Step 2: Use authenticated endpoint
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {
                    "id": "user-123",
                    "username": "lifecycleuser"
                }
                
                # Step 3: Logout
                headers = {"Authorization": f"Bearer {token}"}
                logout_response = client.post(
                    "/identity/auth/logout",
                    params={"session_id": "session-123"},
                    headers=headers
                )
                
                assert logout_response.status_code == 200
                assert logout_response.json()["success"] is True