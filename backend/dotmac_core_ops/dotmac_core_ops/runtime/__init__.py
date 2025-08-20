"""
Runtime components for the DotMac Core Operations package.

This module provides runtime configuration, application factory, middleware,
and background services for deploying the operations platform.
"""

from .app_factory import create_ops_app
from .config import OpsConfig
from .middleware import setup_middleware
from .background_services import BackgroundServiceManager

__all__ = [
    "create_ops_app",
    "OpsConfig",
    "setup_middleware",
    "BackgroundServiceManager",
]
