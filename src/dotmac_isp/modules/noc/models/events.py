"""
NOC Event Models.

Database models for network events, logs, and operational tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EventType(str, Enum):
    """Network event types."""
    DEVICE_STATE_CHANGE = "device_state_change"
    INTERFACE_STATE_CHANGE = "interface_state_change"
    CONFIGURATION_CHANGE = "configuration_change"
    METRIC_THRESHOLD_BREACH = "metric_threshold_breach"
    SERVICE_STATE_CHANGE = "service_state_change"
    CUSTOMER_EVENT = "customer_event"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    MAINTENANCE_EVENT = "maintenance_event"
    CUSTOM_EVENT = "custom_event"


class EventSeverity(str, Enum):
    """Event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NetworkEvent(Base):
    """Network event tracking model."""
    
    __tablename__ = "noc_events"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Event classification
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    category = Column(String(100), index=True)
    
    # Source information
    source_system = Column(String(100))
    device_id = Column(String(255), index=True)
    interface_id = Column(String(255), index=True)
    service_id = Column(String(255), index=True)
    customer_id = Column(String(255), index=True)
    
    # Event details
    title = Column(String(500), nullable=False)
    description = Column(Text)
    raw_data = Column(JSON)
    
    # State tracking
    previous_state = Column(String(100))
    current_state = Column(String(100))
    
    # Correlation and grouping
    correlation_id = Column(String(255), index=True)
    parent_event_id = Column(String(255), index=True)
    root_cause_event_id = Column(String(255), index=True)
    
    # Operational context
    maintenance_window_id = Column(String(255), index=True)
    change_request_id = Column(String(255), index=True)
    
    # Additional metadata
    tags = Column(JSON)
    custom_fields = Column(JSON)
    
    # Timestamps
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "category": self.category,
            "source_system": self.source_system,
            "device_id": self.device_id,
            "interface_id": self.interface_id,
            "service_id": self.service_id,
            "customer_id": self.customer_id,
            "title": self.title,
            "description": self.description,
            "raw_data": self.raw_data,
            "previous_state": self.previous_state,
            "current_state": self.current_state,
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "root_cause_event_id": self.root_cause_event_id,
            "maintenance_window_id": self.maintenance_window_id,
            "change_request_id": self.change_request_id,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
            "event_timestamp": self.event_timestamp.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat(),
        }


class EventRule(Base):
    """Event processing and correlation rules."""
    
    __tablename__ = "noc_event_rules"
    
    id = Column(Integer, primary_key=True)
    rule_id = Column(String(255), unique=True, nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Rule definition
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_enabled = Column(String(10), default="true")
    rule_priority = Column(Integer, default=100)
    
    # Event matching criteria
    event_type_pattern = Column(String(255))
    device_filter = Column(JSON)
    severity_filter = Column(JSON)
    content_filter = Column(JSON)
    
    # Processing actions
    action_type = Column(String(50))  # correlate, suppress, escalate, notify
    action_config = Column(JSON)
    
    # Correlation settings
    correlation_window_minutes = Column(Integer, default=60)
    correlation_key_fields = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))