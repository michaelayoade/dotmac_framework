"""
FastAPI middleware for automatic metrics collection.

This module provides middleware that automatically instruments FastAPI
applications with monitoring capabilities using the unified monitoring system.
"""

import time
from collections.abc import Callable
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .base import BaseMonitoringService, get_monitoring


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic HTTP request monitoring.

    This middleware automatically captures HTTP request metrics including:
    - Request count by method, endpoint, status code, and tenant
    - Request duration
    - Request/response sizes
    - Error tracking
    """

    def __init__(
        self,
        app: ASGIApp,
        monitoring_service: Optional[BaseMonitoringService] = None,
        include_request_size: bool = True,
        include_response_size: bool = True,
        tenant_header: str = "X-Tenant-ID",
        service_name: str = "api",
    ):
        """
        Initialize monitoring middleware.

        Args:
            app: ASGI application
            monitoring_service: Optional monitoring service (uses global if None)
            include_request_size: Whether to measure request sizes
            include_response_size: Whether to measure response sizes
            tenant_header: Header name for tenant ID extraction
            service_name: Service name for monitoring service initialization
        """
        super().__init__(app)
        self.monitoring = monitoring_service or get_monitoring(service_name)
        self.include_request_size = include_request_size
        self.include_response_size = include_response_size
        self.tenant_header = tenant_header

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and capture metrics."""
        start_time = time.time()

        # Extract tenant ID from headers or path
        tenant_id = self._extract_tenant_id(request)

        # Measure request size
        request_size = 0
        if self.include_request_size:
            request_size = self._get_request_size(request)

        # Process request
        response = None
        status_code = 500  # Default to error if something goes wrong

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Record the error
            self.monitoring.record_error(
                error_type=type(e).__name__,
                service="api",
                tenant_id=tenant_id,
            )
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Measure response size
            response_size = 0
            if response and self.include_response_size:
                response_size = self._get_response_size(response)

            # Record metrics
            self.monitoring.record_http_request(
                method=request.method,
                endpoint=self._normalize_endpoint(request),
                status_code=status_code,
                duration=duration,
                tenant_id=tenant_id,
                request_size=request_size,
                response_size=response_size,
            )

        return response

    def _extract_tenant_id(self, request: Request) -> str:
        """Extract tenant ID from request."""
        # Try header first
        tenant_id = request.headers.get(self.tenant_header)
        if tenant_id:
            return tenant_id

        # Try path parameters
        path_params = request.path_params
        if "tenant_id" in path_params:
            return path_params["tenant_id"]

        # Try query parameters
        if "tenant_id" in request.query_params:
            return request.query_params["tenant_id"]

        return "unknown"

    def _normalize_endpoint(self, request: Request) -> str:
        """
        Normalize endpoint path for metrics.

        Replaces path parameters with placeholders to avoid high cardinality.
        """
        try:
            # Get route pattern if available
            if hasattr(request, "scope") and "route" in request.scope:
                route = request.scope["route"]
                if hasattr(route, "path"):
                    return route.path

            # Fallback to actual path (may have high cardinality)
            path = request.url.path

            # Basic normalization - replace UUIDs and numeric IDs
            import re

            # Replace UUIDs
            path = re.sub(
                r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                "/{uuid}",
                path,
                flags=re.IGNORECASE,
            )

            # Replace numeric IDs
            path = re.sub(r"/\d+", "/{id}", path)

            return path

        except Exception:
            return request.url.path

    def _get_request_size(self, request: Request) -> int:
        """Get request content size."""
        try:
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)
        except (ValueError, TypeError):
            pass
        return 0

    def _get_response_size(self, response: Response) -> int:
        """Get response content size."""
        try:
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)

            # If no content-length header, try to get body size
            if hasattr(response, "body") and response.body:
                return len(response.body)
        except (ValueError, TypeError, AttributeError):
            pass
        return 0


class DatabaseMonitoringMixin:
    """
    Mixin class for adding database monitoring to repositories.

    This mixin can be used with SQLAlchemy repositories to automatically
    track database query performance and errors.
    """

    def __init__(
        self,
        *args,
        monitoring_service: Optional[BaseMonitoringService] = None,
        **kwargs,
    ):
        """Initialize with monitoring service."""
        super().__init__(*args, **kwargs)
        self.monitoring = monitoring_service or get_monitoring()

    def _monitor_query(
        self,
        operation: str,
        table: str,
        tenant_id: Optional[str] = None,
    ):
        """Context manager for monitoring database queries."""

        class QueryMonitor:
            """QueryMonitor implementation."""

            def __init__(self, monitoring_service, op, tbl, tid):
                self.monitoring = monitoring_service
                self.operation = op
                self.table = tbl
                self.tenant_id = tid or "unknown"
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                success = exc_type is None

                self.monitoring.record_database_query(
                    operation=self.operation,
                    table=self.table,
                    duration=duration,
                    success=success,
                    tenant_id=self.tenant_id,
                )

        return QueryMonitor(self.monitoring, operation, table, tenant_id)


