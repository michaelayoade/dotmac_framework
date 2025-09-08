"""Tests for idempotency functionality."""


import pytest

from dotmac_tasks_utils.idempotency import (
    IdempotencyManager,
    generate_key,
    with_idempotency,
    with_sync_idempotency,
)
from dotmac_tasks_utils.storage.memory import MemoryIdempotencyStore, SyncMemoryIdempotencyStore


class TestKeyGeneration:
    """Test idempotency key generation."""

    def test_consistent_key_generation(self):
        """Test that same arguments produce same keys."""
        key1 = generate_key("arg1", "arg2", kwarg1="value1", kwarg2="value2")
        key2 = generate_key("arg1", "arg2", kwarg1="value1", kwarg2="value2")
        assert key1 == key2

    def test_different_args_different_keys(self):
        """Test that different arguments produce different keys."""
        key1 = generate_key("arg1", "arg2")
        key2 = generate_key("arg1", "arg3")
        assert key1 != key2

    def test_kwargs_order_independence(self):
        """Test that kwargs order doesn't affect key generation."""
        key1 = generate_key(a="1", b="2", c="3")
        key2 = generate_key(c="3", a="1", b="2")
        assert key1 == key2

    def test_complex_arguments(self):
        """Test key generation with complex arguments."""
        complex_args = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "tuple": (4, 5, 6),
        }

        key1 = generate_key(complex_args)
        key2 = generate_key(complex_args)
        assert key1 == key2


class TestAsyncIdempotency:
    """Test async idempotency decorator."""

    @pytest.mark.asyncio
    async def test_basic_idempotency(self):
        """Test basic idempotent behavior."""
        store = MemoryIdempotencyStore()
        call_count = 0

        @with_idempotency(store, key="test_operation", ttl=60)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # First call
        result1 = await test_func()
        assert result1 == "result_1"
        assert call_count == 1

        # Second call should return cached result
        result2 = await test_func()
        assert result2 == "result_1"  # Same result
        assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_auto_key_generation(self):
        """Test automatic key generation from function name and args."""
        store = MemoryIdempotencyStore()
        call_count = 0

        @with_idempotency(store, ttl=60)
        async def test_func(user_id: str):
            nonlocal call_count
            call_count += 1
            return f"processed_{user_id}_{call_count}"

        # Same arguments should be idempotent
        result1 = await test_func("user123")
        result2 = await test_func("user123")
        assert result1 == result2 == "processed_user123_1"
        assert call_count == 1

        # Different arguments should call function again
        result3 = await test_func("user456")
        assert result3 == "processed_user456_2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_callable_key_generator(self):
        """Test callable key generator."""
        store = MemoryIdempotencyStore()
        call_count = 0

        def make_key(user_id: str, action: str):
            return f"user_{user_id}_{action}"

        @with_idempotency(store, key=make_key, ttl=60)
        async def test_func(user_id: str, action: str):
            nonlocal call_count
            call_count += 1
            return f"executed_{action}_{call_count}"

        # First call
        result1 = await test_func("123", "signup")
        assert result1 == "executed_signup_1"

        # Same key should be idempotent
        result2 = await test_func("123", "signup")
        assert result2 == "executed_signup_1"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_no_result_caching(self):
        """Test idempotency without result caching."""
        store = MemoryIdempotencyStore()
        call_count = 0

        @with_idempotency(store, key="marker_only", include_result=False, ttl=60)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # First call
        result1 = await test_func()
        assert result1 == "result_1"

        # Second call should return None (no cached result)
        result2 = await test_func()
        assert result2 is None
        assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions don't get cached."""
        store = MemoryIdempotencyStore()
        call_count = 0

        @with_idempotency(store, key="failing_operation", ttl=60)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Temporary failure")
            return "success"

        # First two calls should fail
        with pytest.raises(ValueError):
            await test_func()

        with pytest.raises(ValueError):
            await test_func()

        assert call_count == 2

        # Third call should succeed
        result = await test_func()
        assert result == "success"
        assert call_count == 3

        # Fourth call should return cached success
        result2 = await test_func()
        assert result2 == "success"
        assert call_count == 3


class TestSyncIdempotency:
    """Test synchronous idempotency decorator."""

    def test_basic_idempotency(self):
        """Test basic idempotent behavior."""
        store = SyncMemoryIdempotencyStore()
        call_count = 0

        @with_sync_idempotency(store, key="sync_test", ttl=60)
        def test_func():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # First call
        result1 = test_func()
        assert result1 == "result_1"
        assert call_count == 1

        # Second call should return cached result
        result2 = test_func()
        assert result2 == "result_1"
        assert call_count == 1

    def test_auto_key_with_args(self):
        """Test automatic key generation with arguments."""
        store = SyncMemoryIdempotencyStore()
        call_count = 0

        @with_sync_idempotency(store, ttl=60)
        def process_item(item_id: int, category: str):
            nonlocal call_count
            call_count += 1
            return f"processed_{item_id}_{category}_{call_count}"

        # Same arguments
        result1 = process_item(123, "electronics")
        result2 = process_item(123, "electronics")
        assert result1 == result2 == "processed_123_electronics_1"
        assert call_count == 1

        # Different arguments
        result3 = process_item(456, "books")
        assert result3 == "processed_456_books_2"
        assert call_count == 2


class TestIdempotencyManager:
    """Test IdempotencyManager context manager."""

    @pytest.mark.asyncio
    async def test_manual_idempotency_control(self):
        """Test manual idempotency control."""
        store = MemoryIdempotencyStore()

        # First execution
        async with IdempotencyManager(store, "manual_test", ttl=60) as mgr:
            assert not mgr.already_performed

            # Simulate some work
            result = "computed_result"
            mgr.set_result(result)

        # Second execution
        async with IdempotencyManager(store, "manual_test", ttl=60) as mgr:
            assert mgr.already_performed
            cached = mgr.get_cached_result()
            assert cached == "computed_result"

    @pytest.mark.asyncio
    async def test_manager_exception_handling(self):
        """Test that exceptions prevent result caching."""
        store = MemoryIdempotencyStore()

        # First execution fails
        try:
            async with IdempotencyManager(store, "exception_test", ttl=60) as mgr:
                assert not mgr.already_performed
                mgr.set_result("should_not_be_cached")
                raise ValueError("Operation failed")
        except ValueError:
            pass

        # Second execution should not see cached result
        async with IdempotencyManager(store, "exception_test", ttl=60) as mgr:
            assert not mgr.already_performed

    @pytest.mark.asyncio
    async def test_manager_no_result_mode(self):
        """Test manager without result caching."""
        store = MemoryIdempotencyStore()

        # First execution
        async with IdempotencyManager(store, "marker_test", include_result=False, ttl=60) as mgr:
            assert not mgr.already_performed
            mgr.set_result("not_cached")

        # Second execution
        async with IdempotencyManager(store, "marker_test", include_result=False, ttl=60) as mgr:
            assert mgr.already_performed
            # Should not have cached result, just the marker
            cached = mgr.get_cached_result()
            assert cached is True  # Just the marker
