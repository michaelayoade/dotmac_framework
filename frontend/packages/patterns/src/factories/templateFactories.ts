/**
 * Template Factories
 * Factory functions for creating portal-specific templates with TypeScript contracts
 */

import React from 'react';
import { 
  ManagementPageConfig, 
  DashboardConfig, 
  WorkflowConfig,
  MetricConfig,
  FilterConfig,
  ActionConfig,
  ChartConfig,
  WorkflowStepConfig,
  validateTemplateConfig,
  ManagementPageConfigSchema,
  DashboardConfigSchema,
  WorkflowConfigSchema
} from '../types/templates';
import { ManagementPageTemplate } from '../templates/ManagementPageTemplate';
import { DashboardTemplate } from '../templates/DashboardTemplate';
import { WorkflowTemplate } from '../templates/WorkflowTemplate';

// Portal-specific type definitions
export type PortalType = 'admin' | 'customer' | 'reseller' | 'technician' | 'management';

export interface PortalTheme {
  primary: string;
  secondary: string;
  accent: string;
  density: 'compact' | 'comfortable' | 'spacious';
  borderRadius: 'none' | 'sm' | 'md' | 'lg';
  spacing: 'tight' | 'normal' | 'loose';
}

export interface TemplateFactoryOptions {
  portal: PortalType;
  theme?: Partial<PortalTheme>;
  className?: string;
  permissions?: Record<string, boolean>;
  apiBaseUrl?: string;
  enableAnalytics?: boolean;
  enableAccessibility?: boolean;
}

// Default portal themes
export const PORTAL_THEMES: Record<PortalType, PortalTheme> = {
  admin: {
    primary: '#1f2937',
    secondary: '#374151',
    accent: '#3b82f6',
    density: 'compact',
    borderRadius: 'md',
    spacing: 'tight'
  },
  customer: {
    primary: '#059669',
    secondary: '#047857',
    accent: '#10b981',
    density: 'comfortable',
    borderRadius: 'lg',
    spacing: 'normal'
  },
  reseller: {
    primary: '#7c3aed',
    secondary: '#6d28d9',
    accent: '#8b5cf6',
    density: 'comfortable',
    borderRadius: 'md',
    spacing: 'normal'
  },
  technician: {
    primary: '#dc2626',
    secondary: '#b91c1c',
    accent: '#ef4444',
    density: 'spacious',
    borderRadius: 'lg',
    spacing: 'loose'
  },
  management: {
    primary: '#0f172a',
    secondary: '#1e293b',
    accent: '#0ea5e9',
    density: 'compact',
    borderRadius: 'sm',
    spacing: 'tight'
  }
};

// Management Page Factory
export interface CreateManagementPageOptions extends TemplateFactoryOptions {
  title: string;
  description?: string;
  metrics?: MetricConfig[];
  filters?: FilterConfig[];
  actions?: ActionConfig[];
  showExport?: boolean;
  showSearch?: boolean;
  enableBulkActions?: boolean;
  refreshInterval?: number;
  dataEndpoint: string;
  onDataLoad?: (filters: Record<string, any>, sorting: any, pagination: any) => Promise<any>;
  onAction?: (action: string, data?: any) => Promise<void>;
  onExport?: (format: 'csv' | 'excel' | 'json', data: any) => Promise<void>;
}

