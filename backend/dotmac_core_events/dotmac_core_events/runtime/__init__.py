"""
Runtime package for dotmac_core_events.

Provides runtime utilities and application factories:
- FastAPI application factory
- SDK initialization and configuration
- Middleware and error handling
- Background task management
"""

from .app_factory import create_app, create_production_app
from .background_tasks import BackgroundTaskManager, start_background_tasks
from .config import RuntimeConfig, load_config
from .middleware import setup_middleware

__all__ = [
    "create_app",
    "create_production_app",
    "BackgroundTaskManager",
    "start_background_tasks",
    "setup_middleware",
    "RuntimeConfig",
    "load_config",
]
