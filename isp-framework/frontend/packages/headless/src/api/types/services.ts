/**
 * Service-specific Type Definitions
 * Comprehensive types for all ISP Framework service modules
 */

import type { ApiResponse, PaginatedResponse, QueryParams } from './api';

// Common interfaces
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
  tenant_id: string;
}

// Identity Service Types
export namespace Identity {
  export interface User extends BaseEntity {
    email: string;
    name: string;
    role: UserRole;
    permissions: string[];
    portal: Portal;
    status: UserStatus;
    last_login?: string;
    mfa_enabled: boolean;
    email_verified: boolean;
    profile?: UserProfile;
  }

  export interface UserProfile {
    avatar_url?: string;
    phone?: string;
    timezone: string;
    locale: string;
    preferences: Record<string, any>;
  }

  export type UserRole = 'admin' | 'manager' | 'technician' | 'support' | 'customer' | 'reseller';
  export type Portal = 'admin' | 'customer' | 'reseller' | 'technician';
  export type UserStatus = 'active' | 'inactive' | 'locked' | 'pending';

  export interface Customer extends BaseEntity {
    portal_id: string;
    account_number: string;
    company_name?: string;
    contact_name: string;
    email: string;
    phone?: string;
    address: Address;
    status: CustomerStatus;
    account_type: AccountType;
    billing_info: BillingInfo;
    services: CustomerService[];
    notes?: string;
    tags?: string[];
  }

  export type CustomerStatus = 'active' | 'inactive' | 'suspended' | 'pending' | 'canceled';
  export type AccountType = 'residential' | 'business' | 'enterprise';

  export interface Address {
    street: string;
    unit?: string;
    city: string;
    state: string;
    zip: string;
    country: string;
    coordinates?: {
      latitude: number;
      longitude: number;
    };
  }

  export interface BillingInfo {
    billing_address?: Address;
    payment_method_id?: string;
    billing_cycle: BillingCycle;
    auto_pay: boolean;
    tax_exempt: boolean;
    credit_limit?: number;
  }

  export type BillingCycle = 'monthly' | 'quarterly' | 'annually';

  export interface CustomerService {
    id: string;
    service_plan_id: string;
    status: ServiceStatus;
    installed_date?: string;
    activation_date?: string;
    suspension_date?: string;
    cancellation_date?: string;
    monthly_recurring_charge: number;
    configuration: Record<string, any>;
  }

  export type ServiceStatus = 'active' | 'inactive' | 'suspended' | 'pending_install' | 'pending_cancel';
}

// Services Module Types
export namespace Services {
  export interface ServicePlan extends BaseEntity {
    name: string;
    description: string;
    category: ServiceCategory;
    type: ServiceType;
    pricing: ServicePricing;
    features: ServiceFeature[];
    technical_specs: TechnicalSpecs;
    availability: ServiceAvailability;
    status: 'active' | 'inactive' | 'deprecated';
  }

  export type ServiceCategory = 'internet' | 'voice' | 'tv' | 'bundle' | 'add_on';
  export type ServiceType = 'fiber' | 'cable' | 'dsl' | 'wireless' | 'satellite' | 'voip' | 'iptv';

  export interface ServicePricing {
    monthly_price: number;
    setup_fee?: number;
    installation_fee?: number;
    equipment_fee?: number;
    early_termination_fee?: number;
    contract_term_months?: number;
    promotional_pricing?: PromotionalPricing[];
  }

  export interface PromotionalPricing {
    price: number;
    duration_months: number;
    conditions?: string[];
  }

  export interface ServiceFeature {
    name: string;
    description: string;
    included: boolean;
    additional_cost?: number;
  }

  export interface TechnicalSpecs {
    download_speed?: number; // Mbps
    upload_speed?: number; // Mbps
    data_limit?: number; // GB, null for unlimited
    latency?: number; // ms
    availability?: number; // uptime percentage
    equipment_required?: string[];
  }

  export interface ServiceAvailability {
    regions: string[];
    zip_codes?: string[];
    technology_requirements?: string[];
    installation_timeframe?: string;
  }
}

// Billing Module Types
export namespace Billing {
  export interface Invoice extends BaseEntity {
    invoice_number: string;
    customer_id: string;
    billing_period: DateRange;
    due_date: string;
    status: InvoiceStatus;
    amount: InvoiceAmount;
    line_items: LineItem[];
    payments: Payment[];
    adjustments: Adjustment[];
    notes?: string;
  }

  export type InvoiceStatus = 'draft' | 'sent' | 'viewed' | 'partial_payment' | 'paid' | 'overdue' | 'cancelled';

  export interface InvoiceAmount {
    subtotal: number;
    tax: number;
    total: number;
    paid: number;
    balance: number;
  }

  export interface LineItem {
    id: string;
    description: string;
    service_id?: string;
    quantity: number;
    unit_price: number;
    amount: number;
    period?: DateRange;
    type: 'service' | 'equipment' | 'fee' | 'discount' | 'adjustment';
  }

  export interface Payment extends BaseEntity {
    invoice_id: string;
    amount: number;
    method: PaymentMethod;
    status: PaymentStatus;
    transaction_id?: string;
    processed_at?: string;
    notes?: string;
  }

  export type PaymentMethod = 'credit_card' | 'bank_transfer' | 'check' | 'cash' | 'store_credit';
  export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';

  export interface Adjustment {
    id: string;
    type: 'credit' | 'debit';
    amount: number;
    reason: string;
    created_by: string;
  }

  export interface DateRange {
    start_date: string;
    end_date: string;
  }
}

