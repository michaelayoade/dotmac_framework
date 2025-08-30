// Core workflow types and interfaces
export type WorkflowStepStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped' | 'cancelled';
export type WorkflowStatus = 'draft' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
export type WorkflowStepType = 'manual' | 'automated' | 'approval' | 'notification' | 'form' | 'api_call' | 'conditional';
export type WorkflowCategory = 'customer' | 'network' | 'billing' | 'support' | 'admin' | 'onboarding' | 'provisioning';
export type Priority = 'low' | 'medium' | 'high' | 'urgent';

// Core workflow step interface
export interface WorkflowStep {
  id: string;
  name: string;
  description?: string;
  type: WorkflowStepType;
  status: WorkflowStepStatus;
  order: number;

  // Assignment and permissions
  assignedTo?: string;
  assignedRole?: string;
  requiredPermissions?: string[];

  // Timing
  estimatedDuration?: number; // in minutes
  actualDuration?: number;
  startTime?: number;
  endTime?: number;
  dueDate?: number;

  // Data
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  schema?: Record<string, unknown>; // JSON schema for validation

  // Relationships
  dependencies?: string[];
  blockers?: string[];

  // Conditions and rules
  conditions?: Array<{
    field: string;
    operator: 'equals' | 'not_equals' | 'contains' | 'greater_than' | 'less_than' | 'exists' | 'not_exists';
    value: unknown;
  }>;

  // Error handling
  error?: string;
  retryCount?: number;
  maxRetries?: number;

  // UI configuration
  ui?: {
    component?: string;
    props?: Record<string, unknown>;
    validation?: Record<string, unknown>;
    layout?: 'default' | 'compact' | 'expanded';
    theme?: string;
  };

  // Metadata
  metadata?: Record<string, unknown>;
  tags?: string[];
}

// Workflow definition interface
export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  category: WorkflowCategory;
  version: string;

  // Steps configuration
  steps: WorkflowStep[];

  // Triggers
  triggers: Array<{
    type: 'manual' | 'scheduled' | 'event' | 'webhook' | 'api';
    event?: string;
    schedule?: string; // cron expression
    conditions?: unknown[];
    webhook?: {
      url: string;
      method: 'GET' | 'POST' | 'PUT' | 'DELETE';
      headers?: Record<string, string>;
    };
  }>;

  // Settings
  settings: {
    allowParallel?: boolean;
    maxExecutionTime?: number; // in minutes
    retryOnFailure?: boolean;
    maxRetries?: number;
    autoStart?: boolean;
    requireApproval?: boolean;

    // Notifications
    notificationSettings?: {
      onStart?: boolean;
      onComplete?: boolean;
      onFailure?: boolean;
      onStepComplete?: boolean;
      recipients?: string[];
      channels?: Array<'email' | 'sms' | 'push' | 'webhook'>;
    };

    // SLA settings
    sla?: {
      responseTime?: number; // minutes
      completionTime?: number; // minutes
      escalationRules?: Array<{
        condition: string;
        action: string;
        delay: number; // minutes
      }>;
    };
  };

  // Metadata
  createdBy: string;
  createdAt: number;
  updatedBy?: string;
  updatedAt?: number;
  tags?: string[];
  isActive: boolean;
}

// Workflow instance interface
export interface WorkflowInstance {
  id: string;
  definitionId: string;
  name: string;
  status: WorkflowStatus;
  priority: Priority;

  // Progress tracking
  progress: number; // 0-100
  startTime: number;
  endTime?: number;
  estimatedCompletion?: number;

  // Ownership and context
  createdBy: string;
  tenantId: string;
  context: Record<string, unknown>;

  // Step tracking
  currentStep?: string;
  completedSteps: string[];
  failedSteps: string[];
  skippedSteps: string[];

  // Steps with their current state
  steps: WorkflowStep[];

  // Logging and audit
  logs: Array<{
    timestamp: number;
    level: 'info' | 'warn' | 'error' | 'debug';
    message: string;
    stepId?: string;
    data?: unknown;
    userId?: string;
  }>;

  // Metrics
  metrics: {
    totalSteps: number;
    completedSteps: number;
    failedSteps: number;
    averageStepDuration?: number;
    slaCompliance?: boolean;
    bottlenecks?: Array<{
      stepId: string;
      delay: number;
      reason: string;
    }>;
  };

  // Approvals
  approvals?: Array<{
    stepId: string;
    approver: string;
    status: 'pending' | 'approved' | 'rejected';
    timestamp?: number;
    comment?: string;
  }>;

  // External integrations
  integrations?: Record<string, {
    provider: string;
    status: string;
    data: unknown;
  }>;
}

