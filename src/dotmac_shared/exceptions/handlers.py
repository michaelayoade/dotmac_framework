"""
DRY Exception Handling Patterns for DotMac Framework
Replaces broad Exception catching with specific, reusable patterns
"""

import asyncio
import functools
import logging
from contextlib import contextmanager
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ExceptionStrategy(Enum):
    """Strategy for handling different types of exceptions"""

    LOG_AND_RERAISE = "log_and_reraise"
    LOG_AND_CONTINUE = "log_and_continue"
    LOG_AND_RETURN_DEFAULT = "log_and_return_default"
    LOG_AND_RETURN_NONE = "log_and_return_none"
    SILENT_CONTINUE = "silent_continue"


class ExceptionContext:
    """Context for exception handling with specific error types"""

    # Common exception mappings for different domains
    LIFECYCLE_EXCEPTIONS = (
        ImportError,
        AttributeError,
        ValueError,
        TypeError,
        ConnectionError,
        TimeoutError,
        ModuleNotFoundError,
    )

    API_EXCEPTIONS = (ConnectionError, TimeoutError, ValueError, KeyError, AttributeError, TypeError)

    DATABASE_EXCEPTIONS = (ConnectionError, TimeoutError, ValueError, AttributeError, TypeError, KeyError)

    FILE_EXCEPTIONS = (
        FileNotFoundError,
        PermissionError,
        OSError,
        IOError,
        ValueError,
        UnicodeDecodeError,
        IsADirectoryError,
    )

    EXTERNAL_SERVICE_EXCEPTIONS = (ConnectionError, TimeoutError, ValueError, KeyError, AttributeError, OSError)

    PARSING_EXCEPTIONS = (ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError)


def handle_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RERAISE,
    exceptions: tuple = ExceptionContext.LIFECYCLE_EXCEPTIONS,
    context: str = "",
    default_return: Any = None,
    logger_name: Optional[str] = None,
):
    """
    DRY decorator for exception handling

    Args:
        strategy: How to handle the exception
        exceptions: Specific exceptions to catch (instead of broad Exception)
        context: Context description for logging
        default_return: Value to return if using LOG_AND_RETURN_DEFAULT
        logger_name: Specific logger to use

    Example:
        @handle_exceptions(
            strategy=ExceptionStrategy.LOG_AND_CONTINUE,
            exceptions=(ValueError, TypeError),
            context="User input validation"
        )
        def validate_input(self, data):
            # Your code here
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            exc_logger = logging.getLogger(logger_name or func.__module__)
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                return _handle_exception(e, func.__name__, strategy, context, default_return, exc_logger)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            exc_logger = logging.getLogger(logger_name or func.__module__)
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                return _handle_exception(e, func.__name__, strategy, context, default_return, exc_logger)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def _handle_exception(
    e: Exception, func_name: str, strategy: ExceptionStrategy, context: str, default_return: Any, logger: logging.Logger
) -> Any:
    """Internal exception handling logic"""

    error_msg = (
        f"{context} in {func_name}: {type(e).__name__}: {e}"
        if context
        else f"{func_name} failed: {type(e).__name__}: {e}"
    )

    if strategy == ExceptionStrategy.LOG_AND_RERAISE:
        logger.error(error_msg)
        raise
    elif strategy == ExceptionStrategy.LOG_AND_CONTINUE:
        logger.warning(error_msg)
        return None
    elif strategy == ExceptionStrategy.LOG_AND_RETURN_DEFAULT:
        logger.warning(error_msg)
        return default_return
    elif strategy == ExceptionStrategy.LOG_AND_RETURN_NONE:
        logger.warning(error_msg)
        return None
    elif strategy == ExceptionStrategy.SILENT_CONTINUE:
        logger.debug(error_msg)
        return None


@contextmanager
def exception_context(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RERAISE,
    exceptions: tuple = ExceptionContext.LIFECYCLE_EXCEPTIONS,
    context: str = "",
    default_return: Any = None,
):
    """Context manager for exception handling"""
    try:
        yield
    except exceptions as e:
        _handle_exception(e, context, strategy, context, default_return, logger)


# Specific domain decorators for common patterns


def handle_lifecycle_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_CONTINUE, context: str = "Lifecycle operation"
):
    """Handle lifecycle/startup/shutdown exceptions"""
    return handle_exceptions(strategy=strategy, exceptions=ExceptionContext.LIFECYCLE_EXCEPTIONS, context=context)


def handle_api_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RERAISE, context: str = "API operation"
):
    """Handle API-related exceptions"""
    return handle_exceptions(strategy=strategy, exceptions=ExceptionContext.API_EXCEPTIONS, context=context)


def handle_database_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RERAISE, context: str = "Database operation"
):
    """Handle database-related exceptions"""
    return handle_exceptions(strategy=strategy, exceptions=ExceptionContext.DATABASE_EXCEPTIONS, context=context)


def handle_file_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RETURN_NONE, context: str = "File operation"
):
    """Handle file operation exceptions"""
    return handle_exceptions(strategy=strategy, exceptions=ExceptionContext.FILE_EXCEPTIONS, context=context)


def handle_external_service_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RETURN_DEFAULT,
    context: str = "External service call",
    default_return: Any = None,
):
    """Handle external service exceptions"""
    return handle_exceptions(
        strategy=strategy,
        exceptions=ExceptionContext.EXTERNAL_SERVICE_EXCEPTIONS,
        context=context,
        default_return=default_return,
    )


def handle_parsing_exceptions(
    strategy: ExceptionStrategy = ExceptionStrategy.LOG_AND_RETURN_DEFAULT,
    context: str = "Data parsing",
    default_return: Any = None,
):
    """Handle data parsing exceptions"""
    return handle_exceptions(
        strategy=strategy,
        exceptions=ExceptionContext.PARSING_EXCEPTIONS,
        context=context,
        default_return=default_return,
    )
