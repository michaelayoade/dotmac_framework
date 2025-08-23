"""Core Plugin System Components."""

from .base import BasePlugin, PluginInfo, PluginStatus
from .registry import PluginRegistry, plugin_registry
from .loader import PluginLoader
from .manager import PluginManager
# ARCHITECTURE IMPROVEMENT: Explicit imports replace wildcard import
from .exceptions import (
    PluginError, PluginLoadError, PluginConfigError, PluginDependencyError,
    PluginSecurityError, PluginVersionError, PluginRegistrationError,
    PluginLifecycleError, PluginTimeoutError, PluginResourceError, 
    PluginCommunicationError
)

__all__ = [
    "BasePlugin",
    "PluginInfo",
    "PluginStatus",
    "PluginRegistry",
    "plugin_registry",
    "PluginLoader",
    "PluginManager",
]
