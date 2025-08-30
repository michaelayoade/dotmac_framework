import { getApiClient } from '@dotmac/headless/api';
import type {
  ResourceAllocation,
  ResourceLimits,
  TenantUsage,
  ResourceType,
} from '../types';

export interface ResourceQuota {
  tenantId: string;
  resourceType: ResourceType;
  softLimit: number;
  hardLimit: number;
  current: number;
  reserved: number;
  unit: string;
  alertThresholds: {
    warning: number; // percentage
    critical: number; // percentage
  };
  autoScale: {
    enabled: boolean;
    minSize: number;
    maxSize: number;
    scaleUpThreshold: number; // percentage
    scaleDownThreshold: number; // percentage
  };
}

export interface ResourceScalingEvent {
  id: string;
  tenantId: string;
  resourceType: ResourceType;
  action: 'scale_up' | 'scale_down' | 'maintain';
  previousValue: number;
  newValue: number;
  reason: string;
  timestamp: Date;
  triggeredBy: 'auto' | 'manual' | 'policy';
  metadata: Record<string, any>;
}

export interface ResourcePolicyRule {
  id: string;
  name: string;
  description: string;
  tenantTier?: string;
  resourceType: ResourceType;
  conditions: {
    field: string;
    operator: 'eq' | 'gt' | 'lt' | 'gte' | 'lte' | 'in';
    value: any;
  }[];
  actions: {
    type: 'set_limit' | 'scale' | 'alert' | 'suspend';
    parameters: Record<string, any>;
  }[];
  enabled: boolean;
  priority: number;
}

export interface ResourceHealthCheck {
  tenantId: string;
  resourceType: ResourceType;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  metrics: {
    availability: number; // percentage
    performance: number; // percentage
    utilization: number; // percentage
  };
  lastCheck: Date;
  alerts: {
    level: 'info' | 'warning' | 'error' | 'critical';
    message: string;
    timestamp: Date;
  }[];
}

export class ResourceAllocationService {
  private apiClient = getApiClient();

