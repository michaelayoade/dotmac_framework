"""
Shared schemas module for DotMac platform.
Provides unified access to all schema definitions across the platform.
"""

# Import from base_schemas (core foundation schemas)
from .base_schemas import (
    # Base classes
    BaseSchema,
    BaseEntity,
    NamedEntity,
    ActiveEntity,
    TenantEntity,
    PersonEntity,
    CompanyEntity,
    
    # CRUD operation schemas
    BaseCreateSchema,
    BaseUpdateSchema,
    BaseResponseSchema,
    
    # Pagination and search
    PaginationSchema,
    PaginatedResponseSchema,
    SearchSchema,
    
    # Mixins - commonly used across platform
    TimestampMixin,
    IdentifiedMixin,
    NamedMixin,
    DescriptionMixin,
    StatusMixin,
    TenantMixin,
    EmailMixin,
    PhoneMixin,
    AddressMixin,
    CurrencyMixin,
    DateRangeMixin,
    GeoLocationMixin,
)

# Import billing schemas
from .billing import (
    # Re-export key billing schemas
    BillingBaseSchema,
    CustomerSchema as BillingCustomerSchema,
    CustomerCreateSchema as BillingCustomerCreateSchema,
    BillingPlanResponse,
    SubscriptionResponse,
    InvoiceResponse,
    PaymentResponse,
)

# Import ISP-specific DRY schemas
from .isp_schemas import (
    ISPBaseSchema,
    ISPCreateSchema, 
    ISPUpdateSchema,
    ISPResponseSchema,
    ISPListResponseSchema,
)

# Common schemas that were already defined (maintain compatibility)
# Re-export everything that modules expect to find
__all__ = [
    # Base foundation schemas
    'BaseSchema',
    'BaseEntity', 
    'NamedEntity',
    'ActiveEntity',
    'TenantEntity',
    'PersonEntity',
    'CompanyEntity',
    
    # CRUD schemas
    'BaseCreateSchema',
    'BaseUpdateSchema', 
    'BaseResponseSchema',
    
    # Pagination
    'PaginationSchema',
    'PaginatedResponseSchema',
    'SearchSchema',
    
    # Mixins
    'TimestampMixin',
    'IdentifiedMixin',
    'NamedMixin',
    'DescriptionMixin',
    'StatusMixin',
    'TenantMixin',
    'EmailMixin',
    'PhoneMixin',
    'AddressMixin',
    'CurrencyMixin',
    'DateRangeMixin',
    'GeoLocationMixin',
    
    # Billing schemas
    'BillingBaseSchema',
    'BillingCustomerSchema',
    'BillingCustomerCreateSchema',
    'BillingPlanResponse',
    'SubscriptionResponse',
    'InvoiceResponse', 
    'PaymentResponse',
    
    # ISP DRY schemas
    'ISPBaseSchema',
    'ISPCreateSchema',
    'ISPUpdateSchema',
    'ISPResponseSchema',
    'ISPListResponseSchema',
]