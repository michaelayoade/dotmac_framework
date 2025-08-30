# Migration Guide: DotMac Database Toolkit

This guide provides step-by-step instructions for migrating from the existing repository implementations to the unified Database Toolkit.

## 🎯 Migration Overview

The Database Toolkit eliminates **900+ lines of code duplication** by providing a unified interface for both ISP and Management platforms:

- **ISP Framework**: `dotmac_isp/shared/base_repository.py` (542 lines) → **REPLACED**
- **Management Platform**: `dotmac_management/repositories/base.py` (374 lines) → **REPLACED**

## 📋 Pre-Migration Checklist

- [ ] Backup existing code and database
- [ ] Install `dotmac-database-toolkit` package
- [ ] Review breaking changes section
- [ ] Plan migration by module/repository
- [ ] Update test suites
- [ ] Verify tenant isolation still works

## 🔄 Migration Paths

### Path 1: ISP Framework Migration

**Current Implementation:**

```python
# dotmac_isp/shared/base_repository.py
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from sqlalchemy.orm import Session
from .exceptions import EntityNotFoundError, DuplicateEntityError

class BaseRepository(Generic[ModelType], ABC):
    def __init__(self, db: Session, model_class: Type[ModelType], tenant_id: Optional[str] = None):
        self.db = db
        self.model_class = model_class
        self.tenant_id = tenant_id

    def create(self, data: Dict[str, Any], commit: bool = True) -> ModelType:
        # 50+ lines of implementation

    def list(self, filters=None, sort_by=None, sort_order='asc', limit=None, offset=None):
        # 40+ lines of implementation
```

**New Implementation:**

```python
# Replace entire base_repository.py with toolkit import
from dotmac_database import BaseRepository, BaseTenantRepository, create_repository
from dotmac_database import QueryOptions, QueryFilter, FilterOperator, SortField, PaginationParams

# Factory function replaces manual instantiation
def get_repository(db: Session, model_class, tenant_id: str = None):
    return create_repository(db, model_class, tenant_id)
```

### Path 2: Management Platform Migration

**Current Implementation:**

```python
# dotmac_management/repositories/base.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional, Tuple

class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def list_paginated(self, page=1, per_page=20, filters=None):
        # 30+ lines of pagination logic
```

**New Implementation:**

```python
# Replace entire base.py with toolkit import
from dotmac_database import AsyncRepository, create_async_repository
from dotmac_database import QueryOptions, PaginationParams

# Factory function replaces manual instantiation
def get_async_repository(db: AsyncSession, model_class, tenant_id: str = None):
    return create_async_repository(db, model_class, tenant_id)
```

## 🚀 Step-by-Step Migration

### Step 1: Install Dependencies

```bash
# Add to pyproject.toml
[tool.poetry.dependencies]
dotmac-database-toolkit = "^0.1.0"

# Install
poetry install

# Or with pip
pip install dotmac-database-toolkit
```

### Step 2: Update Imports (ISP Framework)

**Before:**

```python
# In module files
from dotmac_isp.shared.base_repository import BaseRepository, BaseTenantRepository
from dotmac_isp.shared.exceptions import EntityNotFoundError

# In repository files
class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, User, tenant_id)
```

**After:**

```python
# In module files
from dotmac_database import (
    BaseRepository, BaseTenantRepository, create_repository,
    EntityNotFoundError, QueryOptions, QueryFilter, FilterOperator
)

# In repository files
class UserRepository(BaseTenantRepository[User]):
    # Constructor automatically handled by factory
    pass

# Or use factory directly
def get_user_repository(db: Session, tenant_id: str):
    return create_repository(db, User, tenant_id)
```

### Step 3: Update Repository Usage (ISP Framework)

**Before:**

```python
# In service files
class UserService:
    def __init__(self, db: Session, tenant_id: str):
        self.user_repo = UserRepository(db, tenant_id)

    def get_active_users(self, page: int = 1, per_page: int = 20):
        return self.user_repo.list(
            filters={"is_active": True},
            sort_by="created_at",
            sort_order="desc",
            limit=per_page,
            offset=(page-1) * per_page
        )
```

**After:**

