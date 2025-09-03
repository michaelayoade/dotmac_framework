"""
Core types and enums for the dotmac-plugins system.

Provides fundamental types used throughout the plugin system including
plugin kinds, status tracking, and custom exceptions.
"""

from enum import Enum, auto
from typing import Any, Dict


class PluginKind(str, Enum):
    """
    Enumeration of supported plugin types.
    
    Each plugin must declare its kind to enable proper categorization
    and lifecycle management within the registry.
    """
    
    EXPORT = "export"
    DEPLOYMENT = "deployment" 
    DNS = "dns"
    OBSERVER = "observer"
    ROUTER = "router"
    CUSTOM = "custom"


class PluginStatus(Enum):
    """
    Plugin lifecycle status tracking.
    
    Represents the current state of a plugin within its lifecycle,
    from initial registration through running state.
    """
    
    UNKNOWN = auto()
    REGISTERED = auto()
    INITIALIZED = auto()
    STARTED = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()
    DISABLED = auto()


# Type aliases for commonly used types
ExportResult = Dict[str, Any]
DeploymentResult = Dict[str, Any]
ValidationResult = Dict[str, Any]
PluginConfig = Dict[str, Any]
PluginCapabilities = Dict[str, Any]


class PluginError(Exception):
    """
    Base exception for all plugin-related errors.
    
    This is the root exception class that all other plugin exceptions
    inherit from. Use this for general plugin error handling.
    """
    
    def __init__(self, message: str, plugin_name: str = None):
        self.plugin_name = plugin_name
        super().__init__(message)


class PluginNotFoundError(PluginError):
    """
    Raised when a requested plugin cannot be found.
    
    Occurs during plugin lookup operations when the specified
    plugin name or kind does not exist in the registry.
    """
    pass


class PluginRegistrationError(PluginError):
    """
    Raised when plugin registration fails.
    
    This includes duplicate name registration, invalid metadata,
    or other registration-time validation failures.
    """
    pass


class PluginInitError(PluginError):
    """
    Raised when plugin initialization fails.
    
    Occurs during the init phase of plugin lifecycle when
    the plugin cannot properly initialize itself.
    """
    pass


class PluginStartError(PluginError):
    """
    Raised when plugin startup fails.
    
    Occurs during the start phase when a plugin fails to
    transition to running state.
    """
    pass


class PluginStopError(PluginError):
    """
    Raised when plugin shutdown fails.
    
    Occurs during the stop phase when a plugin cannot
    properly clean up and transition to stopped state.
    """
    pass


class PluginPermissionError(PluginError):
    """
    Raised when plugin lacks required permissions.
    
    Occurs when a plugin attempts to perform operations
    for which it lacks the necessary permissions.
    """
    pass


class PluginVersionError(PluginError):
    """
    Raised when plugin version requirements are not met.
    
    Occurs when plugin version conflicts or incompatibility
    is detected with the host system or other plugins.
    """
    pass


class PluginConfigError(PluginError):
    """
    Raised when plugin configuration is invalid.
    
    Occurs when plugin configuration validation fails
    or required configuration is missing.
    """
    pass


class PluginDependencyError(PluginError):
    """
    Raised when plugin dependencies cannot be satisfied.
    
    Occurs when required dependencies are missing or
    incompatible versions are detected.
    """
    pass


class PluginSecurityError(PluginError):
    """
    Raised when plugin security validation fails.
    
    Occurs when signature verification fails, permissions
    are insufficient, or other security constraints are violated.
    """
    pass


class PluginDiscoveryError(PluginError):
    """
    Raised when plugin discovery fails.
    
    Occurs during entry point resolution or namespace
    discovery when plugins cannot be properly loaded.
    """
    pass