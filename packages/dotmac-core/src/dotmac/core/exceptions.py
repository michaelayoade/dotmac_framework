"""
Core exceptions for the DotMac Framework.

This module consolidates all common exceptions used across the framework
to eliminate DRY violations and provide consistent error handling.
"""

from typing import Any


class DotMacError(Exception):
    """Base exception for all DotMac Framework errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        """String representation."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class ConfigurationError(DotMacError):
    """Raised when there's a configuration problem."""

    pass


class ValidationError(DotMacError):
    """Raised when data validation fails."""

    pass


class AuthenticationError(DotMacError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(DotMacError):
    """Raised when authorization fails."""

    pass


class ConnectionError(DotMacError):
    """Raised when connection fails."""

    pass


class TimeoutError(DotMacError):
    """Raised when an operation times out."""

    pass


class RateLimitError(DotMacError):
    """Raised when rate limits are exceeded."""

    pass


class CircuitBreakerError(DotMacError):
    """Raised when circuit breaker is open."""

    pass


class SDKError(DotMacError):
    """Raised for SDK-related errors."""

    pass


class DatabaseError(DotMacError):
    """Base exception for database-related errors."""

    pass


class TransactionError(DatabaseError):
    """Raised when database transaction fails."""

    pass


class TenantError(DotMacError):
    """Base exception for tenant-related errors."""

    pass


class TenantNotFoundError(TenantError):
    """Raised when tenant cannot be found."""

    pass


class TenantConfigurationError(TenantError):
    """Raised when tenant configuration is invalid."""

    pass


class MultiTenantError(TenantError):
    """Raised when multiple tenants are found unexpectedly."""

    pass


# Database-specific exceptions
class DatabaseConnectionError(DatabaseError, ConnectionError):
    """Raised when database connection fails."""

    pass


class DatabaseTransactionError(DatabaseError):
    """Raised when database transaction fails."""

    pass


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails."""

    pass


class QueryError(DatabaseError):
    """Raised when query execution fails."""

    pass


class IntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated."""

    pass


# Cache-specific exceptions
class CacheError(DotMacError):
    """Base exception for cache-related errors."""

    pass


class CacheConnectionError(CacheError, ConnectionError):
    """Raised when cache connection fails."""

    pass


class CacheSerializationError(CacheError):
    """Raised when cache serialization fails."""

    pass


# Plugin-specific exceptions
class PluginError(DotMacError):
    """Base exception for plugin-related errors."""

    pass


class PluginLoadError(PluginError):
    """Raised when plugin loading fails."""

    pass


class PluginValidationError(PluginError, ValidationError):
    """Raised when plugin validation fails."""

    pass


# Service-specific exceptions
class ServiceError(DotMacError):
    """Base exception for service-related errors."""

    pass


class ServiceUnavailableError(ServiceError):
    """Raised when a service is unavailable."""

    pass


class ServiceConfigurationError(ServiceError, ConfigurationError):
    """Raised when service configuration is invalid."""

    pass


class BusinessRuleError(DotMacError):
    """Raised when business rules are violated."""

    pass


class NotFoundError(DotMacError):
    """Raised when a requested resource is not found."""

    pass


class AlreadyExistsError(DotMacError):
    """Raised when trying to create a resource that already exists."""

    pass


class EntityNotFoundError(NotFoundError):
    """Alias for NotFoundError - commonly used in legacy code."""

    pass


class ExternalServiceError(ServiceError):
    """Raised when external service integration fails."""

    pass


class PermissionError(AuthorizationError):
    """Alias for AuthorizationError - commonly used in legacy code."""

    pass
