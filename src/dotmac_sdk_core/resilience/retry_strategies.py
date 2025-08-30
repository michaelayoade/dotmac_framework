"""
Retry Strategies for HTTP Client

Provides various retry strategies with configurable backoff algorithms
for resilient HTTP communication.
"""

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RetryContext:
    """Context information for retry attempts."""

    attempt: int
    total_attempts: int
    last_exception: Optional[Exception] = None
    last_response_code: Optional[int] = None
    elapsed_time: float = 0.0


class RetryStrategy(ABC):
    """Abstract base class for retry strategies."""

    @abstractmethod
    def should_retry(self, context: RetryContext) -> bool:
        """
        Determine if operation should be retried.

        Args:
            context: Retry context information

        Returns:
            True if should retry, False otherwise
        """
        pass

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """
        Get delay in seconds before next retry attempt.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        pass

    def get_max_attempts(self) -> int:
        """Get maximum number of retry attempts."""
        return getattr(self, "max_attempts", 3)


class ExponentialBackoffStrategy(RetryStrategy):
    """
    Exponential backoff retry strategy.

    Delay increases exponentially with each attempt:
    delay = base_delay * (multiplier ^ attempt) + random jitter
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        retryable_status_codes: Optional[List[int]] = None,
    ):
        """
        Initialize exponential backoff strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            multiplier: Backoff multiplier for each attempt
            max_delay: Maximum delay cap in seconds
            jitter: Whether to add random jitter
            jitter_range: Jitter range as fraction of delay (e.g., 0.1 = ±10%)
            retryable_status_codes: HTTP status codes that should trigger retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.multiplier = multiplier
        self.max_delay = max_delay
        self.jitter = jitter
        self.jitter_range = jitter_range
        self.retryable_status_codes = retryable_status_codes or [429, 502, 503, 504]

    def should_retry(self, context: RetryContext) -> bool:
        """Check if should retry based on context."""
        # Don't retry if max attempts reached
        if context.attempt >= self.max_attempts:
            return False

        # Check status code if available
        if context.last_response_code is not None:
            return context.last_response_code in self.retryable_status_codes

        # Check exception type
        if context.last_exception is not None:
            # Retry on network/timeout errors
            exception_name = type(context.last_exception).__name__
            retryable_exceptions = [
                "ConnectionError",
                "TimeoutError",
                "HTTPError",
                "ServerError",
            ]
            return any(exc in exception_name for exc in retryable_exceptions)

        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        # Base exponential delay
        delay = self.base_delay * (self.multiplier**attempt)

        # Apply maximum delay cap
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter_offset

        # Ensure minimum delay
        return max(0.1, delay)


class FixedDelayStrategy(RetryStrategy):
    """Fixed delay retry strategy with optional jitter."""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        jitter: bool = False,
        jitter_range: float = 0.1,
        retryable_status_codes: Optional[List[int]] = None,
    ):
        """
        Initialize fixed delay strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            delay: Fixed delay in seconds between attempts
            jitter: Whether to add random jitter
            jitter_range: Jitter range as fraction of delay
            retryable_status_codes: HTTP status codes that should trigger retry
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.jitter = jitter
        self.jitter_range = jitter_range
        self.retryable_status_codes = retryable_status_codes or [429, 502, 503, 504]

    def should_retry(self, context: RetryContext) -> bool:
        """Check if should retry based on context."""
        if context.attempt >= self.max_attempts:
            return False

        if context.last_response_code is not None:
            return context.last_response_code in self.retryable_status_codes

        return True

    def get_delay(self, attempt: int) -> float:
        """Get fixed delay with optional jitter."""
        delay = self.delay

        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter_offset

        return max(0.1, delay)


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        retryable_status_codes: Optional[List[int]] = None,
    ):
        """
        Initialize linear backoff strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            increment: Delay increment for each attempt
            max_delay: Maximum delay cap in seconds
            jitter: Whether to add random jitter
            jitter_range: Jitter range as fraction of delay
            retryable_status_codes: HTTP status codes that should trigger retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.increment = increment
        self.max_delay = max_delay
        self.jitter = jitter
        self.jitter_range = jitter_range
        self.retryable_status_codes = retryable_status_codes or [429, 502, 503, 504]

    def should_retry(self, context: RetryContext) -> bool:
        """Check if should retry based on context."""
        if context.attempt >= self.max_attempts:
            return False

        if context.last_response_code is not None:
            return context.last_response_code in self.retryable_status_codes

        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay."""
        # Linear increase: base + (increment * attempt)
        delay = self.base_delay + (self.increment * attempt)

        # Apply maximum delay cap
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter_offset = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter_offset

        return max(0.1, delay)