export function createManagementPage(options: CreateManagementPageOptions) {
  const theme = { ...PORTAL_THEMES[options.portal], ...options.theme };
  
  const config: ManagementPageConfig = {
    type: 'management' as const,
    title: options.title,
    description: options.description,
    portal: options.portal,
    metrics: options.metrics || [],
    filters: options.filters || [],
    actions: options.actions || [],
    showBreadcrumbs: true,
    showHeader: true,
    showSidebar: false,
    maxWidth: 'none',
    padding: true,
    theme: 'auto',
    density: theme.density,
    showMetrics: (options.metrics?.length || 0) > 0,
    showFilters: (options.filters?.length || 0) > 0,
    showActions: (options.actions?.length || 0) > 0,
    showExport: options.showExport ?? true,
    showSearch: options.showSearch ?? true,
    showSavedViews: true,
    enableBulkActions: options.enableBulkActions ?? false,
    enableColumnConfig: true,
    refreshInterval: options.refreshInterval,
    autoRefresh: !!options.refreshInterval,
    savedViews: []
  };

  // Validate configuration
  const validation = validateTemplateConfig(ManagementPageConfigSchema, config);
  if (!validation.isValid) {
    throw new Error(`Invalid management page configuration: ${validation.errors?.join(', ')}`);
  }

  const validatedConfig = validation.data!;

  // Return React component factory
  return {
    config: validatedConfig,
    theme,
    component: (props: Partial<React.ComponentProps<typeof ManagementPageTemplate>> = {}) => 
      React.createElement(ManagementPageTemplate, {
        config: validatedConfig,
        className: `portal-${options.portal} ${options.className || ''}`,
        onDataLoad: options.onDataLoad,
        onAction: options.onAction,
        onExport: options.onExport,
        ...props
      }),
    // Helper methods
    addMetric: (metric: MetricConfig) => {
      validatedConfig.metrics.push(metric);
      return { config: validatedConfig, theme };
    },
    addFilter: (filter: FilterConfig) => {
      validatedConfig.filters.push(filter);
      return { config: validatedConfig, theme };
    },
    addAction: (action: ActionConfig) => {
      validatedConfig.actions.push(action);
      return { config: validatedConfig, theme };
    }
  };
}

// Dashboard Factory
export interface CreateDashboardPageOptions extends TemplateFactoryOptions {
  title: string;
  subtitle?: string;
  metrics?: MetricConfig[];
  charts?: ChartConfig[];
  layout?: {
    columns?: number;
    gap?: number;
  };
  refreshInterval?: number;
  showDatePicker?: boolean;
  timeRanges?: Array<{ label: string; value: string }>;
  filters?: Array<{
    key: string;
    label: string;
    type: 'select' | 'daterange';
    options?: Array<{ label: string; value: string }>;
  }>;
  dataEndpoint: string;
  onDataLoad?: (data: any) => void;
  onExport?: (format: 'csv' | 'excel' | 'json', data: any) => Promise<void>;
}

