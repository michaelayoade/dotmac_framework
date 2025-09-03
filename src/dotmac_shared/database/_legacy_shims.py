"""
Legacy shim module for backward compatibility.

This module provides compatibility imports from the old dotmac_shared.database
location to the new dotmac.database package.

All imports from this module are deprecated and will be removed in a future version.
Use imports from dotmac.database instead.

Migration Guide:
    OLD: from dotmac_shared.database import BaseModel
    NEW: from dotmac.database import BaseModel

    OLD: from dotmac_shared.database.mixins import SoftDeleteMixin
    NEW: from dotmac.database import SoftDeleteMixin

    OLD: from dotmac_shared.database.engine import create_async_engine
    NEW: from dotmac.database import create_async_engine
"""

import warnings
from typing import Any

# Issue deprecation warning for any imports from this module
warnings.warn(
    "Importing from dotmac_shared.database is deprecated. "
    "Use 'from dotmac.database import ...' instead. "
    "See MIGRATION_GUIDE.md for details.",
    DeprecationWarning,
    stacklevel=2
)


def _deprecated_import(name: str, new_location: str) -> Any:
    """Helper to import from new location with deprecation warning."""
    warnings.warn(
        f"Importing {name} from dotmac_shared.database is deprecated. "
        f"Use 'from {new_location} import {name}' instead.",
        DeprecationWarning,
        stacklevel=3
    )
    
    # Import from new location
    if new_location == "dotmac.database":
        from dotmac.database import BaseModel as _BaseModel
        from dotmac.database import Base as _Base
        from dotmac.database import GUID as _GUID
        from dotmac.database import create_async_engine as _create_async_engine
        from dotmac.database import create_async_sessionmaker as _create_async_sessionmaker
        from dotmac.database import DatabaseManager as _DatabaseManager
        from dotmac.database import DatabaseURL as _DatabaseURL
        
        mapping = {
            "BaseModel": _BaseModel,
            "Base": _Base, 
            "GUID": _GUID,
            "create_async_engine": _create_async_engine,
            "create_async_session_factory": _create_async_sessionmaker,  # Legacy name mapping
            "create_async_sessionmaker": _create_async_sessionmaker,
            "DatabaseManager": _DatabaseManager,
            "DatabaseURL": _DatabaseURL,
        }
        
        return mapping.get(name)
    
    elif new_location == "dotmac.database.mixins":
        from dotmac.database import (
            SoftDeleteMixin as _SoftDeleteMixin,
            AuditMixin as _AuditMixin,
            TenantAwareMixin as _TenantAwareMixin,
            TimestampMixin as _TimestampMixin,
            VersionedMixin as _VersionedMixin,
            SoftDeleteAuditMixin as _SoftDeleteAuditMixin,
            TenantAuditMixin as _TenantAuditMixin,
            FullAuditMixin as _FullAuditMixin,
        )
        
        mapping = {
            "SoftDeleteMixin": _SoftDeleteMixin,
            "AuditMixin": _AuditMixin,
            "TenantAwareMixin": _TenantAwareMixin,
            "TimestampMixin": _TimestampMixin,
            "VersionedMixin": _VersionedMixin,
            "SoftDeleteAuditMixin": _SoftDeleteAuditMixin,
            "TenantAuditMixin": _TenantAuditMixin,
            "FullAuditMixin": _FullAuditMixin,
            # Aliases for backward compatibility
            "TenantAwareSoftDeleteMixin": _TenantAuditMixin,  # Map to closest equivalent
            "CompleteMixin": _FullAuditMixin,  # Map to full audit mixin
        }
        
        return mapping.get(name)
    
    elif new_location == "dotmac.database.deps":
        try:
            from dotmac.database import get_db as _get_db
            from dotmac.database import get_read_session as _get_read_session
            from dotmac.database import get_write_session as _get_write_session
            
            mapping = {
                "get_db": _get_db,
                "get_read_session": _get_read_session,
                "get_write_session": _get_write_session,
            }
            
            return mapping.get(name)
        except ImportError:
            raise ImportError(
                f"Cannot import {name} from {new_location}. "
                "FastAPI integration not available. "
                "Install with: pip install 'dotmac-database[fastapi]'"
            )
    
    elif new_location == "dotmac.database.caching":
        try:
            from dotmac.database import SmartCache as _SmartCache
            from dotmac.database import get_redis_client as _get_redis_client
            from dotmac.database import CacheError as _CacheError
            from dotmac.database import CacheStats as _CacheStats
            
            mapping = {
                "SmartCache": _SmartCache,
                "get_redis_client": _get_redis_client,
                "CacheError": _CacheError,
                "CacheStats": _CacheStats,
            }
            
            return mapping.get(name)
        except ImportError:
            raise ImportError(
                f"Cannot import {name} from {new_location}. "
                "Redis integration not available. "
                "Install with: pip install 'dotmac-database[redis]'"
            )
    
    elif new_location == "dotmac.database.coordination":
        try:
            from dotmac.database import RedisLock as _RedisLock
            from dotmac.database import PgAdvisoryLock as _PgAdvisoryLock
            from dotmac.database import LockError as _LockError
            from dotmac.database import LockTimeout as _LockTimeout
            from dotmac.database import LockNotAcquired as _LockNotAcquired
            
            mapping = {
                "RedisLock": _RedisLock,
                "PgAdvisoryLock": _PgAdvisoryLock,
                "LockError": _LockError,
                "LockTimeout": _LockTimeout,
                "LockNotAcquired": _LockNotAcquired,
            }
            
            return mapping.get(name)
        except ImportError:
            raise ImportError(
                f"Cannot import {name} from {new_location}. "
                "Coordination/locking features not available. "
                "Install with: pip install 'dotmac-database[redis]'"
            )
    
    elif new_location == "dotmac.database.rls":
        from dotmac.database import (
            set_rls_context as _set_rls_context,
            get_rls_context as _get_rls_context,
            clear_rls_context as _clear_rls_context,
            set_schema_search_path as _set_schema_search_path,
            create_tenant_schema as _create_tenant_schema,
            RLSPolicyManager as _RLSPolicyManager,
            RLSError as _RLSError,
            SchemaManagementError as _SchemaManagementError,
        )
        
        mapping = {
            "set_rls_context": _set_rls_context,
            "get_rls_context": _get_rls_context,
            "clear_rls_context": _clear_rls_context,
            "set_schema_search_path": _set_schema_search_path,
            "create_tenant_schema": _create_tenant_schema,
            "RLSPolicyManager": _RLSPolicyManager,
            "RLSError": _RLSError,
            "SchemaManagementError": _SchemaManagementError,
        }
        
        return mapping.get(name)
    
    elif new_location == "dotmac.database.alembic":
        try:
            from dotmac.database import (
                get_alembic_config_url as _get_alembic_config_url,
                include_object as _include_object,
                run_post_migration_hooks as _run_post_migration_hooks,
                create_schema_if_not_exists as _create_schema_if_not_exists,
                enable_rls_on_table as _enable_rls_on_table,
                create_rls_policy as _create_rls_policy,
                MigrationHelpers as _MigrationHelpers,
                AlembicError as _AlembicError,
            )
            
            mapping = {
                "get_alembic_config_url": _get_alembic_config_url,
                "include_object": _include_object,
                "run_post_migration_hooks": _run_post_migration_hooks,
                "create_schema_if_not_exists": _create_schema_if_not_exists,
                "enable_rls_on_table": _enable_rls_on_table,
                "create_rls_policy": _create_rls_policy,
                "MigrationHelpers": _MigrationHelpers,
                "AlembicError": _AlembicError,
            }
            
            return mapping.get(name)
        except ImportError:
            raise ImportError(
                f"Cannot import {name} from {new_location}. "
                "Alembic integration not available. "
                "Install with: pip install 'dotmac-database[alembic]'"
            )
    
    raise ImportError(f"Cannot import {name} from {new_location}")


