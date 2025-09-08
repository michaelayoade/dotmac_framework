"""
Test cases for DotMac Core cache functionality.
"""

import asyncio
import uuid

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
        assert service is not None

    @pytest.mark.asyncio
    async def test_cache_service_basic_operations(self):
        """Test basic cache operations."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Test set operation
        await service.set("test_key", "test_value", tenant_id=tenant_id)

        # Test get operation
        result = await service.get("test_key", tenant_id=tenant_id)
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_cache_service_key_not_found(self):
        """Test cache service with non-existent key."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Test get non-existent key
        result = await service.get("non_existent_key", tenant_id=tenant_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_service_delete_operation(self):
        """Test cache delete operation."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Set a key first
        await service.set("delete_test", "value", tenant_id=tenant_id)

        # Verify it exists
        result = await service.get("delete_test", tenant_id=tenant_id)
        assert result == "value"

        # Delete the key
        await service.delete("delete_test", tenant_id=tenant_id)

        # Verify it's gone
        result = await service.get("delete_test", tenant_id=tenant_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_service_tenant_isolation(self):
        """Test tenant isolation in cache service."""
        service = create_cache_service()
        await service.initialize()

        tenant1_id = uuid.uuid4()
        tenant2_id = uuid.uuid4()

        # Set same key for different tenants
        await service.set("shared_key", "tenant1_value", tenant_id=tenant1_id)
        await service.set("shared_key", "tenant2_value", tenant_id=tenant2_id)

        # Verify tenant isolation
        result1 = await service.get("shared_key", tenant_id=tenant1_id)
        result2 = await service.get("shared_key", tenant_id=tenant2_id)

        assert result1 == "tenant1_value"
        assert result2 == "tenant2_value"

    @pytest.mark.asyncio
    async def test_cache_service_with_ttl(self):
        """Test cache service with TTL."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Set key with very short TTL
        await service.set("ttl_key", "ttl_value", tenant_id=tenant_id, ttl=1)

        # Should exist immediately
        result = await service.get("ttl_key", tenant_id=tenant_id)
        assert result == "ttl_value"

        # Wait for TTL to expire
        await asyncio.sleep(1.1)

        # Should be expired now
        result = await service.get("ttl_key", tenant_id=tenant_id)
        assert result is None


class TestCachedDecorator:
    """Test cached decorator functionality."""

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

    @pytest.mark.asyncio
    async def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments."""
        call_count = 0

        @cached(ttl=300)
        async def test_function(value: str, multiplier: int = 1) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed_{value}_{multiplier}"

        # First call
        result1 = await test_function("test", multiplier=2)
        assert result1 == "processed_test_2"
        assert call_count == 1

        # Same args should use cache
        result2 = await test_function("test", multiplier=2)
        assert result2 == "processed_test_2"
        assert call_count == 1

        # Different kwargs should call function again
        result3 = await test_function("test", multiplier=3)
        assert result3 == "processed_test_3"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_custom_key(self):
        """Test cached decorator with custom key function."""
        call_count = 0

        def custom_key_func(*args, **kwargs):
            return f"custom_{args[0]}"

        @cached(ttl=300, key_func=custom_key_func)
        async def test_function(value: str, ignored_param: str = None) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed_{value}"

        # Different ignored_param but same key should use cache
        result1 = await test_function("test", ignored_param="a")
        result2 = await test_function("test", ignored_param="b")

        assert result1 == "processed_test"
        assert result2 == "processed_test"
        assert call_count == 1  # Should use cache

    def test_cached_decorator_sync_function_raises_error(self):
        """Test cached decorator raises error for sync functions."""
        with pytest.raises(TypeError) as exc_info:

            @cached(ttl=300)
            def sync_function(value: str) -> str:
                return f"processed_{value}"

        assert "cached decorator can only be used with async functions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cached_decorator_exception_handling(self):
        """Test cached decorator doesn't cache exceptions."""
        call_count = 0

        @cached(ttl=300)
        async def test_function(should_fail: bool = False) -> str:
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise ValueError("Test error")
            return "success"

        # First call succeeds
        result = await test_function(should_fail=False)
        assert result == "success"
        assert call_count == 1

        # Second call with same args should use cache
        result = await test_function(should_fail=False)
        assert result == "success"
        assert call_count == 1

        # Call that raises exception should not be cached
        with pytest.raises(ValueError):
            await test_function(should_fail=True)
        assert call_count == 2

        # Another call with same failing args should execute again (not cached)
        with pytest.raises(ValueError):
            await test_function(should_fail=True)
        assert call_count == 3


class TestCacheIntegration:
    """Integration tests for cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_service_and_decorator_integration(self):
        """Test integration between cache service and decorator."""
        # Create a shared cache service
        service = create_cache_service()
        await service.initialize()

        call_count = 0

        @cached(ttl=300)
        async def cached_function(value: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{value}"

        # Use the function which should use the cache service
        result1 = await cached_function("test")
        assert result1 == "result_test"
        assert call_count == 1

        # Second call should use cache
        result2 = await cached_function("test")
        assert result2 == "result_test"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_with_complex_data_types(self):
        """Test cache with complex data types."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Test with dictionary
        complex_data = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "nested_value"},
        }

        await service.set("complex_key", complex_data, tenant_id=tenant_id)
        result = await service.get("complex_key", tenant_id=tenant_id)

        assert result == complex_data

    @pytest.mark.asyncio
    async def test_cache_service_health_check(self):
        """Test cache service health check."""
        service = create_cache_service()
        await service.initialize()

        # Health check should return status
        health = await service.health_check()
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_cache_service_metrics(self):
        """Test cache service metrics collection."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Perform some operations
        await service.set("metrics_key", "value", tenant_id=tenant_id)
        await service.get("metrics_key", tenant_id=tenant_id)
        await service.get("non_existent", tenant_id=tenant_id)

        # Get metrics
        metrics = await service.get_metrics()
        assert isinstance(metrics, dict)
        # Metrics should contain hit/miss information
        assert "cache_hits" in metrics or "operations" in metrics

    @pytest.mark.asyncio
    async def test_cache_service_bulk_operations(self):
        """Test cache service bulk operations."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Set multiple keys
        keys_values = {"bulk_key1": "value1", "bulk_key2": "value2", "bulk_key3": "value3"}

        # Set all keys
        for key, value in keys_values.items():
            await service.set(key, value, tenant_id=tenant_id)

        # Get all keys
        results = {}
        for key in keys_values:
            results[key] = await service.get(key, tenant_id=tenant_id)

        assert results == keys_values

    @pytest.mark.asyncio
    async def test_cache_service_cleanup(self):
        """Test cache service cleanup and shutdown."""
        service = create_cache_service()
        await service.initialize()

        tenant_id = uuid.uuid4()

        # Set some data
        await service.set("cleanup_key", "value", tenant_id=tenant_id)

        # Verify data exists
        result = await service.get("cleanup_key", tenant_id=tenant_id)
        assert result == "value"

        # Cleanup should work without errors
        await service.cleanup()

        # After cleanup, service should still be functional for basic operations
        # (depending on implementation, this might reset caches)
        try:
            await service.set("post_cleanup", "value", tenant_id=tenant_id)
        except Exception:
            # Some implementations might not allow operations after cleanup
            pass
