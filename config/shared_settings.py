"""
Shared Configuration Settings for DotMac Framework

This module provides centralized configuration that can be used across
all services in the DotMac Framework (ISP, Management, SDKs).
"""

import logging.config
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class SharedSettings(BaseSettings):
    """Base shared settings for all DotMac Framework services."""

    # Environment and deployment
    environment: str = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Core application settings
    app_name: str = Field(default="DotMac Framework", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")

    # Security settings
    secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY", "dev-secret-key-change-in-production"
        ),
        description="Application secret key",
    )
    jwt_secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY", "jwt-dev-secret-change-in-production"
        ),
        description="JWT secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_hours: int = Field(
        default=24, description="JWT expiration time in hours"
    )

    # Database settings
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost/dotmac_framework",
        ),
        description="Primary database URL",
    )
    database_pool_size: int = Field(
        default=10, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20, description="Database max overflow connections"
    )

    # Redis settings
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(default=10, description="Redis max connections")

    # API settings
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    cors_origins: List[str] = Field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
        ).split(","),
        description="CORS allowed origins",
    )

    # File storage settings
    upload_directory: str = Field(default="uploads", description="Upload directory")
    max_upload_size: int = Field(
        default=104857600, description="Max upload size in bytes (100MB)"
    )

    # Monitoring and observability
    signoz_endpoint: Optional[str] = Field(
        default_factory=lambda: os.getenv("SIGNOZ_ENDPOINT"),
        description="SignOz endpoint for observability",
    )
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")

    # Multi-tenancy
    enable_multi_tenancy: bool = Field(
        default=True, description="Enable multi-tenant features"
    )
    default_tenant_id: str = Field(default="default", description="Default tenant ID")

    # External service integrations
    stripe_secret_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("STRIPE_SECRET_KEY"),
        description="Stripe API secret key",
    )
    sendgrid_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("SENDGRID_API_KEY"),
        description="SendGrid API key",
    )
    twilio_account_sid: Optional[str] = Field(
        default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID"),
        description="Twilio Account SID",
    )
    twilio_auth_token: Optional[str] = Field(
        default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN"),
        description="Twilio Auth Token",
    )

    @field_validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "testing", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("log_level")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    class Config:
        env_file = ".env"
        case_sensitive = False


class ISPSettings(SharedSettings):
    """ISP Framework specific settings."""

    app_name: str = Field(
        default="DotMac ISP Framework", description="ISP Application name"
    )
    port: int = Field(default=8001, description="ISP service port")

    # ISP specific settings
    base_domain: str = Field(default="dotmac.io", description="Base domain for ISP")
    dns_strategy: str = Field(default="auto", description="DNS management strategy")
    radius_secret: str = Field(
        default_factory=lambda: os.getenv("RADIUS_SECRET", "testing123"),
        description="RADIUS shared secret",
    )


class ManagementSettings(SharedSettings):
    """Management Platform specific settings."""

    app_name: str = Field(
        default="DotMac Management Platform", description="Management Application name"
    )
    port: int = Field(default=8002, description="Management service port")

    # Management specific settings
    max_tenants: int = Field(default=1000, description="Maximum tenants")
    tenant_isolation_level: str = Field(
        default="strict", description="Tenant isolation level"
    )


@lru_cache()
def get_shared_settings() -> SharedSettings:
    """Get cached shared settings instance."""
    return SharedSettings()


@lru_cache()
def get_isp_settings() -> ISPSettings:
    """Get cached ISP settings instance."""
    return ISPSettings()


@lru_cache()
def get_management_settings() -> ManagementSettings:
    """Get cached management settings instance."""
    return ManagementSettings()


def setup_logging(config_path: str = None):
    """Setup logging configuration."""
    if config_path is None:
        config_path = Path(__file__).parent / "logging.conf"

    if config_path.exists():
        logging.config.fileConfig(config_path)
    else:
        # Fallback basic configuration
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Initialize logging on import
setup_logging()
