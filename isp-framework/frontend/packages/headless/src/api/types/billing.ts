/**
 * Billing API Types - Aligned with Backend Schemas
 * 
 * These types mirror the Pydantic schemas from the backend to ensure
 * type safety across the full stack.
 */

export enum InvoiceStatus {
  DRAFT = "draft",
  SENT = "sent", 
  PAID = "paid",
  OVERDUE = "overdue",
  CANCELLED = "cancelled"
}

export enum PaymentStatus {
  PENDING = "pending",
  COMPLETED = "completed", 
  FAILED = "failed",
  REFUNDED = "refunded"
}

export enum PaymentMethod {
  CREDIT_CARD = "credit_card",
  BANK_TRANSFER = "bank_transfer",
  CHECK = "check",
  CASH = "cash",
  ACH = "ach"
}

export enum TaxType {
  SALES_TAX = "sales_tax",
  VAT = "vat",
  GST = "gst", 
  EXCISE = "excise"
}

// Base line item interface
export interface LineItemBase {
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate?: number;
  discount_rate?: number;
}

export interface LineItemCreate extends LineItemBase {
  service_instance_id?: string;
}

export interface LineItem extends LineItemBase {
  id: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number; 
  total: number;
  created_at: string;
}

// Invoice interfaces
export interface InvoiceBase {
  customer_id: string;
  invoice_number?: string;
  issue_date: string;
  due_date: string;
  notes?: string;
  terms?: string;
  currency: string;
}

export interface InvoiceCreate extends InvoiceBase {
  line_items: LineItemCreate[];
}

export interface InvoiceUpdate {
  status?: InvoiceStatus;
  notes?: string;
  due_date?: string;
}

export interface Invoice extends InvoiceBase {
  id: string;
  status: InvoiceStatus;
  line_items: LineItem[];
  subtotal: number;
  tax_total: number;
  discount_total: number;
  total_amount: number;
  amount_paid: number;
  amount_due: number;
  created_at: string;
  updated_at: string;
}

// Payment interfaces  
export interface PaymentBase {
  invoice_id: string;
  amount: number;
  payment_method: PaymentMethod;
  reference_number?: string;
  notes?: string;
}

export interface PaymentCreate extends PaymentBase {}

export interface Payment extends PaymentBase {
  id: string;
  payment_date: string;
  status: PaymentStatus;
  transaction_id?: string;
  created_at: string;
}

// Credit note interfaces
export interface CreditNoteBase {
  invoice_id: string;
  reason: string;
  amount: number;
  notes?: string;
}

export interface CreditNoteCreate extends CreditNoteBase {}

export interface CreditNote extends CreditNoteBase {
  id: string;
  credit_note_number: string;
  status: string;
  created_at: string;
  applied_at?: string;
}

// Receipt interfaces
export interface ReceiptBase {
  payment_id: string;
  receipt_number?: string;
}

export interface ReceiptCreate extends ReceiptBase {}

export interface Receipt extends ReceiptBase {
  id: string;
  receipt_number: string;
  issued_at: string;
  amount: number;
  payment_method: PaymentMethod;
  customer_name: string;
  invoice_number: string;
}

// Tax rate interfaces
export interface TaxRateBase {
  name: string;
  rate: number;
  tax_type: TaxType;
  jurisdiction: string;
  active: boolean;
}

export interface TaxRateCreate extends TaxRateBase {}

export interface TaxRate extends TaxRateBase {
  id: string;
  created_at: string;
  updated_at: string;
}

// Subscription interfaces
export interface SubscriptionBase {
  customer_id: string;
  plan_id: string;
  billing_cycle: string;
  amount: number;
  currency: string;
  start_date: string;
  end_date?: string;
}

export interface SubscriptionCreate extends SubscriptionBase {}

export interface SubscriptionUpdate {
  plan_id?: string;
  billing_cycle?: string;
  amount?: number;
  currency?: string;
  end_date?: string;
  is_active?: boolean;
}

export interface Subscription extends SubscriptionBase {
  id: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  trial_end?: string;
  created_at: string;
  updated_at: string;
}

// Billing report interface
export interface BillingReport {
  period_start: string;
  period_end: string;
  total_invoiced: number;
  total_paid: number;
  total_outstanding: number;
  invoice_count: number;
  payment_count: number;
  average_payment_time?: number;
}

// Request/Response interfaces for API calls
export interface InvoiceListParams {
  customer_id?: string;
  status?: InvoiceStatus;
  due_date_from?: string;
  due_date_to?: string;
  skip?: number;
  limit?: number;
}

export interface PaymentRequest {
  invoice_id: string;
  amount: number;
  payment_method: PaymentMethod;
  reference_number?: string;
  notes?: string;
}

export interface CreditNoteRequest {
  customer_id: string;
  amount: number;
  reason: string;
  invoice_id?: string;
}

export interface InvoiceCalculationResult {
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  line_items: LineItem[];
}

// Utility types for form handling
export interface BillingFormData {
  customerId: string;
  amount: number;
  currency: string;
  taxRate: number;
  discount: number;
  paymentMethod: PaymentMethod;
  billingCycle: string;
}

// API Response wrappers
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}