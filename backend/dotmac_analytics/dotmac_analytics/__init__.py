"""
DotMac Analytics - Comprehensive analytics and business intelligence for ISP operations.

This package provides real-time analytics, data processing, and business intelligence
capabilities for Internet Service Providers and telecommunications companies.
"""

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Main client
from .sdks.client import AnalyticsClient
from .sdks.dashboards import DashboardsSDK
from .sdks.datasets import DatasetsSDK

# Individual SDKs for composable usage
from .sdks.events import EventsSDK
from .sdks.metrics import MetricsSDK
from .sdks.reports import ReportsSDK
from .sdks.segments import SegmentsSDK

__all__ = [
    # Main client
    "AnalyticsClient",

    # Individual SDKs
    "EventsSDK",
    "MetricsSDK",
    "DatasetsSDK",
    "DashboardsSDK",
    "ReportsSDK",
    "SegmentsSDK"
]
