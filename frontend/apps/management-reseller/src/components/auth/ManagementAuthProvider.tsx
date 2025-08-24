'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

interface ManagementUser {
  id: string;
  email: string;
  name: string;
  role: 'MASTER_ADMIN' | 'CHANNEL_MANAGER' | 'OPERATIONS_MANAGER';
  permissions: string[];
  departments: string[];
  last_login?: Date;
}

interface ManagementAuthContextValue {
  user: ManagementUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  canManageResellers: () => boolean;
  canApproveCommissions: () => boolean;
  canViewAnalytics: () => boolean;
}

const ManagementAuthContext = createContext<ManagementAuthContextValue | null>(null);

// Helper functions for role mapping
const mapRoleToManagementRole = (apiRole: string): 'MASTER_ADMIN' | 'CHANNEL_MANAGER' | 'OPERATIONS_MANAGER' => {
  switch (apiRole) {
    case 'master_admin':
    case 'platform_admin':
      return 'MASTER_ADMIN';
    case 'channel_manager':
    case 'reseller_manager':
      return 'CHANNEL_MANAGER';
    case 'operations_manager':
    case 'tenant_admin':
      return 'OPERATIONS_MANAGER';
    default:
      return 'OPERATIONS_MANAGER';
  }
};

const mapRoleToPermissions = (apiRole: string): string[] => {
  const basePermissions = ['VIEW_DASHBOARD', 'VIEW_PROFILE'];
  
  switch (apiRole) {
    case 'master_admin':
    case 'platform_admin':
      return [
        ...basePermissions,
        'MANAGE_RESELLERS',
        'APPROVE_COMMISSIONS',
        'VIEW_ANALYTICS',
        'MANAGE_TERRITORIES',
        'PROCESS_PAYOUTS',
        'MANAGE_TRAINING',
        'SYSTEM_ADMIN',
        'USER_MANAGEMENT',
        'PLATFORM_SETTINGS'
      ];
    case 'channel_manager':
    case 'reseller_manager':
      return [
        ...basePermissions,
        'MANAGE_RESELLERS',
        'APPROVE_COMMISSIONS',
        'VIEW_ANALYTICS',
        'MANAGE_TERRITORIES',
        'PROCESS_PAYOUTS',
        'MANAGE_TRAINING'
      ];
    case 'operations_manager':
    case 'tenant_admin':
      return [
        ...basePermissions,
        'VIEW_ANALYTICS',
        'MANAGE_TERRITORIES',
        'VIEW_COMMISSIONS'
      ];
    default:
      return basePermissions;
  }
};

const mapRoleToDepartments = (apiRole: string): string[] => {
  switch (apiRole) {
    case 'master_admin':
    case 'platform_admin':
      return ['Platform Administration', 'System Operations'];
    case 'channel_manager':
    case 'reseller_manager':
      return ['Channel Operations', 'Partner Management'];
    case 'operations_manager':
    case 'tenant_admin':
      return ['Operations', 'Customer Success'];
    default:
      return ['General'];
  }
};

export function useManagementAuth() {
  const context = useContext(ManagementAuthContext);
  if (!context) {
    throw new Error('useManagementAuth must be used within a ManagementAuthProvider');
  }
  return context;
}

export function ManagementAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<ManagementUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const isAuthenticated = !!user;

  const hasPermission = (permission: string) => {
    return user?.permissions.includes(permission) || user?.role === 'MASTER_ADMIN' || false;
  };

  const canManageResellers = () => {
    return hasPermission('MANAGE_RESELLERS') || user?.role === 'CHANNEL_MANAGER';
  };

  const canApproveCommissions = () => {
    return hasPermission('APPROVE_COMMISSIONS') || user?.role === 'CHANNEL_MANAGER';
  };

  const canViewAnalytics = () => {
    return hasPermission('VIEW_ANALYTICS');
  };

  // Real authentication implementation with Management Platform API
  const login = async (credentials: { email: string; password: string }) => {
    setIsLoading(true);
    try {
      // API call to management platform
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
          remember_me: true
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const loginResponse = await response.json();
      
      // Extract user data and map to ManagementUser interface
      const user = loginResponse.user;
      const managementUser: ManagementUser = {
        id: user.user_id || user.id,
        email: user.email,
        name: user.full_name || user.username || 'Management User',
        role: mapRoleToManagementRole(user.role),
        permissions: mapRoleToPermissions(user.role),
        departments: mapRoleToDepartments(user.role),
        last_login: user.last_login ? new Date(user.last_login) : new Date(),
      };

      // Store tokens securely (in production, use HTTP-only cookies)
      sessionStorage.setItem('access_token', loginResponse.access_token);
      sessionStorage.setItem('refresh_token', loginResponse.refresh_token);
      sessionStorage.setItem('management_user', JSON.stringify(managementUser));
      
      setUser(managementUser);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw new Error(error instanceof Error ? error.message : 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      const accessToken = sessionStorage.getItem('access_token');
      
      // Call logout API to revoke server-side session
      if (accessToken) {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch (error) {
      console.error('Logout API failed:', error);
      // Continue with client-side cleanup even if API fails
    } finally {
      // Clean up client-side storage
      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('refresh_token');
      sessionStorage.removeItem('management_user');
      setUser(null);
      router.push('/login');
    }
  };

  const refreshAuth = async () => {
    try {
      const refreshToken = sessionStorage.getItem('refresh_token');
      const storedUser = sessionStorage.getItem('management_user');
      
      if (!refreshToken || !storedUser) {
        // No stored auth, check if we're on a protected route
        if (pathname !== '/login' && !pathname.startsWith('/auth')) {
          await logout();
        }
        return;
      }

      // Attempt to refresh token
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      });

      if (!response.ok) {
        // Refresh failed, redirect to login
        await logout();
        return;
      }

      const refreshResponse = await response.json();
      
      // Update access token
      sessionStorage.setItem('access_token', refreshResponse.access_token);
      
      // Update user data from storage
      setUser(JSON.parse(storedUser));
      
    } catch (error) {
      console.error('Auth refresh failed:', error);
      await logout();
    }
  };

  // Check authentication on mount and route changes
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      
      const storedUser = sessionStorage.getItem('management_user');
      
      if (storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser);
          setUser(parsedUser);
          
          // Refresh auth in background
          await refreshAuth();
        } catch (error) {
          console.error('Failed to parse stored auth:', error);
          await logout();
        }
      } else if (pathname !== '/login' && !pathname.startsWith('/auth')) {
        // Redirect to login if not authenticated and not on auth pages
        router.push('/login');
      }
      
      setIsLoading(false);
    };

    checkAuth();
  }, [pathname, router]);

  const value: ManagementAuthContextValue = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    refreshAuth,
    hasPermission,
    canManageResellers,
    canApproveCommissions,
    canViewAnalytics,
  };

  return (
    <ManagementAuthContext.Provider value={value}>
      {children}
    </ManagementAuthContext.Provider>
  );
}