export function createDashboardPage(options: CreateDashboardPageOptions) {
  const theme = { ...PORTAL_THEMES[options.portal], ...options.theme };
  
  const config: DashboardConfig = {
    type: 'dashboard' as const,
    title: options.title,
    portal: options.portal,
    charts: options.charts || [],
    metrics: options.metrics || [],
    showBreadcrumbs: true,
    showHeader: true,
    showSidebar: false,
    maxWidth: 'none',
    padding: true,
    theme: 'auto',
    density: theme.density,
    layout: {
      columns: options.layout?.columns || 12,
      gap: options.layout?.gap || 4
    },
    widgets: [
      ...(options.metrics || []).map((metric, index) => ({
        id: `metric-${index}`,
        type: 'metric' as const,
        title: metric.title,
        span: { cols: 3, rows: 1 },
        config: metric,
        permissions: []
      })),
      ...(options.charts || []).map((chart, index) => ({
        id: `chart-${index}`,
        type: 'chart' as const,
        title: chart.title || `Chart ${index + 1}`,
        span: { cols: 6, rows: 2 },
        config: chart,
        permissions: []
      }))
    ],
    refreshInterval: options.refreshInterval || 30000,
    autoRefresh: !!options.refreshInterval,
    showRefreshButton: true,
    showDatePicker: options.showDatePicker ?? false,
    dateRange: options.showDatePicker ? {
      preset: 'week'
    } : undefined
  };

  // Validate configuration
  const validation = validateTemplateConfig(DashboardConfigSchema, config);
  if (!validation.isValid) {
    throw new Error(`Invalid dashboard configuration: ${validation.errors?.join(', ')}`);
  }

  const validatedConfig = validation.data!;

  // Transform to legacy DashboardTemplate props format
  const legacyConfig = {
    title: validatedConfig.title,
    subtitle: options.subtitle,
    portal: validatedConfig.portal,
    metrics: validatedConfig.metrics,
    sections: validatedConfig.widgets.map(widget => ({
      id: widget.id,
      title: widget.title,
      type: widget.type === 'metric' ? 'metrics' as const : 
            widget.type === 'chart' ? 'chart' as const : 'table' as const,
      size: widget.span.cols >= 12 ? 'full' as const :
            widget.span.cols >= 9 ? 'xl' as const :
            widget.span.cols >= 6 ? 'lg' as const :
            widget.span.cols >= 3 ? 'md' as const : 'sm' as const,
      order: 0,
      config: widget.config,
      permission: widget.permissions[0]
    })),
    refreshInterval: validatedConfig.refreshInterval ? validatedConfig.refreshInterval / 1000 : undefined,
    timeRanges: options.timeRanges || [
      { label: 'Last 24 hours', value: '1d' },
      { label: 'Last 7 days', value: '7d' },
      { label: 'Last 30 days', value: '30d' },
      { label: 'Last 90 days', value: '90d' }
    ],
    filters: options.filters,
    apiEndpoint: `${options.apiBaseUrl || '/api'}/${options.dataEndpoint}`,
    permissions: {
      view: `dashboard:${options.portal}:view`,
      export: options.onExport ? `dashboard:${options.portal}:export` : undefined
    }
  };

  return {
    config: validatedConfig,
    theme,
    component: (props: Partial<React.ComponentProps<typeof DashboardTemplate>> = {}) => 
      React.createElement(DashboardTemplate, {
        config: legacyConfig,
        className: `portal-${options.portal} ${options.className || ''}`,
        ...props
      }),
    // Helper methods
    addMetric: (metric: MetricConfig) => {
      validatedConfig.metrics.push(metric);
      validatedConfig.widgets.push({
        id: `metric-${validatedConfig.widgets.length}`,
        type: 'metric',
        title: metric.title,
        span: { cols: 3, rows: 1 },
        config: metric,
        permissions: []
      });
      return { config: validatedConfig, theme };
    },
    addChart: (chart: ChartConfig) => {
      validatedConfig.charts.push(chart);
      validatedConfig.widgets.push({
        id: `chart-${validatedConfig.widgets.length}`,
        type: 'chart',
        title: chart.title || 'Chart',
        span: { cols: 6, rows: 2 },
        config: chart,
        permissions: []
      });
      return { config: validatedConfig, theme };
    }
  };
}

// Workflow Factory
export interface CreateWorkflowPageOptions extends TemplateFactoryOptions {
  title: string;
  description?: string;
  steps: WorkflowStepConfig[];
  allowStepNavigation?: boolean;
  showProgress?: boolean;
  showStepNumbers?: boolean;
  persistData?: boolean;
  autoSave?: boolean;
  autoSaveInterval?: number;
  onStepChange?: (step: number, data: Record<string, any>) => void;
  onComplete?: (data: Record<string, any>) => Promise<void>;
  onCancel?: () => void;
}

export function createWorkflowPage(options: CreateWorkflowPageOptions) {
  const theme = { ...PORTAL_THEMES[options.portal], ...options.theme };
  
  const config: WorkflowConfig = {
    type: 'workflow' as const,
    title: options.title,
    description: options.description,
    portal: options.portal,
    steps: options.steps,
    showBreadcrumbs: true,
    showHeader: true,
    showSidebar: false,
    maxWidth: '2xl',
    padding: true,
    theme: 'auto',
    density: theme.density,
    allowStepNavigation: options.allowStepNavigation ?? false,
    showProgress: options.showProgress ?? true,
    showStepNumbers: options.showStepNumbers ?? true,
    persistData: options.persistData ?? true,
    autoSave: options.autoSave ?? true,
    autoSaveInterval: options.autoSaveInterval || 30000,
    validation: {
      validateOnChange: true,
      validateOnBlur: true,
      showErrorSummary: true
    },
    onStepChange: options.onStepChange,
    onComplete: options.onComplete,
    onCancel: options.onCancel
  };

  // Validate configuration
  const validation = validateTemplateConfig(WorkflowConfigSchema, config);
  if (!validation.isValid) {
    throw new Error(`Invalid workflow configuration: ${validation.errors?.join(', ')}`);
  }

  const validatedConfig = validation.data!;

  return {
    config: validatedConfig,
    theme,
    component: (props: Partial<React.ComponentProps<typeof WorkflowTemplate>> = {}) => 
      React.createElement(WorkflowTemplate, {
        config: validatedConfig,
        className: `portal-${options.portal} ${options.className || ''}`,
        onStepChange: options.onStepChange,
        onComplete: options.onComplete,
        onCancel: options.onCancel,
        ...props
      }),
    // Helper methods
    addStep: (step: WorkflowStepConfig) => {
      validatedConfig.steps.push(step);
      return { config: validatedConfig, theme };
    },
    insertStep: (index: number, step: WorkflowStepConfig) => {
      validatedConfig.steps.splice(index, 0, step);
      return { config: validatedConfig, theme };
    },
    removeStep: (stepId: string) => {
      validatedConfig.steps = validatedConfig.steps.filter(step => step.id !== stepId);
      return { config: validatedConfig, theme };
    }
  };
}

