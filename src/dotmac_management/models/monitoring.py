"""
Monitoring and analytics models.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    """Alert status enumeration."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class MetricType(str, Enum):
    """Metric type enumeration."""

    COUNTER = "counter"  # Always increasing
    GAUGE = "gauge"  # Can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Summary statistics


class HealthCheck(BaseModel):
    """Health check results for tenants and deployments."""

    __tablename__ = "health_checks"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("customer_tenants.id"), nullable=False, index=True)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True, index=True)

    # Health check details
    check_name = Column(String(255), nullable=False, index=True)
    check_type = Column(String(100), nullable=False, index=True)  # http, tcp, database, custom
    endpoint_url = Column(String(500), nullable=True)

    # Health status
    status = Column(SQLEnum(HealthStatus), nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)

    # Check results
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, default=dict, nullable=False)

    # Check configuration
    timeout_seconds = Column(Integer, default=30, nullable=False)
    retry_count = Column(Integer, default=3, nullable=False)
    check_interval_seconds = Column(Integer, default=300, nullable=False)  # 5 minutes

    # Health metadata
    check_details = Column(JSON, default=dict, nullable=False)
    tags = Column(JSON, default=list, nullable=False)

    # Next scheduled check
    next_check_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="health_checks")
    deployment = relationship("Deployment")

    def __repr__(self) -> str:
        return f"<HealthCheck(name='{self.check_name}', status='{self.status}')>"

    @property
    def is_healthy(self) -> bool:
        """Check if health check is passing."""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_overdue(self) -> bool:
        """Check if health check is overdue."""
        if not self.next_check_at:
            return False
        return datetime.now(timezone.utc) > self.next_check_at

    def schedule_next_check(self) -> None:
        """Schedule next health check."""
        from datetime import timedelta

        self.next_check_at = datetime.now(timezone.utc) + timedelta(seconds=self.check_interval_seconds)


class Metric(BaseModel):
    """Metric data collection."""

    __tablename__ = "metrics"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("customer_tenants.id"), nullable=False, index=True)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True, index=True)

    # Metric identification
    metric_name = Column(String(255), nullable=False, index=True)
    metric_type = Column(SQLEnum(MetricType), nullable=False, index=True)

    # Metric value
    value = Column(Numeric(20, 6), nullable=False)
    unit = Column(String(50), nullable=True)

    # Metric timestamp
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Metric dimensions/labels
    labels = Column(JSON, default=dict, nullable=False)

    # Metric metadata
    source = Column(String(255), nullable=True)  # Source system/component
    host = Column(String(255), nullable=True)

    # Aggregation period (for pre-aggregated metrics)
    period_seconds = Column(Integer, nullable=True)  # 60 for 1-minute aggregation

    # Relationships
    tenant = relationship("Tenant")
    deployment = relationship("Deployment")

    def __repr__(self) -> str:
        return f"<Metric(name='{self.metric_name}', value={self.value}, timestamp='{self.timestamp}')>"

    @property
    def value_float(self) -> float:
        """Get metric value as float."""
        return float(self.value)


