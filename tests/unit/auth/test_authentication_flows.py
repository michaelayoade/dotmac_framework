"""
Authentication Flow Tests - Critical Backend Coverage

This module provides comprehensive tests for all authentication flows
across the DotMac Framework, ensuring production-ready security validation.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dotmac_isp.core.auth import AuthService
from dotmac_management.core.auth import ManagementAuthService

# Import framework components
from dotmac_shared.auth.current_user import get_current_tenant, get_current_user
from dotmac_shared.core.exceptions import AuthenticationError, AuthorizationError


class TestAuthenticationFlows:
    """Test authentication flows across all portals."""

    @pytest.fixture
    async def auth_service(self):
        """Create authenticated auth service instance."""
        service = AuthService()
        await service.initialize()
        return service

    @pytest.fixture
    def mock_user_data(self):
        """Mock user data for testing."""
        return {
            "user_id": "test_user_123",
            "email": "test@dotmac.io",
            "roles": ["isp_admin"],
            "tenant_id": "tenant_test_001",
            "permissions": ["read_customers", "write_customers", "billing_access"],
            "is_active": True,
            "last_login": datetime.utcnow().isoformat(),
            "mfa_enabled": True,
        }

    @pytest.fixture
    def mock_jwt_token(self):
        """Mock JWT token for testing."""
        return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"

    # Happy Path Tests

    @pytest.mark.asyncio
    async def test_login_valid_credentials_returns_jwt_token(
        self, auth_service, mock_user_data
    ):
        """Test successful login with valid credentials returns JWT token."""
        # Arrange
        email = "test@dotmac.io"
        password = "SecurePassword123!"

        with patch.object(auth_service, "authenticate_user") as mock_auth:
            mock_auth.return_value = mock_user_data

            with patch.object(auth_service, "generate_jwt_token") as mock_jwt:
                expected_token = "valid.jwt.token"
                mock_jwt.return_value = expected_token

                # Act
                result = await auth_service.login(email, password)

                # Assert
                assert result["success"] is True
                assert result["token"] == expected_token
                assert result["user"]["email"] == email
                assert result["user"]["roles"] == ["isp_admin"]
                mock_auth.assert_called_once_with(email, password)
                mock_jwt.assert_called_once()

    @pytest.mark.asyncio
    async def test_jwt_token_validation_middleware(
        self, auth_service, mock_user_data, mock_jwt_token
    ):
        """Test JWT token validation in middleware."""
        # Arrange
        with patch.object(auth_service, "validate_jwt_token") as mock_validate:
            mock_validate.return_value = mock_user_data

            # Act
            current_user = await get_current_user(
                request=MagicMock(), credentials=MagicMock(credentials=mock_jwt_token)
            )

            # Assert
            assert current_user["user_id"] == mock_user_data["user_id"]
            assert current_user["email"] == mock_user_data["email"]
            assert current_user["tenant_id"] == mock_user_data["tenant_id"]

    @pytest.mark.asyncio
    async def test_role_based_access_control_admin(self, auth_service, mock_user_data):
        """Test role-based access control for admin users."""
        # Arrange
        admin_user = {**mock_user_data, "roles": ["isp_admin", "super_admin"]}

        with patch.object(auth_service, "check_permissions") as mock_check:
            mock_check.return_value = True

            # Act
            has_access = await auth_service.check_user_permission(
                admin_user, "manage_all_customers"
            )

            # Assert
            assert has_access is True
            mock_check.assert_called_once_with(
                admin_user["roles"], "manage_all_customers"
            )

    @pytest.mark.asyncio
    async def test_multi_factor_authentication_flow(self, auth_service, mock_user_data):
        """Test complete MFA authentication flow."""
        # Arrange
        email = "test@dotmac.io"
        password = "SecurePassword123!"
        mfa_token = "123456"

        with patch.object(auth_service, "authenticate_user") as mock_auth:
            mock_auth.return_value = {**mock_user_data, "mfa_required": True}

            with patch.object(auth_service, "verify_mfa_token") as mock_mfa:
                mock_mfa.return_value = True

                with patch.object(auth_service, "generate_jwt_token") as mock_jwt:
                    expected_token = "mfa.validated.token"
                    mock_jwt.return_value = expected_token

                    # Act - Initial login
                    initial_result = await auth_service.login(email, password)

                    # Assert - MFA required
                    assert initial_result["mfa_required"] is True
                    assert "token" not in initial_result

                    # Act - MFA verification
                    final_result = await auth_service.verify_mfa_and_complete_login(
                        initial_result["mfa_session_id"], mfa_token
                    )

                    # Assert - Complete authentication
                    assert final_result["success"] is True
                    assert final_result["token"] == expected_token

    # Error Path Tests

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_returns_401(self, auth_service):
        """Test login with invalid credentials returns 401 error."""
        # Arrange
        email = "invalid@dotmac.io"
        password = "WrongPassword"

        with patch.object(auth_service, "authenticate_user") as mock_auth:
            mock_auth.side_effect = AuthenticationError("Invalid credentials")

            # Act & Assert
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_service.login(email, password)

            assert str(exc_info.value) == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_expired_jwt_token_handling(self, auth_service):
        """Test handling of expired JWT tokens."""
        # Arrange
        expired_token = "expired.jwt.token"

        with patch.object(auth_service, "validate_jwt_token") as mock_validate:
            mock_validate.side_effect = AuthenticationError("Token has expired")

            # Act & Assert
            with pytest.raises(AuthenticationError) as exc_info:
                await get_current_user(
                    request=MagicMock(),
                    credentials=MagicMock(credentials=expired_token),
                )

            assert "Token has expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insufficient_permissions_access_denied(
        self, auth_service, mock_user_data
    ):
        """Test access denied for insufficient permissions."""
        # Arrange
        limited_user = {
            **mock_user_data,
            "roles": ["customer"],
            "permissions": ["read_own_data"],
        }

        with patch.object(auth_service, "check_permissions") as mock_check:
            mock_check.return_value = False

            # Act & Assert
            with pytest.raises(AuthorizationError):
                await auth_service.require_permission(
                    limited_user, "manage_all_customers"
                )

    @pytest.mark.asyncio
    async def test_session_timeout_handling(self, auth_service, mock_user_data):
        """Test session timeout and cleanup."""
        # Arrange
        old_login_time = datetime.utcnow() - timedelta(hours=25)  # 25 hours ago
        expired_user = {**mock_user_data, "last_login": old_login_time.isoformat()}

        with patch.object(auth_service, "is_session_expired") as mock_expired:
            mock_expired.return_value = True

            with patch.object(auth_service, "cleanup_expired_session") as mock_cleanup:
                # Act
                await auth_service.validate_session(expired_user["user_id"])

                # Assert
                mock_cleanup.assert_called_once_with(expired_user["user_id"])

    # Multi-Tenant Tests

    @pytest.mark.asyncio
    async def test_tenant_isolation_validation(self, auth_service, mock_user_data):
        """Test tenant isolation in authentication."""
        # Arrange
        tenant_user = {**mock_user_data, "tenant_id": "tenant_001"}

        with patch.object(auth_service, "validate_tenant_access") as mock_tenant:
            mock_tenant.return_value = True

            # Act
            current_tenant = await get_current_tenant(tenant_user, "tenant_001")

            # Assert
            assert current_tenant["tenant_id"] == "tenant_001"
            mock_tenant.assert_called_once_with(tenant_user, "tenant_001")

    @pytest.mark.asyncio
    async def test_cross_tenant_access_blocked(self, auth_service, mock_user_data):
        """Test that cross-tenant access is properly blocked."""
        # Arrange
        tenant_user = {**mock_user_data, "tenant_id": "tenant_001"}

        with patch.object(auth_service, "validate_tenant_access") as mock_tenant:
            mock_tenant.return_value = False

            # Act & Assert
            with pytest.raises(AuthorizationError) as exc_info:
                await get_current_tenant(tenant_user, "tenant_002")

            assert "cross-tenant access denied" in str(exc_info.value).lower()


class TestManagementPlatformAuth:
    """Test Management Platform specific authentication."""

    @pytest.fixture
    async def mgmt_auth_service(self):
        """Create management auth service instance."""
        service = ManagementAuthService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_management_admin_super_permissions(self, mgmt_auth_service):
        """Test management admin has super permissions."""
        # Arrange
        super_admin = {
            "user_id": "mgmt_admin_001",
            "email": "admin@dotmac.io",
            "roles": ["management_super_admin"],
            "permissions": ["*"],  # All permissions
        }

        # Act
        can_manage_tenants = await mgmt_auth_service.check_user_permission(
            super_admin, "manage_all_tenants"
        )
        can_access_billing = await mgmt_auth_service.check_user_permission(
            super_admin, "access_all_billing"
        )

        # Assert
        assert can_manage_tenants is True
        assert can_access_billing is True

    @pytest.mark.asyncio
    async def test_tenant_admin_limited_scope(self, mgmt_auth_service):
        """Test tenant admin has limited scope permissions."""
        # Arrange
        tenant_admin = {
            "user_id": "tenant_admin_001",
            "email": "tenant.admin@customer.com",
            "roles": ["tenant_admin"],
            "tenant_id": "tenant_001",
            "permissions": ["manage_own_tenant", "view_own_billing"],
        }

        # Act
        can_manage_own = await mgmt_auth_service.check_user_permission(
            tenant_admin, "manage_own_tenant"
        )
        can_manage_others = await mgmt_auth_service.check_user_permission(
            tenant_admin, "manage_all_tenants"
        )

        # Assert
        assert can_manage_own is True
        assert can_manage_others is False


class TestAPIKeyAuthentication:
    """Test API key authentication for external integrations."""

    @pytest.mark.asyncio
    async def test_valid_api_key_authentication(self, auth_service):
        """Test API key authentication for external services."""
        # Arrange
        api_key = "dotmac_api_key_valid_12345"

        with patch.object(auth_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = {
                "key_id": "api_001",
                "client_name": "External Integration",
                "permissions": ["read_customers", "webhook_receiver"],
                "rate_limit": 1000,
            }

            # Act
            api_client = await auth_service.authenticate_api_key(api_key)

            # Assert
            assert api_client["key_id"] == "api_001"
            assert "read_customers" in api_client["permissions"]
            mock_validate.assert_called_once_with(api_key)

    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(self, auth_service):
        """Test API key rate limiting enforcement."""
        # Arrange
        api_key = "dotmac_api_key_limited_67890"

        with patch.object(auth_service, "check_api_rate_limit") as mock_rate_limit:
            mock_rate_limit.return_value = False  # Rate limit exceeded

            # Act & Assert
            with pytest.raises(AuthorizationError) as exc_info:
                await auth_service.enforce_api_rate_limit(api_key)

            assert "rate limit exceeded" in str(exc_info.value).lower()


# Fixtures and Test Data


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """Mock Redis connection for session storage."""
    return AsyncMock()


# Test Configuration
pytest_plugins = ["pytest_asyncio"]
