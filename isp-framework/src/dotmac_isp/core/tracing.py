"""Distributed tracing and observability for DotMac ISP Framework."""

import logging
import time
import uuid
import functools
import asyncio
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from dotmac_isp.shared.cache import get_cache_manager
from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)


class TraceContext:
    """Thread-local trace context for correlation."""

    def __init__(self):
        self._context = {}

    def set_trace_id(self, trace_id: str):
        """Set current trace ID."""
        self._context["trace_id"] = trace_id

    def get_trace_id(self) -> Optional[str]:
        """Get current trace ID."""
        return self._context.get("trace_id")

    def set_span_id(self, span_id: str):
        """Set current span ID."""
        self._context["span_id"] = span_id

    def get_span_id(self) -> Optional[str]:
        """Get current span ID."""
        return self._context.get("span_id")

    def set_tenant_id(self, tenant_id: str):
        """Set current tenant ID."""
        self._context["tenant_id"] = tenant_id

    def get_tenant_id(self) -> Optional[str]:
        """Get current tenant ID."""
        return self._context.get("tenant_id")

    def set_user_id(self, user_id: str):
        """Set current user ID."""
        self._context["user_id"] = user_id

    def get_user_id(self) -> Optional[str]:
        """Get current user ID."""
        return self._context.get("user_id")

    def get_context(self) -> Dict[str, Any]:
        """Get full context."""
        return self._context.copy()

    def clear(self):
        """Clear context."""
        self._context.clear()


