"""
NOC Alarm Models.

Database models for network alarms, incidents, and operational events.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class AlarmSeverity(str, Enum):
    """Alarm severity levels."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INFO = "info"


class AlarmStatus(str, Enum):
    """Alarm status values."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    CLEARED = "cleared"
    SUPPRESSED = "suppressed"


class AlarmType(str, Enum):
    """Types of network alarms."""

    DEVICE_DOWN = "device_down"
    INTERFACE_DOWN = "interface_down"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    HIGH_BANDWIDTH = "high_bandwidth"
    CONFIGURATION_DRIFT = "config_drift"
    SECURITY_VIOLATION = "security_violation"
    SLA_VIOLATION = "sla_violation"
    CONNECTIVITY_LOSS = "connectivity_loss"
    POWER_FAILURE = "power_failure"
    TEMPERATURE_ALARM = "temperature_alarm"
    CUSTOM = "custom"


class Alarm(Base):
    """Network alarm model."""

    __tablename__ = "noc_alarms"

    id = Column(Integer, primary_key=True)
    alarm_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Alarm identification
    alarm_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=AlarmStatus.ACTIVE)

    # Source information
    device_id = Column(String(255), index=True)
    interface_id = Column(String(255), index=True)
    service_id = Column(String(255), index=True)
    customer_id = Column(String(255), index=True)

    # Alarm details
    title = Column(String(500), nullable=False)
    description = Column(Text)
    raw_message = Column(Text)

    # Operational data
    first_occurrence = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_occurrence = Column(DateTime, nullable=False, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)

    # State management
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(255))
    cleared_at = Column(DateTime)
    cleared_by = Column(String(255))

    # Additional context
    source_system = Column(String(100))
    correlation_id = Column(String(255), index=True)
    parent_alarm_id = Column(String(255), ForeignKey("noc_alarms.alarm_id"), index=True)

    # Metadata and context
    context_data = Column(JSON)
    tags = Column(JSON)  # List of tags for filtering

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent_alarm = relationship("Alarm", remote_side=[alarm_id])

    def to_dict(self) -> dict[str, Any]:
        """Convert alarm to dictionary representation."""
        return {
            "alarm_id": self.alarm_id,
            "tenant_id": self.tenant_id,
            "alarm_type": self.alarm_type,
            "severity": self.severity,
            "status": self.status,
            "device_id": self.device_id,
            "interface_id": self.interface_id,
            "service_id": self.service_id,
            "customer_id": self.customer_id,
            "title": self.title,
            "description": self.description,
            "first_occurrence": self.first_occurrence.isoformat()
            if self.first_occurrence
            else None,
            "last_occurrence": self.last_occurrence.isoformat()
            if self.last_occurrence
            else None,
            "occurrence_count": self.occurrence_count,
            "acknowledged_at": self.acknowledged_at.isoformat()
            if self.acknowledged_at
            else None,
            "acknowledged_by": self.acknowledged_by,
            "cleared_at": self.cleared_at.isoformat() if self.cleared_at else None,
            "cleared_by": self.cleared_by,
            "source_system": self.source_system,
            "correlation_id": self.correlation_id,
            "parent_alarm_id": self.parent_alarm_id,
            "context_data": self.context_data,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AlarmRule(Base):
    """Alarm generation rules."""

    __tablename__ = "noc_alarm_rules"

    id = Column(Integer, primary_key=True)
    rule_id = Column(String(255), unique=True, nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Rule definition
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_enabled = Column(String(10), default="true")

    # Trigger conditions
    metric_name = Column(String(255))
    threshold_value = Column(String(100))
    threshold_operator = Column(String(20))  # >, <, >=, <=, ==, !=
    evaluation_window_minutes = Column(Integer, default=5)

    # Target specification
    device_type = Column(String(100))
    device_tags = Column(JSON)
    interface_type = Column(String(100))

    # Alarm generation
    alarm_type = Column(String(50), nullable=False)
    alarm_severity = Column(String(20), nullable=False)
    alarm_title_template = Column(String(500))
    alarm_description_template = Column(Text)

    # Metadata
    rule_definition = Column(JSON)  # Complex rule logic
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
