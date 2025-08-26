# Async/Sync Standardization Guide

## Executive Summary

Analysis of 610 files revealed 245 files with mixed async/sync patterns. The main findings:

- **18 asyncio.run() calls** - primarily in Celery tasks (acceptable pattern)
- **1517 async functions** and **1966 sync functions** - good async adoption
- **Multiple syntax errors** preventing full analysis - need immediate attention

## Pattern Categories

### ✅ Acceptable Patterns (No Action Needed)

#### 1. Celery Task Pattern
```python
@celery_app.task(bind=True, max_retries=3)
def process_subscription_renewals(self):
    """Celery task using asyncio.run() for async code."""
    import asyncio
    
    async def _process_renewals():
        # Async implementation
        pass
    
    return asyncio.run(_process_renewals())
```

**Why acceptable**: Celery currently doesn't support async task functions natively. This pattern enables gradual migration to async while maintaining Celery compatibility.

**Files using this pattern**:
- `management-platform/app/workers/tasks/billing_tasks.py`
- `management-platform/app/workers/tasks/plugin_tasks.py`

### ⚠️ Needs Standardization

#### 2. Service Layer Mixed Patterns
```python
class SomeService:
    async def async_method(self):
        pass
    
    def sync_method(self):  # Should be async
        # Mixed sync/async calls
        pass
```

**Recommendation**: Convert service classes to be fully async for consistency.

#### 3. Adapter Pattern (Currently Used)
```python
class AsyncServiceAdapter:
    def run_async(self, coro):
        return asyncio.run(coro)  # Acceptable for adapters only
```

## Standardization Rules

### For New Code
1. **Always use async/await** for new services and APIs
2. **Consistent async patterns** throughout a module
3. **Proper async context managers** for database operations
4. **Async test patterns** using pytest-asyncio

### For Existing Code Migration

#### Phase 1: Fix Syntax Errors (URGENT)
Many files have syntax errors preventing analysis:
```bash
# Run syntax check on all Python files
python3 -m py_compile filename.py
```

#### Phase 2: Service Layer Standardization
Convert service classes to fully async:

```python
# BEFORE (Mixed)
class BillingService:
    def create_invoice(self, data):  # sync
        # implementation
        pass
    
    async def process_payment(self, payment):  # async
        # implementation
        pass

# AFTER (Standardized)
class BillingService:
    async def create_invoice(self, data):  # async
        # implementation
        pass
    
    async def process_payment(self, payment):  # async
        # implementation
        pass
```

#### Phase 3: Repository Layer
Ensure all repository methods are async:
```python
class BaseRepository:
    async def create(self, data):
        async with self.session() as db:
            # async implementation
            pass
```

## Implementation Priority

### High Priority (Security & Stability)
1. **Fix all syntax errors** (245+ files affected)
2. **Standardize authentication services** to async
3. **Ensure billing services are fully async** (revenue critical)

### Medium Priority (Performance)
1. **Convert remaining service classes** to async
2. **Standardize database operations** to async patterns
3. **Update API endpoints** to consistent async patterns

### Low Priority (Code Quality)
1. **Convert utility functions** where beneficial
2. **Standardize test patterns** to async
3. **Update documentation** to reflect async patterns

## Code Examples

### Database Operations
```python
# Standardized async database pattern
async def create_entity(self, data: dict) -> Model:
    async with database_transaction(self.db) as tx:
        entity = Model(**data)
        tx.add(entity)
        await tx.flush()
        return entity
```

### Error Handling
```python
# Standardized async error handling
async def service_method(self):
    try:
        result = await self.repository.get_data()
        return result
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise ServiceError("Operation failed") from e
```

### Testing Patterns
```python
# Standardized async test pattern
import pytest

@pytest.mark.asyncio
async def test_service_method():
    service = await create_test_service()
    result = await service.method()
    assert result is not None
```

## Migration Checklist

- [ ] Fix syntax errors in all Python files
- [ ] Convert service classes to fully async
- [ ] Update repository methods to async
- [ ] Standardize API endpoints to async
- [ ] Update tests to use async patterns
- [ ] Update documentation

## Tools & Commands

### Syntax Checking
```bash
# Check single file
python3 -m py_compile filename.py

# Check all Python files
find . -name "*.py" -exec python3 -m py_compile {} \;
```

### Async Pattern Detection
```bash
# Find asyncio.run usage
grep -r "asyncio.run" --include="*.py" .

# Find mixed patterns
grep -r "def.*async\|async.*def" --include="*.py" .
```

### Testing
```bash
# Run async tests
pytest -v --asyncio-mode=auto
```

## Benefits of Standardization

1. **Performance**: Better resource utilization with async I/O
2. **Consistency**: Easier maintenance and development
3. **Scalability**: Better handling of concurrent requests
4. **Future-proofing**: Aligned with modern Python patterns
5. **Error Handling**: More predictable exception handling

## Next Steps

1. **Immediate**: Fix syntax errors (blocking further analysis)
2. **Week 1**: Standardize critical services (auth, billing)
3. **Week 2**: Convert repository layer to async
4. **Week 3**: Update API endpoints
5. **Week 4**: Update tests and documentation

This standardization will improve code quality, performance, and maintainability while ensuring a smooth migration path.