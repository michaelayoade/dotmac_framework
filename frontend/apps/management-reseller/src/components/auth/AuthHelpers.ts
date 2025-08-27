import { authService } from '@/lib/auth/real-auth-service';
import { tokenManager } from '@/lib/auth/token-manager';
import type { ManagementUser } from './AuthTypes';
import { 
  mapRoleToManagementRole, 
  mapRoleToPermissions, 
  mapRoleToDepartments 
} from './AuthTypes';

// Convert API user to ManagementUser
export function convertToManagementUser(apiUser: any): ManagementUser {
  return {
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
}

// Session storage helpers
export const authStorage = {
  setUser: (user: ManagementUser) => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.setItem('management_user', JSON.stringify(user));
    }
  },
  
  getUser: (): ManagementUser | null => {
    if (typeof window === 'undefined' || !window.sessionStorage) return null;
    
    const stored = window.sessionStorage.getItem('management_user');
    if (!stored) return null;
    
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  },
  
  clearUser: () => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.removeItem('management_user');
    }
  },
  
  setRedirectUrl: (url: string) => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.setItem('auth_redirect_url', url);
    }
  },
  
  getRedirectUrl: (): string | null => {
    if (typeof window === 'undefined' || !window.sessionStorage) return null;
    return window.sessionStorage.getItem('auth_redirect_url');
  },
  
  clearRedirectUrl: () => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.removeItem('auth_redirect_url');
    }
  }
};

// Permission helpers
export function hasPermission(user: ManagementUser | null, permission: string): boolean {
  return user?.permissions.includes(permission) || user?.role === 'MASTER_ADMIN' || false;
}

export function canManageResellers(user: ManagementUser | null): boolean {
  return hasPermission(user, 'MANAGE_RESELLERS') || user?.role === 'CHANNEL_MANAGER';
}

export function canApproveCommissions(user: ManagementUser | null): boolean {
  return hasPermission(user, 'APPROVE_COMMISSIONS') || user?.role === 'CHANNEL_MANAGER';
}

export function canViewAnalytics(user: ManagementUser | null): boolean {
  return hasPermission(user, 'VIEW_ANALYTICS');
}

// Auth operations
export async function performLogin(
  credentials: { email: string; password: string; rememberMe?: boolean }
): Promise<ManagementUser> {
  const loginResult = await authService.login({
    email: credentials.email,
    password: credentials.password,
    rememberMe: credentials.rememberMe
  });
  
  const managementUser = convertToManagementUser(loginResult.user);
  sessionStorage.setUser(managementUser);
  
  return managementUser;
}

export async function performLogout(): Promise<void> {
  try {
    await authService.logout();
  } catch (error) {
    console.error('Logout failed:', error);
  } finally {
    // Force cleanup even if server call fails
    await tokenManager.clearTokens();
    sessionStorage.clearUser();
    sessionStorage.clearRedirectUrl();
  }
}

export async function refreshAuthState(): Promise<ManagementUser | null> {
  try {
    const currentUser = await authService.getCurrentUser();
    if (!currentUser) return null;
    
    const managementUser = convertToManagementUser(currentUser);
    sessionStorage.setUser(managementUser);
    
    return managementUser;
  } catch (error) {
    console.error('Auth refresh failed:', error);
    throw error;
  }
}

export async function validateAuthState(): Promise<boolean> {
  try {
    return await authService.validateAuth();
  } catch (error) {
    console.error('Auth validation failed:', error);
    return false;
  }
}