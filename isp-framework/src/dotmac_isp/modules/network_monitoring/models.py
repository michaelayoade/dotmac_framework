"""Network monitoring database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    BigInteger,
    Index,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class MonitoringStatus(str, Enum):
    """Monitoring status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    DISABLED = "disabled"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status enumeration."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class MetricType(str, Enum):
    """Metric type enumeration."""

    GAUGE = "gauge"
    COUNTER = "counter"
    COUNTER64 = "counter64"
    DERIVE = "derive"
    ABSOLUTE = "absolute"


class DeviceStatus(str, Enum):
    """Device availability status."""

    UP = "up"
    DOWN = "down"
    WARNING = "warning"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class ScheduleType(str, Enum):
    """Monitoring schedule types."""

    INTERVAL = "interval"
    CRON = "cron"
    ON_DEMAND = "on_demand"


class MonitoringProfile(TenantModel, StatusMixin, AuditMixin):
    """Monitoring profile for device monitoring configuration."""

    __tablename__ = "monitoring_profiles"

    # Profile identification
    profile_name = Column(String(255), nullable=False, index=True)
    profile_type = Column(
        String(100), nullable=False, index=True
    )  # system, interface, custom

    # SNMP configuration
    snmp_version = Column(String(10), default="v2c", nullable=False)
    snmp_community = Column(String(100), nullable=True)  # For v1/v2c
    snmp_port = Column(Integer, default=161, nullable=False)
    snmp_timeout = Column(Integer, default=5, nullable=False)
    snmp_retries = Column(Integer, default=3, nullable=False)

    # SNMPv3 authentication (stored securely)
    snmp_v3_username = Column(String(100), nullable=True)
    snmp_v3_auth_protocol = Column(String(20), nullable=True)  # MD5, SHA
    snmp_v3_auth_key = Column(String(255), nullable=True)  # Encrypted
    snmp_v3_priv_protocol = Column(String(20), nullable=True)  # DES, AES
    snmp_v3_priv_key = Column(String(255), nullable=True)  # Encrypted

    # Monitoring configuration
    monitoring_interval = Column(Integer, default=300, nullable=False)  # seconds
    collection_timeout = Column(Integer, default=30, nullable=False)  # seconds

    # OID configuration
    oids_to_monitor = Column(JSON, nullable=False)  # List of OIDs with metadata
    custom_oids = Column(JSON, nullable=True)  # Additional custom OIDs

    # Data retention
    data_retention_days = Column(Integer, default=30, nullable=False)
    aggregation_rules = Column(JSON, nullable=True)  # Data aggregation configuration

    # Device targeting
    device_types = Column(JSON, nullable=True)  # List of applicable device types
    device_vendors = Column(JSON, nullable=True)  # List of applicable vendors
    device_models = Column(JSON, nullable=True)  # List of applicable models

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    devices = relationship("SnmpDevice", back_populates="monitoring_profile")
    alert_rules = relationship("AlertRule", back_populates="monitoring_profile")

    __table_args__ = (
        Index(
            "ix_monitoring_profiles_tenant_name",
            "tenant_id",
            "profile_name",
            unique=True,
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<MonitoringProfile(name='{self.profile_name}', type='{self.profile_type}')>"


class SnmpDevice(TenantModel, StatusMixin, AuditMixin):
    """SNMP-enabled device for monitoring."""

    __tablename__ = "snmp_devices"

    monitoring_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitoring_profiles.id"),
        nullable=False,
        index=True,
    )
    network_device_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to network device

    # Device identification
    device_name = Column(String(255), nullable=False, index=True)
    device_ip = Column(INET, nullable=False, unique=True, index=True)
    device_type = Column(String(100), nullable=True)
    device_vendor = Column(String(100), nullable=True)
    device_model = Column(String(100), nullable=True)

    # SNMP configuration (can override profile defaults)
    snmp_version_override = Column(String(10), nullable=True)
    snmp_community_override = Column(String(100), nullable=True)
    snmp_port_override = Column(Integer, nullable=True)

    # Monitoring status
    monitoring_enabled = Column(Boolean, default=True, nullable=False, index=True)
    monitoring_status = Column(
        SQLEnum(MonitoringStatus),
        default=MonitoringStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_monitored = Column(DateTime(timezone=True), nullable=True, index=True)

    # Device availability
    availability_status = Column(
        SQLEnum(DeviceStatus), default=DeviceStatus.UNKNOWN, nullable=False, index=True
    )
    last_seen = Column(DateTime(timezone=True), nullable=True)
    response_time_ms = Column(Float, nullable=True)
    uptime_seconds = Column(BigInteger, nullable=True)

    # Error tracking
    consecutive_failures = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    last_error_time = Column(DateTime(timezone=True), nullable=True)

    # Performance metrics (latest values)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    temperature_celsius = Column(Float, nullable=True)

    # Additional device information
    sys_description = Column(Text, nullable=True)
    sys_location = Column(String(255), nullable=True)
    sys_contact = Column(String(255), nullable=True)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    monitoring_profile = relationship("MonitoringProfile", back_populates="devices")
    metrics = relationship(
        "SnmpMetric", back_populates="device", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "MonitoringAlert", back_populates="device", cascade="all, delete-orphan"
    )
    availability_records = relationship("DeviceAvailability", back_populates="device")
    interface_metrics = relationship("InterfaceMetric", back_populates="device")
    system_metrics = relationship("SystemMetric", back_populates="device")
    schedules = relationship("MonitoringSchedule", back_populates="device")

    @hybrid_property
    def is_available(self) -> bool:
        """Check if device is currently available."""
        return self.availability_status == DeviceStatus.UP

    @hybrid_property
    def failure_rate(self) -> float:
        """Calculate recent failure rate."""
        # This would be calculated from recent availability records
        return 0.0

    def __repr__(self):
        """  Repr   operation."""
        return f"<SnmpDevice(name='{self.device_name}', ip='{self.device_ip}', status='{self.availability_status}')>"


class SnmpMetric(TenantModel):
    """SNMP metric data model."""

    __tablename__ = "snmp_metrics"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("snmp_devices.id"), nullable=False, index=True
    )

    # Metric identification
    metric_name = Column(String(255), nullable=False, index=True)
    metric_oid = Column(String(255), nullable=False)
    metric_type = Column(SQLEnum(MetricType), nullable=False)
    metric_instance = Column(String(100), nullable=True)  # For table-based metrics

    # Metric data
    value = Column(Numeric(precision=20, scale=4), nullable=False)
    raw_value = Column(String(255), nullable=True)  # Original SNMP value
    unit = Column(String(50), nullable=True)

    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    collection_time_ms = Column(Float, nullable=True)  # Time taken to collect

    # Context and metadata
    labels = Column(JSON, nullable=True)  # Additional metric labels
    context = Column(JSON, nullable=True)  # Collection context

    # Relationships
    device = relationship("SnmpDevice", back_populates="metrics")

    __table_args__ = (
        Index(
            "ix_snmp_metrics_device_name_time", "device_id", "metric_name", "timestamp"
        ),
        Index("ix_snmp_metrics_oid_time", "metric_oid", "timestamp"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<SnmpMetric(device='{self.device.device_name if self.device else 'Unknown'}', metric='{self.metric_name}', value={self.value})>"


class MonitoringAlert(TenantModel, AuditMixin):
    """Network monitoring alerts model."""

    __tablename__ = "monitoring_alerts"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("snmp_devices.id"), nullable=True, index=True
    )
    alert_rule_id = Column(
        UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=True, index=True
    )

    # Alert identification
    alert_id = Column(String(100), nullable=False, unique=True, index=True)
    alert_name = Column(String(255), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False, index=True)

    # Alert content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)

    # Alert status and lifecycle
    status = Column(
        SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Alert context
    metric_name = Column(String(255), nullable=True)
    metric_value = Column(Numeric(precision=20, scale=4), nullable=True)
    threshold_value = Column(Numeric(precision=20, scale=4), nullable=True)
    threshold_operator = Column(String(20), nullable=True)  # >, <, =, etc.

    # Assignee and handling
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), nullable=True)

    # Notification tracking
    notifications_sent = Column(
        JSON, nullable=True
    )  # List of notification channels used
    escalation_level = Column(Integer, default=0, nullable=False)

    # Additional context
    alert_data = Column(JSON, nullable=True)  # Additional alert context
    tags = Column(JSON, nullable=True)

    # Relationships
    device = relationship("SnmpDevice", back_populates="alerts")
    alert_rule = relationship("AlertRule", back_populates="alerts")

    __table_args__ = (
        Index("ix_network_alerts_device_status", "device_id", "status"),
        Index("ix_network_alerts_severity_time", "severity", "created_at"),
    )

    def acknowledge(self, user_id: str, comment: Optional[str] = None):
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
        if comment:
            if not self.alert_data:
                self.alert_data = {}
            self.alert_data["acknowledgment_comment"] = comment

    def resolve(self, user_id: str, comment: Optional[str] = None):
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_by = user_id
        self.resolved_at = datetime.utcnow()
        if comment:
            if not self.alert_data:
                self.alert_data = {}
            self.alert_data["resolution_comment"] = comment

    def __repr__(self):
        """  Repr   operation."""
        return f"<NetworkAlert(name='{self.alert_name}', severity='{self.severity}', status='{self.status}')>"


class AlertRule(TenantModel, StatusMixin, AuditMixin):
    """Alert rule configuration model."""

    __tablename__ = "alert_rules"

    monitoring_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("monitoring_profiles.id"),
        nullable=False,
        index=True,
    )

    # Rule identification
    rule_name = Column(String(255), nullable=False, index=True)
    rule_type = Column(
        String(100), nullable=False, index=True
    )  # threshold, anomaly, pattern, etc.

    # Rule conditions
    metric_name = Column(String(255), nullable=False, index=True)
    condition_operator = Column(String(20), nullable=False)  # >, <, =, >=, <=, !=
    threshold_value = Column(Numeric(precision=20, scale=4), nullable=False)
    threshold_unit = Column(String(50), nullable=True)

    # Time-based conditions
    evaluation_window = Column(Integer, default=300, nullable=False)  # seconds
    evaluation_frequency = Column(Integer, default=60, nullable=False)  # seconds
    consecutive_violations = Column(Integer, default=1, nullable=False)

    # Alert configuration
    alert_severity = Column(SQLEnum(AlertSeverity), nullable=False)
    alert_template = Column(Text, nullable=True)  # Alert message template

    # Notification settings
    notification_channels = Column(JSON, nullable=True)  # List of notification channels
    notification_cooldown = Column(Integer, default=3600, nullable=False)  # seconds
    escalation_rules = Column(JSON, nullable=True)  # Escalation configuration

    # Rule application
    device_filters = Column(JSON, nullable=True)  # Device selection criteria
    time_restrictions = Column(JSON, nullable=True)  # Time-based restrictions

    # Rule state
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    last_evaluation = Column(DateTime(timezone=True), nullable=True)
    evaluation_count = Column(Integer, default=0, nullable=False)
    alert_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    monitoring_profile = relationship("MonitoringProfile", back_populates="alert_rules")
    alerts = relationship("MonitoringAlert", back_populates="alert_rule")

    __table_args__ = (
        Index("ix_alert_rules_tenant_name", "tenant_id", "rule_name", unique=True),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<AlertRule(name='{self.rule_name}', metric='{self.metric_name}', severity='{self.alert_severity}')>"


class MonitoringSchedule(TenantModel, StatusMixin, AuditMixin):
    """Monitoring schedule configuration."""

    __tablename__ = "monitoring_schedules"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("snmp_devices.id"), nullable=False, index=True
    )

    # Schedule identification
    schedule_name = Column(String(255), nullable=False, index=True)
    schedule_type = Column(SQLEnum(ScheduleType), nullable=False)

    # Schedule configuration
    interval_seconds = Column(Integer, nullable=True)  # For interval-based schedules
    cron_expression = Column(String(100), nullable=True)  # For cron-based schedules
    timezone = Column(String(50), default="UTC", nullable=False)

    # Execution window
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Monitoring configuration
    metrics_to_collect = Column(JSON, nullable=False)  # List of metrics to collect
    collection_timeout = Column(Integer, default=30, nullable=False)

    # Schedule state
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    last_execution = Column(DateTime(timezone=True), nullable=True)
    next_execution = Column(DateTime(timezone=True), nullable=True, index=True)
    execution_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    device = relationship("SnmpDevice", back_populates="schedules")

    def __repr__(self):
        """  Repr   operation."""
        return f"<MonitoringSchedule(name='{self.schedule_name}', device='{self.device.device_name if self.device else 'Unknown'}')>"


