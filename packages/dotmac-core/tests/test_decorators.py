"""
Test cases for DotMac Core decorators.
"""

import asyncio
from unittest.mock import patch

import pytest

from dotmac.core.decorators import (
    RateLimiter,
    rate_limit,
    retry_on_failure,
    standard_exception_handler,
    timeout,
)
from dotmac.core.exceptions import TimeoutError


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        assert isinstance(limiter._calls, dict)

    def test_rate_limiter_allows_calls_under_limit(self):
        """Test rate limiter allows calls under limit."""
        limiter = RateLimiter()

        # Should allow first call
        assert limiter.is_allowed("test_key", max_calls=2, time_window=60) is True

        # Should allow second call
        assert limiter.is_allowed("test_key", max_calls=2, time_window=60) is True

    def test_rate_limiter_blocks_calls_over_limit(self):
        """Test rate limiter blocks calls over limit."""
        limiter = RateLimiter()

        # Allow first two calls
        assert limiter.is_allowed("test_key", max_calls=2, time_window=60) is True
        assert limiter.is_allowed("test_key", max_calls=2, time_window=60) is True

        # Should block third call
        assert limiter.is_allowed("test_key", max_calls=2, time_window=60) is False

    def test_rate_limiter_cleans_old_entries(self):
        """Test rate limiter cleans old entries."""
        limiter = RateLimiter()

        # Mock time to simulate old entries
        with patch("time.time", return_value=1000):
            limiter.is_allowed("test_key", max_calls=1, time_window=60)

        # Move forward in time beyond window
        with patch("time.time", return_value=1100):
            # Should allow call as old entry is cleaned
            assert limiter.is_allowed("test_key", max_calls=1, time_window=60) is True

    def test_rate_limiter_different_keys(self):
        """Test rate limiter handles different keys separately."""
        limiter = RateLimiter()

        # Fill up limit for key1
        assert limiter.is_allowed("key1", max_calls=1, time_window=60) is True
        assert limiter.is_allowed("key1", max_calls=1, time_window=60) is False

        # key2 should still be allowed
        assert limiter.is_allowed("key2", max_calls=1, time_window=60) is True


class TestRateLimitDecorator:
    """Test rate_limit decorator."""

    def test_rate_limit_sync_function_success(self):
        """Test rate limit decorator on sync function allows calls."""

        @rate_limit(max_calls=2, time_window=60)
        def test_func(value):
            return value * 2

        # Should allow first two calls
        assert test_func(5) == 10
        assert test_func(5) == 10

    def test_rate_limit_sync_function_exceeds_limit(self):
        """Test rate limit decorator blocks calls that exceed limit."""

        @rate_limit(max_calls=1, time_window=60)
        def test_func():
            return "success"

        # First call should work
        assert test_func() == "success"

        # Second call should raise exception
        with pytest.raises(Exception) as exc_info:
            test_func()

        assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_async_function_success(self):
        """Test rate limit decorator on async function allows calls."""

        @rate_limit(max_calls=2, time_window=60)
        async def test_func(value):
            return value * 2

        # Should allow first two calls
        assert await test_func(5) == 10
        assert await test_func(5) == 10

    @pytest.mark.asyncio
    async def test_rate_limit_async_function_exceeds_limit(self):
        """Test rate limit decorator blocks async calls that exceed limit."""
        from fastapi import HTTPException

        @rate_limit(max_calls=1, time_window=60)
        async def test_func():
            return "success"

        # First call should work
        assert await test_func() == "success"

        # Second call should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await test_func()

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail

    def test_rate_limit_custom_key_function(self):
        """Test rate limit decorator with custom key function."""

        def custom_key_func(*args, **kwargs):
            return f"custom_{args[0]}"

        @rate_limit(max_calls=1, time_window=60, key_func=custom_key_func)
        def test_func(user_id):
            return f"user_{user_id}"

        # Different users should have separate limits
        assert test_func("user1") == "user_user1"
        assert test_func("user2") == "user_user2"

        # Same user should be rate limited
        with pytest.raises(Exception):
            test_func("user1")

    def test_rate_limit_default_key_generation(self):
        """Test rate limit decorator default key generation."""

        @rate_limit(max_calls=1, time_window=60)
        def test_func_with_args(arg1):
            return arg1

        @rate_limit(max_calls=1, time_window=60)
        def test_func_no_args():
            return "no_args"

        # Function with args uses first arg in key
        test_func_with_args("test")
        with pytest.raises(Exception):
            test_func_with_args("test")

        # Function without args uses 'global' in key
        test_func_no_args()
        with pytest.raises(Exception):
            test_func_no_args()


class TestStandardExceptionHandlerDecorator:
    """Test standard_exception_handler decorator."""

    def test_standard_exception_handler_sync_success(self):
        """Test standard exception handler with successful sync function."""

        @standard_exception_handler
        def test_func(value):
            return value * 2

        result = test_func(5)
        assert result == 10

    def test_standard_exception_handler_sync_exception(self):
        """Test standard exception handler with sync function that raises exception."""

        @standard_exception_handler
        def test_func():
            raise ValueError("Test error")

        with patch("dotmac.core.decorators.logger") as mock_logger:
            with pytest.raises(ValueError):
                test_func()

            # Should log the exception
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_standard_exception_handler_async_success(self):
        """Test standard exception handler with successful async function."""

        @standard_exception_handler
        async def test_func(value):
            return value * 2

        result = await test_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_standard_exception_handler_async_exception(self):
        """Test standard exception handler with async function that raises exception."""

        @standard_exception_handler
        async def test_func():
            raise ValueError("Test error")

        with patch("dotmac.core.decorators.logger") as mock_logger:
            with pytest.raises(ValueError):
                await test_func()

            # Should log the exception
            mock_logger.error.assert_called_once()


class TestRetryOnFailureDecorator:
    """Test retry_on_failure decorator."""

    def test_retry_sync_function_success_first_attempt(self):
        """Test retry decorator with sync function that succeeds on first attempt."""

        @retry_on_failure(max_attempts=3, delay=0.1)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_retry_sync_function_success_after_retries(self):
        """Test retry decorator with sync function that succeeds after retries."""
        attempt_count = 0

        @retry_on_failure(max_attempts=3, delay=0.1)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        with patch("dotmac.core.decorators.logger") as mock_logger:
            result = test_func()
            assert result == "success"
            assert attempt_count == 2

            # Should log warning for failed attempts
            mock_logger.warning.assert_called()

    def test_retry_sync_function_max_attempts_exceeded(self):
        """Test retry decorator when max attempts are exceeded."""

        @retry_on_failure(max_attempts=2, delay=0.1)
        def test_func():
            raise ValueError("Persistent failure")

        with patch("dotmac.core.decorators.logger") as mock_logger:
            with pytest.raises(ValueError) as exc_info:
                test_func()

            assert "Persistent failure" in str(exc_info.value)
            # Should log warning for failed attempts
            assert mock_logger.warning.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_function_success_first_attempt(self):
        """Test retry decorator with async function that succeeds on first attempt."""

        @retry_on_failure(max_attempts=3, delay=0.1)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_async_function_success_after_retries(self):
        """Test retry decorator with async function that succeeds after retries."""
        attempt_count = 0

        @retry_on_failure(max_attempts=3, delay=0.1)
        async def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        with patch("dotmac.core.decorators.logger") as mock_logger:
            result = await test_func()
            assert result == "success"
            assert attempt_count == 2

            # Should log warning for failed attempts
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_retry_async_function_max_attempts_exceeded(self):
        """Test retry decorator with async function when max attempts are exceeded."""

        @retry_on_failure(max_attempts=2, delay=0.1)
        async def test_func():
            raise ValueError("Persistent failure")

        with patch("dotmac.core.decorators.logger") as mock_logger:
            with pytest.raises(ValueError) as exc_info:
                await test_func()

            assert "Persistent failure" in str(exc_info.value)
            # Should log warning for failed attempts
            assert mock_logger.warning.call_count == 1

    def test_retry_backoff_calculation(self):
        """Test retry decorator backoff calculation."""
        delays = []

        def mock_sleep(delay):
            delays.append(delay)

        @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
        def test_func():
            raise ValueError("Always fails")

        with patch("time.sleep", side_effect=mock_sleep):
            with pytest.raises(ValueError):
                test_func()

        # Should have exponential backoff: 1.0, 2.0
        assert delays == [1.0, 2.0]


class TestTimeoutDecorator:
    """Test timeout decorator."""

    @pytest.mark.asyncio
    async def test_timeout_function_completes_within_timeout(self):
        """Test timeout decorator with function that completes within timeout."""

        @timeout(seconds=1.0)
        async def test_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_function_exceeds_timeout(self):
        """Test timeout decorator with function that exceeds timeout."""

        @timeout(seconds=0.1)
        async def test_func():
            await asyncio.sleep(0.5)
            return "should not reach here"

        with pytest.raises(TimeoutError):
            await test_func()

    def test_timeout_decorator_only_works_with_async_functions(self):
        """Test timeout decorator raises TypeError for sync functions."""
        with pytest.raises(TypeError) as exc_info:

            @timeout(seconds=1.0)
            def sync_func():
                return "sync"

        assert "timeout decorator can only be used with async functions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_with_args_and_kwargs(self):
        """Test timeout decorator with function that takes args and kwargs."""

        @timeout(seconds=1.0)
        async def test_func(arg1, arg2=None):
            await asyncio.sleep(0.1)
            return f"{arg1}_{arg2}"

        result = await test_func("test", arg2="value")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_timeout_preserves_function_attributes(self):
        """Test timeout decorator preserves function attributes."""

        @timeout(seconds=1.0)
        async def test_func():
            """Test function docstring."""
            return "success"

        assert test_func.__name__ == "test_func"
        assert "Test function docstring" in test_func.__doc__
