"""
Configuration management for the DotMac Management Platform.

This module provides centralized configuration management with environment variable
support, validation, and security best practices.
"""

import os
import secrets
from typing import Optional, List
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class SecuritySettings(BaseSettings):
    """Security-related configuration settings."""
    
    # JWT Configuration
    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=60 * 24, 
        description="JWT token expiration time in minutes"
    )
    
    # Password requirements
    password_min_length: int = Field(default=12, description="Minimum password length")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    password_require_lowercase: bool = Field(default=True, description="Require lowercase letters")
    password_require_numbers: bool = Field(default=True, description="Require numbers")
    password_require_special: bool = Field(default=True, description="Require special characters")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Requests per minute per user")
    rate_limit_burst_multiplier: int = Field(default=2, description="Burst capacity multiplier")
    
    # Session security
    session_timeout_minutes: int = Field(default=480, description="Session timeout in minutes")
    max_concurrent_sessions: int = Field(default=5, description="Max concurrent sessions per user")
    
    # Security headers
    enable_security_headers: bool = Field(default=True, description="Enable security headers")
    content_security_policy: str = Field(
        default="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        description="Content Security Policy header"
    )
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        if v == "your-secret-key-here" or len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters and not default value")
        return v
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    database_url: str = Field(
        default="postgresql://mgmt_user:mgmt_password@localhost:5432/mgmt_platform",
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=30, description="Database max overflow connections")
    database_pool_timeout: int = Field(default=30, description="Database pool timeout seconds")
    database_pool_recycle: int = Field(default=3600, description="Database pool recycle seconds")
    
    # Tenant isolation
    enable_row_level_security: bool = Field(default=True, description="Enable PostgreSQL RLS")
    tenant_schema_isolation: bool = Field(default=True, description="Use schema-based tenant isolation")
    
    class Config:
        env_prefix = "DATABASE_"
        case_sensitive = False


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    redis_url: str = Field(
        default="redis://:redis_password@localhost:6379/0",
        description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=50, description="Redis max connections")
    redis_socket_keepalive: bool = Field(default=True, description="Redis socket keepalive")
    redis_socket_keepalive_options: dict = Field(
        default_factory=lambda: {"TCP_KEEPIDLE": 600, "TCP_KEEPINTVL": 60, "TCP_KEEPCNT": 3},
        description="Redis keepalive options"
    )
    
    # Cache settings
    cache_ttl_seconds: int = Field(default=3600, description="Default cache TTL")
    session_cache_ttl_seconds: int = Field(default=28800, description="Session cache TTL")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False


class OpenBaoSettings(BaseSettings):
    """OpenBao secrets management configuration."""
    
    openbao_url: str = Field(default="http://localhost:8200", description="OpenBao server URL")
    openbao_token: Optional[str] = Field(default=None, description="OpenBao authentication token")
    openbao_role_id: Optional[str] = Field(default=None, description="OpenBao role ID for AppRole auth")
    openbao_secret_id: Optional[str] = Field(default=None, description="OpenBao secret ID for AppRole auth")
    
    # Secret management
    secret_rotation_enabled: bool = Field(default=True, description="Enable automatic secret rotation")
    secret_rotation_interval_hours: int = Field(default=168, description="Secret rotation interval (hours)")
    
    # Audit
    audit_enabled: bool = Field(default=True, description="Enable OpenBao audit logging")
    
    class Config:
        env_prefix = "OPENBAO_"
        case_sensitive = False


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""
    
    # SignOz configuration
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", 
        description="OpenTelemetry OTLP endpoint"
    )
    otel_service_name: str = Field(default="mgmt-platform", description="Service name for tracing")
    otel_service_version: str = Field(default="1.0.0", description="Service version for tracing")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json|text)")
    log_audit_enabled: bool = Field(default=True, description="Enable audit logging")
    
    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False


