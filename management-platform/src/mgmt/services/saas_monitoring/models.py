"""Database models for SaaS monitoring and health checks."""

import enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, Enum, JSON, UniqueConstraint, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal
from sqlalchemy import Numeric

from mgmt.shared.database.base import TenantModel, TimestampMixin


class HealthStatus(enum.Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(enum.Enum):
    """Alert status states."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged" 
    RESOLVED = "resolved"
    MUTED = "muted"


class MonitoringMetric(enum.Enum):
    """Types of monitoring metrics."""
    RESPONSE_TIME = "response_time"
    UPTIME = "uptime"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    ACTIVE_CONNECTIONS = "active_connections"
    THROUGHPUT = "throughput"
    CUSTOM_METRIC = "custom_metric"


class TenantHealthCheck(TenantModel):
    """Health check records for tenant deployments."""
    
    __tablename__ = "tenant_health_checks"
    __table_args__ = (
        Index('idx_health_check_tenant', 'tenant_id'),
        Index('idx_health_check_timestamp', 'check_timestamp'),
        Index('idx_health_check_status', 'overall_status'),
        Index('idx_health_check_service', 'service_name'),
    )
    
    # Check identification
    check_id = Column(String(255), nullable=False, unique=True, index=True)
    service_name = Column(String(255), nullable=False, index=True)  # ISP Framework service
    
    # Health status
    overall_status = Column(Enum(HealthStatus), nullable=False, index=True)
    check_timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    
    # Connectivity checks
    database_status = Column(Enum(HealthStatus), nullable=True)
    redis_status = Column(Enum(HealthStatus), nullable=True)
    external_apis_status = Column(Enum(HealthStatus), nullable=True)
    
    # Application-specific checks
    active_sessions = Column(Integer, nullable=True)
    queue_size = Column(Integer, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    
    # Detailed results
    check_details = Column(JSONB, nullable=True)  # Detailed health check results
    failed_checks = Column(JSONB, nullable=True)  # List of failed check names
    
    # Performance benchmarks
    avg_response_time_5m = Column(Float, nullable=True)
    avg_response_time_1h = Column(Float, nullable=True)
    error_rate_5m = Column(Float, nullable=True)
    error_rate_1h = Column(Float, nullable=True)
    
    # Compliance and SLA
    sla_compliant = Column(Boolean, default=True, nullable=False)
    sla_violations = Column(JSONB, nullable=True)  # SLA violations details
    
    # Check configuration
    check_type = Column(String(50), default="automatic", nullable=False)  # automatic, manual, scheduled
    check_source = Column(String(100), nullable=True)  # Source of the health check
    
    # Context information
    deployment_version = Column(String(100), nullable=True)
    kubernetes_namespace = Column(String(255), nullable=True)
    pod_name = Column(String(255), nullable=True)
    node_name = Column(String(255), nullable=True)
    
    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.overall_status == HealthStatus.HEALTHY
    
    @property
    def has_sla_violations(self) -> bool:
        """Check if there are SLA violations."""
        return not self.sla_compliant or (self.sla_violations and len(self.sla_violations) > 0)
    
    def calculate_availability_score(self) -> float:
        """Calculate availability score based on health status."""
        if self.overall_status == HealthStatus.HEALTHY:
            return 100.0
        elif self.overall_status == HealthStatus.DEGRADED:
            return 75.0
        elif self.overall_status == HealthStatus.UNHEALTHY:
            return 0.0
        else:
            return 50.0  # UNKNOWN


class MonitoringAlert(TenantModel):
    """Alerts generated from monitoring and health checks."""
    
    __tablename__ = "monitoring_alerts"
    __table_args__ = (
        Index('idx_alert_tenant', 'tenant_id'),
        Index('idx_alert_severity', 'severity'),
        Index('idx_alert_status', 'status'),
        Index('idx_alert_created', 'created_at'),
        Index('idx_alert_metric', 'metric_name'),
    )
    
    # Alert identification
    alert_id = Column(String(255), nullable=False, unique=True, index=True)
    alert_name = Column(String(255), nullable=False)
    alert_description = Column(Text, nullable=False)
    
    # Alert classification
    severity = Column(Enum(AlertSeverity), nullable=False, index=True)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE, index=True)
    
    # Source information
    source_service = Column(String(255), nullable=False)  # Which service triggered alert
    metric_name = Column(String(255), nullable=True, index=True)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    
    # Alert timing
    first_occurred = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_occurred = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Alert management
    acknowledged_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    resolved_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    escalation_level = Column(Integer, default=0, nullable=False)
    
    # Notification tracking
    notifications_sent = Column(Integer, default=0, nullable=False)
    last_notification_at = Column(DateTime(timezone=True), nullable=True)
    notification_channels = Column(JSONB, nullable=True)  # Channels notified
    
    # Alert context
    deployment_id = Column(UUID(as_uuid=True), nullable=True)  # Link to deployment
    health_check_id = Column(UUID(as_uuid=True), nullable=True)  # Link to health check
    
    # Detailed information
    alert_data = Column(JSONB, nullable=True)  # Additional alert context
    resolution_notes = Column(Text, nullable=True)
    
    # Auto-resolution
    auto_resolve_after_minutes = Column(Integer, nullable=True)
    is_auto_resolvable = Column(Boolean, default=False, nullable=False)
    
    # Suppression and grouping
    is_suppressed = Column(Boolean, default=False, nullable=False)
    suppression_reason = Column(Text, nullable=True)
    alert_group_id = Column(String(255), nullable=True)  # For grouping related alerts
    
    @property
    def is_active(self) -> bool:
        """Check if alert is active."""
        return self.status == AlertStatus.ACTIVE
    
    @property
    def duration_minutes(self) -> int:
        """Get alert duration in minutes."""
        end_time = self.resolved_at or datetime.utcnow()
        return int((end_time - self.first_occurred).total_seconds() / 60)
    
    @property
    def is_critical_or_error(self) -> bool:
        """Check if alert is critical or error severity."""
        return self.severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR]
    
    def should_escalate(self, escalation_threshold_minutes: int = 30) -> bool:
        """Check if alert should be escalated."""
        if self.status != AlertStatus.ACTIVE:
            return False
            
        minutes_active = (datetime.utcnow() - self.first_occurred).total_seconds() / 60
        return minutes_active > escalation_threshold_minutes
    
    def acknowledge(self, user_id: Optional[str] = None):
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        if user_id:
            self.acknowledged_by_user_id = user_id
    
    def resolve(self, user_id: Optional[str] = None, notes: Optional[str] = None):
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        if user_id:
            self.resolved_by_user_id = user_id
        if notes:
            self.resolution_notes = notes


class SLAMetrics(TenantModel):
    """SLA metrics and performance tracking for tenants."""
    
    __tablename__ = "sla_metrics"
    __table_args__ = (
        Index('idx_sla_tenant', 'tenant_id'),
        Index('idx_sla_period', 'measurement_period'),
        Index('idx_sla_date', 'period_start'),
        UniqueConstraint('tenant_id', 'measurement_period', 'period_start', name='uq_tenant_sla_period'),
    )
    
    # Time period
    measurement_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Availability metrics
    uptime_percentage = Column(Numeric(5, 2), nullable=False, default=0)  # 99.99%
    downtime_minutes = Column(Integer, nullable=False, default=0)
    total_minutes = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    avg_response_time_ms = Column(Float, nullable=False, default=0)
    p95_response_time_ms = Column(Float, nullable=False, default=0)
    p99_response_time_ms = Column(Float, nullable=False, default=0)
    max_response_time_ms = Column(Float, nullable=False, default=0)
    
    # Error metrics
    total_requests = Column(Integer, nullable=False, default=0)
    successful_requests = Column(Integer, nullable=False, default=0)
    error_requests = Column(Integer, nullable=False, default=0)
    error_rate_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    
    # Throughput metrics
    requests_per_minute = Column(Float, nullable=False, default=0)
    peak_requests_per_minute = Column(Float, nullable=False, default=0)
    
    # SLA compliance
    availability_sla_target = Column(Numeric(5, 2), nullable=False, default=99.9)  # Target SLA
    response_time_sla_target_ms = Column(Integer, nullable=False, default=500)
    error_rate_sla_target = Column(Numeric(5, 2), nullable=False, default=1.0)
    
    # Compliance status
    availability_sla_met = Column(Boolean, nullable=False, default=True)
    response_time_sla_met = Column(Boolean, nullable=False, default=True)
    error_rate_sla_met = Column(Boolean, nullable=False, default=True)
    overall_sla_met = Column(Boolean, nullable=False, default=True)
    
    # SLA violations
    sla_violations = Column(JSONB, nullable=True)  # Details of violations
    violation_count = Column(Integer, nullable=False, default=0)
    
    # Resource utilization
    avg_cpu_usage_percent = Column(Float, nullable=True)
    avg_memory_usage_percent = Column(Float, nullable=True)
    avg_disk_usage_percent = Column(Float, nullable=True)
    
    # Business metrics
    active_users = Column(Integer, nullable=True)
    business_transactions = Column(Integer, nullable=True)
    revenue_impact = Column(Numeric(10, 2), nullable=True)  # Revenue impact of downtime
    
    # Health check summary
    health_checks_performed = Column(Integer, nullable=False, default=0)
    health_checks_passed = Column(Integer, nullable=False, default=0)
    health_checks_failed = Column(Integer, nullable=False, default=0)
    
    # Alert summary
    alerts_generated = Column(Integer, nullable=False, default=0)
    critical_alerts = Column(Integer, nullable=False, default=0)
    alerts_resolved = Column(Integer, nullable=False, default=0)
    avg_alert_resolution_minutes = Column(Float, nullable=True)
    
    # Additional metrics by tier
    tier_specific_metrics = Column(JSONB, nullable=True)
    
    @property
    def overall_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        # Weighted average of key metrics
        availability_weight = 0.4
        response_time_weight = 0.3
        error_rate_weight = 0.3
        
        # Normalize metrics to 0-100 scale
        availability_score = float(self.uptime_percentage)
        
        # Response time score (inverse relationship - lower is better)
        if self.response_time_sla_target_ms > 0:
            response_time_score = max(0, 100 - (self.avg_response_time_ms / self.response_time_sla_target_ms * 100))
        else:
            response_time_score = 100
        
        # Error rate score (inverse relationship - lower is better) 
        error_rate_score = max(0, 100 - float(self.error_rate_percentage))
        
        return (
            availability_score * availability_weight +
            response_time_score * response_time_weight +
            error_rate_score * error_rate_weight
        )
    
    @property
    def is_meeting_sla(self) -> bool:
        """Check if all SLA targets are being met."""
        return self.overall_sla_met
    
    def calculate_uptime_percentage(self) -> Decimal:
        """Calculate uptime percentage from total and downtime minutes."""
        if self.total_minutes == 0:
            return Decimal('100.00')
        
        uptime_minutes = self.total_minutes - self.downtime_minutes
        return Decimal(str(uptime_minutes / self.total_minutes * 100)).quantize(Decimal('0.01'))
    
    def add_violation(self, violation_type: str, details: Dict[str, Any]):
        """Add SLA violation record."""
        if not self.sla_violations:
            self.sla_violations = []
            
        violation = {
            "type": violation_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        
        self.sla_violations.append(violation)
        self.violation_count += 1
        self.overall_sla_met = False


class TenantMetricsSnapshot(TenantModel):
    """Real-time metrics snapshot for tenant deployments."""
    
    __tablename__ = "tenant_metrics_snapshots"
    __table_args__ = (
        Index('idx_metrics_tenant', 'tenant_id'),
        Index('idx_metrics_timestamp', 'snapshot_timestamp'),
        Index('idx_metrics_service', 'service_name'),
    )
    
    # Snapshot identification
    snapshot_id = Column(String(255), nullable=False, unique=True, index=True)
    service_name = Column(String(255), nullable=False, index=True)
    snapshot_timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Performance metrics
    current_response_time_ms = Column(Float, nullable=True)
    current_throughput_rpm = Column(Float, nullable=True)
    current_error_rate = Column(Float, nullable=True)
    
    # Resource metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_gb = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    network_io_mbps = Column(Float, nullable=True)
    
    # Application metrics
    active_connections = Column(Integer, nullable=True)
    active_sessions = Column(Integer, nullable=True)
    queue_depth = Column(Integer, nullable=True)
    cache_hit_rate = Column(Float, nullable=True)
    
    # Database metrics
    database_connections_active = Column(Integer, nullable=True)
    database_query_time_ms = Column(Float, nullable=True)
    database_slow_queries = Column(Integer, nullable=True)
    
    # Custom metrics
    custom_metrics = Column(JSONB, nullable=True)  # Plugin-specific or custom metrics
    
    # Health indicators
    health_score = Column(Float, nullable=True)  # 0-100 health score
    anomaly_score = Column(Float, nullable=True)  # Anomaly detection score
    
    # Deployment context
    deployment_version = Column(String(100), nullable=True)
    replica_count = Column(Integer, nullable=True)
    kubernetes_namespace = Column(String(255), nullable=True)
    
    # Trending indicators
    trend_direction = Column(String(20), nullable=True)  # improving, stable, degrading
    trend_confidence = Column(Float, nullable=True)     # 0-1 confidence in trend
    
    @property
    def is_performing_well(self) -> bool:
        """Check if service is performing well based on metrics."""
        # Define performance thresholds
        if self.current_response_time_ms and self.current_response_time_ms > 1000:
            return False
        if self.current_error_rate and self.current_error_rate > 1.0:
            return False
        if self.cpu_usage_percent and self.cpu_usage_percent > 90:
            return False
        if self.memory_usage_percent and self.memory_usage_percent > 90:
            return False
            
        return True
    
    @property
    def resource_pressure(self) -> str:
        """Get resource pressure level."""
        cpu_pressure = self.cpu_usage_percent or 0
        memory_pressure = self.memory_usage_percent or 0
        disk_pressure = self.disk_usage_percent or 0
        
        max_pressure = max(cpu_pressure, memory_pressure, disk_pressure)
        
        if max_pressure > 95:
            return "critical"
        elif max_pressure > 85:
            return "high"
        elif max_pressure > 70:
            return "medium"
        else:
            return "low"