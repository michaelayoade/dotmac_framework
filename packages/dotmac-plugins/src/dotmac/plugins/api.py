"""
Public API re-exports for dotmac-plugins.

This module provides a clean public API surface by re-exporting
the most commonly used classes and functions from the plugin system.
"""

# Re-export everything from __init__ for API compatibility
from . import *

# Explicit re-exports for documentation and IDE support
from .registry import PluginRegistry
from .lifecycle import PluginLifecycleManager
from .context import PluginContext
from .metadata import PluginMetadata, Version, Author
from .interfaces import (
    IPlugin,
    IExportPlugin,
    IDeploymentProvider,
    IDNSProvider,
    IObserver,
)
from .types import PluginKind, PluginStatus
from .discovery import discover_plugins

# Try to re-export optional components
try:
    from .interfaces import IRouterPlugin
except ImportError:
    pass

try:
    from .signing import PluginSignatureVerifier, PluginSigner
except ImportError:
    pass

try:
    from .sandbox import PluginSandbox, SecurityPolicy
except ImportError:
    pass

# Version information
__version__ = "1.0.0"
__author__ = "DotMac Framework Team"
__email__ = "support@dotmac-framework.com"

# Package metadata for external tools
PACKAGE_INFO = {
    "name": "dotmac-plugins",
    "version": __version__,
    "description": "Standalone plugin system for DotMac Framework",
    "author": __author__,
    "author_email": __email__,
    "license": "MIT",
    "python_requires": ">=3.10",
}

# API compatibility matrix
SUPPORTED_PLUGIN_API_VERSIONS = ["1.0.0"]
CURRENT_API_VERSION = "1.0.0"

def get_api_version() -> str:
    """Get current plugin API version."""
    return CURRENT_API_VERSION

def is_api_compatible(plugin_api_version: str) -> bool:
    """
    Check if plugin API version is compatible.
    
    Args:
        plugin_api_version: Plugin's declared API version
        
    Returns:
        True if API versions are compatible
    """
    return plugin_api_version in SUPPORTED_PLUGIN_API_VERSIONS