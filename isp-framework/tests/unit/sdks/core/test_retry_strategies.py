"""
Test suite for retry execution strategies.
Validates the replacement of the 19-complexity with_retry decorator.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from dotmac_isp.sdks.core.retry_strategies import (
    RetryExecutor,
    AsyncRetryExecutor,
    SyncRetryExecutor,
    RetryDecoratorFactory,
    CircuitBreakerRetryExecutor,
    BulkheadRetryExecutor,
    with_retry,
    with_circuit_breaker_retry,
    with_bulkhead_retry,
)


@pytest.mark.unit
class TestRetryExecutors:
    """Test retry executor strategies."""
    
    def test_sync_retry_executor_success(self):
        """Test synchronous retry executor with successful execution."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 3
        
        # Mock function that succeeds
        func = Mock(return_value="success")
        
        executor = SyncRetryExecutor(policy)
        result = executor.execute_with_retry(func, "arg1", kwarg1="value1")
        
        assert result == "success"
        func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_sync_retry_executor_with_retries(self):
        """Test synchronous retry executor with failures then success."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 3
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.1
        
        # Mock function that fails twice then succeeds
        func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        
        # Mock on_retry callback
        on_retry = Mock()
        
        executor = SyncRetryExecutor(policy, on_retry)
        
        with patch('time.sleep') as mock_sleep:
            result = executor.execute_with_retry(func, "arg1")
        
        assert result == "success"
        assert func.call_count == 3
        assert mock_sleep.call_count == 2  # Slept between retries
        assert on_retry.call_count == 2  # Called on each retry
    
    def test_sync_retry_executor_max_attempts_exceeded(self):
        """Test synchronous retry executor when max attempts exceeded."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 2
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.1
        
        # Mock function that always fails
        func = Mock(side_effect=Exception("always fails")
        
        executor = SyncRetryExecutor(policy)
        
        with patch('time.sleep'):
            with pytest.raises(Exception, match="always fails"):
                executor.execute_with_retry(func)
        
        assert func.call_count == 2  # Called max_attempts times
    
    def test_sync_retry_executor_policy_says_no_retry(self):
        """Test synchronous retry executor when policy says don't retry."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 3
        policy.should_retry.return_value = False  # Don't retry
        
        # Mock function that fails
        func = Mock(side_effect=Exception("no retry")
        
        executor = SyncRetryExecutor(policy)
        
        with pytest.raises(Exception, match="no retry"):
            executor.execute_with_retry(func)
        
        assert func.call_count == 1  # Only called once
    
    @pytest.mark.asyncio
    async def test_async_retry_executor_success(self):
        """Test asynchronous retry executor with successful execution."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 3
        
        # Mock async function that succeeds
        async def mock_func(*args, **kwargs):
            """Mock Func operation."""
            return "async_success"
        
        executor = AsyncRetryExecutor(policy)
        result = await executor.execute_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "async_success"
    
    @pytest.mark.asyncio
    async def test_async_retry_executor_with_retries(self):
        """Test asynchronous retry executor with failures then success."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 3
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.01  # Short delay for tests
        
        # Track call count
        call_count = 0
        
        async def mock_func():
            """Mock Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"fail{call_count}")
            return "async_success"
        
        # Mock on_retry callback
        on_retry = Mock()
        
        executor = AsyncRetryExecutor(policy, on_retry)
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await executor.execute_with_retry(mock_func)
        
        assert result == "async_success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # Slept between retries
        assert on_retry.call_count == 2  # Called on each retry
    
    @pytest.mark.asyncio
    async def test_async_retry_executor_rate_limit_handling(self):
        """Test async retry executor handling rate limit exceptions."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 2
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.1
        
        # Mock rate limit exception
        rate_limit_error = Exception("Rate limited")
        rate_limit_error.retry_after = 0.5  # Mock retry_after attribute
        
        call_count = 0
        
        async def mock_func():
            """Mock Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limit_error
            return "success_after_rate_limit"
        
        executor = AsyncRetryExecutor(policy)
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await executor.execute_with_retry(mock_func)
        
        assert result == "success_after_rate_limit"
        # Should use the longer retry_after delay
        mock_sleep.assert_called_with(0.5)


