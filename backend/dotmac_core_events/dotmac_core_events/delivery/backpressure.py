"""
Back-pressure control with circuit breaker and retry policies.
"""

import asyncio
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class BackpressureStrategy(str, Enum):
    """Back-pressure strategies."""

    DROP = "drop"          # Drop new requests
    QUEUE = "queue"        # Queue with limits
    THROTTLE = "throttle"  # Rate limit
    CIRCUIT_BREAK = "circuit_break"  # Circuit breaker


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 30000
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if attempt <= 0:
            return 0

        # Exponential backoff
        delay_ms = min(
            self.base_delay_ms * (self.exponential_base ** (attempt - 1)),
            self.max_delay_ms
        )

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay_ms * self.jitter_factor
            jitter_offset = (secrets.randbelow(2001) - 1000) / 1000 * jitter_range
            delay_ms += jitter_offset

        return max(0, delay_ms / 1000.0)  # Convert to seconds


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout_ms: int = 60000
    success_threshold: int = 3
    timeout_ms: int = 5000

    # DLQ spike detection
    dlq_spike_threshold: int = 10
    dlq_spike_window_ms: int = 60000


class CircuitBreaker:
    """Circuit breaker for back-pressure control."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.dlq_events: List[datetime] = []
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if not await self._can_execute():
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            start_time = time.time()

            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout_ms / 1000.0
            )

            # Record success
            await self._record_success()
            return result

        except asyncio.TimeoutError:
            await self._record_failure()
            raise CircuitBreakerTimeoutError("Operation timed out")
        except Exception:
            await self._record_failure()
            raise

    async def _can_execute(self) -> bool:
        """Check if execution is allowed."""
        now = datetime.now(timezone.utc)

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and
                (now - self.last_failure_time).total_seconds() * 1000 >= self.config.recovery_timeout_ms):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to half-open")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    async def _record_success(self):
        """Record successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker closed after recovery")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    async def _record_failure(self):
        """Record failed execution."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            self.failure_count += 1
            self.last_failure_time = now

            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        "Circuit breaker opened due to failures",
                        failure_count=self.failure_count,
                        threshold=self.config.failure_threshold
                    )
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker reopened after failed recovery attempt")

    async def record_dlq_event(self):
        """Record DLQ event for spike detection."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            self.dlq_events.append(now)

            # Clean old events outside window
            window_start = now - timedelta(milliseconds=self.config.dlq_spike_window_ms)
            self.dlq_events = [event for event in self.dlq_events if event >= window_start]

            # Check for spike
            if len(self.dlq_events) >= self.config.dlq_spike_threshold:
                if self.state == CircuitState.CLOSED:
                    self.state = CircuitState.OPEN
                    self.last_failure_time = now
                    logger.warning(
                        "Circuit breaker opened due to DLQ spike",
                        dlq_events=len(self.dlq_events),
                        threshold=self.config.dlq_spike_threshold
                    )

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "dlq_events_count": len(self.dlq_events)
        }


