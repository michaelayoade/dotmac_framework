"""
Report models for scheduled analytics and business intelligence.
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


class Report(Base):
    """Report definition and configuration."""

    __tablename__ = "analytics_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Report metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    report_type = Column(String(50), nullable=False)
    category = Column(String(100), index=True)

    # Data configuration
    dataset_ids = Column(JSON, default=list)
    metric_ids = Column(JSON, default=list)
    query_config = Column(JSON, nullable=False)

    # Report configuration
    template_config = Column(JSON, default=dict)
    output_formats = Column(JSON, default=["pdf", "excel"])

    # Scheduling
    schedule_frequency = Column(String(50))
    schedule_config = Column(JSON, default=dict)  # cron, time zones, etc.

    # Distribution
    recipients = Column(JSON, default=list)
    delivery_method = Column(String(50), default="email")

    # State
    is_active = Column(Boolean, default=True)
    last_generated = Column(DateTime)
    next_generation = Column(DateTime)

    # Statistics
    generation_count = Column(Integer, default=0)
    avg_generation_time = Column(Float)

    # Access control
    owner_id = Column(String(255), nullable=False, index=True)
    shared_with = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_reports_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_reports_type_active", "report_type", "is_active"),
        Index("ix_reports_next_generation", "next_generation"),
    )


class ReportExecution(Base):
    """Report execution history and results."""

    __tablename__ = "analytics_report_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Execution metadata
    execution_id = Column(String(255), unique=True, nullable=False)
    triggered_by = Column(String(50))  # schedule, manual, api
    triggered_by_user = Column(String(255))

    # Execution details
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    # Status and results
    status = Column(String(50), nullable=False, index=True)  # running, completed, failed
    error_message = Column(Text)

    # Output
    output_files = Column(JSON, default=list)
    output_size_bytes = Column(Integer)

    # Data statistics
    rows_processed = Column(Integer)
    data_freshness = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_report_executions_report_started", "report_id", "started_at"),
        Index("ix_report_executions_status_started", "status", "started_at"),
    )


class ReportTemplate(Base):
    """Report templates for consistent formatting."""

    __tablename__ = "analytics_report_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Template metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    report_type = Column(String(50), nullable=False)

    # Template configuration
    template_content = Column(Text, nullable=False)  # HTML, Markdown, etc.
    style_config = Column(JSON, default=dict)

    # Supported formats
    output_formats = Column(JSON, default=["pdf", "html"])

    # Usage
    usage_count = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class ReportSubscription(Base):
    """User subscriptions to reports."""

    __tablename__ = "analytics_report_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Subscriber information
    user_id = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False)

    # Subscription preferences
    delivery_method = Column(String(50), default="email")
    preferred_format = Column(String(20), default="pdf")
    frequency_override = Column(String(50))  # Override report's default frequency

    # Filters and customization
    custom_filters = Column(JSON, default=dict)
    custom_parameters = Column(JSON, default=dict)

    # State
    is_active = Column(Boolean, default=True)
    last_delivered = Column(DateTime)
    delivery_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_report_subscriptions_user_active", "user_id", "is_active"),
        Index("ix_report_subscriptions_report_active", "report_id", "is_active"),
    )


class ReportAlert(Base):
    """Alerts based on report data conditions."""

    __tablename__ = "analytics_report_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Alert configuration
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Condition configuration
    condition_config = Column(JSON, nullable=False)
    threshold_value = Column(Float)
    comparison_operator = Column(String(20))  # gt, lt, eq, etc.

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
