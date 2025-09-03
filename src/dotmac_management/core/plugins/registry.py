"""
Plugin registry and management system.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from .base import BasePlugin, PluginError, PluginStatus, PluginType
from .loader import PluginLoader

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for managing plugins."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugins_by_type: Dict[PluginType, List[BasePlugin]] = defaultdict(list)
        self._plugin_dependencies: Dict[str, List[str]] = {}
        self._loader = PluginLoader()
        self._lock = asyncio.Lock()

    async def register_plugin(self, plugin: BasePlugin, force: bool = False) -> bool:
        """Register a plugin instance."""
        async with self._lock:
            try:
                plugin_name = plugin.meta.name

                # Check if plugin already exists
                if plugin_name in self._plugins and not force:
                    raise PluginError(f"Plugin {plugin_name} already registered")

                # Validate plugin
                if not await self._validate_plugin(plugin):
                    return False

                # Initialize plugin
                if not await plugin.initialize():
                    logger.error(f"Failed to initialize plugin: {plugin_name}")
                    return False

                # Register plugin
                self._plugins[plugin_name] = plugin
                self._plugins_by_type[plugin.meta.plugin_type].append(plugin)
                self._plugin_dependencies[plugin_name] = plugin.meta.dependencies

                plugin.status = PluginStatus.ACTIVE
                logger.info(f"Plugin registered successfully: {plugin_name}")
                return True

            except Exception as e:
                logger.error(f"Failed to register plugin {plugin.meta.name}: {e}")
                plugin.log_error(e, "registration")
                return False

    async def unregister_plugin(self, plugin_name: str) -> bool:
        """Unregister a plugin."""
        async with self._lock:
            try:
                if plugin_name not in self._plugins:
                    logger.warning(
                        f"Plugin not found for unregistration: {plugin_name}"
                    )
                    return False

                plugin = self._plugins[plugin_name]

                # Check for dependent plugins
                dependents = self._get_dependent_plugins(plugin_name)
                if dependents:
                    raise PluginError(
                        f"Cannot unregister plugin {plugin_name}: required by {dependents}"
                    )

                # Shutdown plugin
                await plugin.shutdown()

                # Remove from registry
                del self._plugins[plugin_name]
                self._plugins_by_type[plugin.meta.plugin_type].remove(plugin)
                if plugin_name in self._plugin_dependencies:
                    del self._plugin_dependencies[plugin_name]

                logger.info(f"Plugin unregistered: {plugin_name}")
                return True

            except Exception as e:
                logger.error(f"Failed to unregister plugin {plugin_name}: {e}")
                return False

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get plugin by name."""
        return self._plugins.get(plugin_name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """Get all plugins of a specific type."""
        return self._plugins_by_type.get(plugin_type, [])

    def get_active_plugins(self) -> List[BasePlugin]:
        """Get all active plugins."""
        return [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]

    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
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

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all plugins."""
        health_results = {}

        for name, plugin in self._plugins.items():
            try:
                health_results[name] = await plugin.health_check()
            except Exception as e:
                health_results[name] = {"status": "error", "error": str(e)}

        return health_results

    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        try:
            if plugin_name not in self._plugins:
                logger.error(f"Plugin not found for reload: {plugin_name}")
                return False

            plugin = self._plugins[plugin_name]
            plugin_class = type(plugin)
            config = plugin.config

            # Unregister current plugin
            await self.unregister_plugin(plugin_name)

            # Create new instance and register
            new_plugin = plugin_class(config)
            return await self.register_plugin(new_plugin)

        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False

    async def _validate_plugin(self, plugin: BasePlugin) -> bool:
        """Validate plugin before registration."""
        try:
            # Check plugin metadata
            if not plugin.meta.name:
                raise PluginError("Plugin name is required")

            if not plugin.meta.version:
                raise PluginError("Plugin version is required")

            # Validate dependencies
            for dep in plugin.meta.dependencies:
                if dep not in self._plugins:
                    logger.warning(f"Plugin dependency not found: {dep}")
                    # Don't fail validation, just warn

            # Validate configuration
            if not await plugin.validate_configuration(plugin.config):
                raise PluginError("Plugin configuration validation failed")

            return True

        except Exception as e:
            logger.error(f"Plugin validation failed: {e}")
            return False

    def _get_dependent_plugins(self, plugin_name: str) -> List[str]:
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
                try:
                    plugin_instance = plugin_class(config)
                    if await self.register_plugin(plugin_instance):
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to load discovered plugin: {e}")

            logger.info(f"Loaded {loaded_count} plugins from {plugin_directory}")
            return loaded_count

        except Exception as e:
            logger.error(f"Failed to discover and load plugins: {e}")
            return 0

    async def get_plugin_metrics(self) -> Dict[str, Any]:
        """Get metrics about registered plugins."""
        total_plugins = len(self._plugins)
        active_plugins = len(
            [p for p in self._plugins.values() if p.status == PluginStatus.ACTIVE]
        )
        error_plugins = len(
            [p for p in self._plugins.values() if p.status == PluginStatus.ERROR]
        )

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
