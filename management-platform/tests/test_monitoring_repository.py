"""
Tests for monitoring repository.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.monitoring import (
    MonitoringRepository, HealthCheckRepository, MetricRepository, 
    AlertRepository, SLARecordRepository
)
from models.monitoring import (
    HealthCheck, Metric, Alert, SLARecord,
    HealthStatus, AlertSeverity, AlertStatus, MetricType
)


@pytest.fixture
def db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def monitoring_repo(db_session):
    """Monitoring repository fixture."""
    return MonitoringRepository(db_session)


@pytest.fixture
def health_check_repo(db_session):
    """Health check repository fixture."""
    return HealthCheckRepository(db_session)


@pytest.fixture
def metric_repo(db_session):
    """Metric repository fixture."""
    return MetricRepository(db_session)


@pytest.fixture
def alert_repo(db_session):
    """Alert repository fixture."""
    return AlertRepository(db_session)


@pytest.fixture
def sla_repo(db_session):
    """SLA record repository fixture."""
    return SLARecordRepository(db_session)


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID fixture."""
    return uuid4()


@pytest.fixture
def sample_health_check(sample_tenant_id):
    """Sample health check fixture."""
    return HealthCheck(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        deployment_id=uuid4(),
        check_name="API Health Check",
        check_type="http",
        endpoint_url="https://api.example.com/health",
        status=HealthStatus.HEALTHY,
        response_time_ms=150,
        success=True,
        error_message=None,
        response_data={"status": "ok", "version": "1.0.0"},
        timeout_seconds=30,
        retry_count=3,
        check_interval_seconds=300,
        check_details={"method": "GET", "expected_status": 200},
        tags=["api", "critical"],
        next_check_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )


@pytest.fixture
def sample_metric(sample_tenant_id):
    """Sample metric fixture."""
    return Metric(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        deployment_id=uuid4(),
        metric_name="cpu_usage_percent",
        metric_type=MetricType.GAUGE,
        value=Decimal("75.5"),
        unit="percent",
        timestamp=datetime.now(timezone.utc),
        labels={"host": "web01", "service": "api"},
        source="prometheus",
        host="web01.example.com",
        period_seconds=60
    )


@pytest.fixture
def sample_alert(sample_tenant_id):
    """Sample alert fixture."""
    return Alert(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        deployment_id=uuid4(),
        alert_name="High CPU Usage",
        alert_type="threshold",
        severity=AlertSeverity.WARNING,
        status=AlertStatus.ACTIVE,
        title="CPU usage is high",
        description="CPU usage exceeded 80% threshold",
        metric_name="cpu_usage_percent",
        threshold_value=Decimal("80.0"),
        threshold_operator=">=",
        current_value=Decimal("85.2"),
        first_triggered_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        last_triggered_at=datetime.now(timezone.utc),
        acknowledged_at=None,
        resolved_at=None,
        evaluation_interval_seconds=60,
        suppression_duration_seconds=3600,
        labels={"severity": "warning", "service": "api"},
        annotations={"runbook": "https://runbooks.example.com/high-cpu"},
        notification_channels=["email", "slack"],
        notification_sent=True,
        last_notification_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        acknowledged_by=None,
        resolved_by=None
    )


@pytest.fixture
def sample_sla_record(sample_tenant_id):
    """Sample SLA record fixture."""
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    period_end = datetime.now(timezone.utc)
    
    return SLARecord(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        deployment_id=uuid4(),
        period_start=period_start,
        period_end=period_end,
        period_type="monthly",
        uptime_percentage=Decimal("99.95"),
        availability_percentage=Decimal("99.98"),
        response_time_avg_ms=145,
        response_time_95p_ms=220,
        error_rate_percentage=Decimal("0.05"),
        uptime_target_percentage=Decimal("99.9"),
        response_time_target_ms=500,
        error_rate_target_percentage=Decimal("1.0"),
        uptime_met=True,
        response_time_met=True,
        error_rate_met=True,
        overall_sla_met=True,
        incident_count=1,
        total_downtime_minutes=15,
        mttr_minutes=10,
        credit_percentage=Decimal("0.0"),
        credit_amount_cents=0,
        credit_applied=False
    )


