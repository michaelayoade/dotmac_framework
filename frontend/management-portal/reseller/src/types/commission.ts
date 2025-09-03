/**
 * Commission-related types and interfaces
 */

export type CommissionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'PAID';
export type CommissionType = 'SALES' | 'RECRUITMENT' | 'OVERRIDE' | 'BONUS' | 'RESIDUAL';
export type PaymentMethod = 'BANK_TRANSFER' | 'CHECK' | 'PAYPAL' | 'CRYPTOCURRENCY';

// Commission record
export interface Commission {
  id: string;
  partner_id: string;
  partner_name: string;
  type: CommissionType;
  status: CommissionStatus;
  amount: number;
  currency: string;
  percentage?: number;
  base_amount?: number;
  order_id?: string;
  customer_id?: string;
  customer_name?: string;
  product_id?: string;
  product_name?: string;
  tier_level?: number;
  calculation_method: 'PERCENTAGE' | 'FIXED' | 'TIERED' | 'CUSTOM';
  period_start: string;
  period_end: string;
  earned_date: string;
  due_date: string;
  approved_date?: string;
  paid_date?: string;
  approved_by?: string;
  payment_reference?: string;
  payment_method?: PaymentMethod;
  notes?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// Commission summary/statistics
export interface CommissionSummary {
  total_commissions: number;
  pending_amount: number;
  approved_amount: number;
  paid_amount: number;
  rejected_amount: number;
  pending_count: number;
  approved_count: number;
  paid_count: number;
  rejected_count: number;
  average_commission: number;
  highest_commission: number;
  currency: string;
  period_start: string;
  period_end: string;
  by_type: Record<
    CommissionType,
    {
      count: number;
      amount: number;
    }
  >;
  by_partner: Array<{
    partner_id: string;
    partner_name: string;
    total_amount: number;
    count: number;
  }>;
}

// Commission filters
export interface CommissionFilters {
  partner_id?: string;
  status?: CommissionStatus;
  type?: CommissionType;
  period_start?: string;
  period_end?: string;
  earned_after?: string;
  earned_before?: string;
  min_amount?: number;
  max_amount?: number;
  currency?: string;
  payment_method?: PaymentMethod;
  approved_by?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: 'earned_date' | 'amount' | 'status' | 'partner_name' | 'created_at';
  sort_order?: 'asc' | 'desc';
}

// Commission calculation data
export interface CommissionCalculation {
  base_amount: number;
  percentage?: number;
  fixed_amount?: number;
  tier_level?: number;
  tier_percentage?: number;
  multiplier?: number;
  deductions?: Array<{
    type: string;
    amount: number;
    description: string;
  }>;
  bonuses?: Array<{
    type: string;
    amount: number;
    description: string;
  }>;
  calculated_amount: number;
  final_amount: number;
  currency: string;
  calculation_notes?: string;
}

// Commission approval data
export interface CommissionApproval {
  commission_id: string;
  approved_by: string;
  approved_date: string;
  approved_amount: number;
  original_amount: number;
  adjustment_reason?: string;
  notes?: string;
  auto_approved: boolean;
}

// Commission payment data
export interface CommissionPayment {
  id: string;
  commission_ids: string[];
  partner_id: string;
  partner_name: string;
  total_amount: number;
  currency: string;
  payment_method: PaymentMethod;
  payment_reference: string;
  payment_date: string;
  processed_by: string;
  bank_details?: {
    account_name: string;
    account_number: string;
    bank_name: string;
    routing_number?: string;
    swift_code?: string;
  };
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'REVERSED';
  failure_reason?: string;
  receipt_url?: string;
  created_at: string;
  updated_at: string;
}

// Commission tier configuration
export interface CommissionTier {
  id: string;
  name: string;
  level: number;
  min_sales?: number;
  max_sales?: number;
  min_recruits?: number;
  max_recruits?: number;
  percentage: number;
  fixed_amount?: number;
  requirements: Array<{
    type: string;
    value: number;
    description: string;
  }>;
  active: boolean;
  created_at: string;
  updated_at: string;
}

// Commission plan configuration
export interface CommissionPlan {
  id: string;
  name: string;
  description?: string;
  type: 'SALES' | 'MLM' | 'AFFILIATE' | 'HYBRID';
  default_percentage: number;
  max_levels: number;
  tiers: CommissionTier[];
  rules: Array<{
    condition: string;
    action: string;
    value: number;
    description: string;
  }>;
  active: boolean;
  effective_date: string;
  end_date?: string;
  created_at: string;
  updated_at: string;
}

// Bulk commission operations
export interface BulkCommissionAction {
  operation: 'APPROVE' | 'REJECT' | 'MARK_PAID' | 'RECALCULATE';
  commission_ids: string[];
  payload?: {
    notes?: string;
    approved_by?: string;
    payment_reference?: string;
    payment_method?: PaymentMethod;
    adjustment_percentage?: number;
  };
}

export interface BulkCommissionResult {
  success_count: number;
  error_count: number;
  total_amount: number;
  errors: Array<{
    commission_id: string;
    error: string;
  }>;
}
