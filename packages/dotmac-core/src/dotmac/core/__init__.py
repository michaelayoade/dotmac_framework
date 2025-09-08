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

from pydantic import BaseModel as PydanticBaseModel

from dotmac.core.cache import (
    CacheManagerProtocol,
    CacheService,
    MemoryCacheManager,
    RedisCacheManager,
    TenantAwareCacheManager,
    cached,
    create_cache_service,
)
from dotmac.core.config import CacheConfig, DatabaseConfig, SecurityConfig
from dotmac.core.decorators import retry_on_failure, standard_exception_handler, timeout
from dotmac.core.logging import get_logger

# Import from database.py file (not database/ directory)
try:
    from dotmac.core.database import (
        AsyncRepository,
        AuditMixin,
        Base,
        BaseRepository,
        DatabaseHealthChecker,
        DatabasePaginator,
        DBBaseModel,
        TenantBaseModel,
        TimestampMixin,
        TransactionManager,
        UUIDMixin,
    )

    # Compatibility alias for existing code
    BaseModel = DBBaseModel

    _database_available = True
except ImportError:
    # Database components not available
    Base = DBBaseModel = BaseModel = TenantBaseModel = UUIDMixin = TimestampMixin = AuditMixin = None
    BaseRepository = AsyncRepository = TransactionManager = DatabaseHealthChecker = (
        DatabasePaginator
    ) = None
    _database_available = False
from dotmac.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConfigurationError,
    DatabaseError,
    DotMacError,
    EntityNotFoundError,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    ServiceError,
    TenantError,
    TenantNotFoundError,
    ValidationError,
)
from dotmac.core.exceptions import (
    ConnectionError as DotMacConnectionError,
)
from dotmac.core.exceptions import (
    PermissionError as DotMacPermissionError,
)
from dotmac.core.exceptions import (
    TimeoutError as DotMacTimeoutError,
)
from dotmac.core.tenant import (
    TenantContext,
    TenantManager,
    TenantMetadata,
    clear_current_tenant,
    get_current_tenant,
    require_current_tenant,
    set_current_tenant,
)
from dotmac.core.types import GUID

# Schemas - unified schema definitions (with graceful fallback)
try:
    from dotmac.core.schemas import (
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
        from dotmac.core.schemas.base_schemas import (
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


# Guard helper functions
def is_database_available() -> bool:
    """
    Check if database toolkit is available.

    Returns:
        bool: True if database components are fully available

    Example:
        if is_database_available():
            from dotmac.core import DBBaseModel, TransactionManager
        else:
            logger.warning("Database toolkit not available - using fallback")
    """
    return _database_available


def is_schemas_available() -> bool:
    """
    Check if schema definitions are available.

    Returns:
        bool: True if schemas are fully available

    Example:
        if is_schemas_available():
            from dotmac.core import BaseSchema, PaginationSchema
        else:
            logger.warning("Schemas not available - using fallback")
    """
    return _schemas_available


def require_database() -> None:
    """
    Require database toolkit to be available or raise ImportError.

    Raises:
        ImportError: If database toolkit is not available

    Example:
        require_database()
        # Safe to use database components now
        session = get_db_session()
    """
    if not _database_available:
        raise ImportError(
            "Database toolkit not available. Install with: pip install 'dotmac-core[database]'"
        )


def require_schemas() -> None:
    """
    Require schema definitions to be available or raise ImportError.

    Raises:
        ImportError: If schema definitions are not available

    Example:
        require_schemas()
        # Safe to use schema components now
        from dotmac.core import BaseSchema
    """
    if not _schemas_available:
        raise ImportError(
            "Schema definitions not available. Install with: pip install 'dotmac-core[schemas]'"
        )


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
    "DBBaseModel",
    "BaseModel",  # Compatibility alias for DBBaseModel
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
    "DotMacConnectionError",
    "DotMacTimeoutError",
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
    "DotMacPermissionError",
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
    # Guard helpers
    "is_database_available",
    "is_schemas_available",
    "require_database",
    "require_schemas",
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
