# DotMac Core - Developer Handbook

## Overview

DotMac Core provides the foundational layer for the DotMac Framework, consolidating common patterns and eliminating code duplication across packages. This handbook covers essential patterns, best practices, and usage guidelines.

## Key Components

### Database Models

#### BaseModel vs DBBaseModel

**Important**: DotMac Core defines two different "BaseModel" classes:

- **`DBBaseModel`** - SQLAlchemy base class for database models
- **`PydanticBaseModel`** - Pydantic's BaseModel (imported as alias)
- **`BaseModel`** - Compatibility alias for `DBBaseModel`

```python
# Correct usage for database models
from dotmac.core import DBBaseModel

class User(DBBaseModel):
    name: Mapped[str] = mapped_column(String(100))

# Correct usage for schemas/validation
from pydantic import BaseModel  # Import directly

class UserSchema(BaseModel):
    name: str
    email: str
```

#### Database Mixins

DotMac Core provides several mixins for common database patterns:

```python
from dotmac.core import DBBaseModel, UUIDMixin, TimestampMixin, AuditMixin, TenantMixin

# Basic model with UUID and timestamps
class BasicModel(DBBaseModel):
    # Inherits: id (UUID), created_at, updated_at
    pass

# Tenant-isolated model
class TenantModel(DBBaseModel, TenantMixin):
    # Inherits: id (UUID), created_at, updated_at, tenant_id
    pass

# Full audit trail model  
class AuditedModel(DBBaseModel, AuditMixin):
    # Inherits: id (UUID), created_at, updated_at, created_by, updated_by, deleted_at
    pass
```

##### Available Mixins

| Mixin | Provides | Use Case |
|-------|----------|----------|
| `UUIDMixin` | `id: UUID` (primary key) | Unique identifiers |
| `TimestampMixin` | `created_at`, `updated_at` | Record lifecycle |
| `AuditMixin` | `created_by`, `updated_by`, `deleted_at` | Audit trails |
| `TenantMixin` | `tenant_id` + index | Multi-tenancy |
| `TableNamingMixin` | Auto snake_case table names | Consistent naming |

#### Table Naming

Table names are automatically generated from class names:

```python
class UserProfile(DBBaseModel):
    # Automatically creates table: user_profile
    pass

# Override automatic naming if needed
class CustomModel(DBBaseModel):
    __tablename__ = "custom_table_name"  # Explicit override
```

#### Tenant Isolation

For multi-tenant applications, use `TenantMixin`:

```python
from dotmac.core import TenantBaseModel  # Includes TenantMixin

class Customer(TenantBaseModel):
    name: Mapped[str] = mapped_column(String(100))
    # Automatically includes tenant_id with proper indexing
```

### Repository Pattern

Use the provided repository base classes for consistent data access:

```python
from dotmac.core import BaseRepository, AsyncRepository

class UserRepository(AsyncRepository):
    """Async repository for User model."""
    
    async def find_by_email(self, email: str) -> User | None:
        return await self.get_by_field("email", email)

class SyncUserRepository(BaseRepository):
    """Synchronous repository for User model."""
    
    def find_active_users(self) -> list[User]:
        return self.list(filters={"active": True})
```

### Pagination

Built-in pagination helpers are available:

```python
from dotmac.core.db_toolkit.pagination import PaginationParams, PaginationResult

# In your service/repository
def list_users(self, pagination: PaginationParams) -> PaginationResult[User]:
    return self.list_paginated(
        page=pagination.page,
        size=pagination.size,
        order_by="created_at"
    )
```

#### Pagination Schema Mapping

- **API Schema**: `page` (page number), `size` (items per page)
- **Internal Helpers**: `page`, `per_page` - both are supported

### Cache Patterns

DotMac Core provides sophisticated caching patterns:

