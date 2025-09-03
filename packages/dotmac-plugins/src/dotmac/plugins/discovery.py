"""
Plugin discovery system for entry points and namespace packages.

Provides automatic discovery of plugins through Python entry points and
namespace package scanning with comprehensive error handling and validation.
"""

import importlib
import logging
import pkgutil
from typing import Any, Dict, Iterator, List, Optional, Type, Union, Callable

try:
    from importlib.metadata import entry_points, EntryPoint
    IMPORTLIB_METADATA_AVAILABLE = True
except ImportError:
    try:
        from importlib_metadata import entry_points, EntryPoint
        IMPORTLIB_METADATA_AVAILABLE = True
    except ImportError:
        IMPORTLIB_METADATA_AVAILABLE = False
        entry_points = None
        EntryPoint = None

from .interfaces import IPlugin
from .types import (
    PluginError,
    PluginDiscoveryError,
    PluginRegistrationError,
)


class PluginDiscovery:
    """
    Plugin discovery system supporting entry points and namespace packages.
    
    Provides flexible plugin discovery mechanisms with validation,
    error handling, and filtering capabilities.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize plugin discovery.
        
        Args:
            logger: Optional logger instance
        """
        self._logger = logger or logging.getLogger(__name__)
        
        if not IMPORTLIB_METADATA_AVAILABLE:
            self._logger.warning(
                "importlib.metadata not available. "
                "Plugin discovery may be limited. "
                "Install importlib_metadata for Python < 3.12"
            )
    
    def discover_entry_points(
        self, 
        group: str = "dotmac.plugins",
        name_filter: Optional[Callable[[str], bool]] = None
    ) -> List[IPlugin]:
        """
        Discover plugins from entry points.
        
        Args:
            group: Entry point group to discover
            name_filter: Optional function to filter entry point names
            
        Returns:
            List of discovered plugin instances
            
        Raises:
            PluginDiscoveryError: If discovery fails
        """
        if not IMPORTLIB_METADATA_AVAILABLE:
            raise PluginDiscoveryError(
                "Entry point discovery requires importlib.metadata. "
                "Install with: pip install importlib_metadata"
            )
        
        discovered_plugins = []
        
        try:
            # Get entry points for the group
            eps = entry_points(group=group)
            
            self._logger.info(f"Discovering plugins from entry point group: {group}")
            
            for ep in eps:
                # Apply name filter if provided
                if name_filter and not name_filter(ep.name):
                    self._logger.debug(f"Skipping entry point {ep.name} (filtered)")
                    continue
                
                try:
                    plugin = self._load_entry_point(ep)
                    if plugin:
                        discovered_plugins.append(plugin)
                        
                except Exception as e:
                    self._logger.error(f"Failed to load entry point {ep.name}: {e}")
                    continue
            
            self._logger.info(f"Discovered {len(discovered_plugins)} plugins from entry points")
            return discovered_plugins
            
        except Exception as e:
            self._logger.error(f"Entry point discovery failed: {e}")
            raise PluginDiscoveryError(f"Entry point discovery failed: {e}") from e
    
    def discover_namespace_packages(
        self, 
        namespace: str = "dotmac_plugins",
        plugin_attr: str = "PLUGIN",
        plugin_factory_attr: str = "PLUGIN_FACTORY"
    ) -> List[IPlugin]:
        """
        Discover plugins from namespace packages.
        
        Args:
            namespace: Namespace to scan for plugins
            plugin_attr: Attribute name for plugin instances
            plugin_factory_attr: Attribute name for plugin factories
            
        Returns:
            List of discovered plugin instances
            
        Raises:
            PluginDiscoveryError: If discovery fails
        """
        discovered_plugins = []
        
        try:
            self._logger.info(f"Discovering plugins from namespace: {namespace}")
            
            # Try to import the namespace package
            try:
                namespace_module = importlib.import_module(namespace)
            except ImportError:
                self._logger.warning(f"Namespace {namespace} not found")
                return discovered_plugins
            
            # Scan for submodules
            if hasattr(namespace_module, '__path__'):
                for module_info in pkgutil.iter_modules(namespace_module.__path__, f"{namespace}."):
                    module_name = module_info.name
                    
                    try:
                        plugin = self._load_namespace_module(
                            module_name, 
                            plugin_attr, 
                            plugin_factory_attr
                        )
                        if plugin:
                            discovered_plugins.append(plugin)
                            
                    except Exception as e:
                        self._logger.error(f"Failed to load namespace module {module_name}: {e}")
                        continue
            
            self._logger.info(f"Discovered {len(discovered_plugins)} plugins from namespace packages")
            return discovered_plugins
            
        except Exception as e:
            self._logger.error(f"Namespace package discovery failed: {e}")
            raise PluginDiscoveryError(f"Namespace package discovery failed: {e}") from e
    
    def discover_all(
        self,
        entry_point_group: str = "dotmac.plugins",
        namespace: str = "dotmac_plugins",
        enable_entry_points: bool = True,
        enable_namespace: bool = True,
        deduplicate: bool = True
    ) -> List[IPlugin]:
        """
        Discover plugins using all available methods.
        
        Args:
            entry_point_group: Entry point group for discovery
            namespace: Namespace package for discovery  
            enable_entry_points: Whether to use entry point discovery
            enable_namespace: Whether to use namespace discovery
            deduplicate: Whether to remove duplicate plugins by name
            
        Returns:
            List of all discovered plugins
        """
        all_plugins = []
        
        # Entry point discovery
        if enable_entry_points:
            try:
                ep_plugins = self.discover_entry_points(entry_point_group)
                all_plugins.extend(ep_plugins)
            except PluginDiscoveryError as e:
                self._logger.warning(f"Entry point discovery failed: {e}")
        
        # Namespace discovery  
        if enable_namespace:
            try:
                ns_plugins = self.discover_namespace_packages(namespace)
                all_plugins.extend(ns_plugins)
            except PluginDiscoveryError as e:
                self._logger.warning(f"Namespace discovery failed: {e}")
        
        # Deduplicate by name if requested
        if deduplicate:
            all_plugins = self._deduplicate_plugins(all_plugins)
        
        self._logger.info(f"Total discovered plugins: {len(all_plugins)}")
        return all_plugins
    
    def _load_entry_point(self, entry_point: "EntryPoint") -> Optional[IPlugin]:
        """Load plugin from entry point."""
        try:
            self._logger.debug(f"Loading entry point: {entry_point.name}")
            
            # Load the entry point
            plugin_factory = entry_point.load()
            
            # Create plugin instance
            if isinstance(plugin_factory, type):
                # Entry point is a class
                if issubclass(plugin_factory, IPlugin):
                    plugin = plugin_factory()
                else:
                    self._logger.error(
                        f"Entry point {entry_point.name} class does not implement IPlugin"
                    )
                    return None
            elif callable(plugin_factory):
                # Entry point is a factory function
                plugin = plugin_factory()
                if not isinstance(plugin, IPlugin):
                    self._logger.error(
                        f"Entry point {entry_point.name} factory did not return IPlugin instance"
                    )
                    return None
            elif isinstance(plugin_factory, IPlugin):
                # Entry point is already a plugin instance
                plugin = plugin_factory
            else:
                self._logger.error(
                    f"Entry point {entry_point.name} is not a plugin class, factory, or instance"
                )
                return None
            
            # Validate plugin
            self._validate_plugin_basic(plugin, f"entry point {entry_point.name}")
            
            self._logger.debug(f"Successfully loaded plugin {plugin.name} from entry point")
            return plugin
            
        except Exception as e:
            self._logger.error(f"Failed to load entry point {entry_point.name}: {e}")
            return None
    
    def _load_namespace_module(
        self, 
        module_name: str, 
        plugin_attr: str, 
        plugin_factory_attr: str
    ) -> Optional[IPlugin]:
        """Load plugin from namespace module."""
        try:
            self._logger.debug(f"Loading namespace module: {module_name}")
            
            # Import the module
            module = importlib.import_module(module_name)
            
            # Try plugin instance first
            if hasattr(module, plugin_attr):
                plugin = getattr(module, plugin_attr)
                if isinstance(plugin, IPlugin):
                    self._validate_plugin_basic(plugin, f"namespace module {module_name}")
                    self._logger.debug(f"Loaded plugin {plugin.name} from {module_name}.{plugin_attr}")
                    return plugin
                else:
                    self._logger.error(f"{module_name}.{plugin_attr} is not an IPlugin instance")
            
            # Try plugin factory
            if hasattr(module, plugin_factory_attr):
                factory = getattr(module, plugin_factory_attr)
                if callable(factory):
                    try:
                        plugin = factory()
                        if isinstance(plugin, IPlugin):
                            self._validate_plugin_basic(plugin, f"namespace module {module_name}")
                            self._logger.debug(f"Created plugin {plugin.name} from {module_name}.{plugin_factory_attr}")
                            return plugin
                        else:
                            self._logger.error(f"{module_name}.{plugin_factory_attr}() did not return IPlugin")
                    except Exception as e:
                        self._logger.error(f"Error calling {module_name}.{plugin_factory_attr}(): {e}")
                else:
                    self._logger.error(f"{module_name}.{plugin_factory_attr} is not callable")
            
            self._logger.warning(f"No valid plugin found in {module_name}")
            return None
            
        except ImportError as e:
            self._logger.error(f"Failed to import namespace module {module_name}: {e}")
            return None
        except Exception as e:
            self._logger.error(f"Error loading namespace module {module_name}: {e}")
            return None
    
    def _validate_plugin_basic(self, plugin: IPlugin, source: str) -> None:
        """Basic plugin validation."""
        if not isinstance(plugin, IPlugin):
            raise PluginDiscoveryError(f"Plugin from {source} does not implement IPlugin interface")
        
        if not hasattr(plugin, 'name') or not plugin.name:
            raise PluginDiscoveryError(f"Plugin from {source} has no name")
        
        if not hasattr(plugin, 'version') or not plugin.version:
            raise PluginDiscoveryError(f"Plugin from {source} has no version")
        
        if not hasattr(plugin, 'kind'):
            raise PluginDiscoveryError(f"Plugin from {source} has no kind")
    
    def _deduplicate_plugins(self, plugins: List[IPlugin]) -> List[IPlugin]:
        """Remove duplicate plugins by name, keeping the first occurrence."""
        seen_names = set()
        unique_plugins = []
        
        for plugin in plugins:
            if plugin.name not in seen_names:
                unique_plugins.append(plugin)
                seen_names.add(plugin.name)
            else:
                self._logger.warning(f"Duplicate plugin '{plugin.name}' found and skipped")
        
        return unique_plugins


