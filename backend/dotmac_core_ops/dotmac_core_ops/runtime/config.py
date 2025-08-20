"""
Runtime configuration for the DotMac Core Operations package.
"""

import os
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator


class AdapterType(str, Enum):
    """Adapter types for storage and messaging."""

    MEMORY = "memory"
    REDIS = "redis"
    POSTGRES = "postgres"
    MONGODB = "mongodb"
    KAFKA = "kafka"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Maximum overflow connections")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, description="Pool recycle time in seconds")
    echo: bool = Field(False, description="Enable SQL echo")

    class Config:
        extra = "forbid"


class RedisConfig(BaseModel):
    """Redis configuration."""

    url: str = Field("redis://localhost:6379", description="Redis connection URL")
    db: int = Field(0, description="Redis database number")
    max_connections: int = Field(100, description="Maximum connections")
    retry_on_timeout: bool = Field(True, description="Retry on timeout")
    socket_timeout: float = Field(5.0, description="Socket timeout")

    class Config:
        extra = "forbid"


class KafkaConfig(BaseModel):
    """Kafka configuration."""

    bootstrap_servers: List[str] = Field(["localhost:9092"], description="Kafka bootstrap servers")
    security_protocol: str = Field("PLAINTEXT", description="Security protocol")
    sasl_mechanism: Optional[str] = Field(None, description="SASL mechanism")
    sasl_username: Optional[str] = Field(None, description="SASL username")
    sasl_password: Optional[str] = Field(None, description="SASL password")
    ssl_cafile: Optional[str] = Field(None, description="SSL CA file")
    ssl_certfile: Optional[str] = Field(None, description="SSL cert file")
    ssl_keyfile: Optional[str] = Field(None, description="SSL key file")

    class Config:
        extra = "forbid"


