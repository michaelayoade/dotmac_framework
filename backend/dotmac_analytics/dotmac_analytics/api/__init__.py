"""
Analytics API package.
"""

from .dashboards import dashboards_router
from .datasets import datasets_router
from .events import events_router
from .health import health_router
from .metrics import metrics_router
from .reports import reports_router
from .segments import segments_router

__all__ = [
    "events_router",
    "metrics_router",
    "datasets_router",
    "dashboards_router",
    "reports_router",
    "segments_router",
    "health_router"
]
