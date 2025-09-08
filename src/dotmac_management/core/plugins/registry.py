"""
Plugin registry and management system.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Optional

from dotmac_shared.exceptions import ExceptionContext

from .base import (
    BasePlugin,
    PluginError,
    PluginExecutionError,
    PluginStatus,
    PluginType,
    PluginValidationError,
    safe_plugin_call,
)
from .loader import PluginLoader

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for managing plugins."""

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._plugins_by_type: dict[PluginType, list[BasePlugin]] = defaultdict(list)
        self._plugin_dependencies: dict[str, list[str]] = {}
        self._loader = PluginLoader()
        self._lock = asyncio.Lock()

    async def register_plugin(self, plugin: BasePlugin, force: bool = False) -> bool:
        """Register a plugin instance."""
        async with self._lock:
            plugin_name = plugin.meta.name

            try:
                if plugin_name in self._plugins and not force:
                    raise PluginError(f"Plugin {plugin_name} already registered")

                # Validate plugin
                ok, _, err = await safe_plugin_call(self._validate_plugin, plugin)
                if not ok:
                    raise err or PluginValidationError("Plugin validation failed", plugin_name=plugin_name)

                # Initialize plugin
                ok, init_ok, err = await safe_plugin_call(plugin.initialize)
                if not ok or not init_ok:
                    raise PluginExecutionError(f"Failed to initialize plugin: {plugin_name}")

                # Register plugin
                self._plugins[plugin_name] = plugin
                self._plugins_by_type[plugin.meta.plugin_type].append(plugin)
                self._plugin_dependencies[plugin_name] = plugin.meta.dependencies

                plugin.status = PluginStatus.ACTIVE
                logger.info(f"Plugin registered successfully: {plugin_name}")
                return True

            except PluginError as e:
                logger.exception("Failed to register plugin %s", plugin_name)
                plugin.log_error(e, "registration")
                return False

    async def unregister_plugin(self, plugin_name: str) -> bool:
        """Unregister a plugin."""
        async with self._lock:
            try:
                if plugin_name not in self._plugins:
                    logger.warning(f"Plugin not found for unregistration: {plugin_name}")
                    return False

                plugin = self._plugins[plugin_name]

                # Check for dependent plugins
                dependents = self._get_dependent_plugins(plugin_name)
                if dependents:
                    raise PluginError(f"Cannot unregister plugin {plugin_name}: required by {dependents}")

                # Shutdown plugin safely
                ok, _, err = await safe_plugin_call(plugin.shutdown)
                if not ok:
                    plugin.log_error(err or PluginExecutionError("Shutdown failed"), "shutdown")
                    return False

                # Remove from registry
                del self._plugins[plugin_name]
                self._plugins_by_type[plugin.meta.plugin_type].remove(plugin)
                if plugin_name in self._plugin_dependencies:
                    del self._plugin_dependencies[plugin_name]

                logger.info(f"Plugin unregistered: {plugin_name}")
                return True

            except PluginError:
                logger.exception("Failed to unregister plugin %s", plugin_name)
                return False

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get plugin by name."""
        return self._plugins.get(plugin_name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[BasePlugin]:
        """Get all plugins of a specific type."""
        return self._plugins_by_type.get(plugin_type, [])

    def get_active_plugins(self) -> list[BasePlugin]:
        """Get all active plugins."""
        return [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]

    def list_plugins(self) -> dict[str, dict[str, Any]]:
        """List all registered plugins with their status."""
        plugins_info = {}

        for name, plugin in self._plugins.items():
            plugins_info[name] = {
                "name": plugin.meta.name,
                "version": plugin.meta.version,
                "type": plugin.meta.plugin_type.value,
                "status": plugin.status.value,
                "description": plugin.meta.description,
                "author": plugin.meta.author,
                "dependencies": plugin.meta.dependencies,
                "last_error": str(plugin.last_error) if plugin.last_error else None,
            }

        return plugins_info

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """Perform health check on all plugins."""
        health_results = {}

        for name, plugin in self._plugins.items():
            ok, res, err = await safe_plugin_call(plugin.health_check)
            if ok:
                health_results[name] = res
            else:
                health_results[name] = {
                    "status": "error",
                    "error": str(err) if err else "plugin_error",
                }

        return health_results

    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        if plugin_name not in self._plugins:
            logger.error(f"Plugin not found for reload: {plugin_name}")
            return False

        plugin = self._plugins[plugin_name]
        plugin_class = type(plugin)
        config = plugin.config

        # Unregister current plugin
        if not await self.unregister_plugin(plugin_name):
            return False

        # Create new instance and register
        ok, instance, err = await safe_plugin_call(plugin_class, config)
        if not ok or instance is None:
            logger.exception("Failed to instantiate plugin %s during reload", plugin_name)
            return False

        return await self.register_plugin(instance)

    async def _validate_plugin(self, plugin: BasePlugin) -> bool:
        """Validate plugin before registration."""
        # Check plugin metadata
        if not plugin.meta.name:
            raise PluginValidationError("Plugin name is required")

        if not plugin.meta.version:
            raise PluginValidationError("Plugin version is required")

        # Validate dependencies (warn-only)
        for dep in plugin.meta.dependencies:
            if dep not in self._plugins:
                logger.warning(f"Plugin dependency not found: {dep}")

        # Validate configuration safely
        ok, valid, err = await safe_plugin_call(plugin.validate_configuration, plugin.config)
        if not ok:
            raise err or PluginValidationError("Plugin configuration validation failed")
        if not valid:
            raise PluginValidationError("Plugin configuration validation failed")

        return True

    def _get_dependent_plugins(self, plugin_name: str) -> list[str]:
        """Get list of plugins that depend on the given plugin."""
        dependents = []

        for name, dependencies in self._plugin_dependencies.items():
            if plugin_name in dependencies:
                dependents.append(name)

        return dependents

    async def discover_and_load_plugins(self, plugin_directory: str) -> int:
        """Discover and load plugins from directory."""
        try:
            discovered_plugins = await self._loader.discover_plugins(plugin_directory)
            loaded_count = 0

            for plugin_class, config in discovered_plugins:
                ok, plugin_instance, err = await safe_plugin_call(plugin_class, config)
                if not ok or plugin_instance is None:
                    logger.error("Failed to instantiate discovered plugin: %s", err)
                    continue
                if await self.register_plugin(plugin_instance):
                    loaded_count += 1

            logger.info(f"Loaded {loaded_count} plugins from {plugin_directory}")
            return loaded_count

        except ExceptionContext.LIFECYCLE_EXCEPTIONS:
            logger.exception("Failed to discover and load plugins")
            return 0

    async def get_plugin_metrics(self) -> dict[str, Any]:
        """Get metrics about registered plugins."""
        total_plugins = len(self._plugins)
        active_plugins = len([p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE])
        error_plugins = len([p for p in self._plugins.values() if p.status == PluginStatus.ERROR])

        plugins_by_type = {}
        for plugin_type, plugins in self._plugins_by_type.items():
            plugins_by_type[plugin_type.value] = len(plugins)

        return {
            "total_plugins": total_plugins,
            "active_plugins": active_plugins,
            "error_plugins": error_plugins,
            "disabled_plugins": total_plugins - active_plugins - error_plugins,
            "plugins_by_type": plugins_by_type,
            "dependency_graph": self._plugin_dependencies,
        }


# Global plugin registry instance
plugin_registry = PluginRegistry()
