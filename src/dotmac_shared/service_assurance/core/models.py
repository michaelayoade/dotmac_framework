"""Service Assurance database models and schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object

try:
    from sqlalchemy import JSON, Boolean, Column, DateTime
    from sqlalchemy import Enum as SQLEnum
    from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
    from sqlalchemy.dialects.postgresql import INET, UUID
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlalchemy.orm import relationship

    # Try to import shared base classes
    try:
        from dotmac_shared.database.base import AuditMixin, StatusMixin, TenantModel

        SHARED_BASE_AVAILABLE = True
    except ImportError:
        SHARED_BASE_AVAILABLE = False

    if not SHARED_BASE_AVAILABLE:
        # Fallback for when shared database components aren't available
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()

        class TenantModel(Base):
            """TenantModel implementation."""

            __abstract__ = True
            id = Column(UUID(as_uuid=True), primary_key=True)
            tenant_id = Column(String(100), nullable=False, index=True)

        class StatusMixin:
            """StatusMixin implementation."""

            __abstract__ = True
            is_active = Column(Boolean, default=True, nullable=False)

        class AuditMixin:
            """AuditMixin implementation."""

            __abstract__ = True
            created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
            updated_at = Column(
                DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
                nullable=False,
            )

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Create minimal stubs for when SQLAlchemy is not available
    Column = String = Text = Boolean = DateTime = Integer = None
    Float = JSON = ForeignKey = Index = SQLEnum = None
    UUID = INET = relationship = hybrid_property = None
    TenantModel = StatusMixin = AuditMixin = None

from .enums import (
    AlarmSeverity,
    AlarmStatus,
    AlarmType,
    CollectorStatus,
    EventType,
    FlowType,
    ProbeStatus,
    ProbeType,
    SLAComplianceStatus,
)

# Pydantic schemas (if available)
if PYDANTIC_AVAILABLE:

    class ProbeCreate(BaseModel):
        """Schema for creating a service probe."""

        model_config = ConfigDict(str_strip_whitespace=True)

        probe_name: str = Field(..., min_length=1, max_length=200)
        probe_type: ProbeType
        target: str = Field(..., min_length=1)
        interval: int = Field(default=30, ge=1, le=86400)
        timeout: int = Field(default=10, ge=1, le=300)
        parameters: Optional[Dict[str, Any]] = None
        enabled: bool = True
        sla_policy_id: Optional[str] = None
        description: Optional[str] = None

    class ProbeResponse(BaseModel):
        """Schema for probe response."""

        model_config = ConfigDict(from_attributes=True)

        probe_id: str
        probe_name: str
        probe_type: ProbeType
        target: str
        interval: int
        timeout: int
        parameters: Optional[Dict[str, Any]] = None
        enabled: bool
        sla_policy_id: Optional[str] = None
        status: ProbeStatus
        last_run: Optional[datetime] = None
        created_at: datetime
        updated_at: Optional[datetime] = None

    class ProbeResultCreate(BaseModel):
        """Schema for creating a probe result."""

        model_config = ConfigDict(str_strip_whitespace=True)

        probe_id: str
        success: bool
        response_time_ms: Optional[float] = None
        status_code: Optional[int] = None
        error_message: Optional[str] = None
        metrics: Optional[Dict[str, Any]] = None

    class ProbeResultResponse(BaseModel):
        """Schema for probe result response."""

        model_config = ConfigDict(from_attributes=True)

        result_id: str
        probe_id: str
        timestamp: datetime
        success: bool
        response_time_ms: Optional[float] = None
        status_code: Optional[int] = None
        error_message: Optional[str] = None
        metrics: Optional[Dict[str, Any]] = None

    class AlarmRuleCreate(BaseModel):
        """Schema for creating an alarm rule."""

        model_config = ConfigDict(str_strip_whitespace=True)

        rule_name: str = Field(..., min_length=1, max_length=200)
        event_type: EventType
        match_criteria: Dict[str, Any]
        severity: AlarmSeverity = AlarmSeverity.WARNING
        alarm_type: AlarmType = AlarmType.SYSTEM
        auto_clear: bool = False
        clear_conditions: Optional[Dict[str, Any]] = None
        description_template: Optional[str] = None
        enabled: bool = True

    class AlarmResponse(BaseModel):
        """Schema for alarm response."""

        model_config = ConfigDict(from_attributes=True)

        alarm_id: str
        device_id: Optional[str] = None
        alarm_type: AlarmType
        severity: AlarmSeverity
        title: str
        description: str
        source_event_id: Optional[str] = None
        status: AlarmStatus
        acknowledged: bool = False
        acknowledged_by: Optional[str] = None
        acknowledged_at: Optional[datetime] = None
        raised_at: datetime
        cleared_at: Optional[datetime] = None

    class FlowRecordCreate(BaseModel):
        """Schema for creating a flow record."""

        model_config = ConfigDict(str_strip_whitespace=True)

        collector_id: str
        exporter_ip: str
        src_addr: str
        dst_addr: str
        src_port: int = Field(ge=0, le=65535)
        dst_port: int = Field(ge=0, le=65535)
        protocol: int = Field(ge=0, le=255)
        packets: int = Field(ge=0)
        bytes: int = Field(ge=0)
        flow_start: Optional[datetime] = None
        flow_end: Optional[datetime] = None

    class FlowCollectorCreate(BaseModel):
        """Schema for creating a flow collector."""

        model_config = ConfigDict(str_strip_whitespace=True)

        collector_name: str = Field(..., min_length=1, max_length=200)
        flow_type: FlowType
        listen_port: int = Field(ge=1, le=65535)
        listen_address: str = "127.0.0.1"
        version: str = "9"
        sampling_rate: int = Field(default=1, ge=1)
        active_timeout: int = Field(default=1800, ge=1)
        inactive_timeout: int = Field(default=15, ge=1)

    class SLAPolicyCreate(BaseModel):
        """Schema for creating an SLA policy."""

        model_config = ConfigDict(str_strip_whitespace=True)

        policy_name: str = Field(..., min_length=1, max_length=200)
        availability_threshold: float = Field(default=99.9, ge=0, le=100)
        latency_threshold_ms: int = Field(default=100, ge=1)
        measurement_window_hours: int = Field(default=24, ge=1, le=8760)
        violation_threshold: int = Field(default=3, ge=1)
        notification_enabled: bool = True

else:
    # Create stub classes when Pydantic is not available
    class ProbeCreate:
        """ProbeCreate schema stub."""

        pass

    class ProbeResponse:
        """ProbeResponse schema stub."""

        pass

    class ProbeResultCreate:
        """ProbeResultCreate schema stub."""

        pass

    class ProbeResultResponse:
        """ProbeResultResponse schema stub."""

        pass

    class AlarmRuleCreate:
        """AlarmRuleCreate schema stub."""

        pass

    class AlarmResponse:
        """AlarmResponse schema stub."""

        pass

    class FlowRecordCreate:
        """FlowRecordCreate schema stub."""

        pass

    class FlowCollectorCreate:
        """FlowCollectorCreate schema stub."""

        pass

    class SLAPolicyCreate:
        """SLAPolicyCreate schema stub."""

        pass


# SQLAlchemy models (if available)
if SQLALCHEMY_AVAILABLE:

    class ServiceProbe(TenantModel, StatusMixin, AuditMixin):
        """Service assurance probe definition."""

        __tablename__ = "sa_probes"

        # Probe identification
        probe_id = Column(String(100), nullable=False, unique=True, index=True)
        probe_name = Column(String(200), nullable=False)
        description = Column(Text, nullable=True)

        # Probe configuration
        probe_type = Column(SQLEnum(ProbeType), nullable=False, index=True)
        target = Column(String(500), nullable=False)
        interval = Column(Integer, default=30, nullable=False)  # seconds
        timeout = Column(Integer, default=10, nullable=False)  # seconds
        parameters = Column(JSON, nullable=True)

        # Status and policy
        status = Column(
            SQLEnum(ProbeStatus),
            default=ProbeStatus.ENABLED,
            nullable=False,
            index=True,
        )
        sla_policy_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sa_sla_policies.id"),
            nullable=True,
            index=True,
        )

        # Execution tracking
        last_run = Column(DateTime, nullable=True)
        last_success = Column(DateTime, nullable=True)
        consecutive_failures = Column(Integer, default=0, nullable=False)

        # Relationships
        results = relationship(
            "ProbeResult", back_populates="probe", cascade="all, delete-orphan"
        )
        sla_policy = relationship("SLAPolicy", back_populates="probes")

        __table_args__ = (
            Index("ix_probes_tenant_type", "tenant_id", "probe_type"),
            Index("ix_probes_status_enabled", "status", "is_active"),
            Index("ix_probes_last_run", "last_run"),
        )

    class ProbeResult(TenantModel, AuditMixin):
        """Service probe execution result."""

        __tablename__ = "sa_probe_results"

        # Result identification
        result_id = Column(String(100), nullable=False, unique=True, index=True)
        probe_id = Column(
            UUID(as_uuid=True), ForeignKey("sa_probes.id"), nullable=False, index=True
        )

        # Result data
        timestamp = Column(
            DateTime, default=datetime.utcnow, nullable=False, index=True
        )
        success = Column(Boolean, nullable=False)
        response_time_ms = Column(Float, nullable=True)
        status_code = Column(Integer, nullable=True)
        error_message = Column(Text, nullable=True)
        metrics = Column(JSON, nullable=True)

        # Relationships
        probe = relationship("ServiceProbe", back_populates="results")

        __table_args__ = (
            Index("ix_probe_results_probe_time", "probe_id", "timestamp"),
            Index("ix_probe_results_success", "success", "timestamp"),
        )

    class AlarmRule(TenantModel, StatusMixin, AuditMixin):
        """Alarm generation rule."""

        __tablename__ = "sa_alarm_rules"

        # Rule identification
        rule_id = Column(String(100), nullable=False, unique=True, index=True)
        rule_name = Column(String(200), nullable=False)
        description = Column(Text, nullable=True)

        # Event matching
        event_type = Column(SQLEnum(EventType), nullable=False, index=True)
        match_criteria = Column(JSON, nullable=False)

        # Alarm configuration
        severity = Column(
            SQLEnum(AlarmSeverity), default=AlarmSeverity.WARNING, nullable=False
        )
        alarm_type = Column(
            SQLEnum(AlarmType), default=AlarmType.SYSTEM, nullable=False
        )
        auto_clear = Column(Boolean, default=False, nullable=False)
        clear_conditions = Column(JSON, nullable=True)
        description_template = Column(Text, nullable=True)

        # Status and metrics
        enabled = Column(Boolean, default=True, nullable=False)
        rule_priority = Column(Integer, default=0, nullable=False)
        alarms_generated = Column(Integer, default=0, nullable=False)
        last_triggered = Column(DateTime, nullable=True)

        # Relationships
        alarms = relationship("Alarm", back_populates="rule")

        __table_args__ = (
            Index("ix_alarm_rules_tenant_type", "tenant_id", "event_type"),
            Index("ix_alarm_rules_enabled", "enabled", "is_active"),
            Index("ix_alarm_rules_priority", "rule_priority"),
        )

    class Alarm(TenantModel, AuditMixin):
        """Network/service alarm."""

        __tablename__ = "sa_alarms"

        # Alarm identification
        alarm_id = Column(String(100), nullable=False, unique=True, index=True)
        device_id = Column(String(100), nullable=True, index=True)
        rule_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sa_alarm_rules.id"),
            nullable=True,
            index=True,
        )

        # Alarm details
        alarm_type = Column(SQLEnum(AlarmType), nullable=False, index=True)
        severity = Column(SQLEnum(AlarmSeverity), nullable=False, index=True)
        title = Column(String(500), nullable=False)
        description = Column(Text, nullable=True)
        source_event_id = Column(String(100), nullable=True, index=True)

        # Status tracking
        status = Column(
            SQLEnum(AlarmStatus), default=AlarmStatus.ACTIVE, nullable=False, index=True
        )
        acknowledged = Column(Boolean, default=False, nullable=False)
        acknowledged_by = Column(String(200), nullable=True)
        acknowledged_at = Column(DateTime, nullable=True)
        ack_comments = Column(Text, nullable=True)

        # Lifecycle timestamps
        raised_at = Column(
            DateTime, default=datetime.utcnow, nullable=False, index=True
        )
        cleared_at = Column(DateTime, nullable=True, index=True)
        cleared_by = Column(String(200), nullable=True)
        clear_comments = Column(Text, nullable=True)

        # Auto-clear configuration
        auto_clear = Column(Boolean, default=False, nullable=False)
        clear_conditions = Column(JSON, nullable=True)

        # Additional metadata
        tags = Column(JSON, nullable=True)
        custom_fields = Column(JSON, nullable=True)

        # Relationships
        rule = relationship("AlarmRule", back_populates="alarms")

        __table_args__ = (
            Index("ix_alarms_tenant_status", "tenant_id", "status"),
            Index("ix_alarms_device_severity", "device_id", "severity"),
            Index("ix_alarms_raised_cleared", "raised_at", "cleared_at"),
            Index("ix_alarms_acknowledged", "acknowledged", "status"),
        )

    class FlowCollector(TenantModel, StatusMixin, AuditMixin):
        """Network flow data collector."""

        __tablename__ = "sa_flow_collectors"

        # Collector identification
        collector_id = Column(String(100), nullable=False, unique=True, index=True)
        collector_name = Column(String(200), nullable=False)
        description = Column(Text, nullable=True)

        # Collector configuration
        flow_type = Column(SQLEnum(FlowType), nullable=False, index=True)
        listen_port = Column(Integer, nullable=False)
        listen_address = Column(INET, default="127.0.0.1", nullable=False)
        version = Column(String(10), default="9", nullable=False)
        sampling_rate = Column(Integer, default=1, nullable=False)
        active_timeout = Column(Integer, default=1800, nullable=False)
        inactive_timeout = Column(Integer, default=15, nullable=False)

        # Status and metrics
        status = Column(
            SQLEnum(CollectorStatus),
            default=CollectorStatus.ACTIVE,
            nullable=False,
            index=True,
        )
        flows_received = Column(Integer, default=0, nullable=False)
        last_flow = Column(DateTime, nullable=True)
        bytes_received = Column(Integer, default=0, nullable=False)

        # Relationships
        flow_records = relationship(
            "FlowRecord", back_populates="collector", cascade="all, delete-orphan"
        )

        __table_args__ = (
            Index("ix_flow_collectors_tenant_type", "tenant_id", "flow_type"),
            Index("ix_flow_collectors_status", "status", "is_active"),
            Index("ix_flow_collectors_port", "listen_port"),
        )

    class FlowRecord(TenantModel, AuditMixin):
        """Network flow record."""

        __tablename__ = "sa_flow_records"

        # Record identification
        flow_id = Column(String(100), nullable=False, unique=True, index=True)
        collector_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sa_flow_collectors.id"),
            nullable=False,
            index=True,
        )

        # Flow source
        exporter_ip = Column(INET, nullable=False, index=True)

        # Flow data
        src_addr = Column(INET, nullable=False, index=True)
        dst_addr = Column(INET, nullable=False, index=True)
        src_port = Column(Integer, nullable=False)
        dst_port = Column(Integer, nullable=False)
        protocol = Column(Integer, nullable=False, index=True)
        tos = Column(Integer, default=0, nullable=False)
        tcp_flags = Column(Integer, default=0, nullable=False)

        # Traffic metrics
        packets = Column(Integer, default=0, nullable=False)
        bytes = Column(Integer, default=0, nullable=False)

        # Timing
        flow_start = Column(DateTime, nullable=True)
        flow_end = Column(DateTime, nullable=True)
        ingested_at = Column(
            DateTime, default=datetime.utcnow, nullable=False, index=True
        )

        # SNMP interfaces
        input_snmp = Column(Integer, default=0, nullable=False)
        output_snmp = Column(Integer, default=0, nullable=False)

        # Routing information
        next_hop = Column(INET, nullable=True)
        src_as = Column(Integer, default=0, nullable=False)
        dst_as = Column(Integer, default=0, nullable=False)
        src_mask = Column(Integer, default=0, nullable=False)
        dst_mask = Column(Integer, default=0, nullable=False)

        # Relationships
        collector = relationship("FlowCollector", back_populates="flow_records")

        __table_args__ = (
            Index("ix_flow_records_tenant_time", "tenant_id", "ingested_at"),
            Index("ix_flow_records_src_dst", "src_addr", "dst_addr"),
            Index("ix_flow_records_protocol_ports", "protocol", "src_port", "dst_port"),
            Index("ix_flow_records_exporter", "exporter_ip", "ingested_at"),
        )

    class SLAPolicy(TenantModel, StatusMixin, AuditMixin):
        """Service Level Agreement policy."""

        __tablename__ = "sa_sla_policies"

        # Policy identification
        policy_id = Column(String(100), nullable=False, unique=True, index=True)
        policy_name = Column(String(200), nullable=False)
        description = Column(Text, nullable=True)

        # SLA thresholds
        availability_threshold = Column(
            Float, default=99.9, nullable=False
        )  # percentage
        latency_threshold_ms = Column(
            Integer, default=100, nullable=False
        )  # milliseconds

        # Measurement configuration
        measurement_window_hours = Column(Integer, default=24, nullable=False)
        violation_threshold = Column(Integer, default=3, nullable=False)

        # Notification settings
        notification_enabled = Column(Boolean, default=True, nullable=False)
        escalation_enabled = Column(Boolean, default=False, nullable=False)

        # Policy status
        violations_count = Column(Integer, default=0, nullable=False)
        last_violation = Column(DateTime, nullable=True)

        # Relationships
        probes = relationship("ServiceProbe", back_populates="sla_policy")
        violations = relationship("SLAViolation", back_populates="policy")

        __table_args__ = (
            Index("ix_sla_policies_tenant_status", "tenant_id", "is_active"),
            Index(
                "ix_sla_policies_thresholds",
                "availability_threshold",
                "latency_threshold_ms",
            ),
        )

    class SLAViolation(TenantModel, AuditMixin):
        """SLA policy violation record."""

        __tablename__ = "sa_sla_violations"

        # Violation identification
        violation_id = Column(String(100), nullable=False, unique=True, index=True)
        probe_id = Column(
            UUID(as_uuid=True), ForeignKey("sa_probes.id"), nullable=False, index=True
        )
        policy_id = Column(
            UUID(as_uuid=True),
            ForeignKey("sa_sla_policies.id"),
            nullable=False,
            index=True,
        )

        # Violation metrics
        availability_actual = Column(Float, nullable=False)
        availability_threshold = Column(Float, nullable=False)
        latency_actual = Column(Float, nullable=False)
        latency_threshold_ms = Column(Integer, nullable=False)
        measurement_window_hours = Column(Integer, nullable=False)

        # Detection details
        detected_at = Column(
            DateTime, default=datetime.utcnow, nullable=False, index=True
        )
        resolved_at = Column(DateTime, nullable=True, index=True)
        total_measurements = Column(Integer, nullable=False)
        successful_measurements = Column(Integer, nullable=False)

        # Relationships
        probe = relationship("ServiceProbe")
        policy = relationship("SLAPolicy", back_populates="violations")

        __table_args__ = (
            Index("ix_sla_violations_tenant_time", "tenant_id", "detected_at"),
            Index("ix_sla_violations_probe_policy", "probe_id", "policy_id"),
            Index("ix_sla_violations_resolved", "resolved_at"),
        )

else:
    # Create stub classes when SQLAlchemy is not available
    class ServiceProbe:
        """ServiceProbe model stub."""

        pass

    class ProbeResult:
        """ProbeResult model stub."""

        pass

    class AlarmRule:
        """AlarmRule model stub."""

        pass

    class Alarm:
        """Alarm model stub."""

        pass

    class FlowCollector:
        """FlowCollector model stub."""

        pass

    class FlowRecord:
        """FlowRecord model stub."""

        pass

    class SLAPolicy:
        """SLAPolicy model stub."""

        pass

    class SLAViolation:
        """SLAViolation model stub."""

        pass
