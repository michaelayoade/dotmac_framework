# Tenant System Migration Guide

## Overview

The DotMac tenant system has been refactored and extracted into a standalone `dotmac-tenant` package. This migration guide provides information about the changes and how to update your code.

## Migration Summary

### What Changed
- Tenant functionality moved from `dotmac_shared.tenant` to standalone `dotmac-tenant` package
- Enhanced configuration system with `TenantConfig`
- Improved security with `TenantSecurityEnforcer`
- Added database helpers for RLS and schema-per-tenant patterns
- More flexible resolution strategies

### What's Preserved
- All existing imports continue to work through migration shims
- Core APIs remain compatible
- Existing tenant context behavior unchanged
- Middleware integration patterns preserved

## Migration Phases

### Phase 1: Backward Compatibility (Current)
All existing imports continue to work:

```python
# These imports still work and are recommended during transition
from dotmac_shared.tenant import (
    TenantContext,
    TenantMiddleware,
    get_current_tenant,
    require_tenant
)
```

### Phase 2: New Package Adoption (Recommended)
Gradually migrate to new package:

```python
# New recommended imports
from dotmac.tenant import (
    TenantContext,
    TenantMiddleware,
    TenantConfig,
    get_current_tenant,
    require_tenant
)
```

### Phase 3: Legacy Deprecation (Future)
Legacy imports will show deprecation warnings and eventually be removed.

## Key Improvements

### Enhanced Configuration
```python
# Old approach - limited configuration
app.add_middleware(TenantMiddleware)

# New approach - full configuration control
config = TenantConfig(
    resolution_strategy=TenantResolutionStrategy.HOST_BASED,
    host_tenant_mapping={"client1.app.com": "client1"},
    enforce_tenant_isolation=True,
    enable_rls=True
)
app.add_middleware(TenantMiddleware, config=config)
```

### Security Enhancements
```python
# New security middleware (optional)
from dotmac.tenant.boundary import TenantSecurityEnforcer
from dotmac.tenant.middleware import TenantSecurityMiddleware

security_enforcer = TenantSecurityEnforcer(config)
app.add_middleware(TenantSecurityMiddleware, security_enforcer=security_enforcer)
```

### Database Integration
```python
# New database helpers
from dotmac.tenant.db import get_tenant_aware_session, setup_rls_for_table

# RLS-enabled session
async with get_tenant_aware_session() as session:
    users = await session.execute(select(User))

# Setup RLS for existing table
await setup_rls_for_table(engine, "users", "tenant_id")
```

## Breaking Changes (None Currently)

The migration is designed to be fully backward compatible. No immediate code changes are required.

## Migration Timeline

1. **Immediate**: All existing code continues to work via migration shims
2. **Next 3 months**: Gradually adopt new package imports and enhanced features
3. **6-12 months**: Consider leveraging new security and database features
4. **Future**: Legacy shims will be deprecated with advance notice

## Migration Steps

### Step 1: Install New Package
```bash
# Add to dependencies
poetry add dotmac-tenant
```

### Step 2: Update Imports (Gradual)
Replace imports one module at a time:

```python
# Before
from dotmac_shared.tenant import TenantContext, get_current_tenant

# After  
from dotmac.tenant import TenantContext, get_current_tenant
```

### Step 3: Enhanced Configuration (Optional)
Leverage new configuration options:

```python
from dotmac.tenant import TenantConfig, TenantResolutionStrategy

config = TenantConfig(
    resolution_strategy=TenantResolutionStrategy.COMPOSITE,
    fallback_tenant_id="default",
    enable_tenant_caching=True
)
```

### Step 4: Security Features (Optional)
Add enhanced security:

```python
from dotmac.tenant.boundary import TenantSecurityEnforcer

security_enforcer = TenantSecurityEnforcer(config)
# Configure tenant access policies...
```

### Step 5: Database Integration (As Needed)
Use new database helpers:

```python
from dotmac.tenant.db import configure_tenant_database

db_manager = configure_tenant_database(config, engine)
```

## Support

- **Documentation**: See new package README and API docs
- **Issues**: Report migration issues to the development team
- **Questions**: Use internal development channels for migration support

## Rollback Plan

If issues arise, the migration shims ensure that removing the new package and reverting imports will restore original functionality.

The old tenant system remains available as a fallback during the migration period.