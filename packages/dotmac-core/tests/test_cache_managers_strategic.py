"""
Strategic test coverage for cache managers module.
Targets the largest module (382 statements) with low coverage (19%) for maximum impact.
"""

from unittest.mock import Mock, AsyncMock, patch
from dotmac.core.cache.core.managers import RedisCacheManager, MemoryCacheManager, HybridCacheManager, CacheMetrics


class TestCacheManagers:
    """Test Cache Managers - the largest low-coverage module (382 statements)."""

    @patch('dotmac.core.cache.core.managers.logger')
    def test_redis_cache_manager_initialization(self, mock_logger):
        """Test Redis cache manager initialization."""
        with patch('dotmac.core.cache.core.managers.RedisBackend') as mock_backend:
            mock_backend.return_value = AsyncMock()
            
            config = Mock()
            config.redis_url = "redis://localhost:6379"
            config.default_ttl = 300
            
            manager = RedisCacheManager(config=config)
            
            assert manager is not None
            assert hasattr(manager, 'config')

    @patch('dotmac.core.cache.core.managers.logger')
    def test_memory_cache_manager_initialization(self, mock_logger):
        """Test Memory cache manager initialization."""
        with patch('dotmac.core.cache.core.managers.MemoryBackend') as mock_backend:
            mock_backend.return_value = AsyncMock()
            
            config = Mock()
            config.default_ttl = 300
            
            manager = MemoryCacheManager(config=config)
            
            assert manager is not None
            assert hasattr(manager, 'config')

    @patch('dotmac.core.cache.core.managers.logger')
    def test_hybrid_cache_manager_initialization(self, mock_logger):
        """Test Hybrid cache manager initialization."""
        with patch('dotmac.core.cache.core.managers.RedisBackend') as mock_redis:
            with patch('dotmac.core.cache.core.managers.MemoryBackend') as mock_memory:
                mock_redis.return_value = AsyncMock()
                mock_memory.return_value = AsyncMock()
                
                config = Mock()
                config.redis_url = "redis://localhost:6379"
                config.default_ttl = 300
                config.l1_ttl = 60
                
                manager = HybridCacheManager(config=config)
                
                assert manager is not None
                assert hasattr(manager, 'config')

    def test_cache_metrics_functionality(self):
        """Test CacheMetrics dataclass functionality."""
        metrics = CacheMetrics()
        
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.sets == 0
        assert metrics.deletes == 0
        assert metrics.errors == 0
        assert metrics.hit_rate == 0.0
        
        # Test with some data
        metrics.hits = 80
        metrics.misses = 20
        
        assert metrics.hit_rate == 0.8

    @patch('dotmac.core.cache.core.managers.logger')
    def test_redis_manager_methods_exist(self, mock_logger):
        """Test that core methods exist on RedisCacheManager."""
        with patch('dotmac.core.cache.core.managers.RedisBackend') as mock_backend:
            mock_backend.return_value = AsyncMock()
            
            config = Mock()
            config.redis_url = "redis://localhost:6379"
            config.default_ttl = 300
            
            manager = RedisCacheManager(config=config)
            
            # Check for expected methods
            expected_methods = ['get', 'set', 'delete', 'exists', 'clear']
            for method in expected_methods:
                assert hasattr(manager, method), f"Missing method: {method}"

    @patch('dotmac.core.cache.core.managers.logger')
    def test_memory_manager_methods_exist(self, mock_logger):
        """Test that core methods exist on MemoryCacheManager."""
        with patch('dotmac.core.cache.core.managers.MemoryBackend') as mock_backend:
            mock_backend.return_value = AsyncMock()
            
            config = Mock()
            config.default_ttl = 300
            
            manager = MemoryCacheManager(config=config)
            
            # Check for expected methods
            expected_methods = ['get', 'set', 'delete', 'exists', 'clear']
            for method in expected_methods:
                assert hasattr(manager, method), f"Missing method: {method}"

    @patch('dotmac.core.cache.core.managers.logger')
    def test_hybrid_manager_methods_exist(self, mock_logger):
        """Test that core methods exist on HybridCacheManager."""
        with patch('dotmac.core.cache.core.managers.RedisBackend') as mock_redis:
            with patch('dotmac.core.cache.core.managers.MemoryBackend') as mock_memory:
                mock_redis.return_value = AsyncMock()
                mock_memory.return_value = AsyncMock()
                
                config = Mock()
                config.redis_url = "redis://localhost:6379"
                config.default_ttl = 300
                config.l1_ttl = 60
                
                manager = HybridCacheManager(config=config)
                
                # Check for expected methods
                expected_methods = ['get', 'set', 'delete', 'exists', 'clear']
                for method in expected_methods:
                    assert hasattr(manager, method), f"Missing method: {method}"
