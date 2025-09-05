"""
Production-ready configuration for DotMac Audit API.

This module provides comprehensive configuration management for audit functionality
with environment-based settings, validation, and security considerations.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .utils import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ConfigurationError,
    get_logger,
    safe_cast,
    validate_required_field,
)

logger = get_logger(__name__)


class AuditLogLevel(Enum):
    """Audit logging levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class StorageBackend(Enum):
    """Supported audit storage backends."""

    MEMORY = "memory"
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    FILE = "file"


@dataclass
class StorageConfig:
    """Configuration for audit storage backend."""

    backend: StorageBackend = StorageBackend.MEMORY
    connection_string: Optional[str] = None
    max_events: int = 10000
    batch_size: int = 100
    flush_interval: float = 30.0
    retention_days: int = 365

    # Database-specific settings
    table_name: str = "audit_events"
    connection_pool_size: int = 10
    connection_timeout: float = 30.0

    # File storage settings
    file_path: Optional[str] = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    rotate_files: bool = True

    # Security settings
    encrypt_at_rest: bool = False
    encryption_key: Optional[str] = None


@dataclass
class APIConfig:
    """Configuration for audit API endpoints."""

    enabled: bool = True
    prefix: str = "/audit"
    max_page_size: int = MAX_PAGE_SIZE
    default_page_size: int = DEFAULT_PAGE_SIZE
    enable_streaming: bool = True
    enable_export: bool = True
    export_formats: set[str] = field(default_factory=lambda: {"json", "csv"})
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Security settings
    require_authentication: bool = True
    allowed_origins: list[str] = field(default_factory=list)
    enable_cors: bool = False


@dataclass
class MiddlewareConfig:
    """Configuration for audit middleware."""

    enabled: bool = True
    excluded_paths: set[str] = field(
        default_factory=lambda: {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/ping",
            "/ready",
            "/live",
        }
    )
    excluded_methods: set[str] = field(default_factory=lambda: {"OPTIONS", "HEAD"})
    log_request_body: bool = False
    log_response_body: bool = False
    max_body_size: int = 10 * 1024  # 10KB
    sensitive_headers: set[str] = field(
        default_factory=lambda: {
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
            "x-csrf-token",
            "x-session-id",
        }
    )

    # Performance settings
    async_logging: bool = True
    queue_size: int = 1000


@dataclass
class ComplianceConfig:
    """Configuration for compliance features."""

    enabled_frameworks: set[str] = field(default_factory=lambda: {"SOC2", "GDPR"})
    pii_detection: bool = True
    risk_scoring: bool = True
    high_risk_threshold: int = 70
    critical_risk_threshold: int = 90

    # Data classification
    classify_resources: bool = True
    default_classification: str = "internal"

    # Retention policies
    retention_policies: dict[str, int] = field(
        default_factory=lambda: {
            "auth": 2555,  # 7 years
            "data": 2555,  # 7 years
            "system": 365,  # 1 year
            "business": 2555,  # 7 years
            "security": 2555,  # 7 years
        }
    )


@dataclass
class AuditConfig:
    """Master configuration for audit system."""

    # Service identification
    service_name: str = "dotmac-service"
    tenant_id: Optional[str] = None
    environment: str = "development"
    version: str = "1.0.0"

    # Feature flags
    enabled: bool = True
    log_level: AuditLogLevel = AuditLogLevel.INFO

    # Component configurations
    storage: StorageConfig = field(default_factory=StorageConfig)
    api: APIConfig = field(default_factory=APIConfig)
    middleware: MiddlewareConfig = field(default_factory=MiddlewareConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)

    # Performance settings
    max_concurrent_events: int = 100
    event_timeout: float = 30.0
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        validate_required_field(self.service_name, "service_name", str)
        validate_required_field(self.environment, "environment", str)

        if not self.service_name.strip():
            raise ConfigurationError("service_name cannot be empty")

        if (
            self.storage.backend == StorageBackend.POSTGRESQL
            and not self.storage.connection_string
        ):
            raise ConfigurationError("PostgreSQL backend requires connection_string")

        if self.storage.backend == StorageBackend.FILE and not self.storage.file_path:
            raise ConfigurationError("File backend requires file_path")

        if self.storage.encrypt_at_rest and not self.storage.encryption_key:
            raise ConfigurationError(
                "Encryption enabled but no encryption_key provided"
            )

        if self.api.max_page_size > MAX_PAGE_SIZE:
            logger.warning(
                f"API max_page_size {self.api.max_page_size} exceeds recommended maximum {MAX_PAGE_SIZE}"
            )

        if (
            self.compliance.high_risk_threshold
            >= self.compliance.critical_risk_threshold
        ):
            raise ConfigurationError(
                "high_risk_threshold must be less than critical_risk_threshold"
            )


