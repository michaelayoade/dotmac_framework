"""
DotMac Database Package - Core database utilities and patterns.

Provides foundational database components including:
- Declarative base classes and common mixins
- Async engine and session factories with configuration
- FastAPI dependency injection helpers
- Row-Level Security and schema management utilities
- Redis-based caching with intelligent invalidation
- Distributed locking (Redis + PostgreSQL advisory)
- Alembic migration helpers and utilities

Key Features:
- SQLAlchemy 2.0+ async support throughout
- Multi-tenant database patterns (RLS, schema-per-tenant)
- Production-ready caching and coordination primitives
- Type-safe database interactions with comprehensive error handling
- Optional extras for FastAPI, Redis, and Alembic integration

Example Usage:
    from dotmac.database import BaseModel, SoftDeleteMixin
    from dotmac.database.engine import create_async_engine
    from dotmac.database.deps import get_db
    
    class User(BaseModel, SoftDeleteMixin):
        __tablename__ = "users"
        
        email: Mapped[str] = mapped_column(String(255), unique=True)
        name: Mapped[str] = mapped_column(String(100))
    
    engine = create_async_engine("postgresql+asyncpg://...")
"""

# Core base classes and mixins
from .base import Base, BaseModel
from .mixins import (
    SoftDeleteMixin,
    AuditMixin, 
    TenantAwareMixin,
    TimestampMixin,
    VersionedMixin,
    SoftDeleteAuditMixin,
    TenantAuditMixin,
    FullAuditMixin,
)

# Type definitions
from .types import GUID, TenantIdType, UserIdType

# Engine and session management
from .engine import (
    create_async_engine,
    create_async_sessionmaker,
    DatabaseManager,
    DatabaseURL,
)

# Exception types
from .exceptions import (
    DatabaseError,
    ConnectionError,
    TransactionError,
    ValidationError,
)

# Core exports
__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    
    # Mixins
    "SoftDeleteMixin",
    "AuditMixin",
    "TenantAwareMixin",
    "TimestampMixin", 
    "VersionedMixin",
    "SoftDeleteAuditMixin",
    "TenantAuditMixin",
    "FullAuditMixin",
    
    # Types
    "GUID",
    "TenantIdType",
    "UserIdType",
    
    # Engine/Session
    "create_async_engine",
    "create_async_sessionmaker", 
    "DatabaseManager",
    "DatabaseURL",
    
    # Exceptions
    "DatabaseError",
    "ConnectionError",
    "TransactionError",
    "ValidationError",
]

# Optional FastAPI dependencies (only if fastapi extra installed)
try:
    from .deps import get_db, get_read_session, get_write_session
    __all__.extend([
        "get_db",
        "get_read_session", 
        "get_write_session",
    ])
except ImportError:
    pass

# RLS and schema helpers
from .rls import (
    set_rls_context,
    get_rls_context,
    clear_rls_context,
    set_schema_search_path,
    create_tenant_schema,
    RLSPolicyManager,
    RLSError,
    SchemaManagementError,
)

__all__.extend([
    "set_rls_context",
    "get_rls_context", 
    "clear_rls_context",
    "set_schema_search_path",
    "create_tenant_schema",
    "RLSPolicyManager", 
    "RLSError",
    "SchemaManagementError",
])

# Optional Redis caching (only if redis extra installed)
try:
    from .caching import SmartCache, get_redis_client, CacheError, CacheStats
    __all__.extend([
        "SmartCache",
        "get_redis_client",
        "CacheError", 
        "CacheStats",
    ])
except ImportError:
    pass

# Optional coordination/locking (only if redis extra installed)  
try:
    from .coordination import (
        RedisLock,
        PgAdvisoryLock,
        LockError,
        LockTimeout,
        LockNotAcquired,
    )
    __all__.extend([
        "RedisLock",
        "PgAdvisoryLock",
        "LockError",
        "LockTimeout", 
        "LockNotAcquired",
    ])
except ImportError:
    pass

# Optional Alembic helpers (only if alembic extra installed)
try:
    from .alembic import (
        get_alembic_config_url,
        include_object,
        run_post_migration_hooks,
        create_schema_if_not_exists,
        enable_rls_on_table,
        create_rls_policy,
        MigrationHelpers,
        AlembicError,
    )
    __all__.extend([
        "get_alembic_config_url",
        "include_object",
        "run_post_migration_hooks", 
        "create_schema_if_not_exists",
        "enable_rls_on_table",
        "create_rls_policy",
        "MigrationHelpers",
        "AlembicError",
    ])
except ImportError:
    pass