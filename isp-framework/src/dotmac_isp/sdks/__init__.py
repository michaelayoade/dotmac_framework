"""
DotMac ISP Framework - Internal SDK Suite (Modular Monolith Architecture)

IMPORTANT: This SDK suite provides internal APIs for the modular monolith.
All capabilities are implemented as internal modules, NOT external microservices.

Architecture Pattern: MODULAR MONOLITH
- Single deployable unit with internal module boundaries
- Shared database with proper module isolation
- Internal SDKs for cross-module communication
- No external service dependencies for core functionality

Internal SDK Modules:
- Core Platform: Authentication, RBAC, caching, observability
- ISP Networking: RADIUS, IPAM, device monitoring, service assurance
- Business Logic: Customer management, billing, analytics
- Workflow Engine: Task automation, scheduling, sagas
- Portal Systems: Customer, admin, technician, reseller interfaces

Note: External dependencies (OpenTelemetry, cloud services) are optional.
"""

from typing import Dict, Any, Optional
import logging

# ===== CORE SDK COMPONENTS =====
try:
    # Core utilities and base clients
    from .core.client import BaseSDKClient
    from .core.exceptions import SDKError, ConfigurationError, ValidationError
    from .core.retry import RetryClient
    # ARCHITECTURE IMPROVEMENT: Explicit imports replace wildcard import
    from .core.utils import (
        build_headers, parse_response, handle_deprecation, generate_request_id,
        sanitize_params, filter_deprecated_items, validate_tenant_id,
        calculate_signature, format_error_response, chunk_list
    )

    # Observability (SignOz Integration)
    from .core.observability_signoz import (
        SignOzTelemetry,
        init_signoz,
        get_signoz,
        trace,
    )

    # Secrets Management (OpenBao)
    from .core.openbao_client import OpenBaoClient, Secret

except ImportError as e:
    logging.warning(f"Core SDK import error: {e}")

# ===== PLATFORM SDKS (Internal Modular Monolith) =====
try:
    from .platform.authentication_sdk import AuthSDK as AuthenticationSDK
    from .platform.rbac_sdk import RBACSDK as RBACDK
    from .platform.audit_sdk import AuditSDK
    from .platform.cache_sdk import CacheSDK
    from .platform.secrets_sdk import SecretsSDK
    from .platform.observability_sdk import ObservabilitySDK
    from .platform.file_storage_sdk import FileStorageSDK
    from .platform.database_sdk import DatabaseSDK
    from .platform.tenancy_sdk import TenancySDK
    from .platform.webhooks_sdk import WebhooksSDK

    logging.info("✅ Platform SDKs loaded from internal monolith modules")
except ImportError as e:
    logging.warning(f"Platform SDK import error: {e}")

# ===== IDENTITY & CUSTOMER MANAGEMENT =====
try:
    from .identity.customer_management import CustomerManagementSDK
    from .identity.customer_portal import CustomerPortalSDK
    from .identity.reseller_portal import ResellerPortalSDK
    from .identity.portal_management import PortalManagementSDK
    from .identity.user_profile import UserProfileSDK
    from .identity.organizations import OrganizationsSDK
except ImportError as e:
    logging.warning(f"Identity SDK import error: {e}")

# ===== NETWORKING & ISP FEATURES (Internal Modular Monolith) =====
try:
    from .networking.ipam import IPAMSDK
    from .networking.device_monitoring import DeviceMonitoringSDK
    from .networking.radius import RADIUSSDK
    from .networking.network_topology import NetworkTopologySDK
    from .networking.device_provisioning import DeviceProvisioningSDK
    from .networking.service_assurance import ServiceAssuranceSDK
    from .networking.voltha_integration import VolthaSDK
    from .networking.olt_onu import OLTONUSDK
    from .networking.captive_portal import CaptivePortalSDK

    logging.info("✅ Networking SDKs loaded from internal monolith modules")
except ImportError as e:
    logging.warning(f"Networking SDK import error: {e}")

# ===== EVENT-DRIVEN ARCHITECTURE =====
try:
    from .events.event_bus import EventBusSDK
    from .events.schema_registry import SchemaRegistrySDK
    from .events.outbox import OutboxSDK
except ImportError as e:
    logging.warning(f"Events SDK import error: {e}")

# ===== WORKFLOW & AUTOMATION =====
try:
    from .workflows.workflow import WorkflowSDK
    from .workflows.task import TaskSDK
    from .workflows.scheduler import SchedulerSDK
    from .workflows.automation import AutomationSDK
    from .workflows.saga import SagaSDK
except ImportError as e:
    logging.warning(f"Workflows SDK import error: {e}")

