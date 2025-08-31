"""
DotMac Billing Package

A comprehensive, reusable billing system for ISP and service provider applications.
Designed for multi-tenant, scalable deployments with pluggable integrations.

Key Features:
- Multi-tenant billing with tenant isolation
- Flexible pricing models (flat rate, usage-based, tiered)
- Subscription and one-time billing support
- Payment processing integration
- Invoice generation and management
- Revenue recognition and reporting
- Plugin architecture for custom billing rules
- Audit trail and compliance features

Usage:
    from dotmac_shared.billing import BillingService, InvoiceService

    billing = BillingService(config)
    invoice = await billing.create_invoice(customer_id, line_items)
"""

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"
__email__ = "support@dotmac.dev"

# Service factory for easy setup
from .adapters.service_factory import (
    BillingServiceFactory,
    create_basic_billing_service,
    create_full_featured_billing_service,
    create_stripe_billing_service,
)

# Core exports for easy importing
from .core.models import (
    BillingPeriod,
    Customer,
    Invoice,
    Payment,
    PricingTier,
    Subscription,
)
# Multi-currency exchange models
from .core.exchange_models import (
    CustomerCurrency,
    ManualExchangeRate,
    MultiCurrencyPayment,
)
from .schemas.billing_schemas import (
    CustomerCreate,
    CustomerUpdate,
    InvoiceCreate,
    PaymentCreate,
    SubscriptionCreate,
)
from .schemas.exchange_schemas import (
    CustomerCurrencyCreate,
    CustomerCurrencyResponse,
    ManualExchangeRateCreate,
    ManualExchangeRateResponse,
    CurrencyConversionRequest,
    CurrencyConversionResponse,
    PaymentWithExchangeRateCreate,
)
from .services.billing_service import BillingService
from .services.exchange_service import ExchangeRateService

# Note: InvoiceService, PaymentService, SubscriptionService are protocols - concrete implementations in billing_service
from .services.protocols import InvoiceServiceProtocol as InvoiceService
from .services.protocols import PaymentServiceProtocol as PaymentService
from .services.protocols import SubscriptionServiceProtocol as SubscriptionService

__all__ = [
    # Models
    "Customer",
    "Subscription",
    "Invoice",
    "Payment",
    "BillingPeriod",
    "PricingTier",
    # Multi-currency models
    "CustomerCurrency",
    "ManualExchangeRate", 
    "MultiCurrencyPayment",
    # Services
    "BillingService",
    "ExchangeRateService",
    "InvoiceService",
    "PaymentService",
    "SubscriptionService",
    # Schemas
    "CustomerCreate",
    "CustomerUpdate",
    "InvoiceCreate",
    "PaymentCreate",
    "SubscriptionCreate",
    # Exchange schemas
    "CustomerCurrencyCreate",
    "CustomerCurrencyResponse", 
    "ManualExchangeRateCreate",
    "ManualExchangeRateResponse",
    "CurrencyConversionRequest",
    "CurrencyConversionResponse",
    "PaymentWithExchangeRateCreate",
    # Factory
    "BillingServiceFactory",
    "create_basic_billing_service",
    "create_stripe_billing_service",
    "create_full_featured_billing_service",
    # Package metadata
    "__version__",
    "__author__",
    "__email__",
]
