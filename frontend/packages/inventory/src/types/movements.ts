export interface StockMovement {
  id: string;
  tenant_id: string;
  movement_id: string;
  reference_number?: string;
  item_id: string;
  warehouse_id: string;
  movement_type: MovementType;
  movement_date: string;
  quantity: number;
  unit_cost?: number;
  total_cost?: number;
  from_warehouse_id?: string;
  from_location?: string;
  to_location?: string;
  reason_code?: string;
  reason_description?: string;
  purchase_order_id?: string;
  work_order_id?: string;
  project_id?: string;
  invoice_number?: string;
  approved_by?: string;
  approved_date?: string;
  processed_by: string;
  serial_numbers?: Record<string, any>;
  lot_numbers?: Record<string, any>;
  expiry_date?: string;
  notes?: string;
  platform_data?: Record<string, any>;
  created_at: string;
}

export enum MovementType {
  RECEIPT = 'receipt',
  ISSUE = 'issue',
  TRANSFER = 'transfer',
  ADJUSTMENT = 'adjustment',
  RETURN = 'return',
  WRITE_OFF = 'write_off',
  FOUND = 'found',
  INSTALLATION = 'installation',
  REPLACEMENT = 'replacement'
}

export interface StockMovementCreate {
  item_id: string;
  warehouse_id: string;
  movement_type: MovementType;
  quantity: number;
  unit_cost?: number;
  total_cost?: number;
  from_warehouse_id?: string;
  from_location?: string;
  to_location?: string;
  reason_code?: string;
  reason_description?: string;
  purchase_order_id?: string;
  work_order_id?: string;
  project_id?: string;
  invoice_number?: string;
  reference_number?: string;
  serial_numbers?: Record<string, any>;
  lot_numbers?: Record<string, any>;
  expiry_date?: string;
  notes?: string;
  platform_data?: Record<string, any>;
}

export interface MovementFilter {
  item_id?: string;
  warehouse_id?: string;
  movement_type?: MovementType | MovementType[];
  start_date?: string;
  end_date?: string;
  reference_number?: string;
  purchase_order_id?: string;
  work_order_id?: string;
  project_id?: string;
}