class TestMonitoringRepository:
    """Test cases for MonitoringRepository."""

    @pytest.mark.asyncio
    async def test_get_tenant_health_checks(self, monitoring_repo, sample_tenant_id, sample_health_check):
        """Test getting tenant health checks."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_health_check]
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.get_tenant_health_checks(sample_tenant_id, limit=10)
        
        assert result == [sample_health_check]
        monitoring_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tenant_health_checks_with_type_filter(self, monitoring_repo, sample_tenant_id, sample_health_check):
        """Test getting tenant health checks with type filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_health_check]
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.get_tenant_health_checks(
            sample_tenant_id, limit=10, check_type="http"
        )
        
        assert result == [sample_health_check]
        monitoring_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_alerts(self, monitoring_repo, sample_tenant_id, sample_alert):
        """Test getting active alerts."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_alert]
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.get_active_alerts(sample_tenant_id)
        
        assert result == [sample_alert]
        monitoring_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_sla_record(self, monitoring_repo, sample_tenant_id, sample_sla_record):
        """Test getting latest SLA record."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_sla_record
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.get_latest_sla_record(sample_tenant_id)
        
        assert result == sample_sla_record
        monitoring_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tenant_metrics(self, monitoring_repo, sample_tenant_id, sample_metric):
        """Test getting tenant metrics."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        metric_names = ["cpu_usage_percent", "memory_usage_percent"]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_metric]
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.get_tenant_metrics(
            sample_tenant_id, metric_names, start_time, end_time
        )
        
        assert result == [sample_metric]
        monitoring_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_health_check(self, monitoring_repo, sample_tenant_id):
        """Test recording a health check."""
        monitoring_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
        
        result = await monitoring_repo.record_health_check(
            tenant_id=sample_tenant_id,
            check_name="Database Health",
            check_type="database",
            status=HealthStatus.HEALTHY,
            success=True,
            response_time_ms=25,
            endpoint_url="postgresql://db.example.com:5432/mydb"
        )
        
        assert result is not None
        monitoring_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_metric(self, monitoring_repo, sample_tenant_id):
        """Test recording a metric."""
        monitoring_repo.db.add = MagicMock()
        monitoring_repo.db.flush = AsyncMock()
        monitoring_repo.db.refresh = AsyncMock()
        
        result = await monitoring_repo.record_metric(
            tenant_id=sample_tenant_id,
            metric_name="disk_usage_percent",
            metric_type=MetricType.GAUGE,
            value=65.5,
            unit="percent",
            labels={"disk": "/dev/sda1"},
            source="node_exporter",
            host="web01"
        )
        
        assert result is not None
        monitoring_repo.db.add.assert_called_once()
        monitoring_repo.db.flush.assert_called_once()
        monitoring_repo.db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_alert(self, monitoring_repo, sample_tenant_id):
        """Test creating an alert."""
        monitoring_repo.db.add = MagicMock()
        monitoring_repo.db.flush = AsyncMock()
        monitoring_repo.db.refresh = AsyncMock()
        
        result = await monitoring_repo.create_alert(
            tenant_id=sample_tenant_id,
            alert_name="High Memory Usage",
            alert_type="threshold",
            severity=AlertSeverity.CRITICAL,
            title="Memory usage critical",
            description="Memory usage exceeded 90%",
            metric_name="memory_usage_percent",
            threshold_value=90.0,
            current_value=92.5
        )
        
        assert result is not None
        monitoring_repo.db.add.assert_called_once()
        monitoring_repo.db.flush.assert_called_once()
        monitoring_repo.db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_repo):
        """Test resolving an alert."""
        alert_id = uuid4()
        user_id = uuid4()
        
        mock_alert = MagicMock()
        mock_alert.resolve = MagicMock()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_alert
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        monitoring_repo.db.flush = AsyncMock()
        
        result = await monitoring_repo.resolve_alert(alert_id, user_id)
        
        assert result is True
        mock_alert.resolve.assert_called_once_with(str(user_id))
        monitoring_repo.db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(self, monitoring_repo):
        """Test resolving non-existent alert."""
        alert_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.resolve_alert(alert_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_tenant_alert_summary(self, monitoring_repo, sample_tenant_id):
        """Test getting tenant alert summary."""
        mock_rows = [
            MagicMock(severity=AlertSeverity.CRITICAL, status=AlertStatus.ACTIVE, count=2),
            MagicMock(severity=AlertSeverity.WARNING, status=AlertStatus.ACTIVE, count=5),
            MagicMock(severity=AlertSeverity.CRITICAL, status=AlertStatus.RESOLVED, count=1)
        ]
        
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(mock_rows)
        monitoring_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await monitoring_repo.get_tenant_alert_summary(sample_tenant_id)
        
        assert "critical" in result
        assert "warning" in result
        assert result["critical"]["active"] == 2
        assert result["warning"]["active"] == 5
        assert result["critical"]["resolved"] == 1

    def test_monitoring_repository_initialization(self, db_session):
        """Test repository initialization."""
        repo = MonitoringRepository(db_session)
        
        assert repo.db == db_session
        assert repo.model == HealthCheck


class TestMetricRepository:
    """Test cases for MetricRepository."""

    @pytest.mark.asyncio
    async def test_get_metrics_aggregate_avg(self, metric_repo, sample_tenant_id):
        """Test getting average metric aggregation."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 75.5
        metric_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await metric_repo.get_metrics_aggregate(
            sample_tenant_id, "cpu_usage_percent", start_time, end_time, "avg"
        )
        
        assert result == 75.5
        metric_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metrics_aggregate_sum(self, metric_repo, sample_tenant_id):
        """Test getting sum metric aggregation."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1024
        metric_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await metric_repo.get_metrics_aggregate(
            sample_tenant_id, "network_bytes_total", start_time, end_time, "sum"
        )
        
        assert result == 1024
        metric_repo.db.execute.assert_called_once()

    def test_metric_repository_initialization(self, db_session):
        """Test repository initialization."""
        repo = MetricRepository(db_session)
        
        assert repo.db == db_session
        assert repo.model == Metric


class TestAlertRepository:
    """Test cases for AlertRepository."""

    @pytest.mark.asyncio
    async def test_get_alert_history(self, alert_repo, sample_tenant_id, sample_alert):
        """Test getting alert history."""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_alert]
        alert_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await alert_repo.get_alert_history(
            sample_tenant_id, start_date, end_date, AlertSeverity.WARNING
        )
        
        assert result == [sample_alert]
        alert_repo.db.execute.assert_called_once()

    def test_alert_repository_initialization(self, db_session):
        """Test repository initialization."""
        repo = AlertRepository(db_session)
        
        assert repo.db == db_session
        assert repo.model == Alert


class TestSLARecordRepository:
    """Test cases for SLARecordRepository."""

    @pytest.mark.asyncio
    async def test_get_sla_history(self, sla_repo, sample_tenant_id, sample_sla_record):
        """Test getting SLA history."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_sla_record]
        sla_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await sla_repo.get_sla_history(sample_tenant_id, "monthly", 12)
        
        assert result == [sample_sla_record]
        sla_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sla_compliance_summary(self, sla_repo, sample_tenant_id, sample_sla_record):
        """Test getting SLA compliance summary."""
        # Mock the get_sla_history call
        sla_repo.get_sla_history = AsyncMock(return_value=[sample_sla_record])
        
        result = await sla_repo.get_sla_compliance_summary(sample_tenant_id)
        
        assert result["compliance_rate"] == 100.0  # 1 compliant record out of 1
        assert result["average_uptime"] == 99.95
        assert result["average_response_time"] == 145
        assert result["total_incidents"] == 1
        assert result["total_downtime_minutes"] == 15
        assert result["periods_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_get_sla_compliance_summary_no_data(self, sla_repo, sample_tenant_id):
        """Test getting SLA compliance summary with no data."""
        sla_repo.get_sla_history = AsyncMock(return_value=[])
        
        result = await sla_repo.get_sla_compliance_summary(sample_tenant_id)
        
        assert result["compliance_rate"] == 100.0
        assert result["average_uptime"] == 99.9
        assert result["average_response_time"] == 0
        assert result["total_incidents"] == 0
        assert result["total_downtime_minutes"] == 0

    def test_sla_record_repository_initialization(self, db_session):
        """Test repository initialization."""
        repo = SLARecordRepository(db_session)
        
        assert repo.db == db_session
        assert repo.model == SLARecord


class TestMonitoringModels:
    """Test monitoring model properties and methods."""

    def test_health_check_is_healthy_property(self, sample_health_check):
        """Test health check is_healthy property."""
        assert sample_health_check.is_healthy is True
        
        sample_health_check.status = HealthStatus.CRITICAL
        assert sample_health_check.is_healthy is False

    def test_health_check_is_overdue_property(self, sample_health_check):
        """Test health check is_overdue property."""
        # Future check time
        sample_health_check.next_check_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        assert sample_health_check.is_overdue is False
        
        # Past check time
        sample_health_check.next_check_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert sample_health_check.is_overdue is True
        
        # No check time
        sample_health_check.next_check_at = None
        assert sample_health_check.is_overdue is False

    def test_health_check_schedule_next_check(self, sample_health_check):
        """Test scheduling next health check."""
        original_time = sample_health_check.next_check_at
        sample_health_check.schedule_next_check()
        
        assert sample_health_check.next_check_at > original_time

    def test_metric_value_float_property(self, sample_metric):
        """Test metric value_float property."""
        assert sample_metric.value_float == 75.5

    def test_alert_is_active_property(self, sample_alert):
        """Test alert is_active property."""
        assert sample_alert.is_active is True
        
        sample_alert.status = AlertStatus.RESOLVED
        assert sample_alert.is_active is False

    def test_alert_is_critical_property(self, sample_alert):
        """Test alert is_critical property."""
        sample_alert.severity = AlertSeverity.CRITICAL
        assert sample_alert.is_critical is True
        
        sample_alert.severity = AlertSeverity.EMERGENCY
        assert sample_alert.is_critical is True
        
        sample_alert.severity = AlertSeverity.WARNING
        assert sample_alert.is_critical is False

    def test_alert_duration_minutes_property(self, sample_alert):
        """Test alert duration calculation."""
        # Mock time difference
        duration = sample_alert.duration_minutes
        assert isinstance(duration, int)
        assert duration >= 0

    def test_alert_acknowledge_method(self, sample_alert):
        """Test alert acknowledge method."""
        user_id = str(uuid4())
        sample_alert.acknowledge(user_id)
        
        assert sample_alert.status == AlertStatus.ACKNOWLEDGED
        assert sample_alert.acknowledged_by == user_id
        assert sample_alert.acknowledged_at is not None

    def test_alert_resolve_method(self, sample_alert):
        """Test alert resolve method."""
        user_id = str(uuid4())
        sample_alert.resolve(user_id)
        
        assert sample_alert.status == AlertStatus.RESOLVED
        assert sample_alert.resolved_by == user_id
        assert sample_alert.resolved_at is not None

    def test_alert_suppress_method(self, sample_alert):
        """Test alert suppress method."""
        sample_alert.suppress()
        
        assert sample_alert.status == AlertStatus.SUPPRESSED

    def test_sla_record_uptime_percentage_float(self, sample_sla_record):
        """Test SLA record uptime percentage as float."""
        assert sample_sla_record.uptime_percentage_float == 99.95

    def test_sla_record_sla_score(self, sample_sla_record):
        """Test SLA record score calculation."""
        score = sample_sla_record.sla_score
        
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_sla_record_credit_amount(self, sample_sla_record):
        """Test SLA record credit amount property."""
        assert sample_sla_record.credit_amount == Decimal("0.00")

    def test_monitoring_enum_values(self):
        """Test monitoring enum values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.WARNING == "warning"
        assert HealthStatus.CRITICAL == "critical"
        assert HealthStatus.UNKNOWN == "unknown"
        
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.EMERGENCY == "emergency"
        
        assert AlertStatus.ACTIVE == "active"
        assert AlertStatus.ACKNOWLEDGED == "acknowledged"
        assert AlertStatus.RESOLVED == "resolved"
        assert AlertStatus.SUPPRESSED == "suppressed"
        
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"
        assert MetricType.SUMMARY == "summary"


@pytest.mark.integration
class TestMonitoringRepositoryIntegration:
    """Integration tests for monitoring repository."""
    
    @pytest.mark.asyncio
    async def test_monitoring_workflow_integration(self, monitoring_repo, sample_tenant_id):
        """Test complete monitoring workflow."""
        # Mock health check recording
        monitoring_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
        
        # Record health check
        health_check = await monitoring_repo.record_health_check(
            tenant_id=sample_tenant_id,
            check_name="Integration Test",
            check_type="http",
            status=HealthStatus.HEALTHY,
            success=True
        )
        
        # Mock metric recording
        monitoring_repo.db.add = MagicMock()
        monitoring_repo.db.flush = AsyncMock()
        monitoring_repo.db.refresh = AsyncMock()
        
        # Record metric
        metric = await monitoring_repo.record_metric(
            tenant_id=sample_tenant_id,
            metric_name="test_metric",
            metric_type=MetricType.GAUGE,
            value=42.0
        )
        
        # Mock alert creation
        alert = await monitoring_repo.create_alert(
            tenant_id=sample_tenant_id,
            alert_name="Integration Alert",
            alert_type="test",
            severity=AlertSeverity.INFO,
            title="Integration test alert"
        )
        
        assert health_check is not None
        assert metric is not None
        assert alert is not None

    @pytest.mark.asyncio
    async def test_sla_compliance_calculation_integration(self, sla_repo, sample_tenant_id):
        """Test SLA compliance calculation with multiple records."""
        # Create multiple SLA records with different compliance
        sla_records = []
        
        # 3 compliant records
        for i in range(3):
            record = MagicMock()
            record.overall_sla_met = True
            record.uptime_percentage = Decimal("99.95")
            record.response_time_avg_ms = 145
            record.incident_count = 0
            record.total_downtime_minutes = 0
            sla_records.append(record)
        
        # 1 non-compliant record
        record = MagicMock()
        record.overall_sla_met = False
        record.uptime_percentage = Decimal("99.85")
        record.response_time_avg_ms = 180
        record.incident_count = 2
        record.total_downtime_minutes = 45
        sla_records.append(record)
        
        sla_repo.get_sla_history = AsyncMock(return_value=sla_records)
        
        summary = await sla_repo.get_sla_compliance_summary(sample_tenant_id)
        
        assert summary["compliance_rate"] == 75.0  # 3 out of 4 compliant
        assert summary["average_uptime"] == 99.925  # Average of all records
        assert summary["total_incidents"] == 2
        assert summary["total_downtime_minutes"] == 45
        assert summary["periods_analyzed"] == 4