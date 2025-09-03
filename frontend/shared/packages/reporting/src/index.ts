/**
 * @dotmac/reporting - Universal Reporting Package
 * Leverages existing @dotmac systems for comprehensive reporting functionality
 */

// Main Components
export { UniversalReportGenerator } from './generators/UniversalReportGenerator';
export { ReportDashboard, ReportScheduler } from './components';

// Hooks
export { useReportData } from './hooks/useReportData';
export { useReportExport } from './hooks/useReportExport';

// Templates
export {
  ANALYTICS_TEMPLATES,
  FINANCIAL_TEMPLATES,
  OPERATIONAL_TEMPLATES,
  COMPLIANCE_TEMPLATES,
  PORTAL_TEMPLATES,
  getTemplatesByPortal,
  getTemplatesByCategory,
  getFeaturedTemplates,
  getPopularTemplates,
  searchTemplates,
} from './templates/UniversalReportTemplates';

// Types
export type {
  Report,
  ReportTemplate,
  ReportConfig,
  ReportResult,
  ReportCategory,
  ReportType,
  DataSourceConfig,
  VisualizationConfig,
  ChartConfig,
  TableConfig,
  FilterConfig,
  ReportSchedule,
  ReportDashboard as ReportDashboardType,
  ExportFormat,
} from './types';

// Utilities
export { cn } from './utils/cn';