class CacheMonitoringMixin:
    """
    Mixin class for adding cache monitoring to cache implementations.

    This mixin can be used with Redis or other cache implementations
    to track cache performance and hit ratios.
    """

    def __init__(
        self,
        *args,
        monitoring_service: Optional[BaseMonitoringService] = None,
        **kwargs,
    ):
        """Initialize with monitoring service."""
        super().__init__(*args, **kwargs)
        self.monitoring = monitoring_service or get_monitoring()
        self._cache_stats = {}

    def _monitor_cache_operation(
        self,
        operation: str,
        cache_name: str = "default",
        tenant_id: Optional[str] = None,
    ):
        """Context manager for monitoring cache operations."""

        class CacheMonitor:
            """CacheMonitor implementation."""

            def __init__(self, monitoring_service, op, cache, tid, stats):
                self.monitoring = monitoring_service
                self.operation = op
                self.cache_name = cache
                self.tenant_id = tid or "unknown"
                self.stats = stats
                self.success = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.success = exc_type is None

                self.monitoring.record_cache_operation(
                    operation=self.operation,
                    cache_name=self.cache_name,
                    success=self.success,
                    tenant_id=self.tenant_id,
                )

                # Update hit ratio statistics for GET operations
                if self.operation == "get":
                    self._update_hit_ratio_stats()

            def __call__(self, success_override: Optional[bool] = None):
                """Allow manual success setting for complex operations."""
                if success_override is not None:
                    self.success = success_override
                return self

            def _update_hit_ratio_stats(self):
                """Update cache hit ratio statistics."""
                cache_key = f"{self.cache_name}_{self.tenant_id}"

                if cache_key not in self.stats:
                    self.stats[cache_key] = {"hits": 0, "total": 0}

                self.stats[cache_key]["total"] += 1
                if self.success:
                    self.stats[cache_key]["hits"] += 1

                # Calculate and update hit ratio
                stats = self.stats[cache_key]
                hit_ratio = stats["hits"] / stats["total"] if stats["total"] > 0 else 0

                # Only update Prometheus if we have meaningful data
                if stats["total"] % 100 == 0 or stats["total"] <= 10:
                    self.monitoring.cache_hit_ratio.labels(
                        cache_name=self.cache_name,
                        tenant_id=self.tenant_id,
                    ).set(hit_ratio)

        return CacheMonitor(self.monitoring, operation, cache_name, tenant_id, self._cache_stats)


def create_metrics_endpoint(monitoring_service: Optional[BaseMonitoringService] = None):
    """
    Create a FastAPI endpoint for Prometheus metrics exposition.

    Args:
        monitoring_service: Optional monitoring service (uses global if None)

    Returns:
        Callable: FastAPI endpoint function
    """
    monitoring = monitoring_service or get_monitoring()

    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        metrics_data, content_type = monitoring.get_metrics_endpoint()
        return Response(content=metrics_data, media_type=content_type)

    return metrics_endpoint


def create_health_endpoint(monitoring_service: Optional[BaseMonitoringService] = None):
    """
    Create a FastAPI endpoint for health checks.

    Args:
        monitoring_service: Optional monitoring service (uses global if None)

    Returns:
        Callable: FastAPI endpoint function
    """
    monitoring = monitoring_service or get_monitoring()

    async def health_endpoint():
        """Health check endpoint."""
        health_checks = monitoring.perform_health_check()

        # Determine overall status
        overall_status = "healthy"
        for check in health_checks:
            if check.status.value in ["critical", "unhealthy"]:
                overall_status = "unhealthy"
                break
            elif check.status.value == "degraded" and overall_status == "healthy":
                overall_status = "degraded"

        return {
            "status": overall_status,
            "service": monitoring.service_name,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "timestamp": check.timestamp,
                    "response_time": check.response_time,
                    "metadata": check.metadata,
                }
                for check in health_checks
            ],
            "timestamp": time.time(),
        }

    return health_endpoint
