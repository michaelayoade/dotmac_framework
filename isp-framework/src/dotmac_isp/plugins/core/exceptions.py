"""Plugin System Exceptions."""


class PluginError(Exception):
    """Base exception for plugin system errors."""

    def __init__(
        """  Init   operation."""
        self, message: str, plugin_name: str = None, plugin_version: str = None
    ):
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version
        super().__init__(message)

    def __str__(self):
        """  Str   operation."""
        if self.plugin_name:
            plugin_info = f" (Plugin: {self.plugin_name}"
            if self.plugin_version:
                plugin_info += f" v{self.plugin_version}"
            plugin_info += ")"
            return f"{super().__str__()}{plugin_info}"
        return super().__str__()


class PluginLoadError(PluginError):
    """Exception raised when a plugin fails to load."""

    pass


class PluginConfigError(PluginError):
    """Exception raised when plugin configuration is invalid."""

    pass


class PluginDependencyError(PluginError):
    """Exception raised when plugin dependencies cannot be resolved."""

    def __init__(
        """  Init   operation."""
        self, message: str, plugin_name: str = None, missing_dependencies: list = None
    ):
        self.missing_dependencies = missing_dependencies or []
        super().__init__(message, plugin_name)


class PluginSecurityError(PluginError):
    """Exception raised when plugin security validation fails."""

    pass


class PluginVersionError(PluginError):
    """Exception raised when plugin version requirements are not met."""

    pass


class PluginRegistrationError(PluginError):
    """Exception raised when plugin registration fails."""

    pass


class PluginLifecycleError(PluginError):
    """Exception raised during plugin lifecycle operations."""

    pass


class PluginTimeoutError(PluginError):
    """Exception raised when plugin operations timeout."""

    pass


class PluginResourceError(PluginError):
    """Exception raised when plugin resource limits are exceeded."""

    pass


class PluginCommunicationError(PluginError):
    """Exception raised when plugin communication fails."""

    pass
