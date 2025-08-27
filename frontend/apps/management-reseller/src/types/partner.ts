/**
 * Partner-related types and interfaces
 */

export type PartnerStatus = 'ACTIVE' | 'INACTIVE' | 'SUSPENDED' | 'PENDING' | 'TERMINATED';
export type PartnerType = 'RESELLER' | 'DISTRIBUTOR' | 'AGENT' | 'AFFILIATE' | 'REFERRER';
export type PartnerTier = 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM' | 'DIAMOND';

// Partner contact information
export interface PartnerContact {
  email: string;
  phone?: string;
  mobile?: string;
  fax?: string;
  website?: string;
  linkedin?: string;
  preferred_contact_method: 'EMAIL' | 'PHONE' | 'SMS' | 'WHATSAPP';
  timezone: string;
  language: string;
}

// Partner address information
export interface PartnerAddress {
  street1: string;
  street2?: string;
  city: string;
  state_province: string;
  postal_code: string;
  country: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
}

// Partner business information
export interface PartnerBusiness {
  legal_name: string;
  trade_name?: string;
  business_type: 'INDIVIDUAL' | 'CORPORATION' | 'LLC' | 'PARTNERSHIP' | 'NON_PROFIT';
  tax_id?: string;
  vat_number?: string;
  registration_number?: string;
  industry: string;
  website?: string;
  employee_count?: number;
  annual_revenue?: number;
  established_date?: string;
  description?: string;
}

// Partner banking/payment information
export interface PartnerPayment {
  preferred_currency: string;
  payment_terms: 'NET_30' | 'NET_60' | 'NET_90' | 'IMMEDIATE';
  bank_details?: {
    account_name: string;
    account_number: string;
    bank_name: string;
    routing_number?: string;
    swift_code?: string;
    iban?: string;
  };
  paypal_email?: string;
  tax_exempt: boolean;
  tax_certificate_url?: string;
}

// Partner territory/coverage
export interface PartnerTerritory {
  countries: string[];
  states_provinces: string[];
  cities: string[];
  postal_codes: string[];
  exclusive: boolean;
  territory_type: 'GEOGRAPHIC' | 'VERTICAL' | 'ACCOUNT_BASED';
  restrictions?: string[];
  effective_date: string;
  end_date?: string;
}

// Partner performance metrics
export interface PartnerMetrics {
  total_sales: number;
  monthly_sales: number;
  quarterly_sales: number;
  yearly_sales: number;
  total_customers: number;
  active_customers: number;
  new_customers_monthly: number;
  customer_retention_rate: number;
  average_deal_size: number;
  total_commissions_earned: number;
  commissions_ytd: number;
  commission_rate: number;
  performance_rating: number; // 1-5 scale
  tier_progress: {
    current_tier: PartnerTier;
    next_tier?: PartnerTier;
    progress_percentage: number;
    requirements_met: number;
    total_requirements: number;
  };
}

// Partner relationship hierarchy
export interface PartnerHierarchy {
  parent_partner_id?: string;
  parent_partner_name?: string;
  recruitment_level: number;
  recruited_partners: Array<{
    partner_id: string;
    partner_name: string;
    recruitment_date: string;
    status: PartnerStatus;
  }>;
  total_downline: number;
  direct_recruits: number;
  recruitment_bonus_eligible: boolean;
}

// Main Partner interface
export interface Partner {
  id: string;
  partner_code: string;
  name: string;
  display_name?: string;
  type: PartnerType;
  tier: PartnerTier;
  status: PartnerStatus;
  
  // Contact & Business Info
  contact: PartnerContact;
  address: PartnerAddress;
  business: PartnerBusiness;
  payment: PartnerPayment;
  
  // Program Information
  join_date: string;
  activation_date?: string;
  termination_date?: string;
  contract_start_date?: string;
  contract_end_date?: string;
  commission_plan_id: string;
  commission_plan_name: string;
  
  // Territory & Coverage
  territory?: PartnerTerritory;
  
  // Performance & Metrics
  metrics: PartnerMetrics;
  hierarchy?: PartnerHierarchy;
  
  // Settings & Preferences
  settings: {
    auto_commission_approval: boolean;
    marketing_emails: boolean;
    performance_reports: boolean;
    portal_access: boolean;
    api_access: boolean;
    white_label: boolean;
  };
  