```python
from dotmac.core import CacheService, cached, create_cache_service

# Service-level caching
cache_service = create_cache_service(backend="redis")

class UserService:
    def __init__(self, cache: CacheService):
        self.cache = cache
    
    @cached(ttl=300)  # Cache for 5 minutes
    async def get_user_profile(self, user_id: str) -> UserProfile:
        # This will be cached automatically
        return await self.user_repo.get_by_id(user_id)

# Manual cache operations
await cache_service.set("user:123", user_data, ttl=300)
user_data = await cache_service.get("user:123")
```

#### Tenant-Aware Caching

```python
from dotmac.core import TenantAwareCacheManager

cache = TenantAwareCacheManager(backend="redis")

# Automatically prefixes keys with tenant ID
await cache.set("user:123", data, tenant_id="tenant-a")
# Actual key: "tenant:tenant-a:user:123"
```

### Decorators

DotMac Core provides essential decorators for common patterns:

```python
from dotmac.core import standard_exception_handler, retry_on_failure, timeout

@standard_exception_handler
@retry_on_failure(max_retries=3, backoff_factor=2.0)
@timeout(seconds=30)
async def api_call(self):
    # Automatic exception logging, retry logic, and timeout protection
    return await external_service.call()
```

#### Rate Limiting

**Note**: The built-in rate limiter is process-local only:

```python
from dotmac.core.decorators import rate_limit

# WARNING: Process-local only - not suitable for distributed deployments
@rate_limit(max_calls=100, time_window=60)  
async def api_endpoint():
    return {"message": "success"}
```

For production deployments:
- Use platform-level rate limiting (nginx, API gateway)
- Implement Redis-backed rate limiter for shared state
- Use the built-in limiter as a first line of defense only

### Exception Handling

DotMac Core provides a comprehensive exception hierarchy:

```python
from dotmac.core import (
    DotMacError,           # Base exception
    ValidationError,       # Invalid input data
    AuthenticationError,   # Auth failures
    AuthorizationError,    # Permission denied
    DatabaseError,         # Database issues
    TenantError,          # Tenant-related issues
    ServiceError,         # Service communication
    BusinessRuleError,    # Business logic violations
    NotFoundError,        # Resource not found
)

# Repository error handling
class UserRepository(AsyncRepository):
    async def create_user(self, user_data: dict) -> User:
        try:
            return await self.create(user_data)
        except IntegrityError as e:
            if "email" in str(e):
                raise AlreadyExistsError("User with this email exists")
            raise DatabaseError("Failed to create user") from e
```

#### Exception Strategy Guidelines

| Exception Type | When to Use | Example |
|---------------|-------------|---------|
| `ValidationError` | Invalid input data | Email format invalid |
| `BusinessRuleError` | Business logic violation | Insufficient balance |
| `DatabaseError` | Database operation failure | Connection timeout |
| `NotFoundError` | Resource doesn't exist | User ID not found |
| `AuthorizationError` | Permission denied | Not tenant admin |

### Transaction Management

Use the transaction manager for complex operations:

```python
from dotmac.core import TransactionManager

async def transfer_funds(from_user_id: str, to_user_id: str, amount: float):
    async with TransactionManager() as tx:
        # All operations in this block are transactional
        await debit_account(from_user_id, amount, session=tx.session)
        await credit_account(to_user_id, amount, session=tx.session)
        await log_transfer(from_user_id, to_user_id, amount, session=tx.session)
        # Automatic commit on success, rollback on exception
```

### Tenant Context

Manage tenant context throughout your application:

```python
from dotmac.core import (
    get_current_tenant, 
    set_current_tenant, 
    require_current_tenant,
    TenantContext
)

# Set tenant context (usually in middleware)
await set_current_tenant("tenant-123")

# Access current tenant
tenant_id = get_current_tenant()

# Require tenant (raises TenantError if not set)
tenant_id = require_current_tenant()

# Advanced tenant context
context = TenantContext(
    tenant_id="tenant-123",
    user_id="user-456",
    roles=["admin", "user"]
)
```

## Guard Functions

Before using optional components, check availability:

```python
from dotmac.core import (
    is_database_available,
    is_schemas_available,
    require_database,
    require_schemas
)

# Check before use
if is_database_available():
    from dotmac.core import DBBaseModel, TransactionManager
else:
    logger.warning("Database toolkit not available")

# Require and fail fast
require_database()  # Raises ImportError if not available
# Safe to use database components now
```

