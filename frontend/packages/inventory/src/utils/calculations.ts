import type { StockLevel, Item, StockItem, PurchaseOrderLine } from '../types';

/**
 * Calculate stock level status
 */
export function calculateStockStatus(
  currentStock: number,
  reorderPoint: number,
  maxStock?: number
): 'healthy' | 'low' | 'critical' | 'overstock' {
  if (currentStock === 0) return 'critical';
  if (currentStock < reorderPoint * 0.5) return 'critical';
  if (currentStock < reorderPoint) return 'low';
  if (maxStock && currentStock > maxStock) return 'overstock';
  return 'healthy';
}

/**
 * Calculate stock turnover rate
 */
export function calculateStockTurnover(
  averageInventory: number,
  costOfGoodsSold: number,
  periodInDays: number = 365
): number {
  if (averageInventory === 0) return 0;
  return (costOfGoodsSold / averageInventory) * (365 / periodInDays);
}

/**
 * Calculate days of inventory outstanding
 */
export function calculateDaysInventoryOutstanding(
  averageInventory: number,
  costOfGoodsSold: number,
  periodInDays: number = 365
): number {
  const turnoverRate = calculateStockTurnover(averageInventory, costOfGoodsSold, periodInDays);
  if (turnoverRate === 0) return 0;
  return 365 / turnoverRate;
}

/**
 * Calculate reorder point using lead time and safety stock
 */
export function calculateReorderPoint(
  averageDemand: number,
  leadTimeDays: number,
  safetyStockDays: number = 7
): number {
  return Math.ceil(averageDemand * (leadTimeDays + safetyStockDays));
}

/**
 * Calculate economic order quantity (EOQ)
 */
export function calculateEOQ(
  annualDemand: number,
  orderingCost: number,
  holdingCostPerUnit: number
): number {
  if (holdingCostPerUnit === 0) return 0;
  return Math.ceil(Math.sqrt((2 * annualDemand * orderingCost) / holdingCostPerUnit));
}

/**
 * Calculate safety stock level
 */
export function calculateSafetyStock(
  maxDemand: number,
  averageDemand: number,
  maxLeadTime: number,
  averageLeadTime: number
): number {
  return Math.ceil((maxDemand * maxLeadTime) - (averageDemand * averageLeadTime));
}

/**
 * Calculate inventory value using different methods
 */
export function calculateInventoryValue(
  stockItems: StockItem[],
  method: 'FIFO' | 'LIFO' | 'AVERAGE' | 'STANDARD' = 'AVERAGE'
): number {
  return stockItems.reduce((total, item) => {
    const unitCost = item.unit_cost || 0;
    return total + (item.quantity * unitCost);
  }, 0);
}

/**
 * Calculate carrying cost
 */
export function calculateCarryingCost(
  inventoryValue: number,
  carryingCostRate: number = 0.20 // 20% default
): number {
  return inventoryValue * carryingCostRate;
}

/**
 * Calculate inventory accuracy percentage
 */
export function calculateInventoryAccuracy(
  countedQuantity: number,
  systemQuantity: number
): number {
  if (systemQuantity === 0 && countedQuantity === 0) return 100;
  if (systemQuantity === 0) return 0;

  const accuracy = (1 - Math.abs(countedQuantity - systemQuantity) / systemQuantity) * 100;
  return Math.max(0, Math.min(100, accuracy));
}

/**
 * Calculate ABC classification scores
 */
export function calculateABCClassification(
  items: Array<{ value: number; quantity: number }>
): Array<{ index: number; classification: 'A' | 'B' | 'C'; value: number; cumulativeValue: number; cumulativePercent: number }> {
  // Sort items by value in descending order
  const sortedItems = items
    .map((item, index) => ({ ...item, index, cumulativeValue: 0, cumulativePercent: 0 }))
    .sort((a, b) => b.value - a.value);

  const totalValue = sortedItems.reduce((sum, item) => sum + item.value, 0);
  let cumulativeValue = 0;

  return sortedItems.map((item, i) => {
    cumulativeValue += item.value;
    const cumulativePercent = (cumulativeValue / totalValue) * 100;

    let classification: 'A' | 'B' | 'C';
    if (cumulativePercent <= 80) {
      classification = 'A';
    } else if (cumulativePercent <= 95) {
      classification = 'B';
    } else {
      classification = 'C';
    }

    return {
      ...item,
      classification,
      cumulativeValue,
      cumulativePercent
    };
  });
}

