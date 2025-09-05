"""
Retry policies and decorators for database operations.
"""

import asyncio
import functools
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, overload

from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    TimeoutError,
)

from ...exceptions import DatabaseError, TransactionError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Retry strategy enumeration."""

    FIXED = "fixed"  # Fixed delay between retries
    LINEAR = "linear"  # Linear backoff (delay * attempt)
    EXPONENTIAL = "exponential"  # Exponential backoff (delay * 2^attempt)
    JITTERED = "jittered"  # Exponential with random jitter


@dataclass
class RetryPolicy:
    """
    Retry policy configuration for database operations.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter_ratio: float = 0.1
    retryable_exceptions: list[type[Exception]] = None

    def __post_init__(self):
        """Set default retryable exceptions if not provided."""
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [
                OperationalError,
                DisconnectionError,
                TimeoutError,
                ConnectionError,
                TransactionError,
            ]

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2**attempt)
        elif self.strategy == RetryStrategy.JITTERED:
            delay = self.base_delay * (2**attempt)
            jitter = delay * self.jitter_ratio * random.uniform(-1, 1)
            delay += jitter
        else:
            delay = self.base_delay

        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_attempts:
            return False

        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True

        return False


# Type overloads for sync and async functions
@overload
def with_retry(
    policy: RetryPolicy | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    ...


@overload
def with_retry(
    policy: RetryPolicy | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    ...


def with_retry(
    policy: RetryPolicy | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
) -> Callable[[Callable[..., T]], Callable[..., T]] | Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for adding retry logic to database operations.

    Args:
        policy: Retry policy configuration
        max_attempts: Maximum retry attempts (used if policy not provided)
        base_delay: Base delay between retries (used if policy not provided)
        strategy: Retry strategy (used if policy not provided)

    Returns:
        Decorated function with retry logic
    """
    if policy is None:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            strategy=strategy,
        )

    def decorator(
        func: Callable[..., T] | Callable[..., Awaitable[T]],
    ) -> Callable[..., T] | Callable[..., Awaitable[T]]:
        if asyncio.iscoroutinefunction(func):
            # func is Callable[..., Awaitable[T]]
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await _async_retry_operation(func, policy, *args, **kwargs)  # type: ignore

            return async_wrapper  # type: ignore
        else:
            # func is Callable[..., T]
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return _sync_retry_operation(func, policy, *args, **kwargs)  # type: ignore

            return sync_wrapper

    return decorator


def _sync_retry_operation(
    operation: Callable[..., T],
    policy: RetryPolicy,
    *args,
    **kwargs,
) -> T:
    """
    Execute synchronous operation with retry logic.

    Args:
        operation: Operation to execute
        policy: Retry policy
        *args: Operation arguments
        **kwargs: Operation keyword arguments

    Returns:
        Operation result

    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(policy.max_attempts):
        try:
            result = operation(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Operation succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e

            if not policy.should_retry(e, attempt):
                logger.error(f"Operation failed with non-retryable exception: {e}")
                raise

            if attempt == policy.max_attempts - 1:
                logger.error(f"Operation failed after {policy.max_attempts} attempts: {e}")
                raise

            delay = policy.calculate_delay(attempt)
            logger.warning(
                f"Operation failed (attempt {attempt + 1}/{policy.max_attempts}), "
                f"retrying in {delay:.2f}s: {e}"
            )
            time.sleep(delay)

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry operation completed without result or exception")


async def _async_retry_operation(
    operation: Callable[..., Awaitable[T]],
    policy: RetryPolicy,
    *args,
    **kwargs,
) -> T:
    """
    Execute asynchronous operation with retry logic.

    Args:
        operation: Async operation to execute
        policy: Retry policy
        *args: Operation arguments
        **kwargs: Operation keyword arguments

    Returns:
        Operation result

    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(policy.max_attempts):
        try:
            result = await operation(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Async operation succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e

            if not policy.should_retry(e, attempt):
                logger.error(f"Async operation failed with non-retryable exception: {e}")
                raise

            if attempt == policy.max_attempts - 1:
                logger.error(f"Async operation failed after {policy.max_attempts} attempts: {e}")
                raise

            delay = policy.calculate_delay(attempt)
            logger.warning(
                f"Async operation failed (attempt {attempt + 1}/{policy.max_attempts}), "
                f"retrying in {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Async retry operation completed without result or exception")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for database operations.

    Prevents cascading failures by temporarily stopping operations
    when failure rate exceeds threshold.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying again (seconds)
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "closed"  # closed, open, half-open

    def __call__(
        self, func: Callable[..., T] | Callable[..., Awaitable[T]]
    ) -> Callable[..., T] | Callable[..., Awaitable[T]]:
        """Decorator interface for circuit breaker."""
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await self._async_call(func, *args, **kwargs)  # type: ignore

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return self._sync_call(func, *args, **kwargs)  # type: ignore

            return sync_wrapper

    def _sync_call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection (sync)."""
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half-open"
            else:
                raise DatabaseError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    async def _async_call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection (async)."""
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half-open"
            else:
                raise DatabaseError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful operation."""
        self._failure_count = 0
        self._state = "closed"

    def _on_failure(self):
        """Handle failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count
