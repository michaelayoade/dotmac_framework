import {
  validateItemCreate,
  validateWarehouseCreate,
  validateStockAdjustment,
  validateSerialNumber,
  validateQuantity,
  validateCurrencyAmount,
  validateEmail,
  validateDateRange,
} from '../../utils/validators';
import { ItemType, WarehouseType } from '../../types';

describe('Inventory Validators', () => {
  describe('validateItemCreate', () => {
    const validItem = {
      name: 'Test Item',
      item_type: ItemType.HARDWARE,
      category: 'Computer Hardware',
      item_code: 'TEST-001',
      reorder_point: 10,
      reorder_quantity: 50,
    };

    it('should validate correct item data', () => {
      const result = validateItemCreate(validItem);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require item name', () => {
      const result = validateItemCreate({ ...validItem, name: '' });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Item name is required');
    });

    it('should require item type', () => {
      const result = validateItemCreate({ ...validItem, item_type: undefined as any });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Item type is required');
    });

    it('should require category', () => {
      const result = validateItemCreate({ ...validItem, category: '' });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Category is required');
    });

    it('should validate item name length', () => {
      const longName = 'a'.repeat(301);
      const result = validateItemCreate({ ...validItem, name: longName });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Item name cannot exceed 300 characters');
    });

    it('should validate item code format', () => {
      const result = validateItemCreate({ ...validItem, item_code: 'invalid code!' });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Item code can only contain letters, numbers, hyphens, and underscores'
      );
    });

    it('should validate negative reorder point', () => {
      const result = validateItemCreate({ ...validItem, reorder_point: -5 });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Reorder point cannot be negative');
    });

    it('should warn about max stock level vs reorder point', () => {
      const result = validateItemCreate({
        ...validItem,
        reorder_point: 100,
        max_stock_level: 50,
      });
      expect(result.warnings).toContain('Maximum stock level should be higher than reorder point');
    });
  });

  describe('validateWarehouseCreate', () => {
    const validWarehouse = {
      warehouse_code: 'WH-001',
      name: 'Test Warehouse',
      warehouse_type: WarehouseType.MAIN,
    };

    it('should validate correct warehouse data', () => {
      const result = validateWarehouseCreate(validWarehouse);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require warehouse code', () => {
      const result = validateWarehouseCreate({ ...validWarehouse, warehouse_code: '' });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Warehouse code is required');
    });

    it('should require warehouse name', () => {
      const result = validateWarehouseCreate({ ...validWarehouse, name: '' });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Warehouse name is required');
    });

    it('should validate latitude range', () => {
      const result = validateWarehouseCreate({ ...validWarehouse, latitude: 91 });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Latitude must be between -90 and 90');
    });

    it('should validate longitude range', () => {
      const result = validateWarehouseCreate({ ...validWarehouse, longitude: 181 });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Longitude must be between -180 and 180');
    });
  });

  describe('validateStockAdjustment', () => {
    const validAdjustment = {
      item_id: 'item-123',
      warehouse_id: 'warehouse-456',
      quantity_adjustment: 10,
    };

    it('should validate correct adjustment data', () => {
      const result = validateStockAdjustment(validAdjustment);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require item ID', () => {
      const result = validateStockAdjustment({ ...validAdjustment, item_id: '' });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Item ID is required');
    });

    it('should not allow zero adjustment', () => {
      const result = validateStockAdjustment({ ...validAdjustment, quantity_adjustment: 0 });
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Quantity adjustment cannot be zero');
    });

    it('should warn about large adjustments', () => {
      const result = validateStockAdjustment({ ...validAdjustment, quantity_adjustment: 1500 });
      expect(result.warnings).toContain('Large quantity adjustment - please verify');
    });
  });

  describe('validateSerialNumber', () => {
    it('should validate correct serial number', () => {
      const result = validateSerialNumber('SN12345');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require serial number', () => {
      const result = validateSerialNumber('');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Serial number is required');
    });

    it('should validate minimum length', () => {
      const result = validateSerialNumber('AB');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Serial number must be at least 3 characters');
    });

    it('should validate maximum length', () => {
      const result = validateSerialNumber('A'.repeat(51));
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Serial number cannot exceed 50 characters');
    });

    it('should validate character format', () => {
      const result = validateSerialNumber('SN@123!');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Serial number can only contain letters, numbers, hyphens, and underscores'
      );
    });
  });

  describe('validateQuantity', () => {
    it('should validate positive quantity', () => {
      const result = validateQuantity(10);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require quantity', () => {
      const result = validateQuantity(undefined as any);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Quantity is required');
    });

    it('should require whole numbers', () => {
      const result = validateQuantity(10.5);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Quantity must be a whole number');
    });

    it('should not allow negative quantities', () => {
      const result = validateQuantity(-5);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Quantity cannot be negative');
    });

    it('should allow zero when specified', () => {
      const result = validateQuantity(0, 'Quantity', true);
      expect(result.isValid).toBe(true);
    });

    it('should not allow zero by default', () => {
      const result = validateQuantity(0);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Quantity cannot be zero');
    });
  });

  describe('validateCurrencyAmount', () => {
    it('should validate positive amount', () => {
      const result = validateCurrencyAmount(99.99);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require amount', () => {
      const result = validateCurrencyAmount(undefined as any);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Amount is required');
    });

    it('should not allow negative amounts', () => {
      const result = validateCurrencyAmount(-10.5);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Amount cannot be negative');
    });

    it('should validate decimal places', () => {
      const result = validateCurrencyAmount(10.123);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Amount cannot have more than 2 decimal places');
    });
  });

  describe('validateEmail', () => {
    it('should validate correct email', () => {
      const result = validateEmail('test@example.com');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require email', () => {
      const result = validateEmail('');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Email is required');
    });

    it('should validate email format', () => {
      const result = validateEmail('invalid-email');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Invalid email format');
    });

    it('should validate email length', () => {
      const longEmail = 'a'.repeat(250) + '@example.com';
      const result = validateEmail(longEmail);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Email address is too long');
    });
  });

  describe('validateDateRange', () => {
    it('should validate correct date range', () => {
      const start = new Date('2023-01-01');
      const end = new Date('2023-12-31');
      const result = validateDateRange(start, end);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject end date before start date', () => {
      const start = new Date('2023-12-31');
      const end = new Date('2023-01-01');
      const result = validateDateRange(start, end);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Start date must be before end date');
    });

    it('should reject invalid dates', () => {
      const result = validateDateRange('invalid-date', '2023-01-01');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Invalid start date');
    });

    it('should reject ranges over 10 years', () => {
      const start = new Date('2020-01-01');
      const end = new Date('2035-01-01');
      const result = validateDateRange(start, end);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Date range cannot exceed 10 years');
    });
  });
});
