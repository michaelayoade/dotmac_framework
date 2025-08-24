"""
Plugin system for DotMac Management Platform.
"""

from .base import BasePlugin, PluginMeta, PluginError
from .registry import PluginRegistry, plugin_registry
from .hooks import PluginHooks, hook_manager
from .loader import PluginLoader
from .interfaces import (
    MonitoringProviderPlugin,
    DeploymentProviderPlugin,
    NotificationChannelPlugin,
    PaymentProviderPlugin,
    BillingCalculatorPlugin
)

__all__ = [
    'BasePlugin',
    'PluginMeta',
    'PluginError',
    'PluginRegistry',
    'plugin_registry',
    'PluginHooks',
    'hook_manager',
    'PluginLoader',
    'MonitoringProviderPlugin',
    'DeploymentProviderPlugin', 
    'NotificationChannelPlugin',
    'PaymentProviderPlugin',
    'BillingCalculatorPlugin'
]