// Workflow engine state
export interface WorkflowState {
  definitions: WorkflowDefinition[];
  instances: WorkflowInstance[];
  activeInstance: WorkflowInstance | null;
  templates: WorkflowTemplate[];

  // Loading states
  isLoading: boolean;
  isExecuting: boolean;

  // Error handling
  error: string | null;
  errors: Record<string, string>;

  // Filters and search
  filters: WorkflowFilters;
  searchQuery: string;

  // UI state
  viewMode: 'list' | 'grid' | 'timeline' | 'kanban';
  selectedItems: string[];

  // Real-time updates
  isConnected: boolean;
  lastUpdate: number;
}

// Workflow template for common patterns
export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: WorkflowCategory;

  // Template configuration
  definition: Omit<WorkflowDefinition, 'id' | 'createdBy' | 'createdAt'>;

  // Customization options
  customizable: {
    steps?: boolean;
    settings?: boolean;
    notifications?: boolean;
  };

  // Usage metadata
  usageCount: number;
  rating?: number;
  tags: string[];

  // Preview
  preview?: {
    estimatedDuration: number;
    stepCount: number;
    complexity: 'simple' | 'medium' | 'complex';
  };
}

// Form step configuration
export interface FormStepConfig {
  schema: Record<string, unknown>; // JSON schema
  uiSchema?: Record<string, unknown>; // UI schema for form rendering
  validation?: Record<string, unknown>; // Validation rules
  layout?: 'single-column' | 'two-column' | 'grid';
  sections?: Array<{
    title: string;
    fields: string[];
    collapsible?: boolean;
    description?: string;
  }>;
}

// Approval step configuration
export interface ApprovalStepConfig {
  approvers: Array<{
    type: 'user' | 'role' | 'group';
    identifier: string;
    required?: boolean;
    order?: number;
  }>;
  policy: 'any' | 'all' | 'majority' | 'sequential';
  escalation?: {
    delay: number; // minutes
    to: string;
    type: 'user' | 'role';
  };
  autoApprove?: {
    conditions: Array<{
      field: string;
      operator: string;
      value: unknown;
    }>;
  };
}

// Stepper component configuration
export interface StepperConfig {
  orientation: 'horizontal' | 'vertical';
  variant: 'default' | 'compact' | 'minimal';
  showNumbers?: boolean;
  showProgress?: boolean;
  allowSkip?: boolean;
  allowBack?: boolean;

  // Styling
  theme?: 'default' | 'modern' | 'minimal';
  colors?: {
    active?: string;
    completed?: string;
    pending?: string;
    error?: string;
  };

  // Behavior
  autoAdvance?: boolean;
  validateOnNext?: boolean;
  persistProgress?: boolean;
}

// Workflow filters
export interface WorkflowFilters {
  status?: WorkflowStatus[];
  category?: WorkflowCategory[];
  priority?: Priority[];
  assignedTo?: string[];
  dateRange?: {
    start: number;
    end: number;
  };
  tags?: string[];
}

// Event types for workflow engine
export type WorkflowEvent =
  | { type: 'workflow:created'; instanceId: string; definitionId: string }
  | { type: 'workflow:started'; instanceId: string }
  | { type: 'workflow:completed'; instanceId: string }
  | { type: 'workflow:failed'; instanceId: string; error: string }
  | { type: 'workflow:cancelled'; instanceId: string; reason: string }
  | { type: 'workflow:step_started'; instanceId: string; stepId: string }
  | { type: 'workflow:step_completed'; instanceId: string; stepId: string; output?: unknown }
  | { type: 'workflow:step_failed'; instanceId: string; stepId: string; error: string }
  | { type: 'workflow:approval_requested'; instanceId: string; stepId: string; approver: string }
  | { type: 'workflow:approval_granted'; instanceId: string; stepId: string; approver: string }
  | { type: 'workflow:approval_rejected'; instanceId: string; stepId: string; approver: string };

// Workflow engine configuration
export interface WorkflowEngineConfig {
  apiBaseUrl?: string;
  websocketUrl?: string;
  enableRealtime?: boolean;
  enableOffline?: boolean;
  persistenceKey?: string;

  // Performance
  maxConcurrentInstances?: number;
  maxRetries?: number;
  defaultTimeout?: number;

  // Features
  enableApprovals?: boolean;
  enableNotifications?: boolean;
  enableAuditLog?: boolean;

  // Custom handlers
  stepHandlers?: Record<string, (step: WorkflowStep, context: unknown) => Promise<unknown>>;
  eventHandlers?: Record<string, (event: WorkflowEvent) => void>;
}
