"""Plugin System Database Models."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Text,
    Integer,
    DateTime,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import TimestampMixin


class PluginStatusDB(enum.Enum):
    """Plugin status for database storage."""

    REGISTERED = "registered"
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


class PluginCategoryDB(enum.Enum):
    """Plugin category for database storage."""

    NETWORK_AUTOMATION = "network_automation"
    GIS_LOCATION = "gis_location"
    BILLING_INTEGRATION = "billing_integration"
    CRM_INTEGRATION = "crm_integration"
    MONITORING = "monitoring"
    TICKETING = "ticketing"
    COMMUNICATION = "communication"
    REPORTING = "reporting"
    SECURITY = "security"
    CUSTOM = "custom"


class PluginRegistry(TenantModel):
    """Database model for plugin registry."""

    __tablename__ = "plugin_registry"
    __table_args__ = (
        UniqueConstraint("tenant_id", "plugin_id", name="uq_tenant_plugin_id"),
        Index("idx_plugin_category_status", "category", "status"),
        Index("idx_plugin_tenant_status", "tenant_id", "status"),
    )

    # Plugin identification
    plugin_id = Column(String(255), nullable=False, index=True)
    plugin_name = Column(String(255), nullable=False)
    plugin_version = Column(String(50), nullable=False)
    plugin_description = Column(Text, nullable=True)
    plugin_author = Column(String(255), nullable=True)

    # Plugin metadata
    category = Column(Enum(PluginCategoryDB), nullable=False, index=True)
    status = Column(
        Enum(PluginStatusDB),
        default=PluginStatusDB.REGISTERED,
        nullable=False,
        index=True,
    )

    # Installation information
    installed_at = Column(DateTime(timezone=True), nullable=True)
    installed_by = Column(UUID(as_uuid=True), nullable=True)  # User who installed

    # Plugin source and location
    source_type = Column(String(50), nullable=False)  # file, module, package, git
    source_location = Column(String(500), nullable=False)
    source_hash = Column(String(255), nullable=True)  # SHA256 hash for integrity

    # Dependencies and requirements
    dependencies = Column(JSONB, nullable=True)  # List of plugin IDs this depends on
    python_requires = Column(String(50), default=">=3.11", nullable=False)

    # Capabilities and features
    supports_multi_tenant = Column(Boolean, default=True, nullable=False)
    supports_hot_reload = Column(Boolean, default=False, nullable=False)
    requires_restart = Column(Boolean, default=False, nullable=False)

    # Security and permissions
    security_level = Column(String(20), default="standard", nullable=False)
    permissions_required = Column(JSONB, nullable=True)  # List of required permissions

    # Runtime information
    last_loaded = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)

    # Configuration
    default_config = Column(JSONB, nullable=True)
    config_schema = Column(JSONB, nullable=True)  # JSON schema for validation

    # Statistics and monitoring
    load_count = Column(Integer, default=0, nullable=False)
    total_uptime_seconds = Column(Integer, default=0, nullable=False)

    def record_load_success(self):
        """Record successful plugin load."""
        self.status = PluginStatusDB.ACTIVE
        self.last_loaded = datetime.now(timezone.utc)
        self.load_count += 1
        self.last_error = None

    def record_load_failure(self, error_message: str):
        """Record plugin load failure."""
        self.status = PluginStatusDB.ERROR
        self.last_error = error_message
        self.error_count += 1

    def reset_error_state(self):
        """Reset plugin error state."""
        self.status = PluginStatusDB.REGISTERED
        self.last_error = None


class PluginConfiguration(TenantModel):
    """Database model for plugin configurations per tenant."""

    __tablename__ = "plugin_configurations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "plugin_id", name="uq_tenant_plugin_config"),
        Index("idx_plugin_config_enabled", "enabled"),
        Index("idx_plugin_config_priority", "priority"),
    )

    # Plugin reference
    plugin_id = Column(String(255), nullable=False, index=True)
    plugin_registry_id = Column(
        UUID(as_uuid=True), nullable=True
    )  # FK to plugin registry

    # Configuration state
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(
        Integer, default=100, nullable=False
    )  # 0-1000, higher = higher priority

    # Configuration data
    config_data = Column(JSONB, nullable=True)  # Plugin-specific configuration
    environment_vars = Column(JSONB, nullable=True)  # Environment variables for plugin

    # Security and resource settings
    sandbox_enabled = Column(Boolean, default=True, nullable=False)
    resource_limits = Column(JSONB, nullable=True)  # CPU, memory, network limits

    # Monitoring and logging
    metrics_enabled = Column(Boolean, default=True, nullable=False)
    logging_enabled = Column(Boolean, default=True, nullable=False)
    log_level = Column(String(10), default="INFO", nullable=False)

    # Lifecycle settings
    auto_start = Column(Boolean, default=False, nullable=False)
    restart_on_failure = Column(Boolean, default=True, nullable=False)
    max_restart_attempts = Column(Integer, default=3, nullable=False)

    # Configuration metadata
    configured_by = Column(UUID(as_uuid=True), nullable=True)  # User who configured
    configuration_notes = Column(Text, nullable=True)

    # Validation tracking
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_errors = Column(JSONB, nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False)

    def mark_invalid(self, errors: list):
        """Mark configuration as invalid with errors."""
        self.is_valid = False
        self.validation_errors = errors
        self.enabled = False  # Auto-disable invalid configs

    def mark_valid(self):
        """Mark configuration as valid."""
        self.is_valid = True
        self.validation_errors = None
        self.last_validated = datetime.now(timezone.utc)


class PluginInstance(TenantModel):
    """Database model for tracking plugin instances and runtime state."""

    __tablename__ = "plugin_instances"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "plugin_id", "instance_id", name="uq_tenant_plugin_instance"
        ),
        Index("idx_plugin_instance_status", "status"),
        Index("idx_plugin_instance_started", "started_at"),
    )

    # Plugin and instance identification
    plugin_id = Column(String(255), nullable=False, index=True)
    instance_id = Column(
        String(255), default=lambda: str(uuid4()), nullable=False, index=True
    )

    # Runtime state
    status = Column(Enum(PluginStatusDB), nullable=False, index=True)
    process_id = Column(Integer, nullable=True)  # OS process ID if applicable

    # Lifecycle timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    # Resource usage
    cpu_usage_percent = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    network_bytes_sent = Column(Integer, default=0, nullable=False)
    network_bytes_received = Column(Integer, default=0, nullable=False)

    # Health and performance
    health_status = Column(String(20), default="unknown", nullable=False)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    restart_count = Column(Integer, default=0, nullable=False)

    # Context information
    context_data = Column(JSONB, nullable=True)  # Runtime context

    @property
    def uptime_seconds(self) -> int:
        """Calculate uptime in seconds."""
        if not self.started_at:
            return 0

        end_time = self.stopped_at or datetime.now(timezone.utc)
        return int((end_time - self.started_at).total_seconds())

    def record_start(self):
        """Record instance start."""
        self.status = PluginStatusDB.ACTIVE
        self.started_at = datetime.now(timezone.utc)
        self.stopped_at = None
        self.last_heartbeat = datetime.now(timezone.utc)

    def record_stop(self, reason: str = None):
        """Record instance stop."""
        self.status = PluginStatusDB.INACTIVE
        self.stopped_at = datetime.now(timezone.utc)
        if reason:
            self.last_error = reason

    def record_heartbeat(self):
        """Record heartbeat from instance."""
        self.last_heartbeat = datetime.now(timezone.utc)

    def record_error(self, error_message: str):
        """Record error from instance."""
        self.error_count += 1
        self.last_error = error_message

        # Update status if too many errors
        if self.error_count >= 5:
            self.status = PluginStatusDB.ERROR


class PluginEvent(TenantModel):
    """Database model for plugin lifecycle and operational events."""

    __tablename__ = "plugin_events"
    __table_args__ = (
        Index("idx_plugin_event_type", "event_type"),
        Index("idx_plugin_event_timestamp", "created_at"),
        Index("idx_plugin_event_plugin", "plugin_id", "created_at"),
    )

    # Event identification
    plugin_id = Column(String(255), nullable=False, index=True)
    instance_id = Column(String(255), nullable=True)

    # Event details
    event_type = Column(
        String(50), nullable=False, index=True
    )  # load, start, stop, error, config_change, etc.
    event_level = Column(
        String(10), default="INFO", nullable=False
    )  # DEBUG, INFO, WARN, ERROR, CRITICAL

    # Event data
    event_message = Column(Text, nullable=False)
    event_data = Column(JSONB, nullable=True)  # Additional structured data

    # Context information
    user_id = Column(UUID(as_uuid=True), nullable=True)  # User who triggered event
    source_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Performance metrics
    duration_ms = Column(Integer, nullable=True)  # Event duration if applicable

    # Correlation
    correlation_id = Column(String(255), nullable=True)  # For tracing related events
    parent_event_id = Column(UUID(as_uuid=True), nullable=True)  # For event hierarchies

    def __repr__(self) -> str:
        """  Repr   operation."""
        return f"<PluginEvent(plugin={self.plugin_id}, type={self.event_type}, level={self.event_level})>"


class PluginMetrics(TenantModel):
    """Database model for plugin metrics and performance data."""

    __tablename__ = "plugin_metrics"
    __table_args__ = (
        Index("idx_plugin_metrics_timestamp", "metric_timestamp"),
        Index("idx_plugin_metrics_plugin", "plugin_id", "metric_timestamp"),
        Index("idx_plugin_metrics_name", "metric_name"),
    )

    # Metric identification
    plugin_id = Column(String(255), nullable=False, index=True)
    instance_id = Column(String(255), nullable=True)
    metric_name = Column(String(255), nullable=False, index=True)

    # Metric data
    metric_value = Column(
        String(255), nullable=False
    )  # Store as string for flexibility
    metric_type = Column(String(20), nullable=False)  # counter, gauge, histogram, timer
    metric_unit = Column(String(20), nullable=True)  # bytes, seconds, requests, etc.

    # Timestamp
    metric_timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Labels and tags for filtering
    labels = Column(JSONB, nullable=True)  # Key-value pairs for metric dimensions

    def __repr__(self) -> str:
        """  Repr   operation."""
        return f"<PluginMetrics(plugin={self.plugin_id}, name={self.metric_name}, value={self.metric_value})>"
