"""
Integration tests for API endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from dotmac_core_events.runtime import create_app
from dotmac_core_events.runtime.config import RuntimeConfig


@pytest.fixture
def test_config():
    """Test configuration."""
    return RuntimeConfig(
        adapter_type="memory",
        adapter_config={},
        debug=True,
        enable_background_tasks=False
    )


@pytest.fixture
def test_app(test_config):
    """Create test FastAPI app."""
    with patch("dotmac_core_events.runtime.app_factory.initialize_sdks") as mock_init:
        # Mock SDK initialization
        mock_event_bus = AsyncMock()
        mock_schema_registry = AsyncMock()
        mock_init.return_value = (mock_event_bus, mock_schema_registry, None)

        app = create_app(test_config)
        return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestEventsAPI:
    """Test Events API endpoints."""

    def test_publish_event(self, client):
        """Test publishing an event."""
        response = client.post(
            "/api/v1/events/publish",
            json={
                "event_type": "user.created",
                "data": {"user_id": "123", "email": "test@example.com"}
            },
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_publish_event_missing_tenant(self, client):
        """Test publishing without tenant ID."""
        response = client.post(
            "/api/v1/events/publish",
            json={
                "event_type": "user.created",
                "data": {"user_id": "123"}
            }
        )

        assert response.status_code == 422  # Validation error

    def test_get_event_history(self, client):
        """Test getting event history."""
        response = client.get(
            "/api/v1/events/history",
            params={"event_type": "user.created", "limit": 10},
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "pagination" in data


class TestSchemasAPI:
    """Test Schemas API endpoints."""

    def test_register_schema(self, client):
        """Test registering a schema."""
        schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["user_id", "email"]
        }

        response = client.post(
            "/api/v1/schemas/user.created",
            json={
                "version": "1.0",
                "schema": schema,
                "compatibility_level": "BACKWARD"
            },
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_get_schema(self, client):
        """Test getting a schema."""
        response = client.get(
            "/api/v1/schemas/user.created/1.0",
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200

    def test_validate_data(self, client):
        """Test validating data against schema."""
        response = client.post(
            "/api/v1/schemas/user.created/validate",
            json={
                "data": {"user_id": "123", "email": "test@example.com"}
            },
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data


class TestHealthAPI:
    """Test Health API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_readiness_probe(self, client):
        """Test readiness probe."""
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data

    def test_liveness_probe(self, client):
        """Test liveness probe."""
        response = client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert "alive" in data


class TestAdminAPI:
    """Test Admin API endpoints."""

    def test_create_topic(self, client):
        """Test creating a topic."""
        response = client.post(
            "/api/v1/admin/topics",
            json={
                "event_type": "order.created",
                "partitions": 3,
                "replication_factor": 2
            },
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "topic" in data

    def test_list_topics(self, client):
        """Test listing topics."""
        response = client.get(
            "/api/v1/admin/topics",
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_config(self, client):
        """Test getting configuration."""
        response = client.get(
            "/api/v1/admin/config",
            headers={"X-Tenant-ID": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data
        assert "version" in data