// Portal-specific preset factories
export const createAdminManagementPage = (options: Omit<CreateManagementPageOptions, 'portal'>) => 
  createManagementPage({ ...options, portal: 'admin' });

export const createCustomerDashboard = (options: Omit<CreateDashboardPageOptions, 'portal'>) => 
  createDashboardPage({ ...options, portal: 'customer' });

export const createResellerDashboard = (options: Omit<CreateDashboardPageOptions, 'portal'>) => 
  createDashboardPage({ ...options, portal: 'reseller' });

export const createTechnicianWorkflow = (options: Omit<CreateWorkflowPageOptions, 'portal'>) => 
  createWorkflowPage({ ...options, portal: 'technician' });

export const createManagementDashboard = (options: Omit<CreateDashboardPageOptions, 'portal'>) => 
  createDashboardPage({ ...options, portal: 'management' });

// Utility functions for common configurations
export const createStandardMetrics = (portal: PortalType): MetricConfig[] => {
  switch (portal) {
    case 'admin':
      return [
        {
          key: 'total-customers',
          title: 'Total Customers',
          value: 0,
          format: 'number',
          icon: 'Users',
          color: '#3b82f6',
          precision: 0,
          size: 'md'
        },
        {
          key: 'active-services',
          title: 'Active Services',
          value: 0,
          format: 'number',
          icon: 'Activity',
          color: '#10b981',
          precision: 0,
          size: 'md'
        },
        {
          key: 'monthly-revenue',
          title: 'Monthly Revenue',
          value: 0,
          format: 'currency',
          icon: 'DollarSign',
          color: '#8b5cf6',
          precision: 0,
          size: 'md'
        },
        {
          key: 'support-tickets',
          title: 'Support Tickets',
          value: 0,
          format: 'number',
          icon: 'HelpCircle',
          color: '#ef4444',
          precision: 0,
          size: 'md'
        }
      ];
    
    case 'customer':
      return [
        {
          key: 'service-status',
          title: 'Service Status',
          value: 'Active',
          format: 'number',
          icon: 'Wifi',
          color: '#10b981',
          precision: 0,
          size: 'md'
        },
        {
          key: 'data-usage',
          title: 'Data Usage',
          value: 0,
          format: 'bytes',
          icon: 'BarChart3',
          color: '#3b82f6',
          precision: 0,
          size: 'md'
        },
        {
          key: 'monthly-bill',
          title: 'Monthly Bill',
          value: 0,
          format: 'currency',
          icon: 'CreditCard',
          color: '#8b5cf6',
          precision: 0,
          size: 'md'
        }
      ];
    
    case 'reseller':
      return [
        {
          key: 'partner-customers',
          title: 'Partner Customers',
          value: 0,
          format: 'number',
          icon: 'Users',
          color: '#7c3aed',
          precision: 0,
          size: 'md'
        },
        {
          key: 'commission-earned',
          title: 'Commission Earned',
          value: 0,
          format: 'currency',
          icon: 'TrendingUp',
          color: '#10b981',
          precision: 0,
          size: 'md'
        },
        {
          key: 'territory-coverage',
          title: 'Territory Coverage',
          value: 0,
          format: 'percentage',
          icon: 'MapPin',
          color: '#3b82f6',
          precision: 0,
          size: 'md'
        }
      ];
    
    case 'technician':
      return [
        {
          key: 'work-orders',
          title: 'Work Orders',
          value: 0,
          format: 'number',
          icon: 'Clipboard',
          color: '#dc2626',
          precision: 0,
          size: 'md'
        },
        {
          key: 'completed-today',
          title: 'Completed Today',
          value: 0,
          format: 'number',
          icon: 'CheckCircle',
          color: '#10b981',
          precision: 0,
          size: 'md'
        },
        {
          key: 'efficiency-rating',
          title: 'Efficiency Rating',
          value: 0,
          format: 'percentage',
          icon: 'Star',
          color: '#f59e0b',
          precision: 0,
          size: 'md'
        }
      ];
    
    case 'management':
      return [
        {
          key: 'total-revenue',
          title: 'Total Revenue',
          value: 0,
          format: 'currency',
          icon: 'DollarSign',
          color: '#0ea5e9',
          precision: 0,
          size: 'md'
        },
        {
          key: 'market-share',
          title: 'Market Share',
          value: 0,
          format: 'percentage',
          icon: 'PieChart',
          color: '#8b5cf6',
          precision: 0,
          size: 'md'
        },
        {
          key: 'operational-efficiency',
          title: 'Operational Efficiency',
          value: 0,
          format: 'percentage',
          icon: 'TrendingUp',
          color: '#10b981',
          precision: 0,
          size: 'md'
        }
      ];
    
    default:
      return [];
  }
};

