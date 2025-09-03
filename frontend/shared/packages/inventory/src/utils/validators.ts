import type { ItemCreate, ItemUpdate, WarehouseCreate, StockAdjustment } from '../types';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings?: string[];
}

/**
 * Validate item creation data
 */
export function validateItemCreate(data: ItemCreate): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Required fields
  if (!data.name?.trim()) {
    errors.push('Item name is required');
  }

  if (!data.item_type) {
    errors.push('Item type is required');
  }

  if (!data.category?.trim()) {
    errors.push('Category is required');
  }

  // Name length validation
  if (data.name && data.name.length > 300) {
    errors.push('Item name cannot exceed 300 characters');
  }

  // Code validation
  if (data.item_code) {
    if (data.item_code.length > 100) {
      errors.push('Item code cannot exceed 100 characters');
    }
    if (!/^[A-Z0-9\-_]+$/i.test(data.item_code)) {
      errors.push('Item code can only contain letters, numbers, hyphens, and underscores');
    }
  }

  // Barcode validation
  if (data.barcode) {
    if (data.barcode.length > 100) {
      errors.push('Barcode cannot exceed 100 characters');
    }
    if (!/^[0-9A-Z\-]+$/i.test(data.barcode)) {
      errors.push('Barcode contains invalid characters');
    }
  }

  // Numeric validations
  if (data.reorder_point && data.reorder_point < 0) {
    errors.push('Reorder point cannot be negative');
  }

  if (data.reorder_quantity && data.reorder_quantity < 0) {
    errors.push('Reorder quantity cannot be negative');
  }

  if (data.max_stock_level && data.reorder_point && data.max_stock_level <= data.reorder_point) {
    warnings.push('Maximum stock level should be higher than reorder point');
  }

  if (data.weight_kg && data.weight_kg < 0) {
    errors.push('Weight cannot be negative');
  }

  // Price validations
  const priceFields = ['standard_cost', 'list_price'];
  priceFields.forEach((field) => {
    const value = data[field as keyof ItemCreate] as number;
    if (value !== undefined && value < 0) {
      errors.push(`${field.replace('_', ' ')} cannot be negative`);
    }
  });

  // Warranty period validation
  if (data.warranty_period_days && data.warranty_period_days < 0) {
    errors.push('Warranty period cannot be negative');
  }

  // Lead time validation
  if (data.lead_time_days && data.lead_time_days < 0) {
    errors.push('Lead time cannot be negative');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Validate warehouse creation data
 */
export function validateWarehouseCreate(data: WarehouseCreate): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Required fields
  if (!data.warehouse_code?.trim()) {
    errors.push('Warehouse code is required');
  }

  if (!data.name?.trim()) {
    errors.push('Warehouse name is required');
  }

  if (!data.warehouse_type) {
    errors.push('Warehouse type is required');
  }

  // Code validation
  if (data.warehouse_code) {
    if (data.warehouse_code.length > 50) {
      errors.push('Warehouse code cannot exceed 50 characters');
    }
    if (!/^[A-Z0-9\-_]+$/i.test(data.warehouse_code)) {
      errors.push('Warehouse code can only contain letters, numbers, hyphens, and underscores');
    }
  }

  // Name length validation
  if (data.name && data.name.length > 200) {
    errors.push('Warehouse name cannot exceed 200 characters');
  }

  // Coordinate validation
  if (data.latitude !== undefined) {
    if (data.latitude < -90 || data.latitude > 90) {
      errors.push('Latitude must be between -90 and 90');
    }
  }

  if (data.longitude !== undefined) {
    if (data.longitude < -180 || data.longitude > 180) {
      errors.push('Longitude must be between -180 and 180');
    }
  }

  // Area validation
  if (data.total_area_sqm && data.total_area_sqm <= 0) {
    errors.push('Total area must be positive');
  }

  // Capacity validation
  if (data.storage_capacity && data.storage_capacity <= 0) {
    errors.push('Storage capacity must be positive');
  }

  // Zone count validation
  if (data.zone_count && data.zone_count <= 0) {
    errors.push('Zone count must be positive');
  }

  // Staff count validation
  if (data.staff_count && data.staff_count < 0) {
    errors.push('Staff count cannot be negative');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Validate stock adjustment data
 */
export function validateStockAdjustment(data: StockAdjustment): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Required fields
  if (!data.item_id?.trim()) {
    errors.push('Item ID is required');
  }

  if (!data.warehouse_id?.trim()) {
    errors.push('Warehouse ID is required');
  }

  if (data.quantity_adjustment === undefined) {
    errors.push('Quantity adjustment is required');
  }

  // Quantity validation
  if (data.quantity_adjustment === 0) {
    errors.push('Quantity adjustment cannot be zero');
  }

  // Large adjustment warning
  if (Math.abs(data.quantity_adjustment) > 1000) {
    warnings.push('Large quantity adjustment - please verify');
  }

  // Unit cost validation
  if (data.unit_cost !== undefined && data.unit_cost < 0) {
    errors.push('Unit cost cannot be negative');
  }

  // Reason code validation
  if (data.reason_code && data.reason_code.length > 50) {
    errors.push('Reason code cannot exceed 50 characters');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Validate serial number format
 */
export function validateSerialNumber(serialNumber: string): ValidationResult {
  const errors: string[] = [];

  if (!serialNumber?.trim()) {
    errors.push('Serial number is required');
    return { isValid: false, errors };
  }

  // Length validation
  if (serialNumber.length < 3) {
    errors.push('Serial number must be at least 3 characters');
  }

  if (serialNumber.length > 50) {
    errors.push('Serial number cannot exceed 50 characters');
  }

  // Character validation
  if (!/^[A-Z0-9\-_]+$/i.test(serialNumber)) {
    errors.push('Serial number can only contain letters, numbers, hyphens, and underscores');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate quantity values
 */
export function validateQuantity(
  quantity: number,
  fieldName: string = 'Quantity',
  allowZero: boolean = false
): ValidationResult {
  const errors: string[] = [];

  if (quantity === undefined || quantity === null) {
    errors.push(`${fieldName} is required`);
    return { isValid: false, errors };
  }

  if (!Number.isInteger(quantity)) {
    errors.push(`${fieldName} must be a whole number`);
  }

  if (!allowZero && quantity === 0) {
    errors.push(`${fieldName} cannot be zero`);
  }

  if (quantity < 0) {
    errors.push(`${fieldName} cannot be negative`);
  }

  if (quantity > 1000000) {
    errors.push(`${fieldName} cannot exceed 1,000,000`);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate currency amount
 */
export function validateCurrencyAmount(
  amount: number,
  fieldName: string = 'Amount'
): ValidationResult {
  const errors: string[] = [];

  if (amount === undefined || amount === null) {
    errors.push(`${fieldName} is required`);
    return { isValid: false, errors };
  }

  if (amount < 0) {
    errors.push(`${fieldName} cannot be negative`);
  }

  if (amount > 999999999.99) {
    errors.push(`${fieldName} is too large`);
  }

  // Check decimal places
  const decimalPlaces = (amount.toString().split('.')[1] || '').length;
  if (decimalPlaces > 2) {
    errors.push(`${fieldName} cannot have more than 2 decimal places`);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate email address
 */
export function validateEmail(email: string): ValidationResult {
  const errors: string[] = [];

  if (!email?.trim()) {
    errors.push('Email is required');
    return { isValid: false, errors };
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    errors.push('Invalid email format');
  }

  if (email.length > 254) {
    errors.push('Email address is too long');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate date range
 */
export function validateDateRange(
  startDate: string | Date,
  endDate: string | Date
): ValidationResult {
  const errors: string[] = [];

  const start = typeof startDate === 'string' ? new Date(startDate) : startDate;
  const end = typeof endDate === 'string' ? new Date(endDate) : endDate;

  if (isNaN(start.getTime())) {
    errors.push('Invalid start date');
  }

  if (isNaN(end.getTime())) {
    errors.push('Invalid end date');
  }

  if (errors.length === 0 && start >= end) {
    errors.push('Start date must be before end date');
  }

  // Check for reasonable date range (not more than 10 years)
  if (errors.length === 0) {
    const diffYears = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 365);
    if (diffYears > 10) {
      errors.push('Date range cannot exceed 10 years');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate required fields
 */
export function validateRequiredFields<T>(data: T, requiredFields: (keyof T)[]): ValidationResult {
  const errors: string[] = [];

  requiredFields.forEach((field) => {
    const value = data[field];
    const fieldName = String(field).replace('_', ' ');

    if (value === undefined || value === null || value === '') {
      errors.push(`${fieldName} is required`);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate business rules for inventory items
 */
export function validateInventoryBusinessRules(data: {
  current_stock: number;
  reorder_point: number;
  max_stock?: number;
  reserved_stock: number;
}): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Available stock cannot be negative
  const availableStock = data.current_stock - data.reserved_stock;
  if (availableStock < 0) {
    errors.push('Available stock cannot be negative (reserved stock exceeds current stock)');
  }

  // Low stock warning
  if (data.current_stock <= data.reorder_point) {
    warnings.push('Item is below reorder point');
  }

  // Overstock warning
  if (data.max_stock && data.current_stock > data.max_stock) {
    warnings.push('Item exceeds maximum stock level');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}
