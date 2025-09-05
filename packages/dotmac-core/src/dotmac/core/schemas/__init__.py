"""
Shared schemas module for DotMac platform.
Provides unified access to all schema definitions across the platform.
"""

from .base_schemas import (
    ActiveEntity,
    AddressMixin,
    # CRUD operation schemas
    BaseCreateSchema,
    BaseEntity,
    BaseResponseSchema,
    # Base classes
    BaseSchema,
    BaseUpdateSchema,
    CompanyEntity,
    CurrencyMixin,
    DateRangeMixin,
    DescriptionMixin,
    EmailMixin,
    GeoLocationMixin,
    IdentifiedMixin,
    NamedEntity,
    NamedMixin,
    PaginatedResponseSchema,
    # Pagination and search
    PaginationSchema,
    PersonEntity,
    PhoneMixin,
    SearchSchema,
    StatusMixin,
    TenantEntity,
    TenantMixin,
    # Mixins - commonly used across platform
    TimestampMixin,
)

# Import billing schemas
from .billing import (
    # Re-export key billing schemas
    BillingBaseSchema,
    BillingPlanResponse,
    InvoiceResponse,
    PaymentResponse,
    SubscriptionResponse,
)
from .billing import (
    CustomerCreateSchema as BillingCustomerCreateSchema,
)
from .billing import (
    CustomerSchema as BillingCustomerSchema,
)

# Import ISP-specific DRY schemas
from .isp_schemas import (
    ISPBaseSchema,
    ISPCreateSchema,
    ISPListResponseSchema,
    ISPResponseSchema,
    ISPUpdateSchema,
)

# Common schemas that were already defined (maintain compatibility)
# Re-export everything that modules expect to find
__all__ = [
    # Base foundation schemas
    "BaseSchema",
    "BaseEntity",
    "NamedEntity",
    "ActiveEntity",
    "TenantEntity",
    "PersonEntity",
    "CompanyEntity",
    # CRUD schemas
    "BaseCreateSchema",
    "BaseUpdateSchema",
    "BaseResponseSchema",
    # Pagination
    "PaginationSchema",
    "PaginatedResponseSchema",
    "SearchSchema",
    # Mixins
    "TimestampMixin",
    "IdentifiedMixin",
    "NamedMixin",
    "DescriptionMixin",
    "StatusMixin",
    "TenantMixin",
    "EmailMixin",
    "PhoneMixin",
    "AddressMixin",
    "CurrencyMixin",
    "DateRangeMixin",
    "GeoLocationMixin",
    # Billing schemas
    "BillingBaseSchema",
    "BillingCustomerSchema",
    "BillingCustomerCreateSchema",
    "BillingPlanResponse",
    "SubscriptionResponse",
    "InvoiceResponse",
    "PaymentResponse",
    # ISP DRY schemas
    "ISPBaseSchema",
    "ISPCreateSchema",
    "ISPUpdateSchema",
    "ISPResponseSchema",
    "ISPListResponseSchema",
]