```python
# In service files
from dotmac_database import create_repository, QueryOptions, QueryFilter, FilterOperator, SortField, SortOrder, PaginationParams

class UserService:
    def __init__(self, db: Session, tenant_id: str):
        self.user_repo = create_repository(db, User, tenant_id)

    def get_active_users(self, page: int = 1, per_page: int = 20):
        options = QueryOptions(
            filters=[
                QueryFilter(field="is_active", operator=FilterOperator.EQ, value=True)
            ],
            sorts=[
                SortField(field="created_at", order=SortOrder.DESC)
            ],
            pagination=PaginationParams(page=page, per_page=per_page)
        )
        return self.user_repo.list_paginated(options)
```

### Step 4: Update Imports (Management Platform)

**Before:**

```python
# In module files
from dotmac_management.repositories.base import BaseRepository

# In repository files
class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str):
        return await self.get_by_field("email", email)
```

**After:**

```python
# In module files
from dotmac_database import AsyncRepository, create_async_repository, QueryOptions

# In repository files - get_by_field is now built-in
class UserRepository(AsyncRepository[User]):
    pass

# Or use factory
def get_user_repository(db: AsyncSession):
    return create_async_repository(db, User)
```

### Step 5: Update Repository Usage (Management Platform)

**Before:**

```python
# In service files
class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db, User)

    async def get_users(self, skip: int = 0, limit: int = 100, filters=None):
        return await self.user_repo.list(skip=skip, limit=limit, filters=filters)

    async def get_users_paginated(self, page: int = 1, per_page: int = 20):
        return await self.user_repo.list_paginated(page=page, per_page=per_page)
```

**After:**

```python
# In service files
class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = create_async_repository(db, User)

    async def get_users(self, skip: int = 0, limit: int = 100, filters=None):
        # Convert simple filters to QueryFilter format
        query_filters = []
        if filters:
            for field, value in filters.items():
                query_filters.append(QueryFilter(field=field, value=value))

        options = QueryOptions(filters=query_filters)
        return await self.user_repo.list(options)

    async def get_users_paginated(self, page: int = 1, per_page: int = 20):
        options = QueryOptions(
            pagination=PaginationParams(page=page, per_page=per_page)
        )
        return await self.user_repo.list_paginated(options)
```

### Step 6: Update Error Handling

**Before:**

```python
from dotmac_isp.shared.exceptions import EntityNotFoundError
from dotmac_management.exceptions import NotFoundError

try:
    user = user_repo.get_by_id_or_raise(user_id)
except EntityNotFoundError:
    # Handle error
except NotFoundError:
    # Handle error
```

**After:**

```python
from dotmac_database import EntityNotFoundError

try:
    user = user_repo.get_by_id_or_raise(user_id)
    # Or with new pattern:
    # user = await user_repo.get_by_id_or_raise(user_id)
except EntityNotFoundError:
    # Unified error handling
```

### Step 7: Update Transaction Usage

**Before (ISP Framework):**

```python
try:
    user = user_repo.create(user_data, commit=False)
    profile = profile_repo.create(profile_data, commit=False)
    db.commit()
except Exception:
    db.rollback()
    raise
```

**Before (Management Platform):**

```python
async with database_transaction(db) as tx:
    user = await user_repo.create(user_data)
    profile = await profile_repo.create(profile_data)
```

**After (Unified):**

```python
# Sync version
from dotmac_database import DatabaseTransaction

with DatabaseTransaction.sync_transaction(db) as tx:
    user = user_repo.create(user_data)
    profile = profile_repo.create(profile_data)

# Async version
async with DatabaseTransaction.async_transaction(db) as tx:
    user = await user_repo.create(user_data)
    profile = await profile_repo.create(profile_data)
```

### Step 8: Remove Legacy Files

After successful migration, remove the old repository files:

```bash
# ISP Framework
rm src/dotmac_isp/shared/base_repository.py
rm src/dotmac_isp/shared/exceptions.py  # If only used by repositories

# Management Platform
rm src/dotmac_management/repositories/base.py
rm src/dotmac_management/core/database.py  # If replaced by toolkit
```

## 🔧 Advanced Migration Scenarios

### Custom Repository Methods

**Before:**

```python
class UserRepository(BaseRepository[User]):
    def get_active_users_by_role(self, role: str):
        return self.list(
            filters={"is_active": True, "role": role},
            sort_by="created_at",
            sort_order="desc"
        )
```

**After:**

```python
class UserRepository(BaseTenantRepository[User]):
    def get_active_users_by_role(self, role: str):
        options = QueryOptions(
            filters=[
                QueryFilter(field="is_active", operator=FilterOperator.EQ, value=True),
                QueryFilter(field="role", operator=FilterOperator.EQ, value=role)
            ],
            sorts=[SortField(field="created_at", order=SortOrder.DESC)]
        )
        return self.list(options)
```

