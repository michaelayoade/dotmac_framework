export interface Item {
  id: string;
  tenant_id: string;
  item_code: string;
  barcode?: string;
  name: string;
  description?: string;
  item_type: ItemType;
  category: string;
  subcategory?: string;
  manufacturer?: string;
  model?: string;
  part_number?: string;
  manufacturer_part_number?: string;
  weight_kg?: number;
  dimensions?: {
    length?: number;
    width?: number;
    height?: number;
  };
  color?: string;
  technical_specs?: Record<string, any>;
  compatibility?: Record<string, any>;
  operating_conditions?: Record<string, any>;
  unit_of_measure: string;
  reorder_point: number;
  reorder_quantity: number;
  max_stock_level?: number;
  standard_cost?: number;
  last_purchase_cost?: number;
  average_cost?: number;
  list_price?: number;
  introduction_date?: string;
  discontinue_date?: string;
  end_of_life_date?: string;
  quality_grade?: string;
  certifications?: Record<string, any>;
  regulatory_info?: Record<string, any>;
  primary_vendor_id?: string;
  vendor_item_code?: string;
  lead_time_days?: number;
  warranty_period_days?: number;
  service_level?: string;
  maintenance_required: boolean;
  documentation_links?: Record<string, any>;
  image_urls?: Record<string, any>;
  safety_data_sheet_url?: string;
  track_serial_numbers: boolean;
  track_lot_numbers: boolean;
  track_expiry_dates: boolean;
  is_active: boolean;
  is_discontinued: boolean;
  tags?: Record<string, any>;
  platform_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

export enum ItemType {
  HARDWARE = 'hardware',
  SOFTWARE = 'software',
  CONSUMABLE = 'consumable',
  TOOL = 'tool',
  SPARE_PART = 'spare_part',
  KIT = 'kit',
  ACCESSORY = 'accessory',
  NETWORK_EQUIPMENT = 'network_equipment',
  CUSTOMER_PREMISES_EQUIPMENT = 'customer_premises_equipment'
}

export enum ItemCondition {
  NEW = 'new',
  REFURBISHED = 'refurbished',
  USED = 'used',
  DAMAGED = 'damaged',
  DEFECTIVE = 'defective',
  OBSOLETE = 'obsolete'
}

export enum ItemStatus {
  AVAILABLE = 'available',
  RESERVED = 'reserved',
  ALLOCATED = 'allocated',
  IN_USE = 'in_use',
  IN_REPAIR = 'in_repair',
  RETIRED = 'retired',
  LOST = 'lost',
  QUARANTINED = 'quarantined'
}

export interface ItemCreate {
  item_code?: string;
  barcode?: string;
  name: string;
  description?: string;
  item_type: ItemType;
  category: string;
  subcategory?: string;
  manufacturer?: string;
  model?: string;
  part_number?: string;
  manufacturer_part_number?: string;
  weight_kg?: number;
  dimensions?: {
    length?: number;
    width?: number;
    height?: number;
  };
  color?: string;
  technical_specs?: Record<string, any>;
  compatibility?: Record<string, any>;
  operating_conditions?: Record<string, any>;
  unit_of_measure?: string;
  reorder_point?: number;
  reorder_quantity?: number;
  max_stock_level?: number;
  standard_cost?: number;
  list_price?: number;
  primary_vendor_id?: string;
  vendor_item_code?: string;
  lead_time_days?: number;
  warranty_period_days?: number;
  service_level?: string;
  maintenance_required?: boolean;
  documentation_links?: Record<string, any>;
  image_urls?: Record<string, any>;
  safety_data_sheet_url?: string;
  track_serial_numbers?: boolean;
  track_lot_numbers?: boolean;
  track_expiry_dates?: boolean;
  tags?: Record<string, any>;
  platform_data?: Record<string, any>;
}

export interface ItemUpdate extends Partial<ItemCreate> {
  is_active?: boolean;
  is_discontinued?: boolean;
}

export interface ItemFilter {
  item_type?: ItemType | ItemType[];
  category?: string | string[];
  manufacturer?: string | string[];
  status?: ItemStatus | ItemStatus[];
  is_active?: boolean;
  is_discontinued?: boolean;
  low_stock?: boolean;
  search?: string;
}

export interface ItemStockSummary {
  item_id: string;
  total_quantity: number;
  total_available: number;
  total_reserved: number;
  warehouses: Array<{
    warehouse_id: string;
    warehouse_name: string;
    quantity: number;
    available: number;
    reserved: number;
  }>;
}
