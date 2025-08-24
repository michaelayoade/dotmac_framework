import logging

logger = logging.getLogger(__name__)

"""
Central Secret Management

Centralized, secure secret loading with validation and environment-based configuration.
"""

from functools import lru_cache
from typing import Optional
import os
from pydantic import BaseSettings, Field, field_validator


class Secrets(BaseSettings):
    """
    Centralized secret management with validation
    """

    # JWT Configuration
    jwt_secret: str = Field(..., min_length=32, description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=60, description="JWT expiration in minutes")

    # Database Configuration
    db_password: str = Field(..., min_length=8, description="Database password")
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="dotmac", description="Database name")
    db_user: str = Field(default="dotmac", description="Database user")

    # Redis Configuration
    redis_password: str = Field(..., min_length=8, description="Redis password")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")

    # External Service Keys
    stripe_secret_key: Optional[str] = Field(
        default=None, description="Stripe secret key"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default=None, description="Stripe webhook secret"
    )

    # Encryption Keys
    encryption_key: str = Field(..., min_length=32, description="Data encryption key")
    field_encryption_key: str = Field(
        ..., min_length=32, description="Field-level encryption key"
    )

    # Email Configuration
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")

    class Config:
        """Class for Config operations."""
        env_file = ".env", ".env.local", ".env.production"
        env_file_encoding = "utf-8"
        extra = "forbid"  # Fail on unknown environment variables
        case_sensitive = True

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret strength"""
        forbidden_values = [
            "secret123",
            "development",
            "test",
            "password",
            "jwt_secret",
            "your_secret_here",
            "change_me",
        ]
        if v.lower() in forbidden_values:
            raise ValueError("JWT secret must not be a common/default value")
        return v

    @field_validator("db_password")
    @classmethod
    def validate_db_password(cls, v):
        """Validate database password strength"""
        forbidden_values = [
            "password123",
            "development",
            "test",
            "password",
            "postgres",
            "admin",
            "root",
            "change_me",
        ]
        if v.lower() in forbidden_values:
            raise ValueError("Database password must not be a common/default value")
        return v

    @field_validator("redis_password")
    @classmethod
    def validate_redis_password(cls, v):
        """Validate Redis password strength"""
        forbidden_values = [
            "password123",
            "development",
            "test",
            "password",
            "redis",
            "admin",
            "change_me",
        ]
        if v.lower() in forbidden_values:
            raise ValueError("Redis password must not be a common/default value")
        return v

    def get_database_url(self) -> str:
        """Get complete database URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_redis_url(self) -> str:
        """Get complete Redis URL"""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"


@lru_cache(maxsize=1)
def get_secrets() -> Secrets:
    """
    Get cached secrets instance

    Returns:
        Secrets: Validated secrets configuration
    """
    return Secrets()


def validate_production_secrets():
    """
    Validate that all production secrets are properly configured

    Raises:
        ValueError: If any critical secret is missing or invalid
    """
    try:
        secrets = get_secrets()

        # Check critical secrets are present
        critical_secrets = [
            secrets.jwt_secret,
            secrets.db_password,
            secrets.redis_password,
            secrets.encryption_key,
            secrets.field_encryption_key,
        ]

        for secret in critical_secrets:
            if not secret or len(secret) < 8:
                raise ValueError("Critical secrets must be at least 8 characters long")

        # Validate environment
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            if not secrets.stripe_secret_key:
                raise ValueError("Stripe secret key required in production")
            if not secrets.sentry_dsn:
                raise ValueError("Sentry DSN required in production")

    except Exception as e:
        raise ValueError(f"Secret validation failed: {str(e)}")


if __name__ == "__main__":
    validate_production_secrets()
logger.info("✅ All secrets validated successfully")