class MongoConfig(BaseModel):
    """MongoDB configuration."""

    url: str = Field("mongodb://localhost:27017", description="MongoDB connection URL")
    database: str = Field("dotmac_ops", description="Database name")
    max_pool_size: int = Field(100, description="Maximum pool size")
    min_pool_size: int = Field(0, description="Minimum pool size")
    max_idle_time_ms: int = Field(0, description="Maximum idle time")

    class Config:
        extra = "forbid"


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str = Field(..., description="Secret key for signing")
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Access token expiration")
    refresh_token_expire_days: int = Field(7, description="Refresh token expiration")

    # API Keys
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")

    # CORS
    cors_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")
    cors_methods: List[str] = Field(["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    cors_headers: List[str] = Field(["*"], description="CORS allowed headers")

    class Config:
        extra = "forbid"


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    # Metrics
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    metrics_port: int = Field(9090, description="Metrics server port")

    # Tracing
    enable_tracing: bool = Field(False, description="Enable distributed tracing")
    jaeger_endpoint: Optional[str] = Field(None, description="Jaeger endpoint")

    # Logging
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    log_format: str = Field("json", description="Log format (json/text)")

    class Config:
        extra = "forbid"


class WorkflowConfig(BaseModel):
    """Workflow-specific configuration."""

    max_concurrent_executions: int = Field(100, description="Max concurrent workflow executions")
    execution_timeout_seconds: int = Field(3600, description="Default execution timeout")
    step_timeout_seconds: int = Field(300, description="Default step timeout")

    class Config:
        extra = "forbid"


class TaskConfig(BaseModel):
    """Task-specific configuration."""

    max_concurrent_tasks: int = Field(50, description="Max concurrent task executions")
    default_queue_size: int = Field(1000, description="Default queue size")
    worker_count: int = Field(5, description="Number of worker processes")

    class Config:
        extra = "forbid"


class SchedulerConfig(BaseModel):
    """Scheduler-specific configuration."""

    check_interval_seconds: int = Field(1, description="Schedule check interval")
    max_concurrent_jobs: int = Field(20, description="Max concurrent scheduled jobs")
    timezone: str = Field("UTC", description="Default timezone")

    class Config:
        extra = "forbid"


class JobQueueConfig(BaseModel):
    """Job queue-specific configuration."""

    default_queue_size: int = Field(5000, description="Default queue size")
    worker_concurrency: int = Field(10, description="Worker concurrency")
    dead_letter_queue_size: int = Field(1000, description="Dead letter queue size")

    class Config:
        extra = "forbid"


class OpsConfig(BaseModel):
    """Main operations configuration."""

    # Basic settings
    app_name: str = Field("DotMac Operations", description="Application name")
    app_version: str = Field("0.1.0", description="Application version")
    debug: bool = Field(False, description="Debug mode")

    # Server settings
    host: str = Field("127.0.0.1", description="Server host")
    port: int = Field(8000, description="Server port")
    workers: int = Field(1, description="Number of worker processes")

    # Adapter configuration
    storage_adapter: AdapterType = Field(AdapterType.MEMORY, description="Storage adapter type")
    message_adapter: AdapterType = Field(AdapterType.MEMORY, description="Message adapter type")

    # Component configurations
    database: Optional[DatabaseConfig] = Field(None, description="Database configuration")
    redis: Optional[RedisConfig] = Field(None, description="Redis configuration")
    kafka: Optional[KafkaConfig] = Field(None, description="Kafka configuration")
    mongodb: Optional[MongoConfig] = Field(None, description="MongoDB configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig, description="Observability configuration")

    # SDK configurations
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig, description="Workflow configuration")
    task: TaskConfig = Field(default_factory=TaskConfig, description="Task configuration")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Scheduler configuration")
    job_queue: JobQueueConfig = Field(default_factory=JobQueueConfig, description="Job queue configuration")

    @validator('security', pre=True)
    def validate_security(cls, v):
        if isinstance(v, dict) and 'secret_key' not in v:
            # Generate a default secret key if not provided
            import secrets
            v['secret_key'] = secrets.token_urlsafe(32)
        return v

    @classmethod
    def from_env(cls) -> "OpsConfig":
        """Create configuration from environment variables."""
        config_data = {}

        # Basic settings
        config_data["app_name"] = os.getenv("OPS_APP_NAME", "DotMac Operations")
        config_data["app_version"] = os.getenv("OPS_APP_VERSION", "0.1.0")
        config_data["debug"] = os.getenv("OPS_DEBUG", "false").lower() == "true"

        # Server settings
        config_data["host"] = os.getenv("OPS_HOST", "127.0.0.1")
        config_data["port"] = int(os.getenv("OPS_PORT", "8000"))
        config_data["workers"] = int(os.getenv("OPS_WORKERS", "1"))

        # Adapter settings
        config_data["storage_adapter"] = os.getenv("OPS_STORAGE_ADAPTER", "memory")
        config_data["message_adapter"] = os.getenv("OPS_MESSAGE_ADAPTER", "memory")

        # Database configuration
        if db_url := os.getenv("OPS_DATABASE_URL"):
            config_data["database"] = {
                "url": db_url,
                "pool_size": int(os.getenv("OPS_DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("OPS_DB_MAX_OVERFLOW", "20")),
                "echo": os.getenv("OPS_DB_ECHO", "false").lower() == "true",
            }

        # Redis configuration
        if redis_url := os.getenv("OPS_REDIS_URL"):
            config_data["redis"] = {
                "url": redis_url,
                "db": int(os.getenv("OPS_REDIS_DB", "0")),
                "max_connections": int(os.getenv("OPS_REDIS_MAX_CONNECTIONS", "100")),
            }

        # Kafka configuration
        if kafka_servers := os.getenv("OPS_KAFKA_BOOTSTRAP_SERVERS"):
            config_data["kafka"] = {
                "bootstrap_servers": kafka_servers.split(","),
                "security_protocol": os.getenv("OPS_KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
                "sasl_mechanism": os.getenv("OPS_KAFKA_SASL_MECHANISM"),
                "sasl_username": os.getenv("OPS_KAFKA_SASL_USERNAME"),
                "sasl_password": os.getenv("OPS_KAFKA_SASL_PASSWORD"),
            }

        # MongoDB configuration
        if mongo_url := os.getenv("OPS_MONGODB_URL"):
            config_data["mongodb"] = {
                "url": mongo_url,
                "database": os.getenv("OPS_MONGODB_DATABASE", "dotmac_ops"),
                "max_pool_size": int(os.getenv("OPS_MONGODB_MAX_POOL_SIZE", "100")),
            }

        # Security configuration
        config_data["security"] = {
            "secret_key": os.getenv("OPS_SECRET_KEY", ""),
            "algorithm": os.getenv("OPS_JWT_ALGORITHM", "HS256"),
            "access_token_expire_minutes": int(os.getenv("OPS_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            "api_keys": os.getenv("OPS_API_KEYS", "").split(",") if os.getenv("OPS_API_KEYS") else [],
            "cors_origins": os.getenv("OPS_CORS_ORIGINS", "").split(",") if os.getenv("OPS_CORS_ORIGINS") else [],
        }

        # Observability configuration
        config_data["observability"] = {
            "enable_metrics": os.getenv("OPS_ENABLE_METRICS", "true").lower() == "true",
            "metrics_port": int(os.getenv("OPS_METRICS_PORT", "9090")),
            "enable_tracing": os.getenv("OPS_ENABLE_TRACING", "false").lower() == "true",
            "jaeger_endpoint": os.getenv("OPS_JAEGER_ENDPOINT"),
            "log_level": os.getenv("OPS_LOG_LEVEL", "INFO"),
            "log_format": os.getenv("OPS_LOG_FORMAT", "json"),
        }

        # Workflow configuration
        config_data["workflow"] = {
            "max_concurrent_executions": int(os.getenv("OPS_WORKFLOW_MAX_CONCURRENT", "100")),
            "execution_timeout_seconds": int(os.getenv("OPS_WORKFLOW_EXECUTION_TIMEOUT", "3600")),
            "step_timeout_seconds": int(os.getenv("OPS_WORKFLOW_STEP_TIMEOUT", "300")),
        }

        # Task configuration
        config_data["task"] = {
            "max_concurrent_tasks": int(os.getenv("OPS_TASK_MAX_CONCURRENT", "50")),
            "default_queue_size": int(os.getenv("OPS_TASK_QUEUE_SIZE", "1000")),
            "worker_count": int(os.getenv("OPS_TASK_WORKER_COUNT", "5")),
        }

        # Scheduler configuration
        config_data["scheduler"] = {
            "check_interval_seconds": int(os.getenv("OPS_SCHEDULER_CHECK_INTERVAL", "1")),
            "max_concurrent_jobs": int(os.getenv("OPS_SCHEDULER_MAX_CONCURRENT", "20")),
            "timezone": os.getenv("OPS_SCHEDULER_TIMEZONE", "UTC"),
        }

        # Job queue configuration
        config_data["job_queue"] = {
            "default_queue_size": int(os.getenv("OPS_JOB_QUEUE_SIZE", "5000")),
            "worker_concurrency": int(os.getenv("OPS_JOB_WORKER_CONCURRENCY", "10")),
            "dead_letter_queue_size": int(os.getenv("OPS_DLQ_SIZE", "1000")),
        }

        return cls(**config_data)

    class Config:
        extra = "forbid"
        env_prefix = "OPS_"
