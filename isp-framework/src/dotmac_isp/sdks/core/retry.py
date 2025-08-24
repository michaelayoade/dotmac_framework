"""
Retry policies and decorators for SDK operations.
"""

from typing import Callable, Any, Optional, Union, List, Type
from functools import wraps
import asyncio
import time
import random
import logging
from dataclasses import dataclass

from .exceptions import SDKError, SDKRateLimitError, SDKTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[Type[Exception]] = None
    retryable_status_codes: List[int] = None

    def __post_init__(self):
        """  Post Init   operation."""
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [
                SDKTimeoutError,
                SDKRateLimitError,
                ConnectionError,
                TimeoutError,
            ]

        if self.retryable_status_codes is None:
            self.retryable_status_codes = [429, 502, 503, 504]

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.initial_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay,
        )

        if self.jitter:
            # Add random jitter (0-25% of delay)
            delay = delay * (1 + random.random() * 0.25)

        return delay

    def should_retry(
        self, exception: Optional[Exception] = None, status_code: Optional[int] = None
    ) -> bool:
        """
        Determine if operation should be retried.

        Args:
            exception: Exception that occurred
            status_code: HTTP status code

        Returns:
            True if should retry, False otherwise
        """
        if exception:
            # Check if exception type is retryable
            for exc_type in self.retryable_exceptions:
                if isinstance(exception, exc_type):
                    return True

            # Check for rate limit error with retry-after header
            if isinstance(exception, SDKRateLimitError):
                return True

        if status_code and status_code in self.retryable_status_codes:
            return True

        return False


def with_retry(
    policy: Optional[RetryPolicy] = None, on_retry: Optional[Callable] = None
):
    """
    Decorator to add retry logic to functions.
    
    REFACTORED: Replaced 19-complexity decorator with Strategy pattern.
    Now uses RetryExecutor strategies for clean separation (Complexity: 2).

    Args:
        policy: Retry policy to use
        on_retry: Optional callback called on each retry
    """
    # Import here to avoid circular dependencies
    from .retry_strategies import RetryDecoratorFactory
    
    # Use strategy pattern for retry execution (Complexity: 1)
    return RetryDecoratorFactory.create_retry_decorator(policy, on_retry)


class CircuitBreaker:
    """
    Circuit breaker pattern for SDK operations.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception types to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            SDKError: If circuit is open
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise SDKError(
                    f"Circuit breaker is open. Service unavailable for "
                    f"{self.recovery_timeout - (time.time() - self.last_failure_time):.1f}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call async function through circuit breaker.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            SDKError: If circuit is open
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise SDKError(
                    f"Circuit breaker is open. Service unavailable for "
                    f"{self.recovery_timeout - (time.time() - self.last_failure_time):.1f}s"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        return (
            self.last_failure_time
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")

    def reset(self):
        """Manually reset circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"
        logger.info("Circuit breaker manually reset")

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == "open"

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == "closed"


# For backward compatibility
RetryClient = CircuitBreaker
