"""
Production-ready exception handling with strict enforcement.
Mandatory decorator usage - no manual try-catch blocks allowed.
"""

import functools
import logging
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from dotmac.core import (
    AuthorizationError,
    DotMacError,
    ValidationError,
)
from dotmac.core import ValidationError as CustomValidationError

# Try to import additional platform exceptions
try:
    from dotmac.platform.auth.exceptions import AuthenticationError as PlatformAuthError
    from dotmac.platform.auth.exceptions import (
        InvalidTokenError,
        TokenExpiredError,
    )
    _has_platform_auth_exceptions = True
except ImportError:
    PlatformAuthError = None
    TokenExpiredError = None
    InvalidTokenError = None
    _has_platform_auth_exceptions = False

try:
    from dotmac.core.exceptions import BusinessRuleError as CoreBusinessRuleError
    from dotmac.core.exceptions import EntityNotFoundError as CoreEntityNotFoundError
    _has_core_exceptions = True
except ImportError:
    CoreEntityNotFoundError = None
    CoreBusinessRuleError = None
    _has_core_exceptions = False

# Define missing exception types locally for backward compatibility
class AuthenticationError(DotMacError):
    """Authentication failed."""

class BusinessRuleError(DotMacError):
    """Business rule violation."""

class EntityNotFoundError(DotMacError):
    """Entity not found."""

class ExternalServiceError(DotMacError):
    """External service error."""

class RateLimitError(DotMacError):
    """Rate limit exceeded."""

class ServiceError(DotMacError):
    """Internal service error."""

logger = logging.getLogger(__name__)


# === Custom HTTP Exception Classes ===


class DotMacHTTPException(HTTPException):
    """Standard HTTP exception with enhanced error information."""

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(status_code, detail, headers)
        self.error_code = error_code


class ValidationHTTPException(DotMacHTTPException):
    """HTTP exception specifically for validation errors."""

    def __init__(
        self,
        detail: Any = None,
        headers: dict[str, Any] | None = None,
        error_code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            headers=headers,
            error_code=error_code,
        )


# === Standard Error Response Format ===


class ErrorResponse:
    """Standardized error response structure."""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
        field_errors: dict[str, str] | None = None,
        request_id: str | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.field_errors = field_errors or {}
        self.request_id = request_id
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        response = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp,
            }
        }

        if self.details:
            response["error"]["details"] = self.details

        if self.field_errors:
            response["error"]["field_errors"] = self.field_errors

        if self.request_id:
            response["error"]["request_id"] = self.request_id

        return response


# === Comprehensive Exception to HTTP Status Mapping ===

