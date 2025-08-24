'use client';

import { useAuth } from './AuthProvider';
import { Permission, UserRole } from '@/types/auth';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermissions?: Permission[];
  requiredRole?: UserRole;
  requireMasterAdmin?: boolean;
  fallbackPath?: string;
}

export function ProtectedRoute({
  children,
  requiredPermissions = [],
  requiredRole,
  requireMasterAdmin = false,
  fallbackPath = '/login',
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading, hasPermission, isMasterAdmin } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.push(fallbackPath);
      return;
    }

    // Check master admin requirement
    if (requireMasterAdmin && !isMasterAdmin()) {
      router.push('/unauthorized');
      return;
    }

    // Check role requirement
    if (requiredRole && user?.role !== requiredRole) {
      router.push('/unauthorized');
      return;
    }

    // Check permission requirements
    if (requiredPermissions.length > 0 && !hasPermission(requiredPermissions)) {
      router.push('/unauthorized');
      return;
    }
  }, [
    isAuthenticated,
    isLoading,
    user,
    requiredPermissions,
    requiredRole,
    requireMasterAdmin,
    router,
    hasPermission,
    isMasterAdmin,
    fallbackPath,
  ]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect to login
  }

  // Check access after loading is complete
  if (requireMasterAdmin && !isMasterAdmin()) {
    return null; // Will redirect to unauthorized
  }

  if (requiredRole && user?.role !== requiredRole) {
    return null; // Will redirect to unauthorized
  }

  if (requiredPermissions.length > 0 && !hasPermission(requiredPermissions)) {
    return null; // Will redirect to unauthorized
  }

  return <>{children}</>;
}

// Higher-order component for easier usage
export function withProtectedRoute<T extends object>(
  Component: React.ComponentType<T>,
  protectionConfig?: Omit<ProtectedRouteProps, 'children'>
) {
  return function ProtectedComponent(props: T) {
    return (
      <ProtectedRoute {...protectionConfig}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}