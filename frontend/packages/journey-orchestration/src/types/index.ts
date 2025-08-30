// Journey Orchestration Types
export type JourneyStage =
  | 'prospect'
  | 'lead'
  | 'qualified'
  | 'customer'
  | 'active_service'
  | 'support'
  | 'renewal'
  | 'churn'
  | 'win_back';

export type JourneyStatus = 'active' | 'completed' | 'failed' | 'abandoned' | 'paused';

export type HandoffStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'rejected';

export type TriggerType = 'manual' | 'automated' | 'scheduled' | 'conditional' | 'event';

// Core Journey Interface
export interface CustomerJourney {
  id: string;
  customerId?: string;
  leadId?: string;
  tenantId: string;

  // Journey metadata
  name: string;
  type: 'acquisition' | 'onboarding' | 'support' | 'retention' | 'upgrade' | 'custom';
  stage: JourneyStage;
  status: JourneyStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';

  // Timeline
  startedAt: string;
  completedAt?: string;
  estimatedCompletion?: string;
  lastActivity: string;

  // Progress tracking
  currentStep: string;
  completedSteps: string[];
  totalSteps: number;
  progress: number; // 0-100

  // Context data
  context: Record<string, any>;
  metadata: Record<string, any>;

  // Integration tracking
  activeHandoffs: HandoffRecord[];
  integrationStatus: Record<string, 'connected' | 'error' | 'pending'>;

  // Analytics
  touchpoints: TouchpointRecord[];
  conversionEvents: ConversionEvent[];

  // Assignment
  assignedTo?: string;
  assignedTeam?: string;

  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

// Journey Step Definition
export interface JourneyStep {
  id: string;
  name: string;
  description: string;
  stage: JourneyStage;
  order: number;

  // Step configuration
  type: 'manual' | 'automated' | 'integration' | 'approval' | 'notification' | 'workflow';
  packageName?: string; // Which @dotmac package handles this step
  actionType?: string; // Specific action within the package

  // Conditions
  entryConditions?: Condition[];
  exitConditions?: Condition[];

  // Timing
  estimatedDuration: number; // minutes
  maxDuration?: number; // timeout

  // Data requirements
  requiredData?: string[];
  outputData?: string[];

  // UI configuration
  ui?: {
    component?: string;
    props?: Record<string, any>;
    title?: string;
    description?: string;
  };

  // Integration configuration
  integration?: {
    package: string;
    hook?: string;
    api?: string;
    params?: Record<string, any>;
  };
}

// Journey Template
export interface JourneyTemplate {
  id: string;
  name: string;
  description: string;
  category: 'acquisition' | 'onboarding' | 'support' | 'retention' | 'upgrade';

  // Template configuration
  steps: JourneyStep[];
  defaultContext: Record<string, any>;

  // Triggers
  triggers: JourneyTrigger[];

  // Settings
  settings: {
    allowSkipSteps?: boolean;
    requireApproval?: boolean;
    autoProgress?: boolean;
    notificationsEnabled?: boolean;
    slaTracking?: boolean;
  };

  // Metrics
  estimatedDuration: number;
  successRate?: number;
  usageCount: number;

  // Metadata
  tags: string[];
  version: string;
  isActive: boolean;
  createdBy: string;
  createdAt: string;
}

// Journey Triggers
export interface JourneyTrigger {
  id: string;
  name: string;
  type: TriggerType;

  // Trigger configuration
  event?: string; // Event name to listen for
  schedule?: string; // Cron expression for scheduled triggers
  conditions?: Condition[];

  // Target journey
  templateId: string;

  // Context mapping
  contextMapping?: Record<string, string>;

  // Settings
  isActive: boolean;
  priority: number;
}

// Conditions for triggers and steps
export interface Condition {
  field: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'greater_than' | 'less_than' | 'exists' | 'not_exists' | 'in' | 'not_in';
  value: any;
  type?: 'string' | 'number' | 'boolean' | 'date' | 'array';
}

// Handoff Management
export interface HandoffRecord {
  id: string;
  journeyId: string;

  // Handoff details
  fromPackage: string;
  toPackage: string;
  stepId: string;

  // Status tracking
  status: HandoffStatus;
  startedAt: string;
  completedAt?: string;

  // Data transfer
  data: Record<string, any>;
  requiredData?: string[];
  validationErrors?: string[];

  // Assignment
  assignedTo?: string;
  handoffType: 'automatic' | 'manual' | 'approval_required';

  // Results
  result?: 'success' | 'failure' | 'partial';
  errorMessage?: string;
  notes?: string;
}

// Touchpoint Tracking
export interface TouchpointRecord {
  id: string;
  journeyId: string;

  // Touchpoint details
  type: 'email' | 'sms' | 'call' | 'meeting' | 'web_visit' | 'app_usage' | 'support_ticket' | 'billing_interaction';
  channel: string;
  source: string; // Which package/app generated this touchpoint

  // Content
  title: string;
  description?: string;
  outcome?: 'positive' | 'negative' | 'neutral';

  // Context
  userId?: string;
  metadata: Record<string, any>;

  // Timing
  timestamp: string;
  duration?: number; // in seconds
}

// Conversion Events
export interface ConversionEvent {
  id: string;
  journeyId: string;

  // Event details
  eventType: 'lead_created' | 'lead_qualified' | 'customer_converted' | 'service_activated' | 'upsell' | 'renewal' | 'churn';
  fromStage: JourneyStage;
  toStage: JourneyStage;

  // Value tracking
  value?: number; // monetary value
  previousValue?: number;

  // Attribution
  source: string;
  campaign?: string;
  channel?: string;

