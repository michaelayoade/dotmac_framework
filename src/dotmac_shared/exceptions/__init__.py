"""
DRY Exception handling for DotMac Framework
"""

from .handlers import (
    ExceptionContext,
    ExceptionStrategy,
    exception_context,
    handle_api_exceptions,
    handle_database_exceptions,
    handle_exceptions,
    handle_external_service_exceptions,
    handle_file_exceptions,
    handle_lifecycle_exceptions,
    handle_parsing_exceptions,
)
try:
    # Re-export common exception types for compatibility with tests
    from dotmac_shared.core.exceptions import (
        ValidationError,
        BusinessRuleError as BusinessLogicError,
    )
except Exception:  # pragma: no cover - optional in minimal envs
    ValidationError = type("ValidationError", (Exception,), {})  # type: ignore
    BusinessLogicError = type("BusinessLogicError", (Exception,), {})  # type: ignore

__all__ = [
    "ExceptionStrategy",
    "ExceptionContext",
    "handle_exceptions",
    "handle_lifecycle_exceptions",
    "handle_api_exceptions",
    "handle_database_exceptions",
    "handle_file_exceptions",
    "handle_external_service_exceptions",
    "handle_parsing_exceptions",
    "exception_context",
    # Common exception re-exports
    "ValidationError",
    "BusinessLogicError",
]
