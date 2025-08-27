'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { tokenManager } from '@/lib/auth/token-manager';
import { authService } from '@/lib/auth/real-auth-service';
import { useAuthActions } from '@/store';
import { useNotifications } from '@/hooks/useNotifications';

export interface ManagementUser {
  id: string;
  email: string;
  name: string;
  role: 'MASTER_ADMIN' | 'CHANNEL_MANAGER' | 'OPERATIONS_MANAGER';
  permissions: string[];
  departments: string[];
  last_login?: Date;
  created_at: string;
  updated_at: string;
}

interface ManagementAuthContextValue {
  user: ManagementUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  authError: string | null;
  login: (credentials: { email: string; password: string; rememberMe?: boolean }) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  validateAuth: () => Promise<boolean>;
  hasPermission: (permission: string) => boolean;
  canManageResellers: () => boolean;
  canApproveCommissions: () => boolean;
  canViewAnalytics: () => boolean;
  updateProfile: (updates: Partial<ManagementUser>) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
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
  const [authError, setAuthError] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();
  const { setUser: setStoreUser, clearAuth, updateLastActivity } = useAuthActions();
  const { addNotification } = useNotifications();

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

  // Authentication implementation with real auth service
  const login = async (credentials: { email: string; password: string; rememberMe?: boolean }) => {
    setIsLoading(true);
    setAuthError(null);
    
    try {
      // Use real auth service for login
      const loginResult = await authService.login({
        email: credentials.email,
        password: credentials.password,
        rememberMe: credentials.rememberMe
      });
      
      // Extract user data and map to ManagementUser interface
      const apiUser = loginResult.user;
      const managementUser: ManagementUser = {
        id: apiUser.id,
        email: apiUser.email,
        name: apiUser.name,
        role: mapRoleToManagementRole(apiUser.role),
        permissions: mapRoleToPermissions(apiUser.role),
        departments: mapRoleToDepartments(apiUser.role),
        last_login: apiUser.last_login ? new Date(apiUser.last_login) : new Date(),
        created_at: apiUser.created_at,
        updated_at: apiUser.updated_at,
      };

      // Store user data in sessionStorage for quick access
      sessionStorage.setItem('management_user', JSON.stringify(managementUser));
      
      setUser(managementUser);
      setStoreUser(managementUser);
      updateLastActivity();
      
      // Show success notification
      addNotification({
        type: 'success',
        title: 'Welcome back!',
        message: `Successfully logged in as ${managementUser.name}`,
        duration: 3000,
      });
      
      // Redirect to intended page or dashboard
      const redirectUrl = sessionStorage.getItem('auth_redirect_url') || '/dashboard';
      sessionStorage.removeItem('auth_redirect_url');
      router.push(redirectUrl);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      setAuthError(errorMessage);
      
      addNotification({
        type: 'error',
        title: 'Login Failed',
        message: errorMessage,
        duration: 5000,
      });
      
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    
    try {
      // Use real auth service for logout
      await authService.logout();
      
      // Clear local state
      setUser(null);
      setStoreUser(null);
      setAuthError(null);
      clearAuth();
      
      // Show logout notification
      addNotification({
        type: 'info',
        title: 'Logged out',
        message: 'You have been successfully logged out',
        duration: 3000,
      });
      
      // Redirect to login
      router.push('/login');
      
    } catch (error) {
      console.error('Logout failed:', error);
      
      // Force logout even if server call fails
      setUser(null);
      setStoreUser(null);
      setAuthError(null);
      clearAuth();
      
      await tokenManager.clearTokens();
      sessionStorage.removeItem('management_user');
      
      router.push('/login');
    } finally {
      setIsLoading(false);
    }
  };

  const refreshAuth = async () => {
    try {
      // Get current user from server
      const currentUser = await authService.getCurrentUser();
      
      if (!currentUser) {
        // No user found, check if we're on a protected route
        if (pathname && pathname !== '/login' && !pathname.startsWith('/auth') && !pathname.startsWith('/reset-password')) {
          // Store current URL for redirect after login
          sessionStorage.setItem('auth_redirect_url', pathname);
          await logout();
        }
        return;
      }
      
      // Map API user to management user
      const managementUser: ManagementUser = {
        id: currentUser.id,
        email: currentUser.email,
        name: currentUser.name,
        role: mapRoleToManagementRole(currentUser.role),
        permissions: mapRoleToPermissions(currentUser.role),
        departments: mapRoleToDepartments(currentUser.role),
        last_login: currentUser.last_login ? new Date(currentUser.last_login) : new Date(),
        created_at: currentUser.created_at,
        updated_at: currentUser.updated_at,
      };
      
      // Update user data
      sessionStorage.setItem('management_user', JSON.stringify(managementUser));
      setUser(managementUser);
      setStoreUser(managementUser);
      updateLastActivity();
      
    } catch (error) {
      console.error('Auth refresh failed:', error);
      setAuthError('Session expired');
      
      // Don't auto-logout on every error - only on auth errors
      if (error instanceof Error && error.message.includes('Session expired')) {
        if (pathname && pathname !== '/login') {
          sessionStorage.setItem('auth_redirect_url', pathname);
        }
        await logout();
      }
    }
  };
  
  // Validate current authentication state
  const validateAuth = async (): Promise<boolean> => {
    try {
      return await authService.validateAuth();
    } catch (error) {
      console.error('Auth validation failed:', error);
      return false;
    }
  };
  
  // Update user profile
  const updateProfile = async (updates: Partial<ManagementUser>): Promise<void> => {
    try {
      const updatedUser = await authService.updateProfile(updates);
      
      const managementUser: ManagementUser = {
        ...user!,
        ...updates,
        updated_at: updatedUser.updated_at,
      };
      
      setUser(managementUser);
      setStoreUser(managementUser);
      sessionStorage.setItem('management_user', JSON.stringify(managementUser));
      
      addNotification({
        type: 'success',
        title: 'Profile Updated',
        message: 'Your profile has been successfully updated',
        duration: 3000,
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update profile';
      addNotification({
        type: 'error',
        title: 'Update Failed',
        message: errorMessage,
        duration: 5000,
      });
      throw error;
    }
  };
  
  // Change password
  const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    try {
      await authService.changePassword(currentPassword, newPassword);
      
      addNotification({
        type: 'success',
        title: 'Password Changed',
        message: 'Your password has been successfully updated',
        duration: 3000,
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to change password';
      addNotification({
        type: 'error',
        title: 'Password Change Failed',
        message: errorMessage,
        duration: 5000,
      });
      throw error;
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
          setStoreUser(parsedUser);
          
          // Refresh auth in background
          await refreshAuth();
        } catch (error) {
          console.error('Failed to parse stored auth:', error);
          await logout();
        }
      } else if (pathname && pathname !== '/login' && !pathname.startsWith('/auth')) {
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
    authError,
    login,
    logout,
    refreshAuth,
    validateAuth,
    hasPermission,
    canManageResellers,
    canApproveCommissions,
    canViewAnalytics,
    updateProfile,
    changePassword,
  };

  return (
    <ManagementAuthContext.Provider value={value}>
      {children}
    </ManagementAuthContext.Provider>
  );
}