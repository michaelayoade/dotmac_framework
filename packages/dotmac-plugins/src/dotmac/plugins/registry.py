"""
Plugin registry for managing plugin lifecycle and organization.

Provides centralized registration, initialization, and management of plugins
with thread-safe operations and comprehensive error handling.
"""

import asyncio
import inspect
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
from typing import Any, Dict, List, Optional, Set, Union, Callable, Awaitable

from .interfaces import IPlugin
from .context import PluginContext
from .types import (
    PluginKind, 
    PluginStatus,
    PluginError,
    PluginNotFoundError, 
    PluginRegistrationError,
    PluginInitError,
    PluginStartError,
    PluginStopError,
    PluginPermissionError,
)
from .observability import PluginObservabilityHooks


class PluginRegistry:
    """
    Central registry for plugin management and lifecycle.
    
    Provides thread-safe registration, discovery, and lifecycle management
    of plugins with comprehensive error handling and observability hooks.
    """
    
    def __init__(
        self, 
        observability_hooks: Optional[PluginObservabilityHooks] = None,
        max_workers: int = 4
    ):
        """
        Initialize plugin registry.
        
        Args:
            observability_hooks: Optional hooks for plugin events
            max_workers: Maximum worker threads for async operations
        """
        self._plugins: Dict[str, IPlugin] = {}
        self._plugins_by_kind: Dict[PluginKind, List[IPlugin]] = {
            kind: [] for kind in PluginKind
        }
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)
        self._hooks = observability_hooks or PluginObservabilityHooks()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._context: Optional[PluginContext] = None
        self._initialization_order: List[str] = []
        
    def register(self, plugin: IPlugin, force: bool = False) -> bool:
        """
        Register a plugin in the registry.
        
        Args:
            plugin: Plugin instance to register
            force: Whether to force registration over existing plugin
            
        Returns:
            True if registration successful
            
        Raises:
            PluginRegistrationError: If registration fails
        """
        if not isinstance(plugin, IPlugin):
            raise PluginRegistrationError(
                f"Plugin must implement IPlugin interface: {type(plugin)}"
            )
        
        plugin_name = plugin.name
        
        with self._lock:
            # Check for duplicate registration
            if plugin_name in self._plugins and not force:
                raise PluginRegistrationError(
                    f"Plugin '{plugin_name}' already registered. Use force=True to override."
                )
            
            try:
                # Validate plugin metadata
                self._validate_plugin(plugin)
                
                # Check permissions if context is available
                if self._context:
                    self._validate_permissions(plugin, self._context)
                
                # Remove old plugin if forcing
                if plugin_name in self._plugins:
                    self._unregister_plugin_unsafe(plugin_name)
                
                # Register plugin
                plugin.status = PluginStatus.REGISTERED
                self._plugins[plugin_name] = plugin
                self._plugins_by_kind[plugin.kind].append(plugin)
                self._initialization_order.append(plugin_name)
                
                self._logger.info(f"Registered plugin: {plugin_name} (kind: {plugin.kind.value})")
                
                # Trigger observability hook
                self._hooks.on_register(plugin)
                
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to register plugin '{plugin_name}': {e}")
                plugin.status = PluginStatus.ERROR
                raise PluginRegistrationError(f"Plugin registration failed: {e}") from e
    
    def unregister(self, plugin_name: str) -> bool:
        """
        Unregister a plugin from the registry.
        
        Args:
            plugin_name: Name of plugin to unregister
            
        Returns:
            True if unregistration successful
        """
        with self._lock:
            return self._unregister_plugin_unsafe(plugin_name)
    
    def _unregister_plugin_unsafe(self, plugin_name: str) -> bool:
        """Unregister plugin without locking (internal use)."""
        if plugin_name not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_name]
        
        try:
            # Stop plugin if running
            if plugin.status in (PluginStatus.RUNNING, PluginStatus.STARTED):
                self._stop_plugin_unsafe(plugin)
            
            # Remove from registry
            del self._plugins[plugin_name]
            self._plugins_by_kind[plugin.kind].remove(plugin)
            
            if plugin_name in self._initialization_order:
                self._initialization_order.remove(plugin_name)
            
            plugin.status = PluginStatus.UNKNOWN
            
            self._logger.info(f"Unregistered plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to unregister plugin '{plugin_name}': {e}")
            return False
    
    def get(self, plugin_name: str) -> Optional[IPlugin]:
        """
        Get plugin by name.
        
        Args:
            plugin_name: Plugin name to retrieve
            
        Returns:
            Plugin instance or None if not found
        """
        with self._lock:
            return self._plugins.get(plugin_name)
    
    def get_required(self, plugin_name: str) -> IPlugin:
        """
        Get plugin by name, raising exception if not found.
        
        Args:
            plugin_name: Plugin name to retrieve
            
        Returns:
            Plugin instance
            
        Raises:
            PluginNotFoundError: If plugin is not registered
        """
        plugin = self.get(plugin_name)
        if plugin is None:
            raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
        return plugin
    
    def list(self, kind: Optional[PluginKind] = None, status: Optional[PluginStatus] = None) -> List[IPlugin]:
        """
        List plugins by kind and/or status.
        
        Args:
            kind: Optional plugin kind filter
            status: Optional plugin status filter
            
        Returns:
            List of matching plugins
        """
        with self._lock:
            if kind is not None:
                plugins = self._plugins_by_kind[kind].copy()
            else:
                plugins = list(self._plugins.values())
            
            if status is not None:
                plugins = [p for p in plugins if p.status == status]
            
            return plugins
    
    def list_names(self, kind: Optional[PluginKind] = None) -> List[str]:
        """
        List plugin names by kind.
        
        Args:
            kind: Optional plugin kind filter
            
        Returns:
            List of plugin names
        """
        plugins = self.list(kind=kind)
        return [p.name for p in plugins]
    
    def has_plugin(self, plugin_name: str) -> bool:
        """
        Check if plugin is registered.
        
        Args:
            plugin_name: Plugin name to check
            
        Returns:
            True if plugin is registered
        """
        with self._lock:
            return plugin_name in self._plugins
    
    def count(self, kind: Optional[PluginKind] = None) -> int:
        """
        Count plugins by kind.
        
        Args:
            kind: Optional plugin kind filter
            
        Returns:
            Number of matching plugins
        """
        return len(self.list(kind=kind))
    
    def load(self, entry_point_group: str = "dotmac.plugins") -> int:
        """
        Load plugins from entry points.
        
        Args:
            entry_point_group: Entry point group to load from
            
        Returns:
            Number of plugins loaded
            
        Raises:
            PluginError: If discovery fails
        """
        from .discovery import discover_plugins
        
        try:
            plugins = discover_plugins(entry_point_group)
            loaded_count = 0
            
            for plugin in plugins:
                try:
                    self.register(plugin)
                    loaded_count += 1
                except PluginRegistrationError as e:
                    self._logger.warning(f"Skipped plugin registration: {e}")
                    self._hooks.on_error(plugin, e)
            
            self._logger.info(f"Loaded {loaded_count} plugins from entry points")
            return loaded_count
            
        except Exception as e:
            self._logger.error(f"Failed to load plugins: {e}")
            raise PluginError(f"Plugin loading failed: {e}") from e
    
    async def init_all(self, context: PluginContext) -> None:
        """
        Initialize all registered plugins.
        
        Args:
            context: Plugin context for initialization
            
        Raises:
            PluginInitError: If initialization fails
        """
        self._context = context
        
        with self._lock:
            plugins_to_init = [
                self._plugins[name] for name in self._initialization_order
                if name in self._plugins and self._plugins[name].status == PluginStatus.REGISTERED
            ]
        
        for plugin in plugins_to_init:
            await self._init_plugin(plugin, context)
    
    async def start_all(self) -> None:
        """
        Start all initialized plugins.
        
        Raises:
            PluginStartError: If startup fails
        """
        with self._lock:
            plugins_to_start = [
                plugin for plugin in self._plugins.values()
                if plugin.status == PluginStatus.INITIALIZED
            ]
        
        for plugin in plugins_to_start:
            await self._start_plugin(plugin)
    
    async def stop_all(self) -> None:
        """
        Stop all running plugins.
        
        Stops plugins in reverse order of initialization.
        """
        with self._lock:
            plugins_to_stop = [
                self._plugins[name] for name in reversed(self._initialization_order)
                if name in self._plugins and self._plugins[name].status in (PluginStatus.RUNNING, PluginStatus.STARTED)
            ]
        
        for plugin in plugins_to_stop:
            await self._stop_plugin(plugin)
    
    async def _init_plugin(self, plugin: IPlugin, context: PluginContext) -> None:
        """Initialize single plugin."""
        try:
            self._logger.debug(f"Initializing plugin: {plugin.name}")
            
            # Validate permissions
            self._validate_permissions(plugin, context)
            
            # Call init method (sync or async)
            result = plugin.init(context)
            if inspect.iscoroutine(result):
                success = await result
            else:
                success = result
            
            if success:
                plugin.status = PluginStatus.INITIALIZED
                self._logger.info(f"Initialized plugin: {plugin.name}")
                self._hooks.on_init(plugin)
            else:
                plugin.status = PluginStatus.ERROR
                raise PluginInitError(f"Plugin '{plugin.name}' init returned False")
                
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            self._logger.error(f"Failed to initialize plugin '{plugin.name}': {e}")
            self._hooks.on_error(plugin, e)
            raise PluginInitError(f"Plugin '{plugin.name}' initialization failed: {e}") from e
    
    async def _start_plugin(self, plugin: IPlugin) -> None:
        """Start single plugin."""
        try:
            self._logger.debug(f"Starting plugin: {plugin.name}")
            
            # Call start method (sync or async)  
            result = plugin.start()
            if inspect.iscoroutine(result):
                success = await result
            else:
                success = result
            
            if success:
                plugin.status = PluginStatus.RUNNING
                self._logger.info(f"Started plugin: {plugin.name}")
                self._hooks.on_start(plugin)
            else:
                plugin.status = PluginStatus.ERROR
                raise PluginStartError(f"Plugin '{plugin.name}' start returned False")
                
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            self._logger.error(f"Failed to start plugin '{plugin.name}': {e}")
            self._hooks.on_error(plugin, e)
            raise PluginStartError(f"Plugin '{plugin.name}' startup failed: {e}") from e
    
    async def _stop_plugin(self, plugin: IPlugin) -> None:
        """Stop single plugin."""
        with self._lock:
            self._stop_plugin_unsafe(plugin)
    
    def _stop_plugin_unsafe(self, plugin: IPlugin) -> None:
        """Stop single plugin without locking."""
        try:
            self._logger.debug(f"Stopping plugin: {plugin.name}")
            
            # Call stop method (sync or async)
            result = plugin.stop()
            if inspect.iscoroutine(result):
                # Run async stop in event loop
                try:
                    loop = asyncio.get_event_loop()
                    success = loop.run_until_complete(result)
                except RuntimeError:
                    # No event loop, run in thread pool
                    import asyncio
                    success = asyncio.run(result)
            else:
                success = result
            
            if success:
                plugin.status = PluginStatus.STOPPED
                self._logger.info(f"Stopped plugin: {plugin.name}")
                self._hooks.on_stop(plugin)
            else:
                plugin.status = PluginStatus.ERROR
                self._logger.warning(f"Plugin '{plugin.name}' stop returned False")
                
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            self._logger.error(f"Failed to stop plugin '{plugin.name}': {e}")
            self._hooks.on_error(plugin, e)
    
    def _validate_plugin(self, plugin: IPlugin) -> None:
        """Validate plugin interface and metadata."""
        # Check required attributes
        required_attrs = ['name', 'version', 'kind', 'metadata']
        for attr in required_attrs:
            if not hasattr(plugin, attr):
                raise PluginRegistrationError(f"Plugin missing required attribute: {attr}")
        
        # Check name format
        if not plugin.name or not isinstance(plugin.name, str):
            raise PluginRegistrationError("Plugin name must be non-empty string")
        
        # Check version format
        if not plugin.version or not isinstance(plugin.version, str):
            raise PluginRegistrationError("Plugin version must be non-empty string")
        
        # Validate metadata
        if hasattr(plugin.metadata, 'validate'):
            errors = plugin.metadata.validate()
            if errors:
                raise PluginRegistrationError(f"Plugin metadata validation failed: {', '.join(errors)}")
    
    def _validate_permissions(self, plugin: IPlugin, context: PluginContext) -> None:
        """Validate plugin permissions against context."""
        required_permissions = plugin.metadata.permissions_required
        
        for permission in required_permissions:
            if not context.has_permission(permission):
                raise PluginPermissionError(
                    f"Plugin '{plugin.name}' requires permission '{permission}' "
                    f"which is not granted in context",
                    plugin.name
                )
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of plugin registry status.
        
        Returns:
            Status summary dictionary
        """
        with self._lock:
            status_counts = {}
            for status in PluginStatus:
                count = sum(1 for p in self._plugins.values() if p.status == status)
                if count > 0:
                    status_counts[status.name] = count
            
            kind_counts = {}
            for kind in PluginKind:
                count = len(self._plugins_by_kind[kind])
                if count > 0:
                    kind_counts[kind.value] = count
            
            return {
                "total_plugins": len(self._plugins),
                "status_counts": status_counts,
                "kind_counts": kind_counts,
                "plugin_names": list(self._plugins.keys()),
            }
    
    def cleanup(self) -> None:
        """Cleanup registry resources."""
        try:
            # Stop all plugins
            with self._lock:
                for plugin in list(self._plugins.values()):
                    if plugin.status in (PluginStatus.RUNNING, PluginStatus.STARTED):
                        self._stop_plugin_unsafe(plugin)
            
            # Shutdown thread pool
            self._executor.shutdown(wait=True)
            
            self._logger.info("Plugin registry cleanup completed")
            
        except Exception as e:
            self._logger.error(f"Error during registry cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
    
    def __len__(self) -> int:
        """Get number of registered plugins."""
        with self._lock:
            return len(self._plugins)
    
    def __contains__(self, plugin_name: str) -> bool:
        """Check if plugin is registered."""
        return self.has_plugin(plugin_name)
    
    def __iter__(self):
        """Iterate over registered plugins."""
        with self._lock:
            return iter(list(self._plugins.values()))
    
    def __repr__(self) -> str:
        """String representation of registry."""
        with self._lock:
            return (
                f"PluginRegistry("
                f"plugins={len(self._plugins)}, "
                f"kinds={list(kind.value for kind in self._plugins_by_kind.keys() if self._plugins_by_kind[kind])}"
                f")"
            )