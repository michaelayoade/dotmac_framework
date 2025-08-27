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

export interface ManagementAuthContextValue {
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

// Helper functions for role mapping
export const mapRoleToManagementRole = (apiRole: string): 'MASTER_ADMIN' | 'CHANNEL_MANAGER' | 'OPERATIONS_MANAGER' => {
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

export const mapRoleToPermissions = (apiRole: string): string[] => {
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

export const mapRoleToDepartments = (apiRole: string): string[] => {
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