"""Tests for retry mechanisms."""


import pytest

from dotmac_tasks_utils.retry import (
    AsyncRetryManager,
    RetryError,
    calculate_backoff,
    retry_async,
    retry_sync,
    retry_with_manager,
)


class TestBackoffCalculation:
    """Test backoff calculation logic."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        # No jitter for predictable results
        assert calculate_backoff(0, base_delay=1.0, backoff_factor=2.0, jitter=False) == 1.0
        assert calculate_backoff(1, base_delay=1.0, backoff_factor=2.0, jitter=False) == 2.0
        assert calculate_backoff(2, base_delay=1.0, backoff_factor=2.0, jitter=False) == 4.0
        assert calculate_backoff(3, base_delay=1.0, backoff_factor=2.0, jitter=False) == 8.0

    def test_max_delay_cap(self):
        """Test maximum delay capping."""
        delay = calculate_backoff(
            10, base_delay=1.0, backoff_factor=2.0, max_delay=5.0, jitter=False
        )
        assert delay == 5.0

    def test_jitter_variation(self):
        """Test that jitter produces different results."""
        delays = [
            calculate_backoff(3, base_delay=1.0, backoff_factor=2.0, jitter=True)
            for _ in range(10)
        ]

        # Should have some variation due to jitter
        assert len(set(delays)) > 1

        # All delays should be reasonable (around 8.0 +/- 25%)
        for delay in delays:
            assert 6.0 <= delay <= 10.0


class TestAsyncRetry:
    """Test async retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test that successful operations don't retry."""
        call_count = 0

        @retry_async(max_attempts=3)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry behavior on failures."""
        call_count = 0

        @retry_async(max_attempts=3, base_delay=0.01)  # Fast retry for testing
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await failing_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test that RetryError is raised when max attempts exceeded."""
        call_count = 0

        @retry_async(max_attempts=2, base_delay=0.01)
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            await always_failing_func()

        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_exception, ValueError)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_specific_exceptions(self):
        """Test retry only on specific exception types."""
        call_count = 0

        @retry_async(max_attempts=3, exceptions=(ValueError,), base_delay=0.01)
        async def mixed_exceptions_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable")
            if call_count == 2:
                raise TypeError("Not retryable")

        # Should not retry TypeError
        with pytest.raises(TypeError):
            await mixed_exceptions_func()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Test retry callback functionality."""
        retry_calls = []

        def on_retry(attempt: int, exception: Exception):
            retry_calls.append((attempt, str(exception)))

        @retry_async(max_attempts=3, on_retry=on_retry, base_delay=0.01)
        async def failing_func():
            if len(retry_calls) < 2:
                raise ValueError(f"Failure {len(retry_calls) + 1}")
            return "success"

        result = await failing_func()
        assert result == "success"
        assert len(retry_calls) == 2
        assert retry_calls[0] == (1, "Failure 1")
        assert retry_calls[1] == (2, "Failure 2")


class TestSyncRetry:
    """Test synchronous retry decorator."""

    def test_successful_operation(self):
        """Test that successful operations don't retry."""
        call_count = 0

        @retry_sync(max_attempts=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test retry behavior on failures."""
        call_count = 0

        @retry_sync(max_attempts=3, base_delay=0.01)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_max_attempts_exceeded(self):
        """Test that RetryError is raised when max attempts exceeded."""
        call_count = 0

        @retry_sync(max_attempts=2, base_delay=0.01)
        def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            always_failing_func()

        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_exception, ValueError)
        assert call_count == 2


class TestAsyncRetryManager:
    """Test AsyncRetryManager context manager."""

    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test successful operation without retries."""
        attempt_count = 0

        while True:
            async with AsyncRetryManager(max_attempts=3, base_delay=0.01):
                attempt_count += 1
                # Success on first attempt
                break

        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry behavior with context manager."""
        attempt_count = 0

        while True:
            async with AsyncRetryManager(max_attempts=3, base_delay=0.01):
                attempt_count += 1
                if attempt_count < 3:
                    raise ValueError("Temporary failure")
                # Success on third attempt
                break

        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_with_manager(self):
        """Test max attempts exceeded with context manager."""
        attempt_count = 0

        async def always_failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            await retry_with_manager(always_failing_operation, max_attempts=2, base_delay=0.01)

        assert attempt_count == 2


class TestRetryWithManager:
    """Test retry_with_manager utility."""

    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test successful operation with retry manager."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_manager(operation, max_attempts=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_operation(self):
        """Test retry operation with retry manager."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await retry_with_manager(operation, max_attempts=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3
