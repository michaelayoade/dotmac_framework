"""Base Plugin Classes and Interfaces."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class PluginStatus(Enum):
    """Plugin status enumeration."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


class PluginCategory(Enum):
    """Plugin category enumeration."""

    NETWORK_AUTOMATION = "network_automation"
    GIS_LOCATION = "gis_location"
    BILLING_INTEGRATION = "billing_integration"
    CRM_INTEGRATION = "crm_integration"
    MONITORING = "monitoring"
    TICKETING = "ticketing"
    COMMUNICATION = "communication"
    REPORTING = "reporting"
    SECURITY = "security"
    CUSTOM = "custom"


@dataclass
class PluginInfo:
    """Plugin information and metadata."""

    id: str
    name: str
    version: str
    description: str
    author: str
    category: PluginCategory

    # Dependencies
    dependencies: List[str] = None
    python_requires: str = ">=3.11"

    # Capabilities
    supports_multi_tenant: bool = True
    supports_hot_reload: bool = False
    requires_restart: bool = False

    # Security
    security_level: str = "standard"  # minimal, standard, elevated, system
    permissions_required: List[str] = None

    # Lifecycle
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        """  Post Init   operation."""
        if self.dependencies is None:
            self.dependencies = []
        if self.permissions_required is None:
            self.permissions_required = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


class PluginConfig(BaseModel):
    """Plugin configuration schema."""

    enabled: bool = True
    tenant_id: Optional[UUID] = None
    priority: int = Field(default=100, ge=0, le=1000)

    # Configuration data (plugin-specific)
    config_data: Dict[str, Any] = Field(default_factory=dict)

    # Security settings
    sandbox_enabled: bool = True
    resource_limits: Dict[str, Any] = Field(default_factory=dict)

    # Monitoring
    metrics_enabled: bool = True
    logging_enabled: bool = True

    model_config = ConfigDict(extra="allow")

class PluginContext:
    """Plugin execution context."""

    def __init__(self, tenant_id: str, user_id: Optional[str] = None, request_id: Optional[str] = None):
        """Initialize operation."""
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.request_id = request_id or str(uuid4())
        self.metadata: Dict[str, Any] = {}
        self.started_at = datetime.now(timezone.utc)

    def add_metadata(self, key: str, value: Any):
        """Add metadata to context."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from context."""
        return self.metadata.get(key, default)


class PluginAPI:
    """Plugin API interface for accessing framework services."""

    def __init__(self, framework_services: Dict[str, Any]):
        """  Init   operation."""
        self._services = framework_services

    def get_service(self, service_name: str) -> Any:
        """Get framework service by name."""
        return self._services.get(service_name)

    @property
    def database(self):
        """Get database service."""
        return self.get_service("database")

    @property
    def redis(self):
        """Get Redis service."""
        return self.get_service("redis")

    @property
    def event_bus(self):
        """Get event bus service."""
        return self.get_service("event_bus")

    @property
    def logger(self):
        """Get logging service."""
        return self.get_service("logger")

    @property
    def config(self):
        """Get configuration service."""
        return self.get_service("config")


class BasePlugin(ABC):
    """
    Base class for all plugins.

    All plugins must inherit from this class and implement the required methods.
    """

    def __init__(self, config: PluginConfig, api: PluginAPI):
        """Initialize plugin with configuration and API access."""
        self.config = config
        self.api = api
        self.status = PluginStatus.UNLOADED
        self.info: Optional[PluginInfo] = None
        self._context: Optional[PluginContext] = None
        self._lock = asyncio.Lock()

    @property
    @abstractmethod
    def plugin_info(self) -> PluginInfo:
        """Return plugin information and metadata."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the plugin.

        This method is called when the plugin is first loaded.
        Use this to set up any resources, connections, or initial state.
        """
        pass

    @abstractmethod
    async def activate(self) -> None:
        """
        Activate the plugin.

        This method is called to start the plugin's active operations.
        """
        pass

    @abstractmethod
    async def deactivate(self) -> None:
        """
        Deactivate the plugin.

        This method is called to stop the plugin's active operations.
        Plugin should remain loaded but inactive.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up plugin resources.

        This method is called when the plugin is being unloaded.
        Use this to close connections, save state, and release resources.
        """
        pass

    async def validate_config(self, config: PluginConfig) -> bool:
        """
        Validate plugin configuration.

        Override this method to implement custom configuration validation.
        """
        return True

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the plugin.

        Override this method to implement custom health checks.
        """
        return {
            "status": self.status.value,
            "healthy": self.status in [PluginStatus.ACTIVE, PluginStatus.INACTIVE],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get plugin metrics.

        Override this method to provide plugin-specific metrics.
        """
        return {
            "status": self.status.value,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - self._context.started_at).total_seconds()
                if self._context
                else 0
            ),
        }

    def set_context(self, context: PluginContext):
        """Set plugin execution context."""
        self._context = context

    def get_context(self) -> Optional[PluginContext]:
        """Get current plugin execution context."""
        return self._context

    async def _safe_operation(self, operation_name: str, operation_func):
        """Execute plugin operation safely with error handling."""
        try:
            async with self._lock:
                await operation_func()
                self.api.logger.info(
                    f"Plugin {self.plugin_info.name}: {operation_name} completed successfully"
                )
        except Exception as e:
            self.status = PluginStatus.ERROR
            error_msg = (
                f"Plugin {self.plugin_info.name}: {operation_name} failed: {str(e)}"
            )
            self.api.logger.error(error_msg)
            raise

    def __repr__(self) -> str:
        """  Repr   operation."""
        return f"<{self.__class__.__name__}(name={self.plugin_info.name}, status={self.status.value})>"


