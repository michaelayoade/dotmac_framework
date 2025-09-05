"""
Audit middleware for automatic request tracking in DotMac services.

This middleware automatically logs HTTP requests, authentication events,
and other audit-worthy activities for compliance and security monitoring.
"""

import uuid
from collections.abc import Callable
from typing import Optional

from .audit import (
    AuditActor,
    AuditContext,
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditOutcome,
    AuditResource,
    AuditSeverity,
    get_audit_logger,
)
from .utils import format_duration_ms, get_current_timestamp, get_logger, sanitize_dict

try:
    from fastapi import Request, Response
    from fastapi.middleware.base import BaseHTTPMiddleware

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Create dummy classes when FastAPI is not available
    Request = None
    Response = None

    class BaseHTTPMiddleware:
        """Dummy BaseHTTPMiddleware for when FastAPI is not available."""

        def __init__(self, app):
            self.app = app


logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic audit logging.

    Captures HTTP requests, responses, and authentication events
    for comprehensive audit trails.
    """

    def __init__(
        self,
        app,
        audit_logger: Optional[AuditLogger] = None,
        excluded_paths: Optional[set[str]] = None,
        excluded_methods: Optional[set[str]] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024 * 10,  # 10KB
        sensitive_headers: Optional[set[str]] = None,
        extract_actor: Optional[Callable[[Request], Optional[AuditActor]]] = None,
        extract_resource: Optional[Callable[[Request], Optional[AuditResource]]] = None,
    ):
        """
        Initialize audit middleware.

        Args:
            app: FastAPI application instance
            audit_logger: Audit logger instance (uses global if None)
            excluded_paths: Set of paths to exclude from auditing
            excluded_methods: Set of HTTP methods to exclude from auditing
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            max_body_size: Maximum body size to log (bytes)
            sensitive_headers: Headers to redact in logs
            extract_actor: Function to extract actor from request
            extract_resource: Function to extract resource from request
        """
        super().__init__(app)

        self.audit_logger = audit_logger
        self.excluded_paths = excluded_paths or {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/ping",
            "/ready",
            "/live",
        }
        self.excluded_methods = excluded_methods or {"OPTIONS", "HEAD"}
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.sensitive_headers = sensitive_headers or {
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
            "x-csrf-token",
            "x-session-id",
        }
        self.extract_actor = extract_actor or self._default_extract_actor
        self.extract_resource = extract_resource or self._default_extract_resource

    async def dispatch(self, request, call_next: Callable):
        """Process request and log audit events."""

        # If FastAPI is not available, just pass through
        if not FASTAPI_AVAILABLE:
            return await call_next(request)

        # Skip excluded paths and methods
        if request.url.path in self.excluded_paths or request.method in self.excluded_methods:
            return await call_next(request)

        # Get or create audit logger
        audit_logger = self.audit_logger or get_audit_logger()
        if not audit_logger:
            logger.warning("No audit logger available, skipping audit logging")
            return await call_next(request)

        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        start_time = get_current_timestamp()

        # Extract audit information
        actor = await self._extract_actor_safe(request)
        resource = await self._extract_resource_safe(request)
        context = await self._extract_context(request, request_id)

        # Read and store request body if needed
        request_body = None
        if self.log_request_body:
            request_body = await self._read_request_body(request)

        try:
            # Process the request
            response = await call_next(request)
            duration_ms = format_duration_ms(start_time)

            # Read response body if needed
            response_body = None
            if self.log_response_body and response.status_code < 400:
                response_body = await self._read_response_body(response)

            # Determine audit outcome
            outcome = self._determine_outcome(response.status_code)
            severity = self._determine_severity(request.method, response.status_code)

            # Create audit event
            event = AuditEvent(
                event_type=self._determine_event_type(request.method, response.status_code),
                message=f"{request.method} {request.url.path} -> {response.status_code}",
                description=f"HTTP request processed: {request.method} {request.url}",
                actor=actor,
                resource=resource,
                context=context,
                severity=severity,
                outcome=outcome,
                duration_ms=duration_ms,
                custom_attributes={
                    "request_id": request_id,
                    "http_method": request.method,
                    "url_path": request.url.path,
                    "query_params": dict(request.query_params),
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "content_length": response.headers.get("content-length"),
                    "request_headers": self._sanitize_headers(dict(request.headers)),
                    "response_headers": self._sanitize_headers(dict(response.headers)),
                },
            )

            # Add request/response bodies if logged
            if request_body:
                event.custom_attributes["request_body"] = request_body
            if response_body:
                event.custom_attributes["response_body"] = response_body

            # Log the audit event
            audit_logger.store.store_event(event)

            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Log error audit event
            duration_ms = format_duration_ms(start_time)

            error_event = AuditEvent(
                event_type=AuditEventType.SYSTEM_START,  # Could be more specific
                message=f"Request processing error: {request.method} {request.url.path}",
                description=f"Error processing HTTP request: {str(e)}",
                actor=actor,
                resource=resource,
                context=context,
                severity=AuditSeverity.HIGH,
                outcome=AuditOutcome.FAILURE,
                duration_ms=duration_ms,
                custom_attributes={
                    "request_id": request_id,
                    "http_method": request.method,
                    "url_path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "request_headers": self._sanitize_headers(dict(request.headers)),
                },
            )

            try:
                audit_logger.store.store_event(error_event)
            except Exception as log_error:
                logger.error(f"Failed to log audit event for error: {log_error}")

            # Re-raise the original exception
            raise

    async def _extract_actor_safe(self, request) -> Optional[AuditActor]:
        """Safely extract actor from request."""
        try:
            return await self.extract_actor(request)
        except Exception as e:
            logger.warning(f"Failed to extract actor from request: {e}")
            return None

    async def _extract_resource_safe(self, request) -> Optional[AuditResource]:
        """Safely extract resource from request."""
        try:
            return await self.extract_resource(request)
        except Exception as e:
            logger.warning(f"Failed to extract resource from request: {e}")
            return None

    async def _extract_context(self, request, request_id: str) -> AuditContext:
        """Extract audit context from request."""
        return AuditContext(
            request_id=request_id,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            forwarded_for=request.headers.get("x-forwarded-for"),
            service_name=getattr(request.app, "title", "unknown-service"),
        )

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request headers."""
        # Check forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    async def _read_request_body(self, request) -> Optional[str]:
        """Read and return request body if small enough."""
        try:
            body = await request.body()
            if len(body) <= self.max_body_size:
                # Try to decode as text
                try:
                    return body.decode("utf-8")
                except UnicodeDecodeError:
                    return f"<binary data, {len(body)} bytes>"
            else:
                return f"<body too large, {len(body)} bytes>"
        except Exception as e:
            logger.warning(f"Failed to read request body: {e}")
            return None

    async def _read_response_body(self, response) -> Optional[str]:
        """Read and return response body if small enough."""
        try:
            # Note: This is complex with FastAPI StreamingResponse
            # For now, we'll skip response body logging for streaming responses
            return None
        except Exception as e:
            logger.warning(f"Failed to read response body: {e}")
            return None

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Sanitize sensitive headers."""
        return sanitize_dict(headers, self.sensitive_headers)

    def _determine_event_type(self, method: str, status_code: int) -> AuditEventType:
        """Determine audit event type based on HTTP method and status."""
        if status_code >= 400:
            return AuditEventType.SECURITY_POLICY_VIOLATION

        method_map = {
            "POST": AuditEventType.DATA_CREATE,
            "GET": AuditEventType.DATA_READ,
            "PUT": AuditEventType.DATA_UPDATE,
            "PATCH": AuditEventType.DATA_UPDATE,
            "DELETE": AuditEventType.DATA_DELETE,
        }

        return method_map.get(method, AuditEventType.DATA_READ)

    def _determine_outcome(self, status_code: int) -> AuditOutcome:
        """Determine audit outcome based on HTTP status code."""
        if 200 <= status_code < 300:
            return AuditOutcome.SUCCESS
        elif 400 <= status_code < 500:
            return AuditOutcome.FAILURE
        elif status_code >= 500:
            return AuditOutcome.FAILURE
        else:
            return AuditOutcome.PARTIAL

    def _determine_severity(self, method: str, status_code: int) -> AuditSeverity:
        """Determine audit severity based on method and status code."""
        if status_code >= 500:
            return AuditSeverity.HIGH
        elif status_code >= 400:
            return AuditSeverity.MEDIUM
        elif method in ["DELETE", "PUT"]:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW

    async def _default_extract_actor(self, request) -> Optional[AuditActor]:
        """Default actor extraction from request."""
        # Try to extract from common auth headers
        auth_header = request.headers.get("authorization")
        if auth_header:
            # This is a simplified example - in practice you'd decode JWT, etc.
            return AuditActor(
                actor_id="authenticated-user",
                actor_type="user",
                session_id=request.headers.get("x-session-id"),
            )

        # Check for API key
        api_key = request.headers.get("x-api-key")
        if api_key:
            return AuditActor(
                actor_id=api_key[:8] + "...",  # Partial key for audit
                actor_type="api_key",
                api_key_id=api_key[:8],
            )

        # Anonymous user
        return AuditActor(actor_id="anonymous", actor_type="anonymous")

    async def _default_extract_resource(self, request) -> Optional[AuditResource]:
        """Default resource extraction from request path."""
        path_parts = request.url.path.strip("/").split("/")

        if len(path_parts) >= 2:
            resource_type = path_parts[0]  # e.g., "users", "orders"
            resource_id = path_parts[1] if len(path_parts) > 1 else None

            return AuditResource(
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=request.url.path,
            )

        return AuditResource(resource_type="api", resource_name=request.url.path)


class AuditEventCollector:
    """Utility class for collecting and batching audit events."""

    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        batch_size: int = 100,
        flush_interval: float = 30.0,
    ):
        self.audit_logger = audit_logger
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.events: list[AuditEvent] = []
        self.last_flush = get_current_timestamp()

    def add_event(self, event: AuditEvent):
        """Add event to the batch."""
        self.events.append(event)

        # Check if we should flush
        if len(self.events) >= self.batch_size or get_current_timestamp() - self.last_flush >= self.flush_interval:
            self.flush()

    def flush(self):
        """Flush all pending events to the audit logger."""
        if not self.events:
            return

        audit_logger = self.audit_logger or get_audit_logger()
        if not audit_logger:
            logger.warning("No audit logger available for batch flush")
            return

        try:
            stored = audit_logger.store.store_events(self.events)
            logger.debug(f"Flushed {stored}/{len(self.events)} audit events")
            self.events.clear()
            self.last_flush = get_current_timestamp()
        except Exception as e:
            logger.error(f"Failed to flush audit events: {e}")


def create_audit_middleware(audit_logger: Optional[AuditLogger] = None, **kwargs) -> AuditMiddleware:
    """Factory function to create audit middleware."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for audit middleware")

    return AuditMiddleware(
        app=None,
        audit_logger=audit_logger,
        **kwargs,  # Will be set by FastAPI
    )


__all__ = [
    "AuditMiddleware",
    "AuditEventCollector",
    "create_audit_middleware",
    "FASTAPI_AVAILABLE",
]
