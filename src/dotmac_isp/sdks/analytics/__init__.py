from .client import AnalyticsClient
from .dashboards import DashboardsSDK
from .datasets import DatasetsSDK
from .events import EventsSDK
from .metrics import MetricsSDK
from .reports import ReportsSDK
from .segments import SegmentsSDK

"""
Analytics SDK package - Individual SDK exports for composable usage.
"""

# Main client

# Individual SDKs

__all__ = [
    # Main client (for compatibility)
    "AnalyticsClient",
    # Individual SDKs (for composable usage)
    "EventsSDK",
    "MetricsSDK",
    "DatasetsSDK",
    "DashboardsSDK",
    "ReportsSDK",
    "SegmentsSDK",
]
