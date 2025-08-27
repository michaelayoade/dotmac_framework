/**
 * React Hooks for Multi-Tenant Support
 * Provides React integration for tenant management
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { tenantManager, TenantInfo, TenantContext, TenantLimits } from '../lib/tenant-manager';
import { useAuth } from './useAuth';
import { monitoring } from '../lib/monitoring';

// Hook for tenant context
export function useTenant() {
  const [tenantContext, setTenantContext] = useState<TenantContext>(tenantManager.getContext());
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    // Listen for tenant context changes
    const handleContextChange = (data: any) => {
      setTenantContext(tenantManager.getContext());
    };

    const eventTypes = ['tenant_switched', 'tenants_loaded', 'tenant_settings_updated'];
    eventTypes.forEach(event => {
      tenantManager.on(event, handleContextChange);
    });

    // Load tenants on auth
    if (isAuthenticated) {
      tenantManager.loadTenants().catch(error => {
        console.error('Failed to load tenants:', error);
      });
    }

    return () => {
      eventTypes.forEach(event => {
        tenantManager.off(event, handleContextChange);
      });
    };
  }, [isAuthenticated]);

  const switchTenant = useCallback(async (tenantId: string): Promise<void> => {
    monitoring.recordInteraction({
      event: 'tenant_switch_initiated',
      target: tenantId,
    });

    try {
      await tenantManager.switchTenant(tenantId);
    } catch (error) {
      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'tenant_switch_hook',
        metadata: { tenantId },
      });
      throw error;
    }
  }, []);

  const refreshTenants = useCallback(async (): Promise<TenantInfo[]> => {
    try {
      return await tenantManager.loadTenants();
    } catch (error) {
      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'tenant_refresh',
      });
      throw error;
    }
  }, []);

  return {
    // Context
    tenant: tenantContext.tenant,
    availableTenants: tenantContext.availableTenants,
    isMultiTenant: tenantContext.isMultiTenant,
    canSwitchTenants: tenantContext.canSwitchTenants,
    
    // Actions
    switchTenant,
    refreshTenants,
  };
}

// Hook for tenant features
export function useTenantFeatures() {
  const { tenant } = useTenant();

  const hasFeature = useCallback((feature: string): boolean => {
    return tenantManager.hasFeature(feature);
  }, [tenant]);

  const hasAnyFeature = useCallback((features: string[]): boolean => {
    return features.some(feature => tenantManager.hasFeature(feature));
  }, [tenant]);

  const getEnabledFeatures = useCallback((): string[] => {
    return tenant?.features || [];
  }, [tenant]);

  const isFeatureEnabled = useCallback((module: string): boolean => {
    return tenant?.settings.features.enabledModules.includes(module) || false;
  }, [tenant]);

  return {
    hasFeature,
    hasAnyFeature,
    getEnabledFeatures,
    isFeatureEnabled,
    features: tenant?.features || [],
    enabledModules: tenant?.settings.features.enabledModules || [],
  };
}

// Hook for tenant limits and quotas
export function useTenantLimits() {
  const { tenant } = useTenant();

  const isWithinLimits = useCallback((resource: keyof TenantLimits['currentUsage']): boolean => {
    return tenantManager.isWithinLimits(resource);
  }, [tenant]);

  const getRemainingQuota = useCallback((resource: keyof TenantLimits['currentUsage']): number => {
    return tenantManager.getRemainingQuota(resource);
  }, [tenant]);

  const getUsagePercentage = useCallback((resource: keyof TenantLimits['currentUsage']): number => {
    return tenantManager.getUsagePercentage(resource);
  }, [tenant]);

  const getQuotaStatus = useCallback((resource: keyof TenantLimits['currentUsage']) => {
    const percentage = getUsagePercentage(resource);
    const remaining = getRemainingQuota(resource);
    const isWithinLimit = isWithinLimits(resource);

    return {
      percentage,
      remaining,
      isWithinLimit,
      isNearLimit: percentage >= 80,
      isAtLimit: percentage >= 100,
      status: percentage >= 100 ? 'exceeded' : percentage >= 90 ? 'critical' : percentage >= 80 ? 'warning' : 'normal',
    };
  }, [getUsagePercentage, getRemainingQuota, isWithinLimits]);

  const limits = useMemo(() => tenant?.limits || null, [tenant]);

  return {
    limits,
    isWithinLimits,
    getRemainingQuota,
    getUsagePercentage,
    getQuotaStatus,
  };
}

// Hook for tenant settings management
export function useTenantSettings() {
  const { tenant } = useTenant();
  const [isUpdating, setIsUpdating] = useState(false);

  const updateSettings = useCallback(async (settings: Partial<import('../lib/tenant-manager').TenantSettings>): Promise<TenantInfo> => {
    if (!tenant) {
      throw new Error('No active tenant');
    }

    setIsUpdating(true);
    
    try {
      monitoring.recordInteraction({
        event: 'tenant_settings_update_initiated',
        target: tenant.id,
        metadata: { settingsKeys: Object.keys(settings) },
      });

      const updatedTenant = await tenantManager.updateTenantSettings(settings);
      
      monitoring.recordBusinessMetric({
        metric: 'tenant_settings_updated',
        value: 1,
        dimensions: {
          tenant_id: tenant.id,
          settings_count: Object.keys(settings).length.toString(),
        },
      });

      return updatedTenant;
    } catch (error) {
      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'tenant_settings_update',
        metadata: { tenantId: tenant.id, settings },
      });
      
      throw error;
    } finally {
      setIsUpdating(false);
    }
  }, [tenant]);

  const settings = useMemo(() => tenant?.settings || null, [tenant]);

  return {
    settings,
    updateSettings,
    isUpdating,
  };
}

// Hook for tenant-aware routing
export function useTenantRouting() {
  const { tenant, isMultiTenant } = useTenant();

  const buildTenantUrl = useCallback((path: string): string => {
    if (!isMultiTenant || !tenant) {
      return path;
    }

    // Add tenant prefix if not already present
    const tenantPrefix = `/tenant/${tenant.id}`;
    if (path.startsWith(tenantPrefix)) {
      return path;
    }

    return `${tenantPrefix}${path.startsWith('/') ? path : `/${path}`}`;
  }, [tenant, isMultiTenant]);

  const navigateWithTenant = useCallback((path: string) => {
    const tenantAwarePath = buildTenantUrl(path);
    
    if (typeof window !== 'undefined') {
      window.location.href = tenantAwarePath;
    }
  }, [buildTenantUrl]);

  const isCurrentPath = useCallback((path: string): boolean => {
    if (typeof window === 'undefined') return false;
    
    const currentPath = window.location.pathname;
    const tenantAwarePath = buildTenantUrl(path);
    
    return currentPath === tenantAwarePath;
  }, [buildTenantUrl]);

  return {
    buildTenantUrl,
    navigateWithTenant,
    isCurrentPath,
    tenantPrefix: tenant ? `/tenant/${tenant.id}` : '',
  };
}

// Hook for tenant branding
export function useTenantBranding() {
  const { tenant } = useTenant();

  const branding = useMemo(() => {
    return tenant?.settings.branding || {
      logo: undefined,
      primaryColor: undefined,
      secondaryColor: undefined,
      customCss: undefined,
    };
  }, [tenant]);

  const getCSSVariable = useCallback((variable: string): string | null => {
    if (typeof window === 'undefined') return null;
    
    return getComputedStyle(document.documentElement)
      .getPropertyValue(variable)
      .trim() || null;
  }, []);

  const primaryColor = useMemo(() => {
    return branding.primaryColor || getCSSVariable('--primary-color');
  }, [branding.primaryColor, getCSSVariable]);

  const secondaryColor = useMemo(() => {
    return branding.secondaryColor || getCSSVariable('--secondary-color');
  }, [branding.secondaryColor, getCSSVariable]);

  return {
    branding,
    logo: branding.logo,
    primaryColor,
    secondaryColor,
    hasCustomBranding: !!(branding.logo || branding.primaryColor || branding.secondaryColor || branding.customCss),
  };
}

// Component wrapper for tenant-aware features
export function withTenantFeature<T extends {}>(
  Component: React.ComponentType<T>,
  requiredFeatures: string | string[],
  fallback?: React.ComponentType<T>
) {
  const features = Array.isArray(requiredFeatures) ? requiredFeatures : [requiredFeatures];
  
  const WrappedComponent = (props: T) => {
    const { hasAnyFeature } = useTenantFeatures();
    
    if (!hasAnyFeature(features)) {
      const FallbackComponent = fallback;
      return FallbackComponent ? <FallbackComponent {...props} /> : null;
    }

    return <Component {...props} />;
  };

  WrappedComponent.displayName = `withTenantFeature(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

// Component wrapper for quota-aware features
export function withQuotaCheck<T extends {}>(
  Component: React.ComponentType<T>,
  resource: keyof TenantLimits['currentUsage'],
  warningComponent?: React.ComponentType<T & { quotaStatus: any }>
) {
  const WrappedComponent = (props: T) => {
    const { getQuotaStatus } = useTenantLimits();
    const quotaStatus = getQuotaStatus(resource);

    if (quotaStatus.isAtLimit) {
      const WarningComponent = warningComponent;
      return WarningComponent ? 
        <WarningComponent {...props} quotaStatus={quotaStatus} /> : 
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">Resource limit exceeded for {resource}</p>
        </div>;
    }

    if (quotaStatus.isNearLimit && warningComponent) {
      const WarningComponent = warningComponent;
      return <WarningComponent {...props} quotaStatus={quotaStatus} />;
    }

    return <Component {...props} />;
  };

  WrappedComponent.displayName = `withQuotaCheck(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}