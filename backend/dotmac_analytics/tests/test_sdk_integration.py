"""
Integration tests for DotMac Analytics SDK.
"""

from datetime import datetime, timedelta
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso

import pytest

from dotmac_analytics.models.enums import (
    AggregationMethod,
    EventType,
    MetricType,
    TimeGranularity,
)


class TestAnalyticsClientIntegration:
    """Integration tests for AnalyticsClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, analytics_client):
        """Test client initialization and health check."""
        health = await analytics_client.health_check()
        assert health["status"] in ["healthy", "unhealthy"]
        assert health["tenant_id"] == analytics_client.tenant_id

    @pytest.mark.asyncio
    async def test_tenant_initialization(self, analytics_client):
        """Test tenant initialization with default resources."""
        result = await analytics_client.initialize_tenant()
        assert result["status"] == "initialized"
        assert result["tenant_id"] == analytics_client.tenant_id
        assert "created_metrics" in result


class TestEventsSDKIntegration:
    """Integration tests for EventsSDK."""

    @pytest.mark.asyncio
    async def test_track_single_event(self, analytics_client, sample_event_data):
        """Test tracking a single event."""
        result = await analytics_client.events.track(
            event_type=EventType(sample_event_data["event_type"]),
            event_name=sample_event_data["event_name"],
            user_id=sample_event_data["user_id"],
            session_id=sample_event_data["session_id"],
            properties=sample_event_data["properties"],
            context=sample_event_data["context"]
        )

        assert result["status"] == "tracked"
        assert "event_id" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_track_event_batch(self, analytics_client, sample_event_data):
        """Test tracking multiple events in a batch."""
        events = [
            {
                "event_type": sample_event_data["event_type"],
                "event_name": f"{sample_event_data['event_name']}_{i}",
                "user_id": f"{sample_event_data['user_id']}_{i}",
                "properties": sample_event_data["properties"],
                "timestamp": utc_now().isoformat()
            }
            for i in range(3)
        ]

        result = await analytics_client.events.track_batch(events)

        assert result["status"] in ["completed", "partial_success"]
        assert result["success_count"] >= 0
        assert "batch_id" in result

    @pytest.mark.asyncio
    async def test_query_events(self, populated_analytics_client):
        """Test querying events with filters."""
        events = await populated_analytics_client.events.get_events(
            event_type=EventType.PAGE_VIEW,
            limit=10
        )

        assert isinstance(events, list)
        assert len(events) > 0

        for event in events:
            assert "id" in event
            assert "event_name" in event
            assert "timestamp" in event

    @pytest.mark.asyncio
    async def test_event_aggregation(self, populated_analytics_client):
        """Test event aggregation by time."""
        end_time = utc_now()
        start_time = end_time - timedelta(hours=1)

        aggregates = await populated_analytics_client.events.aggregate(
            granularity=TimeGranularity.HOUR,
            start_time=start_time,
            end_time=end_time
        )

        assert isinstance(aggregates, list)

        for aggregate in aggregates:
            assert "time_bucket" in aggregate
            assert "event_count" in aggregate
            assert "unique_users" in aggregate

    @pytest.mark.asyncio
    async def test_convenience_methods(self, analytics_client):
        """Test convenience methods for common event types."""
        # Test page view tracking
        result = await analytics_client.events.track_page_view(
            page_url="/test-page",
            page_title="Test Page",
            user_id="test_user"
        )
        assert result["status"] == "tracked"

        # Test click tracking
        result = await analytics_client.events.track_click(
            element_id="test-button",
            element_text="Click Me",
            user_id="test_user"
        )
        assert result["status"] == "tracked"

        # Test conversion tracking
        result = await analytics_client.events.track_conversion(
            conversion_type="purchase",
            conversion_value=99.99,
            user_id="test_user"
        )
        assert result["status"] == "tracked"


class TestMetricsSDKIntegration:
    """Integration tests for MetricsSDK."""

    @pytest.mark.asyncio
    async def test_create_metric(self, analytics_client, sample_metric_data):
        """Test creating a new metric."""
        result = await analytics_client.metrics.create_metric(
            name=sample_metric_data["name"],
            display_name=sample_metric_data["display_name"],
            metric_type=MetricType(sample_metric_data["metric_type"]),
            description=sample_metric_data["description"],
            unit=sample_metric_data["unit"],
            dimensions=sample_metric_data["dimensions"],
            tags=sample_metric_data["tags"]
        )

        assert "metric_id" in result
        assert result["name"] == sample_metric_data["name"]
        assert result["metric_type"] == sample_metric_data["metric_type"]

    @pytest.mark.asyncio
    async def test_record_metric_value(self, populated_analytics_client, sample_metric_data):
        """Test recording metric values."""
        result = await populated_analytics_client.metrics.record_value(
            metric_id=sample_metric_data["name"],
            value=100.5,
            dimensions={"page_url": "/home", "user_type": "premium"}
        )

        assert "value_id" in result
        assert result["value"] == 100.5
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_metrics(self, populated_analytics_client):
        """Test retrieving metrics."""
        metrics = await populated_analytics_client.metrics.get_metrics(
            metric_type=MetricType.COUNTER,
            limit=10
        )

        assert isinstance(metrics, list)
        assert len(metrics) > 0

        for metric in metrics:
            assert "id" in metric
            assert "name" in metric
            assert "metric_type" in metric

    @pytest.mark.asyncio
    async def test_metric_aggregation(self, populated_analytics_client, sample_metric_data):
        """Test metric value aggregation."""
        # Record some values first
        for i in range(5):
            await populated_analytics_client.metrics.record_value(
                metric_id=sample_metric_data["name"],
                value=i * 10
            )

        end_time = utc_now()
        start_time = end_time - timedelta(hours=1)

        aggregates = await populated_analytics_client.metrics.aggregate(
            metric_id=sample_metric_data["name"],
            aggregation_method=AggregationMethod.SUM,
            granularity=TimeGranularity.HOUR,
            start_time=start_time,
            end_time=end_time
        )

        assert isinstance(aggregates, list)

        for aggregate in aggregates:
            assert "time_bucket" in aggregate
            assert "value" in aggregate
            assert "sample_count" in aggregate

    @pytest.mark.asyncio
    async def test_metric_trend_analysis(self, populated_analytics_client, sample_metric_data):
        """Test metric trend calculation."""
        # Record values for two periods
        current_end = utc_now()
        current_start = current_end - timedelta(hours=1)
        comparison_end = current_start
        comparison_start = comparison_end - timedelta(hours=1)

        # Record values for current period
        for i in range(3):
            await populated_analytics_client.metrics.record_value(
                metric_id=sample_metric_data["name"],
                value=20 + i
            )

        trend = await populated_analytics_client.metrics.calculate_trend(
            metric_id=sample_metric_data["name"],
            current_period_start=current_start,
            current_period_end=current_end,
            comparison_period_start=comparison_start,
            comparison_period_end=comparison_end
        )

        assert "current_period" in trend
        assert "comparison_period" in trend
        assert "trend" in trend
        assert "change_percent" in trend["trend"]

    @pytest.mark.asyncio
    async def test_convenience_methods(self, populated_analytics_client):
        """Test convenience methods for metric operations."""
        # Test increment
        result = await populated_analytics_client.metrics.increment(
            metric_name="test_counter",
            value=5
        )
        assert result["value"] == 5

        # Test set gauge
        result = await populated_analytics_client.metrics.set_gauge(
            metric_name="test_gauge",
            value=75.5
        )
        assert result["value"] == 75.5

        # Test record timing
        result = await populated_analytics_client.metrics.record_timing(
            metric_name="test_timing",
            duration_ms=250.0
        )
        assert result["value"] == 250.0


class TestDashboardsSDKIntegration:
    """Integration tests for DashboardsSDK."""

    @pytest.mark.asyncio
    async def test_create_dashboard(self, analytics_client, sample_dashboard_data):
        """Test creating a dashboard."""
        result = await analytics_client.dashboards.create_dashboard(
            name=sample_dashboard_data["name"],
            display_name=sample_dashboard_data["display_name"],
            description=sample_dashboard_data["description"],
            category=sample_dashboard_data["category"],
            layout=sample_dashboard_data["layout"]
        )

        assert "dashboard_id" in result
        assert result["name"] == sample_dashboard_data["name"]
        assert result["display_name"] == sample_dashboard_data["display_name"]

    @pytest.mark.asyncio
    async def test_create_widget(self, analytics_client, sample_dashboard_data, sample_widget_data):
        """Test creating a widget."""
        # Create dashboard first
        dashboard_result = await analytics_client.dashboards.create_dashboard(
            name=sample_dashboard_data["name"],
            display_name=sample_dashboard_data["display_name"]
        )

        # Create widget
        result = await analytics_client.dashboards.create_widget(
            dashboard_id=dashboard_result["dashboard_id"],
            name=sample_widget_data["name"],
            title=sample_widget_data["title"],
            widget_type=sample_widget_data["widget_type"],
            query_config=sample_widget_data["query_config"],
            visualization_config=sample_widget_data["visualization_config"]
        )

        assert "widget_id" in result
        assert result["name"] == sample_widget_data["name"]
        assert result["title"] == sample_widget_data["title"]


class TestReportsSDKIntegration:
    """Integration tests for ReportsSDK."""

    @pytest.mark.asyncio
    async def test_create_report(self, analytics_client, sample_report_data):
        """Test creating a report."""
        from dotmac_analytics.models.enums import ReportType

        result = await analytics_client.reports.create_report(
            name=sample_report_data["name"],
            display_name=sample_report_data["display_name"],
            report_type=ReportType(sample_report_data["report_type"]),
            query_config=sample_report_data["query_config"],
            description=sample_report_data["description"]
        )

        assert "report_id" in result
        assert result["name"] == sample_report_data["name"]
        assert result["report_type"] == sample_report_data["report_type"]

    @pytest.mark.asyncio
    async def test_generate_report(self, analytics_client, sample_report_data):
        """Test generating a report."""
        from dotmac_analytics.models.enums import ReportType

        # Create report first
        report_result = await analytics_client.reports.create_report(
            name=sample_report_data["name"],
            display_name=sample_report_data["display_name"],
            report_type=ReportType(sample_report_data["report_type"]),
            query_config=sample_report_data["query_config"]
        )

        # Generate report
        result = await analytics_client.reports.generate_report(
            report_id=report_result["report_id"]
        )

        assert "execution_id" in result
        assert result["status"] == "completed"
        assert "output_files" in result


class TestSegmentsSDKIntegration:
    """Integration tests for SegmentsSDK."""

    @pytest.mark.asyncio
    async def test_create_segment(self, analytics_client, sample_segment_data):
        """Test creating a segment."""
        result = await analytics_client.segments.create_segment(
            name=sample_segment_data["name"],
            display_name=sample_segment_data["display_name"],
            entity_type=sample_segment_data["entity_type"],
            description=sample_segment_data["description"],
            category=sample_segment_data["category"]
        )

        assert "segment_id" in result
        assert result["name"] == sample_segment_data["name"]
        assert result["entity_type"] == sample_segment_data["entity_type"]

    @pytest.mark.asyncio
    async def test_add_segment_rule(self, analytics_client, sample_segment_data):
        """Test adding rules to a segment."""
        from dotmac_analytics.models.enums import SegmentOperator

        # Create segment first
        segment_result = await analytics_client.segments.create_segment(
            name=sample_segment_data["name"],
            display_name=sample_segment_data["display_name"],
            entity_type=sample_segment_data["entity_type"]
        )

        # Add rule
        result = await analytics_client.segments.add_segment_rule(
            segment_id=segment_result["segment_id"],
            field_name="last_active",
            operator=SegmentOperator.GREATER_THAN,
            value="2023-01-01"
        )

        assert "rule_id" in result
        assert result["field_name"] == "last_active"


class TestErrorHandling:
    """Test error handling across SDK components."""

    @pytest.mark.asyncio
    async def test_invalid_metric_id(self, analytics_client):
        """Test handling of invalid metric ID."""
        with pytest.raises(Exception):
            await analytics_client.metrics.record_value(
                metric_id="non_existent_metric",
                value=100
            )

    @pytest.mark.asyncio
    async def test_invalid_event_type(self, analytics_client):
        """Test handling of invalid event type."""
        with pytest.raises(Exception):
            await analytics_client.events.track(
                event_type="invalid_type",
                event_name="test_event"
            )


class TestTenantIsolation:
    """Test tenant isolation across all operations."""

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self, db_session):
        """Test that tenant data is properly isolated."""
        # Create clients for different tenants
        client1 = AnalyticsClient("tenant_1", db_session)
        client2 = AnalyticsClient("tenant_2", db_session)

        try:
            # Create metric in tenant 1
            await client1.metrics.create_metric(
                name="test_metric",
                display_name="Test Metric",
                metric_type=MetricType.COUNTER
            )

            # Try to access from tenant 2
            metric = await client2.metrics.get_metric("test_metric")
            assert metric is None  # Should not be accessible

            # Create same metric in tenant 2
            result = await client2.metrics.create_metric(
                name="test_metric",
                display_name="Test Metric",
                metric_type=MetricType.COUNTER
            )
            assert "metric_id" in result

        finally:
            client1.close()
            client2.close()
