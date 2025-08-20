"""
Runtime package for dotmac_analytics.

Provides runtime utilities and application factories:
- FastAPI application factory
- SDK initialization and configuration
- Middleware and error handling
- Background task management
"""

from .app_factory import create_app, create_production_app
from .config import RuntimeConfig, load_config

__all__ = [
    "create_app",
    "create_production_app",
    "RuntimeConfig",
    "load_config",
]