class Alert(BaseModel):
    """Alert management."""

    __tablename__ = "alerts"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("customer_tenants.id"), nullable=False, index=True)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True, index=True)

    # Alert identification
    alert_name = Column(String(255), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False, index=True)  # threshold, anomaly, custom

    # Alert severity and status
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False, index=True)

    # Alert details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Alert trigger
    metric_name = Column(String(255), nullable=True, index=True)
    threshold_value = Column(Numeric(20, 6), nullable=True)
    threshold_operator = Column(String(10), nullable=True)  # >, <, >=, <=, ==, !=
    current_value = Column(Numeric(20, 6), nullable=True)

    # Alert timing
    first_triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Alert configuration
    evaluation_interval_seconds = Column(Integer, default=60, nullable=False)
    suppression_duration_seconds = Column(Integer, default=3600, nullable=False)  # 1 hour

    # Alert metadata
    labels = Column(JSON, default=dict, nullable=False)
    annotations = Column(JSON, default=dict, nullable=False)

    # Notification configuration
    notification_channels = Column(JSON, default=list, nullable=False)
    notification_sent = Column(Boolean, default=False, nullable=False)
    last_notification_at = Column(DateTime, nullable=True)

    # User tracking
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    deployment = relationship("Deployment")
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self) -> str:
        return f"<Alert(name='{self.alert_name}', severity='{self.severity}', status='{self.status}')>"

    @property
    def is_active(self) -> bool:
        """Check if alert is active."""
        return self.status == AlertStatus.ACTIVE

    @property
    def is_critical(self) -> bool:
        """Check if alert is critical."""
        return self.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]

    @property
    def duration_minutes(self) -> int:
        """Get alert duration in minutes."""
        end_time = self.resolved_at or datetime.now(timezone.utc)
        delta = end_time - self.first_triggered_at
        return int(delta.total_seconds() / 60)

    def acknowledge(self, user_id: str) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now(timezone.utc)
        self.acknowledged_by = user_id

    def resolve(self, user_id: Optional[str] = None) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        if user_id:
            self.resolved_by = user_id

    def suppress(self) -> None:
        """Suppress the alert."""
        self.status = AlertStatus.SUPPRESSED


class SLARecord(BaseModel):
    """Service Level Agreement tracking."""

    __tablename__ = "sla_records"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("customer_tenants.id"), nullable=False, index=True)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=True, index=True)

    # SLA period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), default="monthly", nullable=False)  # daily, weekly, monthly

    # SLA metrics
    uptime_percentage = Column(Numeric(5, 4), nullable=False)  # 99.9500 = 99.95%
    availability_percentage = Column(Numeric(5, 4), nullable=False)
    response_time_avg_ms = Column(Integer, nullable=False)
    response_time_95p_ms = Column(Integer, nullable=False)
    error_rate_percentage = Column(Numeric(5, 4), default=0, nullable=False)

    # SLA targets
    uptime_target_percentage = Column(Numeric(5, 4), default=99.9, nullable=False)
    response_time_target_ms = Column(Integer, default=500, nullable=False)
    error_rate_target_percentage = Column(Numeric(5, 4), default=1.0, nullable=False)

    # SLA compliance
    uptime_met = Column(Boolean, nullable=False)
    response_time_met = Column(Boolean, nullable=False)
    error_rate_met = Column(Boolean, nullable=False)
    overall_sla_met = Column(Boolean, nullable=False)

    # Incident tracking
    incident_count = Column(Integer, default=0, nullable=False)
    total_downtime_minutes = Column(Integer, default=0, nullable=False)
    mttr_minutes = Column(Integer, nullable=True)  # Mean Time To Recovery

    # SLA credits (if SLA breached)
    credit_percentage = Column(Numeric(5, 4), default=0, nullable=False)
    credit_amount_cents = Column(Integer, default=0, nullable=False)
    credit_applied = Column(Boolean, default=False, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    deployment = relationship("Deployment")

    def __repr__(self) -> str:
        return f"<SLARecord(tenant_id='{self.tenant_id}', period='{self.period_start}' to '{self.period_end}')>"

    @property
    def uptime_percentage_float(self) -> float:
        """Get uptime percentage as float."""
        return float(self.uptime_percentage)

    @property
    def sla_score(self) -> float:
        """Calculate overall SLA score."""
        scores = []
        if self.uptime_met:
            scores.append(100)
        else:
            scores.append(float(self.uptime_percentage / self.uptime_target_percentage * 100))

        if self.response_time_met:
            scores.append(100)
        else:
            scores.append(
                max(
                    0,
                    100 - (self.response_time_avg_ms - self.response_time_target_ms) / 10,
                )
            )

        if self.error_rate_met:
            scores.append(100)
        else:
            scores.append(max(0, 100 - float(self.error_rate_percentage) * 10))

        return sum(scores) / len(scores)

    @property
    def credit_amount(self) -> Decimal:
        """Get credit amount in dollars."""
        return Decimal(self.credit_amount_cents) / 100
