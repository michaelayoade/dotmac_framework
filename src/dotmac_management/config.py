"""
Application configuration with environment-specific settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """BaseServiceSettings implementation."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="allow")


class Settings(BaseServiceSettings):
    """Management Platform specific settings that extend base configuration."""

    # Override defaults for Management Platform
    app_name: str = Field(
        default="DotMac Management Platform", description="Application name"
    )
    app_version: str = Field(default="1.0.0", description="Application version")
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    jwt_access_token_expire_minutes: int = Field(
        default=30, description="JWT access token lifetime"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, description="JWT refresh token lifetime"
    )

    # Management Platform specific settings
    reload: bool = Field(default=False, description="Enable auto-reload in development")

    # Multi-tenant management
    enable_tenant_isolation: bool = Field(
        default=True, description="Enable tenant isolation"
    )
    max_tenants_per_instance: int = Field(
        default=1000, description="Maximum tenants per instance"
    )
    default_tenant_tier: str = Field(default="small", description="Default tenant tier")

    # Database configuration
    database_echo: bool = Field(
        default=False, description="Enable database query logging"
    )
    database_pool_size: int = Field(
        default=10, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20, description="Database max overflow connections"
    )
    database_pool_timeout: int = Field(
        default=30, description="Database pool timeout seconds"
    )
    database_pool_recycle: int = Field(
        default=3600, description="Database pool recycle seconds"
    )
    database_pool_pre_ping: bool = Field(
        default=True, description="Enable database pool pre-ping"
    )

    # External Services (Management Platform specific)
    stripe_secret_key: Optional[str] = Field(None, description="Stripe secret key")
    stripe_webhook_secret: Optional[str] = Field(
        None, description="Stripe webhook secret"
    )
    stripe_test_mode: bool = Field(default=True, description="Use Stripe test mode")

    sendgrid_api_key: Optional[str] = Field(None, description="SendGrid API key")
    sendgrid_from_email: str = Field(
        default="noreply@dotmac.app", description="SendGrid from email"
    )

    # Cloud Providers (for tenant deployment)
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(
        None, description="AWS secret access key"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")

    # Kubernetes (for tenant orchestration)
    kubernetes_config_path: Optional[str] = Field(
        None, description="Kubernetes config path"
    )
    kubernetes_namespace_prefix: str = Field(
        default="dotmac-tenant", description="K8s namespace prefix"
    )

    # OpenBao/Vault (for secrets management)
    vault_url: Optional[str] = Field(
        None, description="Vault URL for secrets management"
    )
    vault_token: Optional[str] = Field(None, description="Vault authentication token")

    @field_validator("aws_region")
    @classmethod
    def validate_aws_region(cls, v: str) -> str:
        """Validate AWS region format."""
        if v and not v.startswith(("us-", "eu-", "ap-", "ca-", "sa-")):
            raise ValueError("Invalid AWS region format")
        return v

    @field_validator("kubernetes_namespace_prefix")
    @classmethod
    def validate_k8s_namespace_prefix(cls, v: str) -> str:
        """Validate Kubernetes namespace prefix."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Kubernetes namespace prefix must be alphanumeric with hyphens/underscores"
            )
        return v.lower()

    def validate_management_platform_config(self) -> list[str]:
        """Validate Management Platform specific configuration."""
        issues = []

        # Call base validation
        base_issues = self.validate_production_security()
        issues.extend(base_issues)

        # Management Platform specific validation
        if self.is_production:
            if self.stripe_test_mode:
                issues.append("Stripe should not be in test mode for production")

            if not self.sendgrid_api_key:
                issues.append("SendGrid API key should be configured for production")

            if not self.vault_url:
                issues.append(
                    "Vault URL should be configured for production secrets management"
                )

        return issues

    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database URL with optional async driver."""
        if hasattr(self, "database_url") and self.database_url:
            if async_driver and not self.database_url.startswith(
                ("postgresql+asyncpg", "sqlite+aiosqlite")
            ):
                # Convert to async driver
                if self.database_url.startswith("postgresql://"):
                    return self.database_url.replace(
                        "postgresql://", "postgresql+asyncpg://", 1
                    )
                elif self.database_url.startswith("sqlite://"):
                    return self.database_url.replace(
                        "sqlite://", "sqlite+aiosqlite://", 1
                    )
            return self.database_url

        # Fallback to environment or default
        import os

        db_url = os.getenv("DATABASE_URL", "sqlite:///management_platform.db")
        if async_driver:
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("sqlite://"):
                db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return db_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()
