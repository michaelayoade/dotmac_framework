"""
Test cases for DotMac Core configuration management.
"""

import pytest
from pydantic import ValidationError

from dotmac.core.config import (
    CacheConfig,
    DatabaseConfig,
    LoggingConfig,
    RedisConfig,
    SecurityConfig,
)


class TestDatabaseConfig:
    """Test DatabaseConfig."""

    def test_valid_postgresql_url(self):
        """Test valid PostgreSQL URL."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost:5432/db")
        assert config.url == "postgresql://user:pass@localhost:5432/db"
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.echo is False

    def test_valid_asyncpg_url(self):
        """Test valid AsyncPG URL."""
        config = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost:5432/db")
        assert config.url == "postgresql+asyncpg://user:pass@localhost:5432/db"

    def test_valid_sqlite_url(self):
        """Test valid SQLite URL."""
        config = DatabaseConfig(url="sqlite:///path/to/db.sqlite")
        assert config.url == "sqlite:///path/to/db.sqlite"

    def test_invalid_database_url(self):
        """Test invalid database URL."""
        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(url="mysql://localhost/db")

        errors = exc_info.value.errors()
        assert any(
            "Database URL must be postgresql:// or sqlite://" in error["msg"] for error in errors
        )

    def test_custom_pool_settings(self):
        """Test custom pool settings."""
        config = DatabaseConfig(
            url="postgresql://localhost/db",
            pool_size=5,
            max_overflow=10,
            pool_timeout=60,
            pool_recycle=1800,
            echo_queries=True,
        )

        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 60
        assert config.pool_recycle == 1800
        assert config.echo_queries is True

    def test_pool_size_validation(self):
        """Test pool size validation."""
        # Valid range
        DatabaseConfig(url="postgresql://localhost/db", pool_size=1)
        DatabaseConfig(url="postgresql://localhost/db", pool_size=100)

        # Invalid range
        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", pool_size=0)

        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", pool_size=101)

    def test_max_overflow_validation(self):
        """Test max overflow validation."""
        # Valid range
        DatabaseConfig(url="postgresql://localhost/db", max_overflow=0)
        DatabaseConfig(url="postgresql://localhost/db", max_overflow=100)

        # Invalid range
        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", max_overflow=-1)

        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", max_overflow=101)

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid range
        DatabaseConfig(url="postgresql://localhost/db", pool_timeout=1)
        DatabaseConfig(url="postgresql://localhost/db", pool_timeout=300)

        # Invalid range
        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", pool_timeout=0)

        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", pool_timeout=301)

    def test_recycle_validation(self):
        """Test pool recycle validation."""
        # Valid range
        DatabaseConfig(url="postgresql://localhost/db", pool_recycle=300)

        # Invalid range
        with pytest.raises(ValidationError):
            DatabaseConfig(url="postgresql://localhost/db", pool_recycle=299)


class TestCacheConfig:
    """Test CacheConfig."""

    def test_memory_cache_defaults(self):
        """Test memory cache defaults."""
        config = CacheConfig()
        assert config.backend == "memory"
        assert config.url is None
        assert config.default_timeout == 300
        assert config.max_entries == 1000

    def test_redis_cache_with_url(self):
        """Test Redis cache with URL."""
        config = CacheConfig(backend="redis", url="redis://localhost:6379/0")
        assert config.backend == "redis"
        assert config.url == "redis://localhost:6379/0"

    def test_redis_cache_without_url(self):
        """Test Redis cache without URL raises error."""
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(backend="redis")

        errors = exc_info.value.errors()
        assert any("Redis backend requires cache URL" in error["msg"] for error in errors)

    def test_invalid_backend(self):
        """Test invalid cache backend."""
        with pytest.raises(ValidationError):
            CacheConfig(backend="memcached")

    def test_custom_settings(self):
        """Test custom cache settings."""
        config = CacheConfig(backend="memory", default_timeout=600, max_entries=2000)

        assert config.default_timeout == 600
        assert config.max_entries == 2000

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid range
        CacheConfig(default_timeout=1)

        # Invalid range
        with pytest.raises(ValidationError):
            CacheConfig(default_timeout=0)

    def test_max_entries_validation(self):
        """Test max entries validation."""
        # Valid range
        CacheConfig(max_entries=1)

        # Invalid range
        with pytest.raises(ValidationError):
            CacheConfig(max_entries=0)


class TestSecurityConfig:
    """Test SecurityConfig."""

    def test_valid_security_config(self):
        """Test valid security configuration."""
        config = SecurityConfig(secret_key="a" * 32)
        assert config.secret_key == "a" * 32
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expiration_minutes == 15
        assert config.password_min_length == 8
        assert config.max_login_attempts == 5
        assert config.lockout_duration_minutes == 15

    def test_custom_security_settings(self):
        """Test custom security settings."""
        config = SecurityConfig(
            secret_key="b" * 64,
            jwt_algorithm="RS256",
            jwt_expiration_minutes=30,
            password_min_length=12,
            max_login_attempts=3,
            lockout_duration_minutes=30,
        )

        assert config.secret_key == "b" * 64
        assert config.jwt_algorithm == "RS256"
        assert config.jwt_expiration_minutes == 30
        assert config.password_min_length == 12
        assert config.max_login_attempts == 3
        assert config.lockout_duration_minutes == 30

    def test_short_secret_key(self):
        """Test short secret key raises error."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityConfig(secret_key="short")

        errors = exc_info.value.errors()
        assert any(
            "Secret key must be at least 32 characters long" in error["msg"] for error in errors
        )

    def test_common_secret_key_values(self):
        """Test common secret key values raise errors."""
        common_keys = ["changeme", "secret", "password", "key"]

        for key in common_keys:
            # Pad to minimum length
            padded_key = key + "x" * (32 - len(key))
            with pytest.raises(ValidationError) as exc_info:
                SecurityConfig(secret_key=padded_key)

            errors = exc_info.value.errors()
            assert any("Secret key must not be a common value" in error["msg"] for error in errors)

    def test_jwt_expiration_validation(self):
        """Test JWT expiration validation."""
        # Valid range
        SecurityConfig(secret_key="a" * 32, jwt_expiration_minutes=1)
        SecurityConfig(secret_key="a" * 32, jwt_expiration_minutes=1440)

        # Invalid range
        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, jwt_expiration_minutes=0)

        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, jwt_expiration_minutes=1441)

    def test_password_length_validation(self):
        """Test password length validation."""
        # Valid range
        SecurityConfig(secret_key="a" * 32, password_min_length=6)
        SecurityConfig(secret_key="a" * 32, password_min_length=128)

        # Invalid range
        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, password_min_length=5)

        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, password_min_length=129)

    def test_max_login_attempts_validation(self):
        """Test max login attempts validation."""
        # Valid range
        SecurityConfig(secret_key="a" * 32, max_login_attempts=1)
        SecurityConfig(secret_key="a" * 32, max_login_attempts=20)

        # Invalid range
        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, max_login_attempts=0)

        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, max_login_attempts=21)

    def test_lockout_duration_validation(self):
        """Test lockout duration validation."""
        # Valid range
        SecurityConfig(secret_key="a" * 32, lockout_duration_minutes=1)
        SecurityConfig(secret_key="a" * 32, lockout_duration_minutes=1440)

        # Invalid range
        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, lockout_duration_minutes=0)

        with pytest.raises(ValidationError):
            SecurityConfig(secret_key="a" * 32, lockout_duration_minutes=1441)


