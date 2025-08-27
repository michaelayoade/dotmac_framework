// Shared billing type definitions for Admin Portal

export type InvoiceStatus = 'paid' | 'pending' | 'overdue' | 'cancelled';
export type PaymentStatus = 'completed' | 'pending' | 'failed' | 'refunded';
export type ReportStatus = 'ready' | 'generating' | 'failed';
export type ServiceType = 'enterprise' | 'business' | 'residential';
export type TicketStatus = 'open' | 'pending' | 'in_progress' | 'resolved' | 'closed';

export interface Invoice {
  id: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  customerType: string;
  serviceAddress: string;
  amount: number;
  tax: number;
  total: number;
  currency: string;
  status: InvoiceStatus;
  dueDate: string;
  paidDate: string | null;
  paymentMethod: string;
  services: Array<{
    name: string;
    amount: number;
    type: string;
    speed?: { download: number; upload: number };
    technology?: string;
    unitCount?: number;
  }>;
  billingPeriod: {
    start: string;
    end: string;
  };
  createdAt: string;
  updatedAt: string;
  tags: string[];
  territory: string;
  technician: string;
}

export interface Payment {
  id: string;
  invoiceId: string | null;
  customerId: string;
  customerName: string;
  amount: number;
  currency: string;
  method: string;
  status: PaymentStatus;
  transactionId: string;
  gateway: string;
  processedAt: string | null;
  fees: { processing: number; gateway: number };
  metadata: PaymentMetadata;
}

export interface Report {
  id: string;
  name: string;
  type: string;
  description: string;
  lastGenerated: string;
  frequency: string;
  status: ReportStatus;
  format: string;
  size: string | null;
}

export type ServiceStatus = 'active' | 'inactive' | 'deprecated' | 'draft';

export interface Service {
  id: string;
  name: string;
  category: string;
  type: ServiceType;
  status: ServiceStatus;
  description: string;
  pricing: {
    monthly: number;
    setup: number;
    currency: string;
  };
  specifications: ServiceSpecifications;
  availability: {
    regions: string[];
    technologies: string[];
    maxInstallations: number;
  };
  metadata: {
    createdAt: string;
    updatedAt: string;
    version: string;
  };
  tags: string[];
}

export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface Ticket {
  id: string;
  title: string;
  description: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: string;
  assigneeId: string;
  assigneeName: string;
  assigneeAvatar: string;
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
  tags: string[];
  territory: string;
  serviceType: string;
  satisfaction: number | null;
}

// Additional interfaces for proper typing
export interface ServiceSpecifications {
  bandwidth?: {
    download: number;
    upload: number;
    unit: 'Mbps' | 'Gbps';
  };
  technology?: string;
  equipment?: string[];
  installationType?: 'standard' | 'custom' | 'self-install';
  contractLength?: number;
  dataLimits?: {
    monthly: number;
    unit: 'GB' | 'TB' | 'unlimited';
  };
}

export interface PaymentMetadata {
  ipAddress?: string;
  userAgent?: string;
  referenceNumber?: string;
  processorResponse?: string;
  riskScore?: number;
  billingAddress?: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  // Allow payment method specific metadata
  last4?: string;
  brand?: string;
  bank_name?: string;
  account_last4?: string;
  [key: string]: any; // Flexible for additional metadata
}

export interface Metrics {
  totalRevenue: number;
  monthlyRecurring: number;
  outstandingAmount: number;
  collectionsRate: number;
  averageInvoiceValue: number;
  paymentFailureRate: number;
  trends: MetricsTrends;
  chartData: ChartsData;
}

export interface MetricsTrends {
  revenue: number;
  collections: number;
  failures: number;
  customers?: number;
}

export interface ChartsData {
  revenue: RevenueDataPoint[];
  collections: CollectionDataPoint[];
  paymentMethods: PaymentMethodDataPoint[];
}

export interface RevenueDataPoint {
  month: string;
  amount: number;
  target?: number;
  previousYear?: number;
}

export interface CollectionDataPoint {
  month: string;
  rate: number;
  target?: number;
}

export interface PaymentMethodDataPoint {
  method: string;
  percentage: number;
  amount: number;
  transactionCount?: number;
}

// API Response types
export interface BillingApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  errors?: string[];
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// Form data types
export interface CreateInvoiceData {
  customerId: string;
  amount: number;
  tax: number;
  dueDate: string;
  description?: string;
  services: Array<{
    name: string;
    amount: number;
    type: string;
  }>;
}

export interface ProcessPaymentData {
  invoiceId?: string;
  customerId: string;
  amount: number;
  method: string;
  transactionId: string;
}

// Filter and search types
export interface BillingFilters {
  status?: InvoiceStatus[];
  dateRange?: {
    start: string;
    end: string;
  };
  customerId?: string;
  amountRange?: {
    min: number;
    max: number;
  };
  paymentMethod?: string[];
}