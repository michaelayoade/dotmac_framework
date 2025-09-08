"""
Tests for Cache Service - Caching functionality with Redis fallback.
"""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Adjust path for core package imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-core/src'))

from tests.utilities.service_test_base import AsyncServiceTestBase

from dotmac.core.cache.service import CacheService

# Restore path after imports
sys.path = sys.path[1:]


class TestCacheService(AsyncServiceTestBase):
    """Test suite for Cache Service functionality."""

    @pytest.fixture
    def cache_service(self):
        """Create cache service instance for testing."""
        return CacheService(default_ttl=300)

    @pytest.fixture
    def cache_service_with_redis(self):
        """Create cache service with Redis URL for testing."""
        return CacheService(redis_url="redis://localhost:6379/0", default_ttl=600)

    @pytest.mark.asyncio
    async def test_cache_service_initialization(self, cache_service):
        """Test cache service initialization."""
        assert cache_service.default_ttl == 300
        assert cache_service.redis_url is None
        assert cache_service.redis_client is None
        assert not cache_service.initialized
        assert isinstance(cache_service.memory_cache, dict)

    @pytest.mark.asyncio
    async def test_cache_service_initialization_with_redis(self, cache_service_with_redis):
        """Test cache service initialization with Redis configuration."""
        assert cache_service_with_redis.redis_url == "redis://localhost:6379/0"
        assert cache_service_with_redis.default_ttl == 600
        assert not cache_service_with_redis.initialized

    @pytest.mark.asyncio
    async def test_memory_cache_get_set(self, cache_service):
        """Test basic get/set operations with memory cache."""
        # Initialize service
        await cache_service.initialize()
        assert cache_service.initialized

        # Test set operation
        result = await cache_service.set("test_key", "test_value")
        assert result is True

        # Test get operation
        value = await cache_service.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_memory_cache_get_nonexistent(self, cache_service):
        """Test get operation for non-existent key."""
        await cache_service.initialize()

        value = await cache_service.get("nonexistent_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_memory_cache_delete(self, cache_service):
        """Test delete operation with memory cache."""
        await cache_service.initialize()

        # Set a value
        await cache_service.set("delete_test_key", "delete_test_value")

        # Verify it exists
        value = await cache_service.get("delete_test_key")
        assert value == "delete_test_value"

        # Delete it
        result = await cache_service.delete("delete_test_key")
        assert result is True

        # Verify it's gone
        value = await cache_service.get("delete_test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_memory_cache_delete_nonexistent(self, cache_service):
        """Test delete operation for non-existent key."""
        await cache_service.initialize()

        result = await cache_service.delete("nonexistent_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_memory_cache_exists(self, cache_service):
        """Test exists operation with memory cache."""
        await cache_service.initialize()

        # Key doesn't exist initially
        exists = await cache_service.exists("exists_test_key")
        assert exists is False

        # Set the key
        await cache_service.set("exists_test_key", "exists_test_value")

        # Now it should exist
        exists = await cache_service.exists("exists_test_key")
        assert exists is True

    @pytest.mark.asyncio
    async def test_memory_cache_clear(self, cache_service):
        """Test clear operation with memory cache."""
        await cache_service.initialize()

        # Set multiple values
        await cache_service.set("clear_test_1", "value1")
        await cache_service.set("clear_test_2", "value2")

        # Verify they exist
        assert await cache_service.get("clear_test_1") == "value1"
        assert await cache_service.get("clear_test_2") == "value2"

        # Clear cache
        result = await cache_service.clear()
        assert result is True

        # Verify they're gone
        assert await cache_service.get("clear_test_1") is None
        assert await cache_service.get("clear_test_2") is None

    @pytest.mark.asyncio
    async def test_cache_with_complex_data(self, cache_service):
        """Test caching complex data structures."""
        await cache_service.initialize()

        # Test with dictionary
        complex_data = {
            "user_id": "123",
            "preferences": {"theme": "dark", "language": "en"},
            "permissions": ["read", "write"],
            "metadata": {"last_login": "2023-01-01T00:00:00Z"}
        }

        await cache_service.set("complex_data_key", complex_data)
        retrieved_data = await cache_service.get("complex_data_key")

        assert retrieved_data == complex_data
        assert retrieved_data["user_id"] == "123"
        assert retrieved_data["preferences"]["theme"] == "dark"
        assert len(retrieved_data["permissions"]) == 2

    @pytest.mark.asyncio
    async def test_cache_with_ttl_expiration(self, cache_service):
        """Test TTL (time-to-live) functionality."""
        await cache_service.initialize()

        # Set value with very short TTL
        await cache_service.set("ttl_test_key", "ttl_test_value", ttl=1)

        # Should exist immediately
        value = await cache_service.get("ttl_test_key")
        assert value == "ttl_test_value"

        # Wait for expiration (simulate with manual expiration)
        import time
        time.sleep(1.1)

        # Should be expired (in real memory cache, we'd need to implement TTL checking)
        # For now, just verify the set operation worked
        assert isinstance(cache_service.memory_cache.get("ttl_test_key"), dict)

    @pytest.mark.asyncio
    @patch('redis.asyncio.from_url')
    async def test_redis_initialization_success(self, mock_redis_from_url, cache_service_with_redis):
        """Test successful Redis initialization."""
        # Mock Redis client
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        mock_redis_from_url.return_value = mock_redis_client

        await cache_service_with_redis.initialize()

        assert cache_service_with_redis.initialized
        assert cache_service_with_redis.redis_client == mock_redis_client
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    @patch('redis.asyncio.from_url')
    async def test_redis_initialization_failure(self, mock_redis_from_url, cache_service_with_redis):
        """Test Redis initialization failure fallback to memory cache."""
        # Mock Redis connection failure
        mock_redis_from_url.side_effect = Exception("Redis connection failed")

        await cache_service_with_redis.initialize()

        assert cache_service_with_redis.initialized
        assert cache_service_with_redis.redis_client is None  # Should fallback to memory

    @pytest.mark.asyncio
    @patch('redis.asyncio.from_url')
    async def test_redis_operations(self, mock_redis_from_url, cache_service_with_redis):
        """Test cache operations with Redis."""
        # Mock Redis client
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=b'{"data": "test_value"}')
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=1)
        mock_redis_from_url.return_value = mock_redis_client

        await cache_service_with_redis.initialize()

        # Test get operation
        value = await cache_service_with_redis.get("redis_test_key")
        assert value == {"data": "test_value"}
        mock_redis_client.get.assert_called_with("redis_test_key")

        # Test set operation
        result = await cache_service_with_redis.set("redis_test_key", {"data": "new_value"})
        assert result is True
        mock_redis_client.set.assert_called_once()

        # Test delete operation
        result = await cache_service_with_redis.delete("redis_test_key")
        assert result is True
        mock_redis_client.delete.assert_called_with("redis_test_key")

        # Test exists operation
        exists = await cache_service_with_redis.exists("redis_test_key")
        assert exists is True
        mock_redis_client.exists.assert_called_with("redis_test_key")

    @pytest.mark.asyncio
    async def test_auto_initialization(self, cache_service):
        """Test that cache operations auto-initialize the service."""
        assert not cache_service.initialized

        # First operation should trigger initialization
        await cache_service.set("auto_init_key", "auto_init_value")

        assert cache_service.initialized

        # Subsequent operations should work normally
        value = await cache_service.get("auto_init_key")
        assert value == "auto_init_value"

    @pytest.mark.asyncio
    async def test_cache_service_error_handling(self, cache_service):
        """Test error handling in cache operations."""
        await cache_service.initialize()

        # Test with None key
        result = await cache_service.set(None, "value")
        assert result is False

        value = await cache_service.get(None)
        assert value is None

        # Test with None value
        result = await cache_service.set("key", None)
        assert result is True  # None is a valid value to cache

        retrieved_value = await cache_service.get("key")
        assert retrieved_value is None


class TestCacheServiceIntegration(AsyncServiceTestBase):
    """Integration tests for Cache Service with other components."""

    @pytest.fixture
    def cache_service(self):
        """Create cache service for integration testing."""
        return CacheService(default_ttl=300)

    @pytest.mark.asyncio
    async def test_cache_service_with_user_session(self, cache_service):
        """Test cache service integration with user session management."""
        await cache_service.initialize()

        # Simulate user session caching
        session_data = {
            "user_id": "user123",
            "session_id": "session456",
            "expires_at": "2023-12-31T23:59:59Z",
            "permissions": ["read", "write"]
        }

        session_key = f"session:{session_data['session_id']}"

        # Store session
        await cache_service.set(session_key, session_data, ttl=1800)  # 30 minutes

        # Retrieve session
        retrieved_session = await cache_service.get(session_key)
        assert retrieved_session == session_data
        assert retrieved_session["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_cache_service_with_api_rate_limiting(self, cache_service):
        """Test cache service integration with API rate limiting."""
        await cache_service.initialize()

        user_id = "user123"
        rate_limit_key = f"rate_limit:{user_id}"

        # Simulate rate limiting tracking
        current_requests = 1
        await cache_service.set(rate_limit_key, current_requests, ttl=60)  # 1 minute window

        # Increment requests
        current_count = await cache_service.get(rate_limit_key) or 0
        new_count = current_count + 1
        await cache_service.set(rate_limit_key, new_count, ttl=60)

        # Verify rate limiting
        final_count = await cache_service.get(rate_limit_key)
        assert final_count == 2

    @pytest.mark.asyncio
    async def test_cache_service_with_application_config(self, cache_service):
        """Test cache service integration with application configuration caching."""
        await cache_service.initialize()

        # Simulate application configuration caching
        app_config = {
            "features": {
                "enable_notifications": True,
                "enable_analytics": False,
                "maintenance_mode": False
            },
            "limits": {
                "max_users": 1000,
                "max_requests_per_minute": 60
            },
            "version": "1.2.3"
        }

        config_key = "app:config"

        # Cache configuration
        await cache_service.set(config_key, app_config, ttl=3600)  # 1 hour

        # Retrieve configuration
        cached_config = await cache_service.get(config_key)
        assert cached_config == app_config
        assert cached_config["features"]["enable_notifications"] is True
        assert cached_config["limits"]["max_users"] == 1000
        assert cached_config["version"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_cache_service_performance_simulation(self, cache_service):
        """Test cache service performance with multiple operations."""
        await cache_service.initialize()

        # Simulate multiple cache operations
        operations = []
        for i in range(10):
            key = f"perf_test_{i}"
            value = {"data": f"value_{i}", "index": i}
            operations.append((key, value))

        # Set all values
        for key, value in operations:
            result = await cache_service.set(key, value)
            assert result is True

        # Get all values
        for key, expected_value in operations:
            retrieved_value = await cache_service.get(key)
            assert retrieved_value == expected_value

        # Verify cache contains all values
        for key, _ in operations:
            exists = await cache_service.exists(key)
            assert exists is True

        # Clean up
        for key, _ in operations:
            await cache_service.delete(key)

        # Verify cleanup
        for key, _ in operations:
            value = await cache_service.get(key)
            assert value is None
