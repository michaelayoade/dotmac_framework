"""
Pytest configuration and fixtures for DotMac Analytics tests.
"""

import asyncio
from datetime import datetime
from dotmac_analytics.core.datetime_utils import utc_now, utc_now_iso
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dotmac_analytics.core.config import AnalyticsConfig, set_config
from dotmac_analytics.models import (
    dashboards,
    datasets,
    events,
    metrics,
    reports,
    segments,
)
from dotmac_analytics.sdk.client import AnalyticsClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    config = AnalyticsConfig(
        environment="test",
        debug=True,
        database=AnalyticsConfig.DatabaseConfig(
            url="sqlite:///:memory:",
            echo=False
        ),
        cache=AnalyticsConfig.CacheConfig(
            redis_url="redis://localhost:6379/1",
            default_ttl=60
        ),
        processing=AnalyticsConfig.ProcessingConfig(
            batch_size=100,
            max_workers=2
        ),
        security=AnalyticsConfig.SecurityConfig(
            secret_key="test-secret-key",
            encryption_key="test-encryption-key"
        )
    )
    set_config(config)
    return config


@pytest.fixture(scope="session")
def test_engine(test_config):
    """Create test database engine."""
    engine = create_engine(
        test_config.database.url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=test_config.database.echo
    )

    # Create all tables
    events.Base.metadata.create_all(bind=engine)
    metrics.Base.metadata.create_all(bind=engine)
    datasets.Base.metadata.create_all(bind=engine)
    dashboards.Base.metadata.create_all(bind=engine)
    reports.Base.metadata.create_all(bind=engine)
    segments.Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables
    segments.Base.metadata.drop_all(bind=engine)
    reports.Base.metadata.drop_all(bind=engine)
    dashboards.Base.metadata.drop_all(bind=engine)
    datasets.Base.metadata.drop_all(bind=engine)
    metrics.Base.metadata.drop_all(bind=engine)
    events.Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_tenant_id():
    """Test tenant ID."""
    return "test_tenant"


@pytest.fixture
def analytics_client(db_session, test_tenant_id):
    """Analytics client for testing."""
    client = AnalyticsClient(tenant_id=test_tenant_id, db_session=db_session)
    yield client
    client.close()


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "event_type": "page_view",
        "event_name": "home_page_view",
        "user_id": "user_123",
        "session_id": "session_456",
        "properties": {
            "page_url": "/home",
            "page_title": "Home Page",
            "referrer": "https://google.com"
        },
        "context": {
            "user_agent": "Mozilla/5.0...",
            "ip_address": "192.168.1.1"
        }
    }


@pytest.fixture
def sample_metric_data():
    """Sample metric data for testing."""
    return {
        "name": "page_views",
        "display_name": "Page Views",
        "metric_type": "counter",
        "description": "Total number of page views",
        "unit": "count",
        "dimensions": ["page_url", "user_type"],
        "tags": {"category": "engagement"}
    }


@pytest.fixture
def sample_dashboard_data():
    """Sample dashboard data for testing."""
    return {
        "name": "main_dashboard",
        "display_name": "Main Analytics Dashboard",
        "description": "Primary dashboard for analytics overview",
        "category": "overview",
        "layout": {
            "columns": 12,
            "rows": 8
        }
    }


@pytest.fixture
def sample_widget_data():
    """Sample widget data for testing."""
    return {
        "name": "page_views_chart",
        "title": "Page Views Over Time",
        "widget_type": "line_chart",
        "query_config": {
            "metric": "page_views",
            "aggregation": "sum",
            "granularity": "hour"
        },
        "visualization_config": {
            "chart_type": "line",
            "color_scheme": "blue"
        }
    }


@pytest.fixture
def sample_report_data():
    """Sample report data for testing."""
    return {
        "name": "weekly_analytics",
        "display_name": "Weekly Analytics Report",
        "report_type": "analytics",
        "description": "Weekly summary of analytics data",
        "query_config": {
            "metrics": ["page_views", "unique_visitors"],
            "time_range": "7d"
        }
    }


@pytest.fixture
def sample_segment_data():
    """Sample segment data for testing."""
    return {
        "name": "active_users",
        "display_name": "Active Users",
        "entity_type": "user",
        "description": "Users who have been active in the last 30 days",
        "category": "engagement"
    }


@pytest.fixture
async def populated_analytics_client(analytics_client, sample_event_data, sample_metric_data):
    """Analytics client with sample data."""
    from dotmac_analytics.models.enums import EventType, MetricType

    # Create sample metric
    await analytics_client.metrics.create_metric(
        name=sample_metric_data["name"],
        display_name=sample_metric_data["display_name"],
        metric_type=MetricType(sample_metric_data["metric_type"]),
        description=sample_metric_data["description"],
        unit=sample_metric_data["unit"],
        dimensions=sample_metric_data["dimensions"],
        tags=sample_metric_data["tags"]
    )

    # Track sample events
    for i in range(5):
        await analytics_client.events.track(
            event_type=EventType(sample_event_data["event_type"]),
            event_name=f"{sample_event_data['event_name']}_{i}",
            user_id=f"{sample_event_data['user_id']}_{i}",
            session_id=f"{sample_event_data['session_id']}_{i}",
            properties=sample_event_data["properties"],
            context=sample_event_data["context"]
        )

    return analytics_client


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self):
        self.data = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        self.data[key] = value
        return True

    async def delete(self, key: str):
        return self.data.pop(key, None) is not None

    async def exists(self, key: str):
        return key in self.data


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    return MockRedisClient()


@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    class MockEmailService:
        def __init__(self):
            self.sent_emails = []

        async def send_email(self, to: str, subject: str, body: str):
            self.sent_emails.append({
                "to": to,
                "subject": subject,
                "body": body,
                "sent_at": utc_now()
            })
            return True

    return MockEmailService()
