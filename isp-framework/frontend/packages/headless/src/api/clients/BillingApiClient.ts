/**
 * Billing API Client - Real Implementation Aligned with Backend
 * 
 * Connects to FastAPI backend billing endpoints with AI-first validation
 * and revenue protection features.
 */

import { BaseApiClient, RequestConfig } from './BaseApiClient';
import { 
  Invoice, 
  InvoiceCreate, 
  InvoiceUpdate,
  InvoiceListParams,
  InvoiceCalculationResult,
  Payment, 
  PaymentCreate,
  PaymentRequest,
  CreditNote, 
  CreditNoteCreate,
  CreditNoteRequest,
  Receipt,
  ReceiptCreate,
  TaxRate,
  TaxRateCreate,
  Subscription,
  SubscriptionCreate,
  SubscriptionUpdate,
  BillingReport,
  InvoiceStatus,
  PaymentStatus,
  PaymentMethod,
  PaginatedResponse,
  ApiResponse
} from '../types/billing';

export class BillingApiClient extends BaseApiClient {
  constructor(baseURL: string, defaultHeaders: Record<string, string> = {}) {
    super(baseURL, { ...defaultHeaders, 'X-Module': 'billing' }, 'Billing API');
  }

  // AI-First Validation Methods for Revenue Protection
  private validateRevenueCriticalOperation(amount: number, operation: string): void {
    if (amount <= 0) {
      throw new Error(`Revenue-critical validation failed: ${operation} amount must be positive, got ${amount}`);
    }
    
    // AI Safety: Prevent unrealistic amounts that could indicate data corruption
    if (amount > 1000000) { // $1M limit - configurable per ISP
      throw new Error(`Revenue-critical validation failed: ${operation} amount ${amount} exceeds safety threshold`);
    }
  }

  private validateTaxCalculation(subtotal: number, taxRate: number, taxAmount: number): void {
    const expectedTax = subtotal * taxRate;
    const tolerance = 0.01; // 1 cent tolerance for floating point precision
    
    if (Math.abs(taxAmount - expectedTax) > tolerance) {
      throw new Error(`Tax calculation validation failed: Expected ${expectedTax.toFixed(2)}, got ${taxAmount.toFixed(2)}`);
    }
  }

  // Invoice Operations
  async listInvoices(params?: InvoiceListParams, config?: RequestConfig): Promise<Invoice[]> {
    return this.get<Invoice[]>('/invoices', { ...config, params });
  }

  async createInvoice(invoiceData: InvoiceCreate, config?: RequestConfig): Promise<Invoice> {
    // AI-First: Validate revenue-critical data before sending
    const totalAmount = invoiceData.line_items?.reduce((sum, item) => {
      const itemTotal = item.quantity * item.unit_price;
      this.validateRevenueCriticalOperation(itemTotal, 'Line item');
      return sum + itemTotal;
    }, 0) || 0;

    this.validateRevenueCriticalOperation(totalAmount, 'Invoice total');

    return this.post<Invoice>('/invoices', invoiceData, config);
  }

  async getInvoice(invoiceId: string, config?: RequestConfig): Promise<Invoice> {
    return this.get<Invoice>(`/invoices/${invoiceId}`, config);
  }

  async getInvoiceByNumber(invoiceNumber: string, config?: RequestConfig): Promise<Invoice> {
    return this.get<Invoice>(`/invoices/by-number/${invoiceNumber}`, config);
  }

  async updateInvoice(invoiceId: string, updates: InvoiceUpdate, config?: RequestConfig): Promise<Invoice> {
    return this.patch<Invoice>(`/invoices/${invoiceId}`, updates, config);
  }

  async sendInvoice(invoiceId: string, config?: RequestConfig): Promise<Invoice> {
    return this.post<Invoice>(`/invoices/${invoiceId}/send`, {}, config);
  }

  async voidInvoice(invoiceId: string, reason: string, config?: RequestConfig): Promise<Invoice> {
    return this.post<Invoice>(`/invoices/${invoiceId}/void`, {}, { 
      ...config, 
      params: { reason } 
    });
  }

