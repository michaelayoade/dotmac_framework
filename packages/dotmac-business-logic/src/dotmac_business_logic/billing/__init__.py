"""
Billing Module

Comprehensive billing system with invoicing, payments, and subscription management.
Multi-tenant, scalable with pluggable payment integrations.
"""
try:
    from .services.billing_service import BillingService
except ImportError:
    BillingService = None

try:
    from .services.protocols import (
        InvoiceServiceProtocol as InvoiceService,
    )
    from .services.protocols import (
        PaymentServiceProtocol as PaymentService,
    )
    from .services.protocols import (
        SubscriptionServiceProtocol as SubscriptionService,
    )
except ImportError:
    InvoiceService = None
    PaymentService = None
    SubscriptionService = None

try:
    from .core.models import (
        Customer,
        Invoice,
        Payment,
        Subscription,
    )
except ImportError:
    Customer = None
    Invoice = None
    Payment = None
    Subscription = None

__all__ = [
    "BillingService",
    "InvoiceService",
    "PaymentService",
    "SubscriptionService",
    "Customer",
    "Invoice",
    "Payment",
    "Subscription",
]
