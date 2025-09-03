# DotMac Platform Migration Guide

## From Current Architecture to Feature-Licensed Architecture

### Overview
This guide outlines the migration from the current monolithic structure to a feature-licensed, single-container deployment model.

## Migration Phases

### Phase 1: Database Schema Setup (Week 1)
**Goal:** Add licensing infrastructure without breaking existing functionality

#### 1.1 Create License Tables
```sql
-- Run migration: 001_add_licensing_tables.sql
CREATE TABLE tenant_licenses (
    tenant_id UUID PRIMARY KEY,
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'starter',
    features JSONB NOT NULL DEFAULT '{}',
    usage_limits JSONB NOT NULL DEFAULT '{}',
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP + INTERVAL '30 days',
    auto_renew BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migrate existing tenants to default plan
INSERT INTO tenant_licenses (tenant_id, plan_tier, features)
SELECT 
    id,
    'professional',
    '{"crm": true, "tickets": true, "projects": true, "fieldops": false, "analytics": true}'::jsonb
FROM tenants;
```

#### 1.2 Add Usage Tracking
```sql
CREATE TABLE feature_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_licenses(tenant_id),
    feature_name VARCHAR(100) NOT NULL,
    usage_count INTEGER DEFAULT 0,
    usage_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feature_usage_tenant_date ON feature_usage(tenant_id, usage_date);
```

### Phase 2: Backend Implementation (Week 2)

#### 2.1 Add License Manager
```python
# src/dotmac_shared/licensing/manager.py
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

class LicenseManager:
    def __init__(self):
        self.cache = {}
    
    async def get_license(self, tenant_id: str, db: AsyncSession) -> Dict:
        if tenant_id in self.cache:
            cached = self.cache[tenant_id]
            if cached['expires'] > datetime.now():
                return cached['license']
        
        # Fetch from database
        result = await db.execute(
            "SELECT * FROM tenant_licenses WHERE tenant_id = :tid",
            {"tid": tenant_id}
        )
        license = result.first()
        
        # Cache for 5 minutes
        self.cache[tenant_id] = {
            'license': license,
            'expires': datetime.now() + timedelta(minutes=5)
        }
        
        return license

license_manager = LicenseManager()
```

#### 2.2 Add Feature Decorators
```python
# src/dotmac_shared/licensing/decorators.py
from functools import wraps
from fastapi import HTTPException

def requires_feature(feature: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            deps = kwargs.get('deps')
            license = await license_manager.get_license(deps.tenant_id, deps.db)
            
            if not license.features.get(feature, False):
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "Feature not available",
                        "feature": feature,
                        "upgrade_url": f"/billing/upgrade?feature={feature}"
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 2.3 Update Existing Routers
```python
# Before: src/dotmac_isp/modules/crm/api.py
@router.get("/customers")
async def list_customers(deps: Dependencies = Depends()):
    return await CustomerService(deps.db).list_all()

# After: Add feature decorator
from dotmac_shared.licensing import requires_feature

@router.get("/customers")
@requires_feature("crm")
async def list_customers(deps: Dependencies = Depends()):
    return await CustomerService(deps.db).list_all()
```

### Phase 3: Frontend Integration (Week 3)

#### 3.1 Add License Context
```typescript
// frontend/packages/licensing/LicenseProvider.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface License {
  planTier: string;
  features: Record<string, boolean>;
  usageLimits: Record<string, number>;
  validUntil: Date;
}

const LicenseContext = createContext<License | null>(null);

