"""
Main analytics client SDK for DotMac Analytics.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..core.config import get_config
from ..core.database import get_session
from .dashboards import DashboardsSDK
from .datasets import DatasetsSDK
from .events import EventsSDK
from .metrics import MetricsSDK
from .reports import ReportsSDK
from .segments import SegmentsSDK

logger = logging.getLogger(__name__)


class AnalyticsClient:
    """Main client for DotMac Analytics SDK."""

    def __init__(
        self,
        tenant_id: str,
        db_session: Optional[Session] = None,
        config: Optional[dict] = None
    ):
        """
        Initialize analytics client.

        Args:
            tenant_id: Tenant identifier for multi-tenancy
            db_session: Optional database session (will create one if not provided)
            config: Optional configuration overrides
        """
        self.tenant_id = tenant_id
        self._db_session = db_session
        self._config = config

        # Initialize SDK modules
        self._events = None
        self._metrics = None
        self._datasets = None
        self._dashboards = None
        self._reports = None
        self._segments = None

        logger.info(f"Initialized AnalyticsClient for tenant: {tenant_id}")

    @property
    def db(self) -> Session:
        """Get database session."""
        if self._db_session is None:
            self._db_session = get_session()
        return self._db_session

    @property
    def events(self) -> EventsSDK:
        """Get events SDK."""
        if self._events is None:
            self._events = EventsSDK(self.tenant_id, self.db)
        return self._events

    @property
    def metrics(self) -> MetricsSDK:
        """Get metrics SDK."""
        if self._metrics is None:
            self._metrics = MetricsSDK(self.tenant_id, self.db)
        return self._metrics

    @property
    def datasets(self) -> DatasetsSDK:
        """Get datasets SDK."""
        if self._datasets is None:
            self._datasets = DatasetsSDK(self.tenant_id, self.db)
        return self._datasets

    @property
    def dashboards(self) -> DashboardsSDK:
        """Get dashboards SDK."""
        if self._dashboards is None:
            self._dashboards = DashboardsSDK(self.tenant_id, self.db)
        return self._dashboards

    @property
    def reports(self) -> ReportsSDK:
        """Get reports SDK."""
        if self._reports is None:
            self._reports = ReportsSDK(self.tenant_id, self.db)
        return self._reports

    @property
    def segments(self) -> SegmentsSDK:
        """Get segments SDK."""
        if self._segments is None:
            self._segments = SegmentsSDK(self.tenant_id, self.db)
        return self._segments

    async def health_check(self) -> dict:
        """Check health of analytics service."""
        try:
            from ..core.database import check_connection

            db_healthy = check_connection()
            config = get_config()
            config_errors = config.validate()

            return {
                "status": "healthy" if db_healthy and not config_errors else "unhealthy",
                "tenant_id": self.tenant_id,
                "database": "healthy" if db_healthy else "unhealthy",
                "configuration": "healthy" if not config_errors else "unhealthy",
                "config_errors": config_errors
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def initialize_tenant(self) -> dict:
        """Initialize tenant-specific resources."""
        try:
            # Create default metrics
            default_metrics = [
                {
                    "name": "page_views",
                    "display_name": "Page Views",
                    "metric_type": "counter",
                    "description": "Total page views"
                },
                {
                    "name": "unique_visitors",
                    "display_name": "Unique Visitors",
                    "metric_type": "gauge",
                    "description": "Number of unique visitors"
                },
                {
                    "name": "session_duration",
                    "display_name": "Session Duration",
                    "metric_type": "histogram",
                    "description": "Average session duration in seconds",
                    "unit": "seconds"
                }
            ]

            created_metrics = []
            for metric_config in default_metrics:
                try:
                    from ..models.enums import MetricType
                    metric = await self.metrics.create_metric(
                        name=metric_config["name"],
                        display_name=metric_config["display_name"],
                        metric_type=MetricType(metric_config["metric_type"]),
                        description=metric_config["description"],
                        unit=metric_config.get("unit")
                    )
                    created_metrics.append(metric.name)
                except Exception as e:
                    logger.warning(f"Failed to create default metric {metric_config['name']}: {e}")

            return {
                "status": "initialized",
                "tenant_id": self.tenant_id,
                "created_metrics": created_metrics
            }

        except Exception as e:
            logger.error(f"Tenant initialization failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def close(self):
        """Close database session and cleanup resources."""
        if self._db_session:
            self._db_session.close()
            self._db_session = None

        logger.info(f"Closed AnalyticsClient for tenant: {self.tenant_id}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
