# dotmac-database

**Database foundation package for DotMac Framework**

A comprehensive, standalone database package providing declarative base models, mixins, async engine/session management, RLS helpers, caching utilities, and coordination primitives for PostgreSQL-based applications.

## Features

- **🏗️ Declarative Base & Mixins**: Common patterns for models with audit trails, soft deletes, and tenant awareness
- **⚡ Async Engine & Sessions**: SQLAlchemy 2.0+ async support with connection pooling and lifecycle management
- **🚀 FastAPI Integration**: Ready-to-use dependency injection for database sessions
- **🔐 Row-Level Security**: Generic RLS helpers for tenant isolation and security policies
- **📊 Schema-per-Tenant**: Dynamic schema switching and search path management
- **🗄️ Smart Caching**: Redis-based caching with pattern invalidation and statistics
- **🔒 Distributed Coordination**: Redis and PostgreSQL advisory locks for coordination
- **📦 Alembic Integration**: Migration helpers and hooks for complex database operations

## Quick Start

### Installation

```bash
# Base package
pip install dotmac-database

# With FastAPI support
pip install dotmac-database[fastapi]

# With Redis caching
pip install dotmac-database[redis]

# With Alembic migrations
pip install dotmac-database[alembic]

# With PostgreSQL drivers
pip install dotmac-database[pg]  # psycopg
pip install dotmac-database[asyncpg]  # asyncpg

# Everything included
pip install dotmac-database[all]
```

### Basic Usage

```python
from dotmac.database import Base, BaseModel, create_async_engine, get_db
from sqlalchemy import Column, String

# Create your models
class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)

# Setup async engine
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")

# Use with FastAPI
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

## Core Components

### Base Models and Mixins

```python
from dotmac.database import Base, BaseModel, SoftDeleteMixin, AuditMixin, TenantAwareMixin

# Base model with id, created_at, updated_at
class Product(BaseModel):
    __tablename__ = "products"
    
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

# Soft delete support
class Category(BaseModel, SoftDeleteMixin):
    __tablename__ = "categories"
    
    name = Column(String(255), nullable=False)
    
    # Inherits is_active, deleted_at fields
    # Use .soft_delete() and .is_deleted property

# Audit trail support
class Order(BaseModel, AuditMixin):
    __tablename__ = "orders"
    
    total = Column(Numeric(10, 2), nullable=False)
    
    # Inherits created_by, updated_by, request_id fields

# Multi-tenant support
class TenantData(BaseModel, TenantAwareMixin):
    __tablename__ = "tenant_data"
    
    content = Column(Text)
    
    # Inherits tenant_id field with proper indexing
```

### Engine and Session Management

```python
from dotmac.database import create_async_engine, with_async_session
from sqlalchemy.ext.asyncio import async_sessionmaker

# Create engine with sensible defaults
engine = create_async_engine(
    "postgresql+asyncpg://localhost/mydb",
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set via SQLALCHEMY_ECHO env var
)

# Create session factory
async_session = async_sessionmaker(engine)

# Use context manager
async with with_async_session(async_session) as session:
    result = await session.execute(select(User))
    users = result.scalars().all()
    # Automatic commit/rollback handling
```

### FastAPI Dependencies

```python
from dotmac.database import get_db, get_read_session, get_write_session
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()
    return user

@app.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_read_session)  # Read-only session
):
    result = await db.execute(select(User))
    return result.scalars().all()
```

### Row-Level Security (RLS)

```python
from dotmac.database import set_rls_context, clear_rls_context

@app.middleware("http")
async def tenant_rls_middleware(request: Request, call_next):
    tenant_id = extract_tenant_id(request)  # Your logic
    
    async with get_db() as session:
        # Set RLS context for tenant isolation
        await set_rls_context(
            session,
            tenant_id=tenant_id,
            user_id=request.user.id,
            client_ip=request.client.host
        )
        
        response = await call_next(request)
        
        # Clear context (optional)
        await clear_rls_context(session)
        
        return response
```

### Schema-per-Tenant

```python
from dotmac.database import set_schema_search_path

async def get_tenant_session(tenant_id: str):
    async with with_async_session(async_session) as session:
        # Switch to tenant-specific schema
        await set_schema_search_path(session, tenant_id=tenant_id)
        yield session
        
        # Automatic cleanup on exit

@app.get("/tenant-data")
async def get_tenant_data(
    tenant_id: str,
    session: AsyncSession = Depends(get_tenant_session)
):
    # Queries automatically use tenant_{tenant_id} schema
    result = await session.execute(select(TenantData))
    return result.scalars().all()
```

### Smart Caching

```python
from dotmac.database.caching import SmartCache, get_redis_client

# Configure Redis
redis_client = get_redis_client()  # Uses REDIS_URL env var

# Create cache instance
user_cache = SmartCache(namespace="users", ttl=300)

async def get_user_cached(user_id: int):
    # Try cache first
    cached = await user_cache.get("user", user_id)
    if cached:
        return cached
    
    # Fetch from database
    async with get_db() as session:
        user = await session.get(User, user_id)
        
        # Cache the result
        await user_cache.set("user", user_id, user.dict())
        return user

# Invalidate cache patterns
await user_cache.invalidate_pattern("user:*")

# Get cache statistics
stats = await user_cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

### Distributed Coordination

```python
from dotmac.database.coordination import RedisLock, PgAdvisoryLock

# Redis-based distributed lock
async with RedisLock("import:user-data", ttl=60) as lock:
    if lock.acquired:
        # Perform exclusive operation
        await import_user_data()
    else:
        raise HTTPException(409, "Import already in progress")

# PostgreSQL advisory lock
async with PgAdvisoryLock(12345) as lock:
    if lock.acquired:
        # Database-level coordination
        await update_global_counters()
```

