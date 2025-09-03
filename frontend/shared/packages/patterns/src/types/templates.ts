/**
 * Template Configuration Types
 *
 * TypeScript interfaces and Zod schemas for runtime validation
 * of template configurations across all portal types
 */

import { z } from 'zod';

// Base template configuration
export const BaseTemplateConfigSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  showBreadcrumbs: z.boolean().default(true),
  showHeader: z.boolean().default(true),
  showSidebar: z.boolean().default(false),
  maxWidth: z.enum(['sm', 'md', 'lg', 'xl', '2xl', 'full', 'none']).default('none'),
  padding: z.boolean().default(true),
  theme: z.enum(['light', 'dark', 'auto']).default('auto'),
  density: z.enum(['compact', 'comfortable', 'spacious']).default('comfortable'),
  portal: z.enum(['admin', 'customer', 'reseller', 'technician', 'management']).optional(),
});

export type BaseTemplateConfig = z.infer<typeof BaseTemplateConfigSchema>;

// Action configuration
export const ActionConfigSchema = z.object({
  key: z.string(),
  label: z.string(),
  variant: z.enum(['primary', 'secondary', 'outline', 'ghost', 'destructive']).default('primary'),
  icon: z.string().optional(),
  disabled: z.boolean().default(false),
  loading: z.boolean().default(false),
  permissions: z.array(z.string()).default([]),
  onClick: z
    .function()
    .args(z.any())
    .returns(z.void().or(z.promise(z.void())))
    .optional(),
});

export type ActionConfig = z.infer<typeof ActionConfigSchema>;

// Filter configuration
export const FilterConfigSchema = z.object({
  key: z.string(),
  label: z.string(),
  type: z.enum(['text', 'select', 'date', 'dateRange', 'number', 'boolean', 'multiselect']),
  options: z
    .array(
      z.object({
        value: z.string(),
        label: z.string(),
        disabled: z.boolean().default(false),
      })
    )
    .optional(),
  placeholder: z.string().optional(),
  defaultValue: z.any().optional(),
  validation: z
    .object({
      required: z.boolean().default(false),
      min: z.number().optional(),
      max: z.number().optional(),
      pattern: z.string().optional(),
    })
    .optional(),
});

export type FilterConfig = z.infer<typeof FilterConfigSchema>;

// Saved view configuration
export const SavedViewConfigSchema = z.object({
  id: z.string(),
  name: z.string(),
  filters: z.record(z.any()),
  sorting: z
    .object({
      field: z.string(),
      direction: z.enum(['asc', 'desc']),
    })
    .optional(),
  columns: z.array(z.string()).optional(),
  isDefault: z.boolean().default(false),
  isPublic: z.boolean().default(false),
  createdBy: z.string().optional(),
  createdAt: z.date().optional(),
});

export type SavedViewConfig = z.infer<typeof SavedViewConfigSchema>;

// Chart configuration
export const ChartConfigSchema = z.object({
  type: z.enum(['line', 'bar', 'area', 'pie', 'doughnut', 'metric', 'sparkline']),
  title: z.string().optional(),
  data: z.array(
    z.object({
      label: z.string(),
      value: z.number(),
      color: z.string().optional(),
    })
  ),
  options: z.record(z.any()).default({}),
  height: z.number().default(300),
  responsive: z.boolean().default(true),
  showLegend: z.boolean().default(true),
  showTooltip: z.boolean().default(true),
});

export type ChartConfig = z.infer<typeof ChartConfigSchema>;

// Metric configuration
export const MetricConfigSchema = z.object({
  key: z.string(),
  title: z.string(),
  value: z.union([z.string(), z.number()]),
  change: z
    .object({
      value: z.number(),
      type: z.enum(['increase', 'decrease', 'neutral']),
      period: z.string().optional(),
    })
    .optional(),
  format: z.enum(['number', 'currency', 'percentage', 'bytes', 'duration']).default('number'),
  precision: z.number().default(0),
  icon: z.string().optional(),
  color: z.string().optional(),
  size: z.enum(['sm', 'md', 'lg']).default('md'),
});

export type MetricConfig = z.infer<typeof MetricConfigSchema>;

