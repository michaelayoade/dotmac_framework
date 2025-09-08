"""
Application Configuration with OpenBao Integration
=================================================
Provides a centralized configuration system that integrates with OpenBao
for secure secret management across the entire DotMac Framework.
"""

import os
from functools import lru_cache
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from .secure_config import get_config_manager


class DatabaseConfig(BaseSettings):
    """Database configuration with OpenBao integration"""

    async def get_primary_url(self) -> str:
        """Get primary database URL from OpenBao or environment"""
        config_manager = get_config_manager()
        return await config_manager.get_secret(path="database/primary_url", env_fallback="DATABASE_URL", required=True)

    async def get_readonly_url(self) -> str:
        """Get readonly database URL from OpenBao or environment"""
        config_manager = get_config_manager()
        return (
            await config_manager.get_secret(
                path="database/readonly_url",
                env_fallback="DATABASE_READONLY_URL",
                required=False,
            )
            or await self.get_primary_url()
        )

    max_connections: int = Field(default=20, description="Maximum database connections")
    pool_timeout: int = Field(default=30, description="Connection pool timeout")
    ssl_mode: str = Field(default="prefer", description="SSL mode for database connections")


class CacheConfig(BaseSettings):
    """Redis cache configuration with OpenBao integration"""

    async def get_redis_url(self) -> str:
        """Get Redis URL from OpenBao or environment"""
        config_manager = get_config_manager()
        return (
            await config_manager.get_secret(path="cache/redis_url", env_fallback="REDIS_URL", required=False)
            or "redis://localhost:6379/0"
        )

    max_connections: int = Field(default=50, description="Maximum Redis connections")
    timeout: int = Field(default=30, description="Redis operation timeout")
    key_prefix: str = Field(default="dotmac:", description="Cache key prefix")


class SecurityConfig(BaseSettings):
    """Security configuration with OpenBao integration"""

    async def get_jwt_secret(self) -> str:
        """Get JWT secret from OpenBao or environment"""
        config_manager = get_config_manager()
        return await config_manager.get_secret(path="auth/jwt_secret_key", env_fallback="JWT_SECRET_KEY", required=True)

    async def get_encryption_key(self) -> str:
        """Get field encryption key from OpenBao or environment"""
        config_manager = get_config_manager()
        return await config_manager.get_secret(
            path="security/field_encryption_key",
            env_fallback="FIELD_ENCRYPTION_KEY",
            required=True,
        )

    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiry_hours: int = Field(default=24, description="JWT token expiry in hours")
    session_timeout_minutes: int = Field(default=480, description="Session timeout")
    max_failed_attempts: int = Field(default=5, description="Max failed login attempts")
    lockout_duration_minutes: int = Field(default=30, description="Account lockout duration")


class ObservabilityConfig(BaseSettings):
    """Observability and monitoring configuration"""

    otel_endpoint: str = Field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        description="OpenTelemetry collector endpoint",
    )

    otel_service_name: str = Field(
        default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "dotmac-framework"),
        description="OpenTelemetry service name",
    )

    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level",
    )

    metrics_enabled: bool = Field(
        default_factory=lambda: os.getenv("METRICS_ENABLED", "true").lower() == "true",
        description="Enable metrics collection",
    )

    tracing_enabled: bool = Field(
        default_factory=lambda: os.getenv("TRACING_ENABLED", "true").lower() == "true",
        description="Enable distributed tracing",
    )


class DotMacConfig(BaseSettings):
    """
    Main application configuration that integrates all subsystem configurations
    with OpenBao secrets management.
    """

    # Environment
    environment: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development"),
        description="Application environment",
    )

    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true",
        description="Debug mode",
    )

    # Subsystem configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    # OpenBao configuration
    openbao_enabled: bool = Field(
        default_factory=lambda: os.getenv("OPENBAO_ENABLED", "true").lower() == "true",
        description="Enable OpenBao secrets management",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment.lower() == "testing"

    async def initialize_secrets(self) -> bool:
        """
        Initialize secrets in OpenBao for development/testing environments.
        Only runs if OpenBao is enabled and not in production.
        """
        if self.is_production or not self.openbao_enabled:
            return False

        try:
            from .secure_config import initialize_development_secrets

            await initialize_development_secrets()
            logger.info("Development secrets initialized in OpenBao")
            return True
        except Exception as e:
            logger.warning(f"Could not initialize development secrets: {e}")
            return False

    async def get_database_urls(self) -> dict[str, str]:
        """Get all database URLs"""
        return {
            "primary": await self.database.get_primary_url(),
            "readonly": await self.database.get_readonly_url(),
        }

    async def get_cache_url(self) -> str:
        """Get cache URL"""
        return await self.cache.get_redis_url()

    async def get_security_config(self) -> dict[str, Any]:
        """Get security configuration with secrets"""
        return {
            "jwt_secret": await self.security.get_jwt_secret(),
            "jwt_algorithm": self.security.jwt_algorithm,
            "jwt_expiry_hours": self.security.jwt_expiry_hours,
            "encryption_key": await self.security.get_encryption_key(),
            "session_timeout_minutes": self.security.session_timeout_minutes,
            "max_failed_attempts": self.security.max_failed_attempts,
            "lockout_duration_minutes": self.security.lockout_duration_minutes,
        }

    model_config = SettingsConfigDict(
        env_prefix="DOTMAC_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )


# Global configuration instance
_config: Optional[DotMacConfig] = None


@lru_cache
def get_config() -> DotMacConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = DotMacConfig()
        logger.info(f"Configuration loaded for environment: {_config.environment}")
    return _config


async def initialize_application_config() -> DotMacConfig:
    """
    Initialize application configuration with secrets.
    Call this during application startup.
    """
    config = get_config()

    if config.is_development or config.is_testing:
        await config.initialize_secrets()

    return config
