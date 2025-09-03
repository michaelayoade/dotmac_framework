export { TenantProvisioningService } from './TenantProvisioningService';
export { ResourceAllocationService } from './ResourceAllocationService';

// Re-export service-specific types for convenience
export type {
  ResourceQuota,
  ResourceScalingEvent,
  ResourcePolicyRule,
  ResourceHealthCheck,
} from './ResourceAllocationService';
