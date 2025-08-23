"""Analytics models for metrics, reports, dashboards and alerts."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel, Base
from enum import Enum


class MetricType(str, Enum):
    """Available metric types for analytics."""

    BANDWIDTH = "bandwidth"
    REVENUE = "revenue"
    CUSTOMER_COUNT = "customer_count"
    SERVICE_UPTIME = "service_uptime"
    SUPPORT_TICKETS = "support_tickets"
    NETWORK_LATENCY = "network_latency"
    DATA_USAGE = "data_usage"


class ReportType(str, Enum):
    """Available report types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Metric(TenantModel):
    """Metric definition and metadata."""

    __tablename__ = "analytics_metrics"

    # Metric definition
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    metric_type = Column(String(50), nullable=False)

    # Data configuration
    unit = Column(String(50))
    calculation_config = Column(JSON, default=dict)
    dimensions = Column(JSON, default=list)
    tags = Column(JSON, default=dict)

    # Settings
    is_active = Column(Boolean, default=True)
    refresh_interval = Column(Integer, default=300)  # seconds
    retention_days = Column(Integer, default=90)

    # Relationships
    values = relationship(
        "MetricValue", back_populates="metric", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "Alert", back_populates="metric", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_metrics_tenant_name", "tenant_id", "name"),
        Index("ix_metrics_type_active", "metric_type", "is_active"),
    )

    @hybrid_property
    def latest_value(self) -> Optional[float]:
        """Get the latest metric value."""
        if self.values:
            return max(self.values, key=lambda v: v.timestamp).value
        return None

    def calculate_trend(self, period_hours: int = 24) -> Dict[str, Any]:
        """Calculate metric trend over period."""
        if not self.values:
            return {"trend": "stable", "change_percent": 0.0}

        current_time = datetime.utcnow()
        period_start = current_time.replace(hour=current_time.hour - period_hours)

        recent_values = [v for v in self.values if v.timestamp >= period_start]
        if len(recent_values) < 2:
            return {"trend": "stable", "change_percent": 0.0}

        recent_values.sort(key=lambda x: x.timestamp)
        start_value = recent_values[0].value
        end_value = recent_values[-1].value

        if start_value == 0:
            change_percent = 100.0 if end_value > 0 else 0.0
        else:
            change_percent = ((end_value - start_value) / start_value) * 100

        trend = (
            "increasing"
            if change_percent > 5
            else "decreasing" if change_percent < -5 else "stable"
        )

        return {
            "trend": trend,
            "change_percent": round(change_percent, 2),
            "start_value": start_value,
            "end_value": end_value,
            "period_hours": period_hours,
        }


class MetricValue(TenantModel):
    """Time-series metric values."""

    __tablename__ = "analytics_metric_values"

    metric_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analytics_metrics.id"),
        nullable=False,
        index=True,
    )
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    dimensions = Column(JSON, default=dict)
    context = Column(JSON, default=dict)

    # Relationships
    metric = relationship("Metric", back_populates="values")

    __table_args__ = (
        Index("ix_metric_values_tenant_metric", "tenant_id", "metric_id"),
        Index("ix_metric_values_timestamp", "timestamp"),
    )

    def is_anomaly(self, threshold_stddev: float = 2.0) -> bool:
        """Detect if this value is an anomaly."""
        if not self.metric or not self.metric.values:
            return False

        values = [v.value for v in self.metric.values if v.id != self.id]
        if len(values) < 10:  # Need enough data points
            return False

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        stddev = variance**0.5

        return abs(self.value - mean) > (threshold_stddev * stddev)


