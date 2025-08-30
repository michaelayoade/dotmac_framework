"""
Middleware plugin system for extensible middleware functionality.

This module provides a plugin architecture for middleware components,
allowing third-party and custom middleware to be integrated seamlessly.
"""

import importlib
import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class MiddlewarePhase(Enum):
    """Middleware execution phases."""

    PRE_SECURITY = "pre_security"
    SECURITY = "security"
    POST_SECURITY = "post_security"

    PRE_AUTH = "pre_auth"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    POST_AUTH = "post_auth"

    PRE_TENANT = "pre_tenant"
    TENANT_CONTEXT = "tenant_context"
    POST_TENANT = "post_tenant"

    PRE_PROCESSING = "pre_processing"
    PROCESSING = "processing"
    POST_PROCESSING = "post_processing"

    CUSTOM = "custom"


@dataclass
class PluginMetadata:
    """Metadata for middleware plugins."""

    name: str
    version: str
    description: str
    author: str

    # Plugin requirements
    dependencies: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    minimum_framework_version: str = "1.0.0"

    # Execution configuration
    phase: MiddlewarePhase = MiddlewarePhase.CUSTOM
    priority: int = 100  # Lower numbers execute first
    enabled: bool = True

    # Plugin capabilities
    supports_async: bool = True
    thread_safe: bool = True

    # Configuration schema
    config_schema: dict[str, Any] | None = None


class MiddlewarePlugin(ABC):
    """
    Base class for middleware plugins.

    All middleware plugins must inherit from this class and implement
    the required methods.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.metadata = self.get_metadata()
        self._initialized = False

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request."""
        pass

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self._initialized = True
        logger.info("Plugin initialized", plugin=self.metadata.name)

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        logger.info("Plugin cleaned up", plugin=self.metadata.name)

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        if not self.metadata.config_schema:
            return True

        # Basic validation - could use jsonschema for more complex validation
        required_fields = self.metadata.config_schema.get("required", [])
        for required_field in required_fields:
            if required_field not in config:
                logger.error(
                    "Missing required config field",
                    plugin=self.metadata.name,
                    field=required_field,
                )
                return False

        return True

    @property
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized


class PluginWrapper(BaseHTTPMiddleware):
    """Wrapper that adapts MiddlewarePlugin to FastAPI middleware."""

    def __init__(self, app, plugin: MiddlewarePlugin):
        super().__init__(app)
        self.plugin = plugin

        if not plugin.is_initialized:
            plugin.initialize()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Delegate to plugin."""
        return await self.plugin.process_request(request, call_next)


class PluginRegistry:
    """Registry for managing middleware plugins."""

    def __init__(self):
        self._plugins: dict[str, MiddlewarePlugin] = {}
        self._plugin_metadata: dict[str, PluginMetadata] = {}
        self._enabled_plugins: set[str] = set()
        self._plugin_order: list[str] = []

    def register_plugin(self, plugin: MiddlewarePlugin) -> None:
        """Register a middleware plugin."""
        metadata = plugin.get_metadata()

        if metadata.name in self._plugins:
            raise ValueError(f"Plugin '{metadata.name}' already registered")

        # Validate configuration
        if not plugin.validate_config(plugin.config):
            raise ValueError(f"Invalid configuration for plugin '{metadata.name}'")

        self._plugins[metadata.name] = plugin
        self._plugin_metadata[metadata.name] = metadata

        if metadata.enabled:
            self._enabled_plugins.add(metadata.name)

        logger.info(
            "Plugin registered",
            plugin=metadata.name,
            version=metadata.version,
            phase=metadata.phase.value,
        )

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a middleware plugin."""
        if plugin_name not in self._plugins:
            logger.warning(
                "Attempting to unregister unknown plugin", plugin=plugin_name
            )
            return

        plugin = self._plugins[plugin_name]
        plugin.cleanup()

        del self._plugins[plugin_name]
        del self._plugin_metadata[plugin_name]
        self._enabled_plugins.discard(plugin_name)

        if plugin_name in self._plugin_order:
            self._plugin_order.remove(plugin_name)

        logger.info("Plugin unregistered", plugin=plugin_name)

    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a registered plugin."""
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not registered")

        self._enabled_plugins.add(plugin_name)
        self._plugin_metadata[plugin_name].enabled = True

        logger.info("Plugin enabled", plugin=plugin_name)

    def disable_plugin(self, plugin_name: str) -> None:
        """Disable a registered plugin."""
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not registered")

        self._enabled_plugins.discard(plugin_name)
        self._plugin_metadata[plugin_name].enabled = False

        logger.info("Plugin disabled", plugin=plugin_name)

    def get_plugin(self, plugin_name: str) -> MiddlewarePlugin | None:
        """Get a registered plugin."""
        return self._plugins.get(plugin_name)

    def get_enabled_plugins(self) -> list[MiddlewarePlugin]:
        """Get all enabled plugins in execution order."""
        self._update_plugin_order()

        enabled_plugins = []
        for plugin_name in self._plugin_order:
            if plugin_name in self._enabled_plugins:
                enabled_plugins.append(self._plugins[plugin_name])

        return enabled_plugins

    def get_plugins_by_phase(self, phase: MiddlewarePhase) -> list[MiddlewarePlugin]:
        """Get enabled plugins for a specific phase."""
        plugins = []

        for plugin_name in self._enabled_plugins:
            metadata = self._plugin_metadata[plugin_name]
            if metadata.phase == phase:
                plugins.append(self._plugins[plugin_name])

        # Sort by priority
        plugins.sort(key=lambda p: p.metadata.priority)
        return plugins

    def _update_plugin_order(self) -> None:
        """Update plugin execution order based on phases and priorities."""
        phase_order = [
            MiddlewarePhase.PRE_SECURITY,
            MiddlewarePhase.SECURITY,
            MiddlewarePhase.POST_SECURITY,
            MiddlewarePhase.PRE_AUTH,
            MiddlewarePhase.AUTHENTICATION,
            MiddlewarePhase.AUTHORIZATION,
            MiddlewarePhase.POST_AUTH,
            MiddlewarePhase.PRE_TENANT,
            MiddlewarePhase.TENANT_CONTEXT,
            MiddlewarePhase.POST_TENANT,
            MiddlewarePhase.PRE_PROCESSING,
            MiddlewarePhase.PROCESSING,
            MiddlewarePhase.POST_PROCESSING,
            MiddlewarePhase.CUSTOM,
        ]

        ordered_plugins = []

        for phase in phase_order:
            phase_plugins = self.get_plugins_by_phase(phase)
            ordered_plugins.extend([p.metadata.name for p in phase_plugins])

        self._plugin_order = ordered_plugins

    def validate_dependencies(self) -> list[str]:
        """Validate plugin dependencies and return any conflicts."""
        conflicts = []

        for plugin_name in self._enabled_plugins:
            metadata = self._plugin_metadata[plugin_name]

            # Check dependencies
            for dep in metadata.dependencies:
                if dep not in self._enabled_plugins:
                    conflicts.append(
                        f"Plugin '{plugin_name}' requires '{dep}' which is not enabled"
                    )

            # Check conflicts
            for conflict in metadata.conflicts:
                if conflict in self._enabled_plugins:
                    conflicts.append(
                        f"Plugin '{plugin_name}' conflicts with '{conflict}'"
                    )

        return conflicts

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_plugins": len(self._plugins),
            "enabled_plugins": len(self._enabled_plugins),
            "disabled_plugins": len(self._plugins) - len(self._enabled_plugins),
            "plugins_by_phase": {
                phase.value: len(self.get_plugins_by_phase(phase))
                for phase in MiddlewarePhase
            },
        }


class PluginManager:
    """
    Manager for loading and orchestrating middleware plugins.

    Handles plugin discovery, loading, dependency resolution, and lifecycle.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.registry = PluginRegistry()
        self._plugin_directories: list[Path] = []
        self._loaded = False

    def add_plugin_directory(self, directory: str | Path) -> None:
        """Add a directory to search for plugins."""
        path = Path(directory)
        if not path.exists():
            logger.warning("Plugin directory does not exist", directory=str(path))
            return

        self._plugin_directories.append(path)
        logger.info("Added plugin directory", directory=str(path))

    def discover_plugins(self) -> list[str]:
        """Discover available plugins in configured directories."""
        discovered = []

        for directory in self._plugin_directories:
            if not directory.is_dir():
                continue

            # Look for Python files
            for plugin_file in directory.glob("*.py"):
                if plugin_file.name.startswith("__"):
                    continue

                plugin_module = plugin_file.stem
                discovered.append(plugin_module)

                logger.debug(
                    "Discovered plugin module",
                    module=plugin_module,
                    file=str(plugin_file),
                )

        return discovered

    def load_plugin(self, plugin_module: str, plugin_class: str | None = None) -> None:
        """Load a plugin from a module."""
        try:
            # Import the module
            module = importlib.import_module(plugin_module)

            # Find plugin class
            plugin_classes = []
            for _name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, MiddlewarePlugin)
                    and obj != MiddlewarePlugin
                ):
                    plugin_classes.append(obj)

            if not plugin_classes:
                logger.error("No plugin classes found in module", module=plugin_module)
                return

            # Use specified class or first found
            if plugin_class:
                plugin_cls = getattr(module, plugin_class, None)
                if not plugin_cls:
                    logger.error(
                        "Plugin class not found",
                        module=plugin_module,
                        class_name=plugin_class,
                    )
                    return
            else:
                plugin_cls = plugin_classes[0]

            # Get plugin configuration
            plugin_config = self.config.get(plugin_module, {})

            # Instantiate and register plugin
            plugin = plugin_cls(plugin_config)
            self.registry.register_plugin(plugin)

            logger.info(
                "Plugin loaded successfully",
                module=plugin_module,
                class_name=plugin_cls.__name__,
                plugin_name=plugin.metadata.name,
            )

        except Exception as e:
            logger.error(
                "Failed to load plugin",
                module=plugin_module,
                error=str(e),
                exc_info=True,
            )

    def load_all_plugins(self) -> None:
        """Load all discovered plugins."""
        plugins = self.discover_plugins()

        for plugin_module in plugins:
            self.load_plugin(plugin_module)

        # Validate dependencies
        conflicts = self.registry.validate_dependencies()
        if conflicts:
            for conflict in conflicts:
                logger.warning("Plugin dependency conflict", conflict=conflict)

        self._loaded = True
        logger.info("All plugins loaded", stats=self.registry.get_registry_stats())

    def get_middleware_stack(self) -> list[BaseHTTPMiddleware]:
        """Get ordered list of middleware instances for FastAPI."""
        if not self._loaded:
            self.load_all_plugins()

        plugins = self.registry.get_enabled_plugins()
        middlewares = []

        for plugin in plugins:
            wrapper = PluginWrapper(None, plugin)
            middlewares.append(wrapper)

        return middlewares

    def reload_plugins(self) -> None:
        """Reload all plugins."""
        # Cleanup existing plugins
        for plugin_name in list(self.registry._plugins.keys()):
            self.registry.unregister_plugin(plugin_name)

        # Reload
        self._loaded = False
        self.load_all_plugins()

        logger.info("Plugins reloaded")


