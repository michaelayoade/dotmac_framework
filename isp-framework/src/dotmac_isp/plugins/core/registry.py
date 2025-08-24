import logging

logger = logging.getLogger(__name__)

"""Plugin Registry - Central registry for all plugins."""

import asyncio
from typing import Dict, List, Optional, Set, Type
from threading import Lock
from datetime import datetime
import weakref

from .base import BasePlugin, PluginInfo, PluginStatus, PluginCategory, PluginConfig
from .exceptions import PluginRegistrationError, PluginDependencyError


class PluginRegistry:
    """
    Central registry for plugin management.

    Maintains the registry of all available plugins, their metadata,
    dependencies, and current status.
    """

    def __init__(self):
        """Initialize plugin registry."""
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._plugin_instances: Dict[str, BasePlugin] = {}
        self._plugin_configs: Dict[str, PluginConfig] = {}
        self._plugin_dependencies: Dict[str, Set[str]] = {}
        self._plugin_dependents: Dict[str, Set[str]] = {}
        self._load_order: List[str] = []
        self._lock = Lock()

        # Category mappings
        self._category_plugins: Dict[PluginCategory, Set[str]] = {
            category: set() for category in PluginCategory
        }

        # Event listeners
        self._event_listeners: Dict[str, List[weakref.ref]] = {}

    def register_plugin(
        self, plugin_class: Type[BasePlugin], plugin_info: Optional[PluginInfo] = None
    ) -> None:
        """
        Register a plugin class with the registry.

        Args:
            plugin_class: Plugin class to register
            plugin_info: Optional plugin info (will use plugin_class.plugin_info if not provided)
        """
        with self._lock:
            # Get plugin info
            if plugin_info is None:
                # Create temporary instance to get info
                temp_config = PluginConfig()
                temp_api = None  # Will be set properly during loading
                temp_instance = plugin_class(temp_config, temp_api)
                plugin_info = temp_instance.plugin_info

            plugin_id = plugin_info.id

            # Validate plugin ID uniqueness
            if plugin_id in self._plugins:
                raise PluginRegistrationError(
                    f"Plugin with ID '{plugin_id}' is already registered", plugin_id
                )

            # Register plugin
            self._plugins[plugin_id] = plugin_class
            self._plugin_info[plugin_id] = plugin_info

            # Register dependencies
            if plugin_info.dependencies:
                self._plugin_dependencies[plugin_id] = set(plugin_info.dependencies)

                # Update dependent mappings
                for dep_id in plugin_info.dependencies:
                    if dep_id not in self._plugin_dependents:
                        self._plugin_dependents[dep_id] = set()
                    self._plugin_dependents[dep_id].add(plugin_id)
            else:
                self._plugin_dependencies[plugin_id] = set()

            # Add to category mapping
            self._category_plugins[plugin_info.category].add(plugin_id)

            # Recalculate load order
            self._calculate_load_order()

            # Notify listeners
            self._notify_listeners(
                "plugin_registered",
                {"plugin_id": plugin_id, "plugin_info": plugin_info},
            )

    def unregister_plugin(self, plugin_id: str) -> None:
        """
        Unregister a plugin from the registry.

        Args:
            plugin_id: ID of plugin to unregister
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return

            # Check if plugin has dependents
            dependents = self._plugin_dependents.get(plugin_id, set())
            if dependents:
                loaded_dependents = [
                    dep_id for dep_id in dependents if dep_id in self._plugin_instances
                ]
                if loaded_dependents:
                    raise PluginDependencyError(
                        f"Cannot unregister plugin '{plugin_id}' - it has loaded dependents: {loaded_dependents}",
                        plugin_id,
                    )

            # Remove from registry
            plugin_info = self._plugin_info[plugin_id]
            del self._plugins[plugin_id]
            del self._plugin_info[plugin_id]

            # Clean up instance if exists
            if plugin_id in self._plugin_instances:
                del self._plugin_instances[plugin_id]

            # Clean up config if exists
            if plugin_id in self._plugin_configs:
                del self._plugin_configs[plugin_id]

            # Clean up dependencies
            if plugin_id in self._plugin_dependencies:
                deps = self._plugin_dependencies[plugin_id]
                for dep_id in deps:
                    if dep_id in self._plugin_dependents:
                        self._plugin_dependents[dep_id].discard(plugin_id)
                del self._plugin_dependencies[plugin_id]

            # Remove from dependents
            if plugin_id in self._plugin_dependents:
                del self._plugin_dependents[plugin_id]

            # Remove from category mapping
            self._category_plugins[plugin_info.category].discard(plugin_id)

            # Recalculate load order
            self._calculate_load_order()

            # Notify listeners
            self._notify_listeners(
                "plugin_unregistered",
                {"plugin_id": plugin_id, "plugin_info": plugin_info},
            )

    def get_plugin_class(self, plugin_id: str) -> Optional[Type[BasePlugin]]:
        """Get plugin class by ID."""
        return self._plugins.get(plugin_id)

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin info by ID."""
        return self._plugin_info.get(plugin_id)

    def get_plugin_instance(self, plugin_id: str) -> Optional[BasePlugin]:
        """Get plugin instance by ID."""
        return self._plugin_instances.get(plugin_id)

    def set_plugin_instance(self, plugin_id: str, instance: BasePlugin) -> None:
        """Set plugin instance."""
        with self._lock:
            self._plugin_instances[plugin_id] = instance

    def remove_plugin_instance(self, plugin_id: str) -> None:
        """Remove plugin instance."""
        with self._lock:
            if plugin_id in self._plugin_instances:
                del self._plugin_instances[plugin_id]

    def get_plugin_config(self, plugin_id: str) -> Optional[PluginConfig]:
        """Get plugin configuration."""
        return self._plugin_configs.get(plugin_id)

    def set_plugin_config(self, plugin_id: str, config: PluginConfig) -> None:
        """Set plugin configuration."""
        with self._lock:
            self._plugin_configs[plugin_id] = config

    def list_plugins(
        self,
        category: Optional[PluginCategory] = None,
        status: Optional[PluginStatus] = None,
    ) -> List[str]:
        """
        List plugin IDs with optional filtering.

        Args:
            category: Filter by category
            status: Filter by status

        Returns:
            List of plugin IDs matching criteria
        """
        with self._lock:
            plugin_ids = set(self._plugins.keys())

            # Filter by category
            if category:
                plugin_ids &= self._category_plugins[category]

            # Filter by status
            if status:
                filtered_ids = set()
                for plugin_id in plugin_ids:
                    instance = self._plugin_instances.get(plugin_id)
                    if instance and instance.status == status:
                        filtered_ids.add(plugin_id)
                plugin_ids = filtered_ids

            return list(plugin_ids)

    def get_plugins_by_category(
        self, category: PluginCategory
    ) -> Dict[str, PluginInfo]:
        """Get all plugins in a specific category."""
        with self._lock:
            result = {}
            for plugin_id in self._category_plugins[category]:
                if plugin_id in self._plugin_info:
                    result[plugin_id] = self._plugin_info[plugin_id]
            return result

    def get_plugin_dependencies(self, plugin_id: str) -> Set[str]:
        """Get plugin dependencies."""
        return self._plugin_dependencies.get(plugin_id, set()).copy()

    def get_plugin_dependents(self, plugin_id: str) -> Set[str]:
        """Get plugins that depend on this plugin."""
        return self._plugin_dependents.get(plugin_id, set()).copy()

    def get_load_order(self) -> List[str]:
        """Get plugin load order respecting dependencies."""
        with self._lock:
            return self._load_order.copy()

    def validate_dependencies(self, plugin_id: str) -> List[str]:
        """
        Validate plugin dependencies.

        Returns:
            List of missing dependencies
        """
        dependencies = self._plugin_dependencies.get(plugin_id, set())
        missing = []

        for dep_id in dependencies:
            if dep_id not in self._plugins:
                missing.append(dep_id)

        return missing

    def can_load_plugin(self, plugin_id: str) -> bool:
        """Check if plugin can be loaded (all dependencies available)."""
        return len(self.validate_dependencies(plugin_id)) == 0

    def _calculate_load_order(self) -> None:
        """Calculate plugin load order using topological sort."""
        # Kahn's algorithm for topological sorting
        in_degree = {}
        all_plugins = set(self._plugins.keys())

        # Initialize in-degree count
        for plugin_id in all_plugins:
            in_degree[plugin_id] = 0

        # Calculate in-degrees
        for plugin_id, dependencies in self._plugin_dependencies.items():
            for dep_id in dependencies:
                if dep_id in all_plugins:
                    in_degree[plugin_id] += 1

        # Initialize queue with plugins having no dependencies
        queue = [plugin_id for plugin_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Remove plugin with no dependencies
            current = queue.pop(0)
            result.append(current)

            # Update in-degrees of dependents
            dependents = self._plugin_dependents.get(current, set())
            for dependent in dependents:
                if dependent in all_plugins:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check for circular dependencies
        if len(result) != len(all_plugins):
            remaining = [pid for pid in all_plugins if pid not in result]
            # For now, just append remaining plugins (circular dependency handling)
            result.extend(remaining)

        self._load_order = result

    def add_event_listener(self, event_type: str, callback) -> None:
        """Add event listener for registry events."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []

        # Use weak reference to avoid memory leaks
        self._event_listeners[event_type].append(weakref.ref(callback))

    def remove_event_listener(self, event_type: str, callback) -> None:
        """Remove event listener."""
        if event_type in self._event_listeners:
            # Remove matching weak references
            self._event_listeners[event_type] = [
                ref
                for ref in self._event_listeners[event_type]
                if ref() is not None and ref() is not callback
            ]

    def _notify_listeners(self, event_type: str, event_data: dict) -> None:
        """Notify event listeners."""
        if event_type not in self._event_listeners:
            return

        # Clean up dead weak references and call live ones
        live_listeners = []
        for ref in self._event_listeners[event_type]:
            callback = ref()
            if callback is not None:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # Schedule coroutine
                        asyncio.create_task(callback(event_type, event_data))
                    else:
                        callback(event_type, event_data)
                    live_listeners.append(ref)
                except Exception as e:
                    # Log error but continue with other listeners
logger.error(f"Error in plugin registry event listener: {e}")

        self._event_listeners[event_type] = live_listeners

    def get_registry_stats(self) -> Dict[str, any]:
        """Get registry statistics."""
        with self._lock:
            total_plugins = len(self._plugins)
            loaded_plugins = len(self._plugin_instances)

            # Count by category
            category_counts = {}
            for category, plugin_ids in self._category_plugins.items():
                category_counts[category.value] = len(plugin_ids)

            # Count by status
            status_counts = {}
            for instance in self._plugin_instances.values():
                status = instance.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total_registered": total_plugins,
                "total_loaded": loaded_plugins,
                "categories": category_counts,
                "status_distribution": status_counts,
                "load_order_length": len(self._load_order),
            }


# Global plugin registry instance
plugin_registry = PluginRegistry()