# Global trace context
trace_context = TraceContext()


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for distributed tracing."""

    def __init__(self, app, service_name: str = "dotmac-isp"):
        super().__init__(app)
        self.service_name = service_name
        self.cache_manager = get_cache_manager()

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID."""
        return str(uuid.uuid4()).replace("-", "")

    def _generate_span_id(self) -> str:
        """Generate unique span ID."""
        return str(uuid.uuid4()).replace("-", "")[:16]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing."""
        start_time = time.time()

        # Extract or generate trace ID
        trace_id = (
            request.headers.get("X-Trace-ID")
            or request.headers.get("trace-id")
            or self._generate_trace_id()
        )

        # Generate span ID for this request
        span_id = self._generate_span_id()

        # Extract tenant and user context
        tenant_id = request.headers.get("X-Tenant-ID", "unknown")
        user_id = getattr(request.state, "user_id", "anonymous")

        # Set trace context
        trace_context.set_trace_id(trace_id)
        trace_context.set_span_id(span_id)
        trace_context.set_tenant_id(tenant_id)
        trace_context.set_user_id(user_id)

        # Add tracing headers to request state
        request.state.trace_id = trace_id
        request.state.span_id = span_id

        # Create span data
        span_data = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": request.headers.get("X-Parent-Span-ID"),
            "service_name": self.service_name,
            "operation_name": f"{request.method} {request.url.path}",
            "start_time": start_time,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "http_method": request.method,
            "http_url": str(request.url),
            "http_user_agent": request.headers.get("User-Agent"),
            "http_remote_addr": request.client.host if request.client else None,
        }

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Update span with response data
            span_data.update(
                {
                    "duration_seconds": duration,
                    "http_status_code": response.status_code,
                    "success": 200 <= response.status_code < 400,
                    "end_time": time.time(),
                }
            )

            # Add tracing headers to response
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Span-ID"] = span_id

            # Log successful span
            logger.info(
                f"Span completed: {span_data['operation_name']} "
                f"[{trace_id}:{span_id}] {duration:.3f}s {response.status_code}"
            )

        except Exception as e:
            # Calculate duration for failed request
            duration = time.time() - start_time

            # Update span with error data
            span_data.update(
                {
                    "duration_seconds": duration,
                    "success": False,
                    "error": True,
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "end_time": time.time(),
                }
            )

            # Log error span
            logger.error(
                f"Span failed: {span_data['operation_name']} "
                f"[{trace_id}:{span_id}] {duration:.3f}s ERROR: {e}"
            )

            # Re-raise the exception
            raise

        finally:
            # Store span data for analysis
            self._store_span(span_data)

            # Clear trace context
            trace_context.clear()

        return response

    def _store_span(self, span_data: Dict[str, Any]):
        """Store span data for analysis."""
        try:
            # Store in cache for real-time monitoring
            span_key = f"span:{span_data['trace_id']}:{span_data['span_id']}"
            self.cache_manager.set(span_key, span_data, 86400, "traces")  # 24 hours

            # Store in trace timeline
            trace_key = f"trace:{span_data['trace_id']}"
            trace_spans = self.cache_manager.get(trace_key, "traces") or []
            trace_spans.append(span_data)
            self.cache_manager.set(trace_key, trace_spans, 86400, "traces")

            # Store performance metrics
            self._update_performance_metrics(span_data)

        except Exception as e:
            logger.error(f"Failed to store span data: {e}")

    def _update_performance_metrics(self, span_data: Dict[str, Any]):
        """Update performance metrics from span data."""
        try:
            operation = span_data["operation_name"]
            duration = span_data["duration_seconds"]
            success = span_data["success"]

            # Update request counts
            metrics_key = f"perf_metrics:{operation}"
            metrics = self.cache_manager.get(metrics_key, "metrics") or {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
            }

            metrics["total_requests"] += 1
            metrics["total_duration"] += duration
            metrics["min_duration"] = min(metrics["min_duration"], duration)
            metrics["max_duration"] = max(metrics["max_duration"], duration)

            if success:
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1

            # Calculate averages
            metrics["avg_duration"] = (
                metrics["total_duration"] / metrics["total_requests"]
            )
            metrics["success_rate"] = (
                metrics["successful_requests"] / metrics["total_requests"]
            )

            # Store updated metrics
            self.cache_manager.set(metrics_key, metrics, 3600, "metrics")  # 1 hour

        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")


def trace_function(operation_name: str = None, tags: Dict[str, Any] = None):
    """Decorator to trace function execution."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _trace_execution(func, operation_name, tags, args, kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import asyncio

            if asyncio.iscoroutinefunction(func):
                # This shouldn't happen, but handle it gracefully
                return asyncio.run(
                    _trace_execution(func, operation_name, tags, args, kwargs)
                )
            else:
                return _trace_sync_execution(func, operation_name, tags, args, kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def _trace_execution(
    func: Callable, operation_name: str, tags: Dict[str, Any], args, kwargs
):
    """Trace async function execution."""
    start_time = time.time()

    # Get current trace context
    trace_id = trace_context.get_trace_id() or str(uuid.uuid4()).replace("-", "")
    parent_span_id = trace_context.get_span_id()
    span_id = str(uuid.uuid4()).replace("-", "")[:16]

    # Set new span context
    trace_context.set_span_id(span_id)

    # Create span
    span_data = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "operation_name": operation_name or func.__name__,
        "function_name": func.__name__,
        "start_time": start_time,
        "tenant_id": trace_context.get_tenant_id(),
        "user_id": trace_context.get_user_id(),
        "tags": tags or {},
    }

    try:
        # Execute function
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        # Mark as successful
        span_data.update(
            {
                "success": True,
                "duration_seconds": time.time() - start_time,
                "end_time": time.time(),
            }
        )

        logger.debug(
            f"Function traced: {span_data['operation_name']} "
            f"[{trace_id}:{span_id}] {span_data['duration_seconds']:.3f}s"
        )

        return result

    except Exception as e:
        # Mark as failed
        span_data.update(
            {
                "success": False,
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": time.time() - start_time,
                "end_time": time.time(),
            }
        )

        logger.error(
            f"Function failed: {span_data['operation_name']} "
            f"[{trace_id}:{span_id}] ERROR: {e}"
        )

        raise

    finally:
        # Store span data
        cache_manager = get_cache_manager()
        span_key = f"span:{trace_id}:{span_id}"
        cache_manager.set(span_key, span_data, 86400, "traces")

        # Restore parent span context
        if parent_span_id:
            trace_context.set_span_id(parent_span_id)


def _trace_sync_execution(
    func: Callable, operation_name: str, tags: Dict[str, Any], args, kwargs
):
    """Trace sync function execution."""
    # Similar to async version but for sync functions
    start_time = time.time()

    trace_id = trace_context.get_trace_id() or str(uuid.uuid4()).replace("-", "")
    parent_span_id = trace_context.get_span_id()
    span_id = str(uuid.uuid4()).replace("-", "")[:16]

    trace_context.set_span_id(span_id)

    span_data = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "operation_name": operation_name or func.__name__,
        "function_name": func.__name__,
        "start_time": start_time,
        "tenant_id": trace_context.get_tenant_id(),
        "user_id": trace_context.get_user_id(),
        "tags": tags or {},
    }

    try:
        result = func(*args, **kwargs)
        span_data.update(
            {
                "success": True,
                "duration_seconds": time.time() - start_time,
                "end_time": time.time(),
            }
        )
        return result

    except Exception as e:
        span_data.update(
            {
                "success": False,
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": time.time() - start_time,
                "end_time": time.time(),
            }
        )
        raise

    finally:
        cache_manager = get_cache_manager()
        span_key = f"span:{trace_id}:{span_id}"
        cache_manager.set(span_key, span_data, 86400, "traces")

        if parent_span_id:
            trace_context.set_span_id(parent_span_id)


@contextmanager
def trace_span(operation_name: str, tags: Dict[str, Any] = None):
    """Context manager for manual span creation."""
    start_time = time.time()

    trace_id = trace_context.get_trace_id() or str(uuid.uuid4()).replace("-", "")
    parent_span_id = trace_context.get_span_id()
    span_id = str(uuid.uuid4()).replace("-", "")[:16]

    # Set new span context
    old_span_id = trace_context.get_span_id()
    trace_context.set_span_id(span_id)

    span_data = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "operation_name": operation_name,
        "start_time": start_time,
        "tenant_id": trace_context.get_tenant_id(),
        "user_id": trace_context.get_user_id(),
        "tags": tags or {},
    }

    try:
        yield span_data

        # Mark as successful
        span_data.update(
            {
                "success": True,
                "duration_seconds": time.time() - start_time,
                "end_time": time.time(),
            }
        )

    except Exception as e:
        # Mark as failed
        span_data.update(
            {
                "success": False,
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": time.time() - start_time,
                "end_time": time.time(),
            }
        )
        raise

    finally:
        # Store span data
        cache_manager = get_cache_manager()
        span_key = f"span:{trace_id}:{span_id}"
        cache_manager.set(span_key, span_data, 86400, "traces")

        # Restore previous span context
        trace_context.set_span_id(old_span_id)


class TracingService:
    """Service for trace analytics and monitoring."""

    def __init__(self):
        self.cache_manager = get_cache_manager()

    def get_trace(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get all spans for a trace."""
        trace_key = f"trace:{trace_id}"
        return self.cache_manager.get(trace_key, "traces")

    def get_span(self, trace_id: str, span_id: str) -> Optional[Dict[str, Any]]:
        """Get specific span data."""
        span_key = f"span:{trace_id}:{span_id}"
        return self.cache_manager.get(span_key, "traces")

    def get_performance_metrics(self, operation: str = None) -> Dict[str, Any]:
        """Get performance metrics for operations."""
        if operation:
            metrics_key = f"perf_metrics:{operation}"
            return self.cache_manager.get(metrics_key, "metrics") or {}

        # Get all performance metrics
        pattern = "dotmac:metrics:perf_metrics:*"
        keys = self.cache_manager.redis_client.keys(pattern)

        all_metrics = {}
        for key in keys:
            operation_name = key.decode().split(":")[-1]
            metrics = self.cache_manager.get(
                f"perf_metrics:{operation_name}", "metrics"
            )
            if metrics:
                all_metrics[operation_name] = metrics

        return all_metrics

    def get_slow_traces(
        self, threshold_seconds: float = 1.0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get traces that took longer than threshold."""
        # This would require more sophisticated indexing in a real implementation
        # For now, return empty list
        return []

    def get_error_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get traces that had errors."""
        # This would require error indexing in a real implementation
        return []


# Global tracing service
tracing_service = TracingService()
