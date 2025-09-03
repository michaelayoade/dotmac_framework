# @dotmac/tenancy

A comprehensive multi-tenant management system for the DotMac platform, providing tenant provisioning, resource allocation, and management portal core functionality.

## Features

- **Tenant Provisioning**: Automated tenant creation with customizable tiers
- **Resource Management**: Dynamic resource allocation and monitoring
- **Management Portal**: Portal configuration and customization
- **Health Monitoring**: Real-time service health checks
- **Event Tracking**: Comprehensive audit trail and event logging
- **Auto-scaling**: Intelligent resource scaling based on usage patterns

## Installation

```bash
pnpm add @dotmac/tenancy
```

## Quick Start

### 1. Basic Tenant Management

```tsx
import { useTenantManagement } from '@dotmac/tenancy';

function TenantDashboard({ tenantId }: { tenantId: string }) {
  const { tenant, resources, usage, health, isLoading, actions, computed } = useTenantManagement({
    tenantId,
    autoRefresh: true,
    refreshInterval: 30000,
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h1>{tenant?.name}</h1>
      <p>Status: {tenant?.status}</p>
      <p>Health: {computed.isHealthy ? 'Healthy' : 'Issues detected'}</p>

      <div>
        <h2>Resource Usage</h2>
        {resources.map((resource) => (
          <div key={resource.resourceType}>
            <span>{resource.resourceType}: </span>
            <span>
              {resource.used} / {resource.allocated}
            </span>
          </div>
        ))}
      </div>

      <button onClick={() => actions.refresh()}>Refresh Data</button>
    </div>
  );
}
```

### 2. Tenant Provisioning

```tsx
import { TenantProvisioningWizard } from '@dotmac/tenancy';

function NewTenantPage() {
  const handleTenantCreated = (tenantId: string) => {
    console.log('New tenant created:', tenantId);
    // Redirect to tenant dashboard
  };

  return (
    <div>
      <h1>Create New Tenant</h1>
      <TenantProvisioningWizard
        onComplete={handleTenantCreated}
        onCancel={() => window.history.back()}
      />
    </div>
  );
}
```

### 3. Resource Management

```tsx
import { ResourceAllocationService } from '@dotmac/tenancy';

function ResourceManager({ tenantId }: { tenantId: string }) {
  const resourceService = new ResourceAllocationService();
  const [quotas, setQuotas] = useState([]);

  useEffect(() => {
    const loadQuotas = async () => {
      const data = await resourceService.getResourceQuotas(tenantId);
      setQuotas(data);
    };
    loadQuotas();
  }, [tenantId]);

  const handleScaleResource = async (resourceType, targetValue) => {
    try {
      await resourceService.scaleResource(
        tenantId,
        resourceType,
        targetValue,
        'Manual scaling via dashboard'
      );
      // Refresh quotas
    } catch (error) {
      console.error('Failed to scale resource:', error);
    }
  };

  return (
    <div>
      {quotas.map((quota) => (
        <div key={quota.resourceType}>
          <h3>{quota.resourceType}</h3>
          <p>
            Current: {quota.current} / {quota.hardLimit}
          </p>
          <button onClick={() => handleScaleResource(quota.resourceType, quota.current * 1.5)}>
            Scale Up 50%
          </button>
        </div>
      ))}
    </div>
  );
}
```

## API Reference

### Hooks

#### `useTenantManagement(options)`

Primary hook for tenant management operations.

**Parameters:**

- `options.tenantId` - Target tenant ID
- `options.autoRefresh` - Enable automatic data refresh
- `options.refreshInterval` - Refresh interval in milliseconds

**Returns:**

- `tenant` - Current tenant configuration
- `resources` - Resource allocation data
- `usage` - Usage metrics
- `health` - Service health status
- `actions` - Management functions
- `computed` - Derived properties

### Services

#### `TenantProvisioningService`

Handles tenant lifecycle management.

**Key Methods:**

