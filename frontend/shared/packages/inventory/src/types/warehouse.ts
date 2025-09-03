export interface Warehouse {
  id: string;
  tenant_id: string;
  warehouse_code: string;
  name: string;
  description?: string;
  warehouse_type: WarehouseType;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  total_area_sqm?: number;
  storage_capacity?: number;
  zone_count: number;
  bin_locations?: Record<string, any>;
  operating_hours?: Record<string, any>;
  manager_name?: string;
  staff_count: number;
  temperature_controlled: boolean;
  humidity_controlled: boolean;
  security_level: string;
  wms_integrated: boolean;
  barcode_scanning: boolean;
  rfid_enabled: boolean;
  is_active: boolean;
  notes?: string;
  platform_data?: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

export enum WarehouseType {
  MAIN = 'main',
  REGIONAL = 'regional',
  FIELD = 'field',
  VENDOR = 'vendor',
  CUSTOMER = 'customer',
  REPAIR = 'repair',
  QUARANTINE = 'quarantine',
  TECHNICIAN_VAN = 'technician_van',
}

export interface WarehouseCreate {
  warehouse_code: string;
  name: string;
  description?: string;
  warehouse_type: WarehouseType;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  total_area_sqm?: number;
  storage_capacity?: number;
  zone_count?: number;
  bin_locations?: Record<string, any>;
  operating_hours?: Record<string, any>;
  manager_name?: string;
  staff_count?: number;
  temperature_controlled?: boolean;
  humidity_controlled?: boolean;
  security_level?: string;
  wms_integrated?: boolean;
  barcode_scanning?: boolean;
  rfid_enabled?: boolean;
  notes?: string;
  platform_data?: Record<string, any>;
}

export interface WarehouseUpdate extends Partial<WarehouseCreate> {
  is_active?: boolean;
}

export interface WarehouseFilter {
  warehouse_type?: WarehouseType | WarehouseType[];
  city?: string;
  country?: string;
  is_active?: boolean;
  search?: string;
}
