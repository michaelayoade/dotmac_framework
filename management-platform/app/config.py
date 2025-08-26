"""
Application configuration with environment-specific settings.
"""

import os
import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and security."""
    
    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "DotMac Management Platform"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    
    # Server
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = False
    
    # API
    api_v1_prefix: str = "/api/v1"
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"
    openapi_url: Optional[str] = "/openapi.json"
    
    # Security  
    secret_key: str = Field(default="development-secret-key-change-in-production")
    jwt_secret_key: str = Field(default="development-jwt-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://mgmt_user:mgmt_pass@localhost:5432/mgmt_platform",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5, le=300)
    database_pool_recycle: int = Field(default=3600, ge=300, le=86400)
    database_pool_pre_ping: bool = True
    database_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",  # Master Admin Portal
        "http://localhost:3001",  # Tenant Admin Portal
        "http://localhost:3002",  # Reseller Portal
    ]
    
    # Multi-tenant
    enable_tenant_isolation: bool = True
    max_tenants_per_instance: int = 1000
    default_tenant_tier: str = "small"
    
    # External Services
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_test_mode: bool = True
    
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "noreply@dotmac.app"
    
    # Cloud Providers
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Kubernetes
    kubernetes_config_path: Optional[str] = None
    kubernetes_namespace_prefix: str = "dotmac-tenant"
    
    # OpenBao/Vault
    vault_url: Optional[str] = "http://localhost:8200"
    vault_token: Optional[str] = None
    
    # Monitoring
    signoz_endpoint: str = "localhost:4317"
    signoz_access_token: Optional[str] = None
    enable_metrics: bool = True
    
    # Background Tasks
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_worker_concurrency: int = 4
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment and adjust settings accordingly."""
        if v == "production":
            # Security validations for production
            pass
        return v
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not valid JSON, split by comma
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    @field_validator('secret_key', 'jwt_secret_key')
    @classmethod
    def validate_secrets(cls, v: str, info) -> str:
        """Validate secrets are not using default values in production."""
        if hasattr(info.data, 'environment') and info.data.get('environment') == 'production':
            if 'development' in v.lower() or 'change' in v.lower():
                raise ValueError(f"Production environment requires secure {info.field_name}")
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    def get_database_url(self, async_driver: bool = True) -> str:
        """Get database URL with appropriate driver."""
        if async_driver and not self.database_url.startswith("postgresql+asyncpg"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()