# Convenience functions for common discovery patterns

def discover_plugins(
    entry_point_group: str = "dotmac.plugins",
    namespace: str = "dotmac_plugins", 
    logger: Optional[logging.Logger] = None
) -> List[IPlugin]:
    """
    Discover plugins using default settings.
    
    Args:
        entry_point_group: Entry point group to discover
        namespace: Namespace package to discover
        logger: Optional logger instance
        
    Returns:
        List of discovered plugins
    """
    discovery = PluginDiscovery(logger=logger)
    return discovery.discover_all(
        entry_point_group=entry_point_group,
        namespace=namespace
    )


def discover_entry_points_only(
    group: str = "dotmac.plugins",
    logger: Optional[logging.Logger] = None
) -> List[IPlugin]:
    """
    Discover plugins from entry points only.
    
    Args:
        group: Entry point group to discover
        logger: Optional logger instance
        
    Returns:
        List of discovered plugins
    """
    discovery = PluginDiscovery(logger=logger)
    return discovery.discover_entry_points(group)


def discover_namespace_only(
    namespace: str = "dotmac_plugins",
    logger: Optional[logging.Logger] = None
) -> List[IPlugin]:
    """
    Discover plugins from namespace packages only.
    
    Args:
        namespace: Namespace to discover
        logger: Optional logger instance
        
    Returns:
        List of discovered plugins
    """
    discovery = PluginDiscovery(logger=logger)
    return discovery.discover_namespace_packages(namespace)