// Management Page Template Configuration
export const ManagementPageConfigSchema = BaseTemplateConfigSchema.extend({
  type: z.literal('management'),
  metrics: z.array(MetricConfigSchema).default([]),
  filters: z.array(FilterConfigSchema).default([]),
  actions: z.array(ActionConfigSchema).default([]),
  savedViews: z.array(SavedViewConfigSchema).default([]),
  showMetrics: z.boolean().default(true),
  showFilters: z.boolean().default(true),
  showActions: z.boolean().default(true),
  showExport: z.boolean().default(true),
  showSearch: z.boolean().default(true),
  showSavedViews: z.boolean().default(true),
  enableBulkActions: z.boolean().default(false),
  enableColumnConfig: z.boolean().default(true),
  refreshInterval: z.number().optional(),
  autoRefresh: z.boolean().default(false),
});

export type ManagementPageConfig = z.infer<typeof ManagementPageConfigSchema>;

// Dashboard Template Configuration
export const DashboardConfigSchema = BaseTemplateConfigSchema.extend({
  type: z.literal('dashboard'),
  charts: z.array(ChartConfigSchema).default([]),
  metrics: z.array(MetricConfigSchema).default([]),
  layout: z
    .object({
      columns: z.number().min(1).max(12).default(12),
      gap: z.number().default(4),
      responsive: z
        .object({
          sm: z.number().min(1).max(12).optional(),
          md: z.number().min(1).max(12).optional(),
          lg: z.number().min(1).max(12).optional(),
          xl: z.number().min(1).max(12).optional(),
        })
        .optional(),
    })
    .default({ columns: 12, gap: 4 }),
  widgets: z
    .array(
      z.object({
        id: z.string(),
        type: z.enum(['metric', 'chart', 'table', 'list', 'custom']),
        title: z.string(),
        span: z
          .object({
            cols: z.number().min(1).max(12).default(1),
            rows: z.number().min(1).default(1),
          })
          .default({ cols: 1, rows: 1 }),
        config: z.record(z.any()).default({}),
        permissions: z.array(z.string()).default([]),
      })
    )
    .default([]),
  refreshInterval: z.number().default(30000),
  autoRefresh: z.boolean().default(true),
  showRefreshButton: z.boolean().default(true),
  showDatePicker: z.boolean().default(false),
  dateRange: z
    .object({
      start: z.date().optional(),
      end: z.date().optional(),
      preset: z
        .enum(['today', 'yesterday', 'week', 'month', 'quarter', 'year', 'custom'])
        .optional(),
    })
    .optional(),
});

export type DashboardConfig = z.infer<typeof DashboardConfigSchema>;

// Workflow step configuration
export const WorkflowStepConfigSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().optional(),
  type: z.enum(['form', 'review', 'approval', 'action', 'conditional', 'parallel']),
  required: z.boolean().default(true),
  skippable: z.boolean().default(false),
  fields: z
    .array(
      z.object({
        key: z.string(),
        label: z.string(),
        type: z.enum([
          'text',
          'email',
          'number',
          'select',
          'multiselect',
          'boolean',
          'date',
          'file',
          'textarea',
        ]),
        required: z.boolean().default(false),
        validation: z
          .object({
            min: z.number().optional(),
            max: z.number().optional(),
            pattern: z.string().optional(),
            custom: z.function().optional(),
          })
          .optional(),
        options: z
          .array(
            z.object({
              value: z.string(),
              label: z.string(),
            })
          )
          .optional(),
        defaultValue: z.any().optional(),
        helpText: z.string().optional(),
      })
    )
    .default([]),
  validation: z
    .object({
      rules: z
        .array(
          z.object({
            field: z.string(),
            operator: z.enum([
              'equals',
              'notEquals',
              'contains',
              'greaterThan',
              'lessThan',
              'regex',
            ]),
            value: z.any(),
            message: z.string(),
          })
        )
        .default([]),
      onValidate: z
        .function()
        .args(z.record(z.any()))
        .returns(
          z.promise(
            z.object({
              isValid: z.boolean(),
              errors: z.array(z.string()),
            })
          )
        )
        .optional(),
    })
    .optional(),
  actions: z.array(ActionConfigSchema).default([]),
  nextStep: z.string().optional(),
  condition: z
    .object({
      field: z.string(),
      operator: z.enum(['equals', 'notEquals', 'contains', 'greaterThan', 'lessThan']),
      value: z.any(),
      nextStep: z.string(),
    })
    .optional(),
});

