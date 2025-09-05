"""
Production-ready configuration management for DotMac Framework.

Provides secure configuration loading with validation, environment variable
support, and secrets management integration.
"""

from typing import Any, TypeVar

import structlog
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from pydantic_settings import BaseSettings as SettingsBase

    PYDANTIC_V2 = True
except ImportError:
    PYDANTIC_V2 = False

log = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseSettings)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_recycle: int = Field(default=3600, ge=300)
    echo_queries: bool = Field(default=False)

    @field_validator("url")
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://", "sqlite://")):
            raise ValueError("Database URL must be postgresql:// or sqlite://")
        return v


class CacheConfig(BaseModel):
    """Cache configuration."""

    backend: str = Field(default="memory", pattern=r"^(memory|redis)$")
    url: str | None = Field(default=None)
    default_timeout: int = Field(default=300, ge=1)
    max_entries: int = Field(default=1000, ge=1)

    @field_validator("url")
    def validate_cache_url(cls, v: str | None, values: dict[str, Any]) -> str | None:
        """Validate cache URL when backend is redis."""
        if values.get("backend") == "redis" and not v:
            raise ValueError("Redis backend requires cache URL")
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
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        if v == "changeme" or v.lower() in ["secret", "password", "key"]:
            raise ValueError("Secret key must not be a common value")
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

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(env_prefix="DB_")
    else:
        model_config = ConfigDict(env_prefix="DB_")
    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    echo: bool = Field(default=False, description="Enable SQL query logging")

    # Connection timeouts
    connect_timeout: int = Field(default=30, description="Connection timeout in seconds")
    command_timeout: int = Field(default=60, description="Command timeout in seconds")

    # Migration settings
    migration_timeout: int = Field(default=300, description="Migration timeout in seconds")


class RedisConfig(BaseSettings):
    """Redis-specific configuration"""

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(env_prefix="REDIS_")
    else:
        model_config = ConfigDict(env_prefix="REDIS_")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    socket_timeout: int = Field(default=30, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(default=30, description="Connection timeout in seconds")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    max_connections: int = Field(default=50, description="Maximum connections")
