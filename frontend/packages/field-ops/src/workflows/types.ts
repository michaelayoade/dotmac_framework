export type WorkflowStepType =
  | 'arrival_confirmation'
  | 'customer_contact'
  | 'site_assessment'
  | 'safety_check'
  | 'equipment_verification'
  | 'pre_work_photos'
  | 'installation'
  | 'configuration'
  | 'testing'
  | 'customer_demo'
  | 'completion_photos'
  | 'customer_signature'
  | 'cleanup'
  | 'departure';

export interface WorkflowStep {
  id: string;
  type: WorkflowStepType;
  title: string;
  description: string;
  required: boolean;
  order: number;
  estimatedDuration: number; // minutes

  // Validation
  validationRules?: ValidationRule[];
  dependencies?: string[]; // Other step IDs that must be completed first

  // Form configuration
  formFields?: FormField[];

  // Evidence requirements
  evidenceRequired?: {
    photos?: {
      minimum: number;
      categories: string[];
    };
    signature?: boolean;
    notes?: boolean;
    measurements?: boolean;
  };

  // Status
  status: 'pending' | 'in_progress' | 'completed' | 'skipped' | 'failed';
  startedAt?: string;
  completedAt?: string;

  // Data collected
  data?: Record<string, any>;
  evidence?: StepEvidence[];

  // GPS tracking
  locationRequired?: boolean;
  geoFenceValidation?: boolean;
}

export interface ValidationRule {
  field: string;
  type: 'required' | 'min_length' | 'max_length' | 'pattern' | 'custom';
  value?: any;
  message: string;
  validator?: (value: any) => boolean;
}

export interface FormField {
  id: string;
  type: 'text' | 'textarea' | 'number' | 'select' | 'checkbox' | 'radio' | 'date' | 'time' | 'photo' | 'signature';
  label: string;
  placeholder?: string;
  required: boolean;
  options?: { value: string; label: string }[];
  validation?: ValidationRule[];
  defaultValue?: any;
}

export interface StepEvidence {
  id: string;
  type: 'photo' | 'signature' | 'note' | 'measurement' | 'file';
  data: string; // base64 or URL
  metadata: {
    timestamp: string;
    location?: [number, number];
    description?: string;
    category?: string;
  };
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  type: 'installation' | 'maintenance' | 'repair' | 'inspection';
  version: string;

  steps: WorkflowStep[];

  // Configuration
  allowSkipping: boolean;
  requireSequential: boolean;
  gpsTrackingRequired: boolean;
  customerSignatureRequired: boolean;

  // Metadata
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export interface WorkflowInstance {
  id: string;
  templateId: string;
  workOrderId: string;
  technicianId: string;

  // Current state
  currentStepId: string | null;
  status: 'not_started' | 'in_progress' | 'completed' | 'cancelled' | 'failed';
  progress: number; // 0-100

  // Steps with current data
  steps: WorkflowStep[];

  // Tracking
  startedAt?: string;
  completedAt?: string;
  totalDuration?: number; // minutes

  // Customer interaction
  customerPresent: boolean;
  customerSignature?: StepEvidence;
  customerFeedback?: {
    rating: number;
    comments: string;
  };

  // Sync
  syncStatus: 'synced' | 'pending' | 'error';
  lastModified: string;
}

export interface WorkflowValidationResult {
  isValid: boolean;
  errors: {
    stepId: string;
    field?: string;
    message: string;
  }[];
  warnings: {
    stepId: string;
    message: string;
  }[];
}

export interface WorkflowMetrics {
  averageCompletionTime: number;
  stepCompletionRates: Record<string, number>;
  commonIssues: {
    stepId: string;
    issue: string;
    frequency: number;
  }[];
  customerSatisfactionRating: number;
}