// Network Module Types
export namespace Network {
  export interface NetworkDevice extends BaseEntity {
    name: string;
    type: DeviceType;
    model: string;
    serial_number: string;
    mac_address?: string;
    ip_address?: string;
    location: DeviceLocation;
    status: DeviceStatus;
    specifications: DeviceSpecs;
    configuration: Record<string, any>;
    last_seen?: string;
    uptime?: number; // seconds
    firmware_version?: string;
  }

  export type DeviceType = 
    | 'router' 
    | 'switch' 
    | 'access_point' 
    | 'modem' 
    | 'ont' 
    | 'olt' 
    | 'firewall' 
    | 'load_balancer'
    | 'server';

  export type DeviceStatus = 'online' | 'offline' | 'warning' | 'critical' | 'maintenance';

  export interface DeviceLocation {
    site_id?: string;
    building?: string;
    floor?: string;
    room?: string;
    rack?: string;
    position?: string;
    coordinates?: {
      latitude: number;
      longitude: number;
    };
  }

  export interface DeviceSpecs {
    cpu?: string;
    memory?: string;
    storage?: string;
    ports?: PortSpec[];
    power_consumption?: number; // watts
    operating_temp?: {
      min: number;
      max: number;
    };
  }

  export interface PortSpec {
    number: number;
    type: string;
    speed: string;
    status: 'up' | 'down' | 'disabled';
    description?: string;
  }

  export interface NetworkAlert extends BaseEntity {
    device_id?: string;
    severity: AlertSeverity;
    type: AlertType;
    title: string;
    description: string;
    status: AlertStatus;
    acknowledged_by?: string;
    acknowledged_at?: string;
    resolved_by?: string;
    resolved_at?: string;
    resolution_notes?: string;
  }

  export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';
  export type AlertType = 
    | 'device_down' 
    | 'high_cpu' 
    | 'high_memory' 
    | 'high_bandwidth' 
    | 'interface_down'
    | 'configuration_change'
    | 'security_event';

  export type AlertStatus = 'open' | 'acknowledged' | 'resolved' | 'closed';
}

// Analytics Module Types
export namespace Analytics {
  export interface MetricData {
    timestamp: string;
    value: number;
    metadata?: Record<string, any>;
  }

  export interface TimeSeriesData {
    metric_name: string;
    data_points: MetricData[];
    aggregation: 'sum' | 'avg' | 'min' | 'max' | 'count';
    interval: string; // e.g., '1m', '5m', '1h', '1d'
  }

  export interface DashboardWidget {
    id: string;
    type: WidgetType;
    title: string;
    config: WidgetConfig;
    position: WidgetPosition;
    refresh_interval?: number; // seconds
  }

  export type WidgetType = 
    | 'line_chart' 
    | 'bar_chart' 
    | 'pie_chart' 
    | 'gauge' 
    | 'counter' 
    | 'table' 
    | 'status_grid';

  export interface WidgetConfig {
    metrics: string[];
    time_range: string;
    filters?: Record<string, any>;
    display_options?: Record<string, any>;
  }

  export interface WidgetPosition {
    x: number;
    y: number;
    width: number;
    height: number;
  }

  export interface Report extends BaseEntity {
    name: string;
    type: ReportType;
    schedule?: ReportSchedule;
    parameters: Record<string, any>;
    format: 'pdf' | 'excel' | 'csv' | 'json';
    recipients: string[];
    last_generated?: string;
    status: 'active' | 'inactive' | 'error';
  }

  export type ReportType = 
    | 'revenue' 
    | 'customer_growth' 
    | 'network_performance' 
    | 'service_usage'
    | 'support_metrics'
    | 'billing_summary';

  export interface ReportSchedule {
    frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
    time: string; // HH:MM format
    day_of_week?: number; // 0-6, Sunday=0
    day_of_month?: number; // 1-31
  }
}

// Support Module Types
export namespace Support {
  export interface Ticket extends BaseEntity {
    ticket_number: string;
    customer_id: string;
    subject: string;
    description: string;
    status: TicketStatus;
    priority: TicketPriority;
    category: TicketCategory;
    assigned_to?: string;
    assigned_at?: string;
    resolved_at?: string;
    closed_at?: string;
    resolution_notes?: string;
    satisfaction_rating?: number; // 1-5
    satisfaction_feedback?: string;
    tags?: string[];
  }

  export type TicketStatus = 'open' | 'in_progress' | 'waiting_customer' | 'resolved' | 'closed';
  export type TicketPriority = 'low' | 'normal' | 'high' | 'urgent';
  export type TicketCategory = 
    | 'technical_issue' 
    | 'billing_inquiry' 
    | 'service_request'
    | 'installation'
    | 'equipment'
    | 'outage'
    | 'complaint';

  export interface TicketMessage extends BaseEntity {
    ticket_id: string;
    author_id: string;
    author_type: 'customer' | 'agent' | 'system';
    content: string;
    is_internal: boolean;
    attachments?: string[];
  }

  export interface KnowledgeBaseArticle extends BaseEntity {
    title: string;
    content: string;
    category: string;
    tags: string[];
    status: 'draft' | 'published' | 'archived';
    author_id: string;
    view_count: number;
    helpful_votes: number;
    unhelpful_votes: number;
  }
}

// Common query parameter types for each service
export interface ServiceQueryParams extends QueryParams {
  include?: string[];
  fields?: string[];
  expand?: string[];
}

// Response wrappers
export type ServiceApiResponse<T> = ApiResponse<T>;
export type ServicePaginatedResponse<T> = PaginatedResponse<T>;