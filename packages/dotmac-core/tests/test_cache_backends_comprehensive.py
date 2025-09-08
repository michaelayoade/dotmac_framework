"""
Comprehensive test coverage for cache backend modules.
This addresses the 0% coverage issue for cache/backends.py and cache/core/backends.py.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from dotmac.core.cache.core.backends import MemoryBackend, RedisBackend, CacheEntry
from dotmac.core.cache.core.config import CacheConfig
from dotmac.core.cache.core.exceptions import CacheConnectionError, CacheError


class TestCacheEntry:
    """Test CacheEntry dataclass functionality."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            value="test_value",
            created_at=time.time(),
            ttl=300
        )
        
        assert entry.value == "test_value"
        assert isinstance(entry.created_at, float)
        assert entry.ttl == 300

    def test_cache_entry_expiration_check(self):
        """Test cache entry expiration logic."""
        current_time = time.time()
        
        # Non-expired entry
        entry = CacheEntry(
            value="test_value",
            created_at=current_time,
            ttl=300
        )
        entry.last_accessed = current_time
        
        # This would be tested in the actual backend implementation
        assert entry.created_at + entry.ttl > current_time

    def test_cache_entry_access_tracking(self):
        """Test last access time tracking."""
        entry = CacheEntry(
            value="test_value", 
            created_at=time.time(),
            ttl=300
        )
        
        access_time = time.time()
        entry.last_accessed = access_time
        
        assert entry.last_accessed == access_time


class TestMemoryBackend:
    """Test MemoryBackend functionality."""

    def test_memory_backend_initialization(self):
        """Test memory backend initialization."""
        config = CacheConfig(backend="memory", max_entries=100)
        backend = MemoryBackend(config)
        
        assert backend.config == config
        assert backend.cache == {}
        assert not backend._connected

    async def test_memory_backend_connect(self):
        """Test memory backend connection."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        
        result = await backend.connect()
        
        assert result is True
        assert backend._connected is True

    async def test_memory_backend_disconnect(self):
        """Test memory backend disconnection."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        
        await backend.connect()
        result = await backend.disconnect()
        
        assert result is True
        assert backend._connected is False

    async def test_memory_backend_is_connected(self):
        """Test connection status checking."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        
        assert backend.is_connected() is False
        
        await backend.connect()
        assert backend.is_connected() is True

    async def test_memory_backend_basic_operations(self):
        """Test basic get/set/delete operations."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        await backend.connect()
        
        # Test set and get
        test_data = b"test_value"
        result = await backend.set_raw("test_key", test_data, ttl=300)
        assert result is True
        
        retrieved = await backend.get_raw("test_key")
        assert retrieved == test_data
        
        # Test exists
        exists = await backend.exists_raw("test_key")
        assert exists is True
        
        # Test delete
        deleted = await backend.delete_raw("test_key")
        assert deleted is True
        
        # Verify deletion
        retrieved_after_delete = await backend.get_raw("test_key")
        assert retrieved_after_delete is None

    async def test_memory_backend_ttl_expiration(self):
        """Test TTL-based expiration."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        await backend.connect()
        
        # Set with very short TTL
        await backend.set_raw("test_key", b"test_value", ttl=1)
        
        # Should exist immediately
        result = await backend.get_raw("test_key")
        assert result == b"test_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired now
        result = await backend.get_raw("test_key")
        assert result is None

    async def test_memory_backend_keys_pattern_matching(self):
        """Test key pattern matching functionality."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        await backend.connect()
        
        # Set up test keys
        await backend.set_raw("user:123", b"value1")
        await backend.set_raw("user:456", b"value2") 
        await backend.set_raw("order:789", b"value3")
        
        # Test pattern matching
        user_keys = await backend.keys_raw("user:*")
        assert "user:123" in user_keys
        assert "user:456" in user_keys
        assert "order:789" not in user_keys
        
        # Test all keys
        all_keys = await backend.keys_raw("*")
        assert len(all_keys) >= 3

    async def test_memory_backend_ping(self):
        """Test ping functionality."""
        config = CacheConfig(backend="memory")
        backend = MemoryBackend(config)
        
        # Should return False when not connected
        result = await backend.ping_raw()
        assert result is False
        
        # Should return True when connected
        await backend.connect()
        result = await backend.ping_raw()
        assert result is True


