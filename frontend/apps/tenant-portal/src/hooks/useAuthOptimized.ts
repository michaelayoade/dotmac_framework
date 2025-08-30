/**
 * Optimized Authentication Hooks
 * Performance-optimized hooks for consuming auth state
 */

import { useMemo } from 'react';
import { useTenantAuth } from '@/components/auth/TenantAuthProviderNew';

/**
 * Hook that only re-renders when authentication status changes
 * Use this when you only need to know if user is authenticated
 */
export function useIsAuthenticated() {
  const { isAuthenticated, isLoading } = useTenantAuth();

  return useMemo(() => ({
    isAuthenticated,
    isLoading,
  }), [isAuthenticated, isLoading]);
}

/**
 * Hook that only re-renders when user data changes
 * Use this when you need user information but not tenant info
 */
export function useCurrentUser() {
  const { user, isLoading } = useTenantAuth();

  return useMemo(() => ({
    user,
    isLoading,
  }), [user, isLoading]);
}

/**
 * Hook that only re-renders when tenant data changes
 * Use this when you need tenant information but not user info
 */
export function useCurrentTenant() {
  const { tenant, isLoading } = useTenantAuth();

  return useMemo(() => ({
    tenant,
    isLoading,
  }), [tenant, isLoading]);
}

/**
 * Hook for authentication actions (login, logout, refresh)
 * These functions are memoized and won't cause re-renders
 */
export function useAuthActions() {
  const { login, logout, refreshAuth } = useTenantAuth();

  return useMemo(() => ({
    login,
    logout,
    refreshAuth,
  }), [login, logout, refreshAuth]);
}

/**
 * Hook for user permissions
 * Only re-renders when user permissions change
 */
export function useUserPermissions() {
  const { user } = useTenantAuth();

  return useMemo(() => {
    const permissions = user?.permissions || [];

    const hasPermission = (permission: string) => permissions.includes(permission);
    const hasAnyPermission = (permissionList: string[]) =>
      permissionList.some(permission => permissions.includes(permission));
    const hasAllPermissions = (permissionList: string[]) =>
      permissionList.every(permission => permissions.includes(permission));

    return {
      permissions,
      hasPermission,
      hasAnyPermission,
      hasAllPermissions,
    };
  }, [user?.permissions]);
}

/**
 * Hook for tenant status information
 * Only re-renders when tenant status changes
 */
export function useTenantStatus() {
  const { tenant } = useTenantAuth();

  return useMemo(() => {
    const isActive = tenant?.status === 'active';
    const isPending = tenant?.status === 'pending';
    const isSuspended = tenant?.status === 'suspended';
    const isCancelled = tenant?.status === 'cancelled';

    return {
      status: tenant?.status,
      isActive,
      isPending,
      isSuspended,
      isCancelled,
    };
  }, [tenant?.status]);
}

/**
 * Hook for checking if user has a specific role
 * Only re-renders when user role changes
 */
export function useUserRole() {
  const { user } = useTenantAuth();

  return useMemo(() => {
    const role = user?.role;

    const isAdmin = role === 'admin';
    const isManager = role === 'manager';
    const isUser = role === 'user';
    const isOwner = role === 'owner';

    const hasRole = (targetRole: string) => role === targetRole;
    const hasMinimumRole = (minimumRole: string) => {
      const roleHierarchy = ['user', 'manager', 'admin', 'owner'];
      const currentRoleIndex = roleHierarchy.indexOf(role || '');
      const minimumRoleIndex = roleHierarchy.indexOf(minimumRole);

      return currentRoleIndex >= minimumRoleIndex;
    };

    return {
      role,
      isAdmin,
      isManager,
      isUser,
      isOwner,
      hasRole,
      hasMinimumRole,
    };
  }, [user?.role]);
}
