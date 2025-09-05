"""
Test core functionality - Clean, focused unit tests.
"""



from tests.utilities.test_helpers import MockRedisManager, create_mock_settings


class TestCacheSystem:
    """Test the cache system functionality."""

    def test_cache_initialization(self):
        """Test cache system initializes correctly."""
        mock_redis = MockRedisManager()
        assert mock_redis.ping() is True

    def test_cache_set_get(self):
        """Test basic cache operations."""
        mock_redis = MockRedisManager()

        # Test set
        result = mock_redis.set("test_key", "test_value")
        assert result is True

        # Test get
        value = mock_redis.get("test_key")
        assert value == "test_value"

    def test_cache_delete(self):
        """Test cache deletion."""
        mock_redis = MockRedisManager()

        # Set a value
        mock_redis.set("test_key", "test_value")

        # Delete it
        result = mock_redis.delete("test_key")
        assert result is True

        # Verify it's gone
        value = mock_redis.get("test_key")
        assert value is None


class TestSettingsConfiguration:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings are correct."""
        settings = create_mock_settings()

        assert settings.environment == "testing"
        assert settings.debug is False
        assert "test.db" in settings.database_url

    def test_settings_override(self):
        """Test settings can be overridden."""
        settings = create_mock_settings(debug=True, environment="development")

        assert settings.debug is True
        assert settings.environment == "development"