def create_audit_config_from_env() -> AuditConfig:
    """
    Create audit configuration from environment variables.

    Environment variables:
        DOTMAC_AUDIT_ENABLED: Enable/disable audit system (default: true)
        DOTMAC_AUDIT_SERVICE_NAME: Service name for audit events
        DOTMAC_AUDIT_TENANT_ID: Tenant ID for audit events
        DOTMAC_AUDIT_LOG_LEVEL: Audit log level (debug, info, warning, error, critical)
        DOTMAC_AUDIT_STORAGE_BACKEND: Storage backend (memory, postgresql, file)
        DOTMAC_AUDIT_STORAGE_CONNECTION: Database connection string
        DOTMAC_AUDIT_STORAGE_RETENTION_DAYS: Event retention in days
        DOTMAC_AUDIT_API_ENABLED: Enable API endpoints
        DOTMAC_AUDIT_API_PREFIX: API prefix path
        DOTMAC_AUDIT_MIDDLEWARE_ENABLED: Enable middleware
        DOTMAC_AUDIT_COMPLIANCE_FRAMEWORKS: Comma-separated list of frameworks

    Returns:
        Configured AuditConfig instance
    """

    # Basic service configuration
    service_name = os.getenv("DOTMAC_AUDIT_SERVICE_NAME", "dotmac-service")
    tenant_id = os.getenv("DOTMAC_AUDIT_TENANT_ID")
    environment = os.getenv(
        "DOTMAC_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")
    )

    # Feature flags
    enabled = os.getenv("DOTMAC_AUDIT_ENABLED", "true").lower() == "true"
    log_level_str = os.getenv("DOTMAC_AUDIT_LOG_LEVEL", "info").lower()

    try:
        log_level = AuditLogLevel(log_level_str)
    except ValueError:
        logger.warning(f"Invalid log level {log_level_str}, using INFO")
        log_level = AuditLogLevel.INFO

    # Storage configuration
    storage_backend_str = os.getenv("DOTMAC_AUDIT_STORAGE_BACKEND", "memory").lower()
    try:
        storage_backend = StorageBackend(storage_backend_str)
    except ValueError:
        logger.warning(f"Invalid storage backend {storage_backend_str}, using memory")
        storage_backend = StorageBackend.MEMORY

    storage_config = StorageConfig(
        backend=storage_backend,
        connection_string=os.getenv("DOTMAC_AUDIT_STORAGE_CONNECTION"),
        max_events=safe_cast(os.getenv("DOTMAC_AUDIT_STORAGE_MAX_EVENTS"), int, 10000),
        retention_days=safe_cast(
            os.getenv("DOTMAC_AUDIT_STORAGE_RETENTION_DAYS"), int, 365
        ),
        table_name=os.getenv("DOTMAC_AUDIT_STORAGE_TABLE", "audit_events"),
        file_path=os.getenv("DOTMAC_AUDIT_STORAGE_FILE_PATH"),
        encrypt_at_rest=os.getenv("DOTMAC_AUDIT_ENCRYPT_AT_REST", "false").lower()
        == "true",
        encryption_key=os.getenv("DOTMAC_AUDIT_ENCRYPTION_KEY"),
    )

    # API configuration
    api_config = APIConfig(
        enabled=os.getenv("DOTMAC_AUDIT_API_ENABLED", "true").lower() == "true",
        prefix=os.getenv("DOTMAC_AUDIT_API_PREFIX", "/audit"),
        max_page_size=safe_cast(
            os.getenv("DOTMAC_AUDIT_API_MAX_PAGE_SIZE"), int, MAX_PAGE_SIZE
        ),
        require_authentication=os.getenv(
            "DOTMAC_AUDIT_API_REQUIRE_AUTH", "true"
        ).lower()
        == "true",
        enable_cors=os.getenv("DOTMAC_AUDIT_API_ENABLE_CORS", "false").lower()
        == "true",
    )

    # Middleware configuration
    middleware_config = MiddlewareConfig(
        enabled=os.getenv("DOTMAC_AUDIT_MIDDLEWARE_ENABLED", "true").lower() == "true",
        log_request_body=os.getenv("DOTMAC_AUDIT_LOG_REQUEST_BODY", "false").lower()
        == "true",
        log_response_body=os.getenv("DOTMAC_AUDIT_LOG_RESPONSE_BODY", "false").lower()
        == "true",
        max_body_size=safe_cast(
            os.getenv("DOTMAC_AUDIT_MAX_BODY_SIZE"), int, 10 * 1024
        ),
        async_logging=os.getenv("DOTMAC_AUDIT_ASYNC_LOGGING", "true").lower() == "true",
    )

    # Compliance configuration
    frameworks_str = os.getenv("DOTMAC_AUDIT_COMPLIANCE_FRAMEWORKS", "SOC2,GDPR")
    enabled_frameworks = {
        f.strip().upper() for f in frameworks_str.split(",") if f.strip()
    }

    compliance_config = ComplianceConfig(
        enabled_frameworks=enabled_frameworks,
        pii_detection=os.getenv("DOTMAC_AUDIT_PII_DETECTION", "true").lower() == "true",
        risk_scoring=os.getenv("DOTMAC_AUDIT_RISK_SCORING", "true").lower() == "true",
        high_risk_threshold=safe_cast(
            os.getenv("DOTMAC_AUDIT_HIGH_RISK_THRESHOLD"), int, 70
        ),
        critical_risk_threshold=safe_cast(
            os.getenv("DOTMAC_AUDIT_CRITICAL_RISK_THRESHOLD"), int, 90
        ),
    )

    return AuditConfig(
        service_name=service_name,
        tenant_id=tenant_id,
        environment=environment,
        enabled=enabled,
        log_level=log_level,
        storage=storage_config,
        api=api_config,
        middleware=middleware_config,
        compliance=compliance_config,
    )


