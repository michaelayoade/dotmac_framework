"""
Test configuration and fixtures for dotmac-application tests.

Provides common test fixtures, configuration, and utilities for testing
the application factory package.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock provider fixtures
@pytest.fixture
def mock_security_provider():
    """Mock security provider for testing."""
    provider = Mock()
    provider.apply_jwt_authentication = Mock()
    provider.apply_csrf_protection = Mock()
    provider.apply_rate_limiting = Mock()
    return provider


@pytest.fixture
def mock_tenant_provider():
    """Mock tenant boundary provider for testing."""
    provider = Mock()
    provider.apply_tenant_security = Mock()
    provider.apply_tenant_isolation = Mock()
    return provider


@pytest.fixture
def mock_observability_provider():
    """Mock observability provider for testing."""
    provider = Mock()
    provider.apply_metrics = Mock()
    provider.apply_tracing = Mock()
    provider.apply_logging = Mock()
    return provider


@pytest.fixture
def mock_providers(mock_security_provider, mock_tenant_provider, mock_observability_provider):
    """Complete set of mock providers."""
    from dotmac.application import Providers
    
    return Providers(
        security=mock_security_provider,
        tenant=mock_tenant_provider,
        observability=mock_observability_provider
    )


# Configuration fixtures
@pytest.fixture
def basic_config():
    """Basic platform configuration for testing."""
    from dotmac.application import PlatformConfig
    
    return PlatformConfig(
        platform_name="test_platform",
        title="Test Platform",
        description="Test platform description",
        version="1.0.0"
    )


@pytest.fixture
def management_config():
    """Management platform configuration for testing."""
    from dotmac.application import PlatformConfig, DeploymentContext, DeploymentMode
    
    return PlatformConfig(
        platform_name="management_platform",
        title="Management Platform",
        description="Management platform description",
        deployment_context=DeploymentContext(
            mode=DeploymentMode.MANAGEMENT_PLATFORM
        )
    )


@pytest.fixture
def tenant_config():
    """Tenant container configuration for testing."""
    from dotmac.application import TenantConfig, DeploymentContext, DeploymentMode
    
    return TenantConfig(
        tenant_id="test-tenant",
        deployment_context=DeploymentContext(
            mode=DeploymentMode.TENANT_CONTAINER,
            tenant_id="test-tenant"
        )
    )


@pytest.fixture
def development_config():
    """Development mode configuration for testing."""
    from dotmac.application import PlatformConfig, DeploymentContext, DeploymentMode
    
    return PlatformConfig(
        platform_name="dev_platform",
        title="Development Platform",
        description="Development platform description",
        deployment_context=DeploymentContext(
            mode=DeploymentMode.DEVELOPMENT
        )
    )


# Application fixtures
@pytest.fixture
def test_app(basic_config):
    """Basic test application."""
    from dotmac.application import create_app
    
    return create_app(basic_config)


@pytest.fixture
def test_client(test_app):
    """Test client for basic test application."""
    from fastapi.testclient import TestClient
    
    return TestClient(test_app)


@pytest.fixture
def management_app(management_config):
    """Management platform test application."""
    from dotmac.application import create_management_platform_app
    
    return create_management_platform_app(management_config)


@pytest.fixture
def isp_app(tenant_config):
    """ISP framework test application."""
    from dotmac.application import create_isp_framework_app
    
    return create_isp_framework_app(tenant_config=tenant_config)


# Mock utilities
@pytest.fixture
def mock_router():
    """Mock FastAPI router for testing."""
    from fastapi import APIRouter
    
    router = APIRouter()
    
    @router.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    return router


@pytest.fixture
def mock_module(mock_router):
    """Mock module with router for testing."""
    module = Mock()
    module.router = mock_router
    return module


# Async utilities
@pytest.fixture
def mock_async_task():
    """Mock async task for testing lifecycle operations."""
    task = AsyncMock()
    task.return_value = None
    return task


@pytest.fixture
def failing_async_task():
    """Mock failing async task for testing error handling."""
    task = AsyncMock()
    task.side_effect = RuntimeError("Task failed")
    return task


# Helper functions
def assert_health_endpoint_response(response_data: Dict[str, Any], expected_status: str = "healthy"):
    """Assert health endpoint response structure and content."""
    assert "status" in response_data
    assert response_data["status"] == expected_status
    assert "timestamp" in response_data
    assert isinstance(response_data["timestamp"], str)


def assert_platform_info_response(response_data: Dict[str, Any], config):
    """Assert platform info response structure and content."""
    assert "platform_name" in response_data
    assert "title" in response_data
    assert "description" in response_data
    assert "version" in response_data
    
    assert response_data["platform_name"] == config.platform_name
    assert response_data["title"] == config.title
    assert response_data["description"] == config.description


def assert_standard_endpoints_exist(app):
    """Assert that standard endpoints are registered in the app."""
    routes = [route.path for route in app.routes]
    
    expected_endpoints = [
        "/",
        "/health",
        "/health/live", 
        "/health/ready",
        "/health/startup",
        "/favicon.ico"
    ]
    
    for endpoint in expected_endpoints:
        assert endpoint in routes, f"Missing standard endpoint: {endpoint}"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


# Test data generators
@pytest.fixture
def router_configs():
    """Generate router configurations for testing."""
    from dotmac.application import RouterConfig
    
    return [
        RouterConfig(
            module_path="test_app.routers.auth",
            prefix="/api/v1/auth",
            required=True,
            tags=["authentication"]
        ),
        RouterConfig(
            module_path="test_app.routers.users",
            prefix="/api/v1/users",
            required=False,
            tags=["users"]
        ),
        RouterConfig(
            module_path="test_app.modules",
            prefix="/api/v1",
            auto_discover=True,
            tags=["api"]
        )
    ]


@pytest.fixture
def startup_tasks():
    """Generate startup tasks for testing."""
    return [
        "initialize_database",
        "setup_ssl_certificates",
        "configure_monitoring",
        "load_initial_data"
    ]


@pytest.fixture
def shutdown_tasks():
    """Generate shutdown tasks for testing."""
    return [
        "cleanup_resources",
        "close_database_connections",
        "save_application_state",
        "flush_logs"
    ]