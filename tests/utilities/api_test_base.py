"""
API Test Base - Comprehensive FastAPI testing utilities with client mocking.
Provides test client setup, authentication mocking, and request/response validation.
"""
import json
from typing import Any, Optional
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient


class APITestBase:
    """Base class for API testing with FastAPI TestClient utilities."""

    def setup_method(self):
        """Setup method called before each test."""
        self.mock_users = {}
        self.mock_tenants = {}
        self.mock_db_session = None
        self.test_clients = {}

    def create_test_app(self, routers: list[Any], dependencies_override: Optional[dict] = None) -> FastAPI:
        """Create FastAPI test application with routers."""
        app = FastAPI(title="Test App", version="1.0.0")

        # Include routers
        for router in routers:
            app.include_router(router)

        # Override dependencies if provided
        if dependencies_override:
            for original_dep, override_dep in dependencies_override.items():
                app.dependency_overrides[original_dep] = override_dep

        return app

    def create_test_client(self, app: FastAPI) -> TestClient:
        """Create FastAPI TestClient for testing."""
        return TestClient(app)

    def create_async_test_client(self, app: FastAPI) -> AsyncClient:
        """Create AsyncClient for testing async endpoints."""
        return AsyncClient(app=app, base_url="http://test")

    def create_mock_user(self, user_id: Optional[str] = None, **kwargs) -> dict[str, Any]:
        """Create mock user data for authentication testing."""
        user_id = user_id or str(uuid4())

        default_user = {
            "user_id": user_id,
            "id": user_id,
            "email": f"test-{user_id}@example.com",
            "name": f"Test User {user_id[:8]}",
            "is_active": True,
            "is_admin": False,
            "roles": ["user"],
            "tenant_id": "test-tenant",
            "permissions": ["read", "write"]
        }

        default_user.update(kwargs)
        self.mock_users[user_id] = default_user
        return default_user

    def create_mock_admin_user(self, user_id: Optional[str] = None, **kwargs) -> dict[str, Any]:
        """Create mock admin user for admin endpoint testing."""
        admin_kwargs = {
            "is_admin": True,
            "roles": ["admin", "user"],
            "permissions": ["read", "write", "delete", "admin"]
        }
        admin_kwargs.update(kwargs)
        return self.create_mock_user(user_id, **admin_kwargs)

    def create_mock_tenant(self, tenant_id: Optional[str] = None, **kwargs) -> dict[str, Any]:
        """Create mock tenant data."""
        tenant_id = tenant_id or f"tenant-{str(uuid4())[:8]}"

        default_tenant = {
            "id": tenant_id,
            "name": f"Test Tenant {tenant_id}",
            "domain": f"{tenant_id}.example.com",
            "is_active": True,
            "settings": {},
            "created_at": "2023-01-01T00:00:00Z"
        }

        default_tenant.update(kwargs)
        self.mock_tenants[tenant_id] = default_tenant
        return default_tenant

    def create_mock_database_session(self):
        """Create mock database session for dependency injection."""
        if not self.mock_db_session:
            self.mock_db_session = AsyncMock()
            self.mock_db_session.begin = AsyncMock()
            self.mock_db_session.commit = AsyncMock()
            self.mock_db_session.rollback = AsyncMock()
            self.mock_db_session.close = AsyncMock()

        return self.mock_db_session

    def create_auth_headers(self, user: dict[str, Any]) -> dict[str, str]:
        """Create authorization headers for authenticated requests."""
        # Mock JWT token (in real implementation, would use actual JWT)
        mock_token = f"Bearer mock.jwt.token.{user['user_id']}"
        return {
            "Authorization": mock_token,
            "Content-Type": "application/json",
            "X-Tenant-ID": user.get("tenant_id", "test-tenant")
        }

    def mock_current_user_dependency(self, user: dict[str, Any]):
        """Create dependency override for current user authentication."""
        async def override_get_current_user():
            return user

        return override_get_current_user

    def mock_current_tenant_dependency(self, tenant_id: str):
        """Create dependency override for current tenant."""
        async def override_get_current_tenant():
            return tenant_id

        return override_get_current_tenant

    def mock_database_dependency(self):
        """Create dependency override for database session."""
        async def override_get_async_db():
            return self.create_mock_database_session()

        return override_get_async_db

    def assert_response_status(self, response, expected_status: int):
        """Assert response has expected status code."""
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )

    def assert_response_json(self, response, expected_keys: list[str] = None):
        """Assert response is valid JSON with expected keys."""
        assert response.headers.get("content-type", "").startswith("application/json")

        json_data = response.json()
        assert isinstance(json_data, dict)

        if expected_keys:
            for key in expected_keys:
                assert key in json_data, f"Expected key '{key}' not found in response"

        return json_data

    def assert_validation_error(self, response, field_name: Optional[str] = None):
        """Assert response is a validation error (422)."""
        self.assert_response_status(response, 422)

        json_data = response.json()
        assert "detail" in json_data

        if field_name:
            # Check if the field is mentioned in validation errors
            detail_str = json.dumps(json_data["detail"])
            assert field_name in detail_str, f"Field '{field_name}' not found in validation errors"

    def assert_authentication_error(self, response):
        """Assert response is authentication error (401)."""
        self.assert_response_status(response, 401)

    def assert_authorization_error(self, response):
        """Assert response is authorization error (403)."""
        self.assert_response_status(response, 403)

    def assert_not_found_error(self, response):
        """Assert response is not found error (404)."""
        self.assert_response_status(response, 404)


