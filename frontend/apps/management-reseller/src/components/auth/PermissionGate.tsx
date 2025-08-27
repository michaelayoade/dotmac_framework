'use client';

import type { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/lib/permissions/PermissionSystem';

interface PermissionGateProps {
  children: ReactNode;
  permission?: Permission | string;
  permissions?: (Permission | string)[];
  requireAll?: boolean; // If true, requires all permissions. If false, requires any permission
  fallback?: ReactNode;
  role?: string;
  department?: string;
  onUnauthorized?: () => void;
}

/**
 * PermissionGate component - conditionally renders children based on user permissions
 * 
 * Usage:
 * <PermissionGate permission={Permission.MANAGE_RESELLERS}>
 *   <ManageResellerButton />
 * </PermissionGate>
 * 
 * <PermissionGate permissions={[Permission.VIEW_ANALYTICS, Permission.EXPORT_DATA]} requireAll={false}>
 *   <AnalyticsSection />
 * </PermissionGate>
 */
export function PermissionGate({
  children,
  permission,
  permissions,
  requireAll = true,
  fallback = null,
  role,
  department,
  onUnauthorized,
}: PermissionGateProps) {
  const permissionSystem = usePermissions();

  // Check single permission
  if (permission) {
    const hasPermission = permissionSystem.hasPermission(permission);
    if (!hasPermission) {
      onUnauthorized?.();
      return <>{fallback}</>;
    }
  }

  // Check multiple permissions
  if (permissions && permissions.length > 0) {
    const hasPermissions = requireAll 
      ? permissionSystem.hasAllPermissions(permissions)
      : permissionSystem.hasAnyPermission(permissions);
    
    if (!hasPermissions) {
      onUnauthorized?.();
      return <>{fallback}</>;
    }
  }

  // Check role
  if (role) {
    const userRole = permissionSystem.getUserRole();
    if (userRole !== role) {
      onUnauthorized?.();
      return <>{fallback}</>;
    }
  }

  // Check department
  if (department) {
    const belongsToDepartment = permissionSystem.belongsToDepartment(department);
    if (!belongsToDepartment) {
      onUnauthorized?.();
      return <>{fallback}</>;
    }
  }

  return <>{children}</>;
}

// Specialized permission gates for common use cases

interface BusinessPermissionGateProps {
  children: ReactNode;
  fallback?: ReactNode;
  onUnauthorized?: () => void;
}

export function CanManageResellers({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  return (
    <PermissionGate 
      permission={Permission.MANAGE_RESELLERS}
      fallback={fallback}
      onUnauthorized={onUnauthorized}
    >
      {children}
    </PermissionGate>
  );
}

export function CanApproveCommissions({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  return (
    <PermissionGate 
      permission={Permission.APPROVE_COMMISSIONS}
      fallback={fallback}
      onUnauthorized={onUnauthorized}
    >
      {children}
    </PermissionGate>
  );
}

export function CanViewAnalytics({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  return (
    <PermissionGate 
      permission={Permission.VIEW_ANALYTICS}
      fallback={fallback}
      onUnauthorized={onUnauthorized}
    >
      {children}
    </PermissionGate>
  );
}

export function CanManageTerritories({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  return (
    <PermissionGate 
      permission={Permission.MANAGE_TERRITORIES}
      fallback={fallback}
      onUnauthorized={onUnauthorized}
    >
      {children}
    </PermissionGate>
  );
}

export function CanManageTraining({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  return (
    <PermissionGate 
      permission={Permission.MANAGE_TRAINING}
      fallback={fallback}
      onUnauthorized={onUnauthorized}
    >
      {children}
    </PermissionGate>
  );
}

// Admin-only gate
export function AdminOnly({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  const permissions = usePermissions();
  
  if (!permissions.isAdmin()) {
    onUnauthorized?.();
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
}

// Manager-level access gate (includes admins and managers)
export function ManagerOnly({ children, fallback, onUnauthorized }: BusinessPermissionGateProps) {
  const permissions = usePermissions();
  
  if (!permissions.isManager()) {
    onUnauthorized?.();
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
}

// Department-specific gate
interface DepartmentGateProps extends BusinessPermissionGateProps {
  department: string;
}

export function DepartmentOnly({ children, department, fallback, onUnauthorized }: DepartmentGateProps) {
  return (
    <PermissionGate 
      department={department}
      fallback={fallback}
      onUnauthorized={onUnauthorized}
    >
      {children}
    </PermissionGate>
  );
}

// Higher-order component for permission-based rendering
export function withPermission<P extends object>(
  Component: React.ComponentType<P>,
  permission: Permission | string,
  fallback?: ReactNode
) {
  const WrappedComponent = (props: P) => (
    <PermissionGate permission={permission} fallback={fallback}>
      <Component {...props} />
    </PermissionGate>
  );

  WrappedComponent.displayName = `withPermission(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

// Hook-based permission component
interface PermissionRenderProps {
  hasPermission: boolean;
  permissions: ReturnType<typeof usePermissions>;
}

interface ConditionalPermissionProps {
  permission?: Permission | string;
  permissions?: (Permission | string)[];
  requireAll?: boolean;
  children: (props: PermissionRenderProps) => ReactNode;
}

export function ConditionalPermission({
  permission,
  permissions,
  requireAll = true,
  children
}: ConditionalPermissionProps) {
  const permissionSystem = usePermissions();
  
  let hasPermission = true;
  
  if (permission) {
    hasPermission = permissionSystem.hasPermission(permission);
  } else if (permissions && permissions.length > 0) {
    hasPermission = requireAll 
      ? permissionSystem.hasAllPermissions(permissions)
      : permissionSystem.hasAnyPermission(permissions);
  }
  
  return <>{children({ hasPermission, permissions: permissionSystem })}</>;
}