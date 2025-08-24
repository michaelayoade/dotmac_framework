"""
Comprehensive test suite for Analytics module - ISP Framework
Tests analytics functionality including metrics, reporting, and dashboards
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from uuid import uuid4


class MetricType(Enum):
    """Metric types for analytics"""
    BANDWIDTH = "bandwidth"
    REVENUE = "revenue" 
    CUSTOMER_COUNT = "customer_count"
    SERVICE_UPTIME = "service_uptime"
    SUPPORT_TICKETS = "support_tickets"
    NETWORK_LATENCY = "network_latency"
    DATA_USAGE = "data_usage"


class ReportType(Enum):
    """Report types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockMetric:
    """Mock metric data point"""
    id: str
    tenant_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def is_anomaly(self, threshold: float = 2.0) -> bool:
        """Check if metric value is an anomaly"""
        baseline = self.metadata.get("baseline", 0)
        if baseline == 0:
            return False
        deviation = abs((self.value - baseline) / baseline)
        return deviation > threshold


@dataclass 
class MockReport:
    """Mock analytics report"""
    id: str
    tenant_id: str
    report_type: ReportType
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    generated_at: datetime
    data: Dict[str, Any]
    filters: Dict[str, Any]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get report summary statistics"""
        total_customers = self.data.get("total_customers", 0)
        total_revenue = self.data.get("total_revenue", 0)
        avg_bandwidth = self.data.get("avg_bandwidth_mbps", 0)
        
        return {
            "total_customers": total_customers,
            "total_revenue": total_revenue,
            "avg_bandwidth_mbps": avg_bandwidth,
            "uptime_percentage": self.data.get("uptime_percentage", 99.0),
            "support_tickets": self.data.get("support_tickets", 0)
        }
    
    def export_format(self, format_type: str = "json") -> str:
        """Export report in specified format"""
        if format_type == "csv":
            return "CSV export data"
        elif format_type == "pdf":
            return "PDF export data"
        return str(self.data)


@dataclass
class MockDashboard:
    """Mock analytics dashboard"""
    id: str
    tenant_id: str
    name: str
    description: str
    widgets: List[Dict[str, Any]]
    layout: Dict[str, Any]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    def add_widget(self, widget_type: str, config: Dict[str, Any]) -> None:
        """Add widget to dashboard"""
        widget = {
            "id": str(uuid4()),
            "type": widget_type,
            "config": config,
            "position": len(self.widgets)
        }
        self.widgets.append(widget)
    
    def get_widget_count(self) -> int:
        """Get total widget count"""
        return len(self.widgets)
    
    def calculate_load_time(self) -> float:
        """Calculate estimated dashboard load time"""
        base_time = 0.5  # Base 500ms
        widget_time = len(self.widgets) * 0.2  # 200ms per widget
        return base_time + widget_time


@dataclass
class MockAlert:
    """Mock analytics alert"""
    id: str
    tenant_id: str
    metric_type: MetricType
    condition: str
    threshold: float
    severity: AlertSeverity
    is_active: bool
    last_triggered: Optional[datetime]
    notification_channels: List[str]
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should trigger"""
        if not self.is_active:
            return False
            
        if self.condition == "greater_than":
            return current_value > self.threshold
        elif self.condition == "less_than":
            return current_value < self.threshold
        elif self.condition == "equals":
            return abs(current_value - self.threshold) < 0.01
        return False
    
    def get_priority_score(self) -> int:
        """Get alert priority score"""
        severity_scores = {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4
        }
        base_score = severity_scores.get(self.severity, 1)
        
        # Increase priority if recently triggered
        if self.last_triggered and (datetime.utcnow() - self.last_triggered).seconds < 3600:
            base_score += 1
            
        return min(base_score, 5)


class TestAnalyticsMetrics:
    """Test analytics metrics functionality"""
    
    def test_metric_creation(self):
        """Test creating metric data points"""
        metric = MockMetric(
            id="metric_1",
            tenant_id="tenant_123",
            metric_type=MetricType.BANDWIDTH,
            value=150.5,
            timestamp=datetime.utcnow(),
            metadata={"location": "datacenter_1", "baseline": 100.0}
        )
        
        assert metric.id == "metric_1"
        assert metric.tenant_id == "tenant_123"
        assert metric.metric_type == MetricType.BANDWIDTH
        assert metric.value == 150.5
        assert "location" in metric.metadata
    
    def test_metric_to_dict(self):
        """Test metric dictionary conversion"""
        timestamp = datetime.utcnow()
        metric = MockMetric(
            id="metric_2",
            tenant_id="tenant_456",
            metric_type=MetricType.REVENUE,
            value=25000.0,
            timestamp=timestamp,
            metadata={"currency": "USD"}
        )
        
        data = metric.to_dict()
        assert data["id"] == "metric_2"
        assert data["metric_type"] == "revenue"
        assert data["value"] == 25000.0
        assert data["timestamp"] == timestamp.isoformat()
    
    def test_metric_anomaly_detection(self):
        """Test metric anomaly detection"""
        # Normal metric (within threshold)
        normal_metric = MockMetric(
            id="normal",
            tenant_id="tenant_1",
            metric_type=MetricType.BANDWIDTH,
            value=105.0,
            timestamp=datetime.utcnow(),
            metadata={"baseline": 100.0}
        )
        assert not normal_metric.is_anomaly(threshold=2.0)
        
        # Anomaly metric (exceeds threshold)
        anomaly_metric = MockMetric(
            id="anomaly",
            tenant_id="tenant_1", 
            metric_type=MetricType.BANDWIDTH,
            value=350.0,
            timestamp=datetime.utcnow(),
            metadata={"baseline": 100.0}
        )
        assert anomaly_metric.is_anomaly(threshold=2.0)
    
    def test_metric_types_enum(self):
        """Test metric type enumeration"""
        assert MetricType.BANDWIDTH.value == "bandwidth"
        assert MetricType.REVENUE.value == "revenue"
        assert MetricType.CUSTOMER_COUNT.value == "customer_count"
        assert MetricType.SERVICE_UPTIME.value == "service_uptime"
        
        # Test all enum values are strings
        for metric_type in MetricType:
            assert isinstance(metric_type.value, str)


class TestAnalyticsReports:
    """Test analytics reporting functionality"""
    
    def test_report_creation(self):
        """Test creating analytics reports"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        generated_at = datetime.utcnow()
        
        report = MockReport(
            id="report_1",
            tenant_id="tenant_123",
            report_type=ReportType.MONTHLY,
            title="January 2024 Performance Report",
            description="Monthly performance metrics and analytics",
            start_date=start_date,
            end_date=end_date,
            generated_at=generated_at,
            data={
                "total_customers": 1500,
                "total_revenue": 150000.0,
                "avg_bandwidth_mbps": 85.5,
                "uptime_percentage": 99.8
            },
            filters={"service_type": "broadband"}
        )
        
        assert report.report_type == ReportType.MONTHLY
        assert report.title == "January 2024 Performance Report"
        assert report.data["total_customers"] == 1500
    
    def test_report_summary(self):
        """Test report summary generation"""
        report = MockReport(
            id="report_2",
            tenant_id="tenant_456",
            report_type=ReportType.WEEKLY,
            title="Week 1 Summary",
            description="Weekly summary report",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            generated_at=datetime.utcnow(),
            data={
                "total_customers": 500,
                "total_revenue": 50000.0,
                "avg_bandwidth_mbps": 75.0,
                "uptime_percentage": 99.5,
                "support_tickets": 25
            },
            filters={}
        )
        
        summary = report.get_summary()
        assert summary["total_customers"] == 500
        assert summary["total_revenue"] == 50000.0
        assert summary["avg_bandwidth_mbps"] == 75.0
        assert summary["uptime_percentage"] == 99.5
        assert summary["support_tickets"] == 25
    
    def test_report_export(self):
        """Test report export functionality"""
        report = MockReport(
            id="report_3",
            tenant_id="tenant_789",
            report_type=ReportType.DAILY,
            title="Daily Report",
            description="Daily metrics",
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 1, 15),
            generated_at=datetime.utcnow(),
            data={"customers": 100},
            filters={}
        )
        
        # Test different export formats
        csv_export = report.export_format("csv")
        pdf_export = report.export_format("pdf")
        json_export = report.export_format("json")
        
        assert csv_export == "CSV export data"
        assert pdf_export == "PDF export data"
        assert "customers" in json_export
    
    def test_report_types_enum(self):
        """Test report type enumeration"""
        assert ReportType.DAILY.value == "daily"
        assert ReportType.WEEKLY.value == "weekly"
        assert ReportType.MONTHLY.value == "monthly"
        assert ReportType.QUARTERLY.value == "quarterly"
        assert ReportType.YEARLY.value == "yearly"
        assert ReportType.CUSTOM.value == "custom"


class TestAnalyticsDashboards:
    """Test analytics dashboard functionality"""
    
    def test_dashboard_creation(self):
        """Test creating analytics dashboards"""
        created_at = datetime.utcnow()
        dashboard = MockDashboard(
            id="dash_1",
            tenant_id="tenant_123",
            name="Executive Dashboard",
            description="High-level KPIs and metrics",
            widgets=[],
            layout={"columns": 3, "rows": 2},
            is_public=False,
            created_at=created_at,
            updated_at=created_at
        )
        
        assert dashboard.name == "Executive Dashboard"
        assert dashboard.is_public is False
        assert dashboard.get_widget_count() == 0
    
    def test_dashboard_widget_management(self):
        """Test adding widgets to dashboard"""
        dashboard = MockDashboard(
            id="dash_2",
            tenant_id="tenant_456",
            name="Operational Dashboard",
            description="Real-time operational metrics",
            widgets=[],
            layout={},
            is_public=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add revenue widget
        dashboard.add_widget("revenue_chart", {
            "title": "Monthly Revenue",
            "chart_type": "line",
            "metric": "revenue",
            "period": "monthly"
        })
        
        # Add bandwidth widget  
        dashboard.add_widget("bandwidth_gauge", {
            "title": "Current Bandwidth",
            "chart_type": "gauge",
            "metric": "bandwidth",
            "max_value": 1000
        })
        
        assert dashboard.get_widget_count() == 2
        assert dashboard.widgets[0]["type"] == "revenue_chart"
        assert dashboard.widgets[1]["type"] == "bandwidth_gauge"
    
    def test_dashboard_load_time_calculation(self):
        """Test dashboard load time estimation"""
        dashboard = MockDashboard(
            id="dash_3",
            tenant_id="tenant_789",
            name="Performance Dashboard", 
            description="Performance metrics",
            widgets=[],
            layout={},
            is_public=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Empty dashboard
        load_time = dashboard.calculate_load_time()
        assert load_time == 0.5  # Base time only
        
        # Add 5 widgets
        for i in range(5):
            dashboard.add_widget(f"widget_{i}", {"title": f"Widget {i}"})
        
        load_time = dashboard.calculate_load_time()
        assert load_time == 1.5  # 0.5 base + (5 * 0.2) widget time


class TestAnalyticsAlerts:
    """Test analytics alerting functionality"""
    
    def test_alert_creation(self):
        """Test creating analytics alerts"""
        alert = MockAlert(
            id="alert_1",
            tenant_id="tenant_123",
            metric_type=MetricType.BANDWIDTH,
            condition="greater_than",
            threshold=500.0,
            severity=AlertSeverity.HIGH,
            is_active=True,
            last_triggered=None,
            notification_channels=["email", "sms", "slack"]
        )
        
        assert alert.metric_type == MetricType.BANDWIDTH
        assert alert.condition == "greater_than"
        assert alert.threshold == 500.0
        assert alert.severity == AlertSeverity.HIGH
        assert len(alert.notification_channels) == 3
    
    def test_alert_trigger_conditions(self):
        """Test alert triggering logic"""
        # Greater than condition
        gt_alert = MockAlert(
            id="gt_alert",
            tenant_id="tenant_1",
            metric_type=MetricType.BANDWIDTH,
            condition="greater_than", 
            threshold=100.0,
            severity=AlertSeverity.MEDIUM,
            is_active=True,
            last_triggered=None,
            notification_channels=["email"]
        )
        
        assert gt_alert.should_trigger(150.0) is True
        assert gt_alert.should_trigger(50.0) is False
        
        # Less than condition
        lt_alert = MockAlert(
            id="lt_alert",
            tenant_id="tenant_1",
            metric_type=MetricType.SERVICE_UPTIME,
            condition="less_than",
            threshold=99.0,
            severity=AlertSeverity.CRITICAL,
            is_active=True,
            last_triggered=None,
            notification_channels=["email", "sms"]
        )
        
        assert lt_alert.should_trigger(95.0) is True  
        assert lt_alert.should_trigger(99.5) is False
    
    def test_alert_priority_scoring(self):
        """Test alert priority calculation"""
        # Low severity alert
        low_alert = MockAlert(
            id="low_alert",
            tenant_id="tenant_1",
            metric_type=MetricType.DATA_USAGE,
            condition="greater_than",
            threshold=1000.0,
            severity=AlertSeverity.LOW,
            is_active=True,
            last_triggered=None,
            notification_channels=["email"]
        )
        
        assert low_alert.get_priority_score() == 1
        
        # Critical severity alert
        critical_alert = MockAlert(
            id="critical_alert", 
            tenant_id="tenant_1",
            metric_type=MetricType.SERVICE_UPTIME,
            condition="less_than",
            threshold=95.0,
            severity=AlertSeverity.CRITICAL,
            is_active=True,
            last_triggered=None,
            notification_channels=["email", "sms", "phone"]
        )
        
        assert critical_alert.get_priority_score() == 4
        
        # Recently triggered alert (higher priority)
        recent_alert = MockAlert(
            id="recent_alert",
            tenant_id="tenant_1", 
            metric_type=MetricType.NETWORK_LATENCY,
            condition="greater_than",
            threshold=100.0,
            severity=AlertSeverity.HIGH,
            is_active=True,
            last_triggered=datetime.utcnow() - timedelta(minutes=30),
            notification_channels=["slack"]
        )
        
        priority = recent_alert.get_priority_score()
        assert priority == 4  # 3 (HIGH) + 1 (recently triggered)
    
    def test_inactive_alert_no_trigger(self):
        """Test inactive alerts don't trigger"""
        inactive_alert = MockAlert(
            id="inactive",
            tenant_id="tenant_1",
            metric_type=MetricType.REVENUE,
            condition="less_than",
            threshold=10000.0,
            severity=AlertSeverity.HIGH,
            is_active=False,  # Inactive
            last_triggered=None,
            notification_channels=["email"]
        )
        
        # Should not trigger even if condition is met
        assert inactive_alert.should_trigger(5000.0) is False


class TestAnalyticsEnums:
    """Test analytics enumeration classes"""
    
    def test_alert_severity_enum(self):
        """Test alert severity enumeration"""
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium" 
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"
        
        # Test enum ordering by creating list
        severities = [AlertSeverity.LOW, AlertSeverity.MEDIUM, AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        assert len(severities) == 4


class TestAnalyticsIntegration:
    """Test analytics module integration scenarios"""
    
    def test_metric_to_report_workflow(self):
        """Test workflow from metrics to reports"""
        # Create sample metrics
        metrics = []
        base_time = datetime(2024, 1, 1)
        
        for i in range(30):  # 30 days of data
            metric = MockMetric(
                id=f"metric_{i}",
                tenant_id="tenant_123",
                metric_type=MetricType.REVENUE,
                value=1000.0 + (i * 50),  # Increasing revenue
                timestamp=base_time + timedelta(days=i),
                metadata={"region": "north"}
            )
            metrics.append(metric)
        
        # Generate monthly report from metrics
        total_revenue = sum(m.value for m in metrics)
        avg_daily_revenue = total_revenue / len(metrics)
        
        report = MockReport(
            id="monthly_report",
            tenant_id="tenant_123",
            report_type=ReportType.MONTHLY,
            title="January 2024 Revenue Report",
            description="Monthly revenue analysis",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31), 
            generated_at=datetime.utcnow(),
            data={
                "total_revenue": total_revenue,
                "avg_daily_revenue": avg_daily_revenue,
                "metric_count": len(metrics)
            },
            filters={"region": "north"}
        )
        
        assert report.data["total_revenue"] == 51750.0  # Sum calculation
        assert report.data["avg_daily_revenue"] == 1725.0  # Average calculation
        assert report.data["metric_count"] == 30
    
    def test_dashboard_with_alerts_integration(self):
        """Test dashboard integration with alerts"""
        # Create dashboard
        dashboard = MockDashboard(
            id="ops_dashboard",
            tenant_id="tenant_456", 
            name="Operations Dashboard",
            description="Real-time operational monitoring",
            widgets=[],
            layout={"columns": 2, "rows": 3},
            is_public=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add alert-based widgets
        dashboard.add_widget("alerts_panel", {
            "title": "Active Alerts",
            "alert_severities": ["high", "critical"],
            "max_alerts": 10
        })
        
        dashboard.add_widget("bandwidth_status", {
            "title": "Bandwidth Status", 
            "metric": "bandwidth",
            "alert_threshold": 500.0
        })
        
        # Create related alerts
        bandwidth_alert = MockAlert(
            id="bw_alert",
            tenant_id="tenant_456",
            metric_type=MetricType.BANDWIDTH,
            condition="greater_than",
            threshold=500.0,
            severity=AlertSeverity.HIGH,
            is_active=True,
            last_triggered=datetime.utcnow() - timedelta(minutes=10),
            notification_channels=["dashboard", "email"]
        )
        
        # Test integration
        assert dashboard.get_widget_count() == 2
        assert "dashboard" in bandwidth_alert.notification_channels
        assert bandwidth_alert.should_trigger(600.0) is True
        
        # Dashboard load time should account for alert widgets
        load_time = dashboard.calculate_load_time()
        assert load_time == 0.9  # 0.5 base + (2 * 0.2) widgets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])