class TestRedisBackend:
    """Test RedisBackend functionality."""

    def test_redis_backend_unavailable(self):
        """Test Redis backend when Redis is not available."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        
        # Mock Redis as unavailable
        with patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', False):
            with pytest.raises(ImportError, match="redis package required"):
                RedisBackend(config)

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True)
    @patch('dotmac.core.cache.core.backends.aioredis')
    def test_redis_backend_initialization(self, mock_aioredis):
        """Test Redis backend initialization."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        assert backend.config == config
        assert backend.redis is None
        assert backend._connected is False

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True)
    @patch('dotmac.core.cache.core.backends.aioredis')
    async def test_redis_backend_connect_success(self, mock_aioredis):
        """Test successful Redis connection."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        # Mock successful connection
        mock_redis = AsyncMock()
        mock_aioredis.from_url.return_value = mock_redis
        
        result = await backend.connect()
        
        assert result is True
        assert backend._connected is True
        assert backend.redis == mock_redis

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True)
    @patch('dotmac.core.cache.core.backends.aioredis')
    async def test_redis_backend_connect_failure(self, mock_aioredis):
        """Test Redis connection failure."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        # Mock connection failure
        mock_aioredis.from_url.side_effect = Exception("Connection failed")
        
        with pytest.raises(CacheConnectionError, match="Redis connection failed"):
            await backend.connect()

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True)
    @patch('dotmac.core.cache.core.backends.aioredis')
    async def test_redis_backend_disconnect(self, mock_aioredis):
        """Test Redis disconnection."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        # Mock connection
        mock_redis = AsyncMock()
        mock_aioredis.from_url.return_value = mock_redis
        
        await backend.connect()
        result = await backend.disconnect()
        
        assert result is True
        assert backend._connected is False
        assert backend.redis is None
        mock_redis.aclose.assert_called_once()

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True)
    @patch('dotmac.core.cache.core.backends.aioredis')
    async def test_redis_backend_operations_not_connected(self, mock_aioredis):
        """Test Redis operations when not connected."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        # Should raise CacheConnectionError for operations without connection
        with pytest.raises(CacheConnectionError, match="Not connected to Redis"):
            await backend.get_raw("test_key")
            
        with pytest.raises(CacheConnectionError, match="Not connected to Redis"):
            await backend.set_raw("test_key", b"value")
            
        with pytest.raises(CacheConnectionError, match="Not connected to Redis"):
            await backend.delete_raw("test_key")

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True)
    @patch('dotmac.core.cache.core.backends.aioredis')
    async def test_redis_backend_basic_operations(self, mock_aioredis):
        """Test basic Redis operations."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        # Mock Redis connection and operations
        mock_redis = AsyncMock()
        mock_aioredis.from_url.return_value = mock_redis
        
        await backend.connect()
        
        # Test get operation
        mock_redis.get.return_value = b"test_value"
        result = await backend.get_raw("test_key")
        assert result == b"test_value"
        mock_redis.get.assert_called_with("test_key")
        
        # Test set operation  
        mock_redis.set.return_value = True
        result = await backend.set_raw("test_key", b"test_value")
        assert result is True
        mock_redis.set.assert_called_with("test_key", b"test_value")
        
        # Test set with TTL
        mock_redis.setex.return_value = True
        result = await backend.set_raw("test_key", b"test_value", ttl=300)
        assert result is True
        mock_redis.setex.assert_called_with("test_key", 300, b"test_value")
        
        # Test delete operation
        mock_redis.delete.return_value = 1
        result = await backend.delete_raw("test_key")
        assert result is True
        mock_redis.delete.assert_called_with("test_key")

    @patch('dotmac.core.cache.core.backends.REDIS_AVAILABLE', True) 
    @patch('dotmac.core.cache.core.backends.aioredis')
    async def test_redis_backend_error_handling(self, mock_aioredis):
        """Test Redis error handling."""
        config = CacheConfig(backend="redis", redis_url="redis://localhost:6379")
        backend = RedisBackend(config)
        
        # Mock Redis connection
        mock_redis = AsyncMock()
        mock_aioredis.from_url.return_value = mock_redis
        await backend.connect()
        
        # Test Redis connection error
        from dotmac.core import ConnectionError as RedisConnectionError
        mock_redis.get.side_effect = RedisConnectionError("Connection lost")
        
        with pytest.raises(CacheConnectionError, match="Redis get failed"):
            await backend.get_raw("test_key")
        
        assert backend._connected is False  # Should mark as disconnected
        
        # Test general Redis error
        mock_redis.get.side_effect = Exception("Redis error")
        backend._connected = True  # Reset connection status
        
        with pytest.raises(CacheError, match="Redis get operation failed"):
            await backend.get_raw("test_key")


class TestMemoryCache:
    """Test high-level MemoryCache class."""

    def test_memory_cache_initialization(self):
        """Test memory cache initialization."""
        cache = MemoryCache(max_size=100, ttl_seconds=300)
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert cache._cache == {}

    def test_memory_cache_basic_operations(self):
        """Test basic cache operations."""
        cache = MemoryCache(max_size=100, ttl_seconds=300)
        
        # Test set and get
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"
        
        # Test non-existent key
        result = cache.get("non_existent")
        assert result is None
        
        # Test with default value
        result = cache.get("non_existent", "default")
        assert result == "default"

    def test_memory_cache_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = MemoryCache(max_size=100, ttl_seconds=1)
        
        cache.set("test_key", "test_value")
        
        # Should be available immediately
        assert cache.get("test_key") == "test_value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be None after expiration
        assert cache.get("test_key") is None

    def test_memory_cache_size_limit(self):
        """Test cache size limits and eviction."""
        cache = MemoryCache(max_size=2, ttl_seconds=300)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2") 
        assert len(cache._cache) == 2
        
        # Adding third item should trigger eviction
        cache.set("key3", "value3")
        assert len(cache._cache) == 2
        
        # One of the original keys should be evicted
        remaining_keys = list(cache._cache.keys())
        assert "key3" in remaining_keys  # New key should be present

    def test_memory_cache_delete_operation(self):
        """Test cache deletion."""
        cache = MemoryCache(max_size=100, ttl_seconds=300)
        
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        result = cache.delete("test_key")
        assert result is True
        assert cache.get("test_key") is None
        
        # Delete non-existent key
        result = cache.delete("non_existent")
        assert result is False

    def test_memory_cache_clear_operation(self):
        """Test cache clearing."""
        cache = MemoryCache(max_size=100, ttl_seconds=300)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache._cache) == 2
        
        cache.clear()
        assert len(cache._cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRedisCache:
    """Test high-level RedisCache class."""

    @patch('dotmac.core.cache.backends.redis')
    def test_redis_cache_initialization(self, mock_redis):
        """Test Redis cache initialization."""
        mock_redis_client = Mock()
        mock_redis.Redis.return_value = mock_redis_client
        
        cache = RedisCache(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        
        assert cache.client == mock_redis_client
        mock_redis.Redis.assert_called_once_with(
            host="localhost",
            port=6379, 
            db=0,
            decode_responses=True
        )

    @patch('dotmac.core.cache.backends.redis')
    def test_redis_cache_basic_operations(self, mock_redis):
        """Test basic Redis cache operations."""
        mock_redis_client = Mock()
        mock_redis.Redis.return_value = mock_redis_client
        
        cache = RedisCache(host="localhost")
        
        # Test set operation
        cache.set("test_key", "test_value", ttl_seconds=300)
        mock_redis_client.setex.assert_called_once_with("test_key", 300, "test_value")
        
        # Test set without TTL
        cache.set("test_key2", "test_value2")
        mock_redis_client.set.assert_called_once_with("test_key2", "test_value2")
        
        # Test get operation
        mock_redis_client.get.return_value = "test_value"
        result = cache.get("test_key")
        assert result == "test_value"
        mock_redis_client.get.assert_called_with("test_key")

    @patch('dotmac.core.cache.backends.redis')
    def test_redis_cache_delete_operation(self, mock_redis):
        """Test Redis cache deletion."""
        mock_redis_client = Mock()
        mock_redis.Redis.return_value = mock_redis_client
        
        cache = RedisCache(host="localhost")
        
        # Test successful delete
        mock_redis_client.delete.return_value = 1
        result = cache.delete("test_key")
        assert result is True
        
        # Test delete of non-existent key  
        mock_redis_client.delete.return_value = 0
        result = cache.delete("non_existent")
        assert result is False

    @patch('dotmac.core.cache.backends.redis')
    def test_redis_cache_error_handling(self, mock_redis):
        """Test Redis cache error handling."""
        mock_redis_client = Mock()
        mock_redis.Redis.return_value = mock_redis_client
        
        cache = RedisCache(host="localhost")
        
        # Test connection error handling
        mock_redis_client.get.side_effect = Exception("Redis connection failed")
        
        # Should return None on error rather than raising
        result = cache.get("test_key")
        assert result is None
        
        # Test set error handling
        mock_redis_client.set.side_effect = Exception("Redis set failed") 
        
        # Should handle error gracefully
        try:
            cache.set("test_key", "test_value")
        except Exception:
            pytest.fail("Should handle Redis errors gracefully")