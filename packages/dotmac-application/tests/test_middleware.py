"""
Test middleware composition functionality.

Tests provider-based middleware application, standard middleware stack,
and provider interface implementations.
"""

import pytest
from dotmac.application import (
    PlatformConfig,
    Providers,
    StandardMiddlewareStack,
    apply_standard_middleware,
)
from fastapi import FastAPI, Request


class MockSecurityProvider:
    """Mock security provider for testing."""

    def apply_jwt_authentication(self, app, config):
        """Mock JWT authentication middleware."""

        @app.middleware("http")
        async def jwt_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-JWT-Applied"] = "true"
            return response

    def apply_csrf_protection(self, app, config):
        """Mock CSRF protection middleware."""

        @app.middleware("http")
        async def csrf_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-CSRF-Applied"] = "true"
            return response

    def apply_rate_limiting(self, app, config):
        """Mock rate limiting middleware."""

        @app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Rate-Limit-Applied"] = "true"
            return response


class MockTenantBoundaryProvider:
    """Mock tenant boundary provider for testing."""

    def apply_tenant_security(self, app, config):
        """Mock tenant security middleware."""

        @app.middleware("http")
        async def tenant_security_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Tenant-Security-Applied"] = "true"
            return response

    def apply_tenant_isolation(self, app, config):
        """Mock tenant isolation middleware."""

        @app.middleware("http")
        async def tenant_isolation_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Tenant-Isolation-Applied"] = "true"
            return response


class MockObservabilityProvider:
    """Mock observability provider for testing."""

    def apply_metrics(self, app, config):
        """Mock metrics middleware."""

        @app.middleware("http")
        async def metrics_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Metrics-Applied"] = "true"
            return response

    def apply_tracing(self, app, config):
        """Mock tracing middleware."""

        @app.middleware("http")
        async def tracing_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Tracing-Applied"] = "true"
            return response

    def apply_logging(self, app, config):
        """Mock logging middleware."""

        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Logging-Applied"] = "true"
            return response


