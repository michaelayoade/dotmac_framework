"""
Coverage test for config.py module.
Targets 72 statements with 74% coverage - good potential for improvement.
"""

import pytest
from pydantic_core import ValidationError as PydanticValidationError
from dotmac.core.config import DatabaseConfig, CacheConfig, SecurityConfig, LoggingConfig, RedisConfig


class TestDatabaseConfig:
    """Test DatabaseConfig - improve coverage from 74%."""

    def test_database_config_initialization_valid(self):
        """Test database config with valid URLs."""
        # Test PostgreSQL URL
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        assert config.url == "postgresql://user:pass@localhost/db"
        assert config.echo is False
        assert config.pool_size == 10  # Default value
        assert config.max_overflow == 20
        
        # Test PostgreSQL+asyncpg URL
        config = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/db")
        assert config.url == "postgresql+asyncpg://user:pass@localhost/db"
        
        # Test SQLite URL
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config.url == "sqlite:///test.db"

    def test_database_config_initialization_invalid_url(self):
        """Test database config with invalid URLs."""
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="mysql://invalid")
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="http://invalid")
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="invalid_url")

    def test_database_config_custom_values(self):
        """Test database config with custom values."""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            echo=True,
            pool_size=15,
            max_overflow=30,
            connect_timeout=60,
            command_timeout=120
        )
        
        assert config.echo is True
        assert config.pool_size == 15
        assert config.max_overflow == 30
        assert config.connect_timeout == 60
        assert config.command_timeout == 120

    def test_database_config_pool_size_validation(self):
        """Test pool size validation."""
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="postgresql://user:pass@localhost/db", pool_size=0)
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="postgresql://user:pass@localhost/db", pool_size=101)
        
        # Valid pool sizes
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db", pool_size=1)
        assert config.pool_size == 1
        
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db", pool_size=100)
        assert config.pool_size == 100

    def test_database_config_max_overflow_validation(self):
        """Test max overflow validation."""
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="postgresql://user:pass@localhost/db", max_overflow=-1)
        
        with pytest.raises(PydanticValidationError):
            DatabaseConfig(url="postgresql://user:pass@localhost/db", max_overflow=101)
        
        # Valid max overflow
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db", max_overflow=0)
        assert config.max_overflow == 0
        
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db", max_overflow=100)
        assert config.max_overflow == 100


class TestCacheConfig:
    """Test CacheConfig functionality."""

    def test_cache_config_initialization_memory(self):
        """Test cache config with memory backend."""
        config = CacheConfig(backend="memory")
        
        assert config.backend == "memory"
        assert config.url is None
        assert config.default_timeout == 300
        assert config.max_entries == 1000

    def test_cache_config_initialization_redis(self):
        """Test cache config with Redis backend."""
        config = CacheConfig(backend="redis", url="redis://localhost:6379")
        
        assert config.backend == "redis"
        assert config.url == "redis://localhost:6379"

    def test_cache_config_backend_validation_invalid(self):
        """Test invalid backend validation."""
        with pytest.raises(PydanticValidationError):
            CacheConfig(backend="invalid")
        
        with pytest.raises(PydanticValidationError):
            CacheConfig(backend="memcached")

    def test_cache_config_redis_url_validation(self):
        """Test Redis URL validation."""
        # Redis backend without URL should fail (validator)
        with pytest.raises(PydanticValidationError):
            CacheConfig(backend="redis")
        
        # Valid Redis URL
        config = CacheConfig(backend="redis", url="redis://localhost:6379/0")
        assert config.url == "redis://localhost:6379/0"

    def test_cache_config_timeout_validation(self):
        """Test timeout validation."""
        with pytest.raises(PydanticValidationError):
            CacheConfig(backend="memory", default_timeout=0)
        
        # Valid timeout values
        config = CacheConfig(backend="memory", default_timeout=1)
        assert config.default_timeout == 1
        
        config = CacheConfig(backend="memory", default_timeout=3600)
        assert config.default_timeout == 3600

    def test_cache_config_max_entries_validation(self):
        """Test max entries validation."""
        with pytest.raises(PydanticValidationError):
            CacheConfig(backend="memory", max_entries=0)
        
        # Valid max entries
        config = CacheConfig(backend="memory", max_entries=1)
        assert config.max_entries == 1
        
        config = CacheConfig(backend="memory", max_entries=10000)
        assert config.max_entries == 10000


class TestSecurityConfig:
    """Test SecurityConfig functionality."""

    def test_security_config_initialization(self):
        """Test security config initialization."""
        config = SecurityConfig(secret_key="a" * 32)
        
        assert config.secret_key == "a" * 32
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expiration_minutes == 15
        assert config.password_min_length == 8
        assert config.max_login_attempts == 5

    def test_security_config_secret_key_validation(self):
        """Test secret key validation."""
        # Too short
        with pytest.raises(PydanticValidationError):
            SecurityConfig(secret_key="short")
        
        # Common values
        with pytest.raises(PydanticValidationError):
            SecurityConfig(secret_key="changeme" + "x" * 24)
        
        with pytest.raises(PydanticValidationError):
            SecurityConfig(secret_key="secret" + "x" * 26)
        
        # Valid secret key
        config = SecurityConfig(secret_key="valid_secret_key_that_is_long_enough_12345")
        assert len(config.secret_key) >= 32


class TestRedisConfig:
    """Test RedisConfig functionality."""

    def test_redis_config_initialization(self):
        """Test Redis config initialization."""
        config = RedisConfig()
        
        assert config.url == "redis://localhost:6379/0"
        assert config.pool_size == 10
        assert config.socket_timeout == 30
        assert config.retry_on_timeout is True
        assert config.max_connections == 50

    def test_redis_config_url_validation(self):
        """Test Redis URL validation."""
        with pytest.raises(PydanticValidationError):
            RedisConfig(url="http://invalid")
        
        with pytest.raises(PydanticValidationError):
            RedisConfig(url="mysql://invalid")
        
        # Valid Redis URL
        config = RedisConfig(url="redis://localhost:6380/1")
        assert config.url == "redis://localhost:6380/1"

    def test_redis_config_custom_values(self):
        """Test Redis config with custom values."""
        config = RedisConfig(
            url="redis://custom:6379/2",
            pool_size=20,
            socket_timeout=60,
            max_connections=100
        )
        
        assert config.url == "redis://custom:6379/2"
        assert config.pool_size == 20
        assert config.socket_timeout == 60
        assert config.max_connections == 100


class TestLoggingConfig:
    """Test LoggingConfig functionality."""

    def test_logging_config_initialization(self):
        """Test logging config initialization."""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.include_timestamp is True
        assert config.include_caller is False
        assert config.max_string_length == 1000

    def test_logging_config_level_validation(self):
        """Test log level validation."""
        with pytest.raises(PydanticValidationError):
            LoggingConfig(level="INVALID")
        
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_logging_config_format_validation(self):
        """Test log format validation."""
        with pytest.raises(PydanticValidationError):
            LoggingConfig(format="invalid")
        
        # Valid formats
        for fmt in ["json", "console"]:
            config = LoggingConfig(format=fmt)
            assert config.format == fmt

    def test_logging_config_max_string_length_validation(self):
        """Test max string length validation."""
        with pytest.raises(PydanticValidationError):
            LoggingConfig(max_string_length=99)  # Below minimum
        
        with pytest.raises(PydanticValidationError):
            LoggingConfig(max_string_length=10001)  # Above maximum
        
        # Valid lengths
        config = LoggingConfig(max_string_length=100)
        assert config.max_string_length == 100
        
        config = LoggingConfig(max_string_length=10000)
        assert config.max_string_length == 10000