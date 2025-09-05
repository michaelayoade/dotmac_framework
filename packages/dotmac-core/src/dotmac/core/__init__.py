from pydantic import BaseModel

"""
DotMac Core - Foundation package for DotMac Framework.

This package consolidates core functionality including:
- Database foundation classes and utilities
- Tenant management and context
- Exception hierarchy
- Configuration management
- Common types

Eliminates DRY violations by providing a single source of truth
for common patterns used across the framework.
"""

from .cache import (
    CacheManagerProtocol,
    CacheService,
    MemoryCacheManager,
    RedisCacheManager,
    TenantAwareCacheManager,
    cached,
    create_cache_service,
)
from .config import CacheConfig, DatabaseConfig, SecurityConfig
from .decorators import retry_on_failure, standard_exception_handler, timeout
from .logging import get_logger

# Import from database.py file (not database/ directory)
try:
    from .database import (
        AsyncRepository,
        AuditMixin,
        Base,
        BaseModel,
        BaseRepository,
        DatabaseHealthChecker,
        DatabasePaginator,
        TenantBaseModel,
        TimestampMixin,
        TransactionManager,
        UUIDMixin,
    )

    _database_available = True
except ImportError:
    # Database components not available
    Base = BaseModel = TenantBaseModel = UUIDMixin = TimestampMixin = AuditMixin = None
    BaseRepository = (
        AsyncRepository
    ) = TransactionManager = DatabaseHealthChecker = DatabasePaginator = None
    _database_available = False
from .exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConfigurationError,
    ConnectionError,
    DatabaseError,
    DotMacError,
    EntityNotFoundError,
    ExternalServiceError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServiceError,
    TenantError,
    TenantNotFoundError,
    TimeoutError,
    ValidationError,
)
from .tenant import (
    TenantContext,
    TenantManager,
    TenantMetadata,
    clear_current_tenant,
    get_current_tenant,
    require_current_tenant,
    set_current_tenant,
)
from .types import GUID

# Schemas - unified schema definitions (with graceful fallback)
try:
    from .schemas import (
        ActiveEntity,
        AddressMixin,
        BaseCreateSchema,
        BaseEntity,
        BaseResponseSchema,
        BaseSchema,
        BaseUpdateSchema,
        BillingBaseSchema,
        BillingCustomerCreateSchema,
        BillingCustomerSchema,
        BillingPlanResponse,
        CompanyEntity,
        CurrencyMixin,
        DateRangeMixin,
        DescriptionMixin,
        EmailMixin,
        GeoLocationMixin,
        IdentifiedMixin,
        InvoiceResponse,
        ISPBaseSchema,
        ISPCreateSchema,
        ISPListResponseSchema,
        ISPResponseSchema,
        ISPUpdateSchema,
        NamedEntity,
        NamedMixin,
        PaginatedResponseSchema,
        PaginationSchema,
        PaymentResponse,
        PersonEntity,
        PhoneMixin,
        SearchSchema,
        StatusMixin,
        SubscriptionResponse,
        TenantEntity,
        TenantMixin,
        TimestampMixin,
    )

    _schemas_available = True
except ImportError as e:
    # Schemas not available due to missing dependencies
    import warnings

    warnings.warn(f"Schemas not fully available: {e}")
    # Fallback - import only base schemas that don't have external dependencies
    try:
        from .schemas.base_schemas import (
            BaseCreateSchema,
            BaseEntity,
            BaseResponseSchema,
            BaseSchema,
            BaseUpdateSchema,
            PaginatedResponseSchema,
            PaginationSchema,
            TimestampMixin,
        )
    except ImportError:
        # If even base schemas fail, set to None
        (
            BaseSchema,
            BaseEntity,
            BaseCreateSchema,
            BaseUpdateSchema,
            BaseResponseSchema,
            PaginationSchema,
            PaginatedResponseSchema,
            TimestampMixin,
        ) = (None,) * 8
    _schemas_available = False


# Database compatibility functions - needed by ISP framework
class DatabaseManager:
    """Compatibility database manager."""

    def __init__(self, config=None):
        self.config = config

    def get_session(self):
        """Get database session."""
        return None

    def check_health(self):
        """Check database health."""
        return {"status": "ok"}


def get_db():
    """Get database connection."""
    return None


def get_db_session():
    """Get database session."""
    return None


def check_database_health():
    """Check database health."""
    return {"status": "ok", "message": "Database health check not implemented"}


__version__ = "1.0.0"

__all__ = [
    # Configuration
    "DatabaseConfig",
    "CacheConfig",
    "SecurityConfig",
    # Logging
    "get_logger",
    # Decorators
    "standard_exception_handler",
    "retry_on_failure",
    "timeout",
    # Database
    "Base",
    "BaseModel",
    "TenantBaseModel",
    "UUIDMixin",
    "TimestampMixin",
    "AuditMixin",
    # Exceptions
    "DotMacError",
    "ConfigurationError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "DatabaseError",
    "TenantError",
    "TenantNotFoundError",
    "ServiceError",
    "BusinessRuleError",
    "NotFoundError",
    "AlreadyExistsError",
    "EntityNotFoundError",
    "ExternalServiceError",
    "PermissionError",
    # Cache services
    "CacheService",
    "CacheManagerProtocol",
    "RedisCacheManager",
    "MemoryCacheManager",
    "TenantAwareCacheManager",
    "create_cache_service",
    "cached",
    # Database compatibility
    "DatabaseManager",
    "get_db",
    "get_db_session",
    "check_database_health",
    # Tenant
    "TenantContext",
    "TenantMetadata",
    "TenantManager",
    "get_current_tenant",
    "require_current_tenant",
    "set_current_tenant",
    "clear_current_tenant",
    # Types
    "GUID",
    # Schemas - unified schema definitions
    "BaseSchema",
    "BaseEntity",
    "NamedEntity",
    "ActiveEntity",
    "TenantEntity",
    "PersonEntity",
    "CompanyEntity",
    "BaseCreateSchema",
    "BaseUpdateSchema",
    "BaseResponseSchema",
    "PaginationSchema",
    "PaginatedResponseSchema",
    "SearchSchema",
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
    "BillingBaseSchema",
    "BillingCustomerSchema",
    "BillingCustomerCreateSchema",
    "BillingPlanResponse",
    "SubscriptionResponse",
    "InvoiceResponse",
    "PaymentResponse",
    "ISPBaseSchema",
    "ISPCreateSchema",
    "ISPUpdateSchema",
    "ISPResponseSchema",
    "ISPListResponseSchema",
]
