"""
Circuit Breaker Pattern Implementation

Provides resilient HTTP client communication by monitoring failures and
temporarily stopping requests when a service is unhealthy to prevent
cascade failures.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str, state: CircuitBreakerState):
        super().__init__(message)
        self.state = state


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""

    state: CircuitBreakerState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    total_requests: int
    blocked_requests: int


class CircuitBreaker:
    """
    Circuit breaker implementation for HTTP clients.

    Monitors request failures and transitions between states:
    - CLOSED: Normal operation, requests proceed
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        success_threshold: int = 2,
        timeout_duration: float = 30.0,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that counts as failure
            success_threshold: Successes needed to close circuit from half-open
            timeout_duration: Maximum time to wait for operation
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.timeout_duration = timeout_duration

        # State tracking
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._total_requests = 0
        self._blocked_requests = 0

        # Thread safety for sync calls
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Current circuit breaker state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitBreakerState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitBreakerState.HALF_OPEN

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Call function through circuit breaker (async).

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
            Exception: From the wrapped function
        """
        async with self._lock:
            self._total_requests += 1

            # Check if we should allow the request
            if not await self._should_allow_request():
                self._blocked_requests += 1
                raise CircuitBreakerError(
                    f"Circuit breaker is {self._state.value}, request blocked",
                    self._state,
                )

        # Execute the function
        start_time = time.time()
        try:
            # Add timeout to prevent hanging
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.timeout_duration
            )

            await self._record_success()
            return result

        except asyncio.TimeoutError as e:
            await self._record_failure()
            raise self.expected_exception(
                f"Operation timed out after {self.timeout_duration}s"
            ) from e

        except Exception as e:
            if isinstance(e, self.expected_exception):
                await self._record_failure()
            raise

    def call_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Call function through circuit breaker (sync).

        Args:
            func: Sync function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
            Exception: From the wrapped function
        """
        self._total_requests += 1

        # Check if we should allow the request
        if not self._should_allow_request_sync():
            self._blocked_requests += 1
            raise CircuitBreakerError(
                f"Circuit breaker is {self._state.value}, request blocked", self._state
            )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success_sync()
            return result

        except Exception as e:
            if isinstance(e, self.expected_exception):
                self._record_failure_sync()
            raise

    async def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        if self._state == CircuitBreakerState.CLOSED:
            return True

        elif self._state == CircuitBreakerState.OPEN:
            # Check if enough time has passed to try recovery
            if self._last_failure_time is None:
                return False

            if time.time() - self._last_failure_time >= self.recovery_timeout:
                await self._transition_to_half_open()
                return True
            return False

        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True

        return False

    def _should_allow_request_sync(self) -> bool:
        """Sync version of request allowance check."""
        if self._state == CircuitBreakerState.CLOSED:
            return True

        elif self._state == CircuitBreakerState.OPEN:
            # Check if enough time has passed to try recovery
            if self._last_failure_time is None:
                return False

            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._transition_to_half_open_sync()
                return True
            return False

        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True

        return False

    async def _record_success(self):
        """Record successful request."""
        async with self._lock:
            self._success_count += 1
            self._last_success_time = time.time()

            logger.debug(
                f"Circuit breaker success recorded. Count: {self._success_count}"
            )

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._success_count >= self.success_threshold:
                    await self._transition_to_closed()

    def _record_success_sync(self):
        """Sync version of success recording."""
        self._success_count += 1
        self._last_success_time = time.time()

        logger.debug(f"Circuit breaker success recorded. Count: {self._success_count}")

        if self._state == CircuitBreakerState.HALF_OPEN:
            if self._success_count >= self.success_threshold:
                self._transition_to_closed_sync()

    async def _record_failure(self):
        """Record failed request."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            logger.warning(
                f"Circuit breaker failure recorded. Count: {self._failure_count}"
            )

            if self._state == CircuitBreakerState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    await self._transition_to_open()

            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open state reopens circuit
                await self._transition_to_open()

    def _record_failure_sync(self):
        """Sync version of failure recording."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker failure recorded. Count: {self._failure_count}"
        )

        if self._state == CircuitBreakerState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open_sync()

        elif self._state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open state reopens circuit
            self._transition_to_open_sync()

    async def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        self._state = CircuitBreakerState.OPEN
        self._success_count = 0
        logger.warning(
            f"Circuit breaker opened after {self._failure_count} failures. "
            f"Will retry after {self.recovery_timeout} seconds."
        )

    def _transition_to_open_sync(self):
        """Sync version of open transition."""
        self._state = CircuitBreakerState.OPEN
        self._success_count = 0
        logger.warning(
            f"Circuit breaker opened after {self._failure_count} failures. "
            f"Will retry after {self.recovery_timeout} seconds."
        )

    async def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        self._state = CircuitBreakerState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        logger.info("Circuit breaker transitioning to half-open state")

    def _transition_to_half_open_sync(self):
        """Sync version of half-open transition."""
        self._state = CircuitBreakerState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        logger.info("Circuit breaker transitioning to half-open state")

    async def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit breaker closed - service healthy")

    def _transition_to_closed_sync(self):
        """Sync version of closed transition."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit breaker closed - service healthy")

    def reset(self):
        """Reset circuit breaker to initial state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_success_time = None
        self._total_requests = 0
        self._blocked_requests = 0
        logger.info("Circuit breaker reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_requests": self._total_requests,
            "blocked_requests": self._blocked_requests,
            "failure_rate": self._failure_count / max(1, self._total_requests),
            "success_rate": self._success_count / max(1, self._total_requests),
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "success_threshold": self.success_threshold,
        }


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception,
):
    """
    Decorator for adding circuit breaker to functions.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that counts as failure
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call(func, *args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call_sync(func, *args, **kwargs)

            return sync_wrapper

    return decorator
