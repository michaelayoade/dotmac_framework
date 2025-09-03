/**
 * Universal Reporting Types
 * Leverages existing @dotmac/primitives and @dotmac/data-tables types
 */

// Define PortalVariant type locally
export type PortalVariant = 'admin' | 'customer' | 'reseller' | 'technician' | 'management';

import type { ChartType, ChartDataPoint } from '@dotmac/primitives';

// Re-export ChartType for external use
export type { ChartType, ChartDataPoint };
import type { ExportConfig } from '@dotmac/data-tables';

// Base Report Types
export interface Report {
  id: string;
  title: string;
  description?: string;
  portal: PortalVariant;
  category: ReportCategory;
  type: ReportType;
  config: ReportConfig;
  schedule?: ReportSchedule;
  permissions: ReportPermissions;
  metadata: ReportMetadata;
  createdAt: Date;
  updatedAt: Date;
}

export type ReportCategory =
  | 'analytics'
  | 'financial'
  | 'operational'
  | 'compliance'
  | 'performance'
  | 'usage'
  | 'customer'
  | 'network';

export type ReportType = 'dashboard' | 'tabular' | 'chart' | 'mixed' | 'kpi' | 'comparison';

export interface ReportConfig {
  dataSource: DataSourceConfig;
  visualization: VisualizationConfig;
  filters: FilterConfig[];
  grouping?: GroupingConfig;
  sorting?: SortingConfig[];
  aggregation?: AggregationConfig[];
  export: ExportConfig;
}

// Data Source Configuration (leverages @dotmac/headless)
export interface DataSourceConfig {
  type: 'api' | 'query' | 'static' | 'realtime';
  endpoint?: string;
  query?: string;
  parameters?: Record<string, any>;
  refreshInterval?: number;
  caching?: boolean;
  transform?: (data: any[]) => any[];
}

// Visualization Configuration (leverages @dotmac/primitives charts)
export interface VisualizationConfig {
  type: 'table' | 'chart' | 'mixed';
  charts?: ChartConfig[];
  table?: TableConfig;
  layout?: LayoutConfig;
}

export interface ChartConfig {
  id: string;
  title: string;
  type: ChartType;
  data: ChartDataPoint[];
  series?: ChartSeries[];
  xAxis?: string;
  yAxis?: string | string[];
  size?: 'small' | 'medium' | 'large' | 'full';
  position?: { row: number; col: number; span?: number };
}

export interface ChartSeries {
  key: string;
  name: string;
  color?: string;
  type?: ChartType;
}

export interface TableConfig {
  columns: TableColumn[];
  pagination?: boolean;
  sorting?: boolean;
  filtering?: boolean;
  grouping?: string[];
  totals?: boolean;
}

export interface TableColumn {
  key: string;
  title: string;
  width?: number;
  sortable?: boolean;
  filterable?: boolean;
  formatter?: (value: any, row: any) => string | React.ReactNode;
  aggregate?: 'sum' | 'avg' | 'count' | 'min' | 'max';
}

export interface LayoutConfig {
  columns: number;
  gap: number;
  responsive?: boolean;
}

// Report Scheduling
export interface ReportSchedule {
  enabled: boolean;
  frequency: 'once' | 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  interval?: number;
  dayOfWeek?: number;
  dayOfMonth?: number;
  time: string; // HH:MM format
  timezone: string;
  recipients: string[];
  format: ExportFormat[];
  lastRun?: Date;
  nextRun?: Date;
}

export type ExportFormat = 'pdf' | 'csv' | 'xlsx' | 'json' | 'png' | 'html';

// Permissions & Access
export interface ReportPermissions {
  owner: string;
  viewers: string[];
  editors: string[];
  public?: boolean;
  portalAccess: PortalVariant[];
  roleAccess?: string[];
}

// Report Metadata
export interface ReportMetadata {
  tags: string[];
  version: number;
  template?: string;
  lastGenerated?: Date;
  executionTime?: number;
  rowCount?: number;
  fileSize?: number;
  checksum?: string;
}

// Filter Configuration
export interface FilterConfig {
  id: string;
  field: string;
  label: string;
  type: FilterType;
  operator: FilterOperator;
  value: any;
  values?: any[];
  required?: boolean;
  defaultValue?: any;
}

export type FilterType =
  | 'text'
  | 'number'
  | 'date'
  | 'datetime'
  | 'select'
  | 'multiselect'
  | 'boolean'
  | 'range';

export type FilterOperator =
  | 'eq'
  | 'ne'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'contains'
  | 'startsWith'
  | 'endsWith'
  | 'in'
  | 'notIn'
  | 'between'
  | 'isNull'
  | 'isNotNull';

// Grouping & Aggregation
export interface GroupingConfig {
  fields: string[];
  collapsed?: boolean;
  totals?: boolean;
}

export interface SortingConfig {
  field: string;
  direction: 'asc' | 'desc';
  priority: number;
}

export interface AggregationConfig {
  field: string;
  operation: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'countDistinct';
  label?: string;
}

// Report Templates (Portal-specific presets)
export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  category: ReportCategory;
  portal: PortalVariant;
  config: Partial<ReportConfig>;
  preview?: string;
  popular?: boolean;
  featured?: boolean;
}

// Real-time Report Status
export interface ReportExecution {
  id: string;
  reportId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  startTime: Date;
  endTime?: Date;
  duration?: number;
  progress?: number;
  result?: ReportResult;
  error?: string;
  userId: string;
}

export interface ReportResult {
  data: any[];
  metadata: {
    totalRows: number;
    columns: string[];
    executionTime: number;
    dataSource: string;
    generatedAt: Date;
  };
  exports?: {
    format: ExportFormat;
    url: string;
    size: number;
    expiresAt: Date;
  }[];
}

// Report Dashboard Types
export interface ReportDashboard {
  id: string;
  title: string;
  portal: PortalVariant;
  reports: DashboardReport[];
  layout: DashboardLayout;
  filters: GlobalFilter[];
  refreshInterval?: number;
  permissions: ReportPermissions;
}

export interface DashboardReport {
  reportId: string;
  position: { x: number; y: number; w: number; h: number };
  title?: string;
  showHeader?: boolean;
  showExport?: boolean;
  autoRefresh?: boolean;
}

export interface DashboardLayout {
  columns: number;
  rowHeight: number;
  margin: [number, number];
  containerPadding: [number, number];
  responsive?: boolean;
}

export interface GlobalFilter {
  id: string;
  label: string;
  type: FilterType;
  appliesTo: string[]; // Report IDs
  value: any;
}

// Error Types
export interface ReportError {
  code: string;
  message: string;
  details?: any;
  timestamp: Date;
  reportId?: string;
  userId?: string;
}
