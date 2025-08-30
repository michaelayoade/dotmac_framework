"""Application settings and configuration."""

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """ISP Framework specific settings that extend base configuration."""

    # Override defaults for ISP Framework
    app_name: str = Field(
        default="DotMac ISP Framework", description="Application name"
    )
    app_version: str = Field(default="1.0.0", description="Application version")
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8001")),
        description="Server port for ISP Framework",
    )

    # ISP Framework specific settings
    tenant_id: str = Field(default="development", description="Current tenant ID")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database configuration
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:///./isp_framework.db"
        ),
        description="Database connection URL",
    )
    # External services (optional)
    stripe_secret_key: Optional[str] = Field(None, description="Stripe API secret key")
    sendgrid_api_key: Optional[str] = Field(None, description="SendGrid API key")

    # Multi-tenancy settings
    enable_multi_tenancy: bool = Field(
        default=True, description="Enable multi-tenant features"
    )
    max_tenants_per_instance: int = Field(
        default=100, description="Maximum tenants per instance"
    )

    # File upload settings
    max_upload_size: int = Field(
        default=10485760, description="Maximum upload size in bytes"
    )
    upload_directory: str = Field(
        default="uploads", description="Upload directory path"
    )

    # DNS management settings (ISP specific)
    base_domain: str = Field(
        default="dotmac.io", description="Base domain for tenant subdomains"
    )
    dns_strategy: str = Field(default="auto", description="DNS management strategy")
    dns_health_check_interval: int = Field(
        default=300, description="DNS health check interval"
    )

    # Rate limiting settings
    rate_limiting_enabled: bool = Field(
        default=True, description="Enable rate limiting"
    )
    rate_limit_storage_backend: str = Field(
        default="redis", description="Rate limit storage backend (redis/memory)"
    )
    rate_limit_default_per_minute: int = Field(
        default=100, description="Default rate limit per minute"
    )
    rate_limit_auth_per_minute: int = Field(
        default=10, description="Auth endpoint rate limit per minute"
    )
    rate_limit_lockout_threshold: int = Field(
        default=5, description="Failed attempts before lockout"
    )
    rate_limit_lockout_duration: int = Field(
        default=900, description="Lockout duration in seconds"
    )

    @model_validator(mode="after")
    def validate_isp_settings(self):
        """Validate ISP Framework specific settings."""
        # ISP Framework specific validation
        if self.max_tenants_per_instance <= 0:
            raise ValueError("max_tenants_per_instance must be greater than 0")

        if self.dns_health_check_interval <= 0:
            raise ValueError("dns_health_check_interval must be greater than 0")

        if not self.base_domain:
            logger.warning("base_domain should be configured for proper DNS management")

        # Rate limiting validation
        if self.rate_limit_default_per_minute <= 0:
            raise ValueError("rate_limit_default_per_minute must be greater than 0")

        if self.rate_limit_auth_per_minute <= 0:
            raise ValueError("rate_limit_auth_per_minute must be greater than 0")

        if self.rate_limit_storage_backend not in ["redis", "memory"]:
            raise ValueError("rate_limit_storage_backend must be 'redis' or 'memory'")

        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
