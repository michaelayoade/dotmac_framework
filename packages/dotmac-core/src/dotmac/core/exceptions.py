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


class ValidationError(DotMacError):
    """Raised when data validation fails."""


class AuthenticationError(DotMacError):
    """Raised when authentication fails."""


class AuthorizationError(DotMacError):
    """Raised when authorization fails."""


class ConnectionError(DotMacError):
    """Raised when connection fails."""


class TimeoutError(DotMacError):
    """Raised when an operation times out."""


class RateLimitError(DotMacError):
    """Raised when rate limits are exceeded."""


class CircuitBreakerError(DotMacError):
    """Raised when circuit breaker is open."""


class SDKError(DotMacError):
    """Raised for SDK-related errors."""


class DatabaseError(DotMacError):
    """Base exception for database-related errors."""


class TransactionError(DatabaseError):
    """Raised when database transaction fails."""


class TenantError(DotMacError):
    """Base exception for tenant-related errors."""


class TenantNotFoundError(TenantError):
    """Raised when tenant cannot be found."""


class TenantConfigurationError(TenantError):
    """Raised when tenant configuration is invalid."""


class MultiTenantError(TenantError):
    """Raised when multiple tenants are found unexpectedly."""


# Database-specific exceptions
class DatabaseConnectionError(DatabaseError, ConnectionError):
    """Raised when database connection fails."""


class DatabaseTransactionError(DatabaseError):
    """Raised when database transaction fails."""


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails."""


class QueryError(DatabaseError):
    """Raised when query execution fails."""


class IntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated."""


# Cache-specific exceptions
class CacheError(DotMacError):
    """Base exception for cache-related errors."""


class CacheConnectionError(CacheError, ConnectionError):
    """Raised when cache connection fails."""


class CacheSerializationError(CacheError):
    """Raised when cache serialization fails."""


# Plugin-specific exceptions
class PluginError(DotMacError):
    """Base exception for plugin-related errors."""


class PluginLoadError(PluginError):
    """Raised when plugin loading fails."""


class PluginValidationError(PluginError, ValidationError):
    """Raised when plugin validation fails."""


# Service-specific exceptions
class ServiceError(DotMacError):
    """Base exception for service-related errors."""


class ServiceUnavailableError(ServiceError):
    """Raised when a service is unavailable."""


class ServiceConfigurationError(ServiceError, ConfigurationError):
    """Raised when service configuration is invalid."""


class BusinessRuleError(DotMacError):
    """Raised when business rules are violated."""


class NotFoundError(DotMacError):
    """Raised when a requested resource is not found."""


class AlreadyExistsError(DotMacError):
    """Raised when trying to create a resource that already exists."""


class EntityNotFoundError(NotFoundError):
    """Alias for NotFoundError - commonly used in legacy code."""


class ExternalServiceError(ServiceError):
    """Raised when external service integration fails."""


class PermissionError(AuthorizationError):
    """Alias for AuthorizationError - commonly used in legacy code."""
