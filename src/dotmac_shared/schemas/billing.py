"""
Billing schemas module for dotmac_shared.schemas compatibility.
Re-exports billing schemas from the main billing package.
"""

from dotmac_shared.billing.schemas.billing_schemas import (
    # Customer schemas
    CustomerBase as BillingCustomerBase,
    CustomerCreate as BillingCustomerCreate,
    CustomerUpdate as BillingCustomerUpdate,
    CustomerResponse as BillingCustomerResponse,
    CustomerListResponse,
    
    # Billing Plan schemas
    BillingPlanBase,
    BillingPlanCreate,
    BillingPlanUpdate,
    BillingPlanResponse,
    BillingPlanListResponse,
    
    # Subscription schemas
    SubscriptionBase,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionListResponse,
    
    # Invoice schemas
    InvoiceLineItemBase,
    InvoiceLineItemResponse,
    InvoiceBase,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceListResponse,
    
    # Payment schemas
    PaymentBase,
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse,
    
    # Usage Record schemas
    UsageRecordBase,
    UsageRecordCreate,
    UsageRecordResponse,
    UsageRecordListResponse,
    
    # Analytics schemas
    RevenueMetricsResponse,
    CustomerMetricsResponse,
    SubscriptionMetricsResponse,
    BillingAnalyticsResponse,
    
    # Base configuration
    BillingBaseSchema,
)

from dotmac_shared.billing.core.models import (
    # Enums
    BillingCycle,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    PricingModel,
    SubscriptionStatus,
    TaxType,
)

# NO BACKWARD COMPATIBILITY - Use full schema names only
# BREAKING: Use BillingCustomerResponse, BillingCustomerCreate, BillingCustomerUpdate

__all__ = [
    # Base
    'BillingBaseSchema',
    
    # Customer schemas
    'BillingCustomerBase',
    'BillingCustomerCreate', 
    'BillingCustomerUpdate',
    'BillingCustomerResponse',
    'CustomerListResponse',
    'CustomerSchema',  # Alias
    'CustomerCreateSchema',  # Alias
    'CustomerUpdateSchema',  # Alias
    
    # Billing Plan schemas
    'BillingPlanBase',
    'BillingPlanCreate',
    'BillingPlanUpdate', 
    'BillingPlanResponse',
    'BillingPlanListResponse',
    
    # Subscription schemas
    'SubscriptionBase',
    'SubscriptionCreate',
    'SubscriptionUpdate',
    'SubscriptionResponse',
    'SubscriptionListResponse',
    
    # Invoice schemas
    'InvoiceLineItemBase',
    'InvoiceLineItemResponse',
    'InvoiceBase',
    'InvoiceCreate',
    'InvoiceUpdate',
    'InvoiceResponse',
    'InvoiceListResponse',
    
    # Payment schemas
    'PaymentBase',
    'PaymentCreate',
    'PaymentResponse',
    'PaymentListResponse',
    
    # Usage Record schemas
    'UsageRecordBase',
    'UsageRecordCreate',
    'UsageRecordResponse', 
    'UsageRecordListResponse',
    
    # Analytics schemas
    'RevenueMetricsResponse',
    'CustomerMetricsResponse',
    'SubscriptionMetricsResponse',
    'BillingAnalyticsResponse',
    
    # Enums
    'BillingCycle',
    'InvoiceStatus',
    'PaymentMethod',
    'PaymentStatus',
    'PricingModel',
    'SubscriptionStatus',
    'TaxType',
]