def _build_exception_maps() -> tuple[dict, dict]:
    """Build exception mapping dictionaries dynamically."""
    status_map = {
        # Local exceptions
        EntityNotFoundError: status.HTTP_404_NOT_FOUND,
        CustomValidationError: status.HTTP_400_BAD_REQUEST,
        BusinessRuleError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
        ServiceError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    code_map = {
        # Local exceptions
        EntityNotFoundError: "ENTITY_NOT_FOUND",
        CustomValidationError: "VALIDATION_ERROR",
        BusinessRuleError: "BUSINESS_RULE_VIOLATION",
        AuthenticationError: "AUTHENTICATION_FAILED",
        AuthorizationError: "ACCESS_DENIED",
        RateLimitError: "RATE_LIMIT_EXCEEDED",
        ExternalServiceError: "EXTERNAL_SERVICE_ERROR",
        ServiceError: "INTERNAL_ERROR",
    }

    # Add platform auth exceptions if available
    if _has_platform_auth_exceptions:
        if PlatformAuthError:
            status_map[PlatformAuthError] = status.HTTP_401_UNAUTHORIZED
            code_map[PlatformAuthError] = "PLATFORM_AUTH_ERROR"
        if TokenExpiredError:
            status_map[TokenExpiredError] = status.HTTP_401_UNAUTHORIZED
            code_map[TokenExpiredError] = "TOKEN_EXPIRED"
        if InvalidTokenError:
            status_map[InvalidTokenError] = status.HTTP_401_UNAUTHORIZED
            code_map[InvalidTokenError] = "INVALID_TOKEN"

    # Add core exceptions if available
    if _has_core_exceptions:
        if CoreEntityNotFoundError:
            status_map[CoreEntityNotFoundError] = status.HTTP_404_NOT_FOUND
            code_map[CoreEntityNotFoundError] = "CORE_ENTITY_NOT_FOUND"
        if CoreBusinessRuleError:
            status_map[CoreBusinessRuleError] = status.HTTP_422_UNPROCESSABLE_ENTITY
            code_map[CoreBusinessRuleError] = "CORE_BUSINESS_RULE_VIOLATION"

    return status_map, code_map

EXCEPTION_STATUS_MAP, ERROR_CODE_MAP = _build_exception_maps()


# === Standard Exception Handler Decorator ===


def standard_exception_handler(func: Callable) -> Callable:
    """
    MANDATORY exception handler decorator for all router endpoints.
    Using manual try-catch blocks is FORBIDDEN in production code.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Validate decorator is being used correctly
        if not hasattr(func, "__annotations__"):
            raise RuntimeError(f"Function {func.__name__} must have type annotations")

        try:
            # Execute the wrapped function
            result = await func(*args, **kwargs)

            # Log successful execution for audit trail
            logger.debug(f"Successfully executed {func.__name__}")
            return result

        except HTTPException:
            # Re-raise FastAPI HTTPExceptions as-is
            raise

        except tuple(EXCEPTION_STATUS_MAP.keys()) as e:
            status_code = EXCEPTION_STATUS_MAP.get(
                type(e), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            error_code = ERROR_CODE_MAP.get(type(e), "UNKNOWN_ERROR")

            # Enhanced logging with context
            logger.warning(
                f"{error_code} in {func.__name__}: {str(e)}",
                extra={
                    "error_code": error_code,
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                },
            )

            raise HTTPException(
                status_code=status_code,
                detail=ErrorResponse(
                    error_code=error_code,
                    message=str(e),
                    details=getattr(e, "details", None),
                ).to_dict(),
            ) from e

        except ValidationError as e:
            # Enhanced Pydantic validation error handling
            field_errors = {}
            for error in e.errors():
                field_name = ".".join(str(loc) for loc in error["loc"])
                field_errors[field_name] = error["msg"]

            logger.warning(
                f"Validation error in {func.__name__}: {field_errors}",
                extra={"validation_errors": field_errors},
            )

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=ErrorResponse(
                    error_code="VALIDATION_ERROR",
                    message="Request validation failed",
                    field_errors=field_errors,
                ).to_dict(),
            ) from e

        except Exception as e:
            # Handle unexpected errors with enhanced monitoring
            error_id = f"ERR_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

            # Enhanced error logging
            logger.error(
                f"Critical error {error_id} in {func.__name__}: {str(e)}",
                extra={
                    "error_id": error_id,
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
                exc_info=True,
            )

            # In production, don't expose internal details
            is_production = sys.argv[0].endswith("gunicorn") or "prod" in sys.argv

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code="INTERNAL_ERROR",
                    message="An internal error occurred",
                    details={"error_id": error_id} if not is_production else {},
                ).to_dict(),
            ) from e

    return wrapper


# === Application-Level Exception Handlers ===


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions with standardized format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            request_id=getattr(request.state, "request_id", None),
        ).to_dict(),
    )


async def handle_validation_exception(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI validation errors."""
    field_errors = {}
    for error in exc.errors():
        field_name = ".".join(
            str(loc) for loc in error["loc"][1:]
        )  # Skip 'body' prefix
        field_errors[field_name] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            field_errors=field_errors,
            request_id=getattr(request.state, "request_id", None),
        ).to_dict(),
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exception."""
    error_id = f"ERR_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    logger.error(f"Unhandled exception {error_id}: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An internal error occurred",
            details={"error_id": error_id},
            request_id=getattr(request.state, "request_id", None),
        ).to_dict(),
    )


# === Specific Domain Exception Handlers ===


def billing_exception_handler(func: Callable) -> Callable:
    """Specialized exception handler for billing operations."""

    @standard_exception_handler
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            if "payment" in str(e).lower():
                raise CustomValidationError(
                    f"Payment validation failed: {str(e)}"
                ) from e
            raise

    return wrapper


def auth_exception_handler(func: Callable) -> Callable:
    """Specialized exception handler for authentication operations."""

    @standard_exception_handler
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except KeyError as e:
            if "token" in str(e).lower():
                raise AuthenticationError(
                    "Invalid or missing authentication token"
                ) from e
            raise

    return wrapper


def network_exception_handler(func: Callable) -> Callable:
    """Specialized exception handler for network operations."""

    @standard_exception_handler
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ConnectionError as e:
            raise ExternalServiceError(f"Network service unavailable: {str(e)}") from e
        except TimeoutError as e:
            raise ExternalServiceError(f"Network operation timed out: {str(e)}") from e

    return wrapper


# === Router Registration Helper ===


def register_exception_handlers(app):
    """Register all standard exception handlers with FastAPI app."""
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_exception)
    app.add_exception_handler(Exception, handle_generic_exception)


# === Error Logging Configuration ===


class ErrorLogger:
    """Centralized error logging with context."""

    @staticmethod
    def log_business_error(error: Exception, context: dict[str, Any]):
        """Log business rule violations."""
        logger.warning(
            f"Business error: {str(error)}",
            extra={"error_type": type(error).__name__, "context": context},
        )

    @staticmethod
    def log_system_error(error: Exception, context: dict[str, Any]):
        """Log system errors."""
        logger.error(
            f"System error: {str(error)}",
            extra={
                "error_type": type(error).__name__,
                "context": context,
                "traceback": traceback.format_exc(),
            },
        )


# === Usage Examples ===

"""
BEFORE (repeated in every router):
@router.post("/customers")
async def create_customer(data: CustomerCreate, db = Depends(get_db)):  # noqa: B008
    try:
        service = CustomerService(db)
        return await service.create_customer(data)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

AFTER (DRY approach):
@router.post("/customers")
@standard_exception_handler
async def create_customer(data: CustomerCreate, deps: StandardDependencies = Depends(get_standard_deps)):  # noqa: B008
    service = CustomerService(deps.db)
    return await service.create_customer(data)

# All exception handling is automatic!
"""
