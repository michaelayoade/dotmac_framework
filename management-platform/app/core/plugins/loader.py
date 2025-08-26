"""
Plugin loader for dynamic plugin discovery and loading.
"""

import logging
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Tuple, Type, Dict, Any, Optional
import json
import yaml

from base import BasePlugin, PluginError

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loader for discovering and loading plugins dynamically."""
    
    def __init__(self):
        self._loaded_modules = {}
    
    async def discover_plugins(self, plugin_directory: str) -> List[Tuple[Type[BasePlugin], Dict[str, Any]]]:
        """Discover plugins in a directory."""
        plugins = []
        plugin_path = Path(plugin_directory)
        
        if not plugin_path.exists() or not plugin_path.is_dir():
            logger.warning(f"Plugin directory not found: {plugin_directory}")
            return plugins
        
        # Look for plugin definitions
        for item in plugin_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                plugin_info = await self._load_plugin_from_directory(item)
                if plugin_info:
                    plugins.append(plugin_info)
            elif item.suffix == '.py' and not item.name.startswith('_'):
                plugin_info = await self._load_plugin_from_file(item)
                if plugin_info:
                    plugins.append(plugin_info)
        
        logger.info(f"Discovered {len(plugins)} plugins in {plugin_directory}")
        return plugins
    
    async def load_plugin_by_name(self, plugin_name: str, plugin_path: str) -> Tuple[Type[BasePlugin], Dict[str, Any]]:
        """Load a specific plugin by name and path."""
        try:
            # Load plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if not spec or not spec.loader:
                raise PluginError(f"Could not load plugin spec: {plugin_name}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                raise PluginError(f"No plugin class found in {plugin_name}")
            
            # Load configuration
            config = await self._load_plugin_config(Path(plugin_path).parent)
            
            return plugin_class, config
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            raise PluginError(f"Failed to load plugin: {e}")
    
    async def _load_plugin_from_directory(self, plugin_dir: Path) -> Optional[Tuple[Type[BasePlugin], Dict[str, Any]]]:
        """Load plugin from directory structure."""
        try:
            # Look for main plugin file
            main_files = ['plugin.py', '__init__.py', 'main.py']
            plugin_file = None
            
            for filename in main_files:
                candidate = plugin_dir / filename
                if candidate.exists():
                    plugin_file = candidate
                    break
            
            if not plugin_file:
                logger.debug(f"No main plugin file found in {plugin_dir}")
                return None
            
            # Load plugin module
            module_name = f"plugin_{plugin_dir.name}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                return None
            
            # Load configuration
            config = await self._load_plugin_config(plugin_dir)
            
            return plugin_class, config
            
        except Exception as e:
            logger.error(f"Failed to load plugin from directory {plugin_dir}: {e}")
            return None
    
    async def _load_plugin_from_file(self, plugin_file: Path) -> Optional[Tuple[Type[BasePlugin], Dict[str, Any]]]:
        """Load plugin from single Python file."""
        try:
            module_name = f"plugin_{plugin_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                return None
            
            # Look for configuration file in same directory
            config = await self._load_plugin_config(plugin_file.parent, plugin_file.stem)
            
            return plugin_class, config
            
        except Exception as e:
            logger.error(f"Failed to load plugin from file {plugin_file}: {e}")
            return None
    
    def _find_plugin_class(self, module) -> Optional[Type[BasePlugin]]:
        """Find plugin class in module."""
        for name in dir(module):
            obj = getattr(module, name)
            
            if (isinstance(obj, type) and 
                issubclass(obj, BasePlugin) and 
                obj != BasePlugin):
                return obj
        
        return None
    
    async def _load_plugin_config(self, plugin_dir: Path, plugin_name: str = None) -> Dict[str, Any]:
        """Load plugin configuration from various formats."""
        config = {}
        
        # Try different configuration file formats
        config_files = [
            'plugin.json',
            'plugin.yaml', 
            'plugin.yml',
            'config.json',
            'config.yaml',
            'config.yml'
        ]
        
        if plugin_name:
            config_files.extend([
                f'{plugin_name}.json',
                f'{plugin_name}.yaml',
                f'{plugin_name}.yml'
            ])
        
        for config_file in config_files:
            config_path = plugin_dir / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        if config_file.endswith('.json'):
                            config = json.load(f)
                        elif config_file.endswith(('.yaml', '.yml')):
                            config = yaml.safe_load(f)
                    
                    logger.debug(f"Loaded plugin config from {config_path}")
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")
                    continue
        
        return config
    
    def get_loaded_modules(self) -> List[str]:
        """Get list of loaded plugin modules."""
        return list(self._loaded_modules.keys())
    
    async def reload_module(self, module_name: str) -> bool:
        """Reload a plugin module."""
        try:
            if module_name in self._loaded_modules:
                module = self._loaded_modules[module_name]
                importlib.reload(module)
                logger.info(f"Reloaded plugin module: {module_name}")
                return True
            else:
                logger.warning(f"Module not found for reload: {module_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to reload module {module_name}: {e}")
            return False