class MiddlewareRegistry:
    """
    Global registry for middleware components and plugins.

    Provides a unified interface to manage both built-in and plugin middleware.
    """

    def __init__(self):
        self.plugin_manager = PluginManager()
        self._builtin_middlewares: dict[str, type[BaseHTTPMiddleware]] = {}

    def register_builtin_middleware(
        self, name: str, middleware_class: type[BaseHTTPMiddleware]
    ) -> None:
        """Register a built-in middleware component."""
        self._builtin_middlewares[name] = middleware_class
        logger.info("Built-in middleware registered", name=name)

    def get_all_middlewares(self) -> list[BaseHTTPMiddleware]:
        """Get all middleware components (built-in + plugins)."""
        middlewares = []

        # Add built-in middlewares (these would be configured elsewhere)
        # middlewares.extend(self._get_builtin_middleware_instances())

        # Add plugin middlewares
        plugin_middlewares = self.plugin_manager.get_middleware_stack()
        middlewares.extend(plugin_middlewares)

        return middlewares

    def configure_plugins(self, config: dict[str, Any]) -> None:
        """Configure the plugin system."""
        self.plugin_manager.config.update(config)

        # Add plugin directories from config
        directories = config.get("plugin_directories", [])
        for directory in directories:
            self.plugin_manager.add_plugin_directory(directory)

        logger.info("Plugin system configured", directories=len(directories))


# Global registry instance
middleware_registry = MiddlewareRegistry()


# Example plugin implementations


class LoggingPlugin(MiddlewarePlugin):
    """Example logging plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="logging_plugin",
            version="1.0.0",
            description="Enhanced request logging plugin",
            author="DotMac Team",
            phase=MiddlewarePhase.PROCESSING,
            priority=50,
        )

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Log request details."""
        logger.info(
            "Plugin request",
            method=request.method,
            path=request.url.path,
            plugin=self.metadata.name,
        )

        import time

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            "Plugin response",
            status_code=response.status_code,
            duration=duration,
            plugin=self.metadata.name,
        )

        return response


class SecurityPlugin(MiddlewarePlugin):
    """Example security plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security_plugin",
            version="1.0.0",
            description="Additional security checks plugin",
            author="DotMac Team",
            phase=MiddlewarePhase.SECURITY,
            priority=200,
            config_schema={
                "required": ["blocked_ips"],
                "properties": {
                    "blocked_ips": {"type": "array", "items": {"type": "string"}}
                },
            },
        )

    async def process_request(self, request: Request, call_next: Callable) -> Response:
        """Apply additional security checks."""
        blocked_ips = self.config.get("blocked_ips", [])
        client_ip = request.client.host if request.client else "unknown"

        if client_ip in blocked_ips:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        return await call_next(request)
