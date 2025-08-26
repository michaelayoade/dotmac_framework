"""Plugin Manager - High-level plugin management and orchestration."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import UUID

from .base import (
    BasePlugin,
    PluginInfo,
    PluginStatus,
    PluginCategory,
    PluginConfig,
    PluginContext,
    PluginAPI,
)
from .registry import PluginRegistry, plugin_registry
from .loader import PluginLoader
from .exceptions import (
    PluginError,
    PluginLoadError,
    PluginDependencyError,
    PluginLifecycleError,
)
from dotmac_isp.core.management_platform_client import (
    get_management_client,
    UsageMetric,
)


class PluginManager:
    """
    High-level plugin manager.

    Provides the main interface for plugin operations including lifecycle management,
    configuration, monitoring, and tenant isolation.
    """

    def __init__(
        self,
        registry: Optional[PluginRegistry] = None,
        framework_services: Dict[str, Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize plugin manager."""
        self.registry = registry or plugin_registry
        self.api = PluginAPI(framework_services or {})
        self.logger = logger or logging.getLogger(__name__)

        # Plugin loader
        self.loader = PluginLoader(self.registry, self.api, self.logger)

        # Plugin configurations per tenant
        self.tenant_configs: Dict[UUID, Dict[str, PluginConfig]] = {}

        # Active contexts
        self.active_contexts: Dict[str, PluginContext] = {}

        # Plugin metrics and monitoring
        self.plugin_metrics: Dict[str, Dict[str, Any]] = {}
        self.last_health_check: Dict[str, datetime] = {}

        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()

        # Manager state
        self.is_started = False
        self.shutdown_event = asyncio.Event()

        # License validation cache
        self.license_cache: Dict[str, Dict[str, Any]] = {}
        self.license_cache_ttl = 300  # 5 minutes

        # Usage metrics buffer
        self.usage_metrics_buffer: List[UsageMetric] = []
        self.usage_metrics_batch_size = 10

    async def start(self) -> None:
        """Start the plugin manager."""
        if self.is_started:
            return

        self.logger.info("Starting Plugin Manager...")

        # Start background tasks
        await self._start_background_tasks()

        self.is_started = True
        self.logger.info("Plugin Manager started successfully")

    async def stop(self) -> None:
        """Stop the plugin manager."""
        if not self.is_started:
            return

        self.logger.info("Stopping Plugin Manager...")

        # Signal shutdown
        self.shutdown_event.set()

        # Stop all active plugins
        await self._stop_all_plugins()

        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        self.background_tasks.clear()
        self.is_started = False

        self.logger.info("Plugin Manager stopped")

    async def load_plugins_from_directory(
        self, directory: str, tenant_id: Optional[UUID] = None
    ) -> List[str]:
        """
        Load plugins from directory.

        Args:
            directory: Directory containing plugins
            tenant_id: Tenant ID for tenant-specific configurations

        Returns:
            List of loaded plugin IDs
        """
        try:
            # Get tenant-specific configurations
            config_map = {}
            if tenant_id and tenant_id in self.tenant_configs:
                config_map = self.tenant_configs[tenant_id]

            # Load plugins
            plugin_ids = await self.loader.load_plugins_from_directory(
                directory, config_map
            )

            self.logger.info(f"Loaded {len(plugin_ids)} plugins from {directory}")
            return plugin_ids

        except Exception as e:
            self.logger.error(f"Error loading plugins from directory {directory}: {e}")
            raise

    async def install_plugin(
        self,
        plugin_source: str,
        config: Optional[PluginConfig] = None,
        tenant_id: Optional[UUID] = None,
    ) -> str:
        """
        Install and initialize a plugin.

        Args:
            plugin_source: Plugin source (file path or module name)
            config: Plugin configuration
            tenant_id: Tenant ID for tenant-specific installation

        Returns:
            Plugin ID
        """
        try:
            # Determine source type and load
            if plugin_source.endswith(".py"):
                plugin_id = await self.loader.load_plugin_from_file(
                    plugin_source, config
                )
            else:
                plugin_id = await self.loader.load_plugin_from_module(
                    plugin_source, config
                )

            if not plugin_id:
                raise PluginLoadError(f"Failed to load plugin from {plugin_source}")

            # Store tenant-specific configuration
            if tenant_id and config:
                if tenant_id not in self.tenant_configs:
                    self.tenant_configs[tenant_id] = {}
                self.tenant_configs[tenant_id][plugin_id] = config

            # Initialize plugin
            await self.loader.initialize_plugin(plugin_id)

            self.logger.info(f"Successfully installed plugin: {plugin_id}")
            return plugin_id

        except Exception as e:
            self.logger.error(f"Error installing plugin {plugin_source}: {e}")
            raise

    async def uninstall_plugin(
        self, plugin_id: str, tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Uninstall a plugin.

        Args:
            plugin_id: Plugin ID to uninstall
            tenant_id: Tenant ID for tenant-specific uninstall
        """
        try:
            # Check if plugin has dependents
            dependents = self.registry.get_plugin_dependents(plugin_id)
            active_dependents = []

            for dependent_id in dependents:
                instance = self.registry.get_plugin_instance(dependent_id)
                if instance and instance.status == PluginStatus.ACTIVE:
                    active_dependents.append(dependent_id)

            if active_dependents:
                raise PluginDependencyError(
                    f"Cannot uninstall plugin {plugin_id} - active dependents: {active_dependents}",
                    plugin_id,
                )

            # Stop plugin if active
            await self.stop_plugin(plugin_id, tenant_id)

            # Unload from loader
            await self.loader.unload_plugin(plugin_id)

            # Unregister from registry
            self.registry.unregister_plugin(plugin_id)

            # Clean up tenant configuration
            if tenant_id and tenant_id in self.tenant_configs:
                self.tenant_configs[tenant_id].pop(plugin_id, None)

            # Clean up metrics
            self.plugin_metrics.pop(plugin_id, None)
            self.last_health_check.pop(plugin_id, None)

            self.logger.info(f"Successfully uninstalled plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Error uninstalling plugin {plugin_id}: {e}")
            raise

    async def start_plugin(
        self, plugin_id: str, tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Start (activate) a plugin.

        Args:
            plugin_id: Plugin ID to start
            tenant_id: Tenant ID for context
        """
        try:
            instance = self.registry.get_plugin_instance(plugin_id)
            if not instance:
                raise PluginLifecycleError(f"Plugin {plugin_id} is not loaded")

            if instance.status == PluginStatus.ACTIVE:
                self.logger.warning(f"Plugin {plugin_id} is already active")
                return

            # Validate plugin license before starting
            license_valid = await self._validate_plugin_license(plugin_id)
            if not license_valid:
                raise PluginLifecycleError(
                    f"Plugin {plugin_id} license validation failed"
                )

            # Check dependencies are active
            await self._check_dependencies_active(plugin_id)

            # Set context
            context = PluginContext(tenant_id=tenant_id)
            instance.set_context(context)

            # Activate plugin
            await instance.activate()
            instance.status = PluginStatus.ACTIVE

            # Store context
            self.active_contexts[plugin_id] = context

            # Report plugin activation to Management Platform
            await self._report_plugin_usage(plugin_id, "activation", 1)

            self.logger.info(f"Successfully started plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Error starting plugin {plugin_id}: {e}")
            raise PluginLifecycleError(f"Failed to start plugin {plugin_id}: {e}")

    async def stop_plugin(
        self, plugin_id: str, tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Stop (deactivate) a plugin.

        Args:
            plugin_id: Plugin ID to stop
            tenant_id: Tenant ID for context
        """
        try:
            instance = self.registry.get_plugin_instance(plugin_id)
            if not instance:
                self.logger.warning(f"Plugin {plugin_id} is not loaded")
                return

            if instance.status != PluginStatus.ACTIVE:
                self.logger.warning(f"Plugin {plugin_id} is not active")
                return

            # Check for active dependents
            dependents = self.registry.get_plugin_dependents(plugin_id)
            active_dependents = []

            for dependent_id in dependents:
                dep_instance = self.registry.get_plugin_instance(dependent_id)
                if dep_instance and dep_instance.status == PluginStatus.ACTIVE:
                    active_dependents.append(dependent_id)

            if active_dependents:
                self.logger.warning(
                    f"Stopping plugin {plugin_id} with active dependents: {active_dependents}"
                )
                # Stop dependents first
                for dependent_id in active_dependents:
                    await self.stop_plugin(dependent_id, tenant_id)

            # Deactivate plugin
            await instance.deactivate()
            instance.status = PluginStatus.INACTIVE

            # Clean up context
            self.active_contexts.pop(plugin_id, None)

            self.logger.info(f"Successfully stopped plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Error stopping plugin {plugin_id}: {e}")
            raise PluginLifecycleError(f"Failed to stop plugin {plugin_id}: {e}")

    async def restart_plugin(
        self, plugin_id: str, tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Restart a plugin.

        Args:
            plugin_id: Plugin ID to restart
            tenant_id: Tenant ID for context
        """
        await self.stop_plugin(plugin_id, tenant_id)
        await self.start_plugin(plugin_id, tenant_id)

    async def reload_plugin(
        self, plugin_id: str, tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Reload a plugin (hot reload if supported).

        Args:
            plugin_id: Plugin ID to reload
            tenant_id: Tenant ID for context
        """
        try:
            plugin_info = self.registry.get_plugin_info(plugin_id)
            if not plugin_info:
                raise PluginError(f"Plugin {plugin_id} not found")

            if not plugin_info.supports_hot_reload:
                raise PluginError(f"Plugin {plugin_id} does not support hot reload")

            # Reload using loader
            await self.loader.reload_plugin(plugin_id)

            # Restart if it was active
            instance = self.registry.get_plugin_instance(plugin_id)
            if instance and instance.status == PluginStatus.ACTIVE:
                await self.start_plugin(plugin_id, tenant_id)

            self.logger.info(f"Successfully reloaded plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Error reloading plugin {plugin_id}: {e}")
            raise

    def configure_plugin(
        self, plugin_id: str, config: PluginConfig, tenant_id: Optional[UUID] = None
    ) -> None:
        """
        Configure a plugin.

        Args:
            plugin_id: Plugin ID to configure
            config: New plugin configuration
            tenant_id: Tenant ID for tenant-specific configuration
        """
        try:
            # Validate configuration
            instance = self.registry.get_plugin_instance(plugin_id)
            if instance:
                # This would be async in real implementation
                # valid = await instance.validate_config(config)
                # if not valid:
                #     raise PluginConfigError(f"Invalid configuration for plugin {plugin_id}")
                pass

            # Store configuration
            if tenant_id:
                if tenant_id not in self.tenant_configs:
                    self.tenant_configs[tenant_id] = {}
                self.tenant_configs[tenant_id][plugin_id] = config
            else:
                self.registry.set_plugin_config(plugin_id, config)

            # Update instance config if loaded
            if instance:
                instance.config = config

            self.logger.info(f"Updated configuration for plugin: {plugin_id}")

        except Exception as e:
            self.logger.error(f"Error configuring plugin {plugin_id}: {e}")
            raise

    def get_plugin_status(self, plugin_id: str) -> Optional[PluginStatus]:
        """Get plugin status."""
        instance = self.registry.get_plugin_instance(plugin_id)
        return instance.status if instance else None

    def list_plugins(
        self,
        category: Optional[PluginCategory] = None,
        status: Optional[PluginStatus] = None,
        tenant_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        List plugins with optional filtering.

        Args:
            category: Filter by category
            status: Filter by status
            tenant_id: Filter by tenant (if tenant-specific configs exist)

        Returns:
            List of plugin information dictionaries
        """
        plugin_ids = self.registry.list_plugins(category, status)
        result = []

        for plugin_id in plugin_ids:
            plugin_info = self.registry.get_plugin_info(plugin_id)
            instance = self.registry.get_plugin_instance(plugin_id)

            plugin_data = {
                "id": plugin_id,
                "info": plugin_info,
                "status": (
                    instance.status.value if instance else PluginStatus.UNLOADED.value
                ),
                "has_tenant_config": tenant_id is not None
                and tenant_id in self.tenant_configs
                and plugin_id in self.tenant_configs[tenant_id],
            }

            result.append(plugin_data)

        return result

    async def get_plugin_health(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get plugin health status.

        Args:
            plugin_id: Plugin ID

        Returns:
            Health status dictionary
        """
        instance = self.registry.get_plugin_instance(plugin_id)
        if not instance:
            return {
                "plugin_id": plugin_id,
                "status": "not_loaded",
                "healthy": False,
                "last_check": None,
            }

        try:
            health_data = await instance.health_check()
            health_data["plugin_id"] = plugin_id
            health_data["last_check"] = datetime.now(timezone.utc).isoformat()

            # Store last health check time
            self.last_health_check[plugin_id] = datetime.now(timezone.utc)

            return health_data

        except Exception as e:
            return {
                "plugin_id": plugin_id,
                "status": "error",
                "healthy": False,
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    async def get_plugin_metrics(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get plugin metrics.

        Args:
            plugin_id: Plugin ID

        Returns:
            Metrics dictionary
        """
        instance = self.registry.get_plugin_instance(plugin_id)
        if not instance:
            return {"plugin_id": plugin_id, "error": "Plugin not loaded"}

        try:
            metrics = await instance.get_metrics()
            metrics["plugin_id"] = plugin_id
            metrics["collected_at"] = datetime.now(timezone.utc).isoformat()

            # Store metrics
            self.plugin_metrics[plugin_id] = metrics

            return metrics

        except Exception as e:
            return {
                "plugin_id": plugin_id,
                "error": str(e),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }

    async def bulk_operation(
        self, operation: str, plugin_ids: List[str], tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Perform bulk operation on multiple plugins.

        Args:
            operation: Operation to perform ('start', 'stop', 'restart', 'reload')
            plugin_ids: List of plugin IDs
            tenant_id: Tenant ID for context

        Returns:
            Results dictionary with success/failure counts
        """
        results = {
            "operation": operation,
            "total": len(plugin_ids),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

        for plugin_id in plugin_ids:
            try:
                if operation == "start":
                    await self.start_plugin(plugin_id, tenant_id)
                elif operation == "stop":
                    await self.stop_plugin(plugin_id, tenant_id)
                elif operation == "restart":
                    await self.restart_plugin(plugin_id, tenant_id)
                elif operation == "reload":
                    await self.reload_plugin(plugin_id, tenant_id)
                else:
                    raise ValueError(f"Unknown operation: {operation}")

                results["successful"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{plugin_id}: {str(e)}")
                self.logger.error(
                    f"Bulk operation {operation} failed for plugin {plugin_id}: {e}"
                )

        return results

    def get_manager_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics."""
        registry_stats = self.registry.get_registry_stats()
        load_stats = self.loader.get_load_statistics()

        return {
            "registry": registry_stats,
            "loader": load_stats,
            "active_contexts": len(self.active_contexts),
            "tenant_configs": len(self.tenant_configs),
            "background_tasks": len(self.background_tasks),
            "is_started": self.is_started,
        }

    async def _check_dependencies_active(self, plugin_id: str) -> None:
        """Check that all plugin dependencies are active."""
        dependencies = self.registry.get_plugin_dependencies(plugin_id)

        for dep_id in dependencies:
            dep_instance = self.registry.get_plugin_instance(dep_id)
            if not dep_instance or dep_instance.status != PluginStatus.ACTIVE:
                raise PluginDependencyError(
                    f"Dependency {dep_id} is not active for plugin {plugin_id}",
                    plugin_id,
                    [dep_id],
                )

    async def _stop_all_plugins(self) -> None:
        """Stop all active plugins in reverse dependency order."""
        load_order = self.registry.get_load_order()

        # Stop in reverse order
        for plugin_id in reversed(load_order):
            instance = self.registry.get_plugin_instance(plugin_id)
            if instance and instance.status == PluginStatus.ACTIVE:
                try:
                    await self.stop_plugin(plugin_id)
                except Exception as e:
                    self.logger.error(
                        f"Error stopping plugin {plugin_id} during shutdown: {e}"
                    )

    async def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks."""
        # Health check task
        health_check_task = asyncio.create_task(self._health_check_loop())
        self.background_tasks.add(health_check_task)

        # Metrics collection task
        metrics_task = asyncio.create_task(self._metrics_collection_loop())
        self.background_tasks.add(metrics_task)

        # Cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.background_tasks.add(cleanup_task)

        # Usage metrics flush task
        metrics_flush_task = asyncio.create_task(self._usage_metrics_flush_loop())
        self.background_tasks.add(metrics_flush_task)

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while not self.shutdown_event.is_set():
            try:
                active_plugins = [
                    plugin_id
                    for plugin_id in self.registry.list_plugins()
                    if self.registry.get_plugin_instance(plugin_id)
                    and self.registry.get_plugin_instance(plugin_id).status
                    == PluginStatus.ACTIVE
                ]

                for plugin_id in active_plugins:
                    try:
                        await self.get_plugin_health(plugin_id)
                    except Exception as e:
                        self.logger.error(
                            f"Health check failed for plugin {plugin_id}: {e}"
                        )

                await asyncio.sleep(60)  # Health check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)

    async def _metrics_collection_loop(self) -> None:
        """Background metrics collection loop."""
        while not self.shutdown_event.is_set():
            try:
                active_plugins = [
                    plugin_id
                    for plugin_id in self.registry.list_plugins()
                    if self.registry.get_plugin_instance(plugin_id)
                    and self.registry.get_plugin_instance(plugin_id).status
                    == PluginStatus.ACTIVE
                ]

                for plugin_id in active_plugins:
                    try:
                        await self.get_plugin_metrics(plugin_id)
                    except Exception as e:
                        self.logger.error(
                            f"Metrics collection failed for plugin {plugin_id}: {e}"
                        )

                await asyncio.sleep(300)  # Collect metrics every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(300)

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while not self.shutdown_event.is_set():
            try:
                # Clean up old contexts
                current_time = datetime.now(timezone.utc)
                expired_contexts = []

                for plugin_id, context in self.active_contexts.items():
                    # Remove contexts older than 1 hour with no activity
                    if current_time - context.started_at > timedelta(hours=1):
                        expired_contexts.append(plugin_id)

                for plugin_id in expired_contexts:
                    self.active_contexts.pop(plugin_id, None)

                # Clean up old metrics (keep last 24 hours)
                cutoff_time = current_time - timedelta(hours=24)
                for plugin_id in list(self.plugin_metrics.keys()):
                    metrics = self.plugin_metrics[plugin_id]
                    if "collected_at" in metrics:
                        collected_at = datetime.fromisoformat(
                            metrics["collected_at"].replace("Z", "+00:00")
                        )
                        if collected_at < cutoff_time:
                            del self.plugin_metrics[plugin_id]

                await asyncio.sleep(3600)  # Cleanup every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    async def _validate_plugin_license(self, plugin_id: str) -> bool:
        """Validate plugin license with Management Platform."""
        try:
            # Check cache first
            cache_key = f"{plugin_id}"
            cached_license = self.license_cache.get(cache_key)

            if cached_license:
                cache_time = cached_license.get("cached_at", datetime.min)
                if (
                    datetime.now(timezone.utc) - cache_time
                ).total_seconds() < self.license_cache_ttl:
                    return cached_license.get("is_valid", False)

            # Validate with Management Platform
            management_client = await get_management_client()
            license_status = await management_client.validate_plugin_license(plugin_id)

            # Cache result
            self.license_cache[cache_key] = {
                "is_valid": license_status.is_valid,
                "license_status": license_status.license_status,
                "tier": license_status.tier,
                "features": license_status.features,
                "cached_at": datetime.now(timezone.utc),
            }

            return license_status.is_valid

        except Exception as e:
            self.logger.error(f"Error validating license for plugin {plugin_id}: {e}")
            # Default to allowing plugin if validation fails (graceful degradation)
            return True

    async def _report_plugin_usage(
        self,
        plugin_id: str,
        metric_name: str,
        usage_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Report plugin usage to Management Platform."""
        try:
            # Create usage metric
            usage_metric = UsageMetric(
                plugin_id=plugin_id,
                metric_name=metric_name,
                usage_count=usage_count,
                metadata=metadata or {},
            )

            # Add to buffer
            self.usage_metrics_buffer.append(usage_metric)

            # Send batch if buffer is full
            if len(self.usage_metrics_buffer) >= self.usage_metrics_batch_size:
                await self._flush_usage_metrics()

        except Exception as e:
            self.logger.error(f"Error reporting usage for plugin {plugin_id}: {e}")

    async def _flush_usage_metrics(self):
        """Flush usage metrics buffer to Management Platform."""
        if not self.usage_metrics_buffer:
            return

        try:
            # Group metrics by plugin_id
            metrics_by_plugin = {}
            for metric in self.usage_metrics_buffer:
                plugin_id = metric.plugin_id
                if plugin_id not in metrics_by_plugin:
                    metrics_by_plugin[plugin_id] = []
                metrics_by_plugin[plugin_id].append(metric)

            # Report to Management Platform
            management_client = await get_management_client()

            for plugin_id, metrics in metrics_by_plugin.items():
                try:
                    await management_client.report_plugin_usage(plugin_id, metrics)
                except Exception as e:
                    self.logger.error(
                        f"Failed to report usage for plugin {plugin_id}: {e}"
                    )

            # Clear buffer after successful reporting
            self.usage_metrics_buffer.clear()

        except Exception as e:
            self.logger.error(f"Error flushing usage metrics: {e}")

    async def validate_plugin_feature_access(
        self, plugin_id: str, feature: str
    ) -> bool:
        """Validate access to specific plugin feature."""
        try:
            management_client = await get_management_client()
            license_status = await management_client.validate_plugin_license(
                plugin_id, feature
            )

            if license_status.is_valid and feature in license_status.features:
                # Report feature usage
                await self._report_plugin_usage(
                    plugin_id, f"feature_{feature}", 1, {"feature": feature}
                )
                return True

            return False

        except Exception as e:
            self.logger.error(
                f"Error validating feature access {plugin_id}.{feature}: {e}"
            )
            return False

    async def report_plugin_api_call(
        self, plugin_id: str, endpoint: str, response_time_ms: float = None
    ):
        """Report plugin API call usage."""
        metadata = {"endpoint": endpoint}
        if response_time_ms is not None:
            metadata["response_time_ms"] = response_time_ms

        await self._report_plugin_usage(plugin_id, "api_call", 1, metadata)

    async def report_plugin_storage_usage(self, plugin_id: str, storage_bytes: int):
        """Report plugin storage usage."""
        await self._report_plugin_usage(
            plugin_id,
            "storage_usage",
            storage_bytes,
            {"unit": "bytes", "storage_bytes": storage_bytes},
        )

    async def report_plugin_transaction(
        self, plugin_id: str, transaction_amount: float = None
    ):
        """Report plugin transaction processing."""
        metadata = {}
        if transaction_amount is not None:
            metadata["transaction_amount"] = transaction_amount

        await self._report_plugin_usage(plugin_id, "transaction", 1, metadata)

    async def _usage_metrics_flush_loop(self) -> None:
        """Background usage metrics flush loop."""
        while not self.shutdown_event.is_set():
            try:
                await self._flush_usage_metrics()
                await asyncio.sleep(60)  # Flush metrics every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in usage metrics flush loop: {e}")
                await asyncio.sleep(60)
