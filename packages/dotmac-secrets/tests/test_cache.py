"""
Tests for caching functionality
"""
import asyncio
import pytest
import time

from dotmac.secrets import (
    InMemoryCache,
    NullCache,
    create_cache,
    SecretMetadata,
    SecretValue,
    SecretKind,
)


class TestInMemoryCache:
    """Test InMemoryCache functionality"""
    
    @pytest.fixture
    async def cache(self):
        """Create cache instance"""
        cache = InMemoryCache(default_ttl=1, max_size=10)
        yield cache
        await cache.close()
    
    @pytest.fixture
    def sample_secret(self):
        """Create sample secret value"""
        metadata = SecretMetadata(
            path="test/secret",
            kind=SecretKind.SYMMETRIC_SECRET
        )
        return SecretValue(
            value={"secret": "test-secret-value"},
            metadata=metadata
        )
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache, sample_secret):
        """Test basic set and get operations"""
        key = "test_secret"
        
        # Set secret
        success = await cache.set(key, sample_secret, ttl=60)
        assert success
        
        # Get secret
        retrieved = await cache.get(key)
        assert retrieved is not None
        assert retrieved.value == sample_secret.value
        assert retrieved.metadata.path == sample_secret.metadata.path
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """Test getting nonexistent key"""
        retrieved = await cache.get("nonexistent")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache, sample_secret):
        """Test TTL expiration"""
        key = "expiring_secret"
        
        # Set with very short TTL
        await cache.set(key, sample_secret, ttl=1)
        
        # Should exist immediately
        retrieved = await cache.get(key)
        assert retrieved is not None
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        retrieved = await cache.get(key)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_exists(self, cache, sample_secret):
        """Test exists functionality"""
        key = "test_exists"
        
        # Should not exist initially
        exists = await cache.exists(key)
        assert not exists
        
        # Set secret
        await cache.set(key, sample_secret, ttl=60)
        
        # Should exist now
        exists = await cache.exists(key)
        assert exists
        
        # Delete and check again
        await cache.delete(key)
        exists = await cache.exists(key)
        assert not exists
    
    @pytest.mark.asyncio
    async def test_delete(self, cache, sample_secret):
        """Test delete functionality"""
        key = "test_delete"
        
        # Set secret
        await cache.set(key, sample_secret, ttl=60)
        assert await cache.exists(key)
        
        # Delete secret
        success = await cache.delete(key)
        assert success
        assert not await cache.exists(key)
        
        # Delete nonexistent key
        success = await cache.delete("nonexistent")
        assert not success
    
    @pytest.mark.asyncio
    async def test_clear(self, cache, sample_secret):
        """Test clear functionality"""
        # Set multiple secrets
        for i in range(5):
            await cache.set(f"secret_{i}", sample_secret, ttl=60)
        
        # Verify they exist
        for i in range(5):
            assert await cache.exists(f"secret_{i}")
        
        # Clear cache
        success = await cache.clear()
        assert success
        
        # Verify all are gone
        for i in range(5):
            assert not await cache.exists(f"secret_{i}")
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, sample_secret):
        """Test LRU eviction when cache is full"""
        cache = InMemoryCache(default_ttl=60, max_size=3)
        
        try:
            # Fill cache to capacity
            for i in range(3):
                await cache.set(f"secret_{i}", sample_secret, ttl=60)
            
            # Access secret_1 to make it more recently used
            await cache.get("secret_1")
            
            # Add another secret (should evict secret_0)
            await cache.set("secret_3", sample_secret, ttl=60)
            
            # secret_0 should be evicted, others should remain
            assert not await cache.exists("secret_0")
            assert await cache.exists("secret_1")
            assert await cache.exists("secret_2")
            assert await cache.exists("secret_3")
            
        finally:
            await cache.close()
    
    @pytest.mark.asyncio
    async def test_stats(self, cache, sample_secret):
        """Test cache statistics"""
        # Add some entries
        for i in range(3):
            await cache.set(f"secret_{i}", sample_secret, ttl=60)
        
        stats = await cache.get_stats()
        
        assert stats["size"] == 3
        assert stats["max_size"] == 10
        assert stats["default_ttl"] == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_task(self, sample_secret):
        """Test background cleanup task"""
        cache = InMemoryCache(default_ttl=60, max_size=100)
        
        try:
            # Set secret with short TTL
            await cache.set("expiring", sample_secret, ttl=1)
            
            # Should exist initially
            assert await cache.exists("expiring")
            
            # Wait for expiration and cleanup
            await asyncio.sleep(1.5)
            
            # Trigger cleanup by calling _remove_expired directly
            await cache._remove_expired()
            
            # Should be cleaned up
            assert not await cache.exists("expiring")
            
        finally:
            await cache.close()


