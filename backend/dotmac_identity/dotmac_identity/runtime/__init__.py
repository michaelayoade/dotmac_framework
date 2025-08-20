"""
Runtime package for dotmac_identity.

Provides runtime utilities for identity services:
- Configuration management
- Service initialization
- Security settings
"""

from .config import RuntimeConfig, load_config

__all__ = [
    "RuntimeConfig",
    "load_config",
]
