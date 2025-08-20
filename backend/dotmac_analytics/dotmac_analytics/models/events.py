"""
Analytics event models for data collection and tracking.
"""

import uuid
from datetime import datetime
from ..core.datetime_utils import utc_now
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AnalyticsEvent(Base):
    """Analytics event for tracking user actions and system events."""

    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_name = Column(String(255), nullable=False, index=True)

    # Event context
    user_id = Column(String(255), index=True)
    session_id = Column(String(255), index=True)
    customer_id = Column(String(255), index=True)

    # Event data
    properties = Column(JSON, default=dict)
    context = Column(JSON, default=dict)

    # Metadata
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)
    source = Column(String(100))
    version = Column(String(20))

    # Processing
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime)

    # Indexes for performance
    __table_args__ = (
        Index("ix_analytics_events_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_analytics_events_type_name", "event_type", "event_name"),
        Index("ix_analytics_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_analytics_events_customer_timestamp", "customer_id", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "event_name": self.event_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "properties": self.properties,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "processed": self.processed,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }


class EventBatch(Base):
    """Batch of events for efficient processing."""

    __tablename__ = "analytics_event_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Batch metadata
    batch_size = Column(Integer, nullable=False)
    source = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Processing status
    status = Column(String(50), default="pending", index=True)
    processed_at = Column(DateTime)
    error_message = Column(Text)

    # Statistics
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)


class EventSchema(Base):
    """Schema definition for event validation."""

    __tablename__ = "analytics_event_schemas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Schema definition
    event_type = Column(String(50), nullable=False)
    event_name = Column(String(255), nullable=False)
    version = Column(String(20), nullable=False)

    # Schema content
    schema_definition = Column(JSON, nullable=False)
    required_properties = Column(JSON, default=list)
    optional_properties = Column(JSON, default=list)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_event_schemas_type_name_version", "event_type", "event_name", "version"),
    )


class EventAggregate(Base):
    """Pre-aggregated event data for fast queries."""

    __tablename__ = "analytics_event_aggregates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Aggregation dimensions
    event_type = Column(String(50), nullable=False, index=True)
    event_name = Column(String(255), nullable=False, index=True)
    time_bucket = Column(DateTime, nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # hour, day, week, month

    # Aggregated metrics
    event_count = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    unique_sessions = Column(Integer, default=0)
    unique_customers = Column(Integer, default=0)

    # Additional dimensions
    dimensions = Column(JSON, default=dict)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_event_aggregates_tenant_time", "tenant_id", "time_bucket"),
        Index("ix_event_aggregates_type_time", "event_type", "time_bucket"),
        Index("ix_event_aggregates_granularity_time", "granularity", "time_bucket"),
    )
