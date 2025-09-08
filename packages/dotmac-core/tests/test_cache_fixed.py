"""
Test cases for DotMac Core cache functionality - Fixed version.
"""

import asyncio

import pytest

from dotmac.core.cache import (
    CacheService,
    cached,
    create_cache_service,
)


class TestCacheService:
    """Test CacheService basic functionality."""

    def test_cache_service_creation(self):
        """Test basic cache service creation."""
        # Test that we can create a cache service
        service = create_cache_service()
        assert service is not None
        assert isinstance(service, CacheService)

    @pytest.mark.asyncio
    async def test_cache_service_initialization(self):
        """Test cache service initialization."""
        service = create_cache_service()

        # Should be able to initialize without errors
        await service.initialize()

        # Test that service is properly initialized
        assert service.initialized is True

    @pytest.mark.asyncio
    async def test_cache_service_basic_operations(self):
        """Test basic cache operations."""
        service = create_cache_service()
        await service.initialize()

        # Test set operation
        result = await service.set("test_key", "test_value")
        assert result is True

        # Test get operation
        result = await service.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_cache_service_key_not_found(self):
        """Test cache service with non-existent key."""
        service = create_cache_service()
        await service.initialize()

        # Test get non-existent key
        result = await service.get("non_existent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_service_delete_operation(self):
        """Test cache delete operation."""
        service = create_cache_service()
        await service.initialize()

        # Set a key first
        await service.set("delete_test", "value")

        # Verify it exists
        result = await service.get("delete_test")
        assert result == "value"

        # Delete the key
        deleted = await service.delete("delete_test")
        assert deleted is True

        # Verify it's gone
        result = await service.get("delete_test")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_service_exists(self):
        """Test cache exists operation."""
        service = create_cache_service()
        await service.initialize()

        # Key should not exist initially
        exists = await service.exists("test_exists")
        assert exists is False

        # Set the key
        await service.set("test_exists", "value")

        # Now it should exist
        exists = await service.exists("test_exists")
        assert exists is True

    @pytest.mark.asyncio
    async def test_cache_service_with_ttl(self):
        """Test cache service with TTL."""
        service = create_cache_service()
        await service.initialize()

        # Set key with very short TTL
        await service.set("ttl_key", "ttl_value", ttl=1)

        # Should exist immediately
        result = await service.get("ttl_key")
        assert result == "ttl_value"

        # Wait for TTL to expire
        await asyncio.sleep(1.1)

        # Should be expired now
        result = await service.get("ttl_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_service_clear(self):
        """Test cache clear operation."""
        service = create_cache_service()
        await service.initialize()

        # Set multiple keys
        await service.set("clear_key1", "value1")
        await service.set("clear_key2", "value2")

        # Verify they exist
        assert await service.get("clear_key1") == "value1"
        assert await service.get("clear_key2") == "value2"

        # Clear cache
        result = await service.clear()
        assert result is True

        # Verify keys are gone
        assert await service.get("clear_key1") is None
        assert await service.get("clear_key2") is None


class TestCacheIntegration:
    """Integration tests for cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_with_complex_data_types(self):
        """Test cache with complex data types."""
        service = create_cache_service()
        await service.initialize()

        # Test with dictionary
        complex_data = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "nested_value"},
        }

        await service.set("complex_key", complex_data)
        result = await service.get("complex_key")

        assert result == complex_data

    @pytest.mark.asyncio
    async def test_cache_service_health_check(self):
        """Test cache service health check."""
        service = create_cache_service()
        await service.initialize()

        # Health check should return status
        health = await service.health_check()
        assert isinstance(health, dict)
        assert "initialized" in health
        assert health["initialized"] is True

    @pytest.mark.asyncio
    async def test_cache_service_cleanup_expired(self):
        """Test cleanup of expired entries."""
        service = create_cache_service()
        await service.initialize()

        # Set key with short TTL
        await service.set("expire_test", "value", ttl=1)

        # Wait for expiry
        await asyncio.sleep(1.1)

        # Cleanup expired entries
        cleaned = service.cleanup_expired()
        assert cleaned >= 0  # Should return number of cleaned entries

    @pytest.mark.asyncio
    async def test_cache_service_bulk_operations(self):
        """Test cache service bulk operations."""
        service = create_cache_service()
        await service.initialize()

        # Set multiple keys
        keys_values = {"bulk_key1": "value1", "bulk_key2": "value2", "bulk_key3": "value3"}

        # Set all keys
        for key, value in keys_values.items():
            await service.set(key, value)

        # Get all keys
        results = {}
        for key in keys_values:
            results[key] = await service.get(key)

        assert results == keys_values


# Simplified cached decorator tests without tenant support
class TestCachedDecorator:
    """Test cached decorator functionality - simplified."""

    @pytest.mark.asyncio
    async def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        call_count = 0

        @cached(ttl=300)
        async def test_function(value: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed_{value}"

        # First call should execute function
        result1 = await test_function("test")
        assert result1 == "processed_test"
        assert call_count == 1

        # Second call should use cache
        result2 = await test_function("test")
        assert result2 == "processed_test"
        assert call_count == 1  # Should not increment

    @pytest.mark.asyncio
    async def test_cached_decorator_different_args(self):
        """Test cached decorator with different arguments."""
        call_count = 0

        @cached(ttl=300)
        async def test_function(value: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed_{value}"

        # Different arguments should call function separately
        result1 = await test_function("test1")
        result2 = await test_function("test2")

        assert result1 == "processed_test1"
        assert result2 == "processed_test2"
        assert call_count == 2

    def test_cached_decorator_sync_function_raises_error(self):
        """Test cached decorator raises error for sync functions."""
        with pytest.raises(TypeError) as exc_info:

            @cached(ttl=300)
            def sync_function(value: str) -> str:
                return f"processed_{value}"

        assert "cached decorator can only be used with async functions" in str(exc_info.value)
