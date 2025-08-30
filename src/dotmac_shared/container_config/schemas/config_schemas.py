"""Configuration schemas for ISP container deployments."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    REDIS = "redis"


class ServiceStatus(str, Enum):
    """Service status options."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


class DatabaseConfig(BaseModel):
    """Database configuration schema."""

    type: DatabaseType = Field(
        default=DatabaseType.POSTGRESQL, description="Database type"
    )
    host: str = Field(..., description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")

    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, le=200, description="Max pool overflow")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout in seconds")
    pool_recycle: int = Field(
        default=3600, ge=0, description="Pool recycle time in seconds"
    )

    # Advanced settings
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    connect_timeout: int = Field(default=10, ge=1, description="Connection timeout")
    query_timeout: int = Field(default=60, ge=1, description="Query timeout")

    # Additional options
    extra_options: Dict[str, Any] = Field(
        default_factory=dict, description="Extra database options"
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RedisConfig(BaseModel):
    """Redis configuration schema."""

    host: str = Field(..., description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    database: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: Optional[str] = Field(None, description="Redis password")

    # Connection settings
    connection_pool_size: int = Field(
        default=50, ge=1, description="Connection pool size"
    )
    connection_timeout: int = Field(default=5, ge=1, description="Connection timeout")
    socket_timeout: int = Field(default=5, ge=1, description="Socket timeout")

    # SSL settings
    ssl_enabled: bool = Field(default=False, description="Enable SSL")
    ssl_cert_file: Optional[str] = Field(None, description="SSL certificate file path")
    ssl_key_file: Optional[str] = Field(None, description="SSL key file path")

    # Advanced settings
    max_connections: int = Field(default=100, ge=1, description="Max connections")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")


class SecurityConfig(BaseModel):
    """Security configuration schema."""

    # JWT settings
    jwt_secret_key: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=15, description="Access token expiry"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=30, description="Refresh token expiry"
    )

    # Encryption settings
    encryption_key: str = Field(..., description="Data encryption key")
    password_hash_algorithm: str = Field(
        default="bcrypt", description="Password hash algorithm"
    )
    password_hash_rounds: int = Field(
        default=12, ge=10, le=15, description="Hash rounds"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Requests per minute"
    )
    rate_limit_burst: int = Field(default=100, description="Burst limit")

    # CORS settings
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: List[str] = Field(
        default_factory=list, description="Allowed CORS origins"
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], description="Allowed methods"
    )

    # Security headers
    enable_security_headers: bool = Field(
        default=True, description="Enable security headers"
    )
    content_security_policy: Optional[str] = Field(None, description="CSP header")

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        return v


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""

    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_endpoint: str = Field(
        default="/metrics", description="Metrics endpoint path"
    )
    metrics_port: int = Field(default=9090, description="Metrics port")

    # Health checks
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_endpoint: str = Field(
        default="/health", description="Health check endpoint"
    )
    health_check_interval: int = Field(default=30, description="Health check interval")

    # Tracing
    tracing_enabled: bool = Field(
        default=False, description="Enable distributed tracing"
    )
    tracing_endpoint: Optional[str] = Field(None, description="Tracing endpoint")
    tracing_sample_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Trace sample rate"
    )

    # External monitoring services
    prometheus_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    grafana_dashboard_enabled: bool = Field(
        default=False, description="Enable Grafana dashboard"
    )
    alertmanager_enabled: bool = Field(default=False, description="Enable Alertmanager")


class LoggingConfig(BaseModel):
    """Logging configuration schema."""

    level: LogLevel = Field(default=LogLevel.INFO, description="Default log level")
    format: str = Field(default="json", description="Log format (json, text)")

    # File logging
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_file_path: str = Field(
        default="/var/log/isp/app.log", description="Log file path"
    )
    log_file_max_size: str = Field(default="10MB", description="Max log file size")
    log_file_backup_count: int = Field(default=5, description="Number of backup files")

    # Console logging
    log_to_console: bool = Field(default=True, description="Enable console logging")
    console_log_level: LogLevel = Field(
        default=LogLevel.INFO, description="Console log level"
    )

    # Structured logging
    structured_logging: bool = Field(
        default=True, description="Enable structured logging"
    )
    log_request_id: bool = Field(default=True, description="Include request ID in logs")
    log_user_id: bool = Field(default=True, description="Include user ID in logs")
    log_tenant_id: bool = Field(default=True, description="Include tenant ID in logs")

    # External logging
    external_logging_enabled: bool = Field(
        default=False, description="Enable external logging"
    )
    external_logging_endpoint: Optional[str] = Field(
        None, description="External logging endpoint"
    )

    # Log filtering
    sensitive_fields: List[str] = Field(
        default=["password", "token", "secret", "key"],
        description="Fields to filter from logs",
    )


