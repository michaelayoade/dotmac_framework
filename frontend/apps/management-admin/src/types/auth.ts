export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  permissions: Permission[];
  tenantId?: string;
  isActive: boolean;
  lastLogin?: string;
  createdAt: string;
  updatedAt: string;
}

export enum UserRole {
  MASTER_ADMIN = 'master_admin',
  TENANT_ADMIN = 'tenant_admin',
  RESELLER = 'reseller',
  USER = 'user',
}

export enum Permission {
  // Tenant Management
  CREATE_TENANT = 'create_tenant',
  UPDATE_TENANT = 'update_tenant',
  DELETE_TENANT = 'delete_tenant',
  VIEW_TENANT = 'view_tenant',
  MANAGE_TENANT_USERS = 'manage_tenant_users',

  // User Management
  CREATE_USER = 'create_user',
  UPDATE_USER = 'update_user',
  DELETE_USER = 'delete_user',
  VIEW_USER = 'view_user',
  MANAGE_USERS = 'manage_users',

  // Billing
  VIEW_BILLING = 'view_billing',
  MANAGE_BILLING = 'manage_billing',
  MANAGE_ALL_BILLING = 'manage_all_billing',
  CREATE_SUBSCRIPTION = 'create_subscription',
  CANCEL_SUBSCRIPTION = 'cancel_subscription',

  // Infrastructure
  VIEW_INFRASTRUCTURE = 'view_infrastructure',
  MANAGE_INFRASTRUCTURE = 'manage_infrastructure',
  DEPLOY_SERVICES = 'deploy_services',
  SCALE_SERVICES = 'scale_services',

  // Plugins
  VIEW_PLUGINS = 'view_plugins',
  INSTALL_PLUGINS = 'install_plugins',
  MANAGE_PLUGINS = 'manage_plugins',
  REVIEW_PLUGINS = 'review_plugins',

  // Monitoring
  VIEW_MONITORING = 'view_monitoring',
  MANAGE_MONITORING = 'manage_monitoring',

  // System
  SYSTEM_ADMIN = 'system_admin',
  VIEW_ANALYTICS = 'view_analytics',
}

export interface LoginCredentials {
  email: string;
  username?: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  hasPermission: (permission: Permission | Permission[]) => boolean;
  isMasterAdmin: () => boolean;
}

export interface JWTPayload {
  sub: string; // user id
  email: string;
  role: UserRole;
  permissions: Permission[];
  tenant_id?: string;
  exp: number;
  iat: number;
}