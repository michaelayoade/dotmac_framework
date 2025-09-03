# DotMac Multi-App Platform Licensing & Subscription Architecture

## Overview

The DotMac platform employs a **Multi-App Deployment with Cross-App Licensing** architecture. Each tenant organization can subscribe to multiple applications from our catalog, with unified user management and flexible licensing models that span across applications.

### Management Platform Role

The **DotMac Management Platform** (`dotmac_management`) serves as the **global orchestration layer** for:
- **Multi-App Catalog Management**: Managing available applications (ISP, CRM, E-commerce, etc.)
- **Tenant Orchestration**: Creating, provisioning, and managing multi-app tenant containers
- **Cross-App License Administration**: Managing app subscriptions, features, and usage limits
- **Resource Orchestration**: Container deployment and scaling for multiple applications
- **Unified Billing & Subscriptions**: Managing payments across all applications
- **Global Monitoring**: Cross-tenant and cross-app analytics and health monitoring
- **Partner Ecosystem**: Reseller accounts, app integrations, and commission structures

The Management Platform operates at a **higher level** than individual tenant containers and provides **global multi-app administration**.

## Core Architecture Principles

### 1. Multi-App Deployment with Unified Licensing
- Single tenant container contains all subscribed applications
- Applications activated/deactivated based on subscriptions
- No redeployment required for adding/removing apps
- Instant application access upon subscription

### 2. Cross-App Resource Efficiency
- Shared user management across all applications
- Unified database and cache layers per tenant
- Dynamic resource allocation based on active applications
- Optimized background workers per application subscription

### 3. Flexible Subscription Models
- Per-application subscriptions with feature tiers
- Bundle pricing for multiple applications
- Usage-based add-ons and premium features
- Enterprise licensing with custom configurations

## Architecture Components

### Multi-App Platform Architecture

```
┌─────────────────────────────────────────────────────────┐
│              DotMac Management Platform                  │
│          (Global Multi-App Orchestration)               │
├─────────────────────────────────────────────────────────┤
│  📱 App Catalog Management                              │
│  • ISP Framework    • E-commerce Platform               │
│  • CRM System      • Project Management                │
│  • Business Intelligence • Learning Management System   │
│                                                         │
│  🏢 Tenant & Subscription Management                    │
│  • Multi-app container provisioning                    │
│  • Cross-app license assignment                        │
│  • Unified billing across applications                 │
│  • Resource allocation per tenant                       │
│                                                         │
│  🔧 Platform Operations                                 │
│  • Global monitoring & analytics                       │
│  • Partner/reseller ecosystem                          │
│  • Cross-tenant reporting                              │
└─────────────────────────────────────────────────────────┘
                    │ Orchestrates │
     ┌──────────────┼─────────────┼──────────────┐
     ▼              ▼             ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ ABC Corp   │ │ XYZ ISP    │ │ DEF Corp   │ │ GHI Ltd    │
│ Multi-App  │ │ Multi-App  │ │ Multi-App  │ │ Multi-App  │
│ Tenant     │ │ Tenant     │ │ Tenant     │ │ Tenant     │
├────────────┤ ├────────────┤ ├────────────┤ ├────────────┤
│🌐 ISP      │ │🌐 ISP      │ │📞 CRM      │ │🌐 ISP      │
│📞 CRM      │ │📋 Projects │ │🛒 E-comm   │ │🛒 E-comm   │
│🛒 E-comm   │ │            │ │📋 Projects │ │📞 CRM      │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

### Licensing System

```
┌─────────────────────────────────────────────────────────┐
│                   DotMac Platform Container              │
├─────────────────────────────────────────────────────────┤
│                    License Manager                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Database   │  │    Cache     │  │   Feature    │ │
│  │   License    │  │   License    │  │    Flags     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────┤
│                     Platform Modules                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Core Network (Always Active)                     │  │
│  │  - IP Management                                  │  │
│  │  - Circuit Provisioning                          │  │
│  │  - Network Monitoring                            │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  CRM Module (License: crm)                       │  │
│  │  - Customer Management                           │  │
│  │  - Lead Tracking                                 │  │
│  │  - Sales Pipeline                                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Ticketing Module (License: tickets)             │  │
│  │  - Support Tickets                               │  │
│  │  - SLA Management                                │  │
│  │  - Knowledge Base                                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Projects Module (License: projects)             │  │
│  │  - Project Management                            │  │
│  │  - Task Tracking                                 │  │
│  │  - Resource Planning                             │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Field Ops Module (License: fieldops)            │  │
│  │  - Technician Dispatch                           │  │
│  │  - Route Optimization                            │  │
│  │  - Work Orders                                   │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Analytics Module (License: analytics)           │  │
│  │  - Business Intelligence                         │  │
│  │  - Custom Reports                                │  │
│  │  - Predictive Analytics                          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Subscription Tiers

### Starter Plan
- **Core Network**: ✅ Full access
- **CRM**: ❌ Not included
- **Tickets**: ✅ Basic (100 tickets/month)
- **Projects**: ❌ Not included
- **Field Ops**: ❌ Not included
- **Analytics**: ❌ Not included

