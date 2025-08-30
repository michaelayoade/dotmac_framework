/**
 * Portal-specific audit hooks
 * Configured with portal-specific defaults and optimizations
 */

'use client';

import { useUniversalAudit } from './useUniversalAudit';
import type { UseAuditSystemOptions, ActionCategory } from '../types';

// Admin portal audit hook
export function useAdminAudit(options: Partial<UseAuditSystemOptions> = {}) {
  const adminCategories: ActionCategory[] = [
    'authentication',
    'customer_management',
    'billing_operations',
    'service_management',
    'network_operations',
    'configuration',
    'compliance',
    'system_admin',
    'communication',
    'reporting'
  ];

  return useUniversalAudit({
    portalType: 'admin',
    enableAutoTracking: true,
    trackPageViews: true,
    trackUserActions: true,
    customCategories: adminCategories,
    ...options
  });
}

// Management portal audit hook
export function useManagementAudit(options: Partial<UseAuditSystemOptions> = {}) {
  const managementCategories: ActionCategory[] = [
    'authentication',
    'customer_management',
    'billing_operations',
    'service_management',
    'network_operations',
    'configuration',
    'compliance',
    'system_admin',
    'communication',
    'reporting'
  ];

  return useUniversalAudit({
    portalType: 'management',
    enableAutoTracking: true,
    trackPageViews: true,
    trackUserActions: true,
    customCategories: managementCategories,
    ...options
  });
}

// Reseller portal audit hook
export function useResellerAudit(options: Partial<UseAuditSystemOptions> = {}) {
  const resellerCategories: ActionCategory[] = [
    'authentication',
    'customer_management',
    'billing_operations',
    'service_management',
    'communication',
    'reporting'
  ];

  return useUniversalAudit({
    portalType: 'reseller',
    enableAutoTracking: true,
    trackPageViews: true,
    trackUserActions: true,
    customCategories: resellerCategories,
    ...options
  });
}

// Customer portal audit hook
export function useCustomerAudit(options: Partial<UseAuditSystemOptions> = {}) {
  const customerCategories: ActionCategory[] = [
    'authentication',
    'billing_operations',
    'service_management',
    'communication'
  ];

  return useUniversalAudit({
    portalType: 'customer',
    enableAutoTracking: true,
    trackPageViews: false, // Less aggressive tracking for customers
    trackUserActions: false,
    customCategories: customerCategories,
    ...options
  });
}

// Technician portal audit hook
export function useTechnicianAudit(options: Partial<UseAuditSystemOptions> = {}) {
  const technicianCategories: ActionCategory[] = [
    'authentication',
    'service_management',
    'network_operations',
    'communication'
  ];

  return useUniversalAudit({
    portalType: 'technician',
    enableAutoTracking: true,
    trackPageViews: true,
    trackUserActions: true,
    customCategories: technicianCategories,
    ...options
  });
}

// Portal-specific activity feed hooks for existing UniversalActivityFeed integration
export function useAdminActivity(options: Partial<UseAuditSystemOptions> = {}) {
  const audit = useAdminAudit(options);

  return {
    activities: audit.activities,
    isLoading: audit.isLoading,
    error: audit.error,
    refresh: audit.getActivities,
    logAction: audit.logUserAction
  };
}

export function useCustomerActivity(options: Partial<UseAuditSystemOptions> = {}) {
  const audit = useCustomerAudit(options);

  return {
    activities: audit.activities,
    isLoading: audit.isLoading,
    error: audit.error,
    refresh: audit.getActivities,
    logAction: audit.logUserAction
  };
}

export function useResellerActivity(options: Partial<UseAuditSystemOptions> = {}) {
  const audit = useResellerAudit(options);

  return {
    activities: audit.activities,
    isLoading: audit.isLoading,
    error: audit.error,
    refresh: audit.getActivities,
    logAction: audit.logUserAction
  };
}

export function useManagementActivity(options: Partial<UseAuditSystemOptions> = {}) {
  const audit = useManagementAudit(options);

  return {
    activities: audit.activities,
    isLoading: audit.isLoading,
    error: audit.error,
    refresh: audit.getActivities,
    logAction: audit.logUserAction
  };
}

export function useTechnicianActivity(options: Partial<UseAuditSystemOptions> = {}) {
  const audit = useTechnicianAudit(options);

  return {
    activities: audit.activities,
    isLoading: audit.isLoading,
    error: audit.error,
    refresh: audit.getActivities,
    logAction: audit.logUserAction
  };
}
