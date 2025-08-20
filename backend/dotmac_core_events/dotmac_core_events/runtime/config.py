"""
Runtime configuration for dotmac_core_events.

Provides configuration management for:
- Environment-based settings
- Adapter configurations
- Database settings
- Security settings
"""

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator

from ..adapters import AdapterConfig, KafkaConfig, MemoryConfig, RedisConfig


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Max pool overflow")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, description="Pool recycle time in seconds")
    echo: bool = Field(False, description="Enable SQL echo")


class SecurityConfig(BaseModel):
    """Security configuration."""

    jwt_secret_key: Optional[str] = Field(None, description="JWT secret key")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(24, description="JWT expiration in hours")
    api_key_header: str = Field("X-API-Key", description="API key header name")
    tenant_id_header: str = Field("X-Tenant-ID", description="Tenant ID header name")
    cors_origins: list = Field([], description="CORS allowed origins (empty means no CORS)")
    cors_methods: list = Field(["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    cors_headers: list = Field(["Content-Type", "Authorization", "X-Tenant-ID", "X-API-Key"], description="CORS allowed headers")


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    enable_metrics: bool = Field(True, description="Enable metrics collection")
    enable_tracing: bool = Field(True, description="Enable distributed tracing")
    enable_logging: bool = Field(True, description="Enable structured logging")
    log_level: str = Field("INFO", description="Log level")
    metrics_port: int = Field(9090, description="Metrics server port")
    jaeger_endpoint: Optional[str] = Field(None, description="Jaeger endpoint")
    prometheus_endpoint: Optional[str] = Field(None, description="Prometheus endpoint")


class RuntimeConfig(BaseModel):
    """Complete runtime configuration."""

    # Application settings
    app_name: str = Field("dotmac-core-events", description="Application name")
    app_version: str = Field("1.0.0", description="Application version")
    debug: bool = Field(False, description="Debug mode")
    host: str = Field("127.0.0.1", description="Server host (secure default: localhost only)")
    port: int = Field(8000, description="Server port")
    workers: int = Field(1, description="Number of workers")

    # Event adapter configuration
    adapter_type: str = Field("memory", description="Event adapter type")
    adapter_config: Dict[str, Any] = Field(default_factory=dict, description="Adapter configuration")

    # Database configuration
    database: Optional[DatabaseConfig] = Field(None, description="Database configuration")

    # Security configuration
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")

    # Observability configuration
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig, description="Observability configuration")

    # Background tasks
    enable_background_tasks: bool = Field(True, description="Enable background tasks")
    outbox_dispatch_interval: int = Field(5, description="Outbox dispatch interval in seconds")
    cleanup_interval: int = Field(3600, description="Cleanup interval in seconds")

    @validator("adapter_type")
    def validate_adapter_type(cls, v):
        valid_types = ["memory", "redis", "kafka"]
        if v not in valid_types:
            raise ValueError(f"adapter_type must be one of {valid_types}")
        return v

    def get_adapter_config(self) -> AdapterConfig:
        """Get typed adapter configuration."""
        if self.adapter_type == "redis":
            return RedisConfig(**self.adapter_config)
        elif self.adapter_type == "kafka":
            return KafkaConfig(**self.adapter_config)
        elif self.adapter_type == "memory":
            return MemoryConfig(**self.adapter_config)
        else:
            raise ValueError(f"Unknown adapter type: {self.adapter_type}")


def load_config(config_file: Optional[str] = None) -> RuntimeConfig:  # noqa: C901
    """
    Load configuration from environment variables and optional config file.

    Args:
        config_file: Optional path to configuration file

    Returns:
        Runtime configuration
    """
    # Start with environment variables
    config_data = {}

    # Application settings
    config_data.update({
        "app_name": os.getenv("APP_NAME", "dotmac-core-events"),
        "app_version": os.getenv("APP_VERSION", "1.0.0"),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "host": os.getenv("HOST", "127.0.0.1"),  # Secure default
        "port": int(os.getenv("PORT", "8000")),
        "workers": int(os.getenv("WORKERS", "1")),
    })

    # Adapter configuration
    adapter_type = os.getenv("ADAPTER_TYPE", "memory")
    config_data["adapter_type"] = adapter_type

    # Build adapter config based on type
    adapter_config = {}
    if adapter_type == "redis":
        adapter_config = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "db": int(os.getenv("REDIS_DB", "0")),
            "password": os.getenv("REDIS_PASSWORD"),
            "ssl": os.getenv("REDIS_SSL", "false").lower() == "true",
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            "stream_maxlen": int(os.getenv("REDIS_STREAM_MAXLEN", "10000")),
        }
    elif adapter_type == "kafka":
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        adapter_config = {
            "bootstrap_servers": bootstrap_servers.split(","),
            "security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            "sasl_mechanism": os.getenv("KAFKA_SASL_MECHANISM"),
            "sasl_username": os.getenv("KAFKA_SASL_USERNAME"),
            "sasl_password": os.getenv("KAFKA_SASL_PASSWORD"),
            "ssl_cafile": os.getenv("KAFKA_SSL_CAFILE"),
            "ssl_certfile": os.getenv("KAFKA_SSL_CERTFILE"),
            "ssl_keyfile": os.getenv("KAFKA_SSL_KEYFILE"),
        }
    elif adapter_type == "memory":
        adapter_config = {
            "max_messages_per_topic": int(os.getenv("MEMORY_MAX_MESSAGES", "10000")),
            "max_consumer_lag": int(os.getenv("MEMORY_MAX_LAG", "1000")),
        }

    config_data["adapter_config"] = adapter_config

    # Database configuration
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        config_data["database"] = {
            "url": database_url,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "echo": os.getenv("DB_ECHO", "false").lower() == "true",
        }

    # Security configuration
    config_data["security"] = {
        "jwt_secret_key": os.getenv("JWT_SECRET_KEY"),
        "jwt_algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
        "jwt_expiration_hours": int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
        "api_key_header": os.getenv("API_KEY_HEADER", "X-API-Key"),
        "tenant_id_header": os.getenv("TENANT_ID_HEADER", "X-Tenant-ID"),
        "cors_origins": os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [],
        "cors_methods": os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE").split(","),
        "cors_headers": os.getenv("CORS_HEADERS", "Content-Type,Authorization,X-Tenant-ID,X-API-Key").split(","),
    }

    # Observability configuration
    config_data["observability"] = {
        "enable_metrics": os.getenv("ENABLE_METRICS", "true").lower() == "true",
        "enable_tracing": os.getenv("ENABLE_TRACING", "true").lower() == "true",
        "enable_logging": os.getenv("ENABLE_LOGGING", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "metrics_port": int(os.getenv("METRICS_PORT", "9090")),
        "jaeger_endpoint": os.getenv("JAEGER_ENDPOINT"),
        "prometheus_endpoint": os.getenv("PROMETHEUS_ENDPOINT"),
    }

    # Background tasks
    config_data.update({
        "enable_background_tasks": os.getenv("ENABLE_BACKGROUND_TASKS", "true").lower() == "true",
        "outbox_dispatch_interval": int(os.getenv("OUTBOX_DISPATCH_INTERVAL", "5")),
        "cleanup_interval": int(os.getenv("CLEANUP_INTERVAL", "3600")),
    })

    # Load from config file if provided
    if config_file and os.path.exists(config_file):
        import json

        import yaml

        with open(config_file) as f:
            if config_file.endswith(".json"):
                file_config = json.load(f)
            elif config_file.endswith((".yml", ".yaml")):
                file_config = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_file}")

        # Merge file config with environment config (env takes precedence)
        def merge_dicts(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result

        config_data = merge_dicts(file_config, config_data)

    return RuntimeConfig(**config_data)
