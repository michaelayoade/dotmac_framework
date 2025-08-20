"""
Custom exceptions for dotmac_services.
"""


class ServicesError(Exception):
    """Base exception for services operations."""
    pass


class ServiceCatalogError(ServicesError):
    """Service catalog related errors."""
    pass


class ServiceDefinitionError(ServiceCatalogError):
    """Service definition validation errors."""
    pass


class ServicePlanError(ServiceCatalogError):
    """Service plan configuration errors."""
    pass


class BundleError(ServiceCatalogError):
    """Service bundle composition errors."""
    pass


class AddOnError(ServiceCatalogError):
    """Add-on service errors."""
    pass


class ServiceManagementError(ServicesError):
    """Service management related errors."""
    pass


class ServiceStateError(ServiceManagementError):
    """Service state transition errors."""
    pass


class ServiceNotFoundError(ServiceManagementError):
    """Service instance not found."""
    pass


class InvalidStateTransitionError(ServiceStateError):
    """Invalid service state transition."""
    pass


class ProvisioningError(ServiceManagementError):
    """Service provisioning errors."""
    pass


class ProvisioningTimeoutError(ProvisioningError):
    """Provisioning operation timeout."""
    pass


class TariffError(ServicesError):
    """Tariff and pricing related errors."""
    pass


class PricingRuleError(TariffError):
    """Pricing rule validation errors."""
    pass


class PolicyIntentError(TariffError):
    """Policy intent generation errors."""
    pass


class DiscountError(TariffError):
    """Discount calculation errors."""
    pass


class TaxCalculationError(TariffError):
    """Tax calculation errors."""
    pass


class ProvisioningBindingError(ServicesError):
    """Provisioning binding related errors."""
    pass


class ResourceBindingError(ProvisioningBindingError):
    """Resource binding configuration errors."""
    pass


class ResourceAllocationError(ProvisioningBindingError):
    """Resource allocation errors."""
    pass


class DependencyError(ProvisioningBindingError):
    """Service dependency errors."""
    pass


class ResourceValidationError(ProvisioningBindingError):
    """Resource validation errors."""
    pass


class EventError(ServicesError):
    """Event publishing related errors."""
    pass


class EventPublishError(EventError):
    """Event publishing failures."""
    pass


class IntegrationError(ServicesError):
    """External integration errors."""
    pass


class BillingIntegrationError(IntegrationError):
    """Billing system integration errors."""
    pass


class CRMIntegrationError(IntegrationError):
    """CRM system integration errors."""
    pass


class InventoryIntegrationError(IntegrationError):
    """Inventory system integration errors."""
    pass


class NetworkIntegrationError(IntegrationError):
    """Network provisioning integration errors."""
    pass