/**
 * Calculate service level from fill rate
 */
export function calculateServiceLevel(
  demandMet: number,
  totalDemand: number
): number {
  if (totalDemand === 0) return 100;
  return (demandMet / totalDemand) * 100;
}

/**
 * Calculate fill rate
 */
export function calculateFillRate(
  ordersFilled: number,
  totalOrders: number
): number {
  if (totalOrders === 0) return 100;
  return (ordersFilled / totalOrders) * 100;
}

/**
 * Calculate inventory velocity
 */
export function calculateInventoryVelocity(
  unitsShipped: number,
  averageInventory: number,
  periodInDays: number = 30
): number {
  if (averageInventory === 0) return 0;
  return (unitsShipped / averageInventory) * (365 / periodInDays);
}

/**
 * Calculate stockout cost
 */
export function calculateStockoutCost(
  unitsShort: number,
  stockoutCostPerUnit: number,
  lostSalesMultiplier: number = 1
): number {
  return unitsShort * stockoutCostPerUnit * lostSalesMultiplier;
}

/**
 * Calculate purchase order line total
 */
export function calculatePOLineTotal(
  quantity: number,
  unitPrice: number,
  discountPercent: number = 0
): number {
  const subtotal = quantity * unitPrice;
  const discount = subtotal * (discountPercent / 100);
  return subtotal - discount;
}

/**
 * Calculate purchase order total
 */
export function calculatePOTotal(
  lineItems: PurchaseOrderLine[],
  taxRate: number = 0,
  shippingCost: number = 0
): {
  subtotal: number;
  taxAmount: number;
  shippingCost: number;
  total: number;
} {
  const subtotal = lineItems.reduce((total, line) => {
    return total + calculatePOLineTotal(line.quantity_ordered, line.unit_price, line.discount_percent);
  }, 0);

  const taxAmount = subtotal * (taxRate / 100);
  const total = subtotal + taxAmount + shippingCost;

  return {
    subtotal,
    taxAmount,
    shippingCost,
    total
  };
}

/**
 * Calculate demand forecast using simple moving average
 */
export function calculateMovingAverage(
  values: number[],
  periods: number = 3
): number {
  if (values.length === 0) return 0;
  if (values.length < periods) return values.reduce((sum, val) => sum + val, 0) / values.length;

  const recentValues = values.slice(-periods);
  return recentValues.reduce((sum, val) => sum + val, 0) / periods;
}

/**
 * Calculate exponential moving average
 */
export function calculateExponentialMovingAverage(
  values: number[],
  alpha: number = 0.3
): number {
  if (values.length === 0) return 0;
  if (values.length === 1) return values[0];

  let ema = values[0];
  for (let i = 1; i < values.length; i++) {
    ema = alpha * values[i] + (1 - alpha) * ema;
  }

  return ema;
}

/**
 * Calculate seasonal index
 */
export function calculateSeasonalIndex(
  monthlyAverages: number[],
  overallAverage: number
): number[] {
  return monthlyAverages.map(monthlyAvg =>
    overallAverage === 0 ? 1 : monthlyAvg / overallAverage
  );
}

/**
 * Calculate forecast accuracy (MAPE - Mean Absolute Percentage Error)
 */
export function calculateMAPE(
  actualValues: number[],
  forecastValues: number[]
): number {
  if (actualValues.length !== forecastValues.length || actualValues.length === 0) {
    return 0;
  }

  let totalPercentageError = 0;
  let validPairs = 0;

  for (let i = 0; i < actualValues.length; i++) {
    if (actualValues[i] !== 0) {
      totalPercentageError += Math.abs((actualValues[i] - forecastValues[i]) / actualValues[i]);
      validPairs++;
    }
  }

  return validPairs === 0 ? 0 : (totalPercentageError / validPairs) * 100;
}
