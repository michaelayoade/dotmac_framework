"""
DotMac Plugins - Universal Plugin System

A comprehensive, reusable plugin system for any application domain.
Supports dynamic loading, dependency management, and domain-specific adapters.

Example Usage:
    ```python
    from dotmac_shared.plugins import PluginRegistry, PluginManager

    # Initialize plugin system
    registry = PluginRegistry()
    manager = PluginManager(registry)

    # Load plugins from configuration
    await manager.load_plugins_from_config("plugins.yaml")

    # Execute plugin methods
    result = await manager.execute_plugin(
        domain="communication",
        plugin_name="email_sender",
        method="send_message",
        recipient="user@example.com",
        message="Hello World"
    )
    ```

Architecture:
    - Core: Base plugin interfaces and lifecycle management
    - Registry: Plugin discovery, loading, and dependency resolution
    - Middleware: Validation, rate limiting, metrics collection
    - Adapters: Domain-specific plugin implementations
    - Loaders: Multiple plugin source support (YAML, Python, remote)
"""

from .core.dependency_resolver import DependencyResolver
from .core.exceptions import (
    PluginConfigError,
    PluginDependencyError,
    PluginError,
    PluginNotFoundError,
    PluginValidationError,
)
from .core.lifecycle_manager import LifecycleManager

# Main plugin manager for easy access
from .core.manager import PluginManager
from .core.plugin_base import BasePlugin, PluginMetadata, PluginStatus
from .core.registry import PluginRegistry
from .loaders.python_loader import PythonPluginLoader
from .loaders.remote_loader import RemotePluginLoader
from .loaders.yaml_loader import YamlPluginLoader
from .middleware.metrics import MetricsMiddleware
from .middleware.rate_limiting import RateLimitingMiddleware
from .middleware.validation import ValidationMiddleware

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"

__all__ = [
    # Core components
    "BasePlugin",
    "PluginMetadata",
    "PluginStatus",
    "PluginRegistry",
    "PluginManager",
    "LifecycleManager",
    "DependencyResolver",
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginDependencyError",
    "PluginValidationError",
    "PluginConfigError",
    # Loaders
    "YamlPluginLoader",
    "PythonPluginLoader",
    "RemotePluginLoader",
    # Middleware
    "ValidationMiddleware",
    "RateLimitingMiddleware",
    "MetricsMiddleware",
]
