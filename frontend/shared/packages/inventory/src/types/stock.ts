import { ItemCondition, ItemStatus } from './inventory';

export interface StockItem {
  id: string;
  tenant_id: string;
  item_id: string;
  warehouse_id: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  bin_location?: string;
  zone?: string;
  aisle?: string;
  shelf?: string;
  condition: ItemCondition;
  item_status: ItemStatus;
  serial_numbers?: Record<string, any>;
  lot_numbers?: Record<string, any>;
  expiry_dates?: Record<string, any>;
  unit_cost?: number;
  total_value?: number;
  valuation_method: string;
  min_quantity: number;
  max_quantity?: number;
  last_movement_date?: string;
  last_counted_date?: string;
  notes?: string;
  platform_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface StockAdjustment {
  item_id: string;
  warehouse_id: string;
  quantity_adjustment: number;
  reason_code?: string;
  reason_description?: string;
  unit_cost?: number;
  reference_number?: string;
  approval_required?: boolean;
}

export interface StockReservation {
  item_id: string;
  warehouse_id: string;
  quantity: number;
  reserved_for: string;
  reservation_type: 'customer_order' | 'work_order' | 'project' | 'maintenance';
  expiry_date?: string;
  notes?: string;
}
