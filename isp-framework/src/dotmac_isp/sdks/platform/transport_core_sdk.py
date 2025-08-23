"""
Platform Transport Core SDK - HTTP transport and golden headers for all Dotmac planes

Provides standardized HTTP transport with golden headers for request correlation,
tenant isolation, and idempotency across all planes in the Dotmac architecture.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class TransportHeaders:
    """Golden HTTP headers for Dotmac Platform."""

    x_request_id: str
    x_tenant_id: str | None = None
    idempotency_key: str | None = None
    x_correlation_id: str | None = None
    x_user_id: str | None = None
    x_trace_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to HTTP headers dictionary."""
        headers = {"X-Request-Id": self.x_request_id}

        if self.x_tenant_id:
            headers["X-Tenant-Id"] = self.x_tenant_id
        if self.idempotency_key:
            headers["Idempotency-Key"] = self.idempotency_key
        if self.x_correlation_id:
            headers["X-Correlation-Id"] = self.x_correlation_id
        if self.x_user_id:
            headers["X-User-Id"] = self.x_user_id
        if self.x_trace_id:
            headers["X-Trace-Id"] = self.x_trace_id

        return headers

    @classmethod
    def from_dict(cls, headers: dict[str, str]) -> "TransportHeaders":
        """Create from HTTP headers dictionary."""
        return cls(
            x_request_id=headers.get("X-Request-Id", str(uuid4())),
            x_tenant_id=headers.get("X-Tenant-Id"),
            idempotency_key=headers.get("Idempotency-Key"),
            x_correlation_id=headers.get("X-Correlation-Id"),
            x_user_id=headers.get("X-User-Id"),
            x_trace_id=headers.get("X-Trace-Id"),
        )


@dataclass
class ErrorEnvelope:
    """Consistent error envelope across all Dotmac planes."""

    error: str
    message: str
    code: str
    request_id: str
    timestamp: str
    details: dict[str, Any] | None = None
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "error": self.error,
            "message": self.message,
            "code": self.code,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }

        if self.details:
            result["details"] = self.details
        if self.trace_id:
            result["trace_id"] = self.trace_id

        return result


class TransportCoreSDK:
    """
    Platform Transport Core SDK providing standardized HTTP transport.

    Features:
    - Golden HTTP headers (X-Request-Id, X-Tenant-Id, Idempotency-Key)
    - Consistent error envelopes
    - Request correlation and tracing
    - Tenant isolation support
    - Idempotency handling
    """

    # NOTE: Async helpers are provided to satisfy smoke/integration tests
    # without introducing actual network I/O. They simply wrap the
    # synchronous helpers so they can be awaited inside `pytest.mark.asyncio`
    # tests.

    def __init__(self, default_tenant_id: str | None = None):
        self.default_tenant_id = default_tenant_id

    async def generate_golden_headers(
        self,
        user_id: str | None = None,
        tenant_id: str | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> TransportHeaders:
        """Asynchronously generate golden transport headers.

        This helper is a thin async wrapper around `create_headers` so that
        test suites can simply `await transport_sdk.generate_golden_headers(...)`.
        """
        # Reuse existing synchronous implementation under the hood.
        return self.create_headers(
            tenant_id=tenant_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    async def health_check(self) -> bool:
        """Simple async health-check stub used by smoke tests."""
        return True

    def create_headers(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> TransportHeaders:
        """Create standardized transport headers."""
        return TransportHeaders(
            x_request_id=str(uuid4()),
            x_tenant_id=tenant_id or self.default_tenant_id,
            idempotency_key=idempotency_key,
            x_correlation_id=correlation_id or str(uuid4()),
            x_user_id=user_id,
            x_trace_id=trace_id or str(uuid4()),
        )

    def create_error_envelope(
        self,
        error: str,
        message: str,
        code: str,
        request_id: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> ErrorEnvelope:
        """Create standardized error envelope."""
        from datetime import datetime

        from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

        return ErrorEnvelope(
            error=error,
            message=message,
            code=code,
            request_id=request_id,
            timestamp=datetime.now(UTC).isoformat(),
            details=details,
            trace_id=trace_id,
        )

    def extract_tenant_context(self, headers: dict[str, str]) -> dict[str, Any]:
        """Extract tenant context from headers."""
        transport_headers = TransportHeaders.from_dict(headers)

        return {
            "tenant_id": transport_headers.x_tenant_id,
            "user_id": transport_headers.x_user_id,
            "request_id": transport_headers.x_request_id,
            "correlation_id": transport_headers.x_correlation_id,
            "trace_id": transport_headers.x_trace_id,
        }

    def validate_idempotency_key(self, idempotency_key: str) -> bool:
        """Validate idempotency key format."""
        if not idempotency_key:
            return False

        # Basic validation - can be enhanced
        return len(idempotency_key) >= 8 and len(idempotency_key) <= 255

    def create_request_context(
        self,
        headers: dict[str, str],
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create comprehensive request context."""
        transport_headers = TransportHeaders.from_dict(headers)

        context = {
            "method": method,
            "path": path,
            "headers": transport_headers.to_dict(),
            "tenant_context": self.extract_tenant_context(headers),
            "has_idempotency_key": transport_headers.idempotency_key is not None,
            "body_size": len(str(body)) if body else 0,
        }

        return context

    def should_retry_request(
        self, status_code: int, attempt: int, max_attempts: int = 3
    ) -> bool:
        """Determine if request should be retried based on status code."""
        if attempt >= max_attempts:
            return False

        # Retry on server errors and specific client errors
        retry_codes = {500, 502, 503, 504, 408, 429}
        return status_code in retry_codes

    def calculate_backoff_delay(self, attempt: int, base_delay: float = 1.0) -> float:
        """Calculate exponential backoff delay."""
        return base_delay * (2**attempt)

    def log_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        status_code: int,
        duration_ms: float,
        error: str | None = None,
    ):
        """Log request with standardized format."""
        transport_headers = TransportHeaders.from_dict(headers)

        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": transport_headers.x_request_id,
            "tenant_id": transport_headers.x_tenant_id,
            "trace_id": transport_headers.x_trace_id,
        }

        if error:
            log_data["error"] = error
            logger.error("Request failed", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)


__all__ = ["TransportCoreSDK", "TransportHeaders", "ErrorEnvelope"]