class BackpressureController:
    """Back-pressure controller with multiple strategies."""

    def __init__(
        self,
        max_in_flight: int = 100,
        queue_size_limit: int = 1000,
        strategy: BackpressureStrategy = BackpressureStrategy.QUEUE
    ):
        self.max_in_flight = max_in_flight
        self.queue_size_limit = queue_size_limit
        self.strategy = strategy
        self.in_flight_count = 0
        self.queue_size = 0
        self.dropped_count = 0
        self.throttled_count = 0
        self._semaphore = asyncio.Semaphore(max_in_flight)
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Acquire permission to process request.

        Returns:
            True if permission granted, False if back-pressure applied
        """
        async with self._lock:
            if self.strategy == BackpressureStrategy.DROP:
                if self.in_flight_count >= self.max_in_flight:
                    self.dropped_count += 1
                    logger.debug("Request dropped due to back-pressure")
                    return False

            elif self.strategy == BackpressureStrategy.QUEUE:
                if self.queue_size >= self.queue_size_limit:
                    self.dropped_count += 1
                    logger.debug("Request dropped due to queue limit")
                    return False
                self.queue_size += 1

            elif self.strategy == BackpressureStrategy.THROTTLE:
                if self.in_flight_count >= self.max_in_flight:
                    self.throttled_count += 1
                    # Apply throttling delay
                    delay = min(0.1 * (self.in_flight_count - self.max_in_flight), 5.0)
                    await asyncio.sleep(delay)

        # Acquire semaphore for in-flight tracking
        await self._semaphore.acquire()

        async with self._lock:
            self.in_flight_count += 1
            if self.strategy == BackpressureStrategy.QUEUE:
                self.queue_size -= 1

        return True

    async def release(self):
        """Release processing permission."""
        async with self._lock:
            self.in_flight_count -= 1

        self._semaphore.release()

    def get_stats(self) -> Dict[str, Any]:
        """Get back-pressure statistics."""
        return {
            "strategy": self.strategy.value,
            "max_in_flight": self.max_in_flight,
            "in_flight_count": self.in_flight_count,
            "queue_size": self.queue_size,
            "queue_size_limit": self.queue_size_limit,
            "dropped_count": self.dropped_count,
            "throttled_count": self.throttled_count
        }


class RetryableOperation:
    """Wrapper for retryable operations."""

    def __init__(self, retry_policy: RetryPolicy):
        self.retry_policy = retry_policy

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)

                if attempt > 1:
                    logger.info(
                        "Operation succeeded after retry",
                        attempt=attempt,
                        total_attempts=self.retry_policy.max_attempts
                    )

                return result

            except Exception as e:
                last_exception = e

                if attempt == self.retry_policy.max_attempts:
                    logger.error(
                        "Operation failed after all retry attempts",
                        attempt=attempt,
                        total_attempts=self.retry_policy.max_attempts,
                        error=str(e)
                    )
                    break

                # Calculate delay for next attempt
                delay = self.retry_policy.calculate_delay(attempt)

                logger.warning(
                    "Operation failed, retrying",
                    attempt=attempt,
                    total_attempts=self.retry_policy.max_attempts,
                    delay_seconds=delay,
                    error=str(e)
                )

                if delay > 0:
                    await asyncio.sleep(delay)

        # Re-raise the last exception
        if last_exception:
            raise last_exception


class BackpressureMiddleware:
    """Middleware for back-pressure control."""

    def __init__(
        self,
        controller: BackpressureController,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_policy: Optional[RetryPolicy] = None
    ):
        self.controller = controller
        self.circuit_breaker = circuit_breaker
        self.retry_operation = RetryableOperation(retry_policy) if retry_policy else None

    async def __call__(self, envelope, handler, next_middleware):
        """Apply back-pressure control to event processing."""
        # Check circuit breaker
        if self.circuit_breaker:
            if self.circuit_breaker.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        # Apply back-pressure
        if not await self.controller.acquire():
            raise BackpressureError("Request rejected due to back-pressure")

        try:
            if self.retry_operation and self.circuit_breaker:
                # Execute with both retry and circuit breaker
                async def protected_handler():
                    return await self.circuit_breaker.call(next_middleware, envelope, handler)

                result = await self.retry_operation.execute(protected_handler)

            elif self.circuit_breaker:
                # Execute with circuit breaker only
                result = await self.circuit_breaker.call(next_middleware, envelope, handler)

            elif self.retry_operation:
                # Execute with retry only
                result = await self.retry_operation.execute(next_middleware, envelope, handler)

            else:
                # Execute without protection
                result = await next_middleware(envelope, handler)

            return result

        finally:
            await self.controller.release()


# Custom exceptions
class CircuitBreakerError(Exception):
    """Base circuit breaker exception."""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Circuit breaker is open."""
    pass


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Operation timed out."""
    pass


class BackpressureError(Exception):
    """Back-pressure applied."""
    pass


# Factory functions
def create_conservative_backpressure() -> BackpressureController:
    """Create conservative back-pressure controller."""
    return BackpressureController(
        max_in_flight=50,
        queue_size_limit=500,
        strategy=BackpressureStrategy.QUEUE
    )


def create_aggressive_backpressure() -> BackpressureController:
    """Create aggressive back-pressure controller."""
    return BackpressureController(
        max_in_flight=20,
        queue_size_limit=100,
        strategy=BackpressureStrategy.DROP
    )


def create_default_circuit_breaker() -> CircuitBreaker:
    """Create default circuit breaker."""
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout_ms=60000,
        success_threshold=3,
        timeout_ms=5000,
        dlq_spike_threshold=10,
        dlq_spike_window_ms=60000
    )
    return CircuitBreaker(config)


def create_default_retry_policy() -> RetryPolicy:
    """Create default retry policy."""
    return RetryPolicy(
        max_attempts=3,
        base_delay_ms=100,
        max_delay_ms=30000,
        exponential_base=2.0,
        jitter=True,
        jitter_factor=0.1
    )


def create_production_backpressure_middleware() -> BackpressureMiddleware:
    """Create production-ready back-pressure middleware."""
    controller = BackpressureController(
        max_in_flight=100,
        queue_size_limit=1000,
        strategy=BackpressureStrategy.QUEUE
    )

    circuit_breaker = create_default_circuit_breaker()
    retry_policy = create_default_retry_policy()

    return BackpressureMiddleware(
        controller=controller,
        circuit_breaker=circuit_breaker,
        retry_policy=retry_policy
    )
