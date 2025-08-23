"""
DotMac ISP Framework Plugin System

A flexible, extensible plugin architecture for ISP operations.
Supports hot-pluggable modules for network automation, GIS, billing integrations, and more.
"""

from .core.registry import PluginRegistry, plugin_registry
from .core.base import BasePlugin, PluginInfo, PluginStatus
from .core.loader import PluginLoader
from .core.manager import PluginManager
from .core.exceptions import (
    PluginError,
    PluginLoadError,
    PluginConfigError,
    PluginDependencyError,
    PluginSecurityError,
)

__version__ = "1.0.0"

__all__ = [
    "PluginRegistry",
    "plugin_registry",
    "BasePlugin",
    "PluginInfo",
    "PluginStatus",
    "PluginLoader",
    "PluginManager",
    "PluginError",
    "PluginLoadError",
    "PluginConfigError",
    "PluginDependencyError",
    "PluginSecurityError",
]
