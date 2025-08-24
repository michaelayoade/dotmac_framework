"""
Strategic Communication Plugin System

True plugin architecture for communication channels. Plugins can be:
- Loaded at runtime without code deployment
- Distributed as separate packages
- Hot-swapped without system restart
- Configured entirely through external configuration
- Developed by third parties

This eliminates ALL hardcoded dependencies and enables true extensibility.
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Union
import yaml
import json

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Plugin manifest describing plugin capabilities and requirements."""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    channel_type: str
    capabilities: List[str]
    required_config: List[str]
    optional_config: Dict[str, Any]
    dependencies: List[str]
    min_platform_version: str
    entry_point: str  # Module.ClassName
    license: str = "MIT"
    homepage: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginManifest':
        """Create manifest from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_file(cls, manifest_path: Path) -> 'PluginManifest':
        """Load manifest from file."""
        if manifest_path.suffix.lower() == '.json':
            with open(manifest_path, 'r') as f:
                data = json.load(f)
        elif manifest_path.suffix.lower() in ['.yml', '.yaml']:
            with open(manifest_path, 'r') as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported manifest format: {manifest_path.suffix}")
        
        return cls.from_dict(data)


class PluginInterface(ABC):
    """Strategic plugin interface for communication channels."""
    
    def __init__(self, config: Dict[str, Any], manifest: PluginManifest):
        """Initialize plugin with configuration and manifest."""
        self.config = config
        self.manifest = manifest
        self._initialized = False
    
    @property
    def plugin_id(self) -> str:
        """Unique plugin identifier."""
        return self.manifest.plugin_id
    
    @property 
    def channel_type(self) -> str:
        """Communication channel type."""
        return self.manifest.channel_type
    
    @property
    def is_initialized(self) -> bool:
        """Whether plugin is initialized."""
        return self._initialized
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass
    
    @abstractmethod
    async def send_message(self, recipient: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send message via this channel.
        
        Returns:
            {
                "success": bool,
                "message_id": str,
                "error": Optional[str],
                "metadata": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod 
    async def validate_config(self) -> bool:
        """Validate plugin configuration."""
        pass
    
    async def shutdown(self) -> bool:
        """Shutdown plugin gracefully."""
        self._initialized = False
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check plugin health status."""
        return {
            "healthy": self._initialized,
            "plugin_id": self.plugin_id,
            "channel_type": self.channel_type
        }
    
    def get_required_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this plugin."""
        return {
            "required": self.manifest.required_config,
            "optional": self.manifest.optional_config,
            "type": "object",
            "properties": {}
        }


class PluginLoader:
    """Dynamic plugin loader with security and validation."""
    
    def __init__(self):
        """Initialize plugin loader."""
        self._loaded_modules: Dict[str, Any] = {}
        self._plugin_paths: List[Path] = []
        self._security_enabled = True
        
        # Default plugin search paths
        self._plugin_paths = [
            Path("plugins/communication"),
            Path("shared/communication/plugins"),
            Path("/opt/dotmac/plugins/communication"),
            Path.home() / ".dotmac/plugins/communication"
        ]
    
    def add_plugin_path(self, path: Union[str, Path]):
        """Add a plugin search path."""
        plugin_path = Path(path)
        if plugin_path not in self._plugin_paths:
            self._plugin_paths.append(plugin_path)
            logger.info(f"Added plugin search path: {plugin_path}")
    
    async def discover_plugins(self) -> List[PluginManifest]:
        """Discover all available plugins in search paths."""
        discovered_plugins = []
        
        for search_path in self._plugin_paths:
            if not search_path.exists():
                continue
                
            logger.info(f"Scanning for plugins in: {search_path}")
            
            # Look for manifest files
            for manifest_file in search_path.rglob("manifest.*"):
                if manifest_file.suffix.lower() in ['.json', '.yml', '.yaml']:
                    try:
                        manifest = PluginManifest.from_file(manifest_file)
                        manifest.plugin_path = manifest_file.parent
                        discovered_plugins.append(manifest)
                        logger.info(f"Discovered plugin: {manifest.plugin_id}")
                    except Exception as e:
                        logger.error(f"Error loading manifest {manifest_file}: {e}")
        
        return discovered_plugins
    
    async def load_plugin(self, manifest: PluginManifest, config: Dict[str, Any]) -> Optional[PluginInterface]:
        """Load a plugin from its manifest."""
        try:
            # Security validation
            if self._security_enabled and not await self._validate_plugin_security(manifest):
                logger.error(f"Plugin {manifest.plugin_id} failed security validation")
                return None
            
            # Load plugin module
            plugin_module = await self._load_plugin_module(manifest)
            if not plugin_module:
                return None
            
            # Get plugin class
            plugin_class = await self._get_plugin_class(plugin_module, manifest)
            if not plugin_class:
                return None
            
            # Instantiate plugin
            plugin_instance = plugin_class(config, manifest)
            
            # Validate plugin implements interface
            if not isinstance(plugin_instance, PluginInterface):
                logger.error(f"Plugin {manifest.plugin_id} does not implement PluginInterface")
                return None
            
            logger.info(f"Successfully loaded plugin: {manifest.plugin_id}")
            return plugin_instance
            
        except Exception as e:
            logger.error(f"Error loading plugin {manifest.plugin_id}: {e}")
            return None
    
    async def _validate_plugin_security(self, manifest: PluginManifest) -> bool:
        """Validate plugin security (signature, whitelist, etc.)."""
        # Implement security validation here
        # - Check plugin signature
        # - Validate against whitelist
        # - Scan for malicious code patterns
        
        # For now, basic validation
        required_fields = ['plugin_id', 'name', 'version', 'entry_point']
        for field in required_fields:
            if not getattr(manifest, field):
                logger.error(f"Plugin missing required field: {field}")
                return False
        
        return True
    
    async def _load_plugin_module(self, manifest: PluginManifest) -> Optional[Any]:
        """Dynamically load plugin module."""
        try:
            plugin_path = getattr(manifest, 'plugin_path', Path('.'))
            entry_parts = manifest.entry_point.split('.')
            module_name = '.'.join(entry_parts[:-1])
            
            # Find Python file
            module_file = plugin_path / f"{module_name.replace('.', '/')}.py"
            if not module_file.exists():
                # Try direct file
                module_file = plugin_path / f"{module_name}.py"
            
            if not module_file.exists():
                logger.error(f"Plugin module file not found: {module_file}")
                return None
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules for proper importing
            full_module_name = f"plugin_{manifest.plugin_id}_{module_name}"
            sys.modules[full_module_name] = module
            self._loaded_modules[manifest.plugin_id] = module
            
            # Execute module
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            logger.error(f"Error loading plugin module for {manifest.plugin_id}: {e}")
            return None
    
    async def _get_plugin_class(self, module: Any, manifest: PluginManifest) -> Optional[Type[PluginInterface]]:
        """Extract plugin class from loaded module."""
        try:
            class_name = manifest.entry_point.split('.')[-1]
            
            if not hasattr(module, class_name):
                logger.error(f"Plugin class {class_name} not found in module")
                return None
            
            plugin_class = getattr(module, class_name)
            
            # Validate class
            if not inspect.isclass(plugin_class):
                logger.error(f"{class_name} is not a class")
                return None
            
            if not issubclass(plugin_class, PluginInterface):
                logger.error(f"{class_name} does not inherit from PluginInterface")
                return None
            
            return plugin_class
            
        except Exception as e:
            logger.error(f"Error getting plugin class: {e}")
            return None
    
    def unload_plugin(self, plugin_id: str):
        """Unload a plugin and clean up its module."""
        if plugin_id in self._loaded_modules:
            # Remove from sys.modules
            module_name = f"plugin_{plugin_id}"
            modules_to_remove = [name for name in sys.modules.keys() if name.startswith(module_name)]
            for name in modules_to_remove:
                del sys.modules[name]
            
            del self._loaded_modules[plugin_id]
            logger.info(f"Unloaded plugin: {plugin_id}")


class PluginRegistry:
    """Registry for managing loaded communication plugins."""
    
    def __init__(self):
        """Initialize plugin registry."""
        self._plugins: Dict[str, PluginInterface] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._loader = PluginLoader()
        self._config: Dict[str, Any] = {}
    
    async def initialize_from_config(self, config_path: Union[str, Path]):
        """Initialize plugins from configuration file."""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.error(f"Plugin configuration file not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.json':
                    self._config = json.load(f)
                else:
                    self._config = yaml.safe_load(f)
            
            # Add custom plugin paths
            for path in self._config.get('plugin_paths', []):
                self._loader.add_plugin_path(path)
            
            # Discover available plugins
            available_plugins = await self._loader.discover_plugins()
            
            # Load enabled plugins
            enabled_plugins = self._config.get('enabled_plugins', [])
            loaded_count = 0
            
            for plugin_config in enabled_plugins:
                plugin_id = plugin_config.get('plugin_id')
                if not plugin_id:
                    continue
                
                # Find plugin manifest
                manifest = next((p for p in available_plugins if p.plugin_id == plugin_id), None)
                if not manifest:
                    logger.error(f"Plugin {plugin_id} not found in available plugins")
                    continue
                
                # Load plugin
                plugin_instance = await self._loader.load_plugin(manifest, plugin_config.get('config', {}))
                if plugin_instance:
                    # Initialize plugin
                    if await plugin_instance.initialize():
                        self._plugins[plugin_id] = plugin_instance
                        self._manifests[plugin_id] = manifest
                        loaded_count += 1
                        logger.info(f"✅ Plugin initialized: {plugin_id}")
                    else:
                        logger.error(f"❌ Plugin initialization failed: {plugin_id}")
                else:
                    logger.error(f"❌ Plugin loading failed: {plugin_id}")
            
            logger.info(f"🔌 Plugin system initialized: {loaded_count} plugins loaded")
            return loaded_count > 0
            
        except Exception as e:
            logger.error(f"Error initializing plugins: {e}")
            return False
    
    async def send_message(self, channel_type: str, recipient: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send message via plugin system."""
        # Find plugins that support this channel type
        matching_plugins = [p for p in self._plugins.values() if p.channel_type == channel_type]
        
        if not matching_plugins:
            return {
                "success": False,
                "error": f"No plugins available for channel type: {channel_type}"
            }
        
        # Try plugins in priority order
        last_error = None
        for plugin in matching_plugins:
            try:
                result = await plugin.send_message(recipient, content, metadata or {})
                if result.get("success"):
                    return result
                else:
                    last_error = result.get("error", "Unknown error")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Plugin {plugin.plugin_id} failed: {e}")
        
        return {
            "success": False,
            "error": f"All plugins failed. Last error: {last_error}"
        }
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[str]:
        """List all loaded plugins."""
        return list(self._plugins.keys())
    
    def get_plugins_by_channel_type(self, channel_type: str) -> List[PluginInterface]:
        """Get all plugins that support a channel type."""
        return [p for p in self._plugins.values() if p.channel_type == channel_type]
    
    async def reload_plugin(self, plugin_id: str) -> bool:
        """Hot reload a plugin."""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin {plugin_id} not loaded")
            return False
        
        try:
            # Shutdown existing plugin
            await self._plugins[plugin_id].shutdown()
            
            # Unload plugin
            self._loader.unload_plugin(plugin_id)
            del self._plugins[plugin_id]
            
            # Find plugin config
            plugin_config = next((p for p in self._config.get('enabled_plugins', []) if p.get('plugin_id') == plugin_id), None)
            if not plugin_config:
                logger.error(f"Plugin config not found for {plugin_id}")
                return False
            
            # Reload plugin
            available_plugins = await self._loader.discover_plugins()
            manifest = next((p for p in available_plugins if p.plugin_id == plugin_id), None)
            if not manifest:
                logger.error(f"Plugin manifest not found for {plugin_id}")
                return False
            
            plugin_instance = await self._loader.load_plugin(manifest, plugin_config.get('config', {}))
            if plugin_instance and await plugin_instance.initialize():
                self._plugins[plugin_id] = plugin_instance
                self._manifests[plugin_id] = manifest
                logger.info(f"✅ Plugin reloaded: {plugin_id}")
                return True
            else:
                logger.error(f"❌ Plugin reload failed: {plugin_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_id}: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get plugin system status."""
        status = {
            "total_plugins": len(self._plugins),
            "plugins_by_type": {},
            "plugin_health": {}
        }
        
        for plugin_id, plugin in self._plugins.items():
            # Group by channel type
            channel_type = plugin.channel_type
            if channel_type not in status["plugins_by_type"]:
                status["plugins_by_type"][channel_type] = []
            status["plugins_by_type"][channel_type].append(plugin_id)
            
            # Health check
            try:
                health = await plugin.health_check()
                status["plugin_health"][plugin_id] = health
            except Exception as e:
                status["plugin_health"][plugin_id] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return status


# Global plugin registry
global_plugin_registry = PluginRegistry()


# Convenience functions
async def send_message(channel_type: str, recipient: str, content: str, **kwargs) -> bool:
    """Send message via plugin system."""
    result = await global_plugin_registry.send_message(channel_type, recipient, content, kwargs)
    return result.get("success", False)


async def initialize_plugin_system(config_path: str = "config/communication_plugins.yml") -> bool:
    """Initialize the plugin system."""
    return await global_plugin_registry.initialize_from_config(config_path)