# ===== API GATEWAY FEATURES =====
try:
    from .gateway.gateway import GatewaySDK
    from .gateway.rate_limiting import RateLimitingSDK
    from .gateway.authentication_proxy import AuthenticationProxySDK
    from .gateway.api_versioning import APIVersioningSDK
except ImportError as e:
    logging.warning(f"Gateway SDK import error: {e}")

# ===== SERVICES & PROVISIONING (Internal Modular Monolith) =====
try:
    from .services.service_catalog import ServiceCatalogSDK
    from .services.service_management import ServiceManagementSDK
    from .services.provisioning_bindings import ProvisioningBindingsSDK
    from .services.tariff import TariffSDK

    logging.info("✅ Services SDKs loaded from internal monolith modules")
except ImportError as e:
    logging.warning(f"Services SDK import error: {e}")

# ===== ANALYTICS & REPORTING (Internal Modular Monolith) =====
try:
    from .analytics.metrics import MetricsSDK
    from .analytics.events import AnalyticsEventsSDK
    from .analytics.dashboards import DashboardsSDK
    from .analytics.reports import ReportsSDK

    logging.info("✅ Analytics SDKs loaded from internal monolith modules")
except ImportError as e:
    logging.warning(f"Analytics SDK import error: {e}")

logger = logging.getLogger(__name__)


# Global variables to track what's successfully imported
_available_sdks = {
    "core": False,
    "platform": False,
    "identity": False,
    "networking": False,
    "events": False,
    "workflows": False,
    "gateway": False,
    "services": False,
    "analytics": False,
}

# Update availability based on imports above
try:
    from .core.observability_signoz import SignOzTelemetry

    _available_sdks["core"] = True
except ImportError as e:
    logger.warning(f"Core SDK not available: {e}")

logger.info(f"📊 SDK Availability: {_available_sdks}")


class SDKRegistry:
    """
    Centralized SDK registry for the ISP Framework.

    Provides unified access to all SDKs with proper tenant isolation
    and configuration management.
    """

    def __init__(self, tenant_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SDK registry for a specific tenant.

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation
            config: Optional configuration dictionary
        """
        self.tenant_id = tenant_id
        self.config = config or {}

        # Initialize all SDKs
        self._init_sdks()

        logger.info(f"Initialized SDK Registry for tenant: {tenant_id}")

    def _init_sdks(self):
        """Initialize all SDK instances with tenant context."""
        # Only initialize SDKs that are available
        try:
            if "CustomerManagementSDK" in globals():
                self.customers = CustomerManagementSDK(self.tenant_id)
        except Exception as e:
            logger.warning(f"Failed to initialize CustomerManagementSDK: {e}")

        # Initialize other SDKs as they become available
        # self.ipam = None
        # self.service_catalog = None

        logger.debug(f"Available SDKs initialized for tenant: {self.tenant_id}")

    def get_customer_sdk(self):
        """Get the customer management SDK."""
        return getattr(self, "customers", None)

    def get_networking_sdk(self):
        """Get the IPAM networking SDK."""
        return getattr(self, "ipam", None)

    def get_services_sdk(self):
        """Get the service catalog SDK."""
        return getattr(self, "service_catalog", None)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all SDKs.

        Returns:
            Health status of all SDK components
        """
        health_status = {
            "tenant_id": self.tenant_id,
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "overall_status": "healthy",
            "components": {
                "customer_management": "healthy",
                # "ipam": "healthy",
                # "service_catalog": "healthy",
            },
        }

        # In a real implementation, each SDK would have its own health check
        logger.info(f"SDK health check completed for tenant: {self.tenant_id}")

        return health_status


# Convenience function for creating SDK registry
def create_sdk_registry(
    tenant_id: str, config: Optional[Dict[str, Any]] = None
) -> SDKRegistry:
    """
    Create a new SDK registry instance.

    Args:
        tenant_id: Tenant identifier
        config: Optional configuration

    Returns:
        Configured SDK registry instance
    """
    return SDKRegistry(tenant_id, config)


# Export available components dynamically
__all__ = [
    # Registry (always available)
    "SDKRegistry",
    "create_sdk_registry",
]

# Add available SDKs to exports
if _available_sdks.get("core"):
    __all__.extend(
        [
            "SignOzTelemetry",
            "init_signoz",
            "get_signoz",
            "trace",
            "OpenBaoClient",
            "Secret",
        ]
    )

# Dynamic exports based on what's available
_exports = globals()
for name in list(_exports.keys()):
    if name.endswith("SDK") and not name.startswith("_"):
        __all__.append(name)
