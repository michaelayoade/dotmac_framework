"""
Extended conftest.py for API testing.
Additional fixtures and configuration specifically for API test suites.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.utils.api_test_helpers import (
    APITestClient,
    DatabaseTestHelper,
    MockAuthService,
    MockCustomerService,
    MockServicesService,
    TestDataFactory,
)


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application with all routers."""
    from dotmac_isp.modules.identity.router import identity_router
    from dotmac_isp.modules.services.router import services_router

    app = FastAPI(title="DotMac ISP API Test", version="1.0.0")

    # Include routers
    app.include_router(identity_router, prefix="/identity")
    app.include_router(services_router, prefix="/services")

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_client(client: TestClient) -> APITestClient:
    """Create enhanced API test client with auth helpers."""
    return APITestClient(client, tenant_id="test-tenant-123")


@pytest.fixture
def test_tenant_id() -> str:
    """Test tenant ID for consistent testing."""
    return "test-tenant-123"


@pytest.fixture
def mock_auth_service(test_tenant_id: str) -> MockAuthService:
    """Mock authentication service."""
    return MockAuthService(tenant_id=test_tenant_id)


@pytest.fixture
def mock_customer_service(test_tenant_id: str) -> MockCustomerService:
    """Mock customer service."""
    return MockCustomerService(tenant_id=test_tenant_id)


@pytest.fixture
def mock_services_service(test_tenant_id: str) -> MockServicesService:
    """Mock services service."""
    return MockServicesService(tenant_id=test_tenant_id)


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Test data factory for creating test objects."""
    return TestDataFactory()


@pytest.fixture
def sample_customer_data(test_data_factory: TestDataFactory) -> dict[str, Any]:
    """Sample customer data for testing."""
    return test_data_factory.create_customer_data()


@pytest.fixture
def sample_service_plan_data(test_data_factory: TestDataFactory) -> dict[str, Any]:
    """Sample service plan data for testing."""
    return test_data_factory.create_service_plan_data()


@pytest.fixture
def sample_user_data(test_data_factory: TestDataFactory) -> dict[str, Any]:
    """Sample user data for testing."""
    return test_data_factory.create_user_data()


@pytest.fixture
def valid_jwt_token(test_tenant_id: str, test_data_factory: TestDataFactory) -> str:
    """Valid JWT token for testing."""
    return test_data_factory.create_jwt_token(
        user_id="test-user-123",
        tenant_id=test_tenant_id
    )


@pytest.fixture
def expired_jwt_token(test_tenant_id: str, test_data_factory: TestDataFactory) -> str:
    """Expired JWT token for testing."""
    return test_data_factory.create_jwt_token(
        user_id="test-user-123",
        tenant_id=test_tenant_id,
        expired=True
    )


@pytest.fixture
def auth_headers(valid_jwt_token: str, test_tenant_id: str) -> dict[str, str]:
    """Authentication headers for API requests."""
    return {
        "Authorization": f"Bearer {valid_jwt_token}",
        "X-Tenant-ID": test_tenant_id
    }


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Auto-mock FastAPI dependencies for all API tests."""
    with patch('dotmac.auth.dependencies.get_current_user') as mock_get_user:
        with patch('dotmac.auth.dependencies.get_current_tenant') as mock_get_tenant:
            with patch('dotmac.auth.dependencies.require_permissions') as mock_perms:
                # Default user
                mock_get_user.return_value = {
                    "id": "test-user-123",
                    "username": "testuser",
                    "email": "testuser@example.com",
                    "tenant_id": "test-tenant-123"
                }

                # Default tenant
                mock_get_tenant.return_value = {
                    "tenant_id": "test-tenant-123",
                    "name": "Test Tenant"
                }

                # Default permissions (allow all)
                mock_perms.return_value = lambda: None

                yield {
                    "get_current_user": mock_get_user,
                    "get_current_tenant": mock_get_tenant,
                    "require_permissions": mock_perms
                }


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session_mock = MagicMock()

    # Mock common database operations
    session_mock.query.return_value.filter.return_value.first.return_value = None
    session_mock.query.return_value.filter.return_value.all.return_value = []
    session_mock.query.return_value.all.return_value = []
    session_mock.add.return_value = None
    session_mock.commit.return_value = None
    session_mock.refresh.return_value = None
    session_mock.rollback.return_value = None
    session_mock.close.return_value = None

    return session_mock


@pytest.fixture
def db_test_helper(mock_database_session) -> DatabaseTestHelper:
    """Database test helper with mocked session."""
    return DatabaseTestHelper(mock_database_session)


@pytest.fixture
def authenticated_client(api_client: APITestClient, mock_auth_service: MockAuthService) -> APITestClient:
    """Pre-authenticated API client."""
    with patch('dotmac_isp.modules.identity.router.AuthService', return_value=mock_auth_service):
        api_client.authenticate()
        return api_client


# Test markers for organizing API tests
pytest_markers = [
    "auth: mark test as authentication-related",
    "crud: mark test as CRUD operation",
    "error: mark test as error handling",
    "security: mark test as security-related",
    "rate_limit: mark test as rate limiting",
    "integration: mark test as integration test",
    "unit: mark test as unit test",
    "slow: mark test as slow-running"
]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    for marker in pytest_markers:
        config.addinivalue_line("markers", marker)


@pytest.fixture(scope="session")
def api_test_config():
    """API testing configuration."""
    return {
        "base_url": "http://testserver",
        "timeout": 30,
        "rate_limit_window": 60,
        "max_requests_per_window": 100,
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
        "test_tenant_id": "test-tenant-123"
    }


@pytest.fixture
def error_test_cases():
    """Common error test cases for API endpoints."""
    return {
        "invalid_uuid": "not-a-uuid",
        "missing_auth": {},
        "invalid_token": "Bearer invalid_token",
        "expired_token": "Bearer expired_token",
        "malformed_json": '{"invalid": json}',
        "empty_payload": {},
        "oversized_payload": {"data": "X" * 100000},
        "sql_injection": "'; DROP TABLE users; --",
        "xss_payload": "<script>alert('xss')</script>",
        "path_traversal": "../../../etc/passwd"
    }


@pytest.fixture
def performance_benchmarks():
    """Performance benchmarks for API endpoints."""
    return {
        "auth_login": {"max_time": 1.0, "max_memory": "50MB"},
        "customer_list": {"max_time": 0.5, "max_memory": "20MB"},
        "customer_create": {"max_time": 2.0, "max_memory": "30MB"},
        "service_activate": {"max_time": 3.0, "max_memory": "40MB"},
        "bulk_operation": {"max_time": 10.0, "max_memory": "100MB"}
    }


# Custom assertions for API testing
def assert_api_response_structure(response_data: dict[str, Any], required_fields: list):
    """Assert API response has required structure."""
    for field in required_fields:
        assert field in response_data, f"Required field '{field}' missing from response"


def assert_pagination_response(response_data: dict[str, Any]):
    """Assert response follows pagination format."""
    pagination_fields = ["total", "page", "limit", "pages"]
    for field in pagination_fields:
        if field in response_data:
            assert isinstance(response_data[field], int)
            assert response_data[field] >= 0


def assert_error_response_format(response_data: dict[str, Any]):
    """Assert error response follows standard format."""
    assert "detail" in response_data
    assert isinstance(response_data["detail"], (str, list))


# Export test utilities for use in test files
__all__ = [
    "assert_api_response_structure",
    "assert_pagination_response",
    "assert_error_response_format"
]