class CustomRetryStrategy(RetryStrategy):
    """
    Custom retry strategy with user-defined logic.

    Allows for complex retry logic based on response codes,
    exception types, elapsed time, etc.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        retry_condition: Optional[callable] = None,
        delay_calculator: Optional[callable] = None,
    ):
        """
        Initialize custom retry strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            retry_condition: Function that takes RetryContext and returns bool
            delay_calculator: Function that takes attempt number and returns delay
        """
        self.max_attempts = max_attempts
        self.retry_condition = retry_condition or self._default_retry_condition
        self.delay_calculator = delay_calculator or self._default_delay_calculator

    def should_retry(self, context: RetryContext) -> bool:
        """Use custom retry condition."""
        if context.attempt >= self.max_attempts:
            return False
        return self.retry_condition(context)

    def get_delay(self, attempt: int) -> float:
        """Use custom delay calculator."""
        return self.delay_calculator(attempt)

    def _default_retry_condition(self, context: RetryContext) -> bool:
        """Default retry condition for custom strategy."""
        retryable_codes = [429, 500, 502, 503, 504]
        if context.last_response_code is not None:
            return context.last_response_code in retryable_codes
        return True

    def _default_delay_calculator(self, attempt: int) -> float:
        """Default delay calculator (exponential backoff)."""
        return min(2.0**attempt, 60.0)


class AdaptiveRetryStrategy(RetryStrategy):
    """
    Adaptive retry strategy that adjusts based on observed patterns.

    Monitors success/failure rates and adapts retry behavior accordingly.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        success_threshold: float = 0.8,  # Reduce retries if success rate > 80%
        failure_threshold: float = 0.3,  # Increase retries if success rate < 30%
        adaptation_window: int = 100,  # Number of requests to consider
    ):
        """
        Initialize adaptive retry strategy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds
            success_threshold: Success rate above which to reduce retries
            failure_threshold: Success rate below which to increase retries
            adaptation_window: Number of recent requests to consider
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.success_threshold = success_threshold
        self.failure_threshold = failure_threshold
        self.adaptation_window = adaptation_window

        # Track recent outcomes
        self._recent_outcomes: List[bool] = []  # True = success, False = failure
        self._current_multiplier = 1.0

    def should_retry(self, context: RetryContext) -> bool:
        """Adaptive retry decision based on recent patterns."""
        if context.attempt >= self._get_adapted_max_attempts():
            return False

        # Standard retry conditions
        if context.last_response_code is not None:
            return context.last_response_code in [429, 502, 503, 504]

        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate adaptive delay based on recent success patterns."""
        base_delay = self.base_delay * (2.0**attempt) * self._current_multiplier

        # Add jitter
        jitter = random.uniform(0.8, 1.2)
        delay = base_delay * jitter

        return min(delay, 120.0)  # Cap at 2 minutes

    def record_outcome(self, success: bool):
        """Record request outcome for adaptation."""
        self._recent_outcomes.append(success)

        # Keep only recent outcomes
        if len(self._recent_outcomes) > self.adaptation_window:
            self._recent_outcomes.pop(0)

        # Update multiplier based on success rate
        if len(self._recent_outcomes) >= 10:  # Need minimum sample size
            success_rate = sum(self._recent_outcomes) / len(self._recent_outcomes)

            if success_rate > self.success_threshold:
                # High success rate - be less aggressive with retries
                self._current_multiplier = max(0.5, self._current_multiplier * 0.9)
            elif success_rate < self.failure_threshold:
                # Low success rate - be more aggressive with retries
                self._current_multiplier = min(2.0, self._current_multiplier * 1.1)

    def _get_adapted_max_attempts(self) -> int:
        """Get adapted max attempts based on recent patterns."""
        if len(self._recent_outcomes) < 10:
            return self.max_attempts

        success_rate = sum(self._recent_outcomes) / len(self._recent_outcomes)

        if success_rate > self.success_threshold:
            return max(2, self.max_attempts - 1)
        elif success_rate < self.failure_threshold:
            return min(8, self.max_attempts + 2)

        return self.max_attempts

    def get_stats(self) -> dict:
        """Get adaptation statistics."""
        if not self._recent_outcomes:
            return {
                "success_rate": 0.0,
                "current_multiplier": self._current_multiplier,
                "sample_size": 0,
                "adapted_max_attempts": self.max_attempts,
            }

        return {
            "success_rate": sum(self._recent_outcomes) / len(self._recent_outcomes),
            "current_multiplier": self._current_multiplier,
            "sample_size": len(self._recent_outcomes),
            "adapted_max_attempts": self._get_adapted_max_attempts(),
        }
