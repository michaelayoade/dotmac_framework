"""
Runtime configuration for dotmac_analytics.

Provides configuration management for:
- Environment-based settings
- Database settings
- Cache settings
- Security settings
"""

import os
from typing import Optional

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Max pool overflow")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, description="Pool recycle time in seconds")
    echo: bool = Field(False, description="Enable SQL echo")


class CacheConfig(BaseModel):
    """Cache configuration."""

    redis_url: str = Field("redis://localhost:6379", description="Redis URL")
    default_ttl: int = Field(3600, description="Default TTL in seconds")
    key_prefix: str = Field("analytics:", description="Cache key prefix")


class SecurityConfig(BaseModel):
    """Security configuration."""

    jwt_secret_key: Optional[str] = Field(None, description="JWT secret key")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(24, description="JWT expiration in hours")
    api_key_header: str = Field("X-API-Key", description="API key header name")
    tenant_id_header: str = Field("X-Tenant-ID", description="Tenant ID header name")
    cors_origins: list = Field([], description="CORS allowed origins")
    cors_methods: list = Field(["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    cors_headers: list = Field(["Content-Type", "Authorization", "X-Tenant-ID", "X-API-Key"], description="CORS allowed headers")


class ProcessingConfig(BaseModel):
    """Data processing configuration."""

    batch_size: int = Field(1000, description="Processing batch size")
    max_workers: int = Field(4, description="Max worker processes")
    enable_real_time: bool = Field(True, description="Enable real-time processing")
    retention_days: int = Field(90, description="Data retention period in days")


class RuntimeConfig(BaseModel):
    """Complete runtime configuration."""

    # Environment
    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Debug mode")

    # Service - Using secure defaults
    host: str = Field("127.0.0.1", description="Service host (127.0.0.1 for localhost only, 0.0.0.0 for all interfaces)")
    port: int = Field(8000, description="Service port")
    workers: int = Field(1, description="Number of workers")

    # Components
    database: DatabaseConfig
    cache: CacheConfig
    security: SecurityConfig
    processing: ProcessingConfig


def load_config() -> RuntimeConfig:
    """Load configuration from environment variables."""

    # Database config
    database_config = DatabaseConfig(
        url=os.getenv("DATABASE_URL", "postgresql://localhost/analytics"),
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        echo=os.getenv("DB_ECHO", "false").lower() == "true"
    )

    # Cache config
    cache_config = CacheConfig(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
        key_prefix=os.getenv("CACHE_KEY_PREFIX", "analytics:")
    )

    # Security config
    security_config = SecurityConfig(
        jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
        cors_origins=os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
    )

    # Processing config
    processing_config = ProcessingConfig(
        batch_size=int(os.getenv("PROCESSING_BATCH_SIZE", "1000")),
        max_workers=int(os.getenv("PROCESSING_MAX_WORKERS", "4")),
        enable_real_time=os.getenv("ENABLE_REAL_TIME", "true").lower() == "true"
    )

    return RuntimeConfig(
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        host=os.getenv("HOST", "127.0.0.1"),  # Secure default: localhost only
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("WORKERS", "1")),
        database=database_config,
        cache=cache_config,
        security=security_config,
        processing=processing_config
    )