### Professional Plan
- **Core Network**: ✅ Full access
- **CRM**: ✅ Full access
- **Tickets**: ✅ Standard (1000 tickets/month)
- **Projects**: ✅ Full access
- **Field Ops**: ❌ Not included
- **Analytics**: ✅ Basic reports

### Enterprise Plan
- **Core Network**: ✅ Full access
- **CRM**: ✅ Full access + API
- **Tickets**: ✅ Unlimited
- **Projects**: ✅ Full access
- **Field Ops**: ✅ Full access
- **Analytics**: ✅ Advanced + ML features

### Custom Add-ons
- Individual modules can be added à la carte
- Usage-based pricing for specific features
- Trial periods for feature evaluation

## Implementation Details

### License Database Schema

```sql
-- Tenant licensing table
CREATE TABLE tenant_licenses (
    tenant_id UUID PRIMARY KEY,
    plan_tier VARCHAR(50) NOT NULL,
    features JSONB NOT NULL DEFAULT '{}',
    usage_limits JSONB NOT NULL DEFAULT '{}',
    custom_addons JSONB DEFAULT '{}',
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    auto_renew BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature usage tracking
CREATE TABLE feature_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_licenses(tenant_id),
    feature_name VARCHAR(100) NOT NULL,
    usage_count INTEGER DEFAULT 0,
    usage_date DATE NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail for license changes
CREATE TABLE license_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    change_type VARCHAR(50) NOT NULL, -- upgrade, downgrade, renewal, cancellation
    old_plan VARCHAR(50),
    new_plan VARCHAR(50),
    changed_by UUID,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Feature Flag Implementation

```python
# Backend feature checking
from functools import wraps
from fastapi import HTTPException, Depends

class LicenseManager:
    def __init__(self):
        self.cache = {}
    
    async def get_license(self, tenant_id: str) -> TenantLicense:
        # Check cache first
        if tenant_id in self.cache:
            return self.cache[tenant_id]
        
        # Load from database
        license = await db.get_license(tenant_id)
        self.cache[tenant_id] = license
        return license
    
    async def has_feature(self, tenant_id: str, feature: str) -> bool:
        license = await self.get_license(tenant_id)
        
        # Check if feature is enabled
        if not license.features.get(feature, False):
            return False
        
        # Check expiration
        if license.valid_until < datetime.now():
            return False
        
        # Check usage limits
        usage = await self.get_usage(tenant_id, feature)
        limit = license.usage_limits.get(feature)
        if limit and usage >= limit:
            return False
        
        return True

def requires_feature(feature: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            deps = kwargs.get('deps')
            if not await license_manager.has_feature(deps.tenant_id, feature):
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "Feature not available",
                        "feature": feature,
                        "message": "Please upgrade your plan to access this feature",
                        "upgrade_url": f"/billing/upgrade?feature={feature}"
                    }
                )
            
            # Track usage
            await track_usage(deps.tenant_id, feature)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Frontend Feature Gating

```typescript
// Feature context provider
interface License {
  planTier: 'starter' | 'professional' | 'enterprise';
  features: Record<string, boolean>;
  usageLimits: Record<string, number>;
  currentUsage: Record<string, number>;
  validUntil: Date;
}

const LicenseContext = React.createContext<License | null>(null);

export const LicenseProvider: React.FC = ({ children }) => {
  const [license, setLicense] = useState<License | null>(null);
  
  useEffect(() => {
    // Fetch license on mount and subscribe to updates
    fetchLicense().then(setLicense);
    
    const ws = new WebSocket('/ws/license');
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      if (update.type === 'license_updated') {
        setLicense(update.license);
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

// Feature gate component
export const FeatureGate: React.FC<{
  feature: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}> = ({ feature, fallback, children }) => {
  const license = useContext(LicenseContext);
  
  if (!license || !license.features[feature]) {
    return fallback || <UpgradePrompt feature={feature} />;
  }
  
  // Check usage limits
  const limit = license.usageLimits[feature];
  const usage = license.currentUsage[feature];
  
  if (limit && usage >= limit) {
    return <UsageLimitReached feature={feature} limit={limit} />;
  }
  
  return <>{children}</>;
};

// Dynamic navigation based on features
export const useNavigation = () => {
  const license = useContext(LicenseContext);
  
  return useMemo(() => {
    const items = [
      { path: '/', label: 'Dashboard', icon: 'home' },
      { path: '/network', label: 'Network', icon: 'network' },
    ];
    
    if (license?.features.crm) {
      items.push({ path: '/crm', label: 'CRM', icon: 'users' });
    }
    
    if (license?.features.tickets) {
      items.push({ path: '/tickets', label: 'Support', icon: 'help' });
    }
    
    if (license?.features.projects) {
      items.push({ path: '/projects', label: 'Projects', icon: 'tasks' });
    }
    
    if (license?.features.fieldops) {
      items.push({ path: '/fieldops', label: 'Field Ops', icon: 'map' });
    }
    
    if (license?.features.analytics) {
      items.push({ path: '/analytics', label: 'Analytics', icon: 'chart' });
    }
    
    return items;
  }, [license]);
};
```

