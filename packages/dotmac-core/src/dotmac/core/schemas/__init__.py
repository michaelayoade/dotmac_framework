"""
Shared schemas module for DotMac platform.
Provides unified access to all schema definitions across the platform.
"""

from dotmac.core.schemas.base_schemas import (
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

# Import billing schemas (optional)
try:
    from dotmac.core.schemas.billing import (
        # Re-export key billing schemas
        BillingBaseSchema,
        BillingPlanResponse,
        InvoiceResponse,
        PaymentResponse,
        SubscriptionResponse,
    )
    from dotmac.core.schemas.billing import (
        CustomerCreateSchema as BillingCustomerCreateSchema,
    )
    from dotmac.core.schemas.billing import (
        CustomerSchema as BillingCustomerSchema,
    )

    _BILLING_AVAILABLE = True
except ImportError:
    # Billing schemas not available - create stubs for compatibility
    _BILLING_AVAILABLE = False

    class BillingBaseSchema:
        pass

    class BillingPlanResponse:
        pass

    class InvoiceResponse:
        pass

    class PaymentResponse:
        pass

    class SubscriptionResponse:
        pass

    class BillingCustomerCreateSchema:
        pass

    class BillingCustomerSchema:
        pass


# Import ISP-specific DRY schemas (optional)
try:
    from dotmac.core.schemas.isp_schemas import (
        ISPBaseSchema,
        ISPCreateSchema,
        ISPListResponseSchema,
        ISPResponseSchema,
        ISPUpdateSchema,
    )

    _ISP_SCHEMAS_AVAILABLE = True
except ImportError:
    # ISP schemas not available - create stubs for compatibility
    _ISP_SCHEMAS_AVAILABLE = False

    class ISPBaseSchema:
        pass

    class ISPCreateSchema:
        pass

    class ISPListResponseSchema:
        pass

    class ISPResponseSchema:
        pass

    class ISPUpdateSchema:
        pass


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
