"""
Retry execution strategies using Strategy and Template Method patterns.
Replaces the 19-complexity with_retry decorator with focused retry strategies.
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)


class RetryExecutor(ABC):
    """Base class for retry execution strategies."""
    
    def __init__(self, policy, on_retry: Optional[Callable] = None):
        """Initialize retry executor with policy and callback."""
        self.policy = policy
        self.on_retry = on_retry
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic using Template Method pattern.
        
        COMPLEXITY REDUCTION: This method uses template method pattern
        to eliminate duplicate retry logic (Complexity: 3).
        """
        last_exception = None
        
        # Step 1: Execute retry loop (Complexity: 1)
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return self._execute_function(func, *args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                # Check if we should continue retrying
                if not self._should_continue_retry(e, attempt):
                    raise
                
                # Handle retry delay and logging
                self._handle_retry_delay(attempt, e, func.__name__)
        
        # Step 2: Handle final failure (Complexity: 1)
        if last_exception:
            raise last_exception
    
    def _should_continue_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if we should continue retrying."""
        # Check retry policy
        if not self.policy.should_retry(exception=exception):
            return False
        
        # Check if exhausted attempts
        if attempt == self.policy.max_attempts:
            logger.error(
                f"Max retries ({self.policy.max_attempts}) exceeded"
            )
            return False
        
        return True
    
    def _handle_retry_delay(self, attempt: int, exception: Exception, func_name: str) -> None:
        """Handle retry delay and logging."""
        # Calculate delay
        delay = self.policy.calculate_delay(attempt)
        
        # Handle rate limit with retry-after
        if hasattr(exception, 'retry_after') and exception.retry_after:
            delay = max(delay, exception.retry_after)
        
        logger.warning(
            f"Retry {attempt}/{self.policy.max_attempts} for {func_name} "
            f"after {delay:.2f}s due to: {exception}"
        )
        
        # Call retry callback if provided
        if self.on_retry:
            self.on_retry(attempt, delay, exception)
        
        # Execute delay
        self._delay(delay)
    
    @abstractmethod
    def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the function - implemented by subclasses."""
        pass
    
    @abstractmethod
    def _delay(self, seconds: float) -> None:
        """Execute delay - implemented by subclasses."""
        pass


class AsyncRetryExecutor(RetryExecutor):
    """Retry executor for async functions."""
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic."""
        last_exception = None
        
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return await self._execute_function(func, *args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if not self._should_continue_retry(e, attempt):
                    raise
                
                await self._handle_retry_delay_async(attempt, e, func.__name__)
        
        if last_exception:
            raise last_exception
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function."""
        return await func(*args, **kwargs)
    
    def _delay(self, seconds: float) -> None:
        """This should not be called for async executor."""
        raise NotImplementedError("Use _delay_async for async executor")
    
    async def _delay_async(self, seconds: float) -> None:
        """Execute async delay."""
        await asyncio.sleep(seconds)
    
    async def _handle_retry_delay_async(self, attempt: int, exception: Exception, func_name: str) -> None:
        """Handle retry delay and logging for async execution."""
        # Calculate delay
        delay = self.policy.calculate_delay(attempt)
        
        # Handle rate limit with retry-after
        if hasattr(exception, 'retry_after') and exception.retry_after:
            delay = max(delay, exception.retry_after)
        
        logger.warning(
            f"Retry {attempt}/{self.policy.max_attempts} for {func_name} "
            f"after {delay:.2f}s due to: {exception}"
        )
        
        # Call retry callback if provided
        if self.on_retry:
            self.on_retry(attempt, delay, exception)
        
        # Execute async delay
        await self._delay_async(delay)


class SyncRetryExecutor(RetryExecutor):
    """Retry executor for synchronous functions."""
    
    def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute synchronous function."""
        return func(*args, **kwargs)
    
    def _delay(self, seconds: float) -> None:
        """Execute synchronous delay."""
        time.sleep(seconds)


class RetryDecoratorFactory:
    """
    Factory for creating retry decorators using Strategy pattern.
    
    REFACTORED: Replaces 19-complexity with_retry decorator with 
    focused retry strategies (Complexity: 2).
    """
    
    @staticmethod
    def create_retry_decorator(policy=None, on_retry: Optional[Callable] = None):
        """
        Create retry decorator using appropriate strategy.
        
        COMPLEXITY REDUCTION: This method replaces the original 19-complexity 
        decorator with strategy selection (Complexity: 2).
        
        Args:
            policy: Retry policy to use
            on_retry: Optional callback called on each retry
            
        Returns:
            Configured retry decorator
        """
        if policy is None:
            from . import RetryPolicy  # Import here to avoid circular deps
            policy = RetryPolicy()
        
        def decorator(func):
            """Decorator operation."""
            # Step 1: Select appropriate retry strategy (Complexity: 1)
            if asyncio.iscoroutinefunction(func):
                executor = AsyncRetryExecutor(policy, on_retry)
                
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    """Async Wrapper operation."""
                    return await executor.execute_with_retry(func, *args, **kwargs)
                
                return async_wrapper
            else:
                executor = SyncRetryExecutor(policy, on_retry)
                
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    """Sync Wrapper operation."""
                    return executor.execute_with_retry(func, *args, **kwargs)
                
                return sync_wrapper
        
        # Step 2: Return configured decorator (Complexity: 1)
        return decorator


class CircuitBreakerRetryExecutor(RetryExecutor):
    """Advanced retry executor with circuit breaker pattern."""
    
    def __init__(self, policy, on_retry: Optional[Callable] = None, 
                 failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """Initialize with circuit breaker parameters."""
        super().__init__(policy, on_retry)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.circuit_open = False
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with circuit breaker logic."""
        # Check circuit breaker state
        if self._is_circuit_open():
            raise Exception("Circuit breaker is open - too many failures")
        
        try:
            result = super().execute_with_retry(func, *args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self.circuit_open:
            return False
        
        # Check if recovery timeout has passed
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.circuit_open = False
            self.failure_count = 0
            logger.info("Circuit breaker reset - attempting recovery")
            return False
        
        return True
    
    def _record_success(self) -> None:
        """Record successful execution."""
        self.failure_count = 0
        self.circuit_open = False
    
    def _record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute synchronous function."""
        return func(*args, **kwargs)
    
    def _delay(self, seconds: float) -> None:
        """Execute synchronous delay."""
        time.sleep(seconds)


class BulkheadRetryExecutor(RetryExecutor):
    """Retry executor with bulkhead isolation pattern."""
    
    def __init__(self, policy, on_retry: Optional[Callable] = None, 
                 max_concurrent: int = 10):
        """Initialize with bulkhead parameters."""
        super().__init__(policy, on_retry)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with bulkhead isolation."""
        async with self.semaphore:
            return await super().execute_with_retry(func, *args, **kwargs)
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function."""
        return await func(*args, **kwargs)
    
    def _delay(self, seconds: float) -> None:
        """Not used for async executor."""
        raise NotImplementedError("Use async delay")
    
    async def _delay_async(self, seconds: float) -> None:
        """Execute async delay."""
        await asyncio.sleep(seconds)


def with_retry(policy=None, on_retry: Optional[Callable] = None):
    """
    Retry decorator using Strategy pattern.
    
    REFACTORED: Replaces 19-complexity decorator with strategy pattern.
    Now has 2 complexity instead of 19.
    
    Args:
        policy: Retry policy to use
        on_retry: Optional callback called on each retry
        
    Returns:
        Configured retry decorator
    """
    return RetryDecoratorFactory.create_retry_decorator(policy, on_retry)


def with_circuit_breaker_retry(policy=None, on_retry: Optional[Callable] = None,
                              failure_threshold: int = 5, recovery_timeout: float = 60.0):
    """
    Retry decorator with circuit breaker pattern.
    
    Args:
        policy: Retry policy to use
        on_retry: Optional callback called on each retry
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time before attempting recovery
        
    Returns:
        Configured retry decorator with circuit breaker
    """
    if policy is None:
        from . import RetryPolicy
        policy = RetryPolicy()
    
    def decorator(func):
        """Decorator operation."""
        executor = CircuitBreakerRetryExecutor(
            policy, on_retry, failure_threshold, recovery_timeout
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper operation."""
            return executor.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


def with_bulkhead_retry(policy=None, on_retry: Optional[Callable] = None,
                       max_concurrent: int = 10):
    """
    Async retry decorator with bulkhead isolation.
    
    Args:
        policy: Retry policy to use
        on_retry: Optional callback called on each retry
        max_concurrent: Maximum concurrent executions
        
    Returns:
        Configured async retry decorator with bulkhead
    """
    if policy is None:
        from . import RetryPolicy
        policy = RetryPolicy()
    
    def decorator(func):
        """Decorator operation."""
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Bulkhead retry only supports async functions")
        
        executor = BulkheadRetryExecutor(policy, on_retry, max_concurrent)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            """Wrapper operation."""
            return await executor.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator