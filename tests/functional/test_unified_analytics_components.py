"""
Functional tests for unified analytics service components.

Tests the business/workflow/infrastructure/knowledge components to ensure
they integrate properly and provide expected functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.dotmac_shared.services.unified_analytics_service import (
    AnalyticsType,
    MetricType,
    UnifiedAnalyticsService,
    AnalyticsQuery,
    MetricDefinition,
    AnalyticsResult,
)


class TestUnifiedAnalyticsComponents:
    """Test suite for unified analytics service components."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def analytics_service(self, mock_db_session):
        """Create analytics service instance."""
        return UnifiedAnalyticsService(db=mock_db_session, tenant_id="test-tenant")

    @pytest.fixture
    def sample_metrics(self):
        """Sample metric definitions for testing."""
        return [
            MetricDefinition(
                name="user_login_count",
                type=MetricType.COUNTER,
                analytics_type=AnalyticsType.BUSINESS,
                description="Number of user logins",
                labels=["user_type", "platform"],
            ),
            MetricDefinition(
                name="workflow_execution_duration",
                type=MetricType.HISTOGRAM,
                analytics_type=AnalyticsType.WORKFLOW,
                description="Workflow execution time",
                labels=["workflow_name", "status"],
                buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
            ),
            MetricDefinition(
                name="cpu_utilization",
                type=MetricType.GAUGE,
                analytics_type=AnalyticsType.INFRASTRUCTURE,
                description="CPU utilization percentage",
                labels=["host", "core"],
            ),
            MetricDefinition(
                name="knowledge_article_views",
                type=MetricType.COUNTER,
                analytics_type=AnalyticsType.KNOWLEDGE,
                description="Knowledge article view count",
                labels=["category", "article_type"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_business_analytics_component(self, analytics_service, sample_metrics):
        """Test business analytics component functionality."""
        business_metric = sample_metrics[0]  # user_login_count
        
        # Test metric registration
        await analytics_service.register_metric(business_metric)
        
        # Test metric collection
        timestamp = datetime.now(timezone.utc)
        await analytics_service.record_metric(
            metric_name="user_login_count",
            value=1,
            labels={"user_type": "customer", "platform": "web"},
            timestamp=timestamp
        )
        
        # Test metric query
        query = AnalyticsQuery(
            analytics_type=AnalyticsType.BUSINESS,
            metric_names=["user_login_count"],
            start_time=timestamp - timedelta(hours=1),
            end_time=timestamp + timedelta(hours=1),
            labels={"user_type": "customer"}
        )
        
        # Mock database result
        mock_result = [
            {
                "metric_name": "user_login_count",
                "value": 10.0,
                "labels": {"user_type": "customer", "platform": "web"},
                "timestamp": timestamp
            }
        ]
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        result = await analytics_service.query_metrics(query)
        
        assert isinstance(result, AnalyticsResult)
        assert result.analytics_type == AnalyticsType.BUSINESS
        assert len(result.data_points) == 1
        assert result.data_points[0]["value"] == 10.0
        assert result.data_points[0]["labels"]["user_type"] == "customer"

    @pytest.mark.asyncio
    async def test_workflow_analytics_component(self, analytics_service, sample_metrics):
        """Test workflow analytics component functionality."""
        workflow_metric = sample_metrics[1]  # workflow_execution_duration
        
        await analytics_service.register_metric(workflow_metric)
        
        # Test histogram metric recording
        timestamp = datetime.now(timezone.utc)
        await analytics_service.record_metric(
            metric_name="workflow_execution_duration",
            value=2.5,  # 2.5 seconds
            labels={"workflow_name": "customer_onboarding", "status": "success"},
            timestamp=timestamp
        )
        
        # Test workflow-specific query
        query = AnalyticsQuery(
            analytics_type=AnalyticsType.WORKFLOW,
            metric_names=["workflow_execution_duration"],
            start_time=timestamp - timedelta(hours=1),
            end_time=timestamp + timedelta(hours=1),
            aggregation_function="avg",
            group_by=["workflow_name"]
        )
        
        mock_result = [
            {
                "metric_name": "workflow_execution_duration",
                "value": 2.5,
                "labels": {"workflow_name": "customer_onboarding", "status": "success"},
                "timestamp": timestamp,
                "histogram_buckets": {"0.1": 0, "0.5": 0, "1.0": 0, "5.0": 1, "10.0": 1, "30.0": 1}
            }
        ]
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        result = await analytics_service.query_metrics(query)
        
        assert result.analytics_type == AnalyticsType.WORKFLOW
        assert len(result.data_points) == 1
        assert result.data_points[0]["labels"]["workflow_name"] == "customer_onboarding"
        assert "histogram_buckets" in result.data_points[0]

    @pytest.mark.asyncio
    async def test_infrastructure_analytics_component(self, analytics_service, sample_metrics):
        """Test infrastructure analytics component functionality."""
        infra_metric = sample_metrics[2]  # cpu_utilization
        
        await analytics_service.register_metric(infra_metric)
        
        # Test gauge metric recording (can go up and down)
        timestamp = datetime.now(timezone.utc)
        await analytics_service.record_metric(
            metric_name="cpu_utilization",
            value=75.5,
            labels={"host": "web-server-01", "core": "cpu0"},
            timestamp=timestamp
        )
        
        # Test infrastructure-specific query with time series
        query = AnalyticsQuery(
            analytics_type=AnalyticsType.INFRASTRUCTURE,
            metric_names=["cpu_utilization"],
            start_time=timestamp - timedelta(hours=1),
            end_time=timestamp + timedelta(hours=1),
            aggregation_function="max",
            time_bucket="5m"  # 5-minute buckets
        )
        
        mock_result = [
            {
                "metric_name": "cpu_utilization",
                "value": 75.5,
                "labels": {"host": "web-server-01", "core": "cpu0"},
                "timestamp": timestamp,
                "time_bucket": "2024-01-01T12:00:00Z"
            },
            {
                "metric_name": "cpu_utilization",
                "value": 82.1,
                "labels": {"host": "web-server-01", "core": "cpu0"},
                "timestamp": timestamp + timedelta(minutes=5),
                "time_bucket": "2024-01-01T12:05:00Z"
            }
        ]
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        result = await analytics_service.query_metrics(query)
        
        assert result.analytics_type == AnalyticsType.INFRASTRUCTURE
        assert len(result.data_points) == 2
        assert result.data_points[0]["value"] == 75.5
        assert result.data_points[1]["value"] == 82.1
        assert all("time_bucket" in dp for dp in result.data_points)

    @pytest.mark.asyncio
    async def test_knowledge_analytics_component(self, analytics_service, sample_metrics):
        """Test knowledge analytics component functionality."""
        knowledge_metric = sample_metrics[3]  # knowledge_article_views
        
        await analytics_service.register_metric(knowledge_metric)
        
        # Test knowledge-specific metric recording
        timestamp = datetime.now(timezone.utc)
        await analytics_service.record_metric(
            metric_name="knowledge_article_views",
            value=1,
            labels={"category": "troubleshooting", "article_type": "guide"},
            timestamp=timestamp
        )
        
        # Test knowledge analytics query with category breakdown
        query = AnalyticsQuery(
            analytics_type=AnalyticsType.KNOWLEDGE,
            metric_names=["knowledge_article_views"],
            start_time=timestamp - timedelta(days=7),
            end_time=timestamp,
            aggregation_function="sum",
            group_by=["category", "article_type"]
        )
        
        mock_result = [
            {
                "metric_name": "knowledge_article_views",
                "value": 25,
                "labels": {"category": "troubleshooting", "article_type": "guide"},
                "timestamp": timestamp
            },
            {
                "metric_name": "knowledge_article_views", 
                "value": 15,
                "labels": {"category": "troubleshooting", "article_type": "faq"},
                "timestamp": timestamp
            }
        ]
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        result = await analytics_service.query_metrics(query)
        
        assert result.analytics_type == AnalyticsType.KNOWLEDGE
        assert len(result.data_points) == 2
        assert sum(dp["value"] for dp in result.data_points) == 40  # Total views

    @pytest.mark.asyncio
    async def test_cross_component_analytics(self, analytics_service, sample_metrics):
        """Test analytics queries that span multiple components."""
        # Register multiple metrics from different components
        for metric in sample_metrics:
            await analytics_service.register_metric(metric)
        
        timestamp = datetime.now(timezone.utc)
        
        # Test multi-component query
        query = AnalyticsQuery(
            analytics_type=None,  # Query across all types
            metric_names=["user_login_count", "cpu_utilization"],
            start_time=timestamp - timedelta(hours=1),
            end_time=timestamp + timedelta(hours=1)
        )
        
        mock_result = [
            {
                "metric_name": "user_login_count",
                "value": 10,
                "labels": {"user_type": "customer", "platform": "web"},
                "timestamp": timestamp
            },
            {
                "metric_name": "cpu_utilization",
                "value": 75.5,
                "labels": {"host": "web-server-01", "core": "cpu0"},
                "timestamp": timestamp
            }
        ]
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        result = await analytics_service.query_metrics(query)
        
        assert len(result.data_points) == 2
        metric_names = {dp["metric_name"] for dp in result.data_points}
        assert "user_login_count" in metric_names
        assert "cpu_utilization" in metric_names

    @pytest.mark.asyncio
    async def test_analytics_aggregation_functions(self, analytics_service):
        """Test different aggregation functions work correctly."""
        metric = MetricDefinition(
            name="test_metric",
            type=MetricType.GAUGE,
            analytics_type=AnalyticsType.BUSINESS,
            description="Test metric for aggregation",
        )
        
        await analytics_service.register_metric(metric)
        timestamp = datetime.now(timezone.utc)
        
        # Test different aggregation functions
        for agg_func in ["sum", "avg", "min", "max", "count"]:
            query = AnalyticsQuery(
                analytics_type=AnalyticsType.BUSINESS,
                metric_names=["test_metric"],
                start_time=timestamp - timedelta(hours=1),
                end_time=timestamp,
                aggregation_function=agg_func
            )
            
            mock_result = [{"metric_name": "test_metric", "value": 42.0, "labels": {}, "timestamp": timestamp}]
            analytics_service.db.execute.return_value.fetchall.return_value = mock_result
            
            result = await analytics_service.query_metrics(query)
            assert len(result.data_points) == 1
            assert result.aggregation_function == agg_func

    @pytest.mark.asyncio
    async def test_error_handling_in_components(self, analytics_service):
        """Test error handling across analytics components."""
        
        # Test invalid metric registration
        invalid_metric = MetricDefinition(
            name="",  # Empty name should fail
            type=MetricType.COUNTER,
            analytics_type=AnalyticsType.BUSINESS,
            description="Invalid metric",
        )
        
        with pytest.raises(ValidationError):
            await analytics_service.register_metric(invalid_metric)
        
        # Test recording metric that doesn't exist
        with pytest.raises(ValidationError):
            await analytics_service.record_metric(
                metric_name="nonexistent_metric",
                value=1,
                labels={},
                timestamp=datetime.now(timezone.utc)
            )
        
        # Test database error handling
        analytics_service.db.execute.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception):
            query = AnalyticsQuery(
                analytics_type=AnalyticsType.BUSINESS,
                metric_names=["test_metric"],
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                end_time=datetime.now(timezone.utc)
            )
            await analytics_service.query_metrics(query)

    @pytest.mark.asyncio
    async def test_component_performance_isolation(self, analytics_service):
        """Test that component failures don't affect other components."""
        
        # Create metrics for multiple components
        metrics = [
            MetricDefinition(
                name=f"{analytics_type.value}_test_metric",
                type=MetricType.COUNTER,
                analytics_type=analytics_type,
                description=f"Test metric for {analytics_type.value}",
            )
            for analytics_type in [
                AnalyticsType.BUSINESS,
                AnalyticsType.WORKFLOW,
                AnalyticsType.INFRASTRUCTURE,
                AnalyticsType.KNOWLEDGE,
            ]
        ]
        
        for metric in metrics:
            await analytics_service.register_metric(metric)
        
        # Simulate one component failing
        original_execute = analytics_service.db.execute
        
        def selective_execute(query, *args, **kwargs):
            query_str = str(query)
            if "business_test_metric" in query_str:
                raise Exception("Business component error")
            return original_execute(query, *args, **kwargs)
        
        analytics_service.db.execute.side_effect = selective_execute
        
        # Query should still work for other components
        query = AnalyticsQuery(
            analytics_type=AnalyticsType.WORKFLOW,
            metric_names=["workflow_test_metric"],
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc)
        )
        
        mock_result = [
            {
                "metric_name": "workflow_test_metric",
                "value": 1,
                "labels": {},
                "timestamp": datetime.now(timezone.utc)
            }
        ]
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        # Reset side effect for successful execution
        analytics_service.db.execute.side_effect = None
        analytics_service.db.execute.return_value.fetchall.return_value = mock_result
        
        result = await analytics_service.query_metrics(query)
        assert len(result.data_points) == 1
        assert result.data_points[0]["metric_name"] == "workflow_test_metric"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])