## Configuration

DotMac Core provides configuration classes for common components:

```python
from dotmac.core import DatabaseConfig, CacheConfig, SecurityConfig

# Database configuration
db_config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="myapp",
    pool_size=20
)

# Cache configuration  
cache_config = CacheConfig(
    backend="redis",
    host="localhost",
    port=6379,
    ttl_default=300
)
```

## Best Practices

### 1. Model Design

```python
# Good: Clear inheritance hierarchy
class User(TenantBaseModel):
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))

# Good: Specific table name when needed
class UserLoginHistory(DBBaseModel):
    __tablename__ = "user_login_log"  # More specific than auto-generated
```

### 2. Repository Pattern

```python
# Good: Specific methods for business operations
class UserRepository(AsyncRepository):
    async def find_by_email(self, email: str) -> User | None:
        return await self.get_by_field("email", email)
    
    async def find_active_in_tenant(self, tenant_id: str) -> list[User]:
        return await self.list(filters={"tenant_id": tenant_id, "active": True})
```

### 3. Exception Handling

```python
# Good: Specific exception types with context
try:
    user = await user_repo.create(user_data)
except AlreadyExistsError:
    raise ValidationError("Email already registered")
except DatabaseError as e:
    logger.error("Database error creating user: %s", e)
    raise ServiceError("Unable to create user account")
```

### 4. Caching Strategy

```python
# Good: Cache at appropriate levels
class UserService:
    @cached(ttl=300, key="user:{user_id}")
    async def get_user_profile(self, user_id: str) -> UserProfile:
        # Expensive operation cached
        return await self.build_user_profile(user_id)
    
    async def update_user(self, user_id: str, data: dict) -> User:
        user = await self.user_repo.update(user_id, data)
        # Invalidate cache after update
        await self.cache.delete(f"user:{user_id}")
        return user
```

## Migration from Other Packages

### From dotmac_shared

```python
# Old
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import BaseModel

# New
from dotmac.core import standard_exception_handler
from dotmac.core import DBBaseModel  # Note: explicit naming
```

### From dotmac-database

```python
# Old
from dotmac_database.base import BaseRepository, TransactionManager

# New  
from dotmac.core import BaseRepository, TransactionManager
```

## Troubleshooting

### Import Errors

```python
# Check component availability
from dotmac.core import is_database_available

if not is_database_available():
    # Install missing dependencies
    # pip install 'dotmac-core[database]'
    pass
```

### Namespace Conflicts

```python
# Avoid confusion between Pydantic and SQLAlchemy BaseModel
from dotmac.core import DBBaseModel  # For database models
from pydantic import BaseModel       # For schemas

class UserModel(DBBaseModel):      # Database model
    pass

class UserSchema(BaseModel):       # Pydantic schema
    pass
```

### Performance Issues

1. **Use appropriate pagination**: Don't fetch all records
2. **Cache expensive operations**: User profiles, computed values
3. **Optimize database queries**: Use proper indexes, avoid N+1
4. **Monitor transaction scope**: Keep transactions short

## Examples

### Complete CRUD Service

```python
from dotmac.core import (
    DBBaseModel, TenantBaseModel, AsyncRepository, 
    ValidationError, NotFoundError, standard_exception_handler
)

class User(TenantBaseModel):
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))

class UserRepository(AsyncRepository[User]):
    async def find_by_email(self, email: str) -> User | None:
        return await self.get_by_field("email", email)

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    @standard_exception_handler
    async def create_user(self, email: str, name: str) -> User:
        if await self.repo.find_by_email(email):
            raise ValidationError("Email already exists")
        
        return await self.repo.create({
            "email": email,
            "name": name,
            "tenant_id": require_current_tenant()
        })
    
    async def get_user(self, user_id: str) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user
```

This handbook provides the essential patterns for using DotMac Core effectively. For more advanced usage, refer to the individual module documentation and examples in the codebase.