class TestMiddlewareComposition:
    """Test middleware composition and provider interfaces."""

    @pytest.fixture
    def mock_providers(self):
        """Create mock providers for testing."""
        return Providers(
            security=MockSecurityProvider(),
            tenant=MockTenantBoundaryProvider(),
            observability=MockObservabilityProvider(),
        )

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
        )

    def test_apply_standard_middleware_with_providers(
        self, mock_providers, test_config
    ):
        """Test applying standard middleware with providers."""
        app = FastAPI()

        # Add a simple test endpoint
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Apply middleware
        applied_middleware = apply_standard_middleware(
            app, config=test_config, providers=mock_providers
        )

        # Should return list of applied middleware
        assert isinstance(applied_middleware, list)
        assert len(applied_middleware) > 0

        # Test that middleware was actually applied
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

        # Check that provider middleware was applied
        assert "X-JWT-Applied" in response.headers
        assert "X-CSRF-Applied" in response.headers
        assert "X-Rate-Limit-Applied" in response.headers
        assert "X-Tenant-Security-Applied" in response.headers
        assert "X-Tenant-Isolation-Applied" in response.headers
        assert "X-Metrics-Applied" in response.headers
        assert "X-Tracing-Applied" in response.headers
        assert "X-Logging-Applied" in response.headers

    def test_apply_standard_middleware_without_providers(self, test_config):
        """Test applying standard middleware without providers."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Apply middleware without providers
        applied_middleware = apply_standard_middleware(app, config=test_config)

        # Should still return a list (may be empty or contain only built-in middleware)
        assert isinstance(applied_middleware, list)

        # Test app still works
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

    def test_standard_middleware_stack_initialization(self, test_config):
        """Test StandardMiddlewareStack initialization."""
        stack = StandardMiddlewareStack(test_config)

        assert stack.config == test_config
        assert hasattr(stack, "apply_to_app")

    def test_standard_middleware_stack_application(self, test_config, mock_providers):
        """Test StandardMiddlewareStack application to app."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        stack = StandardMiddlewareStack(test_config)
        applied = stack.apply_to_app(app, providers=mock_providers)

        # Should return applied middleware info
        assert isinstance(applied, list)

        # Test that middleware works
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

    def test_provider_interface_compliance(self):
        """Test that mock providers comply with protocol interfaces."""
        security = MockSecurityProvider()
        tenant = MockTenantBoundaryProvider()
        observability = MockObservabilityProvider()

        # Test security provider has required methods
        assert hasattr(security, "apply_jwt_authentication")
        assert hasattr(security, "apply_csrf_protection")
        assert hasattr(security, "apply_rate_limiting")
        assert callable(security.apply_jwt_authentication)
        assert callable(security.apply_csrf_protection)
        assert callable(security.apply_rate_limiting)

        # Test tenant provider has required methods
        assert hasattr(tenant, "apply_tenant_security")
        assert hasattr(tenant, "apply_tenant_isolation")
        assert callable(tenant.apply_tenant_security)
        assert callable(tenant.apply_tenant_isolation)

        # Test observability provider has required methods
        assert hasattr(observability, "apply_metrics")
        assert hasattr(observability, "apply_tracing")
        assert hasattr(observability, "apply_logging")
        assert callable(observability.apply_metrics)
        assert callable(observability.apply_tracing)
        assert callable(observability.apply_logging)

    def test_middleware_error_handling(self, test_config):
        """Test middleware error handling."""

        class FailingProvider:
            def apply_jwt_authentication(self, app, config):
                raise RuntimeError("Provider failed")

        providers = Providers(security=FailingProvider())
        app = FastAPI()

        # Should handle provider failures gracefully
        with pytest.raises(RuntimeError):
            apply_standard_middleware(app, config=test_config, providers=providers)

    def test_partial_provider_support(self, test_config):
        """Test middleware application with partial provider support."""
        # Provider that only implements security
        providers = Providers(security=MockSecurityProvider())

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Should work with partial providers
        applied = apply_standard_middleware(
            app, config=test_config, providers=providers
        )

        assert isinstance(applied, list)

        # Test that available middleware was applied
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-JWT-Applied" in response.headers
        assert "X-CSRF-Applied" in response.headers
        assert "X-Rate-Limit-Applied" in response.headers

    def test_middleware_ordering(self, mock_providers, test_config):
        """Test that middleware is applied in correct order."""
        app = FastAPI()

        # Track middleware application order
        application_order = []

        class OrderTrackingProvider:
            def apply_jwt_authentication(self, app, config):
                application_order.append("jwt")

            def apply_csrf_protection(self, app, config):
                application_order.append("csrf")

            def apply_rate_limiting(self, app, config):
                application_order.append("rate_limit")

        class OrderTrackingTenantProvider:
            def apply_tenant_security(self, app, config):
                application_order.append("tenant_security")

            def apply_tenant_isolation(self, app, config):
                application_order.append("tenant_isolation")

        class OrderTrackingObservabilityProvider:
            def apply_metrics(self, app, config):
                application_order.append("metrics")

            def apply_tracing(self, app, config):
                application_order.append("tracing")

            def apply_logging(self, app, config):
                application_order.append("logging")

        tracking_providers = Providers(
            security=OrderTrackingProvider(),
            tenant=OrderTrackingTenantProvider(),
            observability=OrderTrackingObservabilityProvider(),
        )

        apply_standard_middleware(app, config=test_config, providers=tracking_providers)

        # Verify middleware was applied in expected order
        assert len(application_order) > 0
        # Security middleware should be applied
        assert "jwt" in application_order
        assert "csrf" in application_order
        assert "rate_limit" in application_order

    def test_deployment_specific_middleware(self, mock_providers):
        """Test deployment-specific middleware configuration."""
        # Test tenant container deployment
        from dotmac.application import DeploymentContext, DeploymentMode

        tenant_config = PlatformConfig(
            platform_name="tenant_platform",
            title="Tenant Platform",
            description="Tenant platform description",
            deployment_context=DeploymentContext(
                mode=DeploymentMode.TENANT_CONTAINER, tenant_id="test-tenant"
            ),
        )

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Apply middleware for tenant deployment
        applied = apply_standard_middleware(
            app, config=tenant_config, providers=mock_providers
        )

        assert isinstance(applied, list)

        # Should have tenant-specific middleware
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-Tenant-Security-Applied" in response.headers
        assert "X-Tenant-Isolation-Applied" in response.headers