  /**
   * Get resource allocations for a tenant
   */
  async getResourceAllocations(tenantId: string): Promise<ResourceAllocation[]> {
    try {
      const response = await this.apiClient.request<ResourceAllocation[]>(
        `/api/v1/tenants/${tenantId}/resources/allocations`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource allocations: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get specific resource allocation
   */
  async getResourceAllocation(tenantId: string, resourceType: ResourceType): Promise<ResourceAllocation> {
    try {
      const response = await this.apiClient.request<ResourceAllocation>(
        `/api/v1/tenants/${tenantId}/resources/allocations/${resourceType}`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource allocation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update resource allocation for a tenant
   */
  async updateResourceAllocation(
    tenantId: string,
    resourceType: ResourceType,
    allocation: Partial<ResourceAllocation>
  ): Promise<ResourceAllocation> {
    try {
      const response = await this.apiClient.request<ResourceAllocation>(
        `/api/v1/tenants/${tenantId}/resources/allocations/${resourceType}`,
        {
          method: 'PUT',
          body: JSON.stringify(allocation),
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update resource allocation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get resource quotas for a tenant
   */
  async getResourceQuotas(tenantId: string): Promise<ResourceQuota[]> {
    try {
      const response = await this.apiClient.request<ResourceQuota[]>(
        `/api/v1/tenants/${tenantId}/resources/quotas`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource quotas: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update resource quotas for a tenant
   */
  async updateResourceQuotas(tenantId: string, quotas: Partial<ResourceQuota>[]): Promise<ResourceQuota[]> {
    try {
      const response = await this.apiClient.request<ResourceQuota[]>(
        `/api/v1/tenants/${tenantId}/resources/quotas`,
        {
          method: 'PUT',
          body: JSON.stringify(quotas),
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update resource quotas: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get resource usage history for a tenant
   */
  async getResourceUsageHistory(
    tenantId: string,
    resourceType?: ResourceType,
    period?: { start: Date; end: Date }
  ): Promise<{
    tenantId: string;
    resourceType: ResourceType;
    data: {
      timestamp: Date;
      allocated: number;
      used: number;
      utilization: number;
    }[];
  }[]> {
    try {
      const queryParams = new URLSearchParams();
      if (resourceType) queryParams.append('resourceType', resourceType);
      if (period) {
        queryParams.append('start', period.start.toISOString());
        queryParams.append('end', period.end.toISOString());
      }

      const response = await this.apiClient.request<{
        tenantId: string;
        resourceType: ResourceType;
        data: {
          timestamp: Date;
          allocated: number;
          used: number;
          utilization: number;
        }[];
      }[]>(
        `/api/v1/tenants/${tenantId}/resources/usage/history?${queryParams.toString()}`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource usage history: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Scale resources for a tenant
   */
  async scaleResource(
    tenantId: string,
    resourceType: ResourceType,
    targetValue: number,
    reason?: string
  ): Promise<ResourceScalingEvent> {
    try {
      const response = await this.apiClient.request<ResourceScalingEvent>(
        `/api/v1/tenants/${tenantId}/resources/${resourceType}/scale`,
        {
          method: 'POST',
          body: JSON.stringify({
            targetValue,
            reason,
            triggeredBy: 'manual',
          }),
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to scale resource: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get scaling events for a tenant
   */
  async getScalingEvents(
    tenantId: string,
    resourceType?: ResourceType,
    limit?: number
  ): Promise<ResourceScalingEvent[]> {
    try {
      const queryParams = new URLSearchParams();
      if (resourceType) queryParams.append('resourceType', resourceType);
      if (limit) queryParams.append('limit', limit.toString());

      const response = await this.apiClient.request<ResourceScalingEvent[]>(
        `/api/v1/tenants/${tenantId}/resources/scaling/events?${queryParams.toString()}`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get scaling events: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Configure auto-scaling for a resource
   */
  async configureAutoScaling(
    tenantId: string,
    resourceType: ResourceType,
    config: ResourceQuota['autoScale']
  ): Promise<void> {
    try {
      await this.apiClient.request(
        `/api/v1/tenants/${tenantId}/resources/${resourceType}/auto-scaling`,
        {
          method: 'PUT',
          body: JSON.stringify(config),
          headers: { 'Content-Type': 'application/json' },
        }
      );
    } catch (error) {
      throw new Error(`Failed to configure auto-scaling: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get resource policies
   */
  async getResourcePolicies(tenantId?: string): Promise<ResourcePolicyRule[]> {
    try {
      const queryParams = new URLSearchParams();
      if (tenantId) queryParams.append('tenantId', tenantId);

      const response = await this.apiClient.request<ResourcePolicyRule[]>(
        `/api/v1/resources/policies?${queryParams.toString()}`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource policies: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Create or update a resource policy
   */
  async saveResourcePolicy(policy: Omit<ResourcePolicyRule, 'id'> | ResourcePolicyRule): Promise<ResourcePolicyRule> {
    try {
      const isUpdate = 'id' in policy;
      const url = isUpdate ? `/api/v1/resources/policies/${policy.id}` : '/api/v1/resources/policies';
      const method = isUpdate ? 'PUT' : 'POST';

      const response = await this.apiClient.request<ResourcePolicyRule>(url, {
        method,
        body: JSON.stringify(policy),
        headers: { 'Content-Type': 'application/json' },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to save resource policy: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Delete a resource policy
   */
  async deleteResourcePolicy(policyId: string): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/resources/policies/${policyId}`, {
        method: 'DELETE',
      });
    } catch (error) {
      throw new Error(`Failed to delete resource policy: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get resource health checks for a tenant
   */
  async getResourceHealthChecks(tenantId: string): Promise<ResourceHealthCheck[]> {
    try {
      const response = await this.apiClient.request<ResourceHealthCheck[]>(
        `/api/v1/tenants/${tenantId}/resources/health`,
        { method: 'GET' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource health checks: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Trigger resource health check
   */
  async triggerHealthCheck(tenantId: string, resourceType: ResourceType): Promise<ResourceHealthCheck> {
    try {
      const response = await this.apiClient.request<ResourceHealthCheck>(
        `/api/v1/tenants/${tenantId}/resources/${resourceType}/health/check`,
        { method: 'POST' }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to trigger health check: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get resource recommendations for optimization
   */
  async getResourceRecommendations(tenantId: string): Promise<{
    tenantId: string;
    recommendations: {
      resourceType: ResourceType;
      currentAllocation: number;
      recommendedAllocation: number;
      reason: string;
      potentialSavings?: number;
      impact: 'low' | 'medium' | 'high';
      confidence: number; // 0-100
    }[];
    generatedAt: Date;
  }> {
    try {
      const response = await this.apiClient.request<{
        tenantId: string;
        recommendations: {
          resourceType: ResourceType;
          currentAllocation: number;
          recommendedAllocation: number;
          reason: string;
          potentialSavings?: number;
          impact: 'low' | 'medium' | 'high';
          confidence: number;
        }[];
        generatedAt: Date;
      }>(`/api/v1/tenants/${tenantId}/resources/recommendations`, { method: 'GET' });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource recommendations: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Apply resource recommendation
   */
  async applyResourceRecommendation(
    tenantId: string,
    resourceType: ResourceType,
    newAllocation: number
  ): Promise<ResourceAllocation> {
    try {
      const response = await this.apiClient.request<ResourceAllocation>(
        `/api/v1/tenants/${tenantId}/resources/${resourceType}/apply-recommendation`,
        {
          method: 'POST',
          body: JSON.stringify({ newAllocation }),
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to apply resource recommendation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Reserve resources for a tenant (for upcoming provisioning)
   */
  async reserveResources(
    tenantId: string,
    reservations: {
      resourceType: ResourceType;
      amount: number;
      duration: number; // in minutes
      metadata?: Record<string, any>;
    }[]
  ): Promise<{
    reservationId: string;
    expiresAt: Date;
    resources: {
      resourceType: ResourceType;
      reserved: number;
      available: number;
    }[];
  }> {
    try {
      const response = await this.apiClient.request<{
        reservationId: string;
        expiresAt: Date;
        resources: {
          resourceType: ResourceType;
          reserved: number;
          available: number;
        }[];
      }>(`/api/v1/tenants/${tenantId}/resources/reserve`, {
        method: 'POST',
        body: JSON.stringify(reservations),
        headers: { 'Content-Type': 'application/json' },
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to reserve resources: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Release reserved resources
   */
  async releaseReservation(reservationId: string): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/resources/reservations/${reservationId}/release`, {
        method: 'POST',
      });
    } catch (error) {
      throw new Error(`Failed to release reservation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get global resource statistics
   */
  async getGlobalResourceStats(): Promise<{
    totalAllocated: Record<ResourceType, number>;
    totalUsed: Record<ResourceType, number>;
    totalAvailable: Record<ResourceType, number>;
    utilizationPercentage: Record<ResourceType, number>;
    tenantCount: number;
    activeReservations: number;
    lastUpdated: Date;
  }> {
    try {
      const response = await this.apiClient.request<{
        totalAllocated: Record<ResourceType, number>;
        totalUsed: Record<ResourceType, number>;
        totalAvailable: Record<ResourceType, number>;
        utilizationPercentage: Record<ResourceType, number>;
        tenantCount: number;
        activeReservations: number;
        lastUpdated: Date;
      }>('/api/v1/resources/stats/global', { method: 'GET' });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get global resource stats: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}
