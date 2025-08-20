"""
DotMac Services - Service Catalog, Management, Tariff, and Provisioning Bindings
"""

# Core exports
from .core import (
    ProvisioningBindingError,
    ServiceCatalogError,
    ServiceManagementError,
    ServicesConfig,
    ServicesError,
    TariffError,
    get_config,
    reset_config,
)
from .sdks.provisioning_bindings import ProvisioningBindingsSDK, ResourceType

# SDK exports
from .sdks.service_catalog import ServiceCatalogSDK
from .sdks.service_management import ServiceManagementSDK, ServiceState
from .sdks.tariff import PolicyIntentType, PricingModel, TariffSDK

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "support@dotmac.com"

__all__ = [
    # Core
    "ServicesConfig",
    "get_config",
    "reset_config",
    # Exceptions
    "ServicesError",
    "ServiceCatalogError",
    "ServiceManagementError",
    "TariffError",
    "ProvisioningBindingError",
    # SDKs
    "ServiceCatalogSDK",
    "ServiceManagementSDK",
    "TariffSDK",
    "ProvisioningBindingsSDK",
    # Enums
    "ServiceState",
    "PricingModel",
    "PolicyIntentType",
    "ResourceType",
]