- `provisionTenant(request)` - Create new tenant
- `getTenant(id)` - Retrieve tenant details
- `updateTenant(id, updates)` - Update tenant configuration
- `suspendTenant(id, reason)` - Suspend tenant
- `resumeTenant(id)` - Resume suspended tenant
- `terminateTenant(id)` - Permanently delete tenant

#### `ResourceAllocationService`

Manages resource allocation and scaling.

**Key Methods:**

- `getResourceAllocations(tenantId)` - Get current allocations
- `updateResourceAllocation(tenantId, type, allocation)` - Update allocation
- `scaleResource(tenantId, type, target, reason)` - Scale resource
- `configureAutoScaling(tenantId, type, config)` - Set up auto-scaling
- `getResourceRecommendations(tenantId)` - Get optimization suggestions

### Components

#### `TenantProvisioningWizard`

Multi-step wizard for tenant provisioning.

**Props:**

- `onComplete(tenantId)` - Called when provisioning completes
- `onCancel()` - Called when user cancels
- `className` - Additional CSS classes

## Types

### Core Types

```typescript
interface TenantConfig {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  status: 'active' | 'suspended' | 'pending' | 'terminated';
  tier: 'basic' | 'professional' | 'enterprise';
  features: string[];
  settings: Record<string, any>;
  branding?: TenantBranding;
  limits: ResourceLimits;
  metadata: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

interface ResourceLimits {
  users: number;
  storage: number;
  bandwidth: number;
  apiCalls: number;
  customDomains: number;
  projects: number;
}

interface TenantUsage {
  tenantId: string;
  period: { start: Date; end: Date };
  metrics: {
    users: { active: number; total: number };
    storage: { used: number; quota: number; unit: 'bytes' };
    bandwidth: { used: number; quota: number; unit: 'bytes' };
    apiCalls: { count: number; quota: number };
    uptime: { percentage: number; incidents: number };
  };
  billing: {
    amount: number;
    currency: string;
    breakdown: Record<string, number>;
  };
}
```

## Advanced Usage

### Custom Resource Policies

```typescript
import { ResourceAllocationService } from '@dotmac/tenancy';

const resourceService = new ResourceAllocationService();

// Create auto-scaling policy
const policy = {
  name: 'Database Auto-Scale',
  description: 'Auto-scale database based on CPU usage',
  resourceType: 'database',
  conditions: [
    { field: 'cpu_usage', operator: 'gt', value: 80 },
    { field: 'duration', operator: 'gte', value: 300 }, // 5 minutes
  ],
  actions: [
    {
      type: 'scale',
      parameters: { multiplier: 1.5, max_size: 10 },
    },
  ],
  enabled: true,
  priority: 1,
};

await resourceService.saveResourcePolicy(policy);
```

### Health Monitoring

```typescript
import { useTenantManagement } from '@dotmac/tenancy';

function TenantHealthMonitor({ tenantId }: { tenantId: string }) {
  const { health, actions } = useTenantManagement({ tenantId });

  const handleHealthCheck = async (resourceType) => {
    try {
      await actions.checkHealth();
      const resourceService = new ResourceAllocationService();
      await resourceService.triggerHealthCheck(tenantId, resourceType);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  return (
    <div>
      <h2>Service Health</h2>
      <div>Overall Status: {health?.overall}</div>
      {Object.entries(health?.services || {}).map(([name, service]) => (
        <div key={name}>
          <span>{name}: {service.status}</span>
          {service.responseTime && (
            <span> ({service.responseTime}ms)</span>
          )}
          <button onClick={() => handleHealthCheck(name)}>
            Check Health
          </button>
        </div>
      ))}
    </div>
  );
}
```

## Integration with DotMac Platform

This package is designed to work seamlessly with other DotMac packages:

- **@dotmac/headless**: API client and state management
- **@dotmac/primitives**: UI components
- **@dotmac/providers**: Authentication and context providers

## Contributing

Please refer to the main DotMac framework contribution guidelines.

## License

Proprietary - DotMac Platform
