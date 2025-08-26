"""Plugin Loader - Handles plugin discovery and loading."""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import re
import sys
import hashlib
import hmac
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import traceback

from .base import BasePlugin, PluginInfo, PluginStatus, PluginConfig, PluginAPI
from .registry import PluginRegistry, plugin_registry
from .exceptions import (
    PluginLoadError,
    PluginConfigError,
    PluginDependencyError,
    PluginSecurityError,
)


class PluginLoader:
    """
    Plugin loader and discovery system.

    Handles discovering, loading, and initializing plugins from various sources.
    """

    def __init__(
        self, registry: PluginRegistry, api: PluginAPI, logger: logging.Logger = None
    ):
        """Initialize plugin loader."""
        self.registry = registry
        self.api = api
        self.logger = logger or logging.getLogger(__name__)

        # Plugin search paths
        self.search_paths: List[Path] = []

        # Security settings
        self.security_enabled = True
        self.allowed_modules = set()
        self.blocked_modules = set()

        # Loading statistics
        self.load_stats = {"discovered": 0, "loaded": 0, "failed": 0, "skipped": 0}

    def add_search_path(self, path: str) -> None:
        """Add a directory to plugin search paths."""
        path_obj = Path(path)
        if path_obj.exists() and path_obj.is_dir():
            self.search_paths.append(path_obj)
            self.logger.debug(f"Added plugin search path: {path}")
        else:
            self.logger.warning(f"Plugin search path does not exist: {path}")

    def set_security_policy(
        self,
        enabled: bool = True,
        allowed_modules: List[str] = None,
        blocked_modules: List[str] = None,
    ) -> None:
        """Set plugin security policy."""
        self.security_enabled = enabled

        if allowed_modules:
            self.allowed_modules = set(allowed_modules)

        if blocked_modules:
            self.blocked_modules = set(blocked_modules)

        self.logger.info(f"Plugin security policy updated - enabled: {enabled}")

    async def discover_plugins(self, paths: Optional[List[str]] = None) -> List[str]:
        """
        Discover plugins in search paths.

        Args:
            paths: Optional list of paths to search (uses default search paths if None)

        Returns:
            List of discovered plugin file paths
        """
        discovered_files = []
        search_locations = []

        if paths:
            search_locations = [Path(p) for p in paths]
        else:
            search_locations = self.search_paths

        for search_path in search_locations:
            if not search_path.exists():
                continue

            # Search for Python files containing plugins
            for py_file in search_path.rglob("*.py"):
                # Skip __init__.py and private modules
                if py_file.name.startswith("_"):
                    continue

                # Basic check for plugin content
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "BasePlugin" in content and "class " in content:
                            discovered_files.append(str(py_file))
                            self.logger.debug(f"Discovered potential plugin: {py_file}")
                except Exception as e:
                    self.logger.warning(
                        f"Error reading potential plugin file {py_file}: {e}"
                    )

        self.load_stats["discovered"] = len(discovered_files)
        self.logger.info(f"Discovered {len(discovered_files)} potential plugin files")

        return discovered_files

    async def load_plugin_from_file(
        self, file_path: str, config: Optional[PluginConfig] = None
    ) -> Optional[str]:
        """
        Load a plugin from a Python file.

        Args:
            file_path: Path to Python file containing plugin
            config: Plugin configuration

        Returns:
            Plugin ID if successful, None otherwise
        """
        try:
            # Security check
            if self.security_enabled:
                await self._security_check_file(file_path)

            # Import module
            module_name = Path(file_path).stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)

            if spec is None:
                raise PluginLoadError(f"Cannot create module spec for {file_path}")

            module = importlib.util.module_from_spec(spec)

            # Execute module
            spec.loader.exec_module(module)

            # Find plugin classes
            plugin_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                    and hasattr(obj, "plugin_info")
                ):
                    plugin_classes.append(obj)

            if not plugin_classes:
                self.logger.warning(f"No plugin classes found in {file_path}")
                self.load_stats["skipped"] += 1
                return None

            # Load first plugin class found
            plugin_class = plugin_classes[0]

            if len(plugin_classes) > 1:
                self.logger.warning(
                    f"Multiple plugin classes found in {file_path}, using {plugin_class.__name__}"
                )

            # Create plugin instance to get info
            temp_config = config or PluginConfig()
            plugin_instance = plugin_class(temp_config, self.api)
            plugin_info = plugin_instance.plugin_info

            # Validate plugin
            await self._validate_plugin(plugin_instance)

            # Register plugin
            self.registry.register_plugin(plugin_class, plugin_info)

            if config:
                self.registry.set_plugin_config(plugin_info.id, config)

            self.load_stats["loaded"] += 1
            self.logger.info(
                f"Successfully loaded plugin: {plugin_info.name} ({plugin_info.id})"
            )

            return plugin_info.id

        except Exception as e:
            self.load_stats["failed"] += 1
            error_msg = f"Failed to load plugin from {file_path}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            raise PluginLoadError(error_msg)

    async def load_plugin_from_module(
        self, module_name: str, config: Optional[PluginConfig] = None
    ) -> Optional[str]:
        """
        Load a plugin from a Python module.

        Args:
            module_name: Python module name (e.g., 'mypackage.plugins.myplugin')
            config: Plugin configuration

        Returns:
            Plugin ID if successful, None otherwise
        """
        try:
            # Security check
            if self.security_enabled:
                await self._security_check_module(module_name)

            # Import module
            module = importlib.import_module(module_name)

            # Find plugin classes
            plugin_classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                    and hasattr(obj, "plugin_info")
                ):
                    plugin_classes.append(obj)

            if not plugin_classes:
                self.logger.warning(f"No plugin classes found in module {module_name}")
                self.load_stats["skipped"] += 1
                return None

            # Load first plugin class found
            plugin_class = plugin_classes[0]

            # Create plugin instance to get info
            temp_config = config or PluginConfig()
            plugin_instance = plugin_class(temp_config, self.api)
            plugin_info = plugin_instance.plugin_info

            # Validate plugin
            await self._validate_plugin(plugin_instance)

            # Register plugin
            self.registry.register_plugin(plugin_class, plugin_info)

            if config:
                self.registry.set_plugin_config(plugin_info.id, config)

            self.load_stats["loaded"] += 1
            self.logger.info(
                f"Successfully loaded plugin: {plugin_info.name} ({plugin_info.id})"
            )

            return plugin_info.id

        except Exception as e:
            self.load_stats["failed"] += 1
            error_msg = f"Failed to load plugin from module {module_name}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            raise PluginLoadError(error_msg)

    async def load_plugins_from_directory(
        self, directory: str, config_map: Dict[str, PluginConfig] = None
    ) -> List[str]:
        """
        Load all plugins from a directory.

        Args:
            directory: Directory path to search
            config_map: Optional mapping of plugin IDs to configurations

        Returns:
            List of successfully loaded plugin IDs
        """
        config_map = config_map or {}
        loaded_plugins = []

        # Discover plugins in directory
        plugin_files = await self.discover_plugins([directory])

        # Load each plugin
        for file_path in plugin_files:
            try:
                # Determine config - first try by filename, then use default
                file_stem = Path(file_path).stem
                config = config_map.get(file_stem)

                plugin_id = await self.load_plugin_from_file(file_path, config)
                if plugin_id:
                    loaded_plugins.append(plugin_id)

            except Exception as e:
                self.logger.error(f"Error loading plugin from {file_path}: {e}")

        self.logger.info(f"Loaded {len(loaded_plugins)} plugins from {directory}")
        return loaded_plugins

    async def initialize_plugin(self, plugin_id: str) -> None:
        """
        Initialize a loaded plugin.

        Args:
            plugin_id: Plugin ID to initialize
        """
        plugin_class = self.registry.get_plugin_class(plugin_id)
        if not plugin_class:
            raise PluginLoadError(f"Plugin {plugin_id} not found in registry")

        # Check dependencies
        missing_deps = self.registry.validate_dependencies(plugin_id)
        if missing_deps:
            raise PluginDependencyError(
                f"Plugin {plugin_id} has missing dependencies: {missing_deps}",
                plugin_id,
                missing_deps,
            )

        # Get configuration
        config = self.registry.get_plugin_config(plugin_id) or PluginConfig()

        try:
            # Create plugin instance
            plugin_instance = plugin_class(config, self.api)
            plugin_instance.status = PluginStatus.LOADING

            # Store instance in registry
            self.registry.set_plugin_instance(plugin_id, plugin_instance)

            # Initialize plugin
            await plugin_instance.initialize()
            plugin_instance.status = PluginStatus.LOADED

            self.logger.info(f"Successfully initialized plugin: {plugin_id}")

        except Exception as e:
            error_msg = f"Failed to initialize plugin {plugin_id}: {str(e)}"
            self.logger.error(error_msg)

            # Clean up failed instance
            self.registry.remove_plugin_instance(plugin_id)

            raise PluginLoadError(error_msg, plugin_id)

    async def initialize_all_plugins(self) -> List[str]:
        """
        Initialize all loaded plugins in dependency order.

        Returns:
            List of successfully initialized plugin IDs
        """
        initialized = []
        load_order = self.registry.get_load_order()

        for plugin_id in load_order:
            try:
                await self.initialize_plugin(plugin_id)
                initialized.append(plugin_id)
            except Exception as e:
                self.logger.error(f"Failed to initialize plugin {plugin_id}: {e}")

        self.logger.info(f"Initialized {len(initialized)} plugins")
        return initialized

    async def unload_plugin(self, plugin_id: str) -> None:
        """
        Unload a plugin and clean up resources.

        Args:
            plugin_id: Plugin ID to unload
        """
        plugin_instance = self.registry.get_plugin_instance(plugin_id)

        if plugin_instance:
            try:
                # Deactivate if active
                if plugin_instance.status == PluginStatus.ACTIVE:
                    await plugin_instance.deactivate()

                # Clean up
                await plugin_instance.cleanup()
                plugin_instance.status = PluginStatus.UNLOADED

            except Exception as e:
                self.logger.error(f"Error during plugin cleanup for {plugin_id}: {e}")

            # Remove from registry
            self.registry.remove_plugin_instance(plugin_id)

        self.logger.info(f"Unloaded plugin: {plugin_id}")

    async def reload_plugin(self, plugin_id: str) -> None:
        """
        Reload a plugin.

        Args:
            plugin_id: Plugin ID to reload
        """
        plugin_info = self.registry.get_plugin_info(plugin_id)
        if not plugin_info:
            raise PluginLoadError(f"Plugin {plugin_id} not found")

        if not plugin_info.supports_hot_reload:
            raise PluginLoadError(f"Plugin {plugin_id} does not support hot reload")

        # Unload current instance
        await self.unload_plugin(plugin_id)

        # Reinitialize
        await self.initialize_plugin(plugin_id)

        self.logger.info(f"Reloaded plugin: {plugin_id}")

    def get_load_statistics(self) -> Dict[str, Any]:
        """Get plugin loading statistics."""
        return self.load_stats.model_copy()

    async def _security_check_file(self, file_path: str) -> None:
        """Perform security check on plugin file."""
        if not self.security_enabled:
            return

        # Check if file is in allowed paths
        file_obj = Path(file_path)

        # Basic file safety checks
        if not file_obj.exists():
            raise PluginSecurityError(f"Plugin file does not exist: {file_path}")

        if not file_obj.is_file():
            raise PluginSecurityError(f"Plugin path is not a file: {file_path}")

        # Check file size (prevent loading extremely large files)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_obj.stat().st_size > max_size:
            raise PluginSecurityError(f"Plugin file too large: {file_path}")

        # Signature verification
        await self._verify_plugin_signature(file_obj)
        
        # Content scanning for malicious patterns
        await self._scan_plugin_content(file_obj)

    async def _security_check_module(self, module_name: str) -> None:
        """Perform security check on module name."""
        if not self.security_enabled:
            return

        # Check blocked modules
        if module_name in self.blocked_modules:
            raise PluginSecurityError(f"Module {module_name} is blocked")

        # Check allowed modules (if whitelist is configured)
        if self.allowed_modules and module_name not in self.allowed_modules:
            raise PluginSecurityError(f"Module {module_name} is not in allowed list")

        # Check for potentially dangerous module names
        dangerous_patterns = ["os", "sys", "subprocess", "importlib", "__builtins__"]
        for pattern in dangerous_patterns:
            if pattern in module_name:
                self.logger.warning(
                    f"Loading potentially dangerous module: {module_name}"
                )

    async def _validate_plugin(self, plugin_instance: BasePlugin) -> None:
        """Validate plugin instance before registration."""
        plugin_info = plugin_instance.plugin_info

        # Validate plugin info
        if not plugin_info.id:
            raise PluginConfigError("Plugin ID cannot be empty")

        if not plugin_info.name:
            raise PluginConfigError("Plugin name cannot be empty")

        if not plugin_info.version:
            raise PluginConfigError("Plugin version cannot be empty")

        # Validate plugin class implements required methods
        required_methods = ["initialize", "activate", "deactivate", "cleanup"]
        for method_name in required_methods:
            method = getattr(plugin_instance, method_name, None)
            if not method or not callable(method):
                raise PluginConfigError(f"Plugin must implement {method_name} method")

        # Validate configuration if present
        if hasattr(plugin_instance, "config"):
            if not await plugin_instance.validate_config(plugin_instance.config):
                raise PluginConfigError("Plugin configuration validation failed")

        self.logger.debug(f"Plugin validation passed: {plugin_info.name}")

    async def _verify_plugin_signature(self, file_obj: Path) -> None:
        """Verify plugin file signature if signature verification is enabled."""
        if not self.security_enabled:
            return
        
        # Look for signature file
        signature_file = file_obj.with_suffix(file_obj.suffix + '.sig')
        if not signature_file.exists():
            self.logger.warning(f"No signature file found for plugin: {file_obj}")
            return
        
        try:
            # Read plugin content
            with open(file_obj, 'rb') as f:
                plugin_content = f.read()
            
            # Read signature
            with open(signature_file, 'r') as f:
                signature = f.read().strip()
            
            # For basic implementation, we'll use HMAC with a shared secret
            # In production, this should use proper digital signatures (RSA/ECDSA)
            secret_key = os.getenv('PLUGIN_SIGNATURE_SECRET', 'default-secret-key')
            expected_signature = hmac.new(
                secret_key.encode(),
                plugin_content,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise PluginSecurityError(f"Invalid signature for plugin: {file_obj}")
                
            self.logger.debug(f"Plugin signature verified: {file_obj}")
            
        except Exception as e:
            raise PluginSecurityError(f"Signature verification failed for {file_obj}: {e}")

    async def _scan_plugin_content(self, file_obj: Path) -> None:
        """Scan plugin content for malicious patterns."""
        if not self.security_enabled:
            return
        
        try:
            with open(file_obj, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            raise PluginSecurityError(f"Failed to read plugin content: {e}")
        
        # Define suspicious patterns that could indicate malicious code
        suspicious_patterns = [
            # System execution patterns
            r'subprocess\s*\.\s*(call|run|Popen)',
            r'os\s*\.\s*(system|popen|exec)',
            r'eval\s*\(',
            r'exec\s*\(',
            
            # Network patterns
            r'socket\s*\.\s*socket',
            r'urllib\s*\.\s*request',
            r'requests\s*\.\s*(get|post)',
            
            # File system patterns (overly broad access)
            r'open\s*\(\s*[\'\"]/.*[\'\"]\s*,\s*[\'\"](w|a)',  # Writing to absolute paths
            r'shutil\s*\.\s*(rmtree|copyfile)',
            r'os\s*\.\s*(remove|unlink|rmdir)',
            
            # Import patterns
            r'__import__\s*\(',
            r'importlib\s*\.\s*import_module',
            
            # Obfuscation patterns
            r'base64\s*\.\s*decode',
            r'chr\s*\(\s*\d+\s*\)',  # Character encoding
            r'bytes\s*\.\s*fromhex',
        ]
        
        found_patterns = []
        for pattern in suspicious_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_patterns.extend([(pattern, match) for match in matches])
        
        if found_patterns:
            self.logger.warning(
                f"Suspicious patterns found in plugin {file_obj}: {found_patterns}"
            )
            
            # For now, we'll log warnings. In stricter environments, 
            # this could raise PluginSecurityError
            # Uncomment the following line for stricter security:
            # raise PluginSecurityError(f"Malicious patterns detected in {file_obj}")
        
        # Check for excessive privilege requirements
        privilege_patterns = [
            r'require.*root',
            r'sudo',
            r'administrator',
            r'system.*privileges',
        ]
        
        for pattern in privilege_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.logger.warning(
                    f"Plugin {file_obj} may require elevated privileges: {pattern}"
                )
        
        self.logger.debug(f"Plugin content scan completed: {file_obj}")
