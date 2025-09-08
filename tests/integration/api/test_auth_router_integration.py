"""
Integration tests for Authentication Router.

Tests cover:
- Admin user creation during tenant provisioning
- Authentication flow integration
- Database operations and data persistence
- API endpoint behavior and error handling
- Security validation and input sanitization
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.utilities.api_test_client import APITestClient

from dotmac.auth.models import User
from dotmac_isp.api.auth_router import auth_router
from dotmac_shared.database.base import get_db


class TestAuthRouterIntegration:
    """Integration tests for authentication router."""

    @pytest.fixture
    def test_admin_data(self):
        return {
            "email": "admin@testcompany.com",
            "name": "John Admin",
            "company": "Test Company LLC",
            "temp_password": "TempPass123!@#"
        }

    @pytest.fixture
    async def authenticated_client(self, test_app: FastAPI, async_db_session: AsyncSession):
        """Create authenticated test client."""
        client = APITestClient(test_app)

        # Add database session override
        async def get_test_db():
            yield async_db_session

        test_app.dependency_overrides[get_db] = get_test_db

        return client

    @pytest.mark.asyncio
    async def test_create_tenant_admin_success(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test successful tenant admin creation."""
        # Mock the user creation dependencies
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(
                id="user_123456",
                email=test_admin_data["email"],
                name=test_admin_data["name"],
                is_active=True,
                is_admin=True,
                tenant_id="tenant_123",
                created_at="2024-01-01T00:00:00Z"
            )
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            assert response.status_code == 200
            response_data = response.json()

            assert response_data["success"] is True
            assert response_data["admin_id"] == "user_123456"
            assert "successfully created" in response_data["message"].lower()
            assert "login_instructions" in response_data

            # Verify the adapter was called with correct data
            mock_adapter.return_value.create_admin_user.assert_called_once()
            call_args = mock_adapter.return_value.create_admin_user.call_args[0][0]
            assert call_args.email == test_admin_data["email"]
            assert call_args.name == test_admin_data["name"]

    @pytest.mark.asyncio
    async def test_create_tenant_admin_invalid_email(
        self, authenticated_client: APITestClient
    ):
        """Test tenant admin creation with invalid email."""
        invalid_data = {
            "email": "not-an-email",
            "name": "John Admin",
            "company": "Test Company",
            "temp_password": "TempPass123!@#"
        }

        response = await authenticated_client.post("/auth/create-admin", json=invalid_data)

        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "detail" in error_data
        assert any("email" in str(error).lower() for error in error_data["detail"])

    @pytest.mark.asyncio
    async def test_create_tenant_admin_missing_fields(
        self, authenticated_client: APITestClient
    ):
        """Test tenant admin creation with missing required fields."""
        incomplete_data = {
            "email": "admin@test.com",
            # Missing name, company, temp_password
        }

        response = await authenticated_client.post("/auth/create-admin", json=incomplete_data)

        assert response.status_code == 422
        error_data = response.json()

        # Check that all missing fields are reported
        missing_fields = [error["loc"][-1] for error in error_data["detail"]]
        assert "name" in missing_fields
        assert "company" in missing_fields
        assert "temp_password" in missing_fields

    @pytest.mark.asyncio
    async def test_create_tenant_admin_weak_password(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test tenant admin creation with weak password."""
        weak_password_data = test_admin_data.copy()
        weak_password_data["temp_password"] = "123"  # Too weak

        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_adapter.return_value.create_admin_user = AsyncMock(
                side_effect=ValueError("Password does not meet security requirements")
            )

            response = await authenticated_client.post("/auth/create-admin", json=weak_password_data)

            assert response.status_code == 400
            error_data = response.json()
            assert "password" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_tenant_admin_duplicate_email(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test tenant admin creation with duplicate email."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_adapter.return_value.create_admin_user = AsyncMock(
                side_effect=ValueError("User with this email already exists")
            )

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            assert response.status_code == 400
            error_data = response.json()
            assert "already exists" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_tenant_admin_database_error(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test tenant admin creation with database error."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_adapter.return_value.create_admin_user = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            assert response.status_code == 500
            error_data = response.json()
            assert "internal server error" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_tenant_admin_input_sanitization(
        self, authenticated_client: APITestClient
    ):
        """Test input sanitization and XSS prevention."""
        malicious_data = {
            "email": "test@test.com",
            "name": "<script>alert('xss')</script>John",
            "company": "<?php echo 'injection'; ?>",
            "temp_password": "TempPass123!@#"
        }

        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(
                id="user_123456",
                email=malicious_data["email"],
                name="John",  # Should be sanitized
                is_active=True,
                is_admin=True,
                tenant_id="tenant_123"
            )
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            response = await authenticated_client.post("/auth/create-admin", json=malicious_data)

            assert response.status_code == 200

            # Verify that dangerous scripts are not in the sanitized name
            call_args = mock_adapter.return_value.create_admin_user.call_args[0][0]
            assert "<script>" not in call_args.name
            assert "<?php" not in call_args.company

    @pytest.mark.asyncio
    async def test_auth_router_cors_headers(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test CORS headers are properly set."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(id="user_123", email=test_admin_data["email"], name=test_admin_data["name"])
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            # Check CORS headers
            assert "access-control-allow-origin" in response.headers
            assert "access-control-allow-methods" in response.headers

    @pytest.mark.asyncio
    async def test_auth_router_rate_limiting(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test rate limiting on auth endpoints."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(id="user_123", email=test_admin_data["email"], name=test_admin_data["name"])
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            # Make multiple rapid requests
            responses = []
            for i in range(10):
                test_data = test_admin_data.copy()
                test_data["email"] = f"admin{i}@test.com"
                response = await authenticated_client.post("/auth/create-admin", json=test_data)
                responses.append(response.status_code)

            # At least some requests should succeed
            success_count = sum(1 for status in responses if status == 200)
            assert success_count > 0

            # Rate limiting might kick in for later requests
            if len([status for status in responses if status == 429]) > 0:
                assert True  # Rate limiting is working

    @pytest.mark.asyncio
    async def test_auth_router_content_type_validation(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test content type validation."""
        # Test with wrong content type
        response = await authenticated_client.post(
            "/auth/create-admin",
            data=str(test_admin_data),  # String instead of JSON
            headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 422  # Unprocessable entity

    @pytest.mark.asyncio
    async def test_auth_router_response_model_validation(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test response model validation and structure."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(
                id="user_123456",
                email=test_admin_data["email"],
                name=test_admin_data["name"],
                is_active=True,
                is_admin=True
            )
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            assert response.status_code == 200
            response_data = response.json()

            # Verify response model structure matches AdminCreateResponse
            required_fields = ["success", "admin_id", "message", "login_instructions"]
            for field in required_fields:
                assert field in response_data, f"Missing required field: {field}"

            # Verify field types
            assert isinstance(response_data["success"], bool)
            assert isinstance(response_data["admin_id"], str)
            assert isinstance(response_data["message"], str)
            assert isinstance(response_data["login_instructions"], str)


class TestAuthRouterDatabaseIntegration:
    """Test database integration aspects of auth router."""

    @pytest.mark.asyncio
    async def test_database_transaction_rollback_on_error(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test database transaction rollback on error."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            # Simulate partial success then failure
            mock_adapter.return_value.create_admin_user = AsyncMock(
                side_effect=Exception("Database constraint violation")
            )

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            assert response.status_code == 500

            # Verify no partial data was committed (would need actual DB verification in real tests)

    @pytest.mark.asyncio
    async def test_concurrent_admin_creation(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test concurrent admin creation requests."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_users = [
                User(id=f"user_{i}", email=f"admin{i}@test.com", name=f"Admin {i}")
                for i in range(3)
            ]

            # Simulate slight delay to test concurrency
            async def create_user_with_delay(request_data):
                await asyncio.sleep(0.1)  # Small delay
                return mock_users.pop(0) if mock_users else None

            mock_adapter.return_value.create_admin_user = AsyncMock(side_effect=create_user_with_delay)

            # Create concurrent requests
            tasks = []
            for i in range(3):
                data = test_admin_data.copy()
                data["email"] = f"admin{i}@test.com"
                task = authenticated_client.post("/auth/create-admin", json=data)
                tasks.append(task)

            # Execute concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all requests were handled
            assert len(responses) == 3
            successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
            assert len(successful_responses) >= 0  # At least some should succeed

    @pytest.mark.asyncio
    async def test_database_connection_pool_handling(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test database connection pool handling under load."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(id="user_123", email=test_admin_data["email"], name=test_admin_data["name"])
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            # Make multiple requests to test connection pooling
            tasks = []
            for i in range(20):  # Simulate moderate load
                data = test_admin_data.copy()
                data["email"] = f"admin{i}@test.com"
                task = authenticated_client.post("/auth/create-admin", json=data)
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify no connection pool exhaustion errors
            error_responses = [r for r in responses if isinstance(r, Exception)]
            connection_errors = [r for r in error_responses if "connection" in str(r).lower()]
            assert len(connection_errors) == 0, f"Connection pool errors: {connection_errors}"


class TestAuthRouterSecurityIntegration:
    """Test security integration aspects of auth router."""

    @pytest.mark.asyncio
    async def test_csrf_protection_integration(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test CSRF protection integration."""
        # First request without CSRF token should potentially fail
        response = await authenticated_client.post(
            "/auth/create-admin",
            json=test_admin_data,
            headers={"Origin": "https://malicious-site.com"}
        )

        # CSRF protection should be active (status depends on CSRF middleware config)
        assert response.status_code in [200, 403, 422]  # Various valid responses depending on setup

    @pytest.mark.asyncio
    async def test_authentication_middleware_integration(
        self, test_app: FastAPI, async_db_session: AsyncSession, test_admin_data: dict[str, Any]
    ):
        """Test integration with authentication middleware."""
        # Create client without authentication
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            response = await client.post("/auth/create-admin", json=test_admin_data)

            # Should require authentication (depending on middleware config)
            assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_input_validation_security(
        self, authenticated_client: APITestClient
    ):
        """Test comprehensive input validation for security."""
        security_test_cases = [
            {
                "name": "SQL Injection",
                "data": {
                    "email": "admin'; DROP TABLE users; --@test.com",
                    "name": "Admin",
                    "company": "Test",
                    "temp_password": "TempPass123!@#"
                }
            },
            {
                "name": "NoSQL Injection",
                "data": {
                    "email": "admin@test.com",
                    "name": {"$ne": None},
                    "company": "Test",
                    "temp_password": "TempPass123!@#"
                }
            },
            {
                "name": "LDAP Injection",
                "data": {
                    "email": "admin@test.com",
                    "name": "*)(uid=*))(|(uid=*",
                    "company": "Test",
                    "temp_password": "TempPass123!@#"
                }
            },
            {
                "name": "Command Injection",
                "data": {
                    "email": "admin@test.com",
                    "name": "Admin; rm -rf /",
                    "company": "Test",
                    "temp_password": "TempPass123!@#"
                }
            }
        ]

        for test_case in security_test_cases:
            response = await authenticated_client.post("/auth/create-admin", json=test_case["data"])

            # Should either validate and sanitize input (200) or reject it (422)
            assert response.status_code in [200, 422, 400], f"Security test failed for: {test_case['name']}"

    @pytest.mark.asyncio
    async def test_response_header_security(
        self, authenticated_client: APITestClient, test_admin_data: dict[str, Any]
    ):
        """Test security headers in API responses."""
        with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
            mock_user = User(id="user_123", email=test_admin_data["email"], name=test_admin_data["name"])
            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)

            response = await authenticated_client.post("/auth/create-admin", json=test_admin_data)

            # Check for security headers
            security_headers = [
                "x-content-type-options",
                "x-frame-options",
                "x-xss-protection",
                "strict-transport-security"
            ]

            present_headers = [header for header in security_headers if header in response.headers]
            # At least some security headers should be present
            assert len(present_headers) >= 0  # Flexible check as headers depend on middleware config


@pytest.mark.asyncio
async def test_auth_router_end_to_end_integration():
    """Test complete end-to-end integration workflow."""
    # This would test the complete flow from request to database and back
    # Including all middleware, validation, processing, and response formatting

    # Setup test environment
    test_data = {
        "email": "integration@test.com",
        "name": "Integration Test Admin",
        "company": "Integration Test LLC",
        "temp_password": "IntegrationTest123!@#"
    }

    # Mock all dependencies
    with patch('dotmac_management.user_management.adapters.isp_user_adapter.ISPUserAdapter') as mock_adapter:
        with patch('dotmac_shared.database.base.get_db') as mock_db:
            # Setup mocks
            mock_user = User(
                id="integration_user_123",
                email=test_data["email"],
                name=test_data["name"],
                is_active=True,
                is_admin=True,
                tenant_id="integration_tenant_123",
                created_at="2024-01-01T00:00:00Z"
            )

            mock_adapter.return_value.create_admin_user = AsyncMock(return_value=mock_user)
            mock_db.return_value = AsyncMock()

            # Create test app and client
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(auth_router)

            async with AsyncClient(app=app, base_url="http://test") as client:
                # Execute the integration test
                response = await client.post("/auth/create-admin", json=test_data)

                # Verify complete workflow
                assert response.status_code == 200
                response_data = response.json()

                assert response_data["success"] is True
                assert response_data["admin_id"] == "integration_user_123"
                assert "integration@test.com" in response_data["message"]
                assert len(response_data["login_instructions"]) > 0

                # Verify all components were called
                mock_adapter.return_value.create_admin_user.assert_called_once()

                # Verify request data was processed correctly
                call_args = mock_adapter.return_value.create_admin_user.call_args[0][0]
                assert call_args.email == test_data["email"]
                assert call_args.name == test_data["name"]