export const createStandardFilters = (portal: PortalType): FilterConfig[] => {
  const commonFilters: FilterConfig[] = [
    {
      key: 'dateRange',
      label: 'Date Range',
      type: 'dateRange',
      defaultValue: { start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), end: new Date() }
    },
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { value: 'active', label: 'Active', disabled: false },
        { value: 'inactive', label: 'Inactive', disabled: false },
        { value: 'pending', label: 'Pending', disabled: false }
      ]
    }
  ];

  switch (portal) {
    case 'admin':
      return [
        ...commonFilters,
        {
          key: 'customerType',
          label: 'Customer Type',
          type: 'select',
          options: [
            { value: 'residential', label: 'Residential', disabled: false },
            { value: 'business', label: 'Business', disabled: false },
            { value: 'enterprise', label: 'Enterprise', disabled: false }
          ]
        }
      ];
    
    case 'reseller':
      return [
        ...commonFilters,
        {
          key: 'territory',
          label: 'Territory',
          type: 'select',
          options: []
        },
        {
          key: 'commissionTier',
          label: 'Commission Tier',
          type: 'select',
          options: [
            { value: 'bronze', label: 'Bronze', disabled: false },
            { value: 'silver', label: 'Silver', disabled: false },
            { value: 'gold', label: 'Gold', disabled: false },
            { value: 'platinum', label: 'Platinum', disabled: false }
          ]
        }
      ];
    
    case 'technician':
      return [
        ...commonFilters,
        {
          key: 'priority',
          label: 'Priority',
          type: 'select',
          options: [
            { value: 'low', label: 'Low', disabled: false },
            { value: 'medium', label: 'Medium', disabled: false },
            { value: 'high', label: 'High', disabled: false },
            { value: 'urgent', label: 'Urgent', disabled: false }
          ]
        },
        {
          key: 'workOrderType',
          label: 'Work Order Type',
          type: 'select',
          options: [
            { value: 'installation', label: 'Installation', disabled: false },
            { value: 'maintenance', label: 'Maintenance', disabled: false },
            { value: 'repair', label: 'Repair', disabled: false },
            { value: 'upgrade', label: 'Upgrade', disabled: false }
          ]
        }
      ];
    
    default:
      return commonFilters;
  }
};

// Factory functions are already exported above
