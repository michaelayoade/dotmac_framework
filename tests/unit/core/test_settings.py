"""
Test settings and configuration.
"""

import os
from unittest.mock import patch

import pytest
from dotmac_isp.core.settings import Settings, get_settings


class TestSettings:
    """Test settings configuration."""

    def test_settings_default_values(self):
        """Test default settings values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            # Test default values
            assert settings.app_name == "DotMac ISP Framework"
            assert settings.app_version == "1.0.0"
            assert settings.debug is False
            assert settings.tenant_id == "development"
            assert settings.database_url == "sqlite+aiosqlite:///./isp_framework.db"
            assert settings.port == 8001

    def test_settings_environment_override(self):
        """Test settings can be overridden by environment variables."""
        with patch.dict(
            os.environ,
            {
                "DEBUG": "true",
                "DATABASE_URL": "postgresql://test:test@localhost/test_db",
                "PORT": "9000",
                "TENANT_ID": "test_tenant",
            },
        ):
            settings = Settings()

            assert settings.debug is True
            assert settings.database_url == "postgresql://test:test@localhost/test_db"
            assert settings.port == 9000
            assert settings.tenant_id == "test_tenant"

    def test_settings_isp_specific_defaults(self):
        """Test ISP-specific default settings."""
        settings = Settings()

        assert settings.enable_multi_tenancy is True
        assert settings.max_tenants_per_instance == 100
        assert settings.base_domain == "dotmac.io"
        assert settings.dns_strategy == "auto"
        assert settings.rate_limiting_enabled is True

    def test_settings_validation_positive(self):
        """Test settings validation with valid values."""
        settings = Settings(
            max_tenants_per_instance=50,
            dns_health_check_interval=600,
            rate_limit_default_per_minute=200,
            rate_limit_auth_per_minute=20,
            rate_limit_storage_backend="redis",
        )

        # Should not raise any validation errors
        assert settings.max_tenants_per_instance == 50
        assert settings.dns_health_check_interval == 600

    def test_settings_validation_negative(self):
        """Test settings validation with invalid values."""
        # Test max_tenants_per_instance validation
        with pytest.raises(
            ValueError, match="max_tenants_per_instance must be greater than 0"
        ):
            Settings(max_tenants_per_instance=0)

        # Test dns_health_check_interval validation
        with pytest.raises(
            ValueError, match="dns_health_check_interval must be greater than 0"
        ):
            Settings(dns_health_check_interval=0)

        # Test rate limit validation
        with pytest.raises(
            ValueError, match="rate_limit_default_per_minute must be greater than 0"
        ):
            Settings(rate_limit_default_per_minute=0)

        # Test invalid storage backend
        with pytest.raises(
            ValueError, match="rate_limit_storage_backend must be 'redis' or 'memory'"
        ):
            Settings(rate_limit_storage_backend="invalid")

    def test_get_settings_cached(self):
        """Test get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same cached instance
        assert settings1 is settings2

    def test_file_upload_settings(self):
        """Test file upload configuration."""
        settings = Settings()

        assert settings.max_upload_size == 10485760  # 10MB
        assert settings.upload_directory == "uploads"

    def test_external_service_settings(self):
        """Test external service configuration."""
        settings = Settings()

        # These should be None by default
        assert settings.stripe_secret_key is None
        assert settings.sendgrid_api_key is None

        # Test with environment variables
        with patch.dict(
            os.environ,
            {"STRIPE_SECRET_KEY": "sk_test_123", "SENDGRID_API_KEY": "SG.test123"},
        ):
            settings = Settings()
            assert settings.stripe_secret_key == "sk_test_123"
            assert settings.sendgrid_api_key == "SG.test123"

    def test_rate_limiting_configuration(self):
        """Test rate limiting configuration."""
        settings = Settings()

        assert settings.rate_limiting_enabled is True
        assert settings.rate_limit_storage_backend == "redis"
        assert settings.rate_limit_default_per_minute == 100
        assert settings.rate_limit_auth_per_minute == 10
        assert settings.rate_limit_lockout_threshold == 5
        assert settings.rate_limit_lockout_duration == 900
