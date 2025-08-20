"""
Runtime package for dotmac_networking.

Provides runtime utilities for networking services:
- Configuration management
- Service initialization
- Network settings
"""

from .config import RuntimeConfig, load_config

__all__ = [
    "RuntimeConfig",
    "load_config",
]