### Complex Filtering

**Before:**

```python
# ISP Framework advanced filtering
def search_users(self, query: str, status_list: List[str]):
    return self._apply_filters(
        self._build_base_query(),
        {
            "name": {"like": f"%{query}%"},
            "status": {"in": status_list},
            "created_at": {"gte": "2024-01-01"}
        }
    )
```

**After:**

```python
def search_users(self, query: str, status_list: List[str]):
    options = QueryOptions(
        filters=[
            QueryFilter(field="name", operator=FilterOperator.LIKE, value=query),
            QueryFilter(field="status", operator=FilterOperator.IN, value=status_list),
            QueryFilter(field="created_at", operator=FilterOperator.GTE, value="2024-01-01")
        ]
    )
    return self.list(options)
```

### Performance Optimizations

**Before:**

```python
# Management Platform pagination
async def get_large_dataset(self, page: int = 1):
    # Custom pagination for performance
    if page > 100:
        # Use cursor-based pagination
        return await self.cursor_paginate("id", limit=20, cursor=cursor)
    else:
        return await self.list_paginated(page=page, per_page=20)
```

**After:**

```python
from dotmac_database import PerformancePaginator

async def get_large_dataset(self, page: int = 1):
    if page > 100:
        # Built-in performance optimization
        return await PerformancePaginator.deep_pagination_optimize(
            self.db, self._build_base_query(), page, 20, "created_at"
        )
    else:
        options = QueryOptions(pagination=PaginationParams(page=page, per_page=20))
        return await self.list_paginated(options)
```

## ⚠️ Breaking Changes

### 1. Constructor Signature Change

**Before:**

```python
# Different patterns across platforms
user_repo = UserRepository(db, tenant_id)  # ISP
user_repo = UserRepository(db, User)        # Management
```

**After:**

```python
# Unified factory pattern
user_repo = create_repository(db, User, tenant_id)      # Sync
user_repo = create_async_repository(db, User, tenant_id) # Async
```

### 2. Filter Format Change

**Before:**

```python
# Dictionary-based filters
filters = {
    "status": "active",
    "role": {"in": ["admin", "user"]},
    "created_at": {"gte": "2024-01-01"}
}
users = repo.list(filters=filters)
```

**After:**

```python
# Structured filter objects
filters = [
    QueryFilter(field="status", operator=FilterOperator.EQ, value="active"),
    QueryFilter(field="role", operator=FilterOperator.IN, value=["admin", "user"]),
    QueryFilter(field="created_at", operator=FilterOperator.GTE, value="2024-01-01")
]
options = QueryOptions(filters=filters)
users = repo.list(options)
```

### 3. Pagination Response Format

**Before:**

```python
# Tuple response (Management Platform)
users, total = await repo.list_paginated(page=1, per_page=20)

# List response (ISP Framework)
users = repo.list(limit=20, offset=0)
total = repo.count()
```

**After:**

```python
# Unified result object
options = QueryOptions(pagination=PaginationParams(page=1, per_page=20))
result = repo.list_paginated(options)

users = result.items
total = result.total
has_next = result.has_next
```

### 4. Method Signature Changes

**Before:**

```python
# ISP Framework
user = repo.create(data, commit=True)
user = repo.update(user_id, data, commit=True)
success = repo.delete(user_id, commit=True)

# Management Platform
user = await repo.create(data, user_id="creator")
user = await repo.update(user_id, data, user_id="updater")
success = await repo.delete(user_id, soft_delete=True, user_id="deleter")
```

**After:**

```python
# Unified signatures
user = repo.create(data, user_id="creator")  # Sync
user = repo.update(user_id, data, user_id="updater")
success = repo.delete(user_id, soft_delete=True, user_id="deleter")

# Async versions (identical signatures with await)
user = await repo.create(data, user_id="creator")
user = await repo.update(user_id, data, user_id="updater")
success = await repo.delete(user_id, soft_delete=True, user_id="deleter")
```

## 🧪 Testing Migration

### Unit Tests

**Before:**