class AsyncAPITestBase(APITestBase):
    """Extended API test base for async client testing."""

    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()

    async def create_authenticated_async_client(
        self,
        app: FastAPI,
        user: dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> AsyncClient:
        """Create async client with authentication setup."""
        # Override dependencies
        from dotmac_shared.api.dependencies import (
            get_async_db,
            get_current_tenant,
            get_current_user,
        )

        app.dependency_overrides[get_current_user] = self.mock_current_user_dependency(user)
        app.dependency_overrides[get_current_tenant] = self.mock_current_tenant_dependency(
            tenant_id or user.get("tenant_id", "test-tenant")
        )
        app.dependency_overrides[get_async_db] = self.mock_database_dependency()

        return AsyncClient(app=app, base_url="http://test")

    async def make_authenticated_request(
        self,
        client: AsyncClient,
        method: str,
        url: str,
        user: dict[str, Any],
        **kwargs
    ):
        """Make authenticated request with proper headers."""
        headers = kwargs.pop("headers", {})
        auth_headers = self.create_auth_headers(user)
        headers.update(auth_headers)

        return await getattr(client, method.lower())(url, headers=headers, **kwargs)


class RouterTestBase(APITestBase):
    """Specialized base for testing individual routers."""

    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()

    def setup_router_test(
        self,
        router,
        dependencies_override: Optional[dict] = None,
        user: Optional[dict[str, Any]] = None
    ) -> TestClient:
        """Setup test client for a specific router."""
        app = self.create_test_app([router], dependencies_override)

        # Setup default authentication if user provided
        if user:
            from dotmac_shared.api.dependencies import (
                get_async_db,
                get_current_tenant,
                get_current_user,
            )

            app.dependency_overrides[get_current_user] = self.mock_current_user_dependency(user)
            app.dependency_overrides[get_current_tenant] = self.mock_current_tenant_dependency(
                user.get("tenant_id", "test-tenant")
            )
            app.dependency_overrides[get_async_db] = self.mock_database_dependency()

        return self.create_test_client(app)

    def test_router_endpoints(self, router) -> dict[str, Any]:
        """Analyze router endpoints for testing."""
        endpoints = {}

        for route in router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    if method not in ['HEAD', 'OPTIONS']:  # Skip meta methods
                        endpoint_key = f"{method} {route.path}"
                        endpoints[endpoint_key] = {
                            "method": method,
                            "path": route.path,
                            "endpoint": route.endpoint,
                            "name": getattr(route, 'name', 'unnamed'),
                            "dependencies": getattr(route, 'dependencies', [])
                        }

        return endpoints


class CRUDTestBase(RouterTestBase):
    """Specialized base for testing CRUD endpoints."""

    def setup_method(self):
        """Setup method called before each test."""
        super().setup_method()

    def test_crud_endpoints(
        self,
        client: TestClient,
        base_path: str,
        create_data: dict[str, Any],
        update_data: dict[str, Any],
        user: dict[str, Any],
        entity_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Test standard CRUD operations on endpoints."""
        results = {}
        entity_id = entity_id or str(uuid4())
        headers = self.create_auth_headers(user)

        # Test CREATE (POST)
        create_response = client.post(f"{base_path}/", json=create_data, headers=headers)
        results["create"] = {
            "status": create_response.status_code,
            "success": create_response.status_code == 201,
            "data": create_response.json() if create_response.status_code < 400 else None
        }

        # Test LIST (GET)
        list_response = client.get(f"{base_path}/", headers=headers)
        results["list"] = {
            "status": list_response.status_code,
            "success": list_response.status_code == 200,
            "data": list_response.json() if list_response.status_code < 400 else None
        }

        # Test GET by ID
        get_response = client.get(f"{base_path}/{entity_id}", headers=headers)
        results["get"] = {
            "status": get_response.status_code,
            "success": get_response.status_code == 200,
            "data": get_response.json() if get_response.status_code < 400 else None
        }

        # Test UPDATE (PUT)
        update_response = client.put(f"{base_path}/{entity_id}", json=update_data, headers=headers)
        results["update"] = {
            "status": update_response.status_code,
            "success": update_response.status_code == 200,
            "data": update_response.json() if update_response.status_code < 400 else None
        }

        # Test DELETE
        delete_response = client.delete(f"{base_path}/{entity_id}", headers=headers)
        results["delete"] = {
            "status": delete_response.status_code,
            "success": delete_response.status_code in [200, 204],
            "data": delete_response.json() if delete_response.status_code < 400 and delete_response.text else None
        }

        return results

    def assert_crud_operations(self, results: dict[str, Any], expected_failures: list[str] = None):
        """Assert CRUD operations completed successfully."""
        expected_failures = expected_failures or []

        for operation, result in results.items():
            if operation in expected_failures:
                continue

            assert result["success"], (
                f"CRUD operation '{operation}' failed with status {result['status']}"
            )
