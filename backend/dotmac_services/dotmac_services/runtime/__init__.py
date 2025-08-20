"""
Runtime package for dotmac_services.

Provides runtime utilities for service management:
- Configuration management
- Service initialization
- Event publishing settings
"""

from .config import RuntimeConfig, load_config

__all__ = [
    "RuntimeConfig",
    "load_config",
]
