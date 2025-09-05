"""
Decorators for Performance Benchmarking

Provides exception handling and other decorators for the benchmarking suite.
"""

import functools
import logging
import traceback
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def standard_exception_handler(default_return: Any = None, log_errors: bool = True, reraise: bool = False) -> Callable:
    """
    Standard exception handler decorator for benchmarking functions.

    Args:
        default_return: Default value to return on exception
        log_errors: Whether to log exceptions
        reraise: Whether to reraise the exception after handling

    Returns:
        Decorated function with exception handling
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Exception in {func.__name__}: {str(e)}\n" f"Traceback: {traceback.format_exc()}")

                if reraise:
                    raise

                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Exception in {func.__name__}: {str(e)}\n" f"Traceback: {traceback.format_exc()}")

                if reraise:
                    raise

                return default_return

        # Return appropriate wrapper based on whether the function is async
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