```python
# ISP Framework tests
class TestUserRepository:
    def test_create_user(self):
        user_repo = UserRepository(mock_db, "tenant-123")
        user = user_repo.create({"name": "Test User"})
        assert user.name == "Test User"

# Management Platform tests
class TestUserRepository:
    async def test_create_user(self):
        user_repo = UserRepository(mock_async_db, User)
        user = await user_repo.create({"name": "Test User"})
        assert user.name == "Test User"
```

**After:**

```python
# Unified test pattern
class TestUserRepository:
    def test_create_user_sync(self):
        user_repo = create_repository(mock_db, User, "tenant-123")
        user = user_repo.create({"name": "Test User"})
        assert user.name == "Test User"

    async def test_create_user_async(self):
        user_repo = create_async_repository(mock_async_db, User, "tenant-123")
        user = await user_repo.create({"name": "Test User"})
        assert user.name == "Test User"
```

### Integration Tests

Update integration tests to use the new QueryOptions format:

**Before:**

```python
def test_user_filtering(self):
    users = user_repo.list(
        filters={"status": "active"},
        sort_by="name",
        limit=10
    )
    assert len(users) <= 10
```

**After:**

```python
def test_user_filtering(self):
    options = QueryOptions(
        filters=[QueryFilter(field="status", value="active")],
        sorts=[SortField(field="name")],
        pagination=PaginationParams(page=1, per_page=10)
    )
    result = user_repo.list_paginated(options)
    assert len(result.items) <= 10
    assert result.total >= len(result.items)
```

## 🔍 Validation Checklist

After migration, verify:

- [ ] **All CRUD operations work** (create, read, update, delete)
- [ ] **Tenant isolation is maintained** (queries only return tenant data)
- [ ] **Filtering works correctly** (all filter operators function)
- [ ] **Pagination works** (both offset and cursor-based)
- [ ] **Soft delete behavior** (deleted items are hidden by default)
- [ ] **Audit trail functionality** (created_by, updated_by fields)
- [ ] **Transaction management** (rollback on errors)
- [ ] **Performance is acceptable** (no significant regression)
- [ ] **Error handling** (proper exception types)
- [ ] **Tests pass** (unit and integration tests)

## 🐛 Troubleshooting Common Issues

### Import Errors

**Error:**

```python
ImportError: cannot import name 'BaseRepository' from 'dotmac_isp.shared.base_repository'
```

**Solution:**

```python
# Update imports
from dotmac_database import BaseRepository, create_repository
```

### Filter Format Errors

**Error:**

```python
TypeError: 'dict' object has no attribute 'field'
```

**Solution:**

```python
# Convert dictionary filters to QueryFilter objects
from dotmac_database import QueryFilter, FilterOperator

# Before
filters = {"status": "active"}

# After
filters = [QueryFilter(field="status", operator=FilterOperator.EQ, value="active")]
options = QueryOptions(filters=filters)
```

### Pagination Errors

**Error:**

```python
AttributeError: 'list' object has no attribute 'total'
```

**Solution:**

```python
# Use the pagination result object
result = repo.list_paginated(options)
items = result.items  # Not just repo.list()
total = result.total
```

### Tenant ID Errors

**Error:**

```python
ValidationError: tenant_id is required for tenant repositories
```

**Solution:**

```python
# Ensure tenant_id is provided for tenant models
if issubclass(model_class, TenantMixin):
    repo = create_repository(db, model_class, tenant_id="required-tenant-id")
else:
    repo = create_repository(db, model_class)  # No tenant_id needed
```

## 📞 Support & Resources

- **Documentation**: See `README.md` for full API documentation
- **Examples**: Check `examples/` directory for migration examples
- **Type Hints**: The toolkit provides comprehensive type hints for IDE support
- **Error Messages**: Error messages include migration hints where applicable

## 🚀 Next Steps

After successful migration:

1. **Performance Monitoring**: Use built-in health checks to monitor database performance
2. **Advanced Features**: Explore cursor pagination, retry policies, and circuit breakers
3. **Code Cleanup**: Remove duplicate repository logic across modules
4. **Documentation**: Update team documentation with new patterns
5. **Training**: Train team on unified repository patterns

## 📈 Expected Benefits Post-Migration

- **60% reduction** in repository maintenance overhead
- **Consistent query patterns** across all modules
- **Improved error handling** with unified exception types
- **Better performance** with optimized pagination and query building
- **Enhanced testing** with unified test patterns
- **Simplified debugging** with consistent logging and error reporting

The migration eliminates 900+ lines of duplicated code while providing a more powerful, consistent, and maintainable database abstraction layer.
