"""
Dataset models for analytics data management and processing.
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


class Dataset(Base):
    """Dataset definition for analytics data."""

    __tablename__ = "analytics_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Dataset metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)

    # Data source configuration
    source_type = Column(String(50), nullable=False)
    source_config = Column(JSON, nullable=False)

    # Schema definition
    schema_definition = Column(JSON, nullable=False)
    primary_key_columns = Column(JSON, default=list)
    timestamp_column = Column(String(255))

    # Processing configuration
    refresh_schedule = Column(String(100))  # cron expression
    refresh_interval = Column(Integer)  # seconds
    retention_days = Column(Integer, default=365)

    # State
    is_active = Column(Boolean, default=True)
    last_refresh = Column(DateTime)
    next_refresh = Column(DateTime)

    # Statistics
    row_count = Column(Integer, default=0)
    size_bytes = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_datasets_tenant_name", "tenant_id", "name"),
        Index("ix_datasets_category_active", "category", "is_active"),
    )


class DataSource(Base):
    """Data source configuration for datasets."""

    __tablename__ = "analytics_data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Source metadata
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    source_type = Column(String(50), nullable=False)

    # Connection configuration
    connection_config = Column(JSON, nullable=False)
    credentials = Column(JSON)  # Encrypted

    # Health monitoring
    is_healthy = Column(Boolean, default=True)
    last_health_check = Column(DateTime)
    health_check_message = Column(Text)

    # Usage statistics
    dataset_count = Column(Integer, default=0)
    last_used = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class DataPoint(Base):
    """Individual data points for flexible analytics storage."""

    __tablename__ = "analytics_data_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Data point metadata
    timestamp = Column(DateTime, nullable=False, index=True)
    entity_id = Column(String(255), index=True)  # customer_id, user_id, etc.
    entity_type = Column(String(100), index=True)

    # Data payload
    data = Column(JSON, nullable=False)

    # Dimensions for filtering
    dimensions = Column(JSON, default=dict)

    # Metadata
    source = Column(String(100))
    batch_id = Column(UUID(as_uuid=True), index=True)

    # Processing
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_data_points_dataset_time", "dataset_id", "timestamp"),
        Index("ix_data_points_entity_time", "entity_id", "timestamp"),
        Index("ix_data_points_tenant_time", "tenant_id", "timestamp"),
    )


class DataTransformation(Base):
    """Data transformation rules for processing datasets."""

    __tablename__ = "analytics_data_transformations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Transformation metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    transformation_type = Column(String(50), nullable=False)  # filter, aggregate, join, etc.

    # Transformation configuration
    configuration = Column(JSON, nullable=False)
    input_schema = Column(JSON)
    output_schema = Column(JSON)

    # Execution
    execution_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Performance metrics
    avg_execution_time = Column(Float)
    last_execution_time = Column(Float)
    execution_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class DataQualityRule(Base):
    """Data quality rules for dataset validation."""

    __tablename__ = "analytics_data_quality_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    dataset_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Rule metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    rule_type = Column(String(50), nullable=False)  # completeness, uniqueness, validity, etc.

    # Rule configuration
    column_name = Column(String(255))
    rule_expression = Column(Text, nullable=False)
    threshold = Column(Float)  # For percentage-based rules

    # Severity and actions
    severity = Column(String(20), default="medium")
    action_on_failure = Column(String(50), default="log")  # log, alert, block

    # State
    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime)
    last_result = Column(Boolean)
    failure_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class DataLineage(Base):
    """Data lineage tracking for datasets."""

    __tablename__ = "analytics_data_lineage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Lineage relationship
    source_dataset_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_dataset_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Relationship metadata
    relationship_type = Column(String(50), nullable=False)  # derived, joined, aggregated, etc.
    transformation_id = Column(UUID(as_uuid=True), index=True)

    # Dependency information
    columns_mapping = Column(JSON)  # source -> target column mapping

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_data_lineage_source_target", "source_dataset_id", "target_dataset_id"),
    )
