import {
  calculateStockStatus,
  calculateReorderPoint,
  calculateEOQ,
  calculateInventoryAccuracy,
  calculateABCClassification,
  calculatePOLineTotal,
  calculateMovingAverage,
  calculateMAPE
} from '../../utils/calculations';

describe('Inventory Calculations', () => {
  describe('calculateStockStatus', () => {
    it('should return critical when stock is 0', () => {
      expect(calculateStockStatus(0, 10)).toBe('critical');
    });

    it('should return critical when stock is below 50% of reorder point', () => {
      expect(calculateStockStatus(4, 10)).toBe('critical');
    });

    it('should return low when stock is below reorder point but above 50%', () => {
      expect(calculateStockStatus(7, 10)).toBe('low');
    });

    it('should return healthy when stock is above reorder point', () => {
      expect(calculateStockStatus(15, 10)).toBe('healthy');
    });

    it('should return overstock when stock exceeds max stock', () => {
      expect(calculateStockStatus(25, 10, 20)).toBe('overstock');
    });
  });

  describe('calculateReorderPoint', () => {
    it('should calculate correct reorder point', () => {
      const result = calculateReorderPoint(5, 7, 3); // 5 units/day, 7 day lead time, 3 day safety
      expect(result).toBe(50); // 5 * (7 + 3) = 50
    });

    it('should handle zero values', () => {
      expect(calculateReorderPoint(0, 7, 3)).toBe(0);
    });
  });

  describe('calculateEOQ', () => {
    it('should calculate correct EOQ', () => {
      const result = calculateEOQ(1000, 50, 5); // 1000 annual demand, $50 ordering cost, $5 holding cost
      expect(result).toBe(141); // sqrt((2 * 1000 * 50) / 5) = 141.42, rounded up
    });

    it('should return 0 when holding cost is 0', () => {
      expect(calculateEOQ(1000, 50, 0)).toBe(0);
    });
  });

  describe('calculateInventoryAccuracy', () => {
    it('should calculate 100% accuracy for exact match', () => {
      expect(calculateInventoryAccuracy(10, 10)).toBe(100);
    });

    it('should calculate 0% accuracy for complete mismatch when system is non-zero', () => {
      expect(calculateInventoryAccuracy(0, 10)).toBe(0);
    });

    it('should calculate 50% accuracy for 50% variance', () => {
      expect(calculateInventoryAccuracy(5, 10)).toBe(50);
    });

    it('should handle zero system quantity with zero counted', () => {
      expect(calculateInventoryAccuracy(0, 0)).toBe(100);
    });

    it('should return 0 when system quantity is 0 but counted is not', () => {
      expect(calculateInventoryAccuracy(5, 0)).toBe(0);
    });
  });

  describe('calculateABCClassification', () => {
    it('should classify items correctly', () => {
      const items = [
        { value: 1000, quantity: 1 },
        { value: 500, quantity: 1 },
        { value: 200, quantity: 1 },
        { value: 100, quantity: 1 },
        { value: 50, quantity: 1 }
      ];

      const result = calculateABCClassification(items);

      expect(result).toHaveLength(5);
      expect(result[0].classification).toBe('A'); // Highest value
      expect(result[0].value).toBe(1000);
      expect(result[4].classification).toBe('C'); // Lowest value
      expect(result[4].value).toBe(50);
    });
  });

  describe('calculatePOLineTotal', () => {
    it('should calculate line total without discount', () => {
      expect(calculatePOLineTotal(10, 25)).toBe(250);
    });

    it('should calculate line total with discount', () => {
      expect(calculatePOLineTotal(10, 25, 10)).toBe(225); // 10% discount
    });
  });

  describe('calculateMovingAverage', () => {
    it('should calculate moving average correctly', () => {
      const values = [10, 20, 30, 40, 50];
      expect(calculateMovingAverage(values, 3)).toBe(40); // (30 + 40 + 50) / 3
    });

    it('should handle fewer values than periods', () => {
      const values = [10, 20];
      expect(calculateMovingAverage(values, 3)).toBe(15); // (10 + 20) / 2
    });

    it('should handle empty array', () => {
      expect(calculateMovingAverage([], 3)).toBe(0);
    });
  });

  describe('calculateMAPE', () => {
    it('should calculate MAPE correctly', () => {
      const actual = [100, 200, 300];
      const forecast = [110, 190, 320];
      const mape = calculateMAPE(actual, forecast);

      // Expected: ((|100-110|/100 + |200-190|/200 + |300-320|/300) / 3) * 100
      // = ((10/100 + 10/200 + 20/300) / 3) * 100
      // = ((0.1 + 0.05 + 0.0667) / 3) * 100 = 7.22%
      expect(mape).toBeCloseTo(7.22, 1);
    });

    it('should handle zero actual values', () => {
      const actual = [0, 200, 300];
      const forecast = [10, 190, 320];
      const mape = calculateMAPE(actual, forecast);

      // Should skip zero actual value and calculate only for valid pairs
      expect(mape).toBeCloseTo(5.83, 1);
    });

    it('should return 0 for empty arrays', () => {
      expect(calculateMAPE([], [])).toBe(0);
    });

    it('should return 0 for mismatched array lengths', () => {
      expect(calculateMAPE([1, 2], [1])).toBe(0);
    });
  });
});