# Core database classes
BaseModel = _deprecated_import("BaseModel", "dotmac.database")
Base = _deprecated_import("Base", "dotmac.database")
GUID = _deprecated_import("GUID", "dotmac.database")

# Engine and session management
create_async_engine = _deprecated_import("create_async_engine", "dotmac.database")
create_async_session_factory = _deprecated_import("create_async_session_factory", "dotmac.database")  # Legacy name
create_async_sessionmaker = _deprecated_import("create_async_sessionmaker", "dotmac.database")
DatabaseManager = _deprecated_import("DatabaseManager", "dotmac.database")
DatabaseURL = _deprecated_import("DatabaseURL", "dotmac.database")

# Mixins
SoftDeleteMixin = _deprecated_import("SoftDeleteMixin", "dotmac.database.mixins")
AuditMixin = _deprecated_import("AuditMixin", "dotmac.database.mixins")
TenantAwareMixin = _deprecated_import("TenantAwareMixin", "dotmac.database.mixins")
TimestampMixin = _deprecated_import("TimestampMixin", "dotmac.database.mixins")
VersionedMixin = _deprecated_import("VersionedMixin", "dotmac.database.mixins")
SoftDeleteAuditMixin = _deprecated_import("SoftDeleteAuditMixin", "dotmac.database.mixins")
TenantAuditMixin = _deprecated_import("TenantAuditMixin", "dotmac.database.mixins")
FullAuditMixin = _deprecated_import("FullAuditMixin", "dotmac.database.mixins")

