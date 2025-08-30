"""Analytics module for metrics, reports, dashboards and alerting."""

from . import models, schemas

try:
    from .router import router

    __all__ = ["router", "models", "schemas"]
except ImportError:
    # Router will be available once shared dependencies are resolved
    __all__ = ["models", "schemas"]
