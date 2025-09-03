'use client';

import { AuthProvider, useAuth } from '@dotmac/auth';
import type { PartialAuthConfig } from '@dotmac/auth';
import { createContext, useContext } from 'react';

// Tenant-specific configuration
const tenantAuthConfig: PartialAuthConfig = {
  sessionTimeout: 20 * 60 * 1000, // 20 minutes
  enableMFA: true,
  enablePermissions: true,
  requirePasswordComplexity: true,
  maxLoginAttempts: 3,
  lockoutDuration: 15 * 60 * 1000, // 15 minutes
  enableAuditLog: true,
  tokenRefreshThreshold: 3 * 60 * 1000, // 3 minutes
  endpoints: {
    login: '/api/v1/tenant-admin/auth/login',
    logout: '/api/v1/tenant-admin/auth/logout',
    refresh: '/api/v1/tenant-admin/auth/refresh',
    profile: '/api/v1/tenant-admin/auth/me',
  },
};

interface TenantInfo {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  status: 'active' | 'pending' | 'suspended' | 'cancelled';
  tier: string;
  custom_domain?: string;
  primary_color?: string;
  logo_url?: string;
  features?: string[];
}

interface TenantAuthContextValue {
  tenant: TenantInfo | null;
  tenantStatus: string;
  isValidTenant: boolean;
}

const TenantAuthContext = createContext<TenantAuthContextValue | null>(null);

/**
 * Tenant-specific auth provider that wraps the universal @dotmac/auth
 * Provides tenant context alongside user authentication
 */
export function TenantAuthProvider({ children }: { children: React.ReactNode }) {
  // Use the management portal configuration as base (closest to tenant needs)
  return (
    <AuthProvider variant='secure' portal='management' config={tenantAuthConfig}>
      <TenantAuthWrapper>{children}</TenantAuthWrapper>
    </AuthProvider>
  );
}

/**
 * Internal wrapper to provide tenant-specific context
 */
function TenantAuthWrapper({ children }: { children: React.ReactNode }) {
  const auth = useAuth();

  // Extract tenant info from user metadata
  const tenant: TenantInfo | null = auth.user
    ? {
        id: auth.user.tenantId,
        name: auth.user.metadata?.tenantName || '',
        display_name: auth.user.metadata?.tenantDisplayName || '',
        slug: auth.user.metadata?.tenantSlug || '',
        status: auth.user.metadata?.tenantStatus || 'active',
        tier: auth.user.metadata?.tenantTier || 'standard',
        custom_domain: auth.user.metadata?.tenantCustomDomain,
        primary_color: auth.user.metadata?.tenantPrimaryColor,
        logo_url: auth.user.metadata?.tenantLogoUrl,
        features: auth.user.metadata?.tenantFeatures || [],
      }
    : null;

  const tenantAuthValue: TenantAuthContextValue = {
    tenant,
    tenantStatus: tenant?.status || 'unknown',
    isValidTenant: tenant?.status === 'active',
  };

  return (
    <TenantAuthContext.Provider value={tenantAuthValue}>{children}</TenantAuthContext.Provider>
  );
}

/**
 * Hook to access tenant authentication context
 * Combines user auth from @dotmac/auth with tenant-specific data
 */
export function useTenantAuth() {
  const auth = useAuth();
  const tenantContext = useContext(TenantAuthContext);

  if (!tenantContext) {
    throw new Error('useTenantAuth must be used within a TenantAuthProvider');
  }

  return {
    // Re-export all auth functionality
    ...auth,
    // Add tenant-specific data
    tenant: tenantContext.tenant,
    tenantStatus: tenantContext.tenantStatus,
    isValidTenant: tenantContext.isValidTenant,
    // Override isAuthenticated to include tenant validation
    isAuthenticated: auth.isAuthenticated && tenantContext.isValidTenant,
  };
}