class Report(TenantModel):
    """Analytics report definition and data."""

    __tablename__ = "analytics_reports"

    report_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Report configuration and data
    filters = Column(JSON, default=dict)
    data = Column(JSON, default=dict)
    format_config = Column(JSON, default=dict)

    # Settings
    is_scheduled = Column(Boolean, default=False)
    schedule_config = Column(JSON, default=dict)
    is_public = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_reports_tenant_type", "tenant_id", "report_type"),
        Index("ix_reports_date_range", "start_date", "end_date"),
    )

    @hybrid_property
    def duration_days(self) -> int:
        """Calculate report duration in days."""
        return (self.end_date - self.start_date).days

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get report summary statistics."""
        if not self.data:
            return {}

        summary = {
            "total_customers": self.data.get("total_customers", 0),
            "total_revenue": self.data.get("total_revenue", 0.0),
            "avg_bandwidth_mbps": self.data.get("avg_bandwidth_mbps", 0.0),
            "uptime_percentage": self.data.get("uptime_percentage", 99.0),
            "support_tickets": self.data.get("support_tickets", 0),
            "growth_metrics": self.data.get("growth_metrics", {}),
            "performance_metrics": self.data.get("performance_metrics", {}),
        }

        return summary

    def export_data(self, format_type: str = "json") -> str:
        """Export report data in specified format."""
        if format_type == "csv":
            # Convert data to CSV format
            import csv
            import io

            output = io.StringIO()
            if self.data:
                writer = csv.DictWriter(output, fieldnames=self.data.keys())
                writer.writeheader()
                writer.writerow(self.data)
            return output.getvalue()
        elif format_type == "pdf":
            return f"PDF export of {self.title} - {len(str(self.data))} bytes"
        else:
            import json

            return json.dumps(self.data, default=str, indent=2)


class Dashboard(TenantModel):
    """Analytics dashboard configuration."""

    __tablename__ = "analytics_dashboards"

    name = Column(String(100), nullable=False)
    description = Column(Text)
    layout = Column(JSON, default=dict)
    is_public = Column(Boolean, default=False)

    # Configuration
    refresh_rate = Column(Integer, default=30)  # seconds
    theme_config = Column(JSON, default=dict)
    access_permissions = Column(JSON, default=list)

    # Relationships
    widgets = relationship(
        "Widget", back_populates="dashboard", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_dashboards_tenant_public", "tenant_id", "is_public"),
        Index("ix_dashboards_name", "name"),
    )

    @hybrid_property
    def widget_count(self) -> int:
        """Get total widget count."""
        return len(self.widgets)

    def calculate_load_time(self) -> float:
        """Estimate dashboard load time in seconds."""
        base_time = 0.5  # Base load time
        widget_time = len(self.widgets) * 0.2  # 200ms per widget
        complexity_factor = 1.0

        # Factor in widget complexity
        for widget in self.widgets:
            if widget.widget_type in ["chart", "graph", "heatmap"]:
                complexity_factor += 0.1

        return round((base_time + widget_time) * complexity_factor, 2)

    def get_widget_by_type(self, widget_type: str) -> List["Widget"]:
        """Get widgets by type."""
        return [w for w in self.widgets if w.widget_type == widget_type]


class Widget(TenantModel):
    """Dashboard widget configuration."""

    __tablename__ = "analytics_widgets"

    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analytics_dashboards.id"),
        nullable=False,
        index=True,
    )
    widget_type = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False, default=0)

    # Configuration
    config = Column(JSON, default=dict)
    data_source = Column(JSON, default=dict)
    style_config = Column(JSON, default=dict)

    # Settings
    is_visible = Column(Boolean, default=True)
    refresh_interval = Column(Integer, default=60)  # seconds

    # Relationships
    dashboard = relationship("Dashboard", back_populates="widgets")

    __table_args__ = (
        Index("ix_widgets_dashboard_type", "dashboard_id", "widget_type"),
        Index("ix_widgets_position", "position"),
    )

    def get_data_query(self) -> Dict[str, Any]:
        """Get the data query configuration for this widget."""
        return self.data_source.get("query", {})

    def is_real_time(self) -> bool:
        """Check if widget displays real-time data."""
        return self.refresh_interval <= 10


class Alert(TenantModel):
    """Analytics alert configuration."""

    __tablename__ = "analytics_alerts"

    metric_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analytics_metrics.id"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    condition = Column(String(50), nullable=False)  # greater_than, less_than, equals
    threshold = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)

    # Configuration
    notification_channels = Column(JSON, default=list)
    condition_config = Column(JSON, default=dict)

    # State
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)

    # Relationships
    metric = relationship("Metric", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_tenant_active", "tenant_id", "is_active"),
        Index("ix_alerts_metric_severity", "metric_id", "severity"),
    )

    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should trigger based on current value."""
        if not self.is_active:
            return False

        if self.condition == "greater_than":
            return current_value > self.threshold
        elif self.condition == "less_than":
            return current_value < self.threshold
        elif self.condition == "equals":
            tolerance = self.condition_config.get("tolerance", 0.01)
            return abs(current_value - self.threshold) <= tolerance

        return False

    def get_priority_score(self) -> int:
        """Calculate alert priority score (1-5)."""
        severity_scores = {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }

        base_score = severity_scores.get(AlertSeverity(self.severity), 1)

        # Increase priority for recently triggered alerts
        if self.last_triggered:
            hours_since = (
                datetime.utcnow() - self.last_triggered
            ).total_seconds() / 3600
            if hours_since < 1:
                base_score += 1

        # Increase priority for frequently triggered alerts
        if self.trigger_count > 10:
            base_score += 1

        return min(base_score, 5)

    def trigger_alert(self) -> Dict[str, Any]:
        """Trigger the alert and update state."""
        self.last_triggered = datetime.utcnow()
        self.trigger_count += 1

        return {
            "alert_id": str(self.id),
            "name": self.name,
            "severity": self.severity,
            "metric_id": str(self.metric_id),
            "threshold": self.threshold,
            "triggered_at": self.last_triggered,
            "priority_score": self.get_priority_score(),
            "notification_channels": self.notification_channels,
        }


class DataSource(TenantModel):
    """Analytics data source configuration."""

    __tablename__ = "analytics_data_sources"

    name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)  # database, api, file, stream
    connection_config = Column(JSON, default=dict)

    # Configuration
    query_config = Column(JSON, default=dict)
    refresh_schedule = Column(String(100))  # cron expression
    data_mapping = Column(JSON, default=dict)

    # Settings
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime)
    sync_status = Column(
        String(50), default="pending"
    )  # pending, syncing, success, error

    __table_args__ = (
        Index("ix_data_sources_tenant_type", "tenant_id", "source_type"),
        Index("ix_data_sources_active", "is_active"),
    )

    def test_connection(self) -> Dict[str, Any]:
        """Test the data source connection."""
        # Mock connection test
        return {
            "status": "success",
            "latency_ms": 150,
            "last_tested": datetime.utcnow(),
            "error": None,
        }

    def get_schema(self) -> Dict[str, Any]:
        """Get the data source schema."""
        return {
            "tables": self.data_mapping.get("tables", []),
            "columns": self.data_mapping.get("columns", {}),
            "relationships": self.data_mapping.get("relationships", []),
        }
