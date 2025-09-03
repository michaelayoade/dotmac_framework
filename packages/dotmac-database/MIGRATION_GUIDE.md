# Migration Guide: dotmac_shared.database → dotmac.database

This guide helps you migrate from the legacy `dotmac_shared.database` module to the new standalone `dotmac.database` package.

## Overview

The database utilities have been extracted into a standalone package with improved structure, better type safety, and optional dependencies.

## Package Installation

Install the new package:

```bash
# Core package only
pip install dotmac-database

# With FastAPI integration
pip install "dotmac-database[fastapi]"

# With Redis caching and locking
pip install "dotmac-database[redis]"

# With Alembic helpers
pip install "dotmac-database[alembic]"

# All features
pip install "dotmac-database[all]"
```

## Import Changes

### Core Database Classes

```python
# OLD
from dotmac_shared.database import BaseModel, Base, GUID
from dotmac_shared.database.engine import create_async_engine, DatabaseManager

# NEW
from dotmac.database import BaseModel, Base, GUID, create_async_engine, DatabaseManager
```

### Mixins

```python
# OLD
from dotmac_shared.database.mixins import (
    SoftDeleteMixin, 
    AuditMixin,
    TenantAwareMixin
)

# NEW
from dotmac.database import (
    SoftDeleteMixin,
    AuditMixin, 
    TenantAwareMixin,
    # New combination mixins
    SoftDeleteAuditMixin,
    TenantAwareSoftDeleteMixin,
    CompleteMixin,  # All mixins combined
)
```

### FastAPI Dependencies

```python
# OLD
from dotmac_shared.database.deps import get_db, get_read_session

# NEW
from dotmac.database import get_db, get_read_session, get_write_session
```

### RLS and Schema Management

```python
# OLD
from dotmac_shared.database.rls import set_rls_context, create_tenant_schema

# NEW
from dotmac.database import (
    set_rls_context,
    create_tenant_schema,
    RLSPolicyManager,  # New helper class
)
```

### Caching (New Feature)

```python
# NEW - Redis-based smart caching
from dotmac.database import SmartCache, get_redis_client, CacheStats
```

### Distributed Locking (New Feature)

```python
# NEW - Redis and PostgreSQL locking
from dotmac.database import RedisLock, PgAdvisoryLock
```

### Alembic Helpers (New Feature)

```python
# NEW - Migration utilities
from dotmac.database import (
    get_alembic_config_url,
    include_object,
    run_post_migration_hooks,
    MigrationHelpers,
)
```

## API Changes

### Engine Configuration

```python
# OLD
engine = create_async_engine(
    "postgresql://...", 
    echo=True,
    pool_size=10
)

# NEW - Same interface, improved defaults
engine = create_async_engine(
    "postgresql://...",
    echo=True,
    pool_size=10,
    pool_pre_ping=True,  # Now default
    pool_recycle=3600,   # Now default
)

# NEW - DatabaseURL helper
from dotmac.database import DatabaseURL

url = DatabaseURL(
    driver="postgresql+asyncpg",
    host="localhost",
    database="mydb",
    username="user",
    password="pass"
)
engine = create_async_engine(url)
```

### BaseModel Enhancements

```python
# Models work the same way
class User(BaseModel):
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))

# NEW - Enhanced combination mixins
class Customer(BaseModel, CompleteMixin):  # Includes soft-delete, audit, tenant-aware
    __tablename__ = "customers"
    
    name: Mapped[str] = mapped_column(String(100))
    # Automatically includes: is_active, deleted_at, created_by_id, updated_by_id, tenant_id
```

### Soft Delete Queries

```python
# OLD - Manual queries
active_users = session.execute(
    select(User).where(User.is_active == True)
).scalars().all()

# NEW - Same functionality, but now with scope method
active_users = await User.active(session).scalars().all()  # If using query scopes
```

## New Features

### 1. Smart Caching

```python
from dotmac.database import SmartCache

cache = SmartCache()

# Simple caching
await cache.set("user:123", user_data, ttl=300)
user_data = await cache.get("user:123")

# Pattern invalidation
await cache.invalidate_pattern("user:*")

# Statistics tracking
stats = await cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.2%}")
```

### 2. Distributed Locking

```python
from dotmac.database import RedisLock, PgAdvisoryLock

# Redis distributed lock
async with RedisLock("import-data", ttl=60) as lock:
    if lock.acquired:
        # Perform exclusive operation
        await import_data()

# PostgreSQL advisory lock
async with PgAdvisoryLock("migration-lock", session) as lock:
    if lock.acquired:
        # Database-level coordination
        await run_migration()
```

### 3. Enhanced RLS Management

```python
from dotmac.database import RLSPolicyManager

manager = RLSPolicyManager(session)

# Enable RLS and create tenant policy in one call
await manager.setup_tenant_rls(
    "users", 
    tenant_column="tenant_id"
)

# Create indexes optimized for tenant queries
await manager.create_indexes_for_tenant_aware_table(
    "users",
    additional_columns=["email", "created_at"]
)
```

### 4. Alembic Integration

```python
# In alembic/env.py
from dotmac.database.alembic import get_alembic_config_url, include_object

# Database URL with environment precedence
config.set_main_option(
    'sqlalchemy.url',
    get_alembic_config_url()  # Checks DATABASE_URL env var
)

# Smart object filtering
context.configure(
    include_object=lambda obj, name, type_, reflected, compare_to:
        include_object(
            obj, name, type_, reflected, compare_to,
            skip_schemas=['pg_catalog', 'information_schema'],
            skip_indexes=True
        )
)
```

## Breaking Changes

### 1. Package Structure

- All imports must be updated to use `dotmac.database`
- Optional features require extra dependencies

### 2. Default Settings

```python
# OLD - No defaults for connection pooling
engine = create_async_engine(url)  # Basic settings

# NEW - Production-ready defaults
engine = create_async_engine(url)  # Includes pool_pre_ping=True, pool_recycle=3600
```

### 3. Exception Handling

```python
# OLD - Generic exceptions
try:
    await operation()
except Exception as e:
    # Handle generic database error

# NEW - Specific exception types
from dotmac.database import DatabaseError, TransactionError, ValidationError

try:
    await operation() 
except TransactionError as e:
    # Handle transaction-specific error
except ValidationError as e:
    # Handle validation error
except DatabaseError as e:
    # Handle general database error
```

## Migration Steps

1. **Install the new package:**
   ```bash
   pip install "dotmac-database[all]"
   ```

2. **Update imports gradually:**
   - Legacy shims provide temporary compatibility
   - Update imports file by file
   - Test thoroughly after each change

3. **Update configuration:**
   - Review engine configuration for new defaults
   - Add optional extras as needed
   - Update dependency injection setup

4. **Test thoroughly:**
   - Run existing tests to ensure compatibility
   - Test new features incrementally
   - Verify performance with new defaults

5. **Remove legacy dependencies:**
   - Once migration is complete, remove old imports
   - Update requirements.txt/pyproject.toml
   - Remove deprecated code

## Compatibility Period

- Legacy shims will be maintained for **6 months**
- Deprecation warnings will be shown for legacy imports
- After 6 months, legacy imports will be removed

## Support

For migration assistance:
- Check the comprehensive test suite for usage examples
- Review the package documentation
- Open an issue for specific migration problems

## Performance Improvements

The new package includes several performance improvements:

- Better connection pool defaults
- Smart caching with compression
- Optimized query patterns for tenant-aware models
- Efficient distributed locking primitives
- Improved error handling with specific exception types

Your applications should see improved performance with minimal code changes.