## Container Deployment

### Docker Configuration

```dockerfile
# Single image with all features
FROM python:3.11-slim

# Install all dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all modules
COPY src/ /app/src/
COPY frontend/dist/ /app/static/

# Environment-based configuration
ENV MODULE_CONFIG=/app/config/modules.json

# Start with license check
CMD ["python", "-m", "dotmac.main", "--check-license"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-{{ tenant_id }}
  namespace: tenants
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dotmac
      tenant: {{ tenant_id }}
  template:
    metadata:
      labels:
        app: dotmac
        tenant: {{ tenant_id }}
    spec:
      containers:
      - name: platform
        image: dotmac/platform:latest
        env:
        - name: TENANT_ID
          value: "{{ tenant_id }}"
        - name: LICENSE_CHECK_INTERVAL
          value: "300"  # Check license every 5 minutes
        - name: FEATURE_CACHE_TTL
          value: "60"   # Cache features for 1 minute
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          periodSeconds: 10
```

## Resource Optimization

### Dynamic Worker Management

```python
class WorkerManager:
    """Manages background workers based on licensed features"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.workers = {}
    
    async def optimize_workers(self):
        license = await get_license(self.tenant_id)
        
        # Core workers always run
        self.ensure_worker('network-monitor')
        self.ensure_worker('billing-processor')
        
        # Feature-specific workers
        if license.features.get('analytics'):
            self.ensure_worker('analytics-aggregator')
            self.ensure_worker('report-generator')
        else:
            self.stop_worker('analytics-aggregator')
            self.stop_worker('report-generator')
        
        if license.features.get('fieldops'):
            self.ensure_worker('route-optimizer')
            self.ensure_worker('dispatch-scheduler')
        else:
            self.stop_worker('route-optimizer')
            self.stop_worker('dispatch-scheduler')
```

### Cache Management

```python
class CacheManager:
    """Allocates cache based on active features"""
    
    async def optimize_cache(self, tenant_id: str):
        license = await get_license(tenant_id)
        total_cache = 1024  # MB
        
        # Base allocation
        allocations = {
            'core': 256,
            'session': 128,
        }
        
        # Dynamic allocation
        active_features = [f for f, enabled in license.features.items() if enabled]
        remaining = total_cache - sum(allocations.values())
        per_feature = remaining // len(active_features) if active_features else 0
        
        for feature in active_features:
            allocations[feature] = per_feature
        
        await redis.config_set(f'maxmemory-{tenant_id}', allocations)
```

## Migration Strategy

### Phase 1: License Infrastructure (Week 1-2)
1. Create license database schema
2. Implement LicenseManager service
3. Add feature checking decorators
4. Create subscription management API

### Phase 2: Frontend Integration (Week 3-4)
1. Implement FeatureGate components
2. Update navigation to be license-aware
3. Add upgrade prompts and limits UI
4. Create billing/subscription portal

### Phase 3: Testing & Validation (Week 5)
1. Test feature activation/deactivation
2. Verify resource optimization
3. Load test with various license configurations
4. Security audit of license checks

### Phase 4: Deployment (Week 6)
1. Deploy license management service
2. Migrate existing tenants to new system
3. Monitor resource usage
4. Optimize based on metrics

## Benefits

1. **Simplified Operations**: One image, one deployment
2. **Instant Upgrades**: No redeployment needed
3. **Resource Efficiency**: Shared connections and caches
4. **Better UX**: Immediate feature access
5. **Flexible Pricing**: Easy to implement trials and custom plans
6. **A/B Testing**: Roll out features gradually
7. **Cost Optimization**: Pay for what you use

## Security Considerations

1. **License Validation**: Cryptographically signed licenses
2. **Feature Isolation**: Modules can't access unlicensed data
3. **Audit Trail**: All license changes logged
4. **Rate Limiting**: Per-feature rate limits
5. **Usage Monitoring**: Detect and prevent abuse

## Monitoring & Analytics

```python
# Prometheus metrics
feature_usage = Counter('dotmac_feature_usage', 'Feature usage counter', ['tenant_id', 'feature'])
license_checks = Histogram('dotmac_license_checks', 'License check duration', ['tenant_id'])
feature_denials = Counter('dotmac_feature_denials', 'Feature access denials', ['tenant_id', 'feature'])
```

## Support & Troubleshooting

### Common Issues

1. **Feature not accessible after upgrade**
   - Clear license cache: `redis-cli DEL license:*`
   - Check license validity: `SELECT * FROM tenant_licenses WHERE tenant_id = ?`

2. **Usage limits exceeded**
   - Review usage: `SELECT * FROM feature_usage WHERE tenant_id = ?`
   - Adjust limits: `UPDATE tenant_licenses SET usage_limits = ?`

3. **Performance degradation**
   - Check worker optimization
   - Review cache allocation
   - Monitor feature-specific metrics