  // Context
  metadata: Record<string, any>;
  timestamp: string;
}

// Analytics Types
export interface ConversionFunnel {
  name: string;
  stages: Array<{
    stage: JourneyStage;
    count: number;
    conversionRate: number;
    averageDuration: number; // days
    dropOffReasons?: Array<{
      reason: string;
      count: number;
    }>;
  }>;
  totalConversions: number;
  overallConversionRate: number;
  averageJourneyDuration: number; // days
}

export interface JourneyMetrics {
  totalJourneys: number;
  activeJourneys: number;
  completedJourneys: number;
  abandonedJourneys: number;

  // Conversion metrics
  conversionRates: Record<string, number>;
  averageJourneyDuration: number;

  // Stage metrics
  stageMetrics: Record<JourneyStage, {
    count: number;
    averageDuration: number;
    completionRate: number;
  }>;

  // Performance metrics
  slaCompliance: number;
  handoffSuccessRate: number;
  automationRate: number;

  // Revenue metrics
  totalRevenue?: number;
  revenuePerJourney?: number;
  lifetimeValue?: number;
}

// Event Bus Types
export interface JourneyEvent {
  id: string;
  type: string;
  source: string; // Which package emitted this event
  journeyId?: string;
  customerId?: string;
  leadId?: string;

  // Event data
  data: Record<string, any>;
  metadata?: Record<string, any>;

  // Context
  tenantId: string;
  userId?: string;
  timestamp: string;

  // Processing
  processed?: boolean;
  processingErrors?: string[];
}

// API Response Types
export interface JourneyListResponse {
  journeys: CustomerJourney[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface JourneyAnalyticsResponse {
  metrics: JourneyMetrics;
  funnels: ConversionFunnel[];
  trends: Array<{
    date: string;
    stage: JourneyStage;
    count: number;
    value?: number;
  }>;
}

// Hook Return Types
export interface UseJourneyOrchestrationReturn {
  // State
  journeys: CustomerJourney[];
  activeJourney: CustomerJourney | null;
  loading: boolean;
  error: string | null;

  // Journey management
  startJourney: (templateId: string, context?: Record<string, any>) => Promise<CustomerJourney>;
  pauseJourney: (journeyId: string) => Promise<void>;
  resumeJourney: (journeyId: string) => Promise<void>;
  completeJourney: (journeyId: string) => Promise<void>;
  abandonJourney: (journeyId: string, reason?: string) => Promise<void>;

  // Step management
  advanceStep: (journeyId: string, stepId?: string) => Promise<void>;
  skipStep: (journeyId: string, stepId: string, reason: string) => Promise<void>;
  retryStep: (journeyId: string, stepId: string) => Promise<void>;

  // Context management
  updateContext: (journeyId: string, updates: Record<string, any>) => Promise<void>;
  addTouchpoint: (journeyId: string, touchpoint: Omit<TouchpointRecord, 'id' | 'journeyId'>) => Promise<void>;

  // Handoffs
  initiateHandoff: (journeyId: string, handoff: Omit<HandoffRecord, 'id' | 'journeyId'>) => Promise<HandoffRecord>;
  completeHandoff: (handoffId: string, result: Record<string, any>) => Promise<void>;

  // Search and filter
  searchJourneys: (query: string) => Promise<CustomerJourney[]>;
  filterJourneys: (filters: Record<string, any>) => Promise<void>;

  // Real-time updates
  subscribeToJourney: (journeyId: string, callback: (journey: CustomerJourney) => void) => () => void;
}

export interface UseConversionAnalyticsReturn {
  // Analytics state
  metrics: JourneyMetrics | null;
  funnels: ConversionFunnel[];
  trends: any[];
  loading: boolean;
  error: string | null;

  // Analytics methods
  refreshMetrics: () => Promise<void>;
  getFunnelData: (type: string) => Promise<ConversionFunnel>;
  getDropoffAnalysis: (stage: JourneyStage) => Promise<any>;
  getAttributionData: () => Promise<any>;

  // Reporting
  exportAnalytics: (format: 'csv' | 'json') => Promise<string>;
  generateReport: (type: string, params?: Record<string, any>) => Promise<any>;
}

export interface UseHandoffSystemReturn {
  // State
  activeHandoffs: HandoffRecord[];
  pendingApprovals: HandoffRecord[];
  loading: boolean;
  error: string | null;

  // Handoff management
  createHandoff: (handoff: Omit<HandoffRecord, 'id'>) => Promise<HandoffRecord>;
  processHandoff: (handoffId: string) => Promise<void>;
  approveHandoff: (handoffId: string, notes?: string) => Promise<void>;
  rejectHandoff: (handoffId: string, reason: string) => Promise<void>;

  // Bulk operations
  bulkProcessHandoffs: (handoffIds: string[]) => Promise<void>;

  // Monitoring
  getHandoffStatus: (handoffId: string) => Promise<HandoffRecord>;
  getFailedHandoffs: () => Promise<HandoffRecord[]>;
  retryFailedHandoffs: (handoffIds: string[]) => Promise<void>;
}

// Configuration
export interface JourneyOrchestrationConfig {
  apiBaseUrl?: string;
  websocketUrl?: string;
  enableRealtime?: boolean;
  enableAnalytics?: boolean;
  enableHandoffs?: boolean;

  // Performance
  maxConcurrentJourneys?: number;
  handoffTimeout?: number; // milliseconds
  retryAttempts?: number;

  // Integrations
  packageIntegrations?: Record<string, {
    enabled: boolean;
    config?: Record<string, any>;
  }>;

  // Analytics
  analyticsRetentionDays?: number;
  enableTouchpointTracking?: boolean;
  enableConversionTracking?: boolean;
}
