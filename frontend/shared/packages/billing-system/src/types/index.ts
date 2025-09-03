export interface BillingAccount {
  id: string;
  accountNumber: string;
  customerId: string;
  status: 'active' | 'suspended' | 'cancelled' | 'past_due';
  balance: number;
  billingCycle: 'monthly' | 'quarterly' | 'annually';
  nextBillDate: Date;
  billingAddress: Address;
  paymentMethod?: PaymentMethod;
}

export interface Address {
  street: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

export interface PaymentMethod {
  id: string;
  type: 'credit_card' | 'bank_account' | 'paypal' | 'crypto';
  brand?: string;
  last4: string;
  lastFour: string; // Alias for compatibility
  expiryMonth?: number;
  expiryYear?: number;
  isDefault: boolean;
  autoPayEnabled?: boolean;
  status: 'active' | 'expired' | 'invalid';
}

export interface Invoice {
  id: string;
  invoiceNumber: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  accountId?: string;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled' | 'refunded';
  issueDate: Date;
  dueDate: Date;
  paidDate?: Date;
  amount: number;
  tax: number;
  totalAmount: number;
  amountDue: number;
  lineItems: InvoiceLineItem[];
  services?: ServiceItem[];
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface InvoiceLineItem {
  id?: string;
  description?: string;
  quantity?: number;
  unitPrice?: number;
  amount?: number;
  taxRate?: number;
}

export interface ServiceItem {
  name: string;
  amount: number;
}

export interface Payment {
  id: string;
  invoiceId?: string;
  customerId: string;
  customerName: string;
  amount: number;
  refundedAmount: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'refunded';
  method: PaymentMethod;
  gateway: string;
  transactionId?: string;
  processedAt?: Date;
  fees: PaymentFees;
  metadata?: Record<string, any>;
  createdAt: Date;
}

export interface PaymentFees {
  processing: number;
  gateway: number;
}

export interface BillingMetrics {
  totalRevenue: number;
  monthlyRecurring: number;
  monthlyRecurringRevenue: number;
  outstandingAmount: number;
  totalOutstanding: number;
  collectionsRate: number;
  averageRevenuePerUser: number;
  averageInvoiceValue: number;
  paymentFailureRate: number;
  churnRate: number;
  totalInvoices: number;
  paidInvoices: number;
  overdueInvoices: number;
  trends: {
    revenue: number;
    collections: number;
  };
  chartData: {
    revenue: Array<{
      month: string;
      amount: number;
    }>;
    paymentMethods: Array<{
      method: string;
      percentage: number;
      amount: number;
    }>;
  };
  paymentMethodBreakdown: Record<string, number>;
  revenueByPlan: Record<string, number>;
}

export interface BillingStats extends BillingMetrics {
  recentPayments: Payment[];
  upcomingRenewals: Invoice[];
}

export interface Report {
  id: string;
  name: string;
  description: string;
  type: string;
  frequency: string;
  format: string;
  status: 'ready' | 'generating' | 'failed';
  size?: string;
  lastGenerated: Date;
}

export interface PaymentRequest {
  invoiceId: string;
  amount: number;
  paymentMethodId?: string;
  gateway: string;
  metadata?: Record<string, any>;
}

export interface PaymentResponse {
  id: string;
  status: 'success' | 'failed' | 'pending';
  transactionId?: string;
  message?: string;
  payment?: Payment;
}

export interface RefundRequest {
  paymentId: string;
  amount: number;
  reason: string;
}

export interface BillingFilters {
  status?: string;
  dateFrom?: string;
  dateTo?: string;
  customerId?: string;
  paymentMethod?: string;
  gateway?: string;
}

export interface BillingData {
  currentBalance: number;
  nextBillDate: string;
  nextBillAmount: number;
  lastPayment: {
    amount: number;
    date: string;
    method: string;
    confirmationNumber: string;
  };
  paymentMethod: PaymentMethod;
  recentInvoices: Invoice[];
  paymentHistory: Payment[];
}

export type BillingPortalType = 'admin' | 'customer' | 'reseller' | 'management';

export interface UniversalBillingProps {
  portalType: BillingPortalType;
  customerId?: string;
  accountId?: string;
  permissions?: string[];
  theme?: 'light' | 'dark';
  locale?: string;
  currency?: string;
  features?: BillingFeatures;
}

export interface BillingFeatures {
  invoiceGeneration?: boolean;
  paymentProcessing?: boolean;
  refunds?: boolean;
  reporting?: boolean;
  bulkOperations?: boolean;
  automations?: boolean;
  analytics?: boolean;
}

export interface UseBillingSystemOptions extends UniversalBillingProps {
  apiEndpoint?: string;
  websocketUrl?: string;
  pollInterval?: number;
  enableRealtime?: boolean;
  enableAutoRetry?: boolean;
  maxRetryAttempts?: number;
}
