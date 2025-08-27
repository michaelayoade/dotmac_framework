/**
 * Onboarding-specific types and interfaces
 */

export type OnboardingStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'REJECTED';
export type OnboardingStepStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'APPROVED' | 'REJECTED';
export type PartnerType = 'RESELLER' | 'DISTRIBUTOR' | 'AGENT' | 'AFFILIATE';

// Onboarding step data
export interface OnboardingStep {
  id: string;
  name: string;
  description?: string;
  status: OnboardingStepStatus;
  required: boolean;
  order: number;
  data?: Record<string, unknown>;
  completed_at?: string;
  approved_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  approved_by?: string;
  created_at: string;
  updated_at: string;
}

// Onboarding request data
export interface OnboardingRequest {
  id: string;
  partner_id: string;
  partner_name: string;
  partner_type: PartnerType;
  status: OnboardingStatus;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  assigned_to?: string;
  steps: Record<string, OnboardingStep>;
  progress_percentage: number;
  estimated_completion?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
}

// Onboarding creation payload
export interface CreateOnboardingRequest {
  partner_id: string;
  partner_name: string;
  partner_type: PartnerType;
  priority?: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  assigned_to?: string;
  notes?: string;
  initial_data?: Record<string, unknown>;
}

// Onboarding step update payload
export interface UpdateOnboardingStepData {
  data?: Record<string, unknown>;
  notes?: string;
  status?: OnboardingStepStatus;
}

// Onboarding filters for listing
export interface OnboardingFilters {
  status?: OnboardingStatus;
  partner_type?: PartnerType;
  priority?: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  assigned_to?: string;
  created_after?: string;
  created_before?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: 'created_at' | 'updated_at' | 'priority' | 'progress_percentage';
  sort_order?: 'asc' | 'desc';
}

// Onboarding statistics
export interface OnboardingStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  rejected: number;
  avgCompletionTime: number; // in days
  byPartnerType: Record<PartnerType, number>;
  byPriority: Record<string, number>;
  recentActivity: Array<{
    id: string;
    partner_name: string;
    action: string;
    timestamp: string;
  }>;
}

// Onboarding optimistic update data
export interface OnboardingOptimisticUpdate {
  status?: OnboardingStatus;
  progress_percentage?: number;
  steps?: Record<string, Partial<OnboardingStep>>;
  notes?: string;
  completed_at?: string;
  updated_at?: string;
}

// Onboarding template
export interface OnboardingTemplate {
  id: string;
  name: string;
  description?: string;
  partner_type: PartnerType;
  steps: Array<{
    name: string;
    description?: string;
    required: boolean;
    order: number;
    default_data?: Record<string, unknown>;
  }>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// Onboarding activity log
export interface OnboardingActivity {
  id: string;
  onboarding_id: string;
  user_id: string;
  user_name: string;
  action: 'CREATED' | 'UPDATED' | 'STEP_COMPLETED' | 'STEP_APPROVED' | 'STEP_REJECTED' | 'COMPLETED' | 'REJECTED';
  details?: string;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

// Onboarding assignment data
export interface OnboardingAssignment {
  onboarding_id: string;
  assigned_to: string;
  assigned_by: string;
  assigned_at: string;
  notes?: string;
}

// Onboarding escalation data
export interface OnboardingEscalation {
  id: string;
  onboarding_id: string;
  reason: string;
  escalated_to: string;
  escalated_by: string;
  escalated_at: string;
  resolved_at?: string;
  resolution_notes?: string;
}

// Bulk onboarding operations
export interface BulkOnboardingAction {
  operation: 'ASSIGN' | 'UPDATE_STATUS' | 'UPDATE_PRIORITY' | 'ADD_NOTES';
  onboarding_ids: string[];
  payload: Record<string, unknown>;
}

export interface BulkOnboardingResult {
  success_count: number;
  error_count: number;
  errors: Array<{
    onboarding_id: string;
    error: string;
  }>;
}