export type WorkflowStepConfig = z.infer<typeof WorkflowStepConfigSchema>;

// Workflow Template Configuration
export const WorkflowConfigSchema = BaseTemplateConfigSchema.extend({
  type: z.literal('workflow'),
  steps: z.array(WorkflowStepConfigSchema).min(1, 'At least one step is required'),
  allowStepNavigation: z.boolean().default(false),
  showProgress: z.boolean().default(true),
  showStepNumbers: z.boolean().default(true),
  persistData: z.boolean().default(true),
  autoSave: z.boolean().default(true),
  autoSaveInterval: z.number().default(30000),
  validation: z
    .object({
      validateOnChange: z.boolean().default(true),
      validateOnBlur: z.boolean().default(true),
      showErrorSummary: z.boolean().default(true),
    })
    .default({
      validateOnChange: true,
      validateOnBlur: true,
      showErrorSummary: true,
    }),
  onStepChange: z
    .function()
    .args(z.number(), z.record(z.any()))
    .returns(z.void().or(z.promise(z.void())))
    .optional(),
  onComplete: z.function().args(z.record(z.any())).returns(z.promise(z.any())).optional(),
  onCancel: z
    .function()
    .returns(z.void().or(z.promise(z.void())))
    .optional(),
});

export type WorkflowConfig = z.infer<typeof WorkflowConfigSchema>;

// Template state management
export interface TemplateState {
  loading: boolean;
  error: string | null;
  data: Record<string, any>;
  filters: Record<string, any>;
  sorting: {
    field: string;
    direction: 'asc' | 'desc';
  } | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  selectedItems: string[];
  bulkAction: string | null;
  refreshing: boolean;
  lastRefresh: Date | null;
}

// Template context
export interface TemplateContextValue {
  config: BaseTemplateConfig;
  state: TemplateState;
  actions: {
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    setData: (data: Record<string, any>) => void;
    updateFilters: (filters: Record<string, any>) => void;
    updateSorting: (field: string, direction: 'asc' | 'desc') => void;
    updatePagination: (page: number, pageSize?: number) => void;
    setSelectedItems: (items: string[]) => void;
    setBulkAction: (action: string | null) => void;
    refresh: () => Promise<void>;
    exportData: (format: 'csv' | 'excel' | 'json') => Promise<void>;
  };
  permissions: {
    canView: boolean;
    canEdit: boolean;
    canDelete: boolean;
    canExport: boolean;
    canBulkEdit: boolean;
  };
}

// Validation schemas export
export const TemplateConfigSchemas = {
  base: BaseTemplateConfigSchema,
  management: ManagementPageConfigSchema,
  dashboard: DashboardConfigSchema,
  workflow: WorkflowConfigSchema,
  action: ActionConfigSchema,
  filter: FilterConfigSchema,
  savedView: SavedViewConfigSchema,
  chart: ChartConfigSchema,
  metric: MetricConfigSchema,
  workflowStep: WorkflowStepConfigSchema,
} as const;

// Type guards
export const isManagementPageConfig = (config: any): config is ManagementPageConfig => {
  return ManagementPageConfigSchema.safeParse(config).success;
};

export const isDashboardConfig = (config: any): config is DashboardConfig => {
  return DashboardConfigSchema.safeParse(config).success;
};

export const isWorkflowConfig = (config: any): config is WorkflowConfig => {
  return WorkflowConfigSchema.safeParse(config).success;
};

// Template validation utilities
export const validateTemplateConfig = <T>(
  schema: z.ZodSchema<T>,
  config: unknown
): { isValid: boolean; data?: T; errors?: string[] } => {
  const result = schema.safeParse(config);

  if (result.success) {
    return { isValid: true, data: result.data };
  }

  const errors = result.error.errors.map((error) => `${error.path.join('.')}: ${error.message}`);

  return { isValid: false, errors };
};
