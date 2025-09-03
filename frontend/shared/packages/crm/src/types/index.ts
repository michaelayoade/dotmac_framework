// ========================================
// CORE CRM TYPES
// ========================================

export interface Address {
  id?: string;
  type: 'home' | 'business' | 'billing' | 'service' | 'other';
  street1: string;
  street2?: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
  isPrimary: boolean;
  coordinates?: [number, number];
  serviceability?: 'serviceable' | 'planned' | 'not_serviceable';
}

export interface ContactMethod {
  id: string;
  type: 'email' | 'phone' | 'mobile' | 'fax' | 'website' | 'social';
  value: string;
  label?: string;
  isPrimary: boolean;
  isVerified: boolean;
  preferences: {
    allowMarketing: boolean;
    allowSMS: boolean;
    allowCalls: boolean;
    preferredTime?: 'morning' | 'afternoon' | 'evening';
  };
}

export interface CustomField {
  id: string;
  name: string;
  value: any;
  type: 'text' | 'number' | 'date' | 'boolean' | 'select' | 'multiselect';
  isRequired: boolean;
  category: string;
}

// ========================================
// CUSTOMER TYPES
// ========================================

export type CustomerStatus =
  | 'prospect'
  | 'active'
  | 'inactive'
  | 'suspended'
  | 'churned'
  | 'cancelled';

export type CustomerType = 'residential' | 'business' | 'enterprise';

export type CustomerSegment = 'premium' | 'standard' | 'budget' | 'enterprise' | 'government';

export interface CustomerAccount {
  id: string;
  accountNumber: string;
  status: CustomerStatus;
  type: CustomerType;
  segment: CustomerSegment;

  // Identity
  firstName: string;
  lastName: string;
  companyName?: string;
  displayName: string;

  // Contact Information
  addresses: Address[];
  contactMethods: ContactMethod[];

  // Business Information
  taxId?: string;
  businessType?: string;
  industry?: string;

  // Account Details
  creditScore?: number;
  creditLimit?: number;
  paymentTerms: string;
  billingCycle: string;

  // Relationship
  accountManagerId?: string;
  salesRepId?: string;
  technicianId?: string;

  // Services
  activeServices: CustomerService[];

  // Financial
  totalRevenue: number;
  monthlyRevenue: number;
  lifetimeValue: number;
  outstandingBalance: number;

  // Preferences
  communicationPreferences: {
    preferredMethod: 'email' | 'phone' | 'sms' | 'mail';
    language: string;
    timezone: string;
    marketingOptIn: boolean;
  };

  // Custom Fields
  customFields: CustomField[];

  // Metadata
  source: string;
  referredBy?: string;
  createdAt: string;
  updatedAt: string;
  lastContactDate?: string;
  lastPurchaseDate?: string;

  // Sync
  syncStatus: 'synced' | 'pending' | 'error';
  tenantId: string;
}

export interface CustomerService {
  id: string;
  serviceType: string;
  planName: string;
  status: 'active' | 'suspended' | 'cancelled' | 'pending';
  installDate?: string;
  activationDate?: string;
  cancellationDate?: string;
  monthlyRate: number;
  equipment: ServiceEquipment[];
  address: Address;
  technicalDetails: Record<string, any>;
}

export interface ServiceEquipment {
  id: string;
  type: string;
  model: string;
  serialNumber: string;
  macAddress?: string;
  installDate: string;
  warrantyExpires?: string;
  status: 'active' | 'inactive' | 'replaced' | 'returned';
}

// ========================================
// LEAD TYPES
// ========================================

export type LeadStatus =
  | 'new'
  | 'contacted'
  | 'qualified'
  | 'proposal'
  | 'negotiation'
  | 'closed_won'
  | 'closed_lost';

export type LeadSource =
  | 'website'
  | 'referral'
  | 'advertising'
  | 'social_media'
  | 'cold_call'
  | 'trade_show'
  | 'partner';

export type LeadPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface Lead {
  id: string;
  status: LeadStatus;
  source: LeadSource;
  priority: LeadPriority;

  // Contact Information
  firstName: string;
  lastName: string;
  companyName?: string;
  email: string;
  phone?: string;

  // Address
  address: Partial<Address>;

  // Lead Details
  interestedServices: string[];
  budget?: number;
  timeline?: string;
  notes: string;

  // Assignment
  assignedTo?: string;
  assignedDate?: string;

  // Tracking
  score: number; // 0-100
  lastContactDate?: string;
  nextFollowUpDate?: string;

  // Conversion
  convertedToCustomerId?: string;
  convertedDate?: string;

  // Custom Fields
  customFields: CustomField[];

  // Metadata
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  tenantId: string;
  syncStatus: 'synced' | 'pending' | 'error';
}

// ========================================
// COMMUNICATION TYPES
// ========================================

export type CommunicationType =
  | 'email'
  | 'phone_call'
  | 'sms'
  | 'meeting'
  | 'note'
  | 'support_ticket'
  | 'chat';

export type CommunicationDirection = 'inbound' | 'outbound';

export interface Communication {
  id: string;
  type: CommunicationType;
  direction: CommunicationDirection;

