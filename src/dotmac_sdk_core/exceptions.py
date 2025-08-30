"""
DotMac SDK Core Exceptions

Standardized exception hierarchy for HTTP client operations
providing structured error handling and response context.
"""

from typing import Any, Dict, Optional

from dotmac_shared.api.exception_handlers import standard_exception_handler


class SDKError(Exception):
    """Base exception for all SDK operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class HTTPClientError(SDKError):
    """Base class for HTTP client errors."""

    def __init__(
        self,
        message: str,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.response = response

    @property
    def status_code(self) -> Optional[int]:
        """Get HTTP status code if available."""
        return self.response.status_code if self.response else None

    @property
    def response_text(self) -> Optional[str]:
        """Get response text if available."""
        return self.response.text if self.response else None

    @property
    def response_json(self) -> Optional[Dict[str, Any]]:
        """Get response JSON if available."""
        return self.response.json_data if self.response else None


class ConnectionError(HTTPClientError):
    """Raised when connection to remote server fails."""

    pass


class TimeoutError(HTTPClientError):
    """Raised when request times out."""

    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, response, details)
        self.timeout_duration = timeout_duration


class AuthenticationError(HTTPClientError):
    """Raised when authentication fails (401/403)."""

    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, response, details)
        self.auth_type = auth_type


class RateLimitError(HTTPClientError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        rate_limit_reset: Optional[int] = None,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, response, details)
        self.retry_after = retry_after
        self.rate_limit_reset = rate_limit_reset


class ValidationError(HTTPClientError):
    """Raised when request validation fails (400-499)."""

    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, Any]] = None,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, response, details)
        self.validation_errors = validation_errors or {}


class ServerError(HTTPClientError):
    """Raised when server error occurs (500-599)."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, response, details)
        self.error_code = error_code


class CircuitBreakerError(SDKError):
    """Raised when circuit breaker is open."""

    def __init__(
        self,
        message: str,
        state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.state = state


class RetryExhaustedError(HTTPClientError):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        message: str,
        attempts: int = 0,
        last_exception: Optional[Exception] = None,
        response: Optional["HTTPResponse"] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, response, details)
        self.attempts = attempts
        self.last_exception = last_exception


class ConfigurationError(SDKError):
    """Raised when client configuration is invalid."""

    pass


class TelemetryError(SDKError):
    """Raised when telemetry/observability operation fails."""

    pass


class MiddlewareError(SDKError):
    """Raised when middleware operation fails."""

    def __init__(
        self,
        message: str,
        middleware_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.middleware_name = middleware_name


# Exception mapping for HTTP status codes
STATUS_CODE_EXCEPTIONS = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthenticationError,
    404: ValidationError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}


def create_http_error(
    status_code: int, message: str, response: Optional["HTTPResponse"] = None
) -> HTTPClientError:
    """
    Create appropriate HTTP error based on status code.

    Args:
        status_code: HTTP status code
        message: Error message
        response: Optional HTTP response

    Returns:
        Appropriate HTTPClientError subclass
    """
    exception_class = STATUS_CODE_EXCEPTIONS.get(status_code, HTTPClientError)

    if status_code == 429 and response:
        # Extract rate limit information
        retry_after = None
        rate_limit_reset = None

        if response.headers:
            retry_after = response.headers.get("Retry-After")
            rate_limit_reset = response.headers.get("X-RateLimit-Reset")

            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = None

            if rate_limit_reset:
                try:
                    rate_limit_reset = int(rate_limit_reset)
                except ValueError:
                    rate_limit_reset = None

        return RateLimitError(
            message,
            retry_after=retry_after,
            rate_limit_reset=rate_limit_reset,
            response=response,
        )

    return exception_class(message, response=response)