  // Payment Operations with Revenue Protection
  async listPayments(params?: {
    customer_id?: string;
    invoice_id?: string;
    status?: PaymentStatus;
    payment_method?: PaymentMethod;
    skip?: number;
    limit?: number;
  }, config?: RequestConfig): Promise<Payment[]> {
    return this.get<Payment[]>('/payments', { ...config, params });
  }

  async processPayment(paymentData: PaymentCreate, config?: RequestConfig): Promise<Payment> {
    // AI-First: Critical revenue validation
    this.validateRevenueCriticalOperation(paymentData.amount, 'Payment');

    return this.post<Payment>('/payments', paymentData, config);
  }

  async getPayment(paymentId: string, config?: RequestConfig): Promise<Payment> {
    return this.get<Payment>(`/payments/${paymentId}`, config);
  }

  // Subscription Operations
  async createSubscription(subscriptionData: SubscriptionCreate, config?: RequestConfig): Promise<Subscription> {
    this.validateRevenueCriticalOperation(subscriptionData.amount, 'Subscription');
    
    return this.post<Subscription>('/subscriptions', subscriptionData, config);
  }

  async getSubscription(subscriptionId: string, config?: RequestConfig): Promise<Subscription> {
    return this.get<Subscription>(`/subscriptions/${subscriptionId}`, config);
  }

  async updateSubscription(subscriptionId: string, updates: SubscriptionUpdate, config?: RequestConfig): Promise<Subscription> {
    if (updates.amount) {
      this.validateRevenueCriticalOperation(updates.amount, 'Subscription update');
    }
    
    return this.patch<Subscription>(`/subscriptions/${subscriptionId}`, updates, config);
  }

  async cancelSubscription(subscriptionId: string, cancelDate?: string, config?: RequestConfig): Promise<Subscription> {
    return this.post<Subscription>(`/subscriptions/${subscriptionId}/cancel`, {}, {
      ...config,
      params: cancelDate ? { cancel_date: cancelDate } : undefined
    });
  }

  // Credit Note Operations
  async createCreditNote(creditNoteData: CreditNoteCreate, config?: RequestConfig): Promise<CreditNote> {
    this.validateRevenueCriticalOperation(creditNoteData.amount, 'Credit note');
    
    return this.post<CreditNote>('/credit-notes', creditNoteData, config);
  }

  // Customer-specific Operations
  async getCustomerInvoices(customerId: string, params?: {
    status?: InvoiceStatus;
    skip?: number;
    limit?: number;
  }, config?: RequestConfig): Promise<Invoice[]> {
    return this.get<Invoice[]>(`/customers/${customerId}/invoices`, { ...config, params });
  }

  async getCustomerPayments(customerId: string, params?: {
    status?: PaymentStatus;
    skip?: number;
    limit?: number;
  }, config?: RequestConfig): Promise<Payment[]> {
    return this.get<Payment[]>(`/customers/${customerId}/payments`, { ...config, params });
  }

  // Billing Automation
  async processRecurringBilling(config?: RequestConfig): Promise<any> {
    return this.post('/billing/process-recurring', {}, config);
  }

  // Tax Rate Management
  async createTaxRate(taxRateData: TaxRateCreate, config?: RequestConfig): Promise<TaxRate> {
    // Validate tax rate is reasonable
    if (taxRateData.rate < 0 || taxRateData.rate > 1) {
      throw new Error(`Tax rate validation failed: Rate ${taxRateData.rate} must be between 0 and 1`);
    }
    
    return this.post<TaxRate>('/tax-rates', taxRateData, config);
  }

  async getTaxRates(config?: RequestConfig): Promise<TaxRate[]> {
    return this.get<TaxRate[]>('/tax-rates', config);
  }

  // Receipt Operations
  async createReceipt(receiptData: ReceiptCreate, config?: RequestConfig): Promise<Receipt> {
    return this.post<Receipt>('/receipts', receiptData, config);
  }

