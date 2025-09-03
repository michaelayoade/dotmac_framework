// Main exports
export { default as WorkflowEngine } from './engines/WorkflowEngine';
export { default as useWorkflow } from './workflows/hooks/useWorkflow';

// Phase 2: Unified DRY Components
export { default as VisualWorkflowDesigner } from './designer/VisualWorkflowDesigner';
export { default as AutomationCenter } from './automation/AutomationCenter';
export { default as ServiceIntegrationDashboard } from './integration/ServiceIntegrationDashboard';
export { default as useUnifiedWorkflow } from './hooks/useUnifiedWorkflow';

// Workflow components
export { WorkflowRunner } from './workflows/WorkflowRunner';

// Stepper components
export { Stepper, StepIndicator, StepContent, Step, useStepper } from './stepper';

// Approval components
export { ApprovalStep } from './approval';

// Form components
export { WorkflowFormStep } from './forms';

// Tracking components
export { StatusTracker } from './tracking';

// Types
export type {
  WorkflowDefinition,
  WorkflowInstance,
  WorkflowStep,
  WorkflowState,
  WorkflowTemplate,
  WorkflowEvent,
  WorkflowEngineConfig,
  StepperConfig,
  FormStepConfig,
  ApprovalStepConfig,
  WorkflowFilters,
  WorkflowStatus,
  WorkflowStepStatus,
  WorkflowStepType,
  WorkflowCategory,
  Priority,
} from './types';