class NetworkConfig(BaseModel):
    """Network configuration schema."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, ge=1, description="Number of worker processes")

    # Timeouts
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    keepalive_timeout: int = Field(default=5, description="Keep-alive timeout")

    # Limits
    max_request_size: int = Field(
        default=16777216, description="Max request size in bytes"
    )  # 16MB
    max_concurrent_requests: int = Field(
        default=1000, description="Max concurrent requests"
    )

    # Proxy settings
    proxy_headers: bool = Field(default=True, description="Trust proxy headers")
    proxy_prefix: Optional[str] = Field(None, description="Proxy path prefix")

    # WebSocket settings
    websocket_enabled: bool = Field(
        default=True, description="Enable WebSocket support"
    )
    websocket_max_connections: int = Field(
        default=100, description="Max WebSocket connections"
    )


class ServiceConfig(BaseModel):
    """Individual service configuration."""

    name: str = Field(..., description="Service name")
    version: str = Field(default="latest", description="Service version")
    status: ServiceStatus = Field(
        default=ServiceStatus.ENABLED, description="Service status"
    )

    # Resource limits
    cpu_limit: Optional[float] = Field(None, description="CPU limit (cores)")
    memory_limit: Optional[str] = Field(
        None, description="Memory limit (e.g., '512MB')"
    )

    # Environment variables
    environment_variables: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )

    # Health check
    health_check_path: Optional[str] = Field(None, description="Health check endpoint")
    health_check_interval: int = Field(default=30, description="Health check interval")

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list, description="Service dependencies"
    )

    # Custom configuration
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific config"
    )


class ExternalServiceConfig(BaseModel):
    """External service integration configuration."""

    service_name: str = Field(..., description="External service name")
    endpoint: str = Field(..., description="Service endpoint URL")
    api_key: Optional[str] = Field(None, description="API key for authentication")

    # Authentication
    auth_type: str = Field(default="api_key", description="Authentication type")
    auth_config: Dict[str, Any] = Field(
        default_factory=dict, description="Auth configuration"
    )

    # Connection settings
    timeout: int = Field(default=30, description="Request timeout")
    max_retries: int = Field(default=3, description="Max retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")

    # Rate limiting
    rate_limit: Optional[int] = Field(
        None, description="Rate limit (requests per second)"
    )

    # Circuit breaker
    circuit_breaker_enabled: bool = Field(
        default=True, description="Enable circuit breaker"
    )
    circuit_breaker_threshold: int = Field(
        default=5, description="Circuit breaker threshold"
    )


class FeatureFlagConfig(BaseModel):
    """Feature flag configuration."""

    feature_name: str = Field(..., description="Feature name")
    enabled: bool = Field(default=False, description="Feature enabled")
    rollout_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Rollout percentage"
    )

    # Targeting
    target_plans: List[str] = Field(
        default_factory=list, description="Target subscription plans"
    )
    target_tenants: List[str] = Field(
        default_factory=list, description="Target tenant IDs"
    )
    target_environments: List[str] = Field(
        default_factory=list, description="Target environments"
    )

    # Configuration
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Feature configuration"
    )

    # Metadata
    description: Optional[str] = Field(None, description="Feature description")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Update timestamp"
    )


class ISPConfiguration(BaseModel):
    """Complete ISP container configuration."""

    # Basic info
    tenant_id: UUID = Field(..., description="Tenant identifier")
    environment: str = Field(..., description="Environment (dev, staging, production)")
    config_version: str = Field(default="v1", description="Configuration version")

    # Core configurations
    database: DatabaseConfig = Field(..., description="Database configuration")
    redis: RedisConfig = Field(..., description="Redis configuration")
    security: SecurityConfig = Field(..., description="Security configuration")
    monitoring: MonitoringConfig = Field(..., description="Monitoring configuration")
    logging: LoggingConfig = Field(..., description="Logging configuration")
    network: NetworkConfig = Field(..., description="Network configuration")

    # Services
    services: List[ServiceConfig] = Field(
        default_factory=list, description="Service configurations"
    )
    external_services: List[ExternalServiceConfig] = Field(
        default_factory=list, description="External services"
    )

    # Feature flags
    feature_flags: List[FeatureFlagConfig] = Field(
        default_factory=list, description="Feature flags"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="Configuration creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )
    created_by: Optional[str] = Field(None, description="Configuration creator")

    # Validation settings
    validation_required: bool = Field(default=True, description="Require validation")
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation errors"
    )

    # Custom fields
    custom_config: Dict[str, Any] = Field(
        default_factory=dict, description="Custom configuration"
    )

    @model_validator(mode="after")
    def validate_configuration(self):
        """Perform cross-field validation."""
        # Update timestamp
        self.updated_at = datetime.now()

        # Validate feature flags don't conflict
        feature_names = [f.feature_name for f in self.feature_flags]
        if len(feature_names) != len(set(feature_names)):
            raise ValueError("Duplicate feature flag names found")

        # Validate service dependencies
        service_names = {s.name for s in self.services}
        for service in self.services:
            for dep in service.depends_on:
                if dep not in service_names:
                    raise ValueError(
                        f"Service {service.name} depends on unknown service {dep}"
                    )

        return self

    def get_feature_flag(self, feature_name: str) -> Optional[FeatureFlagConfig]:
        """Get a specific feature flag by name."""
        return next(
            (f for f in self.feature_flags if f.feature_name == feature_name), None
        )

    def get_service(self, service_name: str) -> Optional[ServiceConfig]:
        """Get a specific service configuration by name."""
        return next((s for s in self.services if s.name == service_name), None)

    def get_external_service(
        self, service_name: str
    ) -> Optional[ExternalServiceConfig]:
        """Get a specific external service by name."""
        return next(
            (s for s in self.external_services if s.service_name == service_name), None
        )

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        feature = self.get_feature_flag(feature_name)
        return feature.enabled if feature else False

    def get_enabled_services(self) -> List[ServiceConfig]:
        """Get all enabled services."""
        return [s for s in self.services if s.status == ServiceStatus.ENABLED]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ISPConfiguration":
        """Create configuration from dictionary."""
        return cls.model_validate(data)