export const LicenseProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [license, setLicense] = useState<License | null>(null);

  useEffect(() => {
    api.get('/license').then(setLicense);
    
    // Subscribe to license updates
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/license`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'license_updated') {
        setLicense(data.license);
      }
    };

    return () => ws.close();
  }, []);

  return (
    <LicenseContext.Provider value={license}>
      {children}
    </LicenseContext.Provider>
  );
};

export const useLicense = () => {
  const context = useContext(LicenseContext);
  if (!context) {
    throw new Error('useLicense must be used within LicenseProvider');
  }
  return context;
};
```

#### 3.2 Add Feature Gates
```typescript
// frontend/packages/licensing/FeatureGate.tsx
import React from 'react';
import { useLicense } from './LicenseProvider';
import { UpgradePrompt } from './UpgradePrompt';

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const FeatureGate: React.FC<FeatureGateProps> = ({ 
  feature, 
  children, 
  fallback 
}) => {
  const license = useLicense();
  
  if (!license.features[feature]) {
    return fallback || <UpgradePrompt feature={feature} />;
  }
  
  return <>{children}</>;
};
```

#### 3.3 Update Navigation
```typescript
// frontend/apps/customer/src/components/Navigation.tsx
import { useLicense } from '@dotmac/licensing';

export const Navigation = () => {
  const license = useLicense();
  
  const menuItems = [
    { label: 'Dashboard', path: '/', icon: 'home' },
    { label: 'Network', path: '/network', icon: 'network' },
    license.features.crm && { label: 'CRM', path: '/crm', icon: 'users' },
    license.features.tickets && { label: 'Support', path: '/tickets', icon: 'help' },
    license.features.projects && { label: 'Projects', path: '/projects', icon: 'tasks' },
  ].filter(Boolean);
  
  return <NavigationMenu items={menuItems} />;
};
```

### Phase 4: Folder Reorganization (Week 4)

#### 4.1 Create New Structure
```bash
# Create new module directories
mkdir -p src/dotmac_core/{network,billing,auth,licensing}
mkdir -p src/dotmac_modules/{crm,tickets,projects,fieldops,analytics}

# Move core functionality
mv src/dotmac_isp/modules/network/* src/dotmac_core/network/
mv src/dotmac_isp/modules/billing/* src/dotmac_core/billing/
mv src/dotmac_isp/modules/identity/* src/dotmac_core/auth/

# Move feature modules
mv src/dotmac_isp/modules/crm/* src/dotmac_modules/crm/
mv src/dotmac_isp/modules/support/* src/dotmac_modules/tickets/
mv src/dotmac_isp/modules/projects/* src/dotmac_modules/projects/
mv src/dotmac_isp/modules/field_operations/* src/dotmac_modules/fieldops/
mv src/dotmac_isp/modules/analytics/* src/dotmac_modules/analytics/
```

#### 4.2 Update Imports
```python
# Before
from dotmac_isp.modules.crm import CustomerService

# After
from dotmac_modules.crm import CustomerService
```

### Phase 5: Testing & Validation (Week 5)

#### 5.1 Test Feature Activation
```python
# tests/licensing/test_feature_activation.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_unlicensed_feature_returns_402(client: AsyncClient):
    # Set tenant to starter plan (no CRM)
    await set_tenant_plan("test-tenant", "starter")
    
    response = await client.get("/api/v1/crm/customers")
    assert response.status_code == 402
    assert "upgrade_url" in response.json()

@pytest.mark.asyncio
async def test_licensed_feature_works(client: AsyncClient):
    # Set tenant to professional plan (has CRM)
    await set_tenant_plan("test-tenant", "professional")
    
    response = await client.get("/api/v1/crm/customers")
    assert response.status_code == 200
```

#### 5.2 Test Instant Upgrade
```python
@pytest.mark.asyncio
async def test_instant_feature_activation(client: AsyncClient):
    # Start with starter plan
    await set_tenant_plan("test-tenant", "starter")
    
    # Verify CRM is blocked
    response = await client.get("/api/v1/crm/customers")
    assert response.status_code == 402
    
    # Upgrade to professional
    upgrade_response = await client.post("/api/v1/license/upgrade", 
        json={"new_plan": "professional"})
    assert upgrade_response.status_code == 200
    
    # CRM should work immediately
    response = await client.get("/api/v1/crm/customers")
    assert response.status_code == 200
```

### Phase 6: Production Deployment (Week 6)

#### 6.1 Deployment Checklist
- [ ] Database migrations applied
- [ ] License data populated for all tenants
- [ ] Feature decorators added to all endpoints
- [ ] Frontend feature gates implemented
- [ ] Monitoring dashboards updated
- [ ] Documentation updated
- [ ] Team trained on new system

#### 6.2 Rollout Strategy
1. **Canary Deployment** (Day 1-3)
   - Deploy to 5% of tenants
   - Monitor error rates and performance
   
2. **Gradual Rollout** (Day 4-7)
   - Increase to 25%, then 50%, then 100%
   - Monitor license cache hit rates
   - Check feature activation speeds

3. **Full Production** (Week 2)
   - All tenants on new system
   - Old code paths removed
   - Performance optimizations applied

## Rollback Plan

### Quick Rollback (< 5 minutes)
```bash
# Revert to previous container image
kubectl set image deployment/dotmac-platform platform=dotmac:previous

# Clear license cache
redis-cli FLUSHDB
```

### Data Rollback (< 30 minutes)
```sql
-- Disable license checks
UPDATE tenant_licenses SET features = 
  '{"crm": true, "tickets": true, "projects": true, 
    "fieldops": true, "analytics": true}'::jsonb;

-- Or drop license tables entirely
DROP TABLE IF EXISTS feature_usage CASCADE;
DROP TABLE IF EXISTS tenant_licenses CASCADE;
```

## Monitoring Post-Migration

### Key Metrics to Track
1. **Feature Access Denials**
   ```promql
   rate(dotmac_feature_denials_total[5m])
   ```

2. **License Cache Hit Rate**
   ```promql
   dotmac_license_cache_hits / dotmac_license_cache_requests
   ```

3. **API Response Times**
   ```promql
   histogram_quantile(0.95, dotmac_api_duration_seconds)
   ```

4. **Upgrade Conversion Rate**
   ```sql
   SELECT 
     COUNT(CASE WHEN clicked_upgrade THEN 1 END)::float / 
     COUNT(*) as conversion_rate
   FROM feature_denial_events
   WHERE created_at > NOW() - INTERVAL '7 days';
   ```

## Common Issues & Solutions

### Issue: Feature not accessible after upgrade
**Solution:**
```bash
# Clear specific tenant cache
redis-cli DEL "license:tenant-id"

# Force license refresh
curl -X POST http://api/admin/license/refresh/tenant-id
```

### Issue: High database load from license checks
**Solution:**
```python
# Increase cache TTL
CACHE_TTL = 300  # 5 minutes instead of 1

# Add read replica for license queries
LICENSE_DB_URL = "postgresql://read-replica/dotmac"
```

### Issue: Frontend not updating after license change
**Solution:**
```typescript
// Force refresh license
window.dispatchEvent(new CustomEvent('license:refresh'));

// Or reload the page
window.location.reload();
```

## Success Criteria

- [ ] All existing features remain accessible
- [ ] License changes take effect within 1 minute
- [ ] No increase in API response times (p95 < 200ms)
- [ ] Cache hit rate > 95%
- [ ] Zero data loss during migration
- [ ] Support team trained on new licensing system

## Support Contacts

- **Technical Issues**: devops@dotmac.io
- **License Questions**: licensing@dotmac.io
- **Emergency Rollback**: oncall@dotmac.io (+1-555-0100)