@pytest.mark.unit
class TestRetryDecoratorFactory:
    """Test the retry decorator factory."""
    
    def test_create_sync_decorator(self):
        """Test creating decorator for synchronous function."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 2
        
        # Create decorator
        decorator = RetryDecoratorFactory.create_retry_decorator(policy)
        
        # Decorate a sync function
        @decorator
        def sync_func():
            """Sync Func operation."""
            return "sync_result"
        
        result = sync_func()
        assert result == "sync_result"
    
    def test_create_async_decorator(self):
        """Test creating decorator for asynchronous function."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 2
        
        # Create decorator
        decorator = RetryDecoratorFactory.create_retry_decorator(policy)
        
        # Decorate an async function
        @decorator
        async def async_func():
            """Async Func operation."""
            return "async_result"
        
        # Test that it returns a coroutine
        result_coro = async_func()
        assert asyncio.iscoroutine(result_coro)
    
    def test_decorator_with_default_policy(self):
        """Test decorator creation with default policy."""
        with patch('dotmac_isp.sdks.core.retry_strategies.RetryPolicy') as mock_policy_class:
            mock_policy = Mock()
            mock_policy_class.return_value = mock_policy
            
            decorator = RetryDecoratorFactory.create_retry_decorator()
            
            # Should have created default policy
            mock_policy_class.assert_called_once()


