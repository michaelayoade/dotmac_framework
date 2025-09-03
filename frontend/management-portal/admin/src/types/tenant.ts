export interface Tenant {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  status: TenantStatus;
  plan?: string;
  billingEmail?: string;
  contactEmail?: string;
  contactPhone?: string;
  description?: string;
  settings: TenantSettings;
  metadata: Record<string, any>;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  lastActivity?: string;
}

export enum TenantStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  TERMINATED = 'terminated',
  PENDING = 'pending',
}

export interface TenantSettings {
  allowUserRegistration: boolean;
  maxUsers: number;
  features: string[];
  customization: {
    logo?: string;
    primaryColor?: string;
    theme?: string;
  };
  limits: {
    storage: number;
    bandwidth: number;
    apiCalls: number;
  };
  integrations: Record<string, any>;
}

export interface CreateTenantRequest {
  name: string;
  slug: string;
  domain?: string;
  billingEmail: string;
  contactEmail: string;
  contactPhone?: string;
  description?: string;
  planId?: string;
  settings?: Partial<TenantSettings>;
  metadata?: Record<string, any>;
}

export interface UpdateTenantRequest {
  name?: string;
  slug?: string;
  domain?: string;
  billingEmail?: string;
  contactEmail?: string;
  contactPhone?: string;
  description?: string;
  settings?: Partial<TenantSettings>;
  metadata?: Record<string, any>;
}

export interface TenantListResponse {
  tenants: Tenant[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface TenantUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  lastLogin?: string;
  createdAt: string;
}

export interface TenantStats {
  totalUsers: number;
  activeUsers: number;
  storage: {
    used: number;
    limit: number;
  };
  bandwidth: {
    used: number;
    limit: number;
  };
  apiCalls: {
    used: number;
    limit: number;
  };
  lastActivity?: string;
}