  // Related Records
  customerId?: string;
  leadId?: string;
  contactId?: string;
  supportTicketId?: string;

  // Content
  subject: string;
  content: string;
  summary?: string;

  // Participants
  fromAddress: string;
  toAddresses: string[];
  ccAddresses?: string[];
  bccAddresses?: string[];

  // Metadata
  timestamp: string;
  duration?: number; // in seconds for calls/meetings
  recordingUrl?: string;
  attachments: CommunicationAttachment[];

  // Status
  status: 'sent' | 'delivered' | 'read' | 'replied' | 'failed';

  // Tracking
  openedAt?: string;
  clickedAt?: string;
  repliedAt?: string;

  // Analytics
  sentiment?: 'positive' | 'neutral' | 'negative';
  topics: string[];
  tags: string[];

  // User
  userId: string;
  userName: string;

  // Metadata
  createdAt: string;
  tenantId: string;
  syncStatus: 'synced' | 'pending' | 'error';
}

export interface CommunicationAttachment {
  id: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  url: string;
  thumbnailUrl?: string;
}

// ========================================
// SUPPORT TYPES
// ========================================

export type TicketStatus =
  | 'open'
  | 'in_progress'
  | 'waiting_customer'
  | 'waiting_vendor'
  | 'resolved'
  | 'closed';

export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

export type TicketCategory =
  | 'technical'
  | 'billing'
  | 'sales'
  | 'general'
  | 'complaint'
  | 'feature_request';

export interface SupportTicket {
  id: string;
  ticketNumber: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;

  // Content
  subject: string;
  description: string;
  resolution?: string;

  // Related Records
  customerId: string;
  relatedTickets: string[];

  // Assignment
  assignedTo?: string;
  assignedDate?: string;
  assignedBy?: string;

  // SLA
  slaTarget?: string;
  slaBreached: boolean;
  firstResponseTime?: number;
  resolutionTime?: number;

  // Communication
  communications: Communication[];

  // Metadata
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  closedAt?: string;
  createdBy: string;
  tenantId: string;

  // Sync
  syncStatus: 'synced' | 'pending' | 'error';
}

// ========================================
// ANALYTICS TYPES
// ========================================

export interface CustomerMetrics {
  totalCustomers: number;
  activeCustomers: number;
  newCustomers: number;
  churnedCustomers: number;
  churnRate: number;
  lifetimeValue: number;
  averageRevenue: number;
  customersBySegment: Record<CustomerSegment, number>;
  customersByStatus: Record<CustomerStatus, number>;
}

export interface LeadMetrics {
  totalLeads: number;
  newLeads: number;
  qualifiedLeads: number;
  convertedLeads: number;
  conversionRate: number;
  averageScore: number;
  leadsBySource: Record<LeadSource, number>;
  leadsByStatus: Record<LeadStatus, number>;
}

export interface CommunicationMetrics {
  totalCommunications: number;
  responseRate: number;
  averageResponseTime: number;
  communicationsByType: Record<CommunicationType, number>;
  sentimentAnalysis: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

export interface SupportMetrics {
  totalTickets: number;
  openTickets: number;
  resolvedTickets: number;
  averageResolutionTime: number;
  firstResponseTime: number;
  satisfactionRating: number;
  ticketsByCategory: Record<TicketCategory, number>;
  ticketsByPriority: Record<TicketPriority, number>;
  slaCompliance: number;
}

export interface CRMDashboardMetrics {
  customer: CustomerMetrics;
  lead: LeadMetrics;
  communication: CommunicationMetrics;
  support: SupportMetrics;
  timeRange: {
    start: string;
    end: string;
  };
  lastUpdated: string;
}

// ========================================
// FILTER AND QUERY TYPES
// ========================================

export interface CustomerFilter {
  status?: CustomerStatus[];
  type?: CustomerType[];
  segment?: CustomerSegment[];
  source?: string[];
  accountManager?: string[];
  salesRep?: string[];
  createdAfter?: string;
  createdBefore?: string;
  lastContactAfter?: string;
  lastContactBefore?: string;
  revenueMin?: number;
  revenueMax?: number;
  tags?: string[];
  search?: string;
}

export interface LeadFilter {
  status?: LeadStatus[];
  source?: LeadSource[];
  priority?: LeadPriority[];
  assignedTo?: string[];
  createdAfter?: string;
  createdBefore?: string;
  scoreMin?: number;
  scoreMax?: number;
  interestedServices?: string[];
  search?: string;
}

export interface CommunicationFilter {
  type?: CommunicationType[];
  direction?: CommunicationDirection[];
  customerId?: string;
  leadId?: string;
  dateAfter?: string;
  dateBefore?: string;
  userId?: string;
  sentiment?: ('positive' | 'neutral' | 'negative')[];
  topics?: string[];
  search?: string;
}

export interface SupportTicketFilter {
  status?: TicketStatus[];
  priority?: TicketPriority[];
  category?: TicketCategory[];
  assignedTo?: string[];
  customerId?: string;
  createdAfter?: string;
  createdBefore?: string;
  slaBreached?: boolean;
  search?: string;
}
