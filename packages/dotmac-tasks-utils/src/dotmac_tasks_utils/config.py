"""Configuration management for dotmac-tasks-utils."""
from __future__ import annotations

import os

from pydantic import BaseModel, Field


class RedisConfig(BaseModel):
    """Redis connection configuration."""

    url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum Redis connection pool size"
    )
    socket_timeout: float = Field(
        default=5.0,
        gt=0,
        description="Socket timeout in seconds"
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout"
    )
    decode_responses: bool = Field(
        default=True,
        description="Decode Redis responses to strings"
    )


class RetryConfig(BaseModel):
    """Retry mechanism configuration."""

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum retry attempts"
    )
    base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Base delay in seconds"
    )
    backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff factor"
    )
    max_delay: float = Field(
        default=60.0,
        ge=1.0,
        le=3600.0,
        description="Maximum delay in seconds"
    )
    jitter: bool = Field(
        default=True,
        description="Add random jitter to delays"
    )


class TaskConfig(BaseModel):
    """Task execution configuration."""

    default_queue: str = Field(
        default="dotmac:tasks",
        description="Default queue name"
    )
    result_ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Task result TTL in seconds"
    )
    max_concurrent: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum concurrent task executions"
    )
    cleanup_interval: float = Field(
        default=300.0,
        ge=60.0,
        description="Cleanup interval in seconds"
    )
    task_timeout: float | None = Field(
        default=None,
        ge=1.0,
        description="Default task timeout in seconds"
    )


class IdempotencyConfig(BaseModel):
    """Idempotency configuration."""

    default_ttl: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Default idempotency key TTL in seconds"
    )
    include_result: bool = Field(
        default=True,
        description="Whether to store and return cached results"
    )
    key_prefix: str = Field(
        default="idempotency:",
        description="Prefix for idempotency keys"
    )


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    logging_enabled: bool = Field(
        default=True,
        description="Enable structured logging"
    )
    logging_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    max_metrics: int = Field(
        default=10000,
        ge=1000,
        le=100000,
        description="Maximum metrics to keep in memory"
    )


class DotmacTasksConfig(BaseModel):
    """Main configuration for dotmac-tasks-utils."""

    redis: RedisConfig = Field(default_factory=RedisConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    tasks: TaskConfig = Field(default_factory=TaskConfig)
    idempotency: IdempotencyConfig = Field(default_factory=IdempotencyConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @classmethod
    def from_env(cls, prefix: str = "DOTMAC_") -> DotmacTasksConfig:
        """Load configuration from environment variables."""
        return cls(
            redis=RedisConfig(
                url=os.getenv(f"{prefix}REDIS_URL", "redis://localhost:6379"),
                max_connections=int(os.getenv(f"{prefix}REDIS_MAX_CONN", "10")),
                socket_timeout=float(os.getenv(f"{prefix}REDIS_TIMEOUT", "5.0")),
                retry_on_timeout=os.getenv(f"{prefix}REDIS_RETRY", "true").lower() == "true",
            ),
            retry=RetryConfig(
                max_attempts=int(os.getenv(f"{prefix}MAX_ATTEMPTS", "3")),
                base_delay=float(os.getenv(f"{prefix}BASE_DELAY", "1.0")),
                backoff_factor=float(os.getenv(f"{prefix}BACKOFF_FACTOR", "2.0")),
                max_delay=float(os.getenv(f"{prefix}MAX_DELAY", "60.0")),
                jitter=os.getenv(f"{prefix}JITTER", "true").lower() == "true",
            ),
            tasks=TaskConfig(
                default_queue=os.getenv(f"{prefix}DEFAULT_QUEUE", "dotmac:tasks"),
                result_ttl=int(os.getenv(f"{prefix}RESULT_TTL", "3600")),
                max_concurrent=int(os.getenv(f"{prefix}MAX_CONCURRENT", "10")),
                cleanup_interval=float(os.getenv(f"{prefix}CLEANUP_INTERVAL", "300.0")),
                task_timeout=(
                    float(os.getenv(f"{prefix}TASK_TIMEOUT"))
                    if os.getenv(f"{prefix}TASK_TIMEOUT")
                    else None
                ),
            ),
            idempotency=IdempotencyConfig(
                default_ttl=int(os.getenv(f"{prefix}IDEMPOTENCY_TTL", "3600")),
                include_result=(
                    os.getenv(f"{prefix}IDEMPOTENCY_INCLUDE_RESULT", "true").lower() == "true"
                ),
                key_prefix=os.getenv(f"{prefix}IDEMPOTENCY_PREFIX", "idempotency:"),
            ),
            observability=ObservabilityConfig(
                logging_enabled=os.getenv(f"{prefix}LOGGING_ENABLED", "true").lower() == "true",
                logging_level=os.getenv(f"{prefix}LOGGING_LEVEL", "INFO"),
                metrics_enabled=os.getenv(f"{prefix}METRICS_ENABLED", "true").lower() == "true",
                max_metrics=int(os.getenv(f"{prefix}MAX_METRICS", "10000")),
            ),
        )


class ConfigManager:
    """Configuration manager with singleton pattern."""

    _instance: DotmacTasksConfig | None = None

    @classmethod
    def get_config(cls) -> DotmacTasksConfig:
        """Get the current configuration."""
        if cls._instance is None:
            cls._instance = DotmacTasksConfig.from_env()
        return cls._instance

    @classmethod
    def set_config(cls, config: DotmacTasksConfig) -> None:
        """Set the configuration instance."""
        cls._instance = config

    @classmethod
    def reload_config(cls) -> DotmacTasksConfig:
        """Reload configuration from environment."""
        cls._instance = DotmacTasksConfig.from_env()
        return cls._instance

    @classmethod
    def clear_config(cls) -> None:
        """Clear the configuration instance."""
        cls._instance = None
