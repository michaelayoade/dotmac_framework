/**
 * ISP Framework Tenant Provider
 * Provides multi-tenant context to the entire application
 * Uses the composition pattern with focused sub-hooks
 */

import { ReactNode, useEffect } from 'react';
import { ISPTenantContext, createISPTenantContextValue } from '../hooks/useISPTenant';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';

interface ISPTenantProviderProps {
  children: ReactNode;
  tenantId?: string; // Optional override for specific tenant
  autoLoadOnAuth?: boolean; // Auto-load tenant when user authenticates
  enableRealTimeUpdates?: boolean; // Enable real-time tenant updates
}

export function ISPTenantProvider({
  children,
  tenantId,
  autoLoadOnAuth = true,
  enableRealTimeUpdates = true,
}: ISPTenantProviderProps) {
  // Create the composed context value
  const tenantContextValue = createISPTenantContextValue();
  
  // Access stores for integration
  const { isAuthenticated, user } = useAuthStore();
  const { currentTenant, switchTenant, clearTenant } = useTenantStore();

  // Auto-load tenant when user authenticates
  useEffect(() => {
    if (!autoLoadOnAuth || !isAuthenticated || !user || currentTenant) return;

    // Determine tenant ID from authenticated user data
    let targetTenantId = tenantId;

    if (!targetTenantId) {
      // Extract tenant ID from user data
      if (user.tenant_id) {
        targetTenantId = user.tenant_id;
      } else if (user.profile?.tenant_id) {
        targetTenantId = user.profile.tenant_id;
      }
    }

    if (targetTenantId) {
      tenantContextValue.loadTenant(targetTenantId).catch((err) => {
        console.error('Failed to auto-load tenant:', err);
      });
    }
  }, [
    isAuthenticated,
    user,
    tenantId,
    autoLoadOnAuth,
    currentTenant,
    tenantContextValue,
  ]);

  // Clear tenant when user logs out
  useEffect(() => {
    if (!isAuthenticated && currentTenant) {
      clearTenant();
      tenantContextValue.clearTenant();
    }
  }, [isAuthenticated, currentTenant, clearTenant, tenantContextValue]);

  // Apply branding when tenant session changes
  useEffect(() => {
    if (tenantContextValue.session && tenantContextValue.getBranding) {
      tenantContextValue.applyBranding();
    }
  }, [tenantContextValue.session, tenantContextValue]);

  // Setup real-time updates for tenant changes
  useEffect(() => {
    if (!enableRealTimeUpdates || !currentTenant) return;

    const handleTenantUpdate = (event: CustomEvent) => {
      const { type, data } = event.detail;
      
      switch (type) {
        case 'tenant_updated':
          // Refresh tenant data when updates occur
          tenantContextValue.refreshTenant?.();
          break;
          
        case 'tenant_settings_changed':
          // Update settings and reapply branding
          if (data.branding_changed) {
            tenantContextValue.applyBranding();
          }
          break;
          
        case 'tenant_limits_updated':
          // Refresh limits data
          tenantContextValue.refreshTenant?.();
          break;
          
        case 'tenant_permissions_changed':
          // Refresh permissions
          tenantContextValue.refreshTenant?.();
          break;
      }
    };

    // Listen for real-time tenant updates
    window.addEventListener('tenant-update' as any, handleTenantUpdate);
    
    return () => {
      window.removeEventListener('tenant-update' as any, handleTenantUpdate);
    };
  }, [enableRealTimeUpdates, currentTenant, tenantContextValue]);

  // Handle tenant switching from store
  useEffect(() => {
    const tenantStoreListener = useTenantStore.subscribe(
      (state) => state.currentTenant,
      (newTenant) => {
        if (newTenant && newTenant.tenant.id !== tenantContextValue.tenant?.id) {
          // Sync with tenant context when store changes
          tenantContextValue.loadTenant(newTenant.tenant.id);
        }
      }
    );

    return tenantStoreListener;
  }, [tenantContextValue]);

  return (
    <ISPTenantContext.Provider value={tenantContextValue}>
      {children}
    </ISPTenantContext.Provider>
  );
}
