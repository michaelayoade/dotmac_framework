"""
WebSocket Service Configuration Management

Environment-based configuration with validation and defaults for production deployments.
"""

import os
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class WebSocketConfig(BaseModel):
    """
    WebSocket service configuration with environment variable support.

    All settings can be overridden via environment variables with WEBSOCKET_ prefix.
    """

    # Connection Management
    max_connections: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "10000")),
        description="Maximum concurrent WebSocket connections per instance",
    )

    heartbeat_interval: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30")),
        description="Heartbeat interval in seconds",
    )

    connection_timeout: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_CONNECTION_TIMEOUT", "300")),
        description="Connection timeout in seconds",
    )

    # Message Management
    message_ttl: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_MESSAGE_TTL", "300")),
        description="Message TTL in seconds for persistence",
    )

    max_message_size: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_MAX_MESSAGE_SIZE", "1048576")),
        description="Maximum message size in bytes (1MB default)",
    )

    message_queue_size: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_MESSAGE_QUEUE_SIZE", "1000")),
        description="Maximum messages in queue per connection",
    )

    # Redis Configuration
    redis_url: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis connection URL for scaling",
    )

    redis_cluster_nodes: List[str] = Field(
        default_factory=lambda: (
            os.getenv("REDIS_CLUSTER_NODES", "").split(",")
            if os.getenv("REDIS_CLUSTER_NODES")
            else []
        ),
        description="Redis cluster node URLs",
    )

    redis_max_connections: int = Field(
        default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
        description="Maximum Redis connections per instance",
    )

    # Feature Flags
    enable_persistence: bool = Field(
        default_factory=lambda: os.getenv(
            "WEBSOCKET_ENABLE_PERSISTENCE", "true"
        ).lower()
        == "true",
        description="Enable message persistence for offline clients",
    )

    enable_metrics: bool = Field(
        default_factory=lambda: os.getenv("WEBSOCKET_ENABLE_METRICS", "true").lower()
        == "true",
        description="Enable metrics collection",
    )

    enable_health_checks: bool = Field(
        default_factory=lambda: os.getenv(
            "WEBSOCKET_ENABLE_HEALTH_CHECKS", "true"
        ).lower()
        == "true",
        description="Enable health check endpoints",
    )

    # Security Configuration
    cors_origins: List[str] = Field(
        default_factory=lambda: os.getenv("WEBSOCKET_CORS_ORIGINS", "*").split(","),
        description="Allowed CORS origins",
    )

    require_auth: bool = Field(
        default_factory=lambda: os.getenv("WEBSOCKET_REQUIRE_AUTH", "true").lower()
        == "true",
        description="Require authentication for connections",
    )

    tenant_isolation: bool = Field(
        default_factory=lambda: os.getenv("WEBSOCKET_TENANT_ISOLATION", "true").lower()
        == "true",
        description="Enable tenant-based message isolation",
    )

    # Logging Configuration
    log_level: LogLevel = Field(
        default_factory=lambda: LogLevel(os.getenv("LOG_LEVEL", "INFO")),
        description="Logging level",
    )

    # Service Integration
    service_registry_enabled: bool = Field(
        default_factory=lambda: os.getenv("SERVICE_REGISTRY_ENABLED", "true").lower()
        == "true",
        description="Enable service registry integration",
    )

    health_check_interval: int = Field(
        default_factory=lambda: int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
        description="Health check interval in seconds",
    )

    metrics_port: int = Field(
        default_factory=lambda: int(os.getenv("METRICS_PORT", "9090")),
        description="Prometheus metrics port",
    )

    # Performance Tuning
    worker_count: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_WORKER_COUNT", "1")),
        description="Number of worker processes",
    )

    buffer_size: int = Field(
        default_factory=lambda: int(os.getenv("WEBSOCKET_BUFFER_SIZE", "65536")),
        description="WebSocket buffer size in bytes",
    )

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v):
        if v <= 0:
            raise ValueError("max_connections must be positive")
        if v > 50000:
            raise ValueError("max_connections too high (max 50000)")
        return v

    @field_validator("heartbeat_interval")
    @classmethod
    def validate_heartbeat_interval(cls, v):
        if v < 10 or v > 300:
            raise ValueError("heartbeat_interval must be between 10 and 300 seconds")
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v):
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("redis_url must start with redis:// or rediss://")
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        if not v:
            raise ValueError("cors_origins cannot be empty")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return os.getenv("ENVIRONMENT", "").lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return os.getenv("ENVIRONMENT", "").lower() in ("development", "dev")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump()

    @classmethod
    def from_env(cls) -> "WebSocketConfig":
        """Create config from environment variables."""
        return cls()

    @classmethod
    def for_testing(cls) -> "WebSocketConfig":
        """Create config optimized for testing."""
        return cls(
            max_connections=100,
            heartbeat_interval=5,
            connection_timeout=30,
            message_ttl=60,
            redis_url="redis://localhost:6379/15",  # Test database
            enable_persistence=False,
            enable_metrics=False,
            log_level=LogLevel.DEBUG,
            require_auth=False,
        )

    @classmethod
    def for_production(cls) -> "WebSocketConfig":
        """Create config optimized for production."""
        return cls(
            max_connections=10000,
            heartbeat_interval=30,
            connection_timeout=300,
            message_ttl=300,
            enable_persistence=True,
            enable_metrics=True,
            log_level=LogLevel.INFO,
            require_auth=True,
            tenant_isolation=True,
        )
