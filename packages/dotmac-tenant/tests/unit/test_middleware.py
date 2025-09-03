"""
Unit tests for tenant middleware.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import time

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from dotmac.tenant.middleware import TenantMiddleware, TenantSecurityMiddleware
from dotmac.tenant.exceptions import (
    TenantNotFoundError,
    TenantResolutionError,
    TenantSecurityError,
)


class TestTenantMiddleware:
    """Test TenantMiddleware functionality."""
    
    def test_middleware_initialization(self, tenant_config):
        """Test middleware initialization with config."""
        app = FastAPI()
        middleware = TenantMiddleware(app, config=tenant_config)
        
        assert middleware.config == tenant_config
        assert middleware.resolver is not None
        assert middleware._request_count == 0
        assert middleware._error_count == 0
    
    def test_middleware_with_custom_resolver(self, tenant_config, tenant_resolver):
        """Test middleware with custom resolver."""
        app = FastAPI()
        middleware = TenantMiddleware(
            app, 
            config=tenant_config, 
            resolver=tenant_resolver
        )
        
        assert middleware.resolver == tenant_resolver
    
    @pytest.mark.asyncio
    async def test_successful_tenant_resolution(self, test_app_with_middleware):
        """Test successful tenant resolution through middleware."""
        with TestClient(test_app_with_middleware) as client:
            response = client.get(
                "/api/tenant-info",
                headers={"Host": "tenant1.example.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant1"
        assert "X-Tenant-ID" in response.headers
        assert response.headers["X-Tenant-ID"] == "tenant1"
    
    @pytest.mark.asyncio
    async def test_tenant_not_found_error_handling(self, tenant_config):
        """Test handling of tenant not found errors."""
        app = FastAPI()
        config = tenant_config.copy()
        config.fallback_tenant_id = None  # Disable fallback
        
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get(
                "/test",
                headers={"Host": "unknown.example.com"}
            )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "tenant_not_found"
        assert "Could not identify tenant" in data["message"]
    
    def test_should_skip_resolution_health_checks(self, test_app_with_middleware):
        """Test skipping tenant resolution for health check endpoints."""
        middleware = TenantMiddleware(FastAPI())
        
        mock_request = Mock()
        mock_request.url.path = "/health"
        mock_request.method = "GET"
        
        assert middleware._should_skip_resolution(mock_request) is True
        
        mock_request.url.path = "/api/data"
        assert middleware._should_skip_resolution(mock_request) is False
    
    def test_should_skip_resolution_options(self, test_app_with_middleware):
        """Test skipping tenant resolution for OPTIONS requests."""
        middleware = TenantMiddleware(FastAPI())
        
        mock_request = Mock()
        mock_request.url.path = "/api/data"
        mock_request.method = "OPTIONS"
        
        assert middleware._should_skip_resolution(mock_request) is True
        
        mock_request.method = "GET"
        assert middleware._should_skip_resolution(mock_request) is False
    
    @pytest.mark.asyncio
    async def test_custom_error_handler(self, tenant_config):
        """Test custom error handler for tenant errors."""
        def custom_error_handler(request, error):
            return JSONResponse(
                status_code=418,
                content={"custom_error": str(error)}
            )
        
        app = FastAPI()
        config = tenant_config.copy()
        config.fallback_tenant_id = None
        
        app.add_middleware(
            TenantMiddleware, 
            config=config,
            error_handler=custom_error_handler
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get(
                "/test",
                headers={"Host": "unknown.example.com"}
            )
        
        assert response.status_code == 418
        data = response.json()
        assert "custom_error" in data
    
    def test_get_metrics(self, tenant_config):
        """Test middleware metrics collection."""
        middleware = TenantMiddleware(FastAPI(), config=tenant_config)
        
        # Simulate some requests and errors
        middleware._request_count = 100
        middleware._error_count = 5
        middleware._resolution_times = [0.001, 0.002, 0.003, 0.002, 0.001]
        
        metrics = middleware.get_metrics()
        
        assert metrics["total_requests"] == 100
        assert metrics["total_errors"] == 5
        assert metrics["error_rate"] == 0.05
        assert metrics["avg_resolution_time_ms"] == 1.8  # Average of resolution times in ms
        assert len(metrics["recent_resolution_times"]) == 5


class TestTenantSecurityMiddleware:
    """Test TenantSecurityMiddleware functionality."""
    
    def test_security_middleware_initialization(self, tenant_config):
        """Test security middleware initialization."""
        app = FastAPI()
        middleware = TenantSecurityMiddleware(app, config=tenant_config)
        
        assert middleware.config == tenant_config
        assert middleware.security_enforcer is None
    
    @pytest.mark.asyncio
    async def test_security_middleware_with_enforcer(self, tenant_config, security_enforcer):
        """Test security middleware with enforcer."""
        app = FastAPI()
        
        # Mock security enforcer validation
        security_enforcer.validate_tenant_access = AsyncMock()
        
        app.add_middleware(TenantMiddleware, config=tenant_config)
        app.add_middleware(
            TenantSecurityMiddleware, 
            config=tenant_config,
            security_enforcer=security_enforcer
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get(
                "/test",
                headers={"Host": "tenant1.example.com"}
            )
        
        assert response.status_code == 200
        security_enforcer.validate_tenant_access.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_security_violation_handling(self, tenant_config):
        """Test handling of security violations."""
        app = FastAPI()
        
        # Mock security enforcer that raises violation
        mock_enforcer = Mock()
        mock_enforcer.validate_tenant_access = AsyncMock(
            side_effect=TenantSecurityError(
                "Access denied",
                "tenant1",
                "test_violation"
            )
        )
        
        app.add_middleware(TenantMiddleware, config=tenant_config)
        app.add_middleware(
            TenantSecurityMiddleware,
            config=tenant_config,
            security_enforcer=mock_enforcer
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get(
                "/test",
                headers={"Host": "tenant1.example.com"}
            )
        
        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "tenant_access_denied"
        assert "Access denied for tenant" in data["message"]
    
    @pytest.mark.asyncio
    async def test_missing_tenant_context_enforcement(self, tenant_config):
        """Test enforcement when tenant context is missing."""
        app = FastAPI()
        
        # Create config that enforces tenant isolation
        config = tenant_config.copy()
        config.enforce_tenant_isolation = True
        
        # Add only security middleware (no tenant middleware)
        app.add_middleware(TenantSecurityMiddleware, config=config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get("/test")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "tenant_context_missing"


class TestMiddlewareIntegration:
    """Test integration between tenant and security middleware."""
    
    @pytest.mark.asyncio
    async def test_middleware_chain_success(self, tenant_config, security_enforcer):
        """Test successful request through middleware chain."""
        app = FastAPI()
        
        # Mock successful security validation
        security_enforcer.validate_tenant_access = AsyncMock()
        
        # Add both middlewares
        app.add_middleware(
            TenantSecurityMiddleware,
            config=tenant_config,
            security_enforcer=security_enforcer
        )
        app.add_middleware(TenantMiddleware, config=tenant_config)
        
        @app.get("/api/data")
        async def get_data(request: Request):
            tenant = getattr(request.state, 'tenant', None)
            return {
                "tenant_id": tenant.tenant_id if tenant else None,
                "data": "test"
            }
        
        with TestClient(app) as client:
            response = client.get(
                "/api/data",
                headers={"Host": "tenant1.example.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant1"
        assert data["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_middleware_error_propagation(self, tenant_config):
        """Test error propagation through middleware chain."""
        app = FastAPI()
        
        # Configure without fallback to force errors
        config = tenant_config.copy()
        config.fallback_tenant_id = None
        
        app.add_middleware(TenantSecurityMiddleware, config=config)
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        with TestClient(app) as client:
            response = client.get(
                "/test",
                headers={"Host": "unknown.example.com"}
            )
        
        # Should get tenant resolution error, not security error
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "tenant_not_found"


class TestMiddlewarePerformance:
    """Test middleware performance characteristics."""
    
    def test_metrics_tracking(self, tenant_config):
        """Test that middleware tracks performance metrics."""
        middleware = TenantMiddleware(FastAPI(), config=tenant_config)
        
        # Simulate tracking resolution times
        for time_ms in [1.5, 2.0, 1.8, 2.2, 1.9]:
            middleware._resolution_times.append(time_ms / 1000)  # Convert to seconds
        
        metrics = middleware.get_metrics()
        
        assert metrics["avg_resolution_time_ms"] == pytest.approx(1.88, rel=0.1)
        assert len(metrics["recent_resolution_times"]) == 5
    
    def test_metrics_rollover(self, tenant_config):
        """Test that metrics properly roll over old data."""
        middleware = TenantMiddleware(FastAPI(), config=tenant_config)
        
        # Add more than the limit of 100 measurements
        for i in range(150):
            middleware._resolution_times.append(i * 0.001)
        
        # Should keep only last 100
        assert len(middleware._resolution_times) == 100
        assert middleware._resolution_times[0] == 0.05  # 50 * 0.001
        assert middleware._resolution_times[-1] == 0.149  # 149 * 0.001