class ApplicationSettings(BaseSettings):
    """General application configuration."""
    
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_workers: int = Field(default=1, description="Number of API workers")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    
    # Request limits
    max_request_size: int = Field(default=10 * 1024 * 1024, description="Max request size in bytes")
    request_timeout_seconds: int = Field(default=30, description="Request timeout seconds")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed = ['development', 'staging', 'production', 'testing']
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False


class ExternalServicesSettings(BaseSettings):
    """External service integration configuration."""
    
    # Stripe payment processing
    stripe_secret_key: Optional[str] = Field(default=None, description="Stripe secret key")
    stripe_webhook_secret: Optional[str] = Field(default=None, description="Stripe webhook secret")
    stripe_test_mode: bool = Field(default=True, description="Use Stripe test mode")
    
    # SendGrid email
    sendgrid_api_key: Optional[str] = Field(default=None, description="SendGrid API key")
    sendgrid_from_email: str = Field(default="noreply@dotmac.app", description="Default from email")
    
    # Twilio SMS
    twilio_account_sid: Optional[str] = Field(default=None, description="Twilio account SID")
    twilio_auth_token: Optional[str] = Field(default=None, description="Twilio auth token")
    twilio_from_number: Optional[str] = Field(default=None, description="Twilio from number")
    
    # Cloud provider credentials (handled via OpenBao in production)
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    azure_client_id: Optional[str] = Field(default=None, description="Azure client ID")
    azure_client_secret: Optional[str] = Field(default=None, description="Azure client secret")
    gcp_service_account_json: Optional[str] = Field(default=None, description="GCP service account JSON")
    
    class Config:
        env_prefix = "EXTERNAL_"
        case_sensitive = False


class Settings(BaseSettings):
    """Main settings class that aggregates all configuration."""
    
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    openbao: OpenBaoSettings = Field(default_factory=OpenBaoSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    external: ExternalServicesSettings = Field(default_factory=ExternalServicesSettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience functions for common settings
def get_security_settings() -> SecuritySettings:
    """Get security settings."""
    return get_settings().security


def get_database_settings() -> DatabaseSettings:
    """Get database settings."""
    return get_settings().database


def get_redis_settings() -> RedisSettings:
    """Get Redis settings."""
    return get_settings().redis


def get_openbao_settings() -> OpenBaoSettings:
    """Get OpenBao settings."""
    return get_settings().openbao


def get_monitoring_settings() -> MonitoringSettings:
    """Get monitoring settings."""
    return get_settings().monitoring


def get_app_settings() -> ApplicationSettings:
    """Get application settings."""
    return get_settings().app


def get_external_settings() -> ExternalServicesSettings:
    """Get external services settings."""
    return get_settings().external


# Environment validation
def validate_production_config() -> List[str]:
    """
    Validate configuration for production deployment.
    
    Returns:
        List of validation errors
    """
    errors = []
    settings = get_settings()
    
    if settings.app.environment == "production":
        # Security validation
        if len(settings.security.jwt_secret_key) < 32:
            errors.append("JWT secret key must be at least 32 characters in production")
        
        if settings.app.debug:
            errors.append("Debug mode must be disabled in production")
        
        # Database validation
        if "localhost" in settings.database.database_url:
            errors.append("Database URL should not use localhost in production")
        
        # Redis validation
        if "localhost" in settings.redis.redis_url:
            errors.append("Redis URL should not use localhost in production")
        
        # External services validation
        if not settings.external.stripe_secret_key:
            errors.append("Stripe secret key is required in production")
        
        if not settings.external.sendgrid_api_key:
            errors.append("SendGrid API key is required in production")
        
        # OpenBao validation
        if "localhost" in settings.openbao.openbao_url:
            errors.append("OpenBao URL should not use localhost in production")
        
        if not settings.openbao.openbao_token and not settings.openbao.openbao_role_id:
            errors.append("OpenBao authentication must be configured in production")
    
    return errors