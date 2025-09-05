"""
Configuration management for DotMac applications.

Provides centralized settings management with environment variable support,
type validation, and hierarchical configuration loading.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DotMacSettings(BaseSettings):
    """Core DotMac framework settings with environment variable support."""

    # Application settings
    app_name: str = Field(default="DotMac ISP Framework", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=False, alias="RELOAD")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./dotmac.db", alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")

    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production", alias="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"], alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    # Monitoring settings
    monitoring_enabled: bool = Field(default=True, alias="MONITORING_ENABLED")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    tracing_enabled: bool = Field(default=False, alias="TRACING_ENABLED")

    # SignOz settings
    signoz_endpoint: Optional[str] = Field(default=None, alias="SIGNOZ_ENDPOINT")
    signoz_access_token: Optional[str] = Field(
        default=None, alias="SIGNOZ_ACCESS_TOKEN"
    )

    # File upload settings
    upload_directory: str = Field(default="./uploads", alias="UPLOAD_DIRECTORY")
    max_upload_size: int = Field(
        default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE"
    )  # 10MB

    # Cache settings
    cache_ttl: int = Field(default=300, alias="CACHE_TTL")  # 5 minutes
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")

    # Multi-tenant settings
    tenant_isolation_enabled: bool = Field(
        default=True, alias="TENANT_ISOLATION_ENABLED"
    )
    default_tenant_id: str = Field(default="default", alias="DEFAULT_TENANT_ID")

    # Plugin settings
    plugin_directory: str = Field(default="./plugins", alias="PLUGIN_DIRECTORY")
    plugin_auto_discovery: bool = Field(default=True, alias="PLUGIN_AUTO_DISCOVERY")

    # Business logic settings
    billing_currency: str = Field(default="USD", alias="BILLING_CURRENCY")
    billing_tax_rate: float = Field(default=0.08, alias="BILLING_TAX_RATE")  # 8%

    # Network monitoring settings
    snmp_community: str = Field(default="public", alias="SNMP_COMMUNITY")
    snmp_port: int = Field(default=161, alias="SNMP_PORT")
    monitoring_interval: int = Field(
        default=300, alias="MONITORING_INTERVAL"
    )  # 5 minutes

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment.lower() == "testing"

    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            "url": self.database_url,
            "echo": self.database_echo,
            "pool_size": self.database_pool_size,
        }

    def get_redis_config(self) -> dict[str, Any]:
        """Get Redis configuration dictionary."""
        config = {"url": self.redis_url}
        if self.redis_password:
            config["password"] = self.redis_password
        return config

    def get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration dictionary."""
        return {
            "origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    def get_monitoring_config(self) -> dict[str, Any]:
        """Get monitoring configuration dictionary."""
        return {
            "enabled": self.monitoring_enabled,
            "metrics_enabled": self.metrics_enabled,
            "tracing_enabled": self.tracing_enabled,
            "signoz_endpoint": self.signoz_endpoint,
            "signoz_access_token": self.signoz_access_token,
        }

    def ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.upload_directory,
            self.plugin_directory,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")


# Global settings instance
_settings: Optional[DotMacSettings] = None


@lru_cache
def get_settings() -> DotMacSettings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = DotMacSettings()
        _settings.ensure_directories()
        logger.info(f"Settings loaded for environment: {_settings.environment}")
    return _settings


def reload_settings() -> DotMacSettings:
    """Reload settings (useful for testing)."""
    global _settings
    _settings = None
    get_settings.cache_clear()
    return get_settings()


def get_setting(key: str, default: Any = None) -> Any:
    """Get individual setting by key."""
    settings = get_settings()
    return getattr(settings, key, default)


def update_setting(key: str, value: Any):
    """Update individual setting (runtime only)."""
    settings = get_settings()
    if hasattr(settings, key):
        setattr(settings, key, value)
        logger.info(f"Setting updated: {key} = {value}")
    else:
        logger.warning(f"Unknown setting key: {key}")
