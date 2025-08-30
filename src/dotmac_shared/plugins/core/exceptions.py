"""
Plugin system exceptions.

Comprehensive error handling for all plugin operations.
"""

from typing import Any, Dict, List, Optional


class PluginError(Exception):
    """Base exception for all plugin-related errors."""

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        plugin_domain: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.plugin_name = plugin_name
        self.plugin_domain = plugin_domain
        self.context = context or {}

        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.args[0]]

        if self.plugin_name:
            parts.append(f"Plugin: {self.plugin_name}")

        if self.plugin_domain:
            parts.append(f"Domain: {self.plugin_domain}")

        if self.context:
            parts.append(f"Context: {self.context}")

        return " | ".join(parts)


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin cannot be found."""

    def __init__(
        self,
        plugin_name: str,
        domain: Optional[str] = None,
        available_plugins: Optional[List[str]] = None,
    ):
        message = f"Plugin '{plugin_name}' not found"
        if domain:
            message += f" in domain '{domain}'"

        context = {}
        if available_plugins:
            context["available_plugins"] = available_plugins

        super().__init__(
            message, plugin_name=plugin_name, plugin_domain=domain, context=context
        )


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies cannot be resolved."""

    def __init__(
        self,
        plugin_name: str,
        missing_dependencies: List[str],
        circular_dependencies: Optional[List[str]] = None,
    ):
        message = f"Dependency resolution failed for plugin '{plugin_name}'"

        context = {"missing_dependencies": missing_dependencies}

        if circular_dependencies:
            context["circular_dependencies"] = circular_dependencies
            message += " (circular dependency detected)"

        super().__init__(message, plugin_name=plugin_name, context=context)


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""

    def __init__(
        self,
        plugin_name: str,
        validation_errors: List[str],
        field_name: Optional[str] = None,
    ):
        if field_name:
            message = (
                f"Validation failed for field '{field_name}' in plugin '{plugin_name}'"
            )
        else:
            message = f"Validation failed for plugin '{plugin_name}'"

        context = {"validation_errors": validation_errors, "field_name": field_name}

        super().__init__(message, plugin_name=plugin_name, context=context)


class PluginConfigError(PluginError):
    """Raised when plugin configuration is invalid."""

    def __init__(
        self,
        plugin_name: str,
        config_path: Optional[str] = None,
        config_errors: Optional[List[str]] = None,
        original_error: Optional[Exception] = None,
    ):
        message = f"Configuration error in plugin '{plugin_name}'"
        if config_path:
            message += f" at path '{config_path}'"

        context = {}
        if config_errors:
            context["config_errors"] = config_errors
        if original_error:
            context["original_error"] = str(original_error)

        super().__init__(message, plugin_name=plugin_name, context=context)


class PluginLoadError(PluginError):
    """Raised when plugin cannot be loaded."""

    def __init__(
        self,
        plugin_name: str,
        plugin_path: Optional[str] = None,
        loader_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        message = f"Failed to load plugin '{plugin_name}'"
        if loader_type:
            message += f" using {loader_type} loader"

        context = {}
        if plugin_path:
            context["plugin_path"] = plugin_path
        if original_error:
            context["original_error"] = str(original_error)
            context["original_error_type"] = type(original_error).__name__

        super().__init__(message, plugin_name=plugin_name, context=context)


class PluginExecutionError(PluginError):
    """Raised when plugin execution fails."""

    def __init__(
        self,
        plugin_name: str,
        method_name: str,
        original_error: Optional[Exception] = None,
        execution_context: Optional[Dict[str, Any]] = None,
    ):
        message = (
            f"Execution failed for method '{method_name}' in plugin '{plugin_name}'"
        )

        context = {"method_name": method_name}

        if execution_context:
            context["execution_context"] = execution_context

        if original_error:
            context["original_error"] = str(original_error)
            context["original_error_type"] = type(original_error).__name__

        super().__init__(message, plugin_name=plugin_name, context=context)


class PluginTimeoutError(PluginError):
    """Raised when plugin operation times out."""

    def __init__(self, plugin_name: str, operation: str, timeout_seconds: float):
        message = f"Operation '{operation}' timed out after {timeout_seconds}s in plugin '{plugin_name}'"

        context = {"operation": operation, "timeout_seconds": timeout_seconds}

        super().__init__(message, plugin_name=plugin_name, context=context)


class PluginVersionError(PluginError):
    """Raised when plugin version compatibility issues occur."""

    def __init__(
        self,
        plugin_name: str,
        required_version: str,
        actual_version: str,
        compatibility_mode: Optional[str] = None,
    ):
        message = f"Version mismatch for plugin '{plugin_name}': required {required_version}, found {actual_version}"

        context = {
            "required_version": required_version,
            "actual_version": actual_version,
        }

        if compatibility_mode:
            context["compatibility_mode"] = compatibility_mode

        super().__init__(message, plugin_name=plugin_name, context=context)
