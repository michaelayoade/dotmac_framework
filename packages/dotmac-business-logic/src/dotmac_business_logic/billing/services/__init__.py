"""Billing services for the DotMac Billing Package."""

from .billing_service import BillingService
from .protocols import (
    BillingAnalyticsProtocol,
    BillingServiceProtocol,
    InvoiceServiceProtocol,
    NotificationServiceProtocol,
    PaymentGatewayProtocol,
    PaymentServiceProtocol,
    PdfGeneratorProtocol,
    SubscriptionServiceProtocol,
    TaxCalculationServiceProtocol,
)

__all__ = [
    # Concrete services
    "BillingService",
    # Service protocols
    "BillingServiceProtocol",
    "InvoiceServiceProtocol",
    "PaymentServiceProtocol",
    "SubscriptionServiceProtocol",
    "BillingAnalyticsProtocol",
    # External service protocols
    "PaymentGatewayProtocol",
    "NotificationServiceProtocol",
    "TaxCalculationServiceProtocol",
    "PdfGeneratorProtocol",
]
