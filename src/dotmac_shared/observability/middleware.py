"""
Observability middleware for FastAPI applications.
Handles tenant context propagation, request tracing, and correlation IDs.
"""

import time
import uuid
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import trace, baggage, context
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.propagate import extract

from .otel import tenant_operation_duration, tenant_operation_counter
from .logging import get_logger

logger = get_logger("dotmac.middleware")


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle tenant context and request correlation.
    
    Features:
    - Extracts and validates tenant_id from headers/path/query
    - Generates or extracts correlation IDs
    - Propagates context via OpenTelemetry baggage
    - Records tenant-specific metrics
    - Adds trace_id to response headers
    """
    
    def __init__(
        self,
        app,
        tenant_header: str = "x-tenant-id",
        request_id_header: str = "x-request-id",
        user_id_header: str = "x-user-id",
        enable_tenant_validation: bool = True
    ):
        super().__init__(app)
        self.tenant_header = tenant_header.lower()
        self.request_id_header = request_id_header.lower()
        self.user_id_header = user_id_header.lower()
        self.enable_tenant_validation = enable_tenant_validation

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant context and tracing."""
        start_time = time.perf_counter()
        
        # Extract context information
        tenant_id = self._extract_tenant_id(request)
        request_id = self._extract_or_generate_request_id(request)
        user_id = self._extract_user_id(request)
        
        # Extract distributed trace context from headers
        parent_context = extract(request.headers)
        
        # Create baggage context with tenant/request information
        baggage_context = baggage.set_baggage("tenant.id", tenant_id or "unknown")
        baggage_context = baggage.set_baggage("request.id", request_id, context=baggage_context)
        if user_id:
            baggage_context = baggage.set_baggage("user.id", user_id, context=baggage_context)
        
        # Merge contexts
        merged_context = context.Context(parent_context, baggage_context)
        
        # Get current span and set attributes
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("http.route", self._get_route_pattern(request))
            span.set_attribute("tenant.id", tenant_id or "unknown")
            span.set_attribute("request.id", request_id)
            if user_id:
                span.set_attribute("user.id", user_id)
            
            # Add request metadata
            span.set_attribute("http.user_agent", request.headers.get("user-agent", ""))
            span.set_attribute("http.client_ip", self._get_client_ip(request))
        
        response = None
        error_occurred = False
        
        try:
            # Process request within context
            token = context.attach(merged_context)
            try:
                response = await call_next(request)
            finally:
                context.detach(token)
                
        except Exception as e:
            error_occurred = True
            
            # Record error in span
            if span.is_recording():
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            
            # Log error with context
            logger.error(
                "Request processing error",
                error=str(e),
                tenant_id=tenant_id,
                request_id=request_id,
                path=request.url.path,
                method=request.method
            )
            raise
        
        finally:
            # Record metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            if tenant_id:
                operation_type = f"{request.method}:{self._get_route_pattern(request)}"
                tenant_operation_counter.add(
                    1,
                    {
                        "tenant_id": tenant_id,
                        "operation_type": operation_type,
                        "status": "error" if error_occurred else "success"
                    }
                )
                tenant_operation_duration.record(
                    duration_ms,
                    {
                        "tenant_id": tenant_id,
                        "operation_type": operation_type
                    }
                )
        
        # Add correlation headers to response
        if response:
            response.headers["x-request-id"] = request_id
            
            # Add trace_id if available
            if span.is_recording():
                trace_id = format(span.get_span_context().trace_id, "032x")
                response.headers["x-trace-id"] = trace_id
            
            # Add tenant_id if available (for debugging)
            if tenant_id:
                response.headers["x-tenant-id"] = tenant_id
        
        return response

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request headers, path, or query parameters."""
        # Try header first
        tenant_id = request.headers.get(self.tenant_header)
        if tenant_id:
            return tenant_id
        
        # Try path parameter (for routes like /api/v1/tenants/{tenant_id}/...)
        path_parts = request.url.path.strip("/").split("/")
        if "tenants" in path_parts:
            try:
                tenant_index = path_parts.index("tenants")
                if tenant_index + 1 < len(path_parts):
                    return path_parts[tenant_index + 1]
            except (ValueError, IndexError):
                pass
        
        # Try query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        # Try subdomain (for subdomain-based tenancy)
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain not in ["www", "api", "app"]:  # Common non-tenant subdomains
                return subdomain
        
        return None

    def _extract_or_generate_request_id(self, request: Request) -> str:
        """Extract request ID from headers or generate new one."""
        request_id = request.headers.get(self.request_id_header)
        if not request_id:
            request_id = str(uuid.uuid4())
        return request_id

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from headers or JWT token."""
        # Try header first
        user_id = request.headers.get(self.user_id_header)
        if user_id:
            return user_id
        
        # Try to extract from Authorization header (simplified JWT parsing)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # In production, you'd want proper JWT parsing
            # This is a simplified approach for demonstration
            try:
                import json
                import base64
                token = auth_header.split(" ")[1]
                # This is unsafe in production - use proper JWT library
                payload = token.split(".")[1]
                # Add padding if needed
                payload += "=" * (4 - len(payload) % 4)
                decoded = json.loads(base64.b64decode(payload))
                return decoded.get("sub") or decoded.get("user_id")
            except Exception:
                pass
        
        return None

    def _get_route_pattern(self, request: Request) -> str:
        """Get route pattern for the request."""
        # Try to get from FastAPI route
        if hasattr(request, "scope") and request.scope.get("route"):
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        
        # Fallback to raw path
        return request.url.path

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies."""
        # Check forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (client IP)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to remote address
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting HTTP metrics.
    
    Records request duration, status codes, and route-specific metrics.
    """
    
    def __init__(self, app):
        super().__init__(app)
        from .otel import get_meter
        
        meter = get_meter("dotmac-http")
        
        self.http_requests_total = meter.create_counter(
            "http_requests_total",
            description="Total HTTP requests"
        )
        
        self.http_request_duration = meter.create_histogram(
            "http_request_duration_ms",
            description="HTTP request duration in milliseconds",
            unit="ms"
        )
        
        self.http_requests_in_progress = meter.create_up_down_counter(
            "http_requests_in_progress",
            description="HTTP requests currently in progress"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Record HTTP metrics for the request."""
        start_time = time.perf_counter()
        
        # Extract labels
        method = request.method
        path = self._get_route_pattern(request)
        
        # Increment in-progress counter
        self.http_requests_in_progress.add(1, {"method": method, "path": path})
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Record metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            labels = {
                "method": method,
                "path": path,
                "status": str(status_code)
            }
            
            self.http_requests_total.add(1, labels)
            self.http_request_duration.record(duration_ms, labels)
            self.http_requests_in_progress.add(-1, {"method": method, "path": path})
        
        return response

    def _get_route_pattern(self, request: Request) -> str:
        """Get route pattern, same as TenantContextMiddleware."""
        if hasattr(request, "scope") and request.scope.get("route"):
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        return request.url.path