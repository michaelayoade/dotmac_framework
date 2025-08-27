import { useMemo } from 'react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';
import { PermissionSystem, Permission, PermissionUtils, type PermissionSystemInstance } from '@/lib/permissions/PermissionSystem';

// Main permission hook
export function usePermissions(): PermissionSystemInstance {
  const { user } = useManagementAuth();
  
  return useMemo(() => {
    return PermissionUtils.create(user);
  }, [user]);
}

// Specific permission hooks for common use cases
export function useHasPermission(permission: Permission | string): boolean {
  const permissions = usePermissions();
  return permissions.hasPermission(permission);
}

export function useHasAnyPermission(permissionList: (Permission | string)[]): boolean {
  const permissions = usePermissions();
  return permissions.hasAnyPermission(permissionList);
}

export function useHasAllPermissions(permissionList: (Permission | string)[]): boolean {
  const permissions = usePermissions();
  return permissions.hasAllPermissions(permissionList);
}

// Business logic permission hooks
export function useCanManageResellers(): boolean {
  const permissions = usePermissions();
  return permissions.canManageResellers();
}

export function useCanApproveCommissions(): boolean {
  const permissions = usePermissions();
  return permissions.canApproveCommissions();
}

export function useCanViewAnalytics(): boolean {
  const permissions = usePermissions();
  return permissions.canViewAnalytics();
}

export function useCanManageTerritories(): boolean {
  const permissions = usePermissions();
  return permissions.canManageTerritories();
}

export function useCanManageTraining(): boolean {
  const permissions = usePermissions();
  return permissions.canManageTraining();
}

export function useCanProcessApplications(): boolean {
  const permissions = usePermissions();
  return permissions.canProcessApplications();
}

// Partner-specific permission hooks
export function usePartnerPermissions() {
  const permissions = usePermissions();
  
  return useMemo(() => ({
    canCreate: permissions.canCreatePartners(),
    canEdit: permissions.canEditPartners(),
    canDelete: permissions.canDeletePartners(),
    canApprove: permissions.canApprovePartners(),
    canSuspend: permissions.canSuspendPartners(),
    canManage: permissions.canManageResellers(),
  }), [permissions]);
}

// Commission-specific permission hooks
export function useCommissionPermissions() {
  const permissions = usePermissions();
  
  return useMemo(() => ({
    canView: permissions.hasPermission(Permission.VIEW_COMMISSIONS),
    canApprove: permissions.canApproveCommissions(),
    canProcessPayouts: permissions.canProcessPayouts(),
    canManageDisputes: permissions.canManageCommissionDisputes(),
  }), [permissions]);
}

// User role hooks
export function useUserRole() {
  const permissions = usePermissions();
  return permissions.getUserRole();
}

export function useIsAdmin(): boolean {
  const permissions = usePermissions();
  return permissions.isAdmin();
}

export function useIsManager(): boolean {
  const permissions = usePermissions();
  return permissions.isManager();
}

export function useUserDepartments(): string[] {
  const permissions = usePermissions();
  return permissions.getUserDepartments();
}

export function useBelongsToDepartment(department: string): boolean {
  const permissions = usePermissions();
  return permissions.belongsToDepartment(department);
}

// Navigation permission hook - filters navigation items based on permissions
export function useFilteredNavigation<T extends { permission?: string }>(items: T[]): T[] {
  const permissions = usePermissions();
  
  return useMemo(() => {
    return items.filter(item => {
      if (!item.permission) return true;
      return permissions.hasPermission(item.permission);
    });
  }, [items, permissions]);
}

// Permission gate hook for conditional rendering
export function usePermissionGate() {
  const permissions = usePermissions();
  
  return useMemo(() => ({
    // Simple permission check
    check: (permission: Permission | string) => permissions.hasPermission(permission),
    
    // Check any of multiple permissions
    checkAny: (permissionList: (Permission | string)[]) => permissions.hasAnyPermission(permissionList),
    
    // Check all of multiple permissions
    checkAll: (permissionList: (Permission | string)[]) => permissions.hasAllPermissions(permissionList),
    
    // Business logic checks
    canManageResellers: () => permissions.canManageResellers(),
    canApproveCommissions: () => permissions.canApproveCommissions(),
    canViewAnalytics: () => permissions.canViewAnalytics(),
    
    // Role checks
    isAdmin: () => permissions.isAdmin(),
    isManager: () => permissions.isManager(),
    
    // Department check
    belongsToDepartment: (department: string) => permissions.belongsToDepartment(department),
  }), [permissions]);
}

// Debug hook for development
export function usePermissionDebug() {
  const permissions = usePermissions();
  const { user } = useManagementAuth();
  
  return useMemo(() => {
    if (process.env.NODE_ENV !== 'development') {
      return { debugInfo: 'Debug info only available in development' };
    }
    
    return {
      user: {
        id: user?.id,
        email: user?.email,
        role: user?.role,
        departments: user?.departments,
      },
      allPermissions: permissions.getAllPermissions(),
      rolePermissions: user ? PermissionUtils.getPermissionsForRole(user.role as any) : [],
      isAuthenticated: permissions.isAuthenticated(),
      isAdmin: permissions.isAdmin(),
      isManager: permissions.isManager(),
      businessChecks: {
        canManageResellers: permissions.canManageResellers(),
        canApproveCommissions: permissions.canApproveCommissions(),
        canViewAnalytics: permissions.canViewAnalytics(),
        canManageTerritories: permissions.canManageTerritories(),
        canManageTraining: permissions.canManageTraining(),
      }
    };
  }, [permissions, user]);
}