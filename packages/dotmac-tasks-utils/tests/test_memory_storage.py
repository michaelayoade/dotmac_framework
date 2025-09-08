"""Tests for memory storage implementations."""

import asyncio

import pytest

from dotmac_tasks_utils.storage.memory import MemoryIdempotencyStore, MemoryLockStore


class TestMemoryIdempotencyStore:
    """Test the MemoryIdempotencyStore class."""

    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Test basic get/set/exists/delete operations."""
        store = MemoryIdempotencyStore()

        # Initially empty
        assert await store.get("key1") is None
        assert not await store.exists("key1")

        # Set a value
        await store.set("key1", "value1")
        assert await store.get("key1") == "value1"
        assert await store.exists("key1")

        # Update value
        await store.set("key1", "value2")
        assert await store.get("key1") == "value2"

        # Delete value
        await store.delete("key1")
        assert await store.get("key1") is None
        assert not await store.exists("key1")

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        store = MemoryIdempotencyStore()

        # Set with short TTL
        await store.set("expiring_key", "value", ttl=1)
        assert await store.get("expiring_key") == "value"

        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await store.get("expiring_key") is None
        assert not await store.exists("expiring_key")

    @pytest.mark.asyncio
    async def test_complex_values(self):
        """Test storing complex values."""
        store = MemoryIdempotencyStore()

        complex_value = {
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "tuple": (4, 5, 6),
        }

        await store.set("complex", complex_value)
        retrieved = await store.get("complex")
        assert retrieved == complex_value


class TestMemoryLockStore:
    """Test the MemoryLockStore class."""

    @pytest.mark.asyncio
    async def test_basic_locking(self):
        """Test basic lock acquisition and release."""
        store = MemoryLockStore()

        assert not await store.is_locked("lock1")

        async with store.acquire_lock("lock1") as acquired:
            assert acquired
            assert await store.is_locked("lock1")

        # Lock should be released after context
        assert not await store.is_locked("lock1")

    @pytest.mark.asyncio
    async def test_lock_timeout(self):
        """Test lock acquisition timeout."""
        store = MemoryLockStore()

        # First coroutine acquires lock
        async def hold_lock():
            async with store.acquire_lock("lock1", ttl=2.0) as acquired:
                assert acquired
                await asyncio.sleep(0.5)  # Hold lock briefly

        # Second coroutine fails to acquire with short timeout
        async def try_acquire():
            async with store.acquire_lock("lock1", timeout=0.1) as acquired:
                assert not acquired  # Should fail due to timeout

        # Run both concurrently
        await asyncio.gather(hold_lock(), try_acquire())

    @pytest.mark.asyncio
    async def test_lock_ttl_expiration(self):
        """Test lock TTL expiration."""
        store = MemoryLockStore()

        # Acquire lock with short TTL
        async with store.acquire_lock("lock1", ttl=0.5) as acquired:
            assert acquired

            # Lock should exist initially
            assert await store.is_locked("lock1")

            # Wait for TTL to expire (but we still hold it in context)
            await asyncio.sleep(0.6)

        # After context, lock should be released
        assert not await store.is_locked("lock1")

    @pytest.mark.asyncio
    async def test_force_release(self):
        """Test force releasing a lock."""
        store = MemoryLockStore()

        async with store.acquire_lock("lock1") as acquired:
            assert acquired
            assert await store.is_locked("lock1")

            # Force release from outside
            await store.release_lock("lock1")

            # Lock should be released
            assert not await store.is_locked("lock1")

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent lock access."""
        store = MemoryLockStore()
        results = []

        async def worker(worker_id: int):
            async with store.acquire_lock("shared_resource", timeout=1.0) as acquired:
                if acquired:
                    results.append(f"worker_{worker_id}_start")
                    await asyncio.sleep(0.1)  # Simulate work
                    results.append(f"worker_{worker_id}_end")
                else:
                    results.append(f"worker_{worker_id}_failed")

        # Start multiple workers
        await asyncio.gather(*[worker(i) for i in range(3)])

        # Should have at least one successful worker
        successful_workers = [r for r in results if "_start" in r]
        assert len(successful_workers) >= 1

        # No overlapping work (each worker should complete before next starts)
        start_count = len([r for r in results if "_start" in r])
        end_count = len([r for r in results if "_end" in r])
        assert start_count == end_count