### Alembic Integration

```python
# In your alembic/env.py
from dotmac.database.alembic import get_alembic_config_url, include_object

# Database URL with environment precedence
config.set_main_option("sqlalchemy.url", get_alembic_config_url())

# Skip certain objects during migration
def include_object_callback(object, name, type_, reflected, compare_to):
    return include_object(
        object, name, type_, reflected, compare_to,
        skip_schemas={"information_schema", "pg_catalog"},
        skip_views=True
    )

context.configure(
    include_object=include_object_callback,
    # ... other options
)
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
SQLALCHEMY_ECHO=false

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_RECYCLE=3600
```

### Engine Configuration

```python
from dotmac.database import create_async_engine

engine = create_async_engine(
    database_url,
    # Connection pool
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    
    # Logging
    echo=False,  # or set SQLALCHEMY_ECHO=true
    
    # Performance
    connect_args={
        "command_timeout": 60,
        "server_settings": {
            "jit": "off",
            "application_name": "dotmac-app"
        }
    }
)
```

## Advanced Usage

### Custom Base Model

```python
from dotmac.database import Base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String
from typing import Optional

class CustomBase(Base):
    """Custom base with additional common fields."""
    
    # Add organization-wide fields
    organization_id: Mapped[Optional[str]] = mapped_column(String(50))
    
    @classmethod
    def get_table_prefix(cls) -> str:
        """Override for custom table naming."""
        return "myorg_"

# Use custom base
class MyModel(CustomBase):
    __tablename__ = "my_models"  # Will be "myorg_my_models"
    
    name: Mapped[str] = mapped_column(String(255))
```

### Multi-Database Setup

```python
# Multiple engines for read/write splitting
read_engine = create_async_engine("postgresql+asyncpg://readonly@db-replica/mydb")
write_engine = create_async_engine("postgresql+asyncpg://readwrite@db-primary/mydb")

read_session = async_sessionmaker(read_engine)
write_session = async_sessionmaker(write_engine)

# Custom dependencies
async def get_read_db():
    async with read_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_write_db():
    async with write_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Complex Caching Patterns

```python
from dotmac.database.caching import SmartCache
import json

# Multi-level caching
l1_cache = SmartCache("users", ttl=60)      # 1 minute
l2_cache = SmartCache("users-l2", ttl=3600) # 1 hour

async def get_user_multilevel(user_id: int):
    # L1 cache
    user = await l1_cache.get("user", user_id)
    if user:
        return user
    
    # L2 cache
    user = await l2_cache.get("user", user_id)
    if user:
        # Populate L1
        await l1_cache.set("user", user_id, user)
        return user
    
    # Database
    user = await fetch_user_from_db(user_id)
    
    # Populate both levels
    await l1_cache.set("user", user_id, user)
    await l2_cache.set("user", user_id, user)
    
    return user

# Cache warming
async def warm_user_cache(user_ids: list[int]):
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = result.scalars().all()
        
        for user in users:
            await l1_cache.set("user", user.id, user.dict())
```

## Testing

### Test Utilities

```python
import pytest
from dotmac.database import Base, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = async_sessionmaker(test_engine)
    
    async with async_session() as session:
        yield session
        await session.rollback()

# Use in tests
async def test_user_creation(test_session):
    user = User(name="Test User", email="test@example.com")
    test_session.add(user)
    await test_session.flush()
    
    assert user.id is not None
    assert user.created_at is not None
```

## Migration from dotmac_shared.database

This package replaces `dotmac_shared.database` with enhanced functionality and better separation of concerns.

### Import Changes

```python
# Old imports
from dotmac_shared.database.base import Base, BaseModel
from dotmac_shared.database.caching import get_redis_client

# New imports
from dotmac.database import Base, BaseModel
from dotmac.database.caching import get_redis_client
```

### Breaking Changes

1. **Engine Creation**: Now requires explicit async engine creation
2. **Session Management**: Uses async context managers
3. **Caching**: SmartCache API has been enhanced with statistics
4. **Mixins**: TenantAwareMixin is now framework-agnostic

See [MIGRATION.md](MIGRATION.md) for detailed migration instructions.

## API Reference

### Core Classes

- `Base`: SQLAlchemy DeclarativeBase
- `BaseModel`: Base model with id, timestamps, and common functionality
- `SoftDeleteMixin`: Soft delete support with is_active flag
- `AuditMixin`: Audit trail with created_by, updated_by, request_id
- `TenantAwareMixin`: Multi-tenant support with tenant_id

### Engine & Session Functions

- `create_async_engine(url, **kwargs)`: Create configured async engine
- `with_async_session(sessionmaker)`: Async context manager for sessions
- `get_db()`: FastAPI dependency for database sessions
- `get_read_session()`, `get_write_session()`: Specialized session dependencies

### RLS & Schema Functions

- `set_rls_context(session, tenant_id, user_id, client_ip)`: Configure RLS context
- `set_schema_search_path(session, tenant_id)`: Set tenant schema path
- `clear_rls_context(session)`: Clear RLS configuration

### Caching Classes

- `SmartCache(namespace, ttl)`: Redis-based caching with statistics
- `get_redis_client()`: Get configured Redis client
- `get_redis_pool()`: Get Redis connection pool

### Coordination Classes

- `RedisLock(name, ttl)`: Redis-based distributed lock
- `PgAdvisoryLock(key)`: PostgreSQL advisory lock

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite: `pytest`
5. Submit a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.

## Support

- **Documentation**: https://docs.dotmac.com/database
- **Issues**: https://github.com/dotmac-framework/dotmac-database/issues
- **Discussions**: https://github.com/dotmac-framework/dotmac-database/discussions