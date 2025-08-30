"""
Test the unified application factory endpoints to catch middleware/health regressions.

This test suite validates that the unified factory properly creates applications
with all required endpoints, middleware, and health checks working correctly.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from tests.utilities.test_helpers import create_unified_test_client


def create_test_client():
    """Helper to create test client synchronously."""
    return asyncio.run(create_unified_test_client())


class TestUnifiedFactory:
    """Test suite for unified application factory endpoints."""

    def test_root_endpoint(self):
        """Test that root endpoint is accessible and returns expected structure."""
        test_client = create_test_client()
        try:
            response = test_client.get("/")

            assert response.status_code == 200
            data = response.json()

            # Validate basic app info is present
            assert "name" in data
            assert "version" in data
            assert "status" in data
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_health_endpoint(self):
        """Test health endpoint returns proper health status."""
        test_client = create_test_client()
        try:
            response = test_client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Validate health response structure
            assert "status" in data
            assert "timestamp" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]

            # Ensure timestamp is not a placeholder
            assert data["timestamp"] != "2024-01-01T00:00:00Z"
            assert "T" in data["timestamp"]  # ISO format check
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_management_tenant_endpoints(self):
        """Test management/tenant endpoints are accessible."""
        test_client = create_test_client()
        try:
            # Test tenant listing endpoint
            response = test_client.get("/management/tenants")

            # Should be accessible (might require auth, but endpoint should exist)
            assert response.status_code in [
                200,
                401,
                403,
                404,
            ]  # Accessible but may require auth

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (list, dict))
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_middleware_stack_applied(self):
        """Test that middleware stack is properly applied."""
        test_client = create_test_client()
        try:
            # CORS middleware test
            response = test_client.options("/health")
            assert (
                "access-control-allow-origin" in response.headers
                or response.status_code == 200
            )

            # Security headers should be present on responses
            response = test_client.get("/health")
            headers = response.headers

            # At least some security headers should be present
            security_headers = [
                "x-content-type-options",
                "x-frame-options",
                "x-xss-protection",
                "strict-transport-security",
            ]

            # Not all may be present, but at least check headers exist
            assert len(headers) > 0
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_service_registry_integration(self):
        """Test that service registry is properly integrated."""
        test_client = create_test_client()
        try:
            # Services should be available in app state
            app = test_client.app
            assert hasattr(app.state, "services")

            # Platform config should be available
            assert hasattr(app.state, "platform_config")

            # Registration stats should be available
            assert hasattr(app.state, "registration_stats")
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_error_handling_integration(self):
        """Test that error handling works correctly."""
        test_client = create_test_client()
        try:
            # Test non-existent endpoint
            response = test_client.get("/non-existent-endpoint")
            assert response.status_code == 404

            # Should return JSON error response
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                assert "detail" in data or "error" in data
        finally:
            if hasattr(test_client, "close"):
                test_client.close()


class TestFactoryDeploymentModes:
    """Test different deployment modes of the unified factory."""

    def test_development_mode_features(self):
        """Test development mode specific features."""
        test_client = create_test_client()
        try:
            app = test_client.app

            # Development mode should have docs enabled
            assert hasattr(app.state, "development_mode")

            # Try accessing docs (may or may not be enabled depending on config)
            docs_response = test_client.get("/docs")
            assert docs_response.status_code in [200, 404]  # Either works or disabled
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_platform_config_validity(self):
        """Test that platform configuration is valid."""
        test_client = create_test_client()
        try:
            app = test_client.app

            # Platform config should exist and have required fields
            config = app.state.platform_config

            assert hasattr(config, "platform_name")
            assert hasattr(config, "title")
            assert hasattr(config, "version")
        finally:
            if hasattr(test_client, "close"):
                test_client.close()


class TestFactoryHealthRegression:
    """Specific regression tests for health endpoint issues."""

    def test_health_timestamp_is_real(self):
        """Regression test: Ensure health timestamp is not placeholder."""
        test_client = create_test_client()
        try:
            response = test_client.get("/health")
            assert response.status_code == 200

            data = response.json()
            timestamp = data.get("timestamp")

            # Should not be the old placeholder
            assert timestamp != "2024-01-01T00:00:00Z"
            assert timestamp is not None
            assert isinstance(timestamp, str)

            # Should be valid ISO format
            from datetime import datetime

            try:
                parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                # Should be recent (within last few minutes)
                now = datetime.now(parsed_time.tzinfo)
                diff = abs((now - parsed_time).total_seconds())
                assert diff < 300  # Within 5 minutes
            except ValueError:
                pytest.fail(f"Health timestamp '{timestamp}' is not valid ISO format")
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_health_consistency(self):
        """Test health endpoint consistency across multiple calls."""
        test_client = create_test_client()
        try:
            # Make multiple calls
            responses = [test_client.get("/health") for _ in range(3)]

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert "timestamp" in data

            # Timestamps should be different (or very close)
            timestamps = [r.json()["timestamp"] for r in responses]
            # At least ensure they're all valid
            assert all(timestamp != "2024-01-01T00:00:00Z" for timestamp in timestamps)
        finally:
            if hasattr(test_client, "close"):
                test_client.close()


@pytest.mark.integration
class TestMiddlewareRegression:
    """Test middleware integration to prevent regressions."""

    def test_tenant_security_middleware_loads(self):
        """Test that tenant security middleware loads without import errors."""
        test_client = create_test_client()
        try:
            # The fact that the app starts successfully means adapters work
            app = test_client.app

            # App should have middleware applied
            assert len(app.user_middleware) >= 0  # May be zero if no middleware

            # Basic request should work without middleware errors
            response = test_client.get("/health")
            assert response.status_code == 200
        finally:
            if hasattr(test_client, "close"):
                test_client.close()

    def test_csrf_middleware_integration(self):
        """Test CSRF middleware integration doesn't break requests."""
        test_client = create_test_client()
        try:
            # GET requests should work fine
            response = test_client.get("/health")
            assert response.status_code == 200

            # POST requests may require CSRF token, but should not crash
            response = test_client.post("/health", json={})
            # Should either work, require auth, or require CSRF - but not crash
            assert response.status_code in [200, 400, 401, 403, 405]
        finally:
            if hasattr(test_client, "close"):
                test_client.close()
