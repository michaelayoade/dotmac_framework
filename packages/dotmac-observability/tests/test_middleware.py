"""Tests for middleware module."""

from unittest.mock import MagicMock

import pytest

from dotmac_observability import MetricsCollector


class TestMiddlewareImports:
    """Test middleware import behavior."""

    def test_middleware_availability(self):
        """Test middleware availability flag."""
        from dotmac_observability import MIDDLEWARE_AVAILABLE

        # Should be a boolean
        assert isinstance(MIDDLEWARE_AVAILABLE, bool)

    def test_middleware_imports(self):
        """Test middleware imports when available."""
        try:
            from dotmac_observability.middleware import (
                AuditMiddleware,
                TimingMiddleware,
                create_audit_middleware,
                timing_middleware,
            )

            assert TimingMiddleware is not None
            assert AuditMiddleware is not None
            assert create_audit_middleware is not None
            assert timing_middleware is not None

        except ImportError:
            # If middleware not available, test graceful fallback
            from dotmac_observability import create_audit_middleware, timing_middleware

            assert create_audit_middleware is None
            assert timing_middleware is None


# Only run these tests if FastAPI/middleware is available
pytest_plugins = []

try:
    from dotmac_observability.middleware import (
        AuditMiddleware,
        TimingMiddleware,
        create_audit_middleware,
        timing_middleware,
    )

    class MockRequest:
        """Mock FastAPI Request."""

        def __init__(self, method="GET", path="/test", headers=None, body=b""):
            self.method = method
            self.url = MagicMock()
            self.url.path = path
            self.headers = headers or {}
            self._body = body

        async def body(self):
            return self._body

    class MockResponse:
        """Mock FastAPI Response."""

        def __init__(self, status_code=200, body=b"response"):
            self.status_code = status_code
            self.body = body

    class TestTimingMiddleware:
        """Test TimingMiddleware."""

        def test_timing_middleware_init(self):
            """Test TimingMiddleware initialization."""
            collector = MetricsCollector()
            app = MagicMock()

            middleware = TimingMiddleware(app, collector)

            assert middleware.app is app
            assert middleware.collector is collector

        @pytest.mark.asyncio
        async def test_timing_middleware_call(self):
            """Test TimingMiddleware ASGI call."""
            collector = MetricsCollector()

            async def mock_app(scope, receive, send):
                # Simulate response
                if scope["type"] == "http":
                    await send({"type": "http.response.start", "status": 200, "headers": []})
                    await send({"type": "http.response.body", "body": b"Hello"})

            middleware = TimingMiddleware(mock_app, collector)

            scope = {
                "type": "http",
                "method": "GET",
                "path": "/test",
            }

            messages = []

            async def mock_send(message):
                messages.append(message)

            async def mock_receive():
                return {"type": "http.request", "body": b""}

            await middleware(scope, mock_receive, mock_send)

            # Check that metrics were recorded (with tags)
            summary = collector.get_summary()
            counter_keys = list(summary["counters"].keys())
            histogram_keys = list(summary["histograms"].keys())
            
            # Check that tagged metrics exist
            assert any("http_requests_total" in key for key in counter_keys)
            assert any("http_request_duration_seconds" in key for key in histogram_keys)

        @pytest.mark.asyncio
        async def test_timing_middleware_non_http(self):
            """Test TimingMiddleware with non-HTTP scope."""
            collector = MetricsCollector()

            async def mock_app(scope, receive, send):
                pass

            middleware = TimingMiddleware(mock_app, collector)

            scope = {"type": "websocket"}

            async def mock_receive():
                return {}

            async def mock_send(message):
                pass

            # Should not raise and should not record metrics
            await middleware(scope, mock_receive, mock_send)

            summary = collector.get_summary()
            assert len(summary["counters"]) == 0
            assert len(summary["histograms"]) == 0

    class TestAuditMiddleware:
        """Test AuditMiddleware."""

        def test_audit_middleware_init(self):
            """Test AuditMiddleware initialization."""
            collector = MetricsCollector()
            app = MagicMock()

            middleware = AuditMiddleware(
                app, collector, include_user_agent=True, include_request_size=True
            )

            assert middleware.collector is collector
            assert middleware.include_user_agent is True
            assert middleware.include_request_size is True

        @pytest.mark.asyncio
        async def test_audit_middleware_dispatch(self):
            """Test AuditMiddleware dispatch."""
            collector = MetricsCollector()

            app = MagicMock()
            middleware = AuditMiddleware(app, collector)

            request = MockRequest()

            async def call_next(req):
                return MockResponse()

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check metrics were recorded (with tags)
            summary = collector.get_summary()
            counter_keys = list(summary["counters"].keys())
            histogram_keys = list(summary["histograms"].keys())
            
            # Check that tagged metrics exist
            assert any("http_requests_total" in key for key in counter_keys)
            assert any("http_request_duration_seconds" in key for key in histogram_keys)

        @pytest.mark.asyncio
        async def test_audit_middleware_with_options(self):
            """Test AuditMiddleware with all options enabled."""
            collector = MetricsCollector()

            def path_grouper(path):
                return "/api/users" if path.startswith("/api/users/") else path

            app = MagicMock()
            middleware = AuditMiddleware(
                app,
                collector,
                include_user_agent=True,
                include_request_size=True,
                path_grouping=path_grouper,
            )

            request = MockRequest(
                method="POST",
                path="/api/users/123",
                headers={"user-agent": "test-agent/1.0"},
                body=b"request data",
            )

            async def call_next(req):
                return MockResponse(status_code=201)

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 201

            # Check that path grouping was applied
            summary = collector.get_summary()
            counter_keys = list(summary["counters"].keys())

            # Should contain grouped path
            grouped_path_found = any("path=/api/users" in key for key in counter_keys)
            assert grouped_path_found

        @pytest.mark.asyncio
        async def test_audit_middleware_error_handling(self):
            """Test AuditMiddleware error handling."""
            collector = MetricsCollector()

            app = MagicMock()
            middleware = AuditMiddleware(app, collector)

            request = MockRequest()

            async def call_next_error(req):
                raise ValueError("Something went wrong")

            with pytest.raises(ValueError):
                await middleware.dispatch(request, call_next_error)

            # Check error metrics were recorded (with tags)
            summary = collector.get_summary()
            counter_keys = list(summary["counters"].keys())
            
            # Check that tagged metrics exist
            assert any("http_requests_total" in key for key in counter_keys)
            assert any("http_errors_total" in key for key in counter_keys)

    class TestMiddlewareFactories:
        """Test middleware factory functions."""

        def test_create_audit_middleware(self):
            """Test create_audit_middleware factory."""
            collector = MetricsCollector()

            middleware_factory = create_audit_middleware(collector, include_user_agent=True)

            assert callable(middleware_factory)

            # Test that it returns a middleware instance
            app = MagicMock()
            middleware = middleware_factory(app)

            assert isinstance(middleware, AuditMiddleware)
            assert middleware.include_user_agent is True

        def test_timing_middleware_factory(self):
            """Test timing_middleware factory."""
            collector = MetricsCollector()
            app = MagicMock()

            middleware = timing_middleware(app, collector)

            assert isinstance(middleware, TimingMiddleware)
            assert middleware.app is app
            assert middleware.collector is collector

except ImportError:
    # FastAPI not available, create placeholder tests
    class TestMiddlewareUnavailable:
        """Test behavior when middleware is unavailable."""

        def test_middleware_unavailable(self):
            """Test that middleware gracefully handles unavailability."""
            from dotmac_observability import MIDDLEWARE_AVAILABLE

            assert MIDDLEWARE_AVAILABLE is False
