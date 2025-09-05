"""
Core exceptions for DotMac Framework.
Provides consistent exception handling across all platforms.
"""

from typing import Any, Optional

from fastapi import HTTPException, status


class DotMacException(Exception):
    """Base exception for DotMac Framework."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": True,
            "message": self.message,
            "error_code": self.error_code,
            "status_code": self.status_code,
            "details": self.details,
        }

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "message": self.message,
                "error_code": self.error_code,
                "details": self.details,
            },
        )


class ValidationError(DotMacException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details or {},
        )
        if field:
            self.details["field"] = field


class AuthenticationError(DotMacException):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(DotMacException):
    """Exception raised for authorization failures."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class EntityNotFoundError(DotMacException):
    """Exception raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} with ID {entity_id} not found",
            error_code="ENTITY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class BusinessRuleError(DotMacException):
    """Exception raised for business rule violations."""

    def __init__(self, message: str, rule_code: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VIOLATION",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"rule_code": rule_code} if rule_code else {},
        )


class DuplicateEntityError(DotMacException):
    """Exception raised when trying to create a duplicate entity."""

    def __init__(self, message: str = "Entity already exists"):
        super().__init__(
            message=message,
            error_code="DUPLICATE_ENTITY",
            status_code=status.HTTP_409_CONFLICT,
        )


class DatabaseError(DotMacException):
    """Exception raised for database operation errors."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ServiceError(DotMacException):
    """Exception raised for service-level errors."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {},
        )
        if service_name:
            self.details["service"] = service_name


class RateLimitError(DotMacException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class TenantNotFoundError(EntityNotFoundError):
    """Exception raised when tenant is not found."""

    def __init__(self, tenant_id: str):
        super().__init__("Tenant", tenant_id)
        self.error_code = "TENANT_NOT_FOUND"


class ConfigurationError(DotMacException):
    """Exception raised for configuration errors."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"config_key": config_key} if config_key else {},
        )


class ExternalServiceError(DotMacException):
    """Exception raised for external service errors."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code or "EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details or {},
        )
        if service_name:
            self.details["service"] = service_name


# Legacy exception aliases for backward compatibility
NotFoundError = EntityNotFoundError
BusinessLogicError = BusinessRuleError
