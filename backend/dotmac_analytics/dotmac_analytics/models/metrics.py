"""
Metrics models for analytics data collection and aggregation.
"""

import uuid
from datetime import datetime
from ..core.datetime_utils import utc_now
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Metric(Base):
    """Metric definition and metadata."""

    __tablename__ = "analytics_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Metric definition
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    metric_type = Column(String(50), nullable=False)

    # Data source
    source_table = Column(String(255))
    source_column = Column(String(255))
    source_query = Column(Text)

    # Aggregation
    aggregation_method = Column(String(50), nullable=False)
    dimensions = Column(JSON, default=list)
    filters = Column(JSON, default=dict)

    # Metadata
    unit = Column(String(50))
    format_string = Column(String(100))
    category = Column(String(100), index=True)
    tags = Column(JSON, default=list)

    # Configuration
    is_active = Column(Boolean, default=True)
    refresh_interval = Column(Integer, default=300)  # seconds
    retention_days = Column(Integer, default=90)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_metrics_tenant_name", "tenant_id", "name"),
        Index("ix_metrics_category_active", "category", "is_active"),
    )


class MetricValue(Base):
    """Time-series metric values."""

    __tablename__ = "analytics_metric_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    metric_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Value data
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)

    # Dimensions
    dimensions = Column(JSON, default=dict)

    # Metadata
    source = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_metric_values_metric_time", "metric_id", "timestamp"),
        Index("ix_metric_values_tenant_time", "tenant_id", "timestamp"),
    )


class MetricAggregate(Base):
    """Pre-aggregated metric values for performance."""

    __tablename__ = "analytics_metric_aggregates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    metric_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Time bucket
    time_bucket = Column(DateTime, nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # minute, hour, day, week, month

    # Aggregated values
    value_sum = Column(Float)
    value_avg = Column(Float)
    value_min = Column(Float)
    value_max = Column(Float)
    value_count = Column(Integer)
    value_stddev = Column(Float)

    # Percentiles
    value_p50 = Column(Float)
    value_p95 = Column(Float)
    value_p99 = Column(Float)

    # Dimensions
    dimensions = Column(JSON, default=dict)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_metric_aggregates_metric_time", "metric_id", "time_bucket"),
        Index("ix_metric_aggregates_granularity_time", "granularity", "time_bucket"),
    )


class MetricAlert(Base):
    """Metric-based alerts and thresholds."""

    __tablename__ = "analytics_metric_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    metric_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Alert definition
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Conditions
    condition_operator = Column(String(20), nullable=False)  # gt, lt, eq, etc.
    threshold_value = Column(Float, nullable=False)
    evaluation_window = Column(Integer, default=300)  # seconds

    # Notification
    notification_channels = Column(JSON, default=list)
    severity = Column(String(20), default="medium")

    # State
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class MetricAnnotation(Base):
    """Annotations for metrics (deployments, incidents, etc.)."""

    __tablename__ = "analytics_metric_annotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Annotation data
    timestamp = Column(DateTime, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Categorization
    category = Column(String(100), index=True)
    tags = Column(JSON, default=list)

    # Metadata
    user_id = Column(String(255))
    source = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_metric_annotations_tenant_time", "tenant_id", "timestamp"),
        Index("ix_metric_annotations_category_time", "category", "timestamp"),
    )