  // Advanced Calculations with AI Validation
  async calculateInvoiceTotal(
    lineItems: Array<{
      quantity: number;
      unit_price: number;
      tax_rate?: number;
      discount_rate?: number;
    }>,
    config?: RequestConfig
  ): Promise<InvoiceCalculationResult> {
    // Client-side validation before server calculation
    let subtotal = 0;
    let taxTotal = 0;
    let discountTotal = 0;

    for (const item of lineItems) {
      const itemSubtotal = item.quantity * item.unit_price;
      const itemDiscount = itemSubtotal * (item.discount_rate || 0);
      const discountedAmount = itemSubtotal - itemDiscount;
      const itemTax = discountedAmount * (item.tax_rate || 0);

      subtotal += itemSubtotal;
      discountTotal += itemDiscount;
      taxTotal += itemTax;

      // Validate each line item
      this.validateRevenueCriticalOperation(itemSubtotal, 'Line item subtotal');
      
      if (item.tax_rate && item.tax_rate > 0.001) {
        this.validateTaxCalculation(discountedAmount, item.tax_rate, itemTax);
      }
    }

    const total = subtotal - discountTotal + taxTotal;
    this.validateRevenueCriticalOperation(total, 'Invoice total');

    return this.post<InvoiceCalculationResult>('/invoices/calculate', { line_items: lineItems }, config);
  }

  // ISP-Specific Business Logic
  async createServiceInvoice(params: {
    customer_id: string;
    service_instance_id: string;
    service_name: string;
    billing_period_start: string;
    billing_period_end: string;
    base_amount: number;
    usage_charges?: number;
    overage_charges?: number;
    tax_rate?: number;
    discount_rate?: number;
  }, config?: RequestConfig): Promise<Invoice> {
    const { 
      customer_id, 
      service_instance_id, 
      service_name,
      billing_period_start,
      billing_period_end,
      base_amount, 
      usage_charges = 0, 
      overage_charges = 0,
      tax_rate = 0,
      discount_rate = 0
    } = params;

    // Build line items for ISP service billing
    const lineItems: Array<any> = [
      {
        description: `${service_name} - Service Period: ${billing_period_start} to ${billing_period_end}`,
        quantity: 1,
        unit_price: base_amount,
        tax_rate,
        discount_rate,
        service_instance_id
      }
    ];

    if (usage_charges > 0) {
      lineItems.push({
        description: `${service_name} - Usage Charges`,
        quantity: 1,
        unit_price: usage_charges,
        tax_rate,
        service_instance_id
      });
    }

    if (overage_charges > 0) {
      lineItems.push({
        description: `${service_name} - Overage Charges`,
        quantity: 1,
        unit_price: overage_charges,
        tax_rate,
        service_instance_id
      });
    }

    const invoiceData: InvoiceCreate = {
      customer_id,
      line_items: lineItems,
      issue_date: new Date().toISOString(),
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days
      currency: 'USD',
      notes: `Service billing for ${service_name} (${billing_period_start} to ${billing_period_end})`
    };

    return this.createInvoice(invoiceData, config);
  }

  // Health Check
  async healthCheck(config?: RequestConfig): Promise<{ status: string; module: string; timestamp: string }> {
    return this.get('/health', config);
  }

  // AI-Enhanced Billing Analytics
  async getBillingAnalytics(params: {
    start_date: string;
    end_date: string;
    customer_id?: string;
    service_type?: string;
  }, config?: RequestConfig): Promise<BillingReport> {
    return this.get<BillingReport>('/analytics/billing', { ...config, params });
  }

  // Revenue Protection: Detect Anomalies
  async detectBillingAnomalies(params: {
    period_days: number;
    threshold_percentage: number;
  }, config?: RequestConfig): Promise<Array<{
    type: 'amount_spike' | 'amount_drop' | 'volume_spike' | 'volume_drop';
    description: string;
    current_value: number;
    expected_value: number;
    confidence: number;
    recommended_action: string;
  }>> {
    return this.get('/analytics/anomalies', { ...config, params });
  }
}
