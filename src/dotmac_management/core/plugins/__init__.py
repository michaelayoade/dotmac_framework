"""
Plugin system for DotMac Management Platform.
"""

from .base import BasePlugin, PluginError, PluginMeta
from .hooks import PluginHooks, hook_manager
from .interfaces import (
    BillingCalculatorPlugin,
    DeploymentProviderPlugin,
    MonitoringProviderPlugin,
    NotificationChannelPlugin,
    PaymentProviderPlugin,
)
from .loader import PluginLoader
from .registry import PluginRegistry, plugin_registry

__all__ = [
    "BasePlugin",
    "PluginMeta",
    "PluginError",
    "PluginRegistry",
    "plugin_registry",
    "PluginHooks",
    "hook_manager",
    "PluginLoader",
    "MonitoringProviderPlugin",
    "DeploymentProviderPlugin",
    "NotificationChannelPlugin",
    "PaymentProviderPlugin",
    "BillingCalculatorPlugin",
]