def create_plugin_factory(plugin_class: Type[IPlugin]) -> Callable[[], IPlugin]:
    """
    Create a plugin factory function from a plugin class.
    
    Useful for creating entry points that instantiate plugin classes.
    
    Args:
        plugin_class: Plugin class to create factory for
        
    Returns:
        Factory function that creates plugin instances
        
    Example:
        # In setup.py or pyproject.toml entry points:
        "my_plugin = my_package.plugins:create_plugin_factory(MyPlugin)"
    """
    def factory() -> IPlugin:
        return plugin_class()
    
    factory.__name__ = f"{plugin_class.__name__}_factory"
    factory.__doc__ = f"Factory function for {plugin_class.__name__} plugin"
    
    return factory


def validate_plugin_requirements(plugin: IPlugin) -> List[str]:
    """
    Validate plugin meets basic requirements.
    
    Args:
        plugin: Plugin to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check interface implementation
    if not isinstance(plugin, IPlugin):
        errors.append("Plugin does not implement IPlugin interface")
    
    # Check required attributes
    required_attrs = {
        'name': str,
        'version': str, 
        'kind': object,  # PluginKind enum
        'metadata': object,
    }
    
    for attr, expected_type in required_attrs.items():
        if not hasattr(plugin, attr):
            errors.append(f"Plugin missing required attribute: {attr}")
        elif expected_type == str and not isinstance(getattr(plugin, attr), str):
            errors.append(f"Plugin {attr} must be string")
        elif expected_type == str and not getattr(plugin, attr).strip():
            errors.append(f"Plugin {attr} cannot be empty")
    
    # Check required methods
    required_methods = ['init', 'start', 'stop']
    for method in required_methods:
        if not hasattr(plugin, method) or not callable(getattr(plugin, method)):
            errors.append(f"Plugin missing required method: {method}")
    
    return errors