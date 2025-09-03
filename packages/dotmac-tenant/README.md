# dotmac-tenant

**Tenant identity resolution and isolation for DotMac Framework**

A standalone package providing comprehensive multi-tenant capabilities including tenant identification, context management, security enforcement, and optional database isolation.

## Features

- **Tenant Resolution**: Multiple strategies (host-based, subdomain, trusted headers)
- **Context Management**: Request-scoped tenant context with FastAPI middleware
- **Security Enforcement**: Tenant boundary validation and isolation
- **Database Helpers**: Optional Row-Level Security (RLS) and schema-per-tenant support
- **Production Ready**: Full error handling, logging, and monitoring

## Quick Start

```python
from fastapi import FastAPI
from dotmac.tenant import TenantMiddleware, get_current_tenant

app = FastAPI()

# Add tenant middleware
app.add_middleware(TenantMiddleware)

@app.get("/api/data")
async def get_data():
    tenant = get_current_tenant()
    return {"tenant_id": tenant.id, "data": "tenant-specific-data"}
```

## Installation

```bash
pip install dotmac-tenant
```

## Configuration

```python
from dotmac.tenant import TenantConfig, TenantResolutionStrategy

config = TenantConfig(
    resolution_strategy=TenantResolutionStrategy.HOST_BASED,
    fallback_tenant_id="default",
    enforce_tenant_isolation=True,
    enable_rls=True
)
```

## Tenant Resolution Strategies

### Host-Based Resolution
```python
# tenant1.example.com -> tenant_id: "tenant1"
# tenant2.example.com -> tenant_id: "tenant2"
```

### Subdomain Resolution
```python
# https://tenant1.api.example.com -> tenant_id: "tenant1"
# https://tenant2.api.example.com -> tenant_id: "tenant2"
```

### Header-Based Resolution
```python
# X-Tenant-ID: tenant1 -> tenant_id: "tenant1"
# X-Tenant-Domain: tenant2.com -> tenant_id: "tenant2"
```

## Database Integration

### Row-Level Security (RLS)
```python
from dotmac.tenant.db import setup_rls, get_tenant_aware_session

# Setup RLS for a table
await setup_rls(engine, "users", tenant_column="tenant_id")

# Get tenant-aware database session
async with get_tenant_aware_session() as session:
    # All queries automatically filtered by current tenant
    users = await session.execute(select(User))
```

### Schema-Per-Tenant
```python
from dotmac.tenant.db import get_tenant_schema_session

# Get session for tenant-specific schema
async with get_tenant_schema_session("tenant1") as session:
    # Queries execute in tenant1 schema
    users = await session.execute(select(User))
```

## Security Features

- Automatic tenant boundary enforcement
- Request context isolation
- Tenant-aware logging and monitoring
- Security audit trails
- Cross-tenant access prevention

## Middleware Configuration

```python
from dotmac.tenant import TenantMiddleware, TenantConfig

app.add_middleware(
    TenantMiddleware,
    config=TenantConfig(
        resolution_strategy=TenantResolutionStrategy.SUBDOMAIN,
        fallback_tenant_id="default",
        enforce_tenant_isolation=True,
        log_tenant_access=True,
        tenant_header_name="X-Tenant-ID"
    )
)
```

## Testing

The package includes comprehensive test utilities:

```python
from dotmac.tenant.testing import TenantTestCase, mock_tenant_context

class TestTenantFeature(TenantTestCase):
    tenant_id = "test-tenant"
    
    async def test_tenant_specific_logic(self):
        with mock_tenant_context("tenant1"):
            # Test code here runs with tenant1 context
            pass
```

## API Reference

### Core Classes

- `TenantContext`: Current tenant information and metadata
- `TenantMiddleware`: FastAPI middleware for tenant resolution
- `TenantIdentityResolver`: Pluggable tenant identification
- `TenantSecurityEnforcer`: Boundary validation and isolation

### Database Helpers

- `setup_rls()`: Configure Row-Level Security
- `get_tenant_aware_session()`: RLS-enabled database session
- `get_tenant_schema_session()`: Schema-per-tenant session
- `TenantDatabaseManager`: High-level database operations

### Utilities

- `get_current_tenant()`: Access current tenant context
- `require_tenant()`: Dependency injection for FastAPI
- `tenant_required`: Decorator for tenant enforcement

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: https://docs.dotmac.com/tenant
- Issues: https://github.com/dotmac-framework/dotmac-tenant/issues
- Discussions: https://github.com/dotmac-framework/dotmac-tenant/discussions