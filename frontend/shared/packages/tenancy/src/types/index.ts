export interface TenantConfig {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  status: 'active' | 'suspended' | 'pending' | 'terminated';
  tier: 'basic' | 'professional' | 'enterprise';
  features: string[];
  settings: Record<string, any>;
  branding?: TenantBranding;
  limits: ResourceLimits;
  metadata: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

export interface TenantBranding {
  logo?: string;
  favicon?: string;
  primaryColor: string;
  secondaryColor: string;
  companyName: string;
  customCss?: string;
}

export interface ResourceLimits {
  users: number;
  storage: number; // in bytes
  bandwidth: number; // in bytes per month
  apiCalls: number; // per month
  customDomains: number;
  projects: number;
}

export interface TenantProvisioningRequest {
  name: string;
  slug: string;
  domain?: string;
  tier: 'basic' | 'professional' | 'enterprise';
  adminUser: {
    email: string;
    firstName: string;
    lastName: string;
    phone?: string;
  };
  branding?: Partial<TenantBranding>;
  features?: string[];
  customLimits?: Partial<ResourceLimits>;
  metadata?: Record<string, any>;
}

export interface TenantProvisioningStatus {
  requestId: string;
  tenantId?: string;
  status: 'pending' | 'provisioning' | 'completed' | 'failed';
  progress: number; // 0-100
  currentStep: string;
  steps: ProvisioningStep[];
  error?: string;
  estimatedCompletion?: Date;
}

export interface ProvisioningStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped';
  startTime?: Date;
  endTime?: Date;
  error?: string;
}

export interface ResourceAllocation {
  tenantId: string;
  resourceType: 'compute' | 'storage' | 'network' | 'database' | 'cache';
  allocated: number;
  used: number;
  limit: number;
  unit: string;
  lastUpdated: Date;
}

export interface TenantUsage {
  tenantId: string;
  period: {
    start: Date;
    end: Date;
  };
  metrics: {
    users: {
      active: number;
      total: number;
    };
    storage: {
      used: number;
      quota: number;
      unit: 'bytes';
    };
    bandwidth: {
      used: number;
      quota: number;
      unit: 'bytes';
    };
    apiCalls: {
      count: number;
      quota: number;
    };
    uptime: {
      percentage: number;
      incidents: number;
    };
  };
  billing: {
    amount: number;
    currency: string;
    breakdown: Record<string, number>;
  };
}

export interface TenantManagementAction {
  type: 'provision' | 'suspend' | 'resume' | 'terminate' | 'upgrade' | 'downgrade' | 'migrate';
  tenantId: string;
  parameters?: Record<string, any>;
  scheduledFor?: Date;
  executedAt?: Date;
  status: 'scheduled' | 'executing' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export interface TenantEvent {
  id: string;
  tenantId: string;
  type:
    | 'created'
    | 'suspended'
    | 'resumed'
    | 'terminated'
    | 'upgraded'
    | 'downgraded'
    | 'settings_changed'
    | 'limit_exceeded';
  data: Record<string, any>;
  triggeredBy: string; // user ID
  timestamp: Date;
  severity: 'info' | 'warning' | 'error' | 'critical';
}

// Management portal specific types
export interface TenantPortalConfig {
  tenantId: string;
  portalSettings: {
    allowSelfService: boolean;
    features: {
      billing: boolean;
      userManagement: boolean;
      analytics: boolean;
      support: boolean;
      customization: boolean;
    };
    customization: {
      theme: 'light' | 'dark' | 'auto';
      layout: 'sidebar' | 'top-nav' | 'compact';
      branding: TenantBranding;
    };
  };
  accessControl: {
    adminUsers: string[];
    permissions: Record<string, string[]>;
  };
}

export interface TenantServiceHealth {
  tenantId: string;
  services: {
    [serviceName: string]: {
      status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
      lastCheck: Date;
      responseTime?: number;
      error?: string;
      dependencies: string[];
    };
  };
  overall: 'healthy' | 'degraded' | 'unhealthy';
}

// Hooks and context types
export interface TenancyContextValue {
  currentTenant: TenantConfig | null;
  provisioning: TenantProvisioningStatus | null;
  usage: TenantUsage | null;
  health: TenantServiceHealth | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  provisionTenant: (request: TenantProvisioningRequest) => Promise<string>;
  getTenant: (tenantId: string) => Promise<TenantConfig>;
  updateTenant: (tenantId: string, updates: Partial<TenantConfig>) => Promise<TenantConfig>;
  switchTenant: (tenantId: string) => Promise<void>;
  suspendTenant: (tenantId: string, reason?: string) => Promise<void>;
  resumeTenant: (tenantId: string) => Promise<void>;
  terminateTenant: (tenantId: string) => Promise<void>;

  // Resource management
  getResourceAllocation: (tenantId: string) => Promise<ResourceAllocation[]>;
  updateResourceLimits: (tenantId: string, limits: Partial<ResourceLimits>) => Promise<void>;
  getUsageMetrics: (tenantId: string, period?: { start: Date; end: Date }) => Promise<TenantUsage>;

  // Portal management
  getPortalConfig: (tenantId: string) => Promise<TenantPortalConfig>;
  updatePortalConfig: (tenantId: string, config: Partial<TenantPortalConfig>) => Promise<void>;

  // Health monitoring
  getServiceHealth: (tenantId: string) => Promise<TenantServiceHealth>;

  // Events and audit
  getTenantEvents: (tenantId: string, filter?: Partial<TenantEvent>) => Promise<TenantEvent[]>;
}

// API Response types
export interface TenantListResponse {
  tenants: TenantConfig[];
  pagination: {
    page: number;
    size: number;
    total: number;
    totalPages: number;
  };
}

export interface ProvisioningResponse {
  requestId: string;
  status: TenantProvisioningStatus;
}

export type TenantStatus = TenantConfig['status'];
export type TenantTier = TenantConfig['tier'];
export type ProvisioningStatusType = TenantProvisioningStatus['status'];
export type ResourceType = ResourceAllocation['resourceType'];
export type TenantEventType = TenantEvent['type'];
export type ActionType = TenantManagementAction['type'];
