"""
Segmentation models for customer and user analytics.
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


class Segment(Base):
    """Customer/user segment definition for analytics."""

    __tablename__ = "analytics_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Segment metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)

    # Segment configuration
    entity_type = Column(String(50), nullable=False)  # customer, user, device, etc.
    rules_logic = Column(String(10), default="AND")  # AND, OR

    # Refresh settings
    is_dynamic = Column(Boolean, default=True)
    refresh_interval = Column(Integer, default=3600)  # seconds
    last_refresh = Column(DateTime)
    next_refresh = Column(DateTime)

    # Statistics
    member_count = Column(Integer, default=0)
    last_member_count = Column(Integer, default=0)

    # Access control
    owner_id = Column(String(255), nullable=False, index=True)
    is_public = Column(Boolean, default=False)

    # State
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_segments_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_segments_entity_type", "entity_type", "is_active"),
    )


class SegmentRule(Base):
    """Individual rules that define segment membership."""

    __tablename__ = "analytics_segment_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Rule configuration
    field_name = Column(String(255), nullable=False)
    operator = Column(String(50), nullable=False)
    value = Column(JSON)  # Can be string, number, array, etc.

    # Rule metadata
    rule_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Data source
    data_source = Column(String(100))  # events, metrics, datasets
    data_source_config = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_segment_rules_segment_order", "segment_id", "rule_order"),
    )


class SegmentMembership(Base):
    """Track segment membership for entities."""

    __tablename__ = "analytics_segment_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Entity information
    entity_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)

    # Membership metadata
    joined_at = Column(DateTime, nullable=False, default=utc_now)
    last_evaluated = Column(DateTime, nullable=False, default=utc_now)

    # Membership score (for probabilistic segments)
    membership_score = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_segment_memberships_segment_entity", "segment_id", "entity_id"),
        Index("ix_segment_memberships_entity_type", "entity_id", "entity_type"),
    )


class SegmentHistory(Base):
    """Historical tracking of segment membership changes."""

    __tablename__ = "analytics_segment_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Change information
    entity_id = Column(String(255), nullable=False, index=True)
    change_type = Column(String(20), nullable=False)  # joined, left
    change_timestamp = Column(DateTime, nullable=False, index=True)

    # Context
    trigger_reason = Column(String(100))  # rule_change, data_update, manual
    previous_score = Column(Float)
    new_score = Column(Float)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_segment_history_segment_time", "segment_id", "change_timestamp"),
        Index("ix_segment_history_entity_time", "entity_id", "change_timestamp"),
    )


class SegmentAnalytics(Base):
    """Analytics and insights about segment performance."""

    __tablename__ = "analytics_segment_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Time period
    analysis_date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly

    # Membership metrics
    member_count = Column(Integer, default=0)
    new_members = Column(Integer, default=0)
    lost_members = Column(Integer, default=0)
    retention_rate = Column(Float)

    # Behavioral metrics
    avg_engagement_score = Column(Float)
    avg_revenue_per_member = Column(Float)
    conversion_rate = Column(Float)

    # Segment health
    rule_match_rate = Column(Float)  # How well rules are performing
    data_freshness_score = Column(Float)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_segment_analytics_segment_date", "segment_id", "analysis_date"),
        Index("ix_segment_analytics_period_date", "period_type", "analysis_date"),
    )