class TestLoggingConfig:
    """Test LoggingConfig."""

    def test_logging_defaults(self):
        """Test logging configuration defaults."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.include_timestamp is True
        assert config.include_caller is False
        assert config.max_string_length == 1000

    def test_custom_logging_settings(self):
        """Test custom logging settings."""
        config = LoggingConfig(
            level="DEBUG",
            format="console",
            include_timestamp=False,
            include_caller=True,
            max_string_length=500,
        )

        assert config.level == "DEBUG"
        assert config.format == "console"
        assert config.include_timestamp is False
        assert config.include_caller is True
        assert config.max_string_length == 500

    def test_valid_log_levels(self):
        """Test valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_invalid_log_level(self):
        """Test invalid log level."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="TRACE")

    def test_valid_formats(self):
        """Test valid log formats."""
        valid_formats = ["json", "console"]

        for format_type in valid_formats:
            config = LoggingConfig(format=format_type)
            assert config.format == format_type

    def test_invalid_format(self):
        """Test invalid log format."""
        with pytest.raises(ValidationError):
            LoggingConfig(format="xml")

    def test_max_string_length_validation(self):
        """Test max string length validation."""
        # Valid range
        LoggingConfig(max_string_length=100)
        LoggingConfig(max_string_length=10000)

        # Invalid range
        with pytest.raises(ValidationError):
            LoggingConfig(max_string_length=99)

        with pytest.raises(ValidationError):
            LoggingConfig(max_string_length=10001)


class TestRedisConfig:
    """Test RedisConfig."""

    def test_redis_defaults(self):
        """Test Redis configuration defaults."""
        config = RedisConfig()
        assert config.url == "redis://localhost:6379/0"
        assert config.pool_size == 10
        assert config.socket_timeout == 30
        assert config.socket_connect_timeout == 30
        assert config.retry_on_timeout is True
        assert config.max_connections == 50

    def test_custom_redis_settings(self):
        """Test custom Redis settings."""
        config = RedisConfig(
            url="redis://redis.example.com:6379/1",
            pool_size=20,
            socket_timeout=60,
            socket_connect_timeout=45,
            retry_on_timeout=False,
            max_connections=100,
        )

        assert config.url == "redis://redis.example.com:6379/1"
        assert config.pool_size == 20
        assert config.socket_timeout == 60
        assert config.socket_connect_timeout == 45
        assert config.retry_on_timeout is False
        assert config.max_connections == 100
