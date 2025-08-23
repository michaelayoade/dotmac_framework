"""Application settings and configuration."""

from functools import lru_cache
from typing import Optional
import os
import secrets
import logging
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application settings
    app_name: str = "DotMac ISP Framework"
    app_version: str = "1.0.0"
    debug: bool = Field(
        default=False,  # CHANGED: Default to False for security
        description="Debug mode - MUST be False in production",
    )
    environment: str = Field(
        default="development", pattern="^(development|staging|production)$"
    )

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # API settings
    api_v1_prefix: str = "/api/v1"
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"
    openapi_url: Optional[str] = "/openapi.json"

    # Database settings
    database_url: str = Field(
        default="sqlite:///./dotmac_isp.db", description="Synchronous database URL"
    )
    async_database_url: str = Field(
        default="sqlite+aiosqlite:///./dotmac_isp.db", description="Asynchronous database URL"
    )

    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and sessions",
    )

    # Security settings - MUST be set via environment variables in production
    jwt_secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_OR_SET_JWT_SECRET_KEY_ENV_VAR",
        min_length=32,
        description="JWT secret key - MUST be set via JWT_SECRET_KEY environment variable in production",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=15,  # Reduced from 30 for security
        description="JWT access token expiration in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, description="JWT refresh token expiration in days"
    )

    # CORS settings - restrictive by default
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",  # Only localhost for development
        description="Allowed CORS origins (comma-separated) - MUST be configured for production",
    )

    # Trusted hosts - restrictive by default
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1",  # Removed wildcard and public IPs
        description="Allowed host headers (comma-separated) - MUST be configured for production",
    )

    # Email settings
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    from_email: Optional[str] = None

    # SMS settings (Twilio)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

    # Payment settings (Stripe)
    stripe_publishable_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # Celery settings
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File upload settings
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    upload_directory: str = "uploads"

    # Pagination settings
    default_page_size: int = 20
    max_page_size: int = 100

    # Rate limiting
    rate_limit_per_minute: int = 100

    # SSL/TLS settings
    ssl_enabled: bool = Field(
        default=False, description="Enable HTTPS with SSL certificates"
    )
    ssl_email: Optional[str] = Field(
        default=None, description="Email for Let's Encrypt certificate registration"
    )
    ssl_domains: str = Field(
        default="", description="Comma-separated list of domains for SSL certificates"
    )
    ssl_cert_dir: str = Field(
        default="/etc/ssl/dotmac", description="Directory to store SSL certificates"
    )

    # Multi-tenancy
    enable_multi_tenancy: bool = True
    tenant_id: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        description="Default tenant ID for this ISP instance",
    )

    # Portal ID Generation Settings
    portal_id_pattern: str = Field(
        default="alphanumeric_clean",
        description="Portal ID generation pattern: alphanumeric_clean, alphanumeric, numeric, custom",
    )
    portal_id_length: int = Field(
        default=8, ge=4, le=20, description="Length of generated Portal IDs"
    )
    portal_id_prefix: str = Field(
        default="",
        max_length=5,
        description="Optional prefix for Portal IDs (e.g., 'CX' for customer)",
    )
    portal_id_custom_charset: str = Field(
        default="ABCDEFGHJKMNPQRSTUVWXYZ23456789",
        description="Custom character set for Portal ID generation (used with 'custom' pattern)",
    )
    portal_id_exclude_ambiguous: bool = Field(
        default=True,
        description="Exclude ambiguous characters (0,O,I,1) from Portal IDs",
    )

    # ===== ENTERPRISE BACKEND INTEGRATIONS =====

    # MinIO S3 Storage Settings
    minio_endpoint: str = Field(
        default="localhost:9002", description="MinIO S3 API endpoint"
    )
    minio_access_key: str = Field(default="dotmacadmin", description="MinIO access key")
    minio_secret_key: str = Field(
        default="dotmacpassword", description="MinIO secret key"
    )
    minio_secure: bool = Field(
        default=False, description="Use HTTPS for MinIO connection"
    )
    minio_default_bucket: str = Field(
        default="dotmac-isp-storage", description="Default MinIO bucket name"
    )

    # SignOz Observability Settings
    signoz_endpoint: str = Field(
        default="localhost:4317", description="SignOz OTLP collector endpoint"
    )
    signoz_access_token: Optional[str] = Field(
        default=None, description="SignOz access token for SaaS deployment"
    )
    enable_observability: bool = Field(
        default=True, description="Enable SignOz observability and tracing"
    )

    # OpenBao Secrets Management
    openbao_url: str = Field(
        default="http://localhost:8200", description="OpenBao/Vault server URL"
    )
    openbao_token: Optional[str] = Field(
        default=None, description="OpenBao authentication token"
    )
    enable_secrets_management: bool = Field(
        default=False, description="Enable OpenBao secrets management"
    )

    # Event Bus Settings
    enable_event_bus: bool = Field(
        default=True, description="Enable Redis-based event bus"
    )
    event_bus_prefix: str = Field(
        default="dotmac:events", description="Redis key prefix for event bus"
    )

    # API Gateway Settings
    enable_rate_limiting: bool = Field(
        default=True, description="Enable API rate limiting"
    )
    default_rate_limit: int = Field(
        default=100, description="Default requests per minute per client"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Get allowed hosts as a list."""
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.database_url.replace("+asyncpg", "").replace("+aiomysql", "")

    @model_validator(mode="after")
    def validate_security_settings(self):
        """Validate critical security settings."""

        # Production security validation
        if self.environment == "production":
            errors = []

            # Debug mode must be False in production
            if self.debug:
                errors.append("DEBUG mode MUST be False in production")

            # JWT secret key must be properly set
            if (
                not self.jwt_secret_key
                or self.jwt_secret_key
                == "CHANGE_ME_IN_PRODUCTION_OR_SET_JWT_SECRET_KEY_ENV_VAR"
                or len(self.jwt_secret_key) < 32
            ):
                errors.append(
                    "JWT_SECRET_KEY must be set to a secure value (32+ characters) in production"
                )

            # CORS origins must be explicitly set (not defaults)
            if self.cors_origins in [
                "http://localhost:3000",
                "http://localhost:3000,http://127.0.0.1:3000",
            ]:
                errors.append(
                    "CORS_ORIGINS must be explicitly configured for production (not localhost)"
                )

            # Allowed hosts must be explicitly set (not defaults)
            if self.allowed_hosts in ["localhost,127.0.0.1"]:
                errors.append(
                    "ALLOWED_HOSTS must be explicitly configured for production (not localhost)"
                )

            # SSL should be enabled in production
            if not self.ssl_enabled:
                logger.warning(
                    "SSL is not enabled in production - consider enabling HTTPS"
                )

            if errors:
                error_msg = "CRITICAL PRODUCTION SECURITY ISSUES:\n" + "\n".join(
                    f"- {error}" for error in errors
                )
                logger.critical(error_msg)
                raise ValueError(error_msg)

        return self

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key strength."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")

        # In production, warn about weak keys
        if v == "CHANGE_ME_IN_PRODUCTION_OR_SET_JWT_SECRET_KEY_ENV_VAR":
            logger.warning(
                "Using default JWT secret key - MUST be changed for production!"
            )

        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        if v not in ["development", "staging", "production"]:
            raise ValueError(
                "Environment must be one of: development, staging, production"
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
