"""
Exception classes for DotMac API Gateway.
"""


class GatewayError(Exception):
    """Base exception for API Gateway errors."""

    def __init__(self, message: str, error_code: str = None, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GATEWAY_ERROR"
        self.status_code = status_code


class AuthenticationError(GatewayError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", error_code: str = "AUTH_FAILED"):
        super().__init__(message, error_code, 401)


class AuthorizationError(GatewayError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Authorization failed", error_code: str = "AUTHZ_FAILED"):
        super().__init__(message, error_code, 403)


class RateLimitError(GatewayError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", error_code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(message, error_code, 429)


class RoutingError(GatewayError):
    """Raised when routing fails."""

    def __init__(self, message: str = "Routing failed", error_code: str = "ROUTING_FAILED"):
        super().__init__(message, error_code, 404)


class UpstreamError(GatewayError):
    """Raised when upstream service fails."""

    def __init__(self, message: str = "Upstream service error", error_code: str = "UPSTREAM_ERROR"):
        super().__init__(message, error_code, 502)


class ConfigurationError(GatewayError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str = "Configuration error", error_code: str = "CONFIG_ERROR"):
        super().__init__(message, error_code, 500)


class ValidationError(GatewayError):
    """Raised when request validation fails."""

    def __init__(self, message: str = "Validation failed", error_code: str = "VALIDATION_ERROR"):
        super().__init__(message, error_code, 400)


class TimeoutError(GatewayError):
    """Raised when request times out."""

    def __init__(self, message: str = "Request timeout", error_code: str = "TIMEOUT_ERROR"):
        super().__init__(message, error_code, 504)


class CircuitBreakerError(GatewayError):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker open", error_code: str = "CIRCUIT_BREAKER_OPEN"):
        super().__init__(message, error_code, 503)
