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
        env_file=[".env.development", ".env", ".env.local"],
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
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = False
    
    # API
    api_v1_prefix: str = "/api/v1"
    docs_url: Optional[str] = "/docs"
    redoc_url: Optional[str] = "/redoc"
    openapi_url: Optional[str] = "/openapi.json"
    
    # Security - NO DEFAULTS FOR PRODUCTION SECRETS
    secret_key: str = Field(..., min_length=32, description="Application secret key (required)")
    jwt_secret_key: str = Field(..., min_length=32, description="JWT secret key (required)")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database
    database_url: str = Field(
        ...,
        description="Database connection URL (required)"
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=50)
    database_pool_timeout: int = Field(default=30, ge=5, le=300)
    database_pool_recycle: int = Field(default=3600, ge=300, le=86400)
    database_pool_pre_ping: bool = True
    database_echo: bool = False
    
    # Redis
    redis_url: str = Field(..., description="Redis connection URL (required)")
    redis_max_connections: int = 50
    
    # CORS - Environment-specific origins
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
        description="CORS allowed origins"
    )
    
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
    vault_url: Optional[str] = Field(None, description="Vault URL for secrets management")
    vault_token: Optional[str] = None
    
    # Monitoring
    signoz_endpoint: str = Field(..., description="SignOz endpoint (required)")
    signoz_access_token: Optional[str] = None
    enable_metrics: bool = True
    
    # Background Tasks
    celery_broker_url: str = Field(..., description="Celery broker URL (required)")
    celery_result_backend: str = Field(..., description="Celery result backend URL (required)")
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
        """Validate environment and enforce security requirements."""
        valid_environments = ['development', 'staging', 'production']
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
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
        """Validate secrets meet security requirements."""
        if len(v) < 32:
            raise ValueError(f"Secret keys must be at least 32 characters long")
        
        # Check for common insecure patterns
        insecure_patterns = [
            'development', 'change', 'default', 'secret', 'password',
            '123', 'test', 'demo', 'example', 'placeholder'
        ]
        
        v_lower = v.lower()
        for pattern in insecure_patterns:
            if pattern in v_lower:
                raise ValueError(f"Secret key contains insecure pattern: '{pattern}'")
        
        # Production environment additional checks
        if hasattr(info.data, 'environment') and info.data.get('environment') == 'production':
            if v == info.data.get('jwt_secret_key') if info.field_name == 'secret_key' else v == info.data.get('secret_key'):
                raise ValueError("secret_key and jwt_secret_key must be different in production")
        
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
    
    @property
    def is_secure_deployment(self) -> bool:
        """Check if this is a secure deployment configuration."""
        return (
            self.is_production and 
            len(self.secret_key) >= 32 and
            len(self.jwt_secret_key) >= 32 and
            not any(origin.startswith('http://localhost') for origin in self.cors_origins)
        )
    
    def validate_production_security(self) -> List[str]:
        """Validate production security requirements."""
        issues = []
        
        if self.is_production:
            # Check secret keys
            if len(self.secret_key) < 32:
                issues.append("secret_key must be at least 32 characters for production")
            if len(self.jwt_secret_key) < 32:
                issues.append("jwt_secret_key must be at least 32 characters for production")
            
            # Check CORS origins
            if any(origin.startswith('http://localhost') for origin in self.cors_origins):
                issues.append("CORS origins should not include localhost in production")
            
            # Check database URL
            if 'localhost' in self.database_url:
                issues.append("Database URL should not use localhost in production")
            
            # Check Redis URL
            if 'localhost' in self.redis_url:
                issues.append("Redis URL should not use localhost in production")
        
        return issues


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()