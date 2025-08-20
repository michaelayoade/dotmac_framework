"""
Configuration management for DotMac Analytics.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://localhost/analytics"))
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "10")))
    max_overflow: int = field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "20")))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    echo: bool = field(default_factory=lambda: os.getenv("DB_ECHO", "false").lower() == "true")


@dataclass
class CacheConfig:
    """Cache configuration."""
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    default_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_DEFAULT_TTL", "3600")))
    key_prefix: str = field(default_factory=lambda: os.getenv("CACHE_KEY_PREFIX", "analytics:"))


@dataclass
class ProcessingConfig:
    """Data processing configuration."""
    batch_size: int = field(default_factory=lambda: int(os.getenv("PROCESSING_BATCH_SIZE", "1000")))
    max_workers: int = field(default_factory=lambda: int(os.getenv("PROCESSING_MAX_WORKERS", "4")))
    queue_name: str = field(default_factory=lambda: os.getenv("PROCESSING_QUEUE", "analytics"))
    retry_attempts: int = field(default_factory=lambda: int(os.getenv("PROCESSING_RETRY_ATTEMPTS", "3")))


@dataclass
class StorageConfig:
    """Data storage configuration."""
    data_retention_days: int = field(default_factory=lambda: int(os.getenv("DATA_RETENTION_DAYS", "365")))
    archive_after_days: int = field(default_factory=lambda: int(os.getenv("ARCHIVE_AFTER_DAYS", "90")))
    compression_enabled: bool = field(default_factory=lambda: os.getenv("COMPRESSION_ENABLED", "true").lower() == "true")
    backup_enabled: bool = field(default_factory=lambda: os.getenv("BACKUP_ENABLED", "true").lower() == "true")


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "your-secret-key"))
    encryption_key: str = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY", "your-encryption-key"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expiry_hours: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRY_HOURS", "24")))


@dataclass
class NotificationConfig:
    """Notification configuration."""
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: str = field(default_factory=lambda: os.getenv("SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_use_tls: bool = field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true")

    # Webhook notifications
    webhook_url: str = field(default_factory=lambda: os.getenv("WEBHOOK_URL", ""))
    webhook_secret: str = field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", ""))


@dataclass
class IntegrationConfig:
    """External integrations configuration."""
    # Data sources
    enable_database_sources: bool = field(default_factory=lambda: os.getenv("ENABLE_DATABASE_SOURCES", "true").lower() == "true")
    enable_api_sources: bool = field(default_factory=lambda: os.getenv("ENABLE_API_SOURCES", "true").lower() == "true")
    enable_file_sources: bool = field(default_factory=lambda: os.getenv("ENABLE_FILE_SOURCES", "true").lower() == "true")

    # Export destinations
    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", ""))
    s3_access_key: str = field(default_factory=lambda: os.getenv("S3_ACCESS_KEY", ""))
    s3_secret_key: str = field(default_factory=lambda: os.getenv("S3_SECRET_KEY", ""))

    # Third-party analytics
    google_analytics_id: str = field(default_factory=lambda: os.getenv("GOOGLE_ANALYTICS_ID", ""))
    mixpanel_token: str = field(default_factory=lambda: os.getenv("MIXPANEL_TOKEN", ""))


@dataclass
class AnalyticsConfig:
    """Main analytics configuration."""
    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)

    # Analytics-specific settings
    default_timezone: str = field(default_factory=lambda: os.getenv("DEFAULT_TIMEZONE", "UTC"))
    max_query_results: int = field(default_factory=lambda: int(os.getenv("MAX_QUERY_RESULTS", "10000")))
    query_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("QUERY_TIMEOUT_SECONDS", "300")))

    # Real-time processing
    enable_real_time: bool = field(default_factory=lambda: os.getenv("ENABLE_REAL_TIME", "true").lower() == "true")
    real_time_buffer_size: int = field(default_factory=lambda: int(os.getenv("REAL_TIME_BUFFER_SIZE", "1000")))

    # Performance
    enable_query_cache: bool = field(default_factory=lambda: os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true")
    enable_result_pagination: bool = field(default_factory=lambda: os.getenv("ENABLE_RESULT_PAGINATION", "true").lower() == "true")

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.database.url:
            errors.append("Database URL is required")

        if not self.security.secret_key or self.security.secret_key == "your-secret-key":
            errors.append("Secret key must be set and not use default value")

        if not self.security.encryption_key or self.security.encryption_key == "your-encryption-key":
            errors.append("Encryption key must be set and not use default value")

        if self.processing.batch_size <= 0:
            errors.append("Processing batch size must be positive")

        if self.processing.max_workers <= 0:
            errors.append("Processing max workers must be positive")

        if self.storage.data_retention_days <= 0:
            errors.append("Data retention days must be positive")

        return errors


# Global configuration instance
_config: Optional[AnalyticsConfig] = None


def get_config() -> AnalyticsConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = AnalyticsConfig()

        # Validate configuration
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    return _config


def set_config(config: AnalyticsConfig):
    """Set global configuration instance."""
    global _config
    _config = config
