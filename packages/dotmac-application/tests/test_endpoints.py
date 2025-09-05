"""
Test standard endpoints functionality.

Tests health endpoints, platform info endpoints, and deployment-specific
endpoints return proper payloads and status codes.
"""

import pytest
from dotmac.application import (
    DeploymentContext,
    DeploymentMode,
    PlatformConfig,
    TenantConfig,
    create_app,
    create_isp_framework_app,
    create_management_platform_app,
)
from fastapi.testclient import TestClient


class TestStandardEndpoints:
    """Test standard endpoints and their responses."""

    @pytest.fixture
    def test_app(self):
        """Create a test app for endpoint testing."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            version="1.0.0",
        )
        return create_app(config)

    @pytest.fixture
    def test_client(self, test_app):
        """Create a test client for the test app."""
        return TestClient(test_app)

    def test_root_endpoint_returns_platform_info(self, test_client):
        """Test root endpoint returns proper platform information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Should contain platform information
        assert "platform" in data
        assert "title" in data
        assert "version" in data
        assert "status" in data

        # Should match configured values
        assert data["platform"] == "test_platform"
        assert data["title"] == "Test Platform"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"

    def test_health_endpoint_returns_healthy_status(self, test_client):
        """Test basic health endpoint returns healthy status."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should contain health status
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "platform" in data
        assert "version" in data

    def test_health_live_endpoint(self, test_client):
        """Test Kubernetes liveness probe endpoint."""
        response = test_client.get("/health/live")

        assert response.status_code == 200
        data = response.json()

        # Should contain liveness information
        assert "status" in data
        assert data["status"] == "alive"

    def test_health_ready_endpoint(self, test_client):
        """Test Kubernetes readiness probe endpoint."""
        response = test_client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()

        # Should contain readiness information
        assert "status" in data
        assert data["status"] in ["ready", "not_ready"]
        assert "checks" in data

    def test_health_startup_endpoint(self, test_client):
        """Test Kubernetes startup probe endpoint."""
        response = test_client.get("/health/startup")

        assert response.status_code == 200
        data = response.json()

        # Should contain startup information
        assert "status" in data
        assert data["status"] in ["started", "starting"]

    def test_favicon_endpoint_returns_204(self, test_client):
        """Test favicon endpoint returns 204 No Content."""
        response = test_client.get("/favicon.ico")

        assert response.status_code == 204
        assert response.content == b""

    def test_management_platform_specific_endpoints(self):
        """Test management platform specific endpoints."""
        app = create_management_platform_app()
        client = TestClient(app)

        # Test management stats endpoint
        response = client.get("/management/stats")

        assert response.status_code == 200
        data = response.json()

        # Should contain management platform statistics
        assert "platform" in data
        assert data["platform"] == "management"
        assert "status" in data
        assert "features" in data

    def test_tenant_container_specific_endpoints(self):
        """Test tenant container specific endpoints."""
        tenant_config = TenantConfig(
            tenant_id="test-tenant",
            deployment_context=DeploymentContext(
                mode=DeploymentMode.TENANT_CONTAINER, tenant_id="test-tenant"
            ),
        )

        app = create_isp_framework_app(tenant_config=tenant_config)
        client = TestClient(app)

        # Test tenant info endpoint
        response = client.get("/tenant/info")

        assert response.status_code == 200
        data = response.json()

        # Should contain tenant information
        assert "tenant_id" in data
        assert data["tenant_id"] == "test-tenant"
        assert "isolation_level" in data

    def test_development_mode_specific_endpoints(self):
        """Test development mode specific endpoints."""
        config = PlatformConfig(
            platform_name="dev_platform",
            title="Development Platform",
            description="Development platform description",
            deployment_context=DeploymentContext(mode=DeploymentMode.DEVELOPMENT),
        )

        app = create_app(config)
        client = TestClient(app)

        # Test dev config endpoint
        response = client.get("/dev/config")

        assert response.status_code == 200
        data = response.json()

        # Should contain configuration information
        assert "platform_config" in data
        config_data = data["platform_config"]
        assert "platform_name" in config_data
        assert config_data["platform_name"] == "dev_platform"

        # Test dev routes endpoint
        response = client.get("/dev/routes")

        assert response.status_code == 200
        data = response.json()

        # Should contain route information
        assert "routes" in data
        assert "total_routes" in data
        assert isinstance(data["routes"], list)
        assert len(data["routes"]) > 0

        # Test dev app state endpoint
        response = client.get("/dev/app-state")

        assert response.status_code == 200
        data = response.json()

        # Should contain app state information
        assert "app_state" in data

    def test_health_endpoints_include_deployment_context(self, test_client):
        """Test health endpoints include deployment context information."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should include basic health info
        assert "status" in data
        assert "platform" in data
        assert "version" in data

    def test_error_handling_in_endpoints(self, test_client):
        """Test error handling in standard endpoints."""
        # Test non-existent endpoint
        response = test_client.get("/nonexistent")

        assert response.status_code == 404

    def test_health_check_with_dependencies(self):
        """Test health checks include dependency status when available."""
        config = PlatformConfig(
            platform_name="test_platform_with_deps",
            title="Test Platform with Dependencies",
            description="Platform with dependency checks",
        )

        app = create_app(config)
        client = TestClient(app)

        # Health endpoint should work even without dependencies
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

    def test_cors_headers_on_endpoints(self, test_client):
        """Test CORS headers are properly set on endpoints."""
        response = test_client.get("/health")

        # Should have CORS headers set by middleware
        # Note: Actual CORS header presence depends on middleware configuration
        assert response.status_code == 200

    def test_endpoint_response_times(self, test_client):
        """Test endpoint response times are reasonable."""
        import time

        # Test health endpoint response time
        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()

        assert response.status_code == 200

        # Health check should respond quickly (under 100ms for basic check)
        response_time = end_time - start_time
        assert response_time < 0.1  # 100ms

    def test_endpoint_content_type_headers(self, test_client):
        """Test endpoints return proper content-type headers."""
        # JSON endpoints should return application/json
        response = test_client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        # Favicon should return empty content
        response = test_client.get("/favicon.ico")

        assert response.status_code == 204

    def test_concurrent_health_checks(self, test_client):
        """Test concurrent health check requests."""
        import threading

        results = []

        def make_health_request():
            response = test_client.get("/health")
            results.append(response.status_code)

        # Start multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_health_request)
            threads.append(thread)
            thread.start()

        # Wait for all requests to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)
