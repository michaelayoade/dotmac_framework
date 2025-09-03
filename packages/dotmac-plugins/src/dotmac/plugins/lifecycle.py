"""
Plugin lifecycle management and orchestration.

Provides high-level lifecycle management for plugins with dependency resolution,
batch operations, and comprehensive error handling across plugin kinds.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Union

from .interfaces import IPlugin
from .registry import PluginRegistry
from .context import PluginContext
from .observability import PluginObservabilityHooks
from .types import (
    PluginKind, 
    PluginStatus,
    PluginError,
    PluginInitError,
    PluginStartError,
    PluginStopError,
)


class PluginLifecycleManager:
    """
    High-level plugin lifecycle orchestration.
    
    Provides a higher-level interface over PluginRegistry with enhanced
    lifecycle management, dependency resolution, and batch operations.
    """
    
    def __init__(
        self, 
        registry: Optional[PluginRegistry] = None,
        observability_hooks: Optional[PluginObservabilityHooks] = None
    ):
        """
        Initialize lifecycle manager.
        
        Args:
            registry: Optional existing registry (creates new if None)
            observability_hooks: Optional observability hooks
        """
        self._hooks = observability_hooks or PluginObservabilityHooks()
        self._registry = registry or PluginRegistry(observability_hooks=self._hooks)
        self._logger = logging.getLogger(__name__)
        self._startup_order: List[PluginKind] = [
            PluginKind.OBSERVER,    # Start observers first
            PluginKind.DNS,         # Then DNS providers
            PluginKind.DEPLOYMENT,  # Then deployment providers
            PluginKind.EXPORT,      # Then export plugins
            PluginKind.ROUTER,      # Then router plugins
            PluginKind.CUSTOM,      # Finally custom plugins
        ]
        self._shutdown_order = list(reversed(self._startup_order))
    
    @property
    def registry(self) -> PluginRegistry:
        """Access to underlying registry."""
        return self._registry
    
    def register(self, plugin: IPlugin, force: bool = False) -> bool:
        """
        Register plugin with lifecycle management.
        
        Args:
            plugin: Plugin to register
            force: Force registration over existing plugin
            
        Returns:
            True if registration successful
        """
        return self._registry.register(plugin, force=force)
    
    def load_plugins(self, entry_point_group: str = "dotmac.plugins") -> int:
        """
        Load plugins from entry points.
        
        Args:
            entry_point_group: Entry point group to load from
            
        Returns:
            Number of plugins loaded
        """
        return self._registry.load(entry_point_group)
    
    async def initialize_all(self, context: PluginContext) -> Dict[str, Any]:
        """
        Initialize all plugins with enhanced error handling.
        
        Args:
            context: Plugin context for initialization
            
        Returns:
            Summary of initialization results
        """
        self._logger.info("Starting plugin initialization")
        
        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
            "total": self._registry.count()
        }
        
        # Initialize plugins by kind in startup order
        for kind in self._startup_order:
            plugins = self._registry.list(kind=kind, status=PluginStatus.REGISTERED)
            
            if not plugins:
                continue
            
            self._logger.info(f"Initializing {len(plugins)} {kind.value} plugins")
            
            for plugin in plugins:
                try:
                    with self._hooks.time_operation("init", plugin):
                        await self._registry._init_plugin(plugin, context)
                    results["successful"].append(plugin.name)
                    
                except PluginInitError as e:
                    self._logger.error(f"Failed to initialize {plugin.name}: {e}")
                    results["failed"].append({
                        "name": plugin.name,
                        "error": str(e),
                        "kind": plugin.kind.value
                    })
                    
                except Exception as e:
                    self._logger.error(f"Unexpected error initializing {plugin.name}: {e}")
                    results["failed"].append({
                        "name": plugin.name, 
                        "error": f"Unexpected error: {e}",
                        "kind": plugin.kind.value
                    })
        
        self._logger.info(
            f"Plugin initialization complete: "
            f"{len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )
        
        return results
    
    async def start_all(self, fail_fast: bool = False) -> Dict[str, Any]:
        """
        Start all initialized plugins.
        
        Args:
            fail_fast: Whether to stop on first failure
            
        Returns:
            Summary of startup results
        """
        self._logger.info("Starting plugin startup")
        
        results = {
            "successful": [],
            "failed": [],
            "skipped": []
        }
        
        # Start plugins by kind in startup order
        for kind in self._startup_order:
            plugins = self._registry.list(kind=kind, status=PluginStatus.INITIALIZED)
            
            if not plugins:
                continue
            
            self._logger.info(f"Starting {len(plugins)} {kind.value} plugins")
            
            for plugin in plugins:
                try:
                    with self._hooks.time_operation("start", plugin):
                        await self._registry._start_plugin(plugin)
                    results["successful"].append(plugin.name)
                    
                except PluginStartError as e:
                    self._logger.error(f"Failed to start {plugin.name}: {e}")
                    results["failed"].append({
                        "name": plugin.name,
                        "error": str(e), 
                        "kind": plugin.kind.value
                    })
                    
                    if fail_fast:
                        raise
                        
                except Exception as e:
                    self._logger.error(f"Unexpected error starting {plugin.name}: {e}")
                    results["failed"].append({
                        "name": plugin.name,
                        "error": f"Unexpected error: {e}",
                        "kind": plugin.kind.value
                    })
                    
                    if fail_fast:
                        raise
        
        self._logger.info(
            f"Plugin startup complete: "
            f"{len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )
        
        return results
    
    async def stop_all(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Stop all running plugins.
        
        Args:
            timeout: Optional timeout for stop operations
            
        Returns:
            Summary of shutdown results
        """
        self._logger.info("Starting plugin shutdown")
        
        results = {
            "successful": [],
            "failed": [],
            "skipped": []
        }
        
        # Stop plugins by kind in shutdown order (reverse of startup)
        for kind in self._shutdown_order:
            plugins = self._registry.list(
                kind=kind, 
                status=PluginStatus.RUNNING
            )
            
            if not plugins:
                continue
            
            self._logger.info(f"Stopping {len(plugins)} {kind.value} plugins")
            
            # Create stop tasks with timeout
            stop_tasks = []
            for plugin in plugins:
                task = asyncio.create_task(
                    self._stop_plugin_with_timeout(plugin, timeout)
                )
                stop_tasks.append((plugin, task))
            
            # Wait for all stops to complete
            for plugin, task in stop_tasks:
                try:
                    success = await task
                    if success:
                        results["successful"].append(plugin.name)
                    else:
                        results["failed"].append({
                            "name": plugin.name,
                            "error": "Stop returned False",
                            "kind": plugin.kind.value
                        })
                        
                except Exception as e:
                    self._logger.error(f"Error stopping {plugin.name}: {e}")
                    results["failed"].append({
                        "name": plugin.name,
                        "error": str(e),
                        "kind": plugin.kind.value
                    })
        
        self._logger.info(
            f"Plugin shutdown complete: "
            f"{len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )
        
        return results
    
    async def _stop_plugin_with_timeout(
        self, 
        plugin: IPlugin, 
        timeout: Optional[float]
    ) -> bool:
        """Stop plugin with optional timeout."""
        try:
            if timeout:
                await asyncio.wait_for(
                    self._registry._stop_plugin(plugin),
                    timeout=timeout
                )
            else:
                await self._registry._stop_plugin(plugin)
            return True
            
        except asyncio.TimeoutError:
            self._logger.error(f"Timeout stopping plugin {plugin.name} (timeout={timeout}s)")
            plugin.status = PluginStatus.ERROR
            return False
        except Exception as e:
            self._logger.error(f"Error stopping plugin {plugin.name}: {e}")
            plugin.status = PluginStatus.ERROR
            return False
    
    async def restart_plugin(self, plugin_name: str, context: PluginContext) -> bool:
        """
        Restart specific plugin.
        
        Args:
            plugin_name: Name of plugin to restart
            context: Plugin context
            
        Returns:
            True if restart successful
        """
        plugin = self._registry.get(plugin_name)
        if not plugin:
            self._logger.error(f"Plugin {plugin_name} not found for restart")
            return False
        
        try:
            self._logger.info(f"Restarting plugin: {plugin_name}")
            
            # Stop if running
            if plugin.status == PluginStatus.RUNNING:
                await self._registry._stop_plugin(plugin)
            
            # Reinitialize
            await self._registry._init_plugin(plugin, context)
            
            # Start
            await self._registry._start_plugin(plugin)
            
            self._logger.info(f"Successfully restarted plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to restart plugin {plugin_name}: {e}")
            self._hooks.on_error(plugin, e, {"operation": "restart"})
            return False
    
    async def restart_all(self, context: PluginContext) -> Dict[str, Any]:
        """
        Restart all plugins.
        
        Args:
            context: Plugin context
            
        Returns:
            Summary of restart results
        """
        self._logger.info("Starting full plugin restart")
        
        # Stop all first
        stop_results = await self.stop_all()
        
        # Then initialize and start all
        init_results = await self.initialize_all(context)
        start_results = await self.start_all()
        
        return {
            "stop_results": stop_results,
            "init_results": init_results,
            "start_results": start_results,
            "overall_success": (
                len(init_results["failed"]) == 0 and 
                len(start_results["failed"]) == 0
            )
        }
    
    def get_plugin_health(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get health status of specific plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin health information or None if not found
        """
        plugin = self._registry.get(plugin_name)
        if not plugin:
            return None
        
        base_health = plugin.get_health_status() if hasattr(plugin, 'get_health_status') else {}
        
        return {
            "name": plugin.name,
            "version": plugin.version,
            "kind": plugin.kind.value,
            "status": plugin.status.name,
            "healthy": plugin.status == PluginStatus.RUNNING,
            **base_health
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall plugin system health.
        
        Returns:
            System health summary
        """
        all_plugins = self._registry.list()
        
        status_counts = {}
        for status in PluginStatus:
            count = sum(1 for p in all_plugins if p.status == status)
            if count > 0:
                status_counts[status.name] = count
        
        kind_counts = {}
        for kind in PluginKind:
            count = len(self._registry.list(kind=kind))
            if count > 0:
                kind_counts[kind.value] = count
        
        running_plugins = self._registry.list(status=PluginStatus.RUNNING)
        error_plugins = self._registry.list(status=PluginStatus.ERROR)
        
        return {
            "total_plugins": len(all_plugins),
            "running_plugins": len(running_plugins),
            "error_plugins": len(error_plugins),
            "healthy": len(error_plugins) == 0,
            "status_counts": status_counts,
            "kind_counts": kind_counts,
            "running_plugin_names": [p.name for p in running_plugins],
            "error_plugin_names": [p.name for p in error_plugins],
        }
    
    def get_plugins_by_capability(self, capability: str) -> List[IPlugin]:
        """
        Get plugins that have specific capability.
        
        Args:
            capability: Capability name to search for
            
        Returns:
            List of plugins with capability
        """
        matching_plugins = []
        
        for plugin in self._registry:
            if hasattr(plugin.metadata, 'has_capability') and plugin.metadata.has_capability(capability):
                matching_plugins.append(plugin)
        
        return matching_plugins
    
    async def graceful_shutdown(self, timeout: float = 30.0) -> None:
        """
        Perform graceful shutdown of all plugins.
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        self._logger.info(f"Starting graceful plugin shutdown (timeout: {timeout}s)")
        
        try:
            await self.stop_all(timeout=timeout)
        except Exception as e:
            self._logger.error(f"Error during graceful shutdown: {e}")
        finally:
            self._registry.cleanup()
            self._logger.info("Plugin system shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Run graceful shutdown synchronously
        try:
            asyncio.run(self.graceful_shutdown())
        except RuntimeError:
            # Event loop already running, cleanup registry directly
            self._registry.cleanup()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.graceful_shutdown()
    
    def __repr__(self) -> str:
        """String representation."""
        health = self.get_system_health()
        return (
            f"PluginLifecycleManager("
            f"total={health['total_plugins']}, "
            f"running={health['running_plugins']}, "
            f"errors={health['error_plugins']}"
            f")"
        )