def validate_production_config(config: AuditConfig) -> list[str]:
    """
    Validate configuration for production deployment.

    Args:
        config: Configuration to validate

    Returns:
        List of validation warnings/errors
    """
    warnings = []

    # Storage validation
    if config.storage.backend == StorageBackend.MEMORY:
        warnings.append(
            "Memory storage not recommended for production - events will be lost on restart"
        )

    if (
        config.storage.backend == StorageBackend.FILE
        and not config.storage.rotate_files
    ):
        warnings.append("File rotation disabled - log files may grow very large")

    if not config.storage.encrypt_at_rest and config.environment == "production":
        warnings.append("Encryption at rest disabled in production environment")

    # API validation
    if config.api.enabled and not config.api.require_authentication:
        warnings.append("API authentication disabled - audit data exposed without auth")

    if config.api.enable_cors and not config.api.allowed_origins:
        warnings.append("CORS enabled but no allowed origins specified")

    # Performance validation
    if config.storage.batch_size < 10:
        warnings.append("Very small batch size may impact performance")

    if config.storage.flush_interval > 300:  # 5 minutes
        warnings.append("Large flush interval may cause data loss during crashes")

    # Security validation
    if config.middleware.log_request_body or config.middleware.log_response_body:
        warnings.append(
            "Request/response body logging enabled - may log sensitive data"
        )

    if config.log_level == AuditLogLevel.DEBUG and config.environment == "production":
        warnings.append(
            "Debug logging enabled in production - may log sensitive information"
        )

    return warnings


# Global configuration instance
_global_config: Optional[AuditConfig] = None


def get_audit_config() -> Optional[AuditConfig]:
    """Get the global audit configuration."""
    return _global_config


def init_audit_config(config: Optional[AuditConfig] = None) -> AuditConfig:
    """
    Initialize the global audit configuration.

    Args:
        config: Optional configuration instance. If None, loads from environment.

    Returns:
        The initialized configuration
    """
    if config is None:
        config = create_audit_config_from_env()
    global _global_config
    # Validate for production
    if config.environment in ["production", "prod"]:
        warnings = validate_production_config(config)
        for warning in warnings:
            logger.warning(f"Production config warning: {warning}")

    _global_config = config
    logger.info(
        f"Audit configuration initialized for service '{config.service_name}' in '{config.environment}' environment"
    )

    return config


__all__ = [
    # Configuration classes
    "AuditConfig",
    "StorageConfig",
    "APIConfig",
    "MiddlewareConfig",
    "ComplianceConfig",
    # Enums
    "AuditLogLevel",
    "StorageBackend",
    # Factory functions
    "create_audit_config_from_env",
    "validate_production_config",
    "get_audit_config",
    "init_audit_config",
]
