/**
 * Billing Operations Hook
 * Complete ISP billing and financial management
 */

import { useCallback, useState, useEffect } from 'react';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { useRealTimeSync } from './useRealTimeSync';
import { CurrencyUtils } from '../utils/currencyUtils';
import { DateTimeUtils } from '../utils/dateTimeUtils';

// Billing entities
export interface Invoice {
  id: string;
  invoiceNumber: string;
  customerId: string;
  customerName: string;
  status: 'draft' | 'sent' | 'viewed' | 'partial' | 'paid' | 'overdue' | 'cancelled' | 'refunded';
  type: 'monthly' | 'one_time' | 'usage' | 'setup' | 'adjustment';
  
  // Financial details
  subtotal: number;
  taxAmount: number;
  discountAmount: number;
  total: number;
  amountPaid: number;
  amountDue: number;
  currency: string;
  
  // Line items
  lineItems: Array<{
    id: string;
    description: string;
    quantity: number;
    unitPrice: number;
    total: number;
    taxable: boolean;
    serviceId?: string;
    usageDetails?: {
      period: { start: string; end: string };
      units: number;
      rate: number;
      includedUnits?: number;
      overage?: number;
    };
  }>;
  
  // Dates
  issueDate: string;
  dueDate: string;
  servicePeriod: { start: string; end: string };
  paidDate?: string;
  
  // Payment tracking
  payments: Array<{
    id: string;
    amount: number;
    method: string;
    date: string;
    transactionId?: string;
    status: 'pending' | 'completed' | 'failed' | 'refunded';
  }>;
  
  // Communication
  sentAt?: string;
  viewedAt?: string;
  remindersSent: number;
  lastReminderAt?: string;
  
  // Metadata
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  notes?: string;
  tags: string[];
}

export interface PaymentPlan {
  id: string;
  customerId: string;
  invoiceIds: string[];
  totalAmount: number;
  remainingAmount: number;
  currency: string;
  
  status: 'active' | 'completed' | 'defaulted' | 'cancelled';
  
  installments: Array<{
    id: string;
    amount: number;
    dueDate: string;
    status: 'pending' | 'paid' | 'overdue' | 'failed';
    paidDate?: string;
    paidAmount?: number;
    paymentId?: string;
  }>;
  
  setupFee?: number;
  interestRate?: number;
  
  createdAt: string;
  approvedBy: string;
  terms: string;
}

export interface BillingCycle {
  id: string;
  name: string;
  frequency: 'monthly' | 'quarterly' | 'semi_annually' | 'annually';
  cutoffDay: number; // 1-28
  dueTerms: number; // days after invoice
  isDefault: boolean;
  
  customers: Array<{
    customerId: string;
    nextBillDate: string;
    lastInvoiceDate?: string;
  }>;
}

export interface UsageRecord {
  id: string;
  customerId: string;
  serviceId: string;
  period: { start: string; end: string };
  
  usage: {
    download: number; // bytes
    upload: number; // bytes
    total: number; // bytes
    peakUsage: number; // bytes
    peakTime: string;
  };
  
  billing: {
    includedData: number; // bytes
    overageData: number; // bytes
    overageRate: number; // per GB
    overageCharge: number;
  };
  
  processed: boolean;
  processedAt?: string;
  invoiceId?: string;
}

export interface TaxConfiguration {
  id: string;
  name: string;
  type: 'percentage' | 'fixed';
  rate: number;
  
  applicableServices: string[];
  exemptServices: string[];
  
  jurisdiction: {
    country: string;
    state?: string;
    county?: string;
    city?: string;
  };
  
  effective: { start: string; end?: string };
  isActive: boolean;
}

export interface BillingAnalytics {
  period: { start: string; end: string };
  
  revenue: {
    total: number;
    recurring: number;
    oneTime: number;
    usage: number;
    byService: Array<{ serviceType: string; amount: number }>;
    growth: number; // percentage
  };
  
  invoices: {
    total: number;
    sent: number;
    paid: number;
    overdue: number;
    averageValue: number;
    paymentTime: number; // average days to pay
  };
  
  customers: {
    total: number;
    active: number;
    new: number;
    churned: number;
    arpu: number; // average revenue per user
    ltv: number; // lifetime value
  };
  
  collections: {
    collectionRate: number; // percentage
    overdueAmount: number;
    averageOverdueDays: number;
    writeOffs: number;
  };
}

