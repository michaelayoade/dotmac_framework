export interface PurchaseOrder {
  id: string;
  tenant_id: string;
  po_number: string;
  title: string;
  description?: string;
  vendor_id: string;
  vendor_name: string;
  vendor_contact?: string;
  order_date: string;
  required_date?: string;
  promised_date?: string;
  po_status: PurchaseOrderStatus;
  approved_by?: string;
  approval_date?: string;
  subtotal: number;
  tax_amount: number;
  shipping_cost: number;
  total_amount: number;
  ship_to_warehouse_id: string;
  shipping_method?: string;
  tracking_number?: string;
  payment_terms?: string;
  currency: string;
  shipped_date?: string;
  received_date?: string;
  terms_and_conditions?: string;
  notes?: string;
  platform_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  line_items?: PurchaseOrderLine[];
}

export enum PurchaseOrderStatus {
  DRAFT = 'draft',
  PENDING_APPROVAL = 'pending_approval',
  APPROVED = 'approved',
  SENT_TO_VENDOR = 'sent_to_vendor',
  PARTIALLY_RECEIVED = 'partially_received',
  RECEIVED = 'received',
  CANCELLED = 'cancelled',
  CLOSED = 'closed',
}

export interface PurchaseOrderLine {
  id: string;
  tenant_id: string;
  purchase_order_id: string;
  item_id: string;
  line_number: number;
  item_description?: string;
  quantity_ordered: number;
  quantity_received: number;
  quantity_remaining: number;
  unit_price: number;
  discount_percent: number;
  line_total: number;
  required_date?: string;
  promised_date?: string;
  line_status: string;
  vendor_item_code?: string;
  notes?: string;
  platform_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrderCreate {
  title: string;
  description?: string;
  vendor_id: string;
  vendor_name: string;
  vendor_contact?: string;
  required_date?: string;
  ship_to_warehouse_id: string;
  shipping_method?: string;
  payment_terms?: string;
  currency?: string;
  terms_and_conditions?: string;
  notes?: string;
  platform_data?: Record<string, any>;
}

export interface PurchaseOrderLineCreate {
  item_id: string;
  line_number: number;
  item_description?: string;
  quantity_ordered: number;
  unit_price: number;
  discount_percent?: number;
  required_date?: string;
  promised_date?: string;
  vendor_item_code?: string;
  notes?: string;
  platform_data?: Record<string, any>;
}

export interface PurchaseOrderUpdate extends Partial<PurchaseOrderCreate> {
  po_status?: PurchaseOrderStatus;
  approved_by?: string;
  approval_date?: string;
  subtotal?: number;
  tax_amount?: number;
  shipping_cost?: number;
  total_amount?: number;
  tracking_number?: string;
  shipped_date?: string;
  received_date?: string;
}

export interface PurchaseOrderFilter {
  vendor_id?: string;
  po_status?: PurchaseOrderStatus | PurchaseOrderStatus[];
  order_date_from?: string;
  order_date_to?: string;
  required_date_from?: string;
  required_date_to?: string;
  search?: string;
}
