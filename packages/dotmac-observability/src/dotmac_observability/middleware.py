"""FastAPI and ASGI middleware for dotmac-observability."""

import time
from typing import Any, Callable, Optional

from .metrics import MetricsCollector

try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.types import ASGIApp, Receive, Scope, Send

    FASTAPI_AVAILABLE = True
except ImportError:
    # Graceful degradation when FastAPI is not installed
    FASTAPI_AVAILABLE = False
    Request = Response = BaseHTTPMiddleware = ASGIApp = Receive = Scope = Send = Any


class TimingMiddleware:
    """
    Generic ASGI middleware for request timing.

    Works with any ASGI framework, not just FastAPI.
    """

    def __init__(self, app: ASGIApp, collector: MetricsCollector):
        """
        Initialize timing middleware.

        Args:
            app: ASGI application
            collector: Metrics collector instance
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI extras not installed. Install with: pip install dotmac-observability[fastapi]"
            )

        self.app = app
        self.collector = collector

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Start timing
        start_time = time.perf_counter()

        # Track response info
        status_code = 500  # Default to error

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Record metrics
            duration = time.perf_counter() - start_time
            method = scope.get("method", "UNKNOWN")
            path = scope.get("path", "/unknown")

            tags = {
                "method": method,
                "status": str(status_code),
                "path": path,
            }

            self.collector.counter("http_requests_total", 1.0, tags)
            self.collector.histogram("http_request_duration_seconds", duration, tags)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive HTTP request auditing.

    Provides detailed metrics including request/response sizes,
    user agents, and more detailed path patterns.
    """

    def __init__(
        self,
        app: ASGIApp,
        collector: MetricsCollector,
        *,
        include_user_agent: bool = False,
        include_request_size: bool = False,
        path_grouping: Optional[Callable[[str], str]] = None,
    ):
        """
        Initialize audit middleware.

        Args:
            app: FastAPI application
            collector: Metrics collector instance
            include_user_agent: Include user agent in tags
            include_request_size: Track request/response sizes
            path_grouping: Optional function to group paths (e.g., /users/123 -> /users/{id})
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI extras not installed. Install with: pip install dotmac-observability[fastapi]"
            )

        super().__init__(app)
        self.collector = collector
        self.include_user_agent = include_user_agent
        self.include_request_size = include_request_size
        self.path_grouping = path_grouping

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and collect metrics."""
        start_time = time.perf_counter()

        # Get request info
        method = request.method
        path = str(request.url.path)

        # Apply path grouping if provided
        if self.path_grouping:
            path = self.path_grouping(path)

        # Base tags
        tags = {
            "method": method,
            "path": path,
        }

        # Optional request size tracking
        request_size = 0
        if self.include_request_size:
            try:
                # Estimate request size from headers
                request_size = len(str(request.headers))
                if hasattr(request, "body"):
                    body = await request.body()
                    request_size += len(body)
            except Exception:
                pass  # Ignore errors in size calculation

        # Optional user agent
        if self.include_user_agent:
            user_agent = request.headers.get("user-agent", "unknown")
            # Truncate user agent to avoid tag explosion
            tags["user_agent"] = user_agent[:50] if user_agent else "unknown"

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code

            # Success metrics
            tags["status"] = str(status_code)
            tags["status_class"] = f"{status_code // 100}xx"

        except Exception as e:
            # Error metrics
            status_code = 500
            tags["status"] = "500"
            tags["status_class"] = "5xx"
            tags["error_type"] = type(e).__name__

            # Record error
            self.collector.counter(
                "http_errors_total",
                1.0,
                {
                    "method": method,
                    "path": path,
                    "error_type": type(e).__name__,
                },
            )

            # Re-raise the exception
            raise
        finally:
            # Record timing metrics
            duration = time.perf_counter() - start_time

            self.collector.counter("http_requests_total", 1.0, tags)
            self.collector.histogram("http_request_duration_seconds", duration, tags)

            # Optional size metrics
            if self.include_request_size and request_size > 0:
                self.collector.histogram(
                    "http_request_size_bytes",
                    request_size,
                    {
                        "method": method,
                        "path": path,
                    },
                )

            # Response size (if available)
            if self.include_request_size and hasattr(response, "body"):
                try:
                    response_size = len(response.body) if response.body else 0
                    if response_size > 0:
                        self.collector.histogram(
                            "http_response_size_bytes",
                            response_size,
                            {
                                "method": method,
                                "path": path,
                                "status": str(status_code),
                            },
                        )
                except Exception:
                    pass  # Ignore errors in response size calculation

        return response


def create_audit_middleware(collector: MetricsCollector, **kwargs: Any) -> AuditMiddleware:
    """
    Factory function to create audit middleware.

    Args:
        collector: Metrics collector instance
        **kwargs: Additional middleware options

    Returns:
        Configured AuditMiddleware class

    Example:
        app.add_middleware(create_audit_middleware(get_collector()))
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI extras not installed. Install with: pip install dotmac-observability[fastapi]"
        )

    def middleware_factory(app: ASGIApp) -> AuditMiddleware:
        return AuditMiddleware(app, collector, **kwargs)

    return middleware_factory


def timing_middleware(app: ASGIApp, collector: MetricsCollector) -> TimingMiddleware:
    """
    Factory function to create timing middleware.

    Args:
        app: ASGI application
        collector: Metrics collector instance

    Returns:
        Configured TimingMiddleware instance
    """
    return TimingMiddleware(app, collector)
