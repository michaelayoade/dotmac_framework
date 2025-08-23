"""Vendor Plugin Loader - Utility for loading and managing vendor-specific plugins."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

from ..core.manager import PluginManager
from ..core.registry import PluginRegistry
from ..core.base import PluginConfig, PluginContext, PluginAPI
from ..core.exceptions import PluginError, PluginLoadError


class VendorPluginLoader:
    """
    Vendor Plugin Loader.
    
    Provides utilities for:
    - Loading vendor-specific integration plugins
    - Managing plugin configurations
    - Handling vendor-specific secrets and credentials
    - Monitoring vendor integration health
    - Automatic plugin discovery and registration
    """
    
    def __init__(
        self,
        plugin_manager: PluginManager,
        config_directory: str = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize vendor plugin loader."""
        self.plugin_manager = plugin_manager
        self.config_directory = config_directory or self._get_default_config_dir()
        self.logger = logger or logging.getLogger(__name__)
        
        # Vendor plugin configurations
        self.vendor_configs = {}
        self.loaded_plugins = {}
        self.plugin_health_status = {}
        
    def _get_default_config_dir(self) -> str:
        """Get default configuration directory."""
        current_dir = Path(__file__).parent.parent
        config_dir = current_dir / "config"
        return str(config_dir)
        
    async def load_vendor_integrations(
        self,
        environment: str = "development",
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load vendor integration plugins based on environment.
        
        Args:
            environment: Target environment (development, production, etc.)
            tenant_id: Tenant ID for tenant-specific configurations
            
        Returns:
            Dictionary with loading results
        """
        try:
            # Load vendor integration configurations
            config_path = Path(self.config_directory) / "vendor_integrations.json"
            
            if not config_path.exists():
                raise PluginError(f"Vendor integration config not found: {config_path}")
                
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            vendor_integrations = config_data.get("vendor_integrations", {})
            environment_config = config_data.get("deployment_scenarios", {}).get(environment, {})
            
            results = {
                "environment": environment,
                "tenant_id": tenant_id,
                "loaded_plugins": [],
                "failed_plugins": [],
                "skipped_plugins": [],
                "total_plugins": len(vendor_integrations),
            }
            
            for plugin_id, plugin_config in vendor_integrations.items():
                try:
                    # Check if plugin is enabled for this environment
                    env_config = environment_config.get(plugin_id, {})
                    if not env_config.get("enabled", plugin_config.get("enabled", True)):
                        results["skipped_plugins"].append({
                            "plugin_id": plugin_id,
                            "reason": "disabled_for_environment"
                        })
                        continue
                        
                    # Merge environment-specific configuration
                    merged_config = self._merge_configurations(plugin_config, env_config)
                    
                    # Load the plugin
                    success = await self._load_vendor_plugin(plugin_id, merged_config, tenant_id)
                    
                    if success:
                        results["loaded_plugins"].append(plugin_id)
                        self.logger.info(f"Successfully loaded vendor plugin: {plugin_id}")
                    else:
                        results["failed_plugins"].append({
                            "plugin_id": plugin_id,
                            "reason": "load_failed"
                        })
                        
                except Exception as e:
                    self.logger.error(f"Failed to load vendor plugin {plugin_id}: {e}")
                    results["failed_plugins"].append({
                        "plugin_id": plugin_id,
                        "reason": str(e)
                    })
                    
            self.logger.info(
                f"Vendor plugin loading complete - "
                f"Loaded: {len(results['loaded_plugins'])}, "
                f"Failed: {len(results['failed_plugins'])}, "
                f"Skipped: {len(results['skipped_plugins'])}"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to load vendor integrations: {e}")
            raise PluginError(f"Vendor integration loading failed: {e}")
            
    async def _load_vendor_plugin(
        self,
        plugin_id: str,
        plugin_config: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Load a specific vendor plugin."""
        try:
            # Validate required secrets
            await self._validate_plugin_secrets(plugin_id, plugin_config)
            
            # Create plugin configuration
            config_data = plugin_config.get("configuration", {})
            
            plugin_cfg = PluginConfig(
                enabled=plugin_config.get("enabled", True),
                tenant_id=tenant_id,
                priority=plugin_config.get("priority", 100),
                config_data=config_data,
                sandbox_enabled=plugin_config.get("sandbox_enabled", True),
                resource_limits=plugin_config.get("resource_limits", {}),
            )
            
            # Get module path and class name
            module_path = plugin_config.get("module_path")
            class_name = plugin_config.get("class_name")
            
            if not module_path or not class_name:
                raise PluginError(f"Missing module_path or class_name for plugin {plugin_id}")
                
            # Load plugin from module
            success_plugin_id = await self.plugin_manager.install_plugin(
                plugin_source=module_path,
                config=plugin_cfg,
                tenant_id=tenant_id
            )
            
            if success_plugin_id:
                # Store plugin configuration
                self.vendor_configs[plugin_id] = plugin_config
                self.loaded_plugins[plugin_id] = success_plugin_id
                
                # Start the plugin if auto_load is enabled
                if plugin_config.get("auto_load", False):
                    await self.plugin_manager.start_plugin(success_plugin_id, tenant_id)
                    
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to load vendor plugin {plugin_id}: {e}")
            return False
            
    async def _validate_plugin_secrets(
        self,
        plugin_id: str,
        plugin_config: Dict[str, Any]
    ) -> None:
        """Validate that required secrets are available."""
        security_config = plugin_config.get("security", {})
        required_secrets = security_config.get("secrets_required", [])
        optional_secrets = security_config.get("optional_secrets", [])
        
        missing_required = []
        missing_optional = []
        
        for secret_id in required_secrets:
            env_var = secret_id.upper().replace("-", "_")
            if not os.getenv(env_var):
                missing_required.append(secret_id)
                
        for secret_id in optional_secrets:
            env_var = secret_id.upper().replace("-", "_")
            if not os.getenv(env_var):
                missing_optional.append(secret_id)
                
        if missing_required:
            raise PluginError(
                f"Plugin {plugin_id} missing required secrets: {missing_required}. "
                f"Please set environment variables: {[s.upper().replace('-', '_') for s in missing_required]}"
            )
            
        if missing_optional:
            self.logger.warning(
                f"Plugin {plugin_id} missing optional secrets: {missing_optional}. "
                f"Some features may not be available."
            )
            
    def _merge_configurations(
        self,
        base_config: Dict[str, Any],
        env_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge base configuration with environment-specific overrides."""
        merged = base_config.copy()
        
        # Merge configuration section
        if "configuration" in env_config:
            if "configuration" not in merged:
                merged["configuration"] = {}
            merged["configuration"].update(env_config["configuration"])
            
        # Merge other top-level settings
        for key, value in env_config.items():
            if key != "configuration":
                merged[key] = value
                
        return merged
        
    async def unload_vendor_integrations(self) -> Dict[str, Any]:
        """Unload all loaded vendor integration plugins."""
        results = {
            "unloaded_plugins": [],
            "failed_plugins": [],
            "total_plugins": len(self.loaded_plugins),
        }
        
        for plugin_id, manager_plugin_id in list(self.loaded_plugins.items()):
            try:
                await self.plugin_manager.uninstall_plugin(manager_plugin_id)
                
                # Clean up tracking
                self.loaded_plugins.pop(plugin_id, None)
                self.vendor_configs.pop(plugin_id, None)
                self.plugin_health_status.pop(plugin_id, None)
                
                results["unloaded_plugins"].append(plugin_id)
                self.logger.info(f"Unloaded vendor plugin: {plugin_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to unload vendor plugin {plugin_id}: {e}")
                results["failed_plugins"].append({
                    "plugin_id": plugin_id,
                    "reason": str(e)
                })
                
        return results
        
    async def get_vendor_plugin_status(self) -> Dict[str, Any]:
        """Get status of all loaded vendor plugins."""
        status = {
            "total_plugins": len(self.loaded_plugins),
            "plugins": {}
        }
        
        for plugin_id, manager_plugin_id in self.loaded_plugins.items():
            try:
                # Get plugin status from manager
                plugin_status = self.plugin_manager.get_plugin_status(manager_plugin_id)
                
                # Get health check data
                health_data = await self.plugin_manager.get_plugin_health(manager_plugin_id)
                
                # Get plugin metrics
                metrics = await self.plugin_manager.get_plugin_metrics(manager_plugin_id)
                
                status["plugins"][plugin_id] = {
                    "manager_plugin_id": manager_plugin_id,
                    "status": plugin_status.value if plugin_status else "unknown",
                    "health": health_data,
                    "metrics": metrics,
                    "config": self.vendor_configs.get(plugin_id, {}),
                }
                
            except Exception as e:
                self.logger.error(f"Failed to get status for plugin {plugin_id}: {e}")
                status["plugins"][plugin_id] = {
                    "manager_plugin_id": manager_plugin_id,
                    "status": "error",
                    "error": str(e)
                }
                
        return status
        
    async def start_vendor_plugin(
        self,
        plugin_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Start a specific vendor plugin."""
        if plugin_id not in self.loaded_plugins:
            self.logger.error(f"Plugin {plugin_id} not loaded")
            return False
            
        try:
            manager_plugin_id = self.loaded_plugins[plugin_id]
            await self.plugin_manager.start_plugin(manager_plugin_id, tenant_id)
            
            self.logger.info(f"Started vendor plugin: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start vendor plugin {plugin_id}: {e}")
            return False
            
    async def stop_vendor_plugin(
        self,
        plugin_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Stop a specific vendor plugin."""
        if plugin_id not in self.loaded_plugins:
            self.logger.error(f"Plugin {plugin_id} not loaded")
            return False
            
        try:
            manager_plugin_id = self.loaded_plugins[plugin_id]
            await self.plugin_manager.stop_plugin(manager_plugin_id, tenant_id)
            
            self.logger.info(f"Stopped vendor plugin: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop vendor plugin {plugin_id}: {e}")
            return False
            
    async def restart_vendor_plugin(
        self,
        plugin_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Restart a specific vendor plugin."""
        if plugin_id not in self.loaded_plugins:
            self.logger.error(f"Plugin {plugin_id} not loaded")
            return False
            
        try:
            manager_plugin_id = self.loaded_plugins[plugin_id]
            await self.plugin_manager.restart_plugin(manager_plugin_id, tenant_id)
            
            self.logger.info(f"Restarted vendor plugin: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart vendor plugin {plugin_id}: {e}")
            return False
            
    async def configure_vendor_plugin(
        self,
        plugin_id: str,
        new_config: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Update configuration for a vendor plugin."""
        if plugin_id not in self.loaded_plugins:
            self.logger.error(f"Plugin {plugin_id} not loaded")
            return False
            
        try:
            # Create new plugin configuration
            plugin_cfg = PluginConfig(
                enabled=new_config.get("enabled", True),
                tenant_id=tenant_id,
                priority=new_config.get("priority", 100),
                config_data=new_config.get("configuration", {}),
                sandbox_enabled=new_config.get("sandbox_enabled", True),
                resource_limits=new_config.get("resource_limits", {}),
            )
            
            # Update plugin configuration
            manager_plugin_id = self.loaded_plugins[plugin_id]
            self.plugin_manager.configure_plugin(manager_plugin_id, plugin_cfg, tenant_id)
            
            # Update stored configuration
            self.vendor_configs[plugin_id].update(new_config)
            
            self.logger.info(f"Updated configuration for vendor plugin: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure vendor plugin {plugin_id}: {e}")
            return False
            
    async def health_check_all_plugins(self) -> Dict[str, Any]:
        """Perform health check on all loaded vendor plugins."""
        results = {
            "timestamp": asyncio.get_event_loop().time(),
            "total_plugins": len(self.loaded_plugins),
            "healthy_plugins": 0,
            "unhealthy_plugins": 0,
            "plugins": {}
        }
        
        for plugin_id, manager_plugin_id in self.loaded_plugins.items():
            try:
                health_data = await self.plugin_manager.get_plugin_health(manager_plugin_id)
                
                is_healthy = health_data.get("healthy", False)
                if is_healthy:
                    results["healthy_plugins"] += 1
                else:
                    results["unhealthy_plugins"] += 1
                    
                results["plugins"][plugin_id] = health_data
                
                # Store health status for tracking
                self.plugin_health_status[plugin_id] = {
                    "healthy": is_healthy,
                    "last_check": health_data.get("timestamp"),
                    "details": health_data
                }
                
            except Exception as e:
                self.logger.error(f"Health check failed for plugin {plugin_id}: {e}")
                results["unhealthy_plugins"] += 1
                results["plugins"][plugin_id] = {
                    "healthy": False,
                    "error": str(e)
                }
                
        return results
        
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded vendor plugin IDs."""
        return list(self.loaded_plugins.keys())
        
    def is_plugin_loaded(self, plugin_id: str) -> bool:
        """Check if a vendor plugin is loaded."""
        return plugin_id in self.loaded_plugins
        
    def get_plugin_config(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific plugin."""
        return self.vendor_configs.get(plugin_id)
        
    async def discover_available_plugins(self) -> Dict[str, Any]:
        """Discover available vendor plugins from configuration."""
        config_path = Path(self.config_directory) / "vendor_integrations.json"
        
        if not config_path.exists():
            return {"available_plugins": []}
            
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            
        vendor_integrations = config_data.get("vendor_integrations", {})
        
        return {
            "available_plugins": list(vendor_integrations.keys()),
            "total_available": len(vendor_integrations),
            "loaded_plugins": list(self.loaded_plugins.keys()),
            "total_loaded": len(self.loaded_plugins),
            "plugin_details": {
                plugin_id: {
                    "name": config.get("name"),
                    "description": config.get("description"),
                    "version": config.get("version"),
                    "category": config.get("category"),
                    "features": config.get("features", []),
                    "loaded": plugin_id in self.loaded_plugins
                }
                for plugin_id, config in vendor_integrations.items()
            }
        }


# Utility functions for common use cases

async def load_voltha_integration(
    plugin_manager: PluginManager,
    environment: str = "development",
    tenant_id: Optional[str] = None
) -> bool:
    """Load VOLTHA integration plugin."""
    loader = VendorPluginLoader(plugin_manager)
    results = await loader.load_vendor_integrations(environment, tenant_id)
    
    return "voltha_integration" in results["loaded_plugins"]


async def load_analytics_events(
    plugin_manager: PluginManager,
    environment: str = "development", 
    tenant_id: Optional[str] = None
) -> bool:
    """Load Analytics Events plugin."""
    loader = VendorPluginLoader(plugin_manager)
    results = await loader.load_vendor_integrations(environment, tenant_id)
    
    return "analytics_events" in results["loaded_plugins"]


async def load_all_vendor_integrations(
    plugin_manager: PluginManager,
    environment: str = "development",
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """Load all available vendor integration plugins."""
    loader = VendorPluginLoader(plugin_manager)
    return await loader.load_vendor_integrations(environment, tenant_id)