class NetworkAutomationPlugin(BasePlugin):
    """Base class for network automation plugins."""

    @abstractmethod
    async def discover_devices(self, context: PluginContext) -> List[Dict[str, Any]]:
        """Discover network devices."""
        pass

    @abstractmethod
    async def configure_device(
        self, device_id: str, config: Dict[str, Any], context: PluginContext
    ) -> bool:
        """Configure a network device."""
        pass

    @abstractmethod
    async def get_device_status(
        self, device_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Get device status and metrics."""
        pass


class GISLocationPlugin(BasePlugin):
    """Base class for GIS and location plugins."""

    @abstractmethod
    async def get_device_location(
        self, device_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Get device GPS coordinates and location info."""
        pass

    @abstractmethod
    async def update_device_location(
        self, device_id: str, location: Dict[str, Any], context: PluginContext
    ) -> bool:
        """Update device location."""
        pass

    @abstractmethod
    async def get_coverage_map(
        self, area_bounds: Dict[str, Any], context: PluginContext
    ) -> Dict[str, Any]:
        """Get service coverage map for an area."""
        pass


class BillingIntegrationPlugin(BasePlugin):
    """Base class for billing integration plugins."""

    @abstractmethod
    async def create_invoice(
        self, customer_id: str, invoice_data: Dict[str, Any], context: PluginContext
    ) -> str:
        """Create invoice in external billing system."""
        pass

    @abstractmethod
    async def process_payment(
        self, payment_data: Dict[str, Any], context: PluginContext
    ) -> Dict[str, Any]:
        """Process payment through external gateway."""
        pass

    @abstractmethod
    async def sync_customer_data(
        self, customer_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Sync customer data with external billing system."""
        pass


class CRMIntegrationPlugin(BasePlugin):
    """Base class for CRM integration plugins."""

    @abstractmethod
    async def create_lead(
        self, lead_data: Dict[str, Any], context: PluginContext
    ) -> str:
        """Create lead in CRM system."""
        pass

    @abstractmethod
    async def update_customer(
        self, customer_id: str, customer_data: Dict[str, Any], context: PluginContext
    ) -> bool:
        """Update customer in CRM system."""
        pass

    @abstractmethod
    async def get_customer_history(
        self, customer_id: str, context: PluginContext
    ) -> List[Dict[str, Any]]:
        """Get customer interaction history from CRM."""
        pass


class MonitoringPlugin(BasePlugin):
    """Base class for monitoring plugins."""

    @abstractmethod
    async def collect_metrics(
        self, resource_ids: List[str], context: PluginContext
    ) -> Dict[str, Any]:
        """Collect metrics from monitored resources."""
        pass

    @abstractmethod
    async def create_alert(
        self, alert_data: Dict[str, Any], context: PluginContext
    ) -> str:
        """Create alert in monitoring system."""
        pass

    @abstractmethod
    async def get_alert_status(
        self, alert_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Get alert status and details."""
        pass


class TicketingPlugin(BasePlugin):
    """Base class for ticketing system plugins."""

    @abstractmethod
    async def create_ticket(
        self, ticket_data: Dict[str, Any], context: PluginContext
    ) -> str:
        """Create ticket in external ticketing system."""
        pass

    @abstractmethod
    async def update_ticket(
        self, ticket_id: str, update_data: Dict[str, Any], context: PluginContext
    ) -> bool:
        """Update ticket in external system."""
        pass

    @abstractmethod
    async def sync_ticket_status(
        self, ticket_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Sync ticket status from external system."""
        pass
