/**
 * Template Components Index
 * Exports all reusable template components
 */

export { ManagementPageTemplate } from './ManagementPageTemplate';
export { DashboardTemplate } from './DashboardTemplate';
export { WorkflowTemplate, useWorkflow } from './WorkflowTemplate';
export { KanbanBoard } from './KanbanBoard';

// Re-export types from the types module
export type {
  ManagementPageConfig,
  DashboardConfig,
  WorkflowConfig,
  ChartConfig,
  MetricConfig,
  FilterConfig,
  ActionConfig,
  SavedViewConfig,
  WorkflowStepConfig,
} from '../types/templates';
