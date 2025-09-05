"""
Base plugin classes and interfaces for the DotMac Management Platform.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from inspect import iscoroutine
from typing import Any, Optional
from uuid import UUID

from dotmac_shared.exceptions import ExceptionContext

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Types of plugins supported by the platform."""

    MONITORING_PROVIDER = "monitoring_provider"
    DEPLOYMENT_PROVIDER = "deployment_provider"
    NOTIFICATION_CHANNEL = "notification_channel"
    PAYMENT_PROVIDER = "payment_provider"
    BILLING_CALCULATOR = "billing_calculator"
    SECURITY_SCANNER = "security_scanner"
    BACKUP_PROVIDER = "backup_provider"
    ANALYTICS_PROVIDER = "analytics_provider"
    DNS_PROVIDER = "dns_provider"
    INFRASTRUCTURE_PROVIDER = "infrastructure_provider"


class PluginStatus(str, Enum):
    """Plugin execution status."""

    LOADING = "loading"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMeta:
    """Plugin metadata and configuration."""

    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str
    dependencies: list[str] = field(default_factory=list)
    min_platform_version: str = "1.0.0"
    max_platform_version: Optional[str] = None
    configuration_schema: dict[str, Any] = field(default_factory=dict)
    supported_features: list[str] = field(default_factory=list)
    requires_license: bool = False
    license_tier: Optional[str] = None


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.plugin_name = plugin_name
        self.error_code = error_code
        super().__init__(self.message)


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""

    pass


class PluginExecutionError(PluginError):
    """Raised when plugin execution fails."""

    pass


class PluginConfigurationError(PluginError):
    """Raised when plugin configuration is invalid."""

    pass


class BasePlugin(ABC):
    """Base class for all management platform plugins."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self.status = PluginStatus.LOADING
        self.last_error: Optional[Exception] = None
        self._logger = logging.getLogger(f"plugin.{self.meta.name}")

    @property
    @abstractmethod
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass

    @abstractmethod
    async def validate_configuration(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration. Return True if valid."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform health check. Return status and details."""
        pass

    async def shutdown(self) -> bool:
        """Shutdown the plugin cleanly. Return True if successful."""
        try:
            self.status = PluginStatus.INACTIVE
            self._logger.info(f"Plugin {self.meta.name} shutdown successfully")
            return True
        except ExceptionContext.LIFECYCLE_EXCEPTIONS as e:
            self._logger.error(f"Error shutting down plugin {self.meta.name}: {e}")
            return False

    async def get_status(self) -> dict[str, Any]:
        """Get current plugin status and health information."""
        health = await self.health_check()

        return {
            "name": self.meta.name,
            "version": self.meta.version,
            "type": self.meta.plugin_type.value,
            "status": self.status.value,
            "health": health,
            "last_error": str(self.last_error) if self.last_error else None,
            "configuration": self._get_safe_config(),
        }

    def _get_safe_config(self) -> dict[str, Any]:
        """Get configuration without sensitive data."""
        safe_config = {}
        sensitive_keys = {
            "password",
            "secret",
            "key",
            "token",
            "api_key",
            "private_key",
        }

        for key, value in self.config.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_config[key] = "***REDACTED***"
            else:
                safe_config[key] = value

        return safe_config

    def log_error(self, error: Exception, context: Optional[str] = None):
        """Log and store plugin error."""
        self.last_error = error
        self.status = PluginStatus.ERROR

        if context:
            self._logger.error(f"Plugin error in {context}: {error}")
        else:
            self._logger.error(f"Plugin error: {error}")

    def validate_tenant_context(self, tenant_id: UUID) -> bool:
        """Validate that plugin has access to tenant context."""
        if not tenant_id:
            raise PluginValidationError("Tenant context required for plugin execution")
        return True


async def safe_plugin_call(
    callable_or_coro, *args, plugin_name: Optional[str] = None, **kwargs
) -> tuple[bool, Any, Optional[PluginError]]:
    """Safely invoke a plugin callable or awaitable, normalizing exceptions to PluginError.

    Returns (ok, result, error). Never raises; unexpected exceptions are logged via the caller's logger if provided.
    """
    try:
        if callable(callable_or_coro):
            res = callable_or_coro(*args, **kwargs)
        else:
            res = callable_or_coro

        if iscoroutine(res):
            res = await res

        return True, res, None
    except PluginError as e:
        return False, None, e
    except (
        ImportError,
        SyntaxError,
        AttributeError,
        TypeError,
        OSError,
        ValueError,
    ) as e:
        return False, None, PluginExecutionError(str(e))
    except Exception as e:  # noqa: BLE001 - normalization boundary for plugin calls
        # The calling site is expected to log context; we normalize to a PluginExecutionError
        return False, None, PluginExecutionError(str(e))


class PluginCapability(ABC):
    """Base class for plugin capabilities."""

    @abstractmethod
    def get_capability_name(self) -> str:
        """Return the name of this capability."""
        pass

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the capability with given context."""
        pass


class EventBasedPlugin(BasePlugin):
    """Base class for event-driven plugins."""

    @abstractmethod
    def get_supported_events(self) -> list[str]:
        """Return list of events this plugin can handle."""
        pass

    @abstractmethod
    async def handle_event(self, event_type: str, event_data: dict[str, Any]) -> bool:
        """Handle a specific event. Return True if handled successfully."""
        pass


class AsyncPlugin(BasePlugin):
    """Base class for asynchronous background plugins."""

    @abstractmethod
    async def start_background_task(self) -> bool:
        """Start background processing. Return True if started successfully."""
        pass

    @abstractmethod
    async def stop_background_task(self) -> bool:
        """Stop background processing. Return True if stopped successfully."""
        pass

    @abstractmethod
    async def get_task_status(self) -> dict[str, Any]:
        """Get status of background tasks."""
        pass


class TenantAwarePlugin(BasePlugin):
    """Base class for plugins that need tenant context."""

    def __init__(
        self, config: Optional[dict[str, Any]] = None, tenant_id: Optional[UUID] = None
    ):
        super().__init__(config)
        self.tenant_id = tenant_id

    @abstractmethod
    async def validate_tenant_permissions(self, tenant_id: UUID) -> bool:
        """Validate that plugin can operate for this tenant."""
        pass

    def ensure_tenant_context(self):
        """Ensure tenant context is available."""
        if not self.tenant_id:
            raise PluginConfigurationError("Tenant context required but not provided")


class BillablePlugin(TenantAwarePlugin):
    """Base class for plugins that generate billable usage."""

    @abstractmethod
    async def record_usage(
        self, usage_type: str, quantity: int, metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """Record billable usage for this plugin."""
        pass

    @abstractmethod
    async def get_usage_summary(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Get usage summary for billing purposes."""
        pass

    def get_billing_category(self) -> str:
        """Return billing category for this plugin."""
        return self.meta.plugin_type.value