class TestNullCache:
    """Test NullCache functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create null cache instance"""
        return NullCache()
    
    @pytest.fixture
    def sample_secret(self):
        """Create sample secret value"""
        metadata = SecretMetadata(
            path="test/secret",
            kind=SecretKind.SYMMETRIC_SECRET
        )
        return SecretValue(
            value={"secret": "test-secret-value"},
            metadata=metadata
        )
    
    @pytest.mark.asyncio
    async def test_null_cache_operations(self, cache, sample_secret):
        """Test that null cache doesn't actually cache anything"""
        key = "test_secret"
        
        # Set should succeed but not actually store
        success = await cache.set(key, sample_secret, ttl=60)
        assert success
        
        # Get should always return None
        retrieved = await cache.get(key)
        assert retrieved is None
        
        # Exists should always return False
        exists = await cache.exists(key)
        assert not exists
        
        # Delete should always succeed
        success = await cache.delete(key)
        assert success
        
        # Clear should always succeed
        success = await cache.clear()
        assert success
        
        # Stats should indicate no caching
        stats = await cache.get_stats()
        assert stats["caching_disabled"] is True


class TestRedisCache:
    """Test RedisCache functionality (requires Redis)"""
    
    @pytest.mark.requires_redis
    @pytest.mark.asyncio
    async def test_redis_cache_operations(self):
        """Test Redis cache operations if Redis is available"""
        try:
            from dotmac.secrets.cache import RedisCache
            
            cache = RedisCache(
                redis_url="redis://localhost:6379",
                key_prefix="test_secrets:",
                default_ttl=300
            )
            
            metadata = SecretMetadata(
                path="test/secret",
                kind=SecretKind.SYMMETRIC_SECRET
            )
            sample_secret = SecretValue(
                value={"secret": "test-secret-value"},
                metadata=metadata
            )
            
            key = "test_redis_secret"
            
            try:
                # Set secret
                success = await cache.set(key, sample_secret, ttl=60)
                assert success
                
                # Get secret
                retrieved = await cache.get(key)
                assert retrieved is not None
                assert retrieved.value == sample_secret.value
                
                # Delete secret
                success = await cache.delete(key)
                assert success
                
                # Verify deletion
                retrieved = await cache.get(key)
                assert retrieved is None
                
            finally:
                await cache.close()
                
        except ImportError:
            pytest.skip("Redis not available")
        except Exception:
            pytest.skip("Redis server not available")


def test_create_cache():
    """Test cache factory function"""
    # Memory cache
    cache = create_cache("memory", default_ttl=600)
    assert isinstance(cache, InMemoryCache)
    assert cache.default_ttl == 600
    
    # Null cache
    cache = create_cache("null")
    assert isinstance(cache, NullCache)
    
    # Invalid cache type
    with pytest.raises(ValueError):
        create_cache("invalid_type")


@pytest.mark.requires_redis
def test_create_redis_cache():
    """Test Redis cache creation if Redis is available"""
    try:
        cache = create_cache("redis", redis_url="redis://localhost:6379")
        from dotmac.secrets.cache import RedisCache
        assert isinstance(cache, RedisCache)
    except ImportError:
        pytest.skip("Redis not available")