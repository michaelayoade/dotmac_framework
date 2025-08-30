import { getApiClient } from '@dotmac/headless/api';
import type {
  TenantConfig,
  TenantProvisioningRequest,
  TenantProvisioningStatus,
  ResourceAllocation,
  ResourceLimits,
  TenantUsage,
  TenantListResponse,
  ProvisioningResponse,
  TenantManagementAction,
  TenantEvent,
  TenantPortalConfig,
  TenantServiceHealth,
} from '../types';

export class TenantProvisioningService {
  private apiClient = getApiClient();

  /**
   * Provision a new tenant with all required resources
   */
  async provisionTenant(request: TenantProvisioningRequest): Promise<string> {
    try {
      const response = await this.apiClient.request<ProvisioningResponse>('/api/v1/tenants/provision', {
        method: 'POST',
        body: JSON.stringify(request),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      return response.data.requestId;
    } catch (error) {
      throw new Error(`Failed to provision tenant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get provisioning status for a tenant
   */
  async getProvisioningStatus(requestId: string): Promise<TenantProvisioningStatus> {
    try {
      const response = await this.apiClient.request<TenantProvisioningStatus>(
        `/api/v1/tenants/provision/${requestId}/status`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get provisioning status: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * List all tenants with pagination and filtering
   */
  async listTenants(options?: {
    page?: number;
    size?: number;
    status?: string;
    tier?: string;
    search?: string;
  }): Promise<TenantListResponse> {
    try {
      const queryParams = new URLSearchParams();

      if (options?.page) queryParams.append('page', options.page.toString());
      if (options?.size) queryParams.append('size', options.size.toString());
      if (options?.status) queryParams.append('status', options.status);
      if (options?.tier) queryParams.append('tier', options.tier);
      if (options?.search) queryParams.append('search', options.search);

      const response = await this.apiClient.request<TenantListResponse>(
        `/api/v1/tenants?${queryParams.toString()}`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to list tenants: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get tenant details by ID
   */
  async getTenant(tenantId: string): Promise<TenantConfig> {
    try {
      const response = await this.apiClient.request<TenantConfig>(
        `/api/v1/tenants/${tenantId}`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get tenant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update tenant configuration
   */
  async updateTenant(tenantId: string, updates: Partial<TenantConfig>): Promise<TenantConfig> {
    try {
      const response = await this.apiClient.request<TenantConfig>(
        `/api/v1/tenants/${tenantId}`,
        {
          method: 'PUT',
          body: JSON.stringify(updates),
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to update tenant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Suspend a tenant
   */
  async suspendTenant(tenantId: string, reason?: string): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/tenants/${tenantId}/suspend`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      throw new Error(`Failed to suspend tenant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Resume a suspended tenant
   */
  async resumeTenant(tenantId: string): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/tenants/${tenantId}/resume`, {
        method: 'POST',
      });
    } catch (error) {
      throw new Error(`Failed to resume tenant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Terminate a tenant (permanent deletion)
   */
  async terminateTenant(tenantId: string): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/tenants/${tenantId}/terminate`, {
        method: 'DELETE',
      });
    } catch (error) {
      throw new Error(`Failed to terminate tenant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get resource allocation for a tenant
   */
  async getResourceAllocation(tenantId: string): Promise<ResourceAllocation[]> {
    try {
      const response = await this.apiClient.request<ResourceAllocation[]>(
        `/api/v1/tenants/${tenantId}/resources`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource allocation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update resource limits for a tenant
   */
  async updateResourceLimits(tenantId: string, limits: Partial<ResourceLimits>): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/tenants/${tenantId}/resources/limits`, {
        method: 'PUT',
        body: JSON.stringify(limits),
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      throw new Error(`Failed to update resource limits: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get usage metrics for a tenant
   */
  async getUsageMetrics(
    tenantId: string,
    period?: { start: Date; end: Date }
  ): Promise<TenantUsage> {
    try {
      const queryParams = new URLSearchParams();

      if (period) {
        queryParams.append('start', period.start.toISOString());
        queryParams.append('end', period.end.toISOString());
      }

      const response = await this.apiClient.request<TenantUsage>(
        `/api/v1/tenants/${tenantId}/usage?${queryParams.toString()}`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get usage metrics: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get tenant portal configuration
   */
  async getPortalConfig(tenantId: string): Promise<TenantPortalConfig> {
    try {
      const response = await this.apiClient.request<TenantPortalConfig>(
        `/api/v1/tenants/${tenantId}/portal/config`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get portal config: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update tenant portal configuration
   */
  async updatePortalConfig(
    tenantId: string,
    config: Partial<TenantPortalConfig>
  ): Promise<void> {
    try {
      await this.apiClient.request(`/api/v1/tenants/${tenantId}/portal/config`, {
        method: 'PUT',
        body: JSON.stringify(config),
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      throw new Error(`Failed to update portal config: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get service health for a tenant
   */
  async getServiceHealth(tenantId: string): Promise<TenantServiceHealth> {
    try {
      const response = await this.apiClient.request<TenantServiceHealth>(
        `/api/v1/tenants/${tenantId}/health`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get service health: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get tenant events/audit trail
   */
  async getTenantEvents(
    tenantId: string,
    filter?: {
      type?: string;
      severity?: string;
      startDate?: Date;
      endDate?: Date;
      limit?: number;
    }
  ): Promise<TenantEvent[]> {
    try {
      const queryParams = new URLSearchParams();

      if (filter?.type) queryParams.append('type', filter.type);
      if (filter?.severity) queryParams.append('severity', filter.severity);
      if (filter?.startDate) queryParams.append('start', filter.startDate.toISOString());
      if (filter?.endDate) queryParams.append('end', filter.endDate.toISOString());
      if (filter?.limit) queryParams.append('limit', filter.limit.toString());

      const response = await this.apiClient.request<TenantEvent[]>(
        `/api/v1/tenants/${tenantId}/events?${queryParams.toString()}`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get tenant events: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Execute a management action on a tenant
   */
  async executeManagementAction(action: Omit<TenantManagementAction, 'executedAt' | 'status' | 'result' | 'error'>): Promise<string> {
    try {
      const response = await this.apiClient.request<{ actionId: string }>(
        `/api/v1/tenants/${action.tenantId}/actions`,
        {
          method: 'POST',
          body: JSON.stringify(action),
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data.actionId;
    } catch (error) {
      throw new Error(`Failed to execute management action: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get management action status
   */
  async getManagementActionStatus(actionId: string): Promise<TenantManagementAction> {
    try {
      const response = await this.apiClient.request<TenantManagementAction>(
        `/api/v1/tenants/actions/${actionId}`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to get action status: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Validate tenant configuration before provisioning
   */
  async validateTenantConfig(request: TenantProvisioningRequest): Promise<{ valid: boolean; errors: string[] }> {
    try {
      const response = await this.apiClient.request<{ valid: boolean; errors: string[] }>(
        '/api/v1/tenants/validate',
        {
          method: 'POST',
          body: JSON.stringify(request),
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to validate tenant config: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Check if a tenant slug is available
   */
  async checkSlugAvailability(slug: string): Promise<{ available: boolean; suggestion?: string }> {
    try {
      const response = await this.apiClient.request<{ available: boolean; suggestion?: string }>(
        `/api/v1/tenants/check-slug/${encodeURIComponent(slug)}`,
        {
          method: 'GET',
        }
      );

      return response.data;
    } catch (error) {
      throw new Error(`Failed to check slug availability: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}
