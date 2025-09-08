"""
Custom exception classes and error handlers for the DotMac Management Platform.

Provides structured error handling with specific exception types
for different business logic and system errors.
"""
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from dotmac_shared.exceptions import DotMacException

logger = logging.getLogger(__name__)


class DotMacError(Exception):
    """Base exception class for all DotMac Management Platform errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(DotMacError):
    """Raised when input validation fails."""

    pass


class AuthenticationError(DotMacError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(DotMacError):
    """Raised when user lacks required permissions."""

    pass


class ResourceNotFoundError(DotMacError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, identifier: Any, **kwargs):
        message = f"{resource_type} with identifier '{identifier}' not found"
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.identifier = identifier


class ResourceConflictError(DotMacError):
    """Raised when a resource conflict occurs (e.g., duplicate names)."""

    pass


class BusinessLogicError(DotMacError):
    """Raised when business logic validation fails."""

    pass


class ExternalServiceError(DotMacError):
    """Raised when external service integration fails."""

    pass


class DatabaseError(DotMacError):
    """Raised when database operations fail."""

    pass


# NO BACKWARD COMPATIBILITY - Use DotMacError directly
# BREAKING: Replace DotMacException with DotMacError


# Tenant-specific exceptions
class TenantNotFoundError(ResourceNotFoundError):
    """Raised when tenant is not found."""

    def __init__(self, tenant_id: UUID, **kwargs):
        super().__init__("Tenant", tenant_id, **kwargs)


class TenantNameConflictError(ResourceConflictError):
    """Raised when tenant name already exists."""

    def __init__(self, tenant_name: str, **kwargs):
        message = f"Tenant name '{tenant_name}' already exists"
        super().__init__(message, **kwargs)


class TenantNotActiveError(BusinessLogicError):
    """Raised when attempting operations on inactive tenant."""

    def __init__(self, tenant_id: UUID, status: str, **kwargs):
        message = f"Tenant {tenant_id} is not active (status: {status})"
        super().__init__(message, **kwargs)


# User-specific exceptions
class UserNotFoundError(ResourceNotFoundError):
    """Raised when user is not found."""

    def __init__(self, user_identifier: str, **kwargs):
        super().__init__("User", user_identifier, **kwargs)


class UserEmailConflictError(ResourceConflictError):
    """Raised when user email already exists."""

    def __init__(self, email: str, **kwargs):
        message = f"User with email '{email}' already exists"
        super().__init__(message, **kwargs)


class UserInactiveError(BusinessLogicError):
    """Raised when user account is inactive."""

    def __init__(self, user_id: UUID, **kwargs):
        message = f"User account {user_id} is inactive"
        super().__init__(message, **kwargs)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    def __init__(self, **kwargs):
        message = "Invalid email or password"
        super().__init__(message, **kwargs)


# Billing-specific exceptions
class SubscriptionNotFoundError(ResourceNotFoundError):
    """Raised when subscription is not found."""

    def __init__(self, subscription_identifier: str, **kwargs):
        super().__init__("Subscription", subscription_identifier, **kwargs)


class ActiveSubscriptionExistsError(BusinessLogicError):
    """Raised when tenant already has active subscription."""

    def __init__(self, tenant_id: UUID, **kwargs):
        message = f"Tenant {tenant_id} already has an active subscription"
        super().__init__(message, **kwargs)


class PaymentProcessingError(ExternalServiceError):
    """Raised when payment processing fails."""

    def __init__(self, reason: str, provider: str = "stripe", **kwargs):
        message = f"Payment processing failed: {reason}"
        super().__init__(message, error_code=f"{provider}_payment_error", **kwargs)


# Security exceptions
class TenantIsolationViolationError(AuthorizationError):
    """Raised when tenant isolation is violated."""

    def __init__(self, user_tenant_id: UUID, requested_tenant_id: UUID, **kwargs):
        message = f"Access denied: user from tenant {user_tenant_id} cannot access resources from tenant {requested_tenant_id}"
        super().__init__(message, **kwargs)


class SecurityValidationError(ValidationError):
    """Raised when security validation fails."""

    def __init__(self, field: str, reason: str, **kwargs):
        message = f"Security validation failed for {field}: {reason}"
        super().__init__(message, **kwargs)


class TenantLimitExceededError(DotMacException):
    """Tenant limit exceeded error."""

    def __init__(self, current_count: int, max_limit: int):
        super().__init__(
            message=f"Tenant limit exceeded: {current_count}/{max_limit}",
            error_code="TENANT_LIMIT_EXCEEDED",
            details={"current_count": current_count, "max_limit": max_limit},
        )


class DeploymentFailedError(DotMacException):
    """Deployment failed error."""

    def __init__(self, deployment_id: str, reason: str):
        super().__init__(
            message=f"Deployment '{deployment_id}' failed: {reason}",
            error_code="DEPLOYMENT_FAILED",
            details={"deployment_id": deployment_id, "reason": reason},
        )


class BillingError(DotMacException):
    """Billing operation error."""

    def __init__(self, message: str, subscription_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="BILLING_ERROR",
            details={"subscription_id": subscription_id} if subscription_id else {},
        )


class PluginLicenseError(DotMacException):
    """Plugin licensing error."""

    def __init__(self, plugin_id: str, tenant_id: str, reason: str):
        super().__init__(
            message=f"Plugin license error for '{plugin_id}' on tenant '{tenant_id}': {reason}",
            error_code="PLUGIN_LICENSE_ERROR",
            details={"plugin_id": plugin_id, "tenant_id": tenant_id, "reason": reason},
        )


class ValidationError(DotMacException):
    """Validation error."""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error for '{field}': {message}",
            error_code="VALIDATION_ERROR",
            details={"field": field},
        )


async def dotmac_exception_handler(request: Request, exc: DotMacError) -> JSONResponse:
    """Handle DotMac custom exceptions."""
    logger.error(
        f"DotMac exception: {exc.error_code} - {exc.message}",
        extra={"details": exc.details, "path": str(request.url)},
    )
    # Map exception types to HTTP status codes
    if isinstance(exc, ResourceNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ResourceConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, AuthenticationError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, BusinessLogicError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, ExternalServiceError):
        # Payment errors get 402, others get 503
        if "payment" in exc.error_code.lower():
            status_code = status.HTTP_402_PAYMENT_REQUIRED
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, DatabaseError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "type": exc.__class__.__name__,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={"path": str(request.url)},
    )
    # Return standard FastAPI format for HTTP exceptions
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database exceptions."""
    logger.error(
        f"Database exception: {type(exc).__name__} - {str(exc)}",
        extra={"path": str(request.url)},
    )
    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "INTEGRITY_ERROR",
                    "message": "Database integrity constraint violation",
                    "details": {"type": "integrity_error"},
                }
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database operation failed",
                "details": {"type": type(exc).__name__},
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general unexpected exceptions."""
    logger.error(
        "Unexpected exception: %s - %s",
        type(exc).__name__,
        str(exc),
        extra={"path": str(request.url)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__},
            }
        },
    )


def add_exception_handlers(app: FastAPI) -> None:
    """Add all exception handlers to FastAPI app."""
    app.add_exception_handler(DotMacError, dotmac_exception_handler)
    app.add_exception_handler(DotMacException, dotmac_exception_handler)  # Legacy support
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
