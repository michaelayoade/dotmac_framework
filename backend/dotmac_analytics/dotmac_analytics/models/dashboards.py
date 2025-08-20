"""
Dashboard and visualization models for analytics.
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


class Dashboard(Base):
    """Dashboard for organizing analytics visualizations."""

    __tablename__ = "analytics_dashboards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Dashboard metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)

    # Layout configuration
    layout = Column(JSON, default=dict)  # Grid layout configuration
    theme = Column(String(50), default="default")

    # Access control
    is_public = Column(Boolean, default=False)
    owner_id = Column(String(255), nullable=False, index=True)
    shared_with = Column(JSON, default=list)  # List of user/role IDs

    # Settings
    auto_refresh_interval = Column(Integer, default=300)  # seconds
    is_favorite = Column(Boolean, default=False)

    # Usage statistics
    view_count = Column(Integer, default=0)
    last_viewed = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_dashboards_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_dashboards_category_public", "category", "is_public"),
    )


class Widget(Base):
    """Dashboard widget for data visualization."""

    __tablename__ = "analytics_widgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    dashboard_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Widget metadata
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    widget_type = Column(String(50), nullable=False)

    # Data configuration
    dataset_id = Column(UUID(as_uuid=True), index=True)
    metric_ids = Column(JSON, default=list)  # List of metric IDs
    query_config = Column(JSON, nullable=False)

    # Visualization configuration
    visualization_config = Column(JSON, default=dict)
    color_scheme = Column(String(50), default="default")

    # Layout
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)

    # Settings
    refresh_interval = Column(Integer, default=300)  # seconds
    cache_duration = Column(Integer, default=60)  # seconds

    # State
    is_active = Column(Boolean, default=True)
    last_refresh = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_widgets_dashboard_position", "dashboard_id", "position_x", "position_y"),
    )


class DashboardTemplate(Base):
    """Pre-built dashboard templates."""

    __tablename__ = "analytics_dashboard_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Template metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)

    # Template configuration
    dashboard_config = Column(JSON, nullable=False)
    widget_configs = Column(JSON, nullable=False)
    required_datasets = Column(JSON, default=list)

    # Usage
    usage_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class DashboardShare(Base):
    """Dashboard sharing and collaboration."""

    __tablename__ = "analytics_dashboard_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    dashboard_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Share configuration
    share_token = Column(String(255), unique=True, nullable=False)
    share_type = Column(String(50), nullable=False)  # public, private, password
    password_hash = Column(String(255))

    # Permissions
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)

    # Restrictions
    expires_at = Column(DateTime)
    max_views = Column(Integer)
    current_views = Column(Integer, default=0)

    # Metadata
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    last_accessed = Column(DateTime)

    __table_args__ = (
        Index("ix_dashboard_shares_token", "share_token"),
        Index("ix_dashboard_shares_dashboard", "dashboard_id"),
    )


class WidgetCache(Base):
    """Cache for widget data to improve performance."""

    __tablename__ = "analytics_widget_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    widget_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Cache key and data
    cache_key = Column(String(255), nullable=False, index=True)
    cached_data = Column(JSON, nullable=False)

    # Cache metadata
    created_at = Column(DateTime, nullable=False, default=utc_now)
    expires_at = Column(DateTime, nullable=False, index=True)
    hit_count = Column(Integer, default=0)

    # Data statistics
    data_size = Column(Integer)
    query_duration = Column(Float)

    __table_args__ = (
        Index("ix_widget_cache_widget_key", "widget_id", "cache_key"),
        Index("ix_widget_cache_expires", "expires_at"),
    )