class DeviceAvailability(TenantModel):
    """Device availability tracking model."""

    __tablename__ = "device_availability"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("snmp_devices.id"), nullable=False, index=True
    )

    # Availability data
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(SQLEnum(DeviceStatus), nullable=False)
    response_time_ms = Column(Float, nullable=True)

    # Check details
    check_method = Column(String(50), default="snmp", nullable=False)  # snmp, ping, tcp
    check_details = Column(JSON, nullable=True)  # Additional check information

    # Failure information
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # Relationships
    device = relationship("SnmpDevice", back_populates="availability_records")

    __table_args__ = (
        Index("ix_device_availability_device_time", "device_id", "timestamp"),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<DeviceAvailability(device='{self.device.device_name if self.device else 'Unknown'}', status='{self.status}', time='{self.timestamp}')>"


class InterfaceMetric(TenantModel):
    """Interface-specific metrics model."""

    __tablename__ = "interface_metrics"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("snmp_devices.id"), nullable=False, index=True
    )

    # Interface identification
    interface_index = Column(Integer, nullable=False, index=True)
    interface_name = Column(String(255), nullable=True)
    interface_description = Column(Text, nullable=True)

    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Interface status
    admin_status = Column(Integer, nullable=True)  # 1=up, 2=down, 3=testing
    operational_status = Column(Integer, nullable=True)  # 1=up, 2=down, 3=testing, etc.

    # Traffic counters
    in_octets = Column(BigInteger, nullable=True)
    out_octets = Column(BigInteger, nullable=True)
    in_packets = Column(BigInteger, nullable=True)
    out_packets = Column(BigInteger, nullable=True)
    in_errors = Column(BigInteger, nullable=True)
    out_errors = Column(BigInteger, nullable=True)
    in_discards = Column(BigInteger, nullable=True)
    out_discards = Column(BigInteger, nullable=True)

    # High-capacity counters (64-bit)
    hc_in_octets = Column(BigInteger, nullable=True)
    hc_out_octets = Column(BigInteger, nullable=True)

    # Interface properties
    interface_speed = Column(BigInteger, nullable=True)  # bits per second
    high_speed = Column(Integer, nullable=True)  # Mbps for high-speed interfaces

    # Utilization calculations (derived)
    in_utilization_percent = Column(Float, nullable=True)
    out_utilization_percent = Column(Float, nullable=True)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    device = relationship("SnmpDevice", back_populates="interface_metrics")

    __table_args__ = (
        Index(
            "ix_interface_metrics_device_if_time",
            "device_id",
            "interface_index",
            "timestamp",
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<InterfaceMetric(device='{self.device.device_name if self.device else 'Unknown'}', interface={self.interface_index})>"


class SystemMetric(TenantModel):
    """System-level metrics model."""

    __tablename__ = "system_metrics"

    device_id = Column(
        UUID(as_uuid=True), ForeignKey("snmp_devices.id"), nullable=False, index=True
    )

    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # System information
    system_uptime = Column(BigInteger, nullable=True)  # In timeticks (1/100th second)
    system_uptime_seconds = Column(BigInteger, nullable=True)  # Converted to seconds

    # CPU metrics
    cpu_usage_percent = Column(Float, nullable=True)
    cpu_5min_percent = Column(Float, nullable=True)
    cpu_1min_percent = Column(Float, nullable=True)

    # Memory metrics
    memory_total_bytes = Column(BigInteger, nullable=True)
    memory_used_bytes = Column(BigInteger, nullable=True)
    memory_free_bytes = Column(BigInteger, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)

    # Storage metrics
    storage_total_bytes = Column(BigInteger, nullable=True)
    storage_used_bytes = Column(BigInteger, nullable=True)
    storage_usage_percent = Column(Float, nullable=True)

    # Environmental metrics
    temperature_celsius = Column(Float, nullable=True)
    power_consumption_watts = Column(Float, nullable=True)
    fan_speed_rpm = Column(Integer, nullable=True)

    # Process and session counts
    process_count = Column(Integer, nullable=True)
    active_sessions = Column(Integer, nullable=True)

    # Additional metrics
    custom_metrics = Column(JSON, nullable=True)

    # Relationships
    device = relationship("SnmpDevice", back_populates="system_metrics")

    __table_args__ = (Index("ix_system_metrics_device_time", "device_id", "timestamp"),)

    def __repr__(self):
        """  Repr   operation."""
        return f"<SystemMetric(device='{self.device.device_name if self.device else 'Unknown'}', time='{self.timestamp}')>"