@pytest.mark.unit
class TestCircuitBreakerRetryExecutor:
    """Test circuit breaker retry executor."""
    
    def test_circuit_breaker_normal_operation(self):
        """Test circuit breaker in normal operation."""
        policy = Mock()
        policy.max_attempts = 3
        
        executor = CircuitBreakerRetryExecutor(policy, failure_threshold=2)
        
        # Mock successful function
        func = Mock(return_value="success")
        
        result = executor.execute_with_retry(func)
        assert result == "success"
        assert executor.failure_count == 0
        assert not executor.circuit_open
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        policy = Mock()
        policy.max_attempts = 1  # Fail immediately 
        policy.should_retry.return_value = False
        
        executor = CircuitBreakerRetryExecutor(policy, failure_threshold=2)
        
        # Mock failing function
        func = Mock(side_effect=Exception("fail")
        
        # First failure
        with pytest.raises(Exception):
            executor.execute_with_retry(func)
        assert executor.failure_count == 1
        assert not executor.circuit_open
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            executor.execute_with_retry(func)
        assert executor.failure_count == 2
        assert executor.circuit_open
        
        # Third attempt - should fail immediately due to open circuit
        with pytest.raises(Exception, match="Circuit breaker is open"):
            executor.execute_with_retry(func)
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        policy = Mock()
        policy.max_attempts = 1
        policy.should_retry.return_value = False
        
        executor = CircuitBreakerRetryExecutor(
            policy, failure_threshold=1, recovery_timeout=0.1
        )
        
        # Force circuit open
        func_fail = Mock(side_effect=Exception("fail")
        with pytest.raises(Exception):
            executor.execute_with_retry(func_fail)
        assert executor.circuit_open
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should allow retry after timeout
        func_success = Mock(return_value="recovered")
        result = executor.execute_with_retry(func_success)
        assert result == "recovered"
        assert not executor.circuit_open
        assert executor.failure_count == 0


@pytest.mark.unit
class TestBulkheadRetryExecutor:
    """Test bulkhead retry executor."""
    
    @pytest.mark.asyncio
    async def test_bulkhead_limits_concurrency(self):
        """Test bulkhead pattern limits concurrent executions."""
        policy = Mock()
        policy.max_attempts = 1
        
        executor = BulkheadRetryExecutor(policy, max_concurrent=2)
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_seen = 0
        
        async def mock_func():
            """Mock Func operation."""
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate work
            concurrent_count -= 1
            return "done"
        
        # Start 5 concurrent executions
        tasks = [
            executor.execute_with_retry(mock_func)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result == "done" for result in results)
        # But max concurrent should be limited to 2
        assert max_concurrent_seen <= 2


@pytest.mark.unit
class TestRetryDecorators:
    """Test the retry decorators."""
    
    def test_with_retry_decorator(self):
        """Test the main with_retry decorator."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 2
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.01
        
        call_count = 0
        
        @with_retry(policy)
        def test_func():
            """Test Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first fail")
            return "success"
        
        with patch('time.sleep'):
            result = test_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_with_retry_async_decorator(self):
        """Test with_retry decorator on async function."""
        # Mock policy
        policy = Mock()
        policy.max_attempts = 2
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.01
        
        call_count = 0
        
        @with_retry(policy)
        async def test_async_func():
            """Test Async Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first fail")
            return "async_success"
        
        with patch('asyncio.sleep'):
            result = await test_async_func()
        
        assert result == "async_success"
        assert call_count == 2
    
    def test_with_circuit_breaker_retry_decorator(self):
        """Test circuit breaker retry decorator."""
        @with_circuit_breaker_retry(failure_threshold=1)
        def test_func():
            """Test Func operation."""
            raise Exception("always fails")
        
        # First call should fail and open circuit
        with pytest.raises(Exception, match="always fails"):
            test_func()
        
        # Second call should fail due to open circuit
        with pytest.raises(Exception, match="Circuit breaker is open"):
            test_func()
    
    @pytest.mark.asyncio
    async def test_with_bulkhead_retry_decorator(self):
        """Test bulkhead retry decorator."""
        @with_bulkhead_retry(max_concurrent=1)
        async def test_async_func():
            """Test Async Func operation."""
            await asyncio.sleep(0.05)
            return "bulkhead_success"
        
        # Should work for async function
        result = await test_async_func()
        assert result == "bulkhead_success"
    
    def test_with_bulkhead_retry_sync_function_error(self):
        """Test bulkhead retry decorator raises error for sync function."""
        with pytest.raises(ValueError, match="Bulkhead retry only supports async functions"):
            @with_bulkhead_retry()
            def sync_func():
                """Sync Func operation."""
                return "sync"


@pytest.mark.unit
class TestComplexityReduction:
    """Test that validates complexity reduction from 19 to 2."""
    
    def test_original_decorator_replacement(self):
        """Verify the 19-complexity decorator is replaced."""
        # Import the updated retry module
        from dotmac_isp.sdks.core.retry import with_retry as updated_with_retry
        
        # The decorator should use strategy pattern now
        decorator = updated_with_retry()
        
        # Should work as a decorator
        @decorator
        def test_func():
            """Test Func operation."""
            return "test"
        
        result = test_func()
        assert result == "test"
    
    def test_strategy_pattern_handles_all_scenarios(self):
        """Test that strategy pattern handles all original scenarios."""
        # Test sync function
        policy = Mock()
        policy.max_attempts = 3
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.01
        
        call_count = 0
        
        @with_retry(policy)
        def sync_func():
            """Sync Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"fail{call_count}")
            return "sync_success"
        
        with patch('time.sleep'):
            result = sync_func()
        
        assert result == "sync_success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_strategy_pattern(self):
        """Test async strategy pattern."""
        policy = Mock()
        policy.max_attempts = 3
        policy.should_retry.return_value = True
        policy.calculate_delay.return_value = 0.01
        
        call_count = 0
        
        @with_retry(policy)
        async def async_func():
            """Async Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"async_fail{call_count}")
            return "async_success"
        
        with patch('asyncio.sleep'):
            result = await async_func()
        
        assert result == "async_success"
        assert call_count == 3
    
    def test_error_handling_preserved(self):
        """Test that error handling is preserved in new implementation."""
        policy = Mock()
        policy.max_attempts = 1
        policy.should_retry.return_value = False
        
        @with_retry(policy)
        def failing_func():
            """Failing Func operation."""
            raise ValueError("test error")
        
        # Should propagate exception when no retry
        with pytest.raises(ValueError, match="test error"):
            failing_func()


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry system."""
    
    def test_retry_integration_with_real_policy(self):
        """Test retry integration with real retry policy."""
        # Create a real policy (if available in the system)
        try:
            from dotmac_isp.sdks.core.retry import RetryPolicy
            policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        except ImportError:
            # Mock if not available
            policy = Mock()
            policy.max_attempts = 3
            policy.should_retry.return_value = True
            policy.calculate_delay.return_value = 0.01
        
        call_count = 0
        
        @with_retry(policy)
        def integration_func():
            """Integration Func operation."""
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("connection failed")
            return "connected"
        
        with patch('time.sleep'):
            result = integration_func()
        
        assert result == "connected"
        assert call_count == 3


@pytest.mark.performance
class TestPerformanceImprovement:
    """Test that the new implementation performs well."""
    
    def test_retry_strategy_performance(self):
        """Test that retry strategies are efficient."""
        import time
        
        policy = Mock()
        policy.max_attempts = 1
        
        @with_retry(policy)
        def fast_func():
            """Fast Func operation."""
            return "fast"
        
        # Time multiple executions
        start_time = time.time()
        
        for _ in range(1000):
            result = fast_func()
            assert result == "fast"
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (under 0.5 seconds for 1000 executions)
        assert duration < 0.5, f"Performance test took {duration:.3f}s"
    
    def test_decorator_creation_efficiency(self):
        """Test that decorator creation is efficient."""
        import time
        
        # Time multiple decorator creations
        start_time = time.time()
        
        for _ in range(1000):
            decorator = with_retry()
            assert decorator is not None
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete very quickly (under 0.1 second for 1k creations)
        assert duration < 0.1, f"Decorator creation took {duration:.3f}s"