  // Certification & Training
  certifications: Array<{
    name: string;
    obtained_date: string;
    expiry_date?: string;
    certificate_url?: string;
  }>;
  
  training_progress: {
    completed_modules: number;
    total_modules: number;
    last_activity: string;
    certificates_earned: number;
  };
  
  // Notes & History
  notes?: string;
  tags: string[];
  assigned_manager?: string;
  account_manager?: string;
  
  // Audit fields
  created_by: string;
  created_at: string;
  updated_at: string;
  last_login?: string;
  last_activity?: string;
}

// Partner creation/registration data
export interface CreatePartnerRequest {
  name: string;
  type: PartnerType;
  contact: Omit<PartnerContact, 'timezone' | 'language'> & {
    timezone?: string;
    language?: string;
  };
  address: PartnerAddress;
  business: Partial<PartnerBusiness> & {
    legal_name: string;
    business_type: PartnerBusiness['business_type'];
  };
  payment: Partial<PartnerPayment> & {
    preferred_currency: string;
  };
  territory?: Partial<PartnerTerritory>;
  commission_plan_id: string;
  parent_partner_id?: string;
  notes?: string;
  tags?: string[];
}

// Partner update data
export interface UpdatePartnerRequest {
  name?: string;
  display_name?: string;
  type?: PartnerType;
  tier?: PartnerTier;
  status?: PartnerStatus;
  contact?: Partial<PartnerContact>;
  address?: Partial<PartnerAddress>;
  business?: Partial<PartnerBusiness>;
  payment?: Partial<PartnerPayment>;
  territory?: Partial<PartnerTerritory>;
  commission_plan_id?: string;
  settings?: Partial<Partner['settings']>;
  notes?: string;
  tags?: string[];
  assigned_manager?: string;
  account_manager?: string;
}

// Partner filters
export interface PartnerFilters {
  status?: PartnerStatus;
  type?: PartnerType;
  tier?: PartnerTier;
  country?: string;
  state_province?: string;
  city?: string;
  commission_plan_id?: string;
  assigned_manager?: string;
  account_manager?: string;
  parent_partner_id?: string;
  joined_after?: string;
  joined_before?: string;
  min_sales?: number;
  max_sales?: number;
  performance_rating_min?: number;
  performance_rating_max?: number;
  has_territory?: boolean;
  certification_name?: string;
  tags?: string[];
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: 'name' | 'join_date' | 'total_sales' | 'tier' | 'status' | 'last_activity';
  sort_order?: 'asc' | 'desc';
}

// Partner statistics/summary
export interface PartnerStats {
  total_partners: number;
  active_partners: number;
  new_partners_monthly: number;
  by_status: Record<PartnerStatus, number>;
  by_type: Record<PartnerType, number>;
  by_tier: Record<PartnerTier, number>;
  by_region: Record<string, number>;
  performance_metrics: {
    total_sales: number;
    average_performance_rating: number;
    top_performers: Array<{
      partner_id: string;
      partner_name: string;
      sales: number;
      rating: number;
    }>;
  };
  recruitment_metrics: {
    total_recruited: number;
    recruitment_rate: number;
    top_recruiters: Array<{
      partner_id: string;
      partner_name: string;
      recruited_count: number;
    }>;
  };
}

// Partner activity/event
export interface PartnerActivity {
  id: string;
  partner_id: string;
  type: 'REGISTRATION' | 'STATUS_CHANGE' | 'SALE' | 'COMMISSION' | 'TRAINING' | 'CERTIFICATION' | 'LOGIN' | 'PROFILE_UPDATE';
  description: string;
  metadata?: Record<string, unknown>;
  created_by?: string;
  timestamp: string;
}

// Bulk partner operations
export interface BulkPartnerAction {
  operation: 'UPDATE_STATUS' | 'UPDATE_TIER' | 'ASSIGN_MANAGER' | 'ADD_TAGS' | 'REMOVE_TAGS';
  partner_ids: string[];
  payload: Record<string, unknown>;
}

export interface BulkPartnerResult {
  success_count: number;
  error_count: number;
  errors: Array<{
    partner_id: string;
    error: string;
  }>;
}