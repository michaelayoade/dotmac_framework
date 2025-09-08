"""
Production-ready configuration management for DotMac Framework.

Provides secure configuration loading with validation, environment variable
support, and secrets management integration.
"""

from typing import TypeVar

import structlog
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# Using Pydantic v2 - no backward compatibility needed

log = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseSettings)


class CacheConfig(BaseModel):
    """Cache configuration."""

    backend: str = Field(default="memory", pattern=r"^(memory|redis)$")
    url: str | None = Field(default=None)
    default_timeout: int = Field(default=300, ge=1)
    max_entries: int = Field(default=1000, ge=1)

    @field_validator("url", mode="after")
    @classmethod
    def validate_cache_url(cls, v: str | None, info) -> str | None:
        """Validate cache URL when backend is redis."""
        if hasattr(info, "data") and info.data.get("backend") == "redis" and not v:
            msg = "Redis backend requires cache URL"
            raise ValueError(msg)
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=15, ge=1, le=1440)
    password_min_length: int = Field(default=8, ge=6, le=128)
    max_login_attempts: int = Field(default=5, ge=1, le=20)
    lockout_duration_minutes: int = Field(default=15, ge=1, le=1440)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            msg = "Secret key must be at least 32 characters long"
            raise ValueError(msg)
        if v == "changeme" or v.lower() in ["secret", "password", "key"]:
            msg = "Secret key must not be a common value"
            raise ValueError(msg)
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = Field(default="json", pattern=r"^(json|console)$")
    include_timestamp: bool = Field(default=True)
    include_caller: bool = Field(default=False)
    max_string_length: int = Field(default=1000, ge=100, le=10000)


class DatabaseConfig(BaseSettings):
    """Database-specific configuration"""

    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=100, description="Maximum pool overflow")
    echo: bool = Field(default=False, description="Enable SQL query logging")

    # Connection timeouts
    connect_timeout: int = Field(
        default=30, ge=1, le=300, description="Connection timeout in seconds"
    )
    command_timeout: int = Field(default=60, ge=1, le=600, description="Command timeout in seconds")

    # Migration settings
    migration_timeout: int = Field(
        default=300, ge=30, le=1800, description="Migration timeout in seconds"
    )

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://", "sqlite://")):
            msg = "Database URL must be postgresql:// or sqlite://"
            raise ValueError(msg)
        return v


class RedisConfig(BaseSettings):
    """Redis-specific configuration"""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    socket_timeout: int = Field(default=30, ge=1, le=300, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(
        default=30, ge=1, le=300, description="Connection timeout in seconds"
    )
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    max_connections: int = Field(default=50, ge=1, le=1000, description="Maximum connections")

    @field_validator("url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            msg = "Redis URL must start with redis://"
            raise ValueError(msg)
        return v
