'use client';

import { AuthProvider } from '@dotmac/auth';
import { ReactNode } from 'react';

// Role mapping configuration for management portal
const managementRoleMapping = {
  // Map API roles to management roles
  roleMap: {
    master_admin: 'MASTER_ADMIN',
    platform_admin: 'MASTER_ADMIN',
    channel_manager: 'CHANNEL_MANAGER',
    reseller_manager: 'CHANNEL_MANAGER',
    operations_manager: 'OPERATIONS_MANAGER',
    tenant_admin: 'OPERATIONS_MANAGER',
  },

  // Permission mapping based on roles
  permissionMap: {
    MASTER_ADMIN: [
      'VIEW_DASHBOARD',
      'VIEW_PROFILE',
      'MANAGE_RESELLERS',
      'APPROVE_COMMISSIONS',
      'VIEW_ANALYTICS',
      'MANAGE_TERRITORIES',
      'PROCESS_PAYOUTS',
      'MANAGE_TRAINING',
      'SYSTEM_ADMIN',
      'USER_MANAGEMENT',
      'PLATFORM_SETTINGS',
    ],
    CHANNEL_MANAGER: [
      'VIEW_DASHBOARD',
      'VIEW_PROFILE',
      'MANAGE_RESELLERS',
      'APPROVE_COMMISSIONS',
      'VIEW_ANALYTICS',
      'MANAGE_TERRITORIES',
      'PROCESS_PAYOUTS',
      'MANAGE_TRAINING',
    ],
    OPERATIONS_MANAGER: [
      'VIEW_DASHBOARD',
      'VIEW_PROFILE',
      'VIEW_ANALYTICS',
      'MANAGE_TERRITORIES',
      'VIEW_COMMISSIONS',
    ],
  },

  // Department mapping
  departmentMap: {
    MASTER_ADMIN: ['Platform Administration', 'System Operations'],
    CHANNEL_MANAGER: ['Channel Operations', 'Partner Management'],
    OPERATIONS_MANAGER: ['Operations', 'Customer Success'],
  },
};

interface IntegratedAuthProviderProps {
  children: ReactNode;
}

export function IntegratedAuthProvider({ children }: IntegratedAuthProviderProps) {
  return (
    <AuthProvider
      variant='enterprise'
      portal='management'
      config={{
        // Role and permission mapping
        roleMapping: managementRoleMapping,

        // Session management
        sessionTimeout: 30 * 60 * 1000, // 30 minutes
        refreshTokenExpiry: 7 * 24 * 60 * 60 * 1000, // 7 days

        // Security settings
        enableMFA: false, // Can be enabled based on role
        requirePasswordChange: false,
        enableSessionInactivityTimeout: true,

        // Redirect configuration
        loginRedirectPath: '/dashboard',
        logoutRedirectPath: '/login',
        unauthorizedRedirectPath: '/login',

        // Features
        enableProfileManagement: true,
        enablePasswordChange: true,
        enableNotifications: true,

        // API configuration
        baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
        endpoints: {
          login: '/auth/management/login',
          logout: '/auth/management/logout',
          refresh: '/auth/management/refresh',
          profile: '/auth/management/profile',
          changePassword: '/auth/management/change-password',
        },

        // Storage preferences
        persistAuth: true,
        storageType: 'sessionStorage', // Use sessionStorage for management portal

        // Error handling
        enableErrorReporting: true,
        retryFailedRequests: 3,

        // Development settings
        enableDevTools: process.env.NODE_ENV === 'development',
      }}
    >
      {children}
    </AuthProvider>
  );
}