# Backward compatibility aliases
TenantAwareSoftDeleteMixin = _deprecated_import("TenantAwareSoftDeleteMixin", "dotmac.database.mixins")
CompleteMixin = _deprecated_import("CompleteMixin", "dotmac.database.mixins")

# RLS and schema helpers
set_rls_context = _deprecated_import("set_rls_context", "dotmac.database.rls")
get_rls_context = _deprecated_import("get_rls_context", "dotmac.database.rls")
clear_rls_context = _deprecated_import("clear_rls_context", "dotmac.database.rls")
set_schema_search_path = _deprecated_import("set_schema_search_path", "dotmac.database.rls")
create_tenant_schema = _deprecated_import("create_tenant_schema", "dotmac.database.rls")
RLSPolicyManager = _deprecated_import("RLSPolicyManager", "dotmac.database.rls")
RLSError = _deprecated_import("RLSError", "dotmac.database.rls")
SchemaManagementError = _deprecated_import("SchemaManagementError", "dotmac.database.rls")

# Optional imports with error handling
try:
    get_db = _deprecated_import("get_db", "dotmac.database.deps")
    get_read_session = _deprecated_import("get_read_session", "dotmac.database.deps")
    get_write_session = _deprecated_import("get_write_session", "dotmac.database.deps")
except ImportError:
    # FastAPI integration not available
    pass

try:
    SmartCache = _deprecated_import("SmartCache", "dotmac.database.caching")
    get_redis_client = _deprecated_import("get_redis_client", "dotmac.database.caching")
    CacheError = _deprecated_import("CacheError", "dotmac.database.caching")
    CacheStats = _deprecated_import("CacheStats", "dotmac.database.caching")
except ImportError:
    # Redis integration not available
    pass

try:
    RedisLock = _deprecated_import("RedisLock", "dotmac.database.coordination")
    PgAdvisoryLock = _deprecated_import("PgAdvisoryLock", "dotmac.database.coordination")
    LockError = _deprecated_import("LockError", "dotmac.database.coordination")
    LockTimeout = _deprecated_import("LockTimeout", "dotmac.database.coordination")
    LockNotAcquired = _deprecated_import("LockNotAcquired", "dotmac.database.coordination")
except ImportError:
    # Coordination features not available
    pass

try:
    get_alembic_config_url = _deprecated_import("get_alembic_config_url", "dotmac.database.alembic")
    include_object = _deprecated_import("include_object", "dotmac.database.alembic")
    run_post_migration_hooks = _deprecated_import("run_post_migration_hooks", "dotmac.database.alembic")
    create_schema_if_not_exists = _deprecated_import("create_schema_if_not_exists", "dotmac.database.alembic")
    enable_rls_on_table = _deprecated_import("enable_rls_on_table", "dotmac.database.alembic")
    create_rls_policy = _deprecated_import("create_rls_policy", "dotmac.database.alembic")
    MigrationHelpers = _deprecated_import("MigrationHelpers", "dotmac.database.alembic")
    AlembicError = _deprecated_import("AlembicError", "dotmac.database.alembic")
except ImportError:
    # Alembic integration not available
    pass