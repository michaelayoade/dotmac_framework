import { useState, useEffect, useCallback, useMemo } from 'react';
import { TenantProvisioningService } from '../services/TenantProvisioningService';
import { ResourceAllocationService } from '../services/ResourceAllocationService';
import type {
  TenantConfig,
  TenantProvisioningRequest,
  TenantProvisioningStatus,
  ResourceAllocation,
  TenantUsage,
  TenantPortalConfig,
  TenantServiceHealth,
  TenantEvent,
  ResourceLimits,
} from '../types';

export interface UseTenantManagementOptions {
  tenantId?: string;
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
}

export interface UseTenantManagementReturn {
  // Current tenant state
  tenant: TenantConfig | null;
  isLoading: boolean;
  error: string | null;

  // Provisioning state
  provisioning: TenantProvisioningStatus | null;

  // Resource management
  resources: ResourceAllocation[];
  usage: TenantUsage | null;

  // Portal configuration
  portalConfig: TenantPortalConfig | null;

  // Health monitoring
  health: TenantServiceHealth | null;

  // Events
  events: TenantEvent[];

  // Actions
  actions: {
    // Tenant management
    loadTenant: (tenantId: string) => Promise<void>;
    updateTenant: (updates: Partial<TenantConfig>) => Promise<void>;
    suspendTenant: (reason?: string) => Promise<void>;
    resumeTenant: () => Promise<void>;
    terminateTenant: () => Promise<void>;

    // Provisioning
    provisionTenant: (request: TenantProvisioningRequest) => Promise<string>;
    checkProvisioningStatus: (requestId: string) => Promise<void>;

    // Resource management
    loadResources: () => Promise<void>;
    updateResourceLimits: (limits: Partial<ResourceLimits>) => Promise<void>;
    loadUsage: (period?: { start: Date; end: Date }) => Promise<void>;

    // Portal management
    loadPortalConfig: () => Promise<void>;
    updatePortalConfig: (config: Partial<TenantPortalConfig>) => Promise<void>;

    // Health monitoring
    checkHealth: () => Promise<void>;

    // Events
    loadEvents: (filter?: Partial<TenantEvent>) => Promise<void>;

    // Utilities
    refresh: () => Promise<void>;
    reset: () => void;
  };

  // Computed properties
  computed: {
    isHealthy: boolean;
    isActive: boolean;
    isProvisioned: boolean;
    resourceUtilization: Record<string, number>;
    canManage: boolean;
  };
}

export function useTenantManagement(options: UseTenantManagementOptions = {}): UseTenantManagementReturn {
  const { tenantId, autoRefresh = false, refreshInterval = 30000 } = options;

  // Services
  const tenantService = useMemo(() => new TenantProvisioningService(), []);
  const resourceService = useMemo(() => new ResourceAllocationService(), []);

  // State
  const [tenant, setTenant] = useState<TenantConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provisioning, setProvisioning] = useState<TenantProvisioningStatus | null>(null);
  const [resources, setResources] = useState<ResourceAllocation[]>([]);
  const [usage, setUsage] = useState<TenantUsage | null>(null);
  const [portalConfig, setPortalConfig] = useState<TenantPortalConfig | null>(null);
  const [health, setHealth] = useState<TenantServiceHealth | null>(null);
  const [events, setEvents] = useState<TenantEvent[]>([]);

  // Helper function to handle errors
  const handleError = useCallback((error: Error, context: string) => {
    console.error(`Error in ${context}:`, error);
    setError(`${context}: ${error.message}`);
  }, []);

  // Load tenant data
  const loadTenant = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const tenantData = await tenantService.getTenant(id);
      setTenant(tenantData);
    } catch (error) {
      handleError(error as Error, 'loading tenant');
    } finally {
      setIsLoading(false);
    }
  }, [tenantService, handleError]);

  // Update tenant
  const updateTenant = useCallback(async (updates: Partial<TenantConfig>) => {
    if (!tenant) return;

    setIsLoading(true);
    setError(null);

    try {
      const updated = await tenantService.updateTenant(tenant.id, updates);
      setTenant(updated);
    } catch (error) {
      handleError(error as Error, 'updating tenant');
    } finally {
      setIsLoading(false);
    }
  }, [tenant, tenantService, handleError]);

  // Suspend tenant
  const suspendTenant = useCallback(async (reason?: string) => {
    if (!tenant) return;

    setIsLoading(true);
    setError(null);

    try {
      await tenantService.suspendTenant(tenant.id, reason);
      setTenant(prev => prev ? { ...prev, status: 'suspended' } : null);
    } catch (error) {
      handleError(error as Error, 'suspending tenant');
    } finally {
      setIsLoading(false);
    }
  }, [tenant, tenantService, handleError]);

  // Resume tenant
  const resumeTenant = useCallback(async () => {
    if (!tenant) return;

    setIsLoading(true);
    setError(null);

    try {
      await tenantService.resumeTenant(tenant.id);
      setTenant(prev => prev ? { ...prev, status: 'active' } : null);
    } catch (error) {
      handleError(error as Error, 'resuming tenant');
    } finally {
      setIsLoading(false);
    }
  }, [tenant, tenantService, handleError]);

  // Terminate tenant
  const terminateTenant = useCallback(async () => {
    if (!tenant) return;

    setIsLoading(true);
    setError(null);

    try {
      await tenantService.terminateTenant(tenant.id);
      setTenant(prev => prev ? { ...prev, status: 'terminated' } : null);
    } catch (error) {
      handleError(error as Error, 'terminating tenant');
    } finally {
      setIsLoading(false);
    }
  }, [tenant, tenantService, handleError]);

  // Provision tenant
  const provisionTenant = useCallback(async (request: TenantProvisioningRequest): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const requestId = await tenantService.provisionTenant(request);
      return requestId;
    } catch (error) {
      handleError(error as Error, 'provisioning tenant');
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [tenantService, handleError]);

  // Check provisioning status
  const checkProvisioningStatus = useCallback(async (requestId: string) => {
    try {
      const status = await tenantService.getProvisioningStatus(requestId);
      setProvisioning(status);
    } catch (error) {
      handleError(error as Error, 'checking provisioning status');
    }
  }, [tenantService, handleError]);

  // Load resources
  const loadResources = useCallback(async () => {
    if (!tenant) return;

    try {
      const resourceData = await resourceService.getResourceAllocations(tenant.id);
      setResources(resourceData);
    } catch (error) {
      handleError(error as Error, 'loading resources');
    }
  }, [tenant, resourceService, handleError]);

  // Update resource limits
  const updateResourceLimits = useCallback(async (limits: Partial<ResourceLimits>) => {
    if (!tenant) return;

    setIsLoading(true);
    setError(null);

    try {
      await resourceService.updateResourceLimits(tenant.id, limits);
      // Update tenant with new limits
      setTenant(prev => prev ? { ...prev, limits: { ...prev.limits, ...limits } } : null);
      // Reload resources to get updated data
      await loadResources();
    } catch (error) {
      handleError(error as Error, 'updating resource limits');
    } finally {
      setIsLoading(false);
    }
  }, [tenant, resourceService, loadResources, handleError]);

  // Load usage
  const loadUsage = useCallback(async (period?: { start: Date; end: Date }) => {
    if (!tenant) return;

    try {
      const usageData = await tenantService.getUsageMetrics(tenant.id, period);
      setUsage(usageData);
    } catch (error) {
      handleError(error as Error, 'loading usage');
    }
  }, [tenant, tenantService, handleError]);

  // Load portal config
  const loadPortalConfig = useCallback(async () => {
    if (!tenant) return;

    try {
      const config = await tenantService.getPortalConfig(tenant.id);
      setPortalConfig(config);
    } catch (error) {
      handleError(error as Error, 'loading portal config');
    }
  }, [tenant, tenantService, handleError]);

  // Update portal config
  const updatePortalConfig = useCallback(async (config: Partial<TenantPortalConfig>) => {
    if (!tenant) return;

    setIsLoading(true);
    setError(null);

    try {
      await tenantService.updatePortalConfig(tenant.id, config);
      setPortalConfig(prev => prev ? { ...prev, ...config } : null);
    } catch (error) {
      handleError(error as Error, 'updating portal config');
    } finally {
      setIsLoading(false);
    }
  }, [tenant, tenantService, handleError]);

  // Check health
  const checkHealth = useCallback(async () => {
    if (!tenant) return;

    try {
      const healthData = await tenantService.getServiceHealth(tenant.id);
      setHealth(healthData);
    } catch (error) {
      handleError(error as Error, 'checking health');
    }
  }, [tenant, tenantService, handleError]);

  // Load events
  const loadEvents = useCallback(async (filter?: Partial<TenantEvent>) => {
    if (!tenant) return;

    try {
      const eventsData = await tenantService.getTenantEvents(tenant.id, filter);
      setEvents(eventsData);
    } catch (error) {
      handleError(error as Error, 'loading events');
    }
  }, [tenant, tenantService, handleError]);

  // Refresh all data
  const refresh = useCallback(async () => {
    if (!tenant) return;

    await Promise.allSettled([
      loadTenant(tenant.id),
      loadResources(),
      loadUsage(),
      loadPortalConfig(),
      checkHealth(),
      loadEvents(),
    ]);
  }, [tenant, loadTenant, loadResources, loadUsage, loadPortalConfig, checkHealth, loadEvents]);

  // Reset state
  const reset = useCallback(() => {
    setTenant(null);
    setIsLoading(false);
    setError(null);
    setProvisioning(null);
    setResources([]);
    setUsage(null);
    setPortalConfig(null);
    setHealth(null);
    setEvents([]);
  }, []);

  // Computed properties
  const computed = useMemo(() => ({
    isHealthy: health?.overall === 'healthy',
    isActive: tenant?.status === 'active',
    isProvisioned: tenant?.status !== 'pending',
    resourceUtilization: resources.reduce((acc, resource) => {
      acc[resource.resourceType] = (resource.used / resource.allocated) * 100;
      return acc;
    }, {} as Record<string, number>),
    canManage: tenant?.status === 'active' || tenant?.status === 'suspended',
  }), [health, tenant, resources]);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !tenant) return;

    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, tenant, refresh, refreshInterval]);

  // Load initial data when tenantId changes
  useEffect(() => {
    if (tenantId) {
      loadTenant(tenantId);
    } else {
      reset();
    }
  }, [tenantId, loadTenant, reset]);

  return {
    // State
    tenant,
    isLoading,
    error,
    provisioning,
    resources,
    usage,
    portalConfig,
    health,
    events,

    // Actions
    actions: {
      loadTenant,
      updateTenant,
      suspendTenant,
      resumeTenant,
      terminateTenant,
      provisionTenant,
      checkProvisioningStatus,
      loadResources,
      updateResourceLimits,
      loadUsage,
      loadPortalConfig,
      updatePortalConfig,
      checkHealth,
      loadEvents,
      refresh,
      reset,
    },

    // Computed
    computed,
  };
}
