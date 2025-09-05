"""
Billing schemas module for dotmac_shared.schemas compatibility.
Re-exports billing schemas from the main billing package.
"""

from dotmac_business_logic.billing.core.models import (
    BillingCycle,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    PricingModel,
    SubscriptionStatus,
    TaxType,
)
from dotmac_business_logic.billing.schemas.billing_schemas import (
    BillingAnalyticsResponse,
    # Base configuration
    BillingBaseSchema,
    # Billing Plan schemas
    BillingPlanBase,
    BillingPlanCreate,
    BillingPlanListResponse,
    BillingPlanResponse,
    BillingPlanUpdate,
    # Customer schemas
    CustomerCreate,
    CustomerListResponse,
    CustomerMetricsResponse,
    InvoiceBase,
    InvoiceCreate,
    # Invoice schemas
    InvoiceLineItemBase,
    InvoiceLineItemResponse,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    # Payment schemas
    PaymentBase,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    # Analytics schemas
    RevenueMetricsResponse,
    # Subscription schemas
    SubscriptionBase,
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionMetricsResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    # Usage Record schemas
    UsageRecordBase,
    UsageRecordCreate,
    UsageRecordListResponse,
    UsageRecordResponse,
)
from dotmac_business_logic.billing.schemas.billing_schemas import (
    # Customer schemas
    CustomerBase as BillingCustomerBase,
)
from dotmac_business_logic.billing.schemas.billing_schemas import (
    CustomerCreate as BillingCustomerCreate,
)
from dotmac_business_logic.billing.schemas.billing_schemas import (
    CustomerResponse as BillingCustomerResponse,
)
from dotmac_business_logic.billing.schemas.billing_schemas import (
    CustomerUpdate as BillingCustomerUpdate,
)

# Compatibility aliases (temporary)
CustomerCreateSchema = CustomerCreate  # Alias for compatibility
CustomerSchema = BillingCustomerResponse  # Alias for compatibility
CustomerUpdateSchema = BillingCustomerUpdate  # Alias for compatibility

# NO BACKWARD COMPATIBILITY - Use full schema names only
# BREAKING: Use BillingCustomerResponse, BillingCustomerCreate, BillingCustomerUpdate

__all__ = [
    # Base
    "BillingBaseSchema",
    # Customer schemas
    "BillingCustomerBase",
    "BillingCustomerCreate",
    "BillingCustomerUpdate",
    "BillingCustomerResponse",
    "CustomerListResponse",
    "CustomerSchema",  # Alias
    "CustomerCreateSchema",  # Alias
    "CustomerUpdateSchema",  # Alias
    # Billing Plan schemas
    "BillingPlanBase",
    "BillingPlanCreate",
    "BillingPlanUpdate",
    "BillingPlanResponse",
    "BillingPlanListResponse",
    # Subscription schemas
    "SubscriptionBase",
    "SubscriptionCreate",
    "SubscriptionUpdate",
    "SubscriptionResponse",
    "SubscriptionListResponse",
    # Invoice schemas
    "InvoiceLineItemBase",
    "InvoiceLineItemResponse",
    "InvoiceBase",
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceListResponse",
    # Payment schemas
    "PaymentBase",
    "PaymentCreate",
    "PaymentResponse",
    "PaymentListResponse",
    # Usage Record schemas
    "UsageRecordBase",
    "UsageRecordCreate",
    "UsageRecordResponse",
    "UsageRecordListResponse",
    # Analytics schemas
    "RevenueMetricsResponse",
    "CustomerMetricsResponse",
    "SubscriptionMetricsResponse",
    "BillingAnalyticsResponse",
    # Enums
    "BillingCycle",
    "InvoiceStatus",
    "PaymentMethod",
    "PaymentStatus",
    "PricingModel",
    "SubscriptionStatus",
    "TaxType",
]
