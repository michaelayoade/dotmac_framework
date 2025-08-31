"""Monitoring module for system health, metrics and alerts."""

from . import models, schemas

try:
    from .router import monitoring_router as router

    __all__ = ["router", "models", "schemas"]
except ImportError:
    # Router will be available once shared dependencies are resolved
    __all__ = ["models", "schemas"]