"""Retry mechanisms with configurable backoff strategies."""
from __future__ import annotations

import asyncio
import functools
import random
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any, TypeVar

from .observability.logging import TaskLogger
from .observability.metrics import get_global_metrics
from .types import TaskStatus

F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Failed after {attempts} attempts. Last error: {last_exception}"
        )


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """
    Calculate backoff delay for retry attempt.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Delay in seconds
    """
    delay = base_delay * (backoff_factor ** attempt)
    delay = min(delay, max_delay)

    if jitter:
        # Add up to 25% jitter
        jitter_amount = delay * 0.25
        delay += random.uniform(-jitter_amount, jitter_amount)
        delay = max(0, delay)  # Ensure non-negative

    return delay


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[AsyncF], AsyncF]:
    """
    Async retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback for retry events (attempt, exception)

    Returns:
        Decorated function

    Example:
        @retry_async(max_attempts=3, base_delay=1.0)
        async def flaky_function():
            # May fail and be retried up to 3 times
            pass
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = TaskLogger("retry")
            get_global_metrics()
            task_type = f"{func.__module__}.{func.__qualname__}"
            last_exception = None
            start_time = time.time()

            for attempt in range(max_attempts):
                attempt_start = time.time()

                try:
                    result = await func(*args, **kwargs)

                    # Log successful execution
                    duration_ms = (time.time() - start_time) * 1000
                    if attempt > 0:  # Only log if there were retries
                        logger.task_completed(
                            task_id=f"{task_type}:{id(args)}",
                            task_type=task_type,
                            duration_ms=duration_ms,
                            attempt=attempt + 1,
                            status=TaskStatus.SUCCESS
                        )

                    return result

                except exceptions as e:
                    last_exception = e
                    (time.time() - attempt_start) * 1000

                    # Log retry attempt
                    if attempt < max_attempts - 1:
                        delay = calculate_backoff(
                            attempt,
                            base_delay=base_delay,
                            backoff_factor=backoff_factor,
                            max_delay=max_delay,
                            jitter=jitter,
                        )

                        logger.task_retry(
                            task_id=f"{task_type}:{id(args)}",
                            task_type=task_type,
                            attempt=attempt + 1,
                            next_attempt_in_ms=delay * 1000,
                            error_type=type(e).__name__
                        )

                        # Call retry callback if provided
                        if on_retry:
                            with suppress(Exception):
                                on_retry(attempt + 1, e)

                        await asyncio.sleep(delay)
                    else:
                        # Final failure
                        total_duration = (time.time() - start_time) * 1000
                        logger.task_failed(
                            task_id=f"{task_type}:{id(args)}",
                            task_type=task_type,
                            duration_ms=total_duration,
                            attempt=attempt + 1,
                            error_type=type(e).__name__,
                            error_message=str(e),
                            will_retry=False
                        )
                        break

            # All attempts exhausted
            raise RetryError(max_attempts, last_exception)

        return wrapper
    return decorator


def retry_sync(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[F], F]:
    """
    Synchronous retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback for retry events (attempt, exception)

    Returns:
        Decorated function

    Example:
        @retry_sync(max_attempts=3, base_delay=1.0)
        def flaky_function():
            # May fail and be retried up to 3 times
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt failed, raise RetryError
                        break

                    # Call retry callback if provided
                    if on_retry:
                        with suppress(Exception):
                            on_retry(attempt + 1, e)

                    # Calculate and wait for backoff delay
                    delay = calculate_backoff(
                        attempt,
                        base_delay=base_delay,
                        backoff_factor=backoff_factor,
                        max_delay=max_delay,
                        jitter=jitter,
                    )

                    time.sleep(delay)

            # All attempts exhausted
            raise RetryError(max_attempts, last_exception)

        return wrapper
    return decorator


class AsyncRetryManager:
    """Context manager for async retry operations."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        exceptions: tuple[type[Exception], ...] = (Exception,),
        on_retry: Callable[[int, Exception], None] | None = None,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter
        self.exceptions = exceptions
        self.on_retry = on_retry
        self.attempt = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True  # Success, don't retry

        if not issubclass(exc_type, self.exceptions):
            return False  # Don't retry this exception type

        self.attempt += 1

        if self.attempt >= self.max_attempts:
            # Convert to RetryError but preserve original exception
            raise RetryError(self.max_attempts, exc_val) from exc_val

        # Call retry callback if provided
        if self.on_retry:
            with suppress(Exception):
                self.on_retry(self.attempt, exc_val)

        # Calculate and wait for backoff delay
        delay = calculate_backoff(
            self.attempt - 1,
            base_delay=self.base_delay,
            backoff_factor=self.backoff_factor,
            max_delay=self.max_delay,
            jitter=self.jitter,
        )

        await asyncio.sleep(delay)
        return True  # Suppress the exception and retry


async def retry_with_manager(operation: Callable[[], Awaitable[Any]], **kwargs: Any) -> Any:
    """
    Retry an async operation using AsyncRetryManager.

    Args:
        operation: Async callable to retry
        **kwargs: Arguments passed to AsyncRetryManager

    Returns:
        Result of successful operation

    Example:
        async def fetch_data():
            return await api_client.get("/data")

        result = await retry_with_manager(fetch_data, max_attempts=3)
    """
    manager = AsyncRetryManager(**kwargs)
    while True:
        async with manager:
            return await operation()
