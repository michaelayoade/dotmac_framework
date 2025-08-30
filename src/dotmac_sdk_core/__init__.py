"""
DotMac SDK Core - HTTP Client Framework with Observability

A comprehensive HTTP client framework for DotMac services providing:
- Standardized HTTP client with async/sync support
- Retry logic with exponential backoff
- Circuit breaker patterns for resilience
- OpenTelemetry observability and metrics
- Centralized error handling and logging
- Request/response middleware
- Authentication and tenant context

Author: DotMac Framework Team
License: MIT
"""

# Authentication and middleware
from .auth.providers import APIKeyAuth, AuthProvider, BearerTokenAuth, JWTAuth

# Core HTTP client components
from .client.http_client import (
    DotMacHTTPClient,
    HTTPClientConfig,
    HTTPError,
    HTTPResponse,
)

# Error handling and exceptions
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    HTTPClientError,
    RateLimitError,
    SDKError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .middleware.base import HTTPMiddleware, RequestMiddleware, ResponseMiddleware
from .middleware.logging_middleware import LoggingMiddleware
from .middleware.rate_limiting import RateLimitMiddleware
from .middleware.tenant_context import TenantContextMiddleware

# Observability and metrics
from .observability.telemetry import HTTPMetrics, SDKTelemetry, TelemetryConfig
from .observability.tracing import (
    SpanAttributes,
    TraceableHTTPClient,
    trace_http_request,
)

# Circuit breaker and resilience
from .resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerState,
)
from .resilience.retry_strategies import (
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
    LinearBackoffStrategy,
    RetryStrategy,
)
from .utils.header_utils import build_headers, extract_tenant_context
from .utils.request_builder import RequestBuilder

# Utilities
from .utils.response_parser import ResponseParser

__version__ = "1.0.0"

__all__ = [
    # Core client
    "DotMacHTTPClient",
    "HTTPClientConfig",
    "HTTPResponse",
    "HTTPError",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerError",
    # Retry strategies
    "RetryStrategy",
    "ExponentialBackoffStrategy",
    "FixedDelayStrategy",
    "LinearBackoffStrategy",
    # Observability
    "SDKTelemetry",
    "TelemetryConfig",
    "HTTPMetrics",
    "TraceableHTTPClient",
    "SpanAttributes",
    "trace_http_request",
    # Authentication
    "AuthProvider",
    "BearerTokenAuth",
    "APIKeyAuth",
    "JWTAuth",
    # Middleware
    "HTTPMiddleware",
    "RequestMiddleware",
    "ResponseMiddleware",
    "TenantContextMiddleware",
    "RateLimitMiddleware",
    "LoggingMiddleware",
    # Exceptions
    "SDKError",
    "HTTPClientError",
    "ConnectionError",
    "TimeoutError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    # Utilities
    "ResponseParser",
    "RequestBuilder",
    "build_headers",
    "extract_tenant_context",
]
