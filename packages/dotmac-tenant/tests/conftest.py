"""
Test configuration and fixtures for dotmac-tenant tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from dotmac.tenant import (
    TenantConfig,
    TenantContext,
    TenantIdentityResolver,
    TenantMiddleware,
    TenantResolutionStrategy,
)
from dotmac.tenant.boundary import TenantSecurityEnforcer


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tenant_config():
    """Default tenant configuration for tests."""
    return TenantConfig(
        resolution_strategy=TenantResolutionStrategy.HOST_BASED,
        fallback_tenant_id="test-tenant",
        enforce_tenant_isolation=True,
        host_tenant_mapping={
            "tenant1.example.com": "tenant1",
            "tenant2.example.com": "tenant2",
            "test.localhost": "test-tenant"
        },
        default_host_pattern="{tenant}.example.com"
    )


@pytest.fixture
def tenant_resolver(tenant_config):
    """Tenant identity resolver with test configuration."""
    return TenantIdentityResolver(tenant_config)


@pytest.fixture
def security_enforcer(tenant_config):
    """Tenant security enforcer for tests."""
    return TenantSecurityEnforcer(tenant_config)


@pytest.fixture
def sample_tenant_context():
    """Sample tenant context for testing."""
    return TenantContext(
        tenant_id="test-tenant",
        display_name="Test Tenant",
        resolution_method="test",
        resolved_from="fixture",
        request_id="test-request-123",
        security_level="standard",
        permissions=["read", "write"],
        context_data={"test_key": "test_value"}
    )


@pytest.fixture
def mock_request():
    """Mock FastAPI request object."""
    request = AsyncMock(spec=Request)
    request.headers = {
        "host": "tenant1.example.com",
        "user-agent": "test-client/1.0",
        "x-forwarded-for": "192.168.1.100"
    }
    request.method = "GET"
    request.url.path = "/api/test"
    request.url.scheme = "https"
    request.client.host = "192.168.1.100"
    request.state = AsyncMock()
    return request


@pytest.fixture
def test_app():
    """FastAPI test application."""
    app = FastAPI(title="Tenant Test App")
    
    @app.get("/")
    async def root():
        return {"message": "test"}
    
    @app.get("/api/tenant-info")
    async def tenant_info(request: Request):
        tenant = getattr(request.state, 'tenant', None)
        return {
            "tenant_id": tenant.tenant_id if tenant else None,
            "message": "tenant info"
        }
    
    return app


@pytest.fixture
def test_app_with_middleware(test_app, tenant_config):
    """Test app with tenant middleware configured."""
    test_app.add_middleware(TenantMiddleware, config=tenant_config)
    return test_app


@pytest.fixture
def client(test_app_with_middleware):
    """Test client with tenant middleware."""
    return TestClient(test_app_with_middleware)


@pytest.fixture
def multiple_tenant_contexts():
    """Multiple tenant contexts for testing."""
    return [
        TenantContext(
            tenant_id="tenant1",
            display_name="Tenant One",
            resolution_method="host",
            resolved_from="tenant1.example.com"
        ),
        TenantContext(
            tenant_id="tenant2", 
            display_name="Tenant Two",
            resolution_method="subdomain",
            resolved_from="tenant2.api.example.com"
        ),
        TenantContext(
            tenant_id="tenant3",
            display_name="Tenant Three",
            resolution_method="header",
            resolved_from="X-Tenant-ID: tenant3"
        )
    ]


@pytest.fixture
async def async_mock_engine():
    """Mock async SQLAlchemy engine."""
    from unittest.mock import AsyncMock
    engine = AsyncMock()
    engine.begin = AsyncMock()
    return engine


@pytest.fixture
def subdomain_config():
    """Configuration for subdomain-based tenant resolution."""
    return TenantConfig(
        resolution_strategy=TenantResolutionStrategy.SUBDOMAIN,
        base_domain="example.com",
        subdomain_position=0,
        fallback_tenant_id="default"
    )


@pytest.fixture
def header_config():
    """Configuration for header-based tenant resolution."""
    return TenantConfig(
        resolution_strategy=TenantResolutionStrategy.HEADER_BASED,
        tenant_header_name="X-Tenant-ID",
        require_tenant_header=True
    )


@pytest.fixture
def composite_config():
    """Configuration for composite tenant resolution."""
    return TenantConfig(
        resolution_strategy=TenantResolutionStrategy.COMPOSITE,
        tenant_header_name="X-Tenant-ID",
        host_tenant_mapping={
            "app.example.com": "main-tenant"
        },
        fallback_tenant_id="default"
    )