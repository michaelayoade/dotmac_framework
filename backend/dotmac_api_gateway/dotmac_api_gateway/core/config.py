"""
Configuration management for DotMac API Gateway.
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field


class GatewayServerConfig(BaseModel):
    """Gateway server configuration."""

    host: str = Field("127.0.0.1", description="Gateway host (secure default: localhost only)")
    port: int = Field(8080, description="Gateway port")
    workers: int = Field(4, description="Number of workers")
    enable_docs: bool = Field(True, description="Enable API documentation")
    enable_health_check: bool = Field(True, description="Enable health check endpoint")


class AuthenticationConfig(BaseModel):
    """Authentication configuration."""

    jwt_secret_key: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(24, description="JWT expiration in hours")
    api_key_header: str = Field("X-API-Key", description="API key header name")
    enable_bearer_token: bool = Field(True, description="Enable Bearer token authentication")
    enable_api_key: bool = Field(True, description="Enable API key authentication")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    redis_url: str = Field("redis://localhost:6379", description="Redis URL for rate limiting")
    default_requests_per_minute: int = Field(1000, description="Default requests per minute")
    default_burst_size: int = Field(100, description="Default burst size")
    enable_per_user_limits: bool = Field(True, description="Enable per-user rate limits")
    enable_per_api_limits: bool = Field(True, description="Enable per-API rate limits")


class CacheConfig(BaseModel):
    """Cache configuration."""

    redis_url: str = Field("redis://localhost:6379", description="Redis URL for caching")
    default_ttl: int = Field(300, description="Default TTL in seconds")
    max_cache_size: int = Field(1000, description="Maximum cache size (MB)")
    enable_response_caching: bool = Field(True, description="Enable response caching")


class UpstreamConfig(BaseModel):
    """Upstream services configuration."""

    analytics_url: str = Field("http://analytics-service:8000", description="Analytics service URL")
    identity_url: str = Field("http://identity-service:8000", description="Identity service URL")
    networking_url: str = Field("http://networking-service:8000", description="Networking service URL")
    services_url: str = Field("http://services-service:8000", description="Services service URL")
    billing_url: str = Field("http://billing-service:8000", description="Billing service URL")
    platform_url: str = Field("http://platform-service:8000", description="Platform service URL")

    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    read_timeout: int = Field(60, description="Read timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff: float = Field(1.0, description="Retry backoff multiplier")


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    enabled: bool = Field(True, description="Enable monitoring")
    prometheus_port: int = Field(9090, description="Prometheus metrics port")
    metrics_interval: int = Field(30, description="Metrics collection interval")
    enable_request_logging: bool = Field(True, description="Enable request logging")
    enable_error_tracking: bool = Field(True, description="Enable error tracking")
    enable_performance_tracking: bool = Field(True, description="Enable performance tracking")


class SecurityConfig(BaseModel):
    """Security configuration."""

    enable_cors: bool = Field(True, description="Enable CORS")
    cors_origins: List[str] = Field([], description="CORS allowed origins")
    cors_methods: List[str] = Field(["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    cors_headers: List[str] = Field(["Content-Type", "Authorization"], description="CORS allowed headers")
    cors_max_age: int = Field(86400, description="CORS max age")

    enable_request_validation: bool = Field(True, description="Enable request validation")
    enable_response_filtering: bool = Field(True, description="Enable response filtering")
    max_request_size: int = Field(10 * 1024 * 1024, description="Max request size in bytes")


class GatewayConfig(BaseModel):
    """Complete gateway configuration."""

    environment: str = Field("development", description="Environment")
    debug: bool = Field(False, description="Debug mode")
    tenant_id: Optional[str] = Field(None, description="Default tenant ID")

    server: GatewayServerConfig
    authentication: AuthenticationConfig
    rate_limit: RateLimitConfig
    cache: CacheConfig
    upstream: UpstreamConfig
    monitoring: MonitoringConfig
    security: SecurityConfig


# Simple config object for compatibility
class Config(BaseModel):
    """Simple config for compatibility."""
    debug: bool = Field(default=True, description="Debug mode")
    tenant_id: str = Field(default="default", description="Tenant ID")

# Global config instance
config = Config()

def load_config() -> GatewayConfig:
    """Load configuration from environment variables."""

    # Server config
    server_config = GatewayServerConfig(
        host=os.getenv("DOTMAC_GATEWAY_HOST", "127.0.0.1"),  # Secure default
        port=int(os.getenv("DOTMAC_GATEWAY_PORT", "8080")),
        workers=int(os.getenv("DOTMAC_GATEWAY_WORKERS", "4")),
        enable_docs=os.getenv("DOTMAC_GATEWAY_ENABLE_DOCS", "true").lower() == "true",
        enable_health_check=os.getenv("DOTMAC_GATEWAY_ENABLE_HEALTH_CHECK", "true").lower() == "true"
    )

    # Authentication config
    auth_config = AuthenticationConfig(
        jwt_secret_key=os.getenv("DOTMAC_AUTH_JWT_SECRET_KEY", "your-secret-key"),
        jwt_algorithm=os.getenv("DOTMAC_AUTH_JWT_ALGORITHM", "HS256"),
        jwt_expiration_hours=int(os.getenv("DOTMAC_AUTH_JWT_EXPIRATION_HOURS", "24")),
        api_key_header=os.getenv("DOTMAC_AUTH_API_KEY_HEADER", "X-API-Key"),
        enable_bearer_token=os.getenv("DOTMAC_AUTH_ENABLE_BEARER_TOKEN", "true").lower() == "true",
        enable_api_key=os.getenv("DOTMAC_AUTH_ENABLE_API_KEY", "true").lower() == "true"
    )

    # Rate limit config
    rate_limit_config = RateLimitConfig(
        redis_url=os.getenv("DOTMAC_RATE_LIMIT_REDIS_URL", "redis://localhost:6379"),
        default_requests_per_minute=int(os.getenv("DOTMAC_RATE_LIMIT_DEFAULT_RPM", "1000")),
        default_burst_size=int(os.getenv("DOTMAC_RATE_LIMIT_BURST_SIZE", "100")),
        enable_per_user_limits=os.getenv("DOTMAC_RATE_LIMIT_PER_USER", "true").lower() == "true",
        enable_per_api_limits=os.getenv("DOTMAC_RATE_LIMIT_PER_API", "true").lower() == "true"
    )

    # Cache config
    cache_config = CacheConfig(
        redis_url=os.getenv("DOTMAC_CACHE_REDIS_URL", "redis://localhost:6379"),
        default_ttl=int(os.getenv("DOTMAC_CACHE_DEFAULT_TTL", "300")),
        max_cache_size=int(os.getenv("DOTMAC_CACHE_MAX_SIZE", "1000")),
        enable_response_caching=os.getenv("DOTMAC_CACHE_ENABLE_RESPONSE", "true").lower() == "true"
    )

    # Upstream config
    upstream_config = UpstreamConfig(
        analytics_url=os.getenv("DOTMAC_UPSTREAM_ANALYTICS", "http://analytics-service:8000"),
        identity_url=os.getenv("DOTMAC_UPSTREAM_IDENTITY", "http://identity-service:8000"),
        networking_url=os.getenv("DOTMAC_UPSTREAM_NETWORKING", "http://networking-service:8000"),
        services_url=os.getenv("DOTMAC_UPSTREAM_SERVICES", "http://services-service:8000"),
        billing_url=os.getenv("DOTMAC_UPSTREAM_BILLING", "http://billing-service:8000"),
        platform_url=os.getenv("DOTMAC_UPSTREAM_PLATFORM", "http://platform-service:8000"),
        connection_timeout=int(os.getenv("DOTMAC_UPSTREAM_CONNECTION_TIMEOUT", "30")),
        read_timeout=int(os.getenv("DOTMAC_UPSTREAM_READ_TIMEOUT", "60")),
        max_retries=int(os.getenv("DOTMAC_UPSTREAM_MAX_RETRIES", "3")),
        retry_backoff=float(os.getenv("DOTMAC_UPSTREAM_RETRY_BACKOFF", "1.0"))
    )

    # Monitoring config
    monitoring_config = MonitoringConfig(
        enabled=os.getenv("DOTMAC_MONITORING_ENABLED", "true").lower() == "true",
        prometheus_port=int(os.getenv("DOTMAC_MONITORING_PROMETHEUS_PORT", "9090")),
        metrics_interval=int(os.getenv("DOTMAC_MONITORING_METRICS_INTERVAL", "30")),
        enable_request_logging=os.getenv("DOTMAC_MONITORING_REQUEST_LOGGING", "true").lower() == "true",
        enable_error_tracking=os.getenv("DOTMAC_MONITORING_ERROR_TRACKING", "true").lower() == "true",
        enable_performance_tracking=os.getenv("DOTMAC_MONITORING_PERFORMANCE_TRACKING", "true").lower() == "true"
    )

    # Security config
    cors_origins = os.getenv("DOTMAC_SECURITY_CORS_ORIGINS", "").split(",") if os.getenv("DOTMAC_SECURITY_CORS_ORIGINS") else []
    cors_methods = os.getenv("DOTMAC_SECURITY_CORS_METHODS", "GET,POST,PUT,DELETE").split(",")
    cors_headers = os.getenv("DOTMAC_SECURITY_CORS_HEADERS", "Content-Type,Authorization").split(",")

    security_config = SecurityConfig(
        enable_cors=os.getenv("DOTMAC_SECURITY_ENABLE_CORS", "true").lower() == "true",
        cors_origins=cors_origins,
        cors_methods=cors_methods,
        cors_headers=cors_headers,
        cors_max_age=int(os.getenv("DOTMAC_SECURITY_CORS_MAX_AGE", "86400")),
        enable_request_validation=os.getenv("DOTMAC_SECURITY_ENABLE_REQUEST_VALIDATION", "true").lower() == "true",
        enable_response_filtering=os.getenv("DOTMAC_SECURITY_ENABLE_RESPONSE_FILTERING", "true").lower() == "true",
        max_request_size=int(os.getenv("DOTMAC_SECURITY_MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))
    )

    return GatewayConfig(
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        tenant_id=os.getenv("DOTMAC_TENANT_ID"),
        server=server_config,
        authentication=auth_config,
        rate_limit=rate_limit_config,
        cache=cache_config,
        upstream=upstream_config,
        monitoring=monitoring_config,
        security=security_config
    )
