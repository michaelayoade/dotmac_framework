"""
Core exception classes for the DotMac framework.

Provides structured, JSON-serializable exceptions with error codes and details.
All exceptions are designed to be framework-agnostic and dependency-free.
"""

from typing import Any


class CoreError(Exception):
    """
    Base exception class for all DotMac framework errors.
    
    Provides structured error information with optional error codes and details
    for consistent error handling across services.
    
    Args:
        message: Human-readable error description
        error_code: Optional machine-readable error code
        details: Optional additional error context as key-value pairs
        
    Example:
        raise CoreError("Database connection failed", "DB_CONN_ERROR", {"host": "localhost"})
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"details={self.details!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert this error to a JSON-serializable dictionary.
        
        Returns:
            Dictionary containing error information suitable for JSON serialization
        """
        return {
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ValidationError(CoreError):
    """
    Raised when input validation fails.
    
    Example:
        raise ValidationError("Invalid email format", "INVALID_EMAIL", {"value": "not-an-email"})
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "VALIDATION_ERROR", details)


class NotFoundError(CoreError):
    """
    Raised when a requested resource is not found.
    
    Example:
        raise NotFoundError("User not found", "USER_NOT_FOUND", {"user_id": "123"})
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "NOT_FOUND", details)


class ConflictError(CoreError):
    """
    Raised when a request conflicts with current state.
    
    Example:
        raise ConflictError("Email already exists", "EMAIL_CONFLICT", {"email": "user@example.com"})
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "CONFLICT", details)


class UnauthorizedError(CoreError):
    """
    Raised when authentication is required but missing or invalid.
    
    Example:
        raise UnauthorizedError("Invalid API key", "INVALID_API_KEY")
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "UNAUTHORIZED", details)


class ForbiddenError(CoreError):
    """
    Raised when the authenticated user lacks required permissions.
    
    Example:
        raise ForbiddenError("Insufficient permissions", "ACCESS_DENIED", {"required_role": "admin"})
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "FORBIDDEN", details)


class ExternalServiceError(CoreError):
    """
    Raised when an external service call fails.
    
    Example:
        raise ExternalServiceError("Payment gateway timeout", "PAYMENT_TIMEOUT", {"service": "stripe"})
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "EXTERNAL_SERVICE_ERROR", details)


class TimeoutError(CoreError):
    """
    Raised when an operation times out.
    
    Example:
        raise TimeoutError("Database query timeout", "DB_TIMEOUT", {"timeout_seconds": 30})
    """
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        super().__init__(message, error_code or "TIMEOUT", details)


def to_dict(err: Exception) -> dict[str, Any]:
    """
    Convert an exception to a JSON-serializable dictionary.
    
    For CoreError instances, includes structured fields. For other exceptions,
    provides basic information with a default error code.
    
    Args:
        err: Exception to convert
        
    Returns:
        Dictionary containing error information suitable for JSON serialization
        
    Example:
        >>> error = ValidationError("Invalid email", "INVALID_EMAIL", {"value": "bad-email"})
        >>> to_dict(error)
        {
            'message': 'Invalid email',
            'error_code': 'INVALID_EMAIL',
            'details': {'value': 'bad-email'}
        }
    """
    if isinstance(err, CoreError):
        return {
            "message": err.message,
            "error_code": err.error_code,
            "details": err.details
        }
    else:
        return {
            "message": str(err),
            "error_code": "UNKNOWN_ERROR",
            "details": None
        }


__all__ = [
    "CoreError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "ExternalServiceError",
    "TimeoutError",
    "to_dict",
]