export function useBillingOperations() {
  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'Billing Operations',
    enableRetry: true,
    maxRetries: 2
  });
  const { emit, subscribe } = useRealTimeSync();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [paymentPlans, setPaymentPlans] = useState<PaymentPlan[]>([]);
  const [billingCycles, setBillingCycles] = useState<BillingCycle[]>([]);
  const [usageRecords, setUsageRecords] = useState<UsageRecord[]>([]);
  const [taxConfig, setTaxConfig] = useState<TaxConfiguration[]>([]);
  const [analytics, setAnalytics] = useState<BillingAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  // Load invoices with filtering
  const loadInvoices = useCallback(async (filters: {
    status?: Invoice['status'][];
    type?: Invoice['type'][];
    customerId?: string;
    dateFrom?: string;
    dateTo?: string;
    overdue?: boolean;
  } = {}): Promise<void> => {
    if (!currentTenant?.tenant?.id) return;

    return withErrorHandling(async () => {
      setIsLoading(true);
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/invoices', {
        params: {
          tenantId: currentTenant.tenant.id,
          ...filters
        }
      });

      const invoiceData = response.data.invoices || [];
      
      // Enhance invoices with computed fields
      const enhancedInvoices = invoiceData.map((invoice: Invoice) => ({
        ...invoice,
        isOverdue: new Date(invoice.dueDate) < new Date() && invoice.amountDue > 0,
        daysPastDue: calculateDaysPastDue(invoice.dueDate, invoice.amountDue),
        paymentStatus: getPaymentStatus(invoice)
      }));

      setInvoices(enhancedInvoices);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Generate invoice
  const generateInvoice = useCallback(async (invoiceData: {
    customerId: string;
    type: Invoice['type'];
    servicePeriod?: { start: string; end: string };
    lineItems: Omit<Invoice['lineItems'][0], 'id'>[];
    dueTerms?: number;
    notes?: string;
    tags?: string[];
  }): Promise<string | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      // Revenue-critical validation
      const totalAmount = invoiceData.lineItems.reduce((sum, item) => sum + item.total, 0);
      if (totalAmount <= 0) {
        throw new Error('Invoice total must be greater than zero');
      }

      const response = await apiClient.request('/api/v1/billing/invoices', {
        method: 'POST',
        body: {
          ...invoiceData,
          tenantId: currentTenant?.tenant?.id,
          createdBy: user?.id,
          currency: currentTenant?.tenant?.defaultCurrency || 'USD',
          issueDate: new Date().toISOString(),
          dueDate: DateTimeUtils.addDays(new Date(), invoiceData.dueTerms || 30).toISOString()
        }
      });

      const newInvoice = response.data.invoice;
      setInvoices(prev => [newInvoice, ...prev]);
      
      emit('billing:invoice_generated', { 
        invoiceId: newInvoice.id, 
        customerId: newInvoice.customerId,
        amount: newInvoice.total 
      });
      
      return newInvoice.id;
    });
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Process usage billing
  const processUsageBilling = useCallback(async (
    customerId: string,
    period: { start: string; end: string }
  ): Promise<{ invoiceId?: string; amount: number; usageRecords: number }> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/usage/process', {
        method: 'POST',
        body: {
          customerId,
          period,
          tenantId: currentTenant?.tenant?.id,
          processedBy: user?.id
        }
      });

      const result = response.data;
      
      // Update local state if new invoice was generated
      if (result.invoice) {
        setInvoices(prev => [result.invoice, ...prev]);
      }
      
      // Update usage records
      if (result.usageRecords) {
        setUsageRecords(prev => [...prev, ...result.usageRecords]);
      }

      emit('billing:usage_processed', { customerId, period, amount: result.amount });
      
      return {
        invoiceId: result.invoice?.id,
        amount: result.amount || 0,
        usageRecords: result.usageRecords?.length || 0
      };
    }) || { amount: 0, usageRecords: 0 };
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Record payment
  const recordPayment = useCallback(async (
    invoiceId: string,
    paymentData: {
      amount: number;
      method: string;
      transactionId?: string;
      notes?: string;
    }
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      // Revenue-critical validation
      if (paymentData.amount <= 0) {
        throw new Error('Payment amount must be greater than zero');
      }

      const response = await apiClient.request(`/api/v1/billing/invoices/${invoiceId}/payments`, {
        method: 'POST',
        body: {
          ...paymentData,
          recordedBy: user?.id,
          recordedAt: new Date().toISOString()
        }
      });

      const payment = response.data.payment;
      const updatedInvoice = response.data.invoice;

      // Update local state
      setInvoices(prev => prev.map(invoice =>
        invoice.id === invoiceId ? updatedInvoice : invoice
      ));

      if (selectedInvoice?.id === invoiceId) {
        setSelectedInvoice(updatedInvoice);
      }

      emit('billing:payment_recorded', { 
        invoiceId, 
        paymentId: payment.id, 
        amount: payment.amount,
        customerId: updatedInvoice.customerId
      });

      return true;
    }) || false;
  }, [user?.id, selectedInvoice?.id, withErrorHandling, emit]);

  // Create payment plan
  const createPaymentPlan = useCallback(async (planData: {
    customerId: string;
    invoiceIds: string[];
    installmentCount: number;
    setupFee?: number;
    interestRate?: number;
    terms: string;
  }): Promise<string | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/payment-plans', {
        method: 'POST',
        body: {
          ...planData,
          tenantId: currentTenant?.tenant?.id,
          approvedBy: user?.id
        }
      });

      const newPlan = response.data.paymentPlan;
      setPaymentPlans(prev => [newPlan, ...prev]);
      
      emit('billing:payment_plan_created', { 
        planId: newPlan.id,
        customerId: newPlan.customerId,
        amount: newPlan.totalAmount
      });
      
      return newPlan.id;
    });
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Process payment plan installment
  const processInstallment = useCallback(async (
    paymentPlanId: string,
    installmentId: string,
    paymentData: {
      amount: number;
      method: string;
      transactionId?: string;
    }
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/billing/payment-plans/${paymentPlanId}/installments/${installmentId}/pay`, {
        method: 'POST',
        body: {
          ...paymentData,
          processedBy: user?.id
        }
      });

      // Reload payment plans to reflect the change
      const response = await apiClient.request(`/api/v1/billing/payment-plans/${paymentPlanId}`);
      const updatedPlan = response.data.paymentPlan;
      
      setPaymentPlans(prev => prev.map(plan =>
        plan.id === paymentPlanId ? updatedPlan : plan
      ));

      emit('billing:installment_paid', { paymentPlanId, installmentId });
      return true;
    }) || false;
  }, [user?.id, withErrorHandling, emit]);

  // Load usage records
  const loadUsageRecords = useCallback(async (filters: {
    customerId?: string;
    serviceId?: string;
    period?: { start: string; end: string };
    processed?: boolean;
  } = {}): Promise<void> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/usage', {
        params: {
          tenantId: currentTenant?.tenant?.id,
          ...filters
        }
      });

      setUsageRecords(response.data.usageRecords || []);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Load tax configuration
  const loadTaxConfiguration = useCallback(async (): Promise<void> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/tax-config', {
        params: {
          tenantId: currentTenant?.tenant?.id
        }
      });

      setTaxConfig(response.data.taxConfiguration || []);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Calculate tax for invoice
  const calculateTax = useCallback(async (
    lineItems: Invoice['lineItems'],
    customerLocation: { country: string; state?: string; city?: string }
  ): Promise<{ taxAmount: number; taxBreakdown: Array<{ name: string; rate: number; amount: number }> }> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/tax/calculate', {
        method: 'POST',
        body: {
          lineItems,
          customerLocation,
          tenantId: currentTenant?.tenant?.id
        }
      });

      return response.data;
    }) || { taxAmount: 0, taxBreakdown: [] };
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Load billing analytics
  const loadAnalytics = useCallback(async (
    period: { start: string; end: string }
  ): Promise<void> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/billing/analytics', {
        params: {
          tenantId: currentTenant?.tenant?.id,
          startDate: period.start,
          endDate: period.end
        }
      });

      setAnalytics(response.data.analytics);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Send invoice
  const sendInvoice = useCallback(async (
    invoiceId: string,
    deliveryMethod: 'email' | 'mail' | 'both' = 'email'
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/billing/invoices/${invoiceId}/send`, {
        method: 'POST',
        body: {
          deliveryMethod,
          sentBy: user?.id
        }
      });

      // Update local state
      setInvoices(prev => prev.map(invoice =>
        invoice.id === invoiceId
          ? { ...invoice, status: 'sent', sentAt: new Date().toISOString() }
          : invoice
      ));

      emit('billing:invoice_sent', { invoiceId, deliveryMethod });
      return true;
    }) || false;
  }, [user?.id, withErrorHandling, emit]);

  // Send payment reminder
  const sendPaymentReminder = useCallback(async (invoiceId: string): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/billing/invoices/${invoiceId}/remind`, {
        method: 'POST',
        body: {
          sentBy: user?.id
        }
      });

      // Update local state
      setInvoices(prev => prev.map(invoice =>
        invoice.id === invoiceId
          ? { 
              ...invoice, 
              remindersSent: invoice.remindersSent + 1,
              lastReminderAt: new Date().toISOString() 
            }
          : invoice
      ));

      emit('billing:reminder_sent', { invoiceId });
      return true;
    }) || false;
  }, [user?.id, withErrorHandling, emit]);

  // Format currency amounts
  const formatAmount = useCallback((amount: number, currency = 'USD'): string => {
    return CurrencyUtils.format(amount, currency as any);
  }, []);

  // Real-time billing updates
  useEffect(() => {
    return subscribe('billing:*', (event) => {
      switch (event.type) {
        case 'billing:payment_received':
          if (event.data && typeof event.data === 'object') {
            const { invoiceId } = event.data as any;
            // Refresh the specific invoice
            loadInvoices();
          }
          break;
        case 'billing:invoice_overdue':
          if (event.data && typeof event.data === 'object') {
            const { invoiceId } = event.data as any;
            setInvoices(prev => prev.map(invoice =>
              invoice.id === invoiceId ? { ...invoice, status: 'overdue' } : invoice
            ));
          }
          break;
      }
    });
  }, [subscribe, loadInvoices]);

  // Load initial data
  useEffect(() => {
    if (currentTenant?.tenant?.id) {
      loadInvoices();
      loadTaxConfiguration();
      
      // Load current month analytics
      const now = new Date();
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      loadAnalytics({
        start: startOfMonth.toISOString(),
        end: now.toISOString()
      });
    }
  }, [currentTenant?.tenant?.id, loadInvoices, loadTaxConfiguration, loadAnalytics]);

  return {
    // State
    invoices,
    paymentPlans,
    billingCycles,
    usageRecords,
    taxConfig,
    analytics,
    isLoading,
    selectedInvoice,

    // Invoice operations
    loadInvoices,
    generateInvoice,
    sendInvoice,
    sendPaymentReminder,
    recordPayment,
    setSelectedInvoice,

    // Usage billing
    processUsageBilling,
    loadUsageRecords,

    // Payment plans
    createPaymentPlan,
    processInstallment,

    // Tax operations
    loadTaxConfiguration,
    calculateTax,

    // Analytics
    loadAnalytics,

    // Utilities
    formatAmount,

    // Computed values
    totalRevenue: analytics?.revenue.total || 0,
    monthlyRecurringRevenue: analytics?.revenue.recurring || 0,
    overdueInvoices: invoices.filter(i => i.status === 'overdue'),
    pendingInvoices: invoices.filter(i => ['draft', 'sent'].includes(i.status)),
    paidInvoices: invoices.filter(i => i.status === 'paid'),
    
    collectionMetrics: analytics ? {
      collectionRate: analytics.collections.collectionRate,
      overdueAmount: analytics.collections.overdueAmount,
      averagePaymentTime: analytics.invoices.paymentTime
    } : null,

    // Revenue breakdown
    revenueByType: analytics ? [
      { type: 'Recurring', amount: analytics.revenue.recurring },
      { type: 'One-time', amount: analytics.revenue.oneTime },
      { type: 'Usage', amount: analytics.revenue.usage }
    ] : []
  };
}

// Helper functions
function calculateDaysPastDue(dueDate: string, amountDue: number): number | undefined {
  if (amountDue <= 0) return undefined;
  
  const due = new Date(dueDate);
  const now = new Date();
  const diffTime = now.getTime() - due.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  return diffDays > 0 ? diffDays : undefined;
}

function getPaymentStatus(invoice: Invoice): 'paid' | 'partial' | 'unpaid' | 'overdue' {
  if (invoice.amountPaid >= invoice.total) return 'paid';
  if (invoice.amountPaid > 0) return 'partial';
  if (new Date(invoice.dueDate) < new Date()) return 'overdue';
  return 'unpaid';
}

export type { 
  Invoice, 
  PaymentPlan, 
  BillingCycle, 
  UsageRecord, 
  TaxConfiguration, 
  BillingAnalytics 
};