"""Exception handlers for DotMac ISP Framework."""

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)


class DotMacISPException(Exception):
    """Base exception for DotMac ISP Framework."""

    def __init__(self, message: str, error_code: str = None, status_code: int = 500):
        """  Init   operation."""
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.status_code = status_code
        super().__init__(self.message)


class TenantNotFoundError(DotMacISPException):
    """Exception raised when tenant is not found."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            message=f"Tenant {tenant_id} not found",
            error_code="TENANT_NOT_FOUND",
            status_code=404,
        )


class InsufficientPermissionsError(DotMacISPException):
    """Exception raised when user has insufficient permissions."""

    def __init__(self, required_permission: str = None):
        """  Init   operation."""
        message = "Insufficient permissions"
        if required_permission:
            message += f" (required: {required_permission})"

        super().__init__(
            message=message, error_code="INSUFFICIENT_PERMISSIONS", status_code=403
        )


class ResourceNotFoundError(DotMacISPException):
    """Exception raised when a resource is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        """  Init   operation."""
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
        )


class ValidationError(DotMacISPException):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: str = None):
        """  Init   operation."""
        error_code = "VALIDATION_ERROR"
        if field:
            error_code = f"VALIDATION_ERROR_{field.upper()}"

        super().__init__(message=message, error_code=error_code, status_code=400)


class AuthenticationError(DotMacISPException):
    """Exception raised for authentication failures."""

    def __init__(self, message: str = "Authentication failed"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(DotMacISPException):
    """Exception raised for authorization failures."""

    def __init__(self, message: str = "Authorization failed"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class SecurityViolationError(DotMacISPException):
    """Exception raised for security violations."""

    def __init__(self, message: str = "Security violation detected"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="SECURITY_VIOLATION",
            status_code=403,
        )


class RateLimitExceededError(DotMacISPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )


class BillingError(DotMacISPException):
    """Exception raised for billing-related errors."""

    def __init__(self, message: str = "Billing error occurred"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="BILLING_ERROR",
            status_code=400,
        )


class InsufficientCreditError(BillingError):
    """Exception raised when customer has insufficient credit."""

    def __init__(self, message: str = "Insufficient credit"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_CREDIT",
            status_code=402,
        )


class PaymentFailedError(BillingError):
    """Exception raised when payment processing fails."""

    def __init__(self, message: str = "Payment failed"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="PAYMENT_FAILED",
            status_code=402,
        )


class IPAMError(DotMacISPException):
    """Exception raised for IPAM (IP Address Management) related errors."""

    def __init__(self, message: str = "IPAM operation failed"):
        """  Init   operation."""
        super().__init__(
            message=message,
            error_code="IPAM_ERROR",
            status_code=400,
        )


def create_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: Any = None,
    request_id: str = None,
) -> JSONResponse:
    """Create a standardized error response."""
    error_content: Dict[str, Any] = {
        "error": True,
        "message": message,
        "status_code": status_code,
    }

    if error_code:
        error_content["error_code"] = error_code

    if details:
        error_content["details"] = details

    if request_id:
        error_content["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=error_content)


async def dotmac_exception_handler(
    request: Request, exc: DotMacISPException
) -> JSONResponse:
    """Handle DotMac ISP Framework exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(f"DotMac ISP Exception: {exc.message}", exc_info=True)

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        request_id=request_id,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    return create_error_response(
        status_code=exc.status_code,
        message=exc.detail,
        error_code="HTTP_ERROR",
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    request_id = getattr(request.state, "request_id", None)

    # Convert any bytes objects to strings for JSON serialization
    errors = []
    for error in exc.errors():
        clean_error = {}
        for key, value in error.items():
            if isinstance(value, bytes):
                clean_error[key] = value.decode("utf-8", errors="replace")
            else:
                clean_error[key] = value
        errors.append(clean_error)

    logger.warning(f"Validation error: {errors}")

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        error_code="VALIDATION_ERROR",
        details=errors,
        request_id=request_id,
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handle database integrity errors."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(f"Database integrity error: {exc}", exc_info=True)

    # Check for common integrity constraints
    message = "Data integrity constraint violation"
    if "unique constraint" in str(exc).lower():
        message = "A record with these values already exists"
    elif "foreign key constraint" in str(exc).lower():
        message = "Referenced record does not exist"
    elif "check constraint" in str(exc).lower():
        message = "Data does not meet validation requirements"

    return create_error_response(
        status_code=status.HTTP_409_CONFLICT,
        message=message,
        error_code="INTEGRITY_ERROR",
        request_id=request_id,
    )


async def operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    """Handle database operational errors."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(f"Database operational error: {exc}", exc_info=True)

    return create_error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        message="Database temporarily unavailable",
        error_code="DATABASE_ERROR",
        request_id=request_id,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        error_code="INTERNAL_ERROR",
        request_id=request_id,
    )


def add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to the FastAPI application."""
    logger.info("Adding exception handlers...")

    # Custom exception handlers
    app.add_exception_handler(DotMacISPException, dotmac_exception_handler)

    # FastAPI/Starlette exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Database exception handlers
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)

    # General exception handler (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers added successfully")
