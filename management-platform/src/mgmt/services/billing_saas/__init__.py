"""
SaaS Billing Service for DotMac Management Platform.

This service manages platform subscription billing, usage tracking, and revenue management
with support for multi-tenant billing, commission calculations, and subscription lifecycle.
"""

from .models import (
    Subscription,
    SubscriptionStatus,
    UsageRecord,
    Invoice,
    CommissionRecord,
    PricingTier,
)
from .service import BillingSaasService
from .schemas import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    UsageRecordCreate,
    InvoiceResponse,
    CommissionCalculation,
)

__all__ = [
    "Subscription",
    "SubscriptionStatus", 
    "UsageRecord",
    "Invoice",
    "CommissionRecord",
    "PricingTier",
    "BillingSaasService",
    "SubscriptionCreate",
    "SubscriptionUpdate",
    "SubscriptionResponse",
    "UsageRecordCreate",
    "InvoiceResponse",
    "CommissionCalculation",
]