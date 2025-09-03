import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { ItemType, ItemStatus, MovementType, PurchaseOrderStatus } from '../types';

// Re-export currency formatter from utils package
export { formatCurrency } from '@dotmac/utils/formatting';

/**
 * Format quantities with units
 */
export function formatQuantity(quantity: number, unit: string = 'each'): string {
  const formatted = new Intl.NumberFormat().format(quantity);
  return `${formatted} ${unit}${quantity !== 1 ? 's' : ''}`;
}

/**
 * Format item codes with prefix
 */
export function formatItemCode(code: string, prefix?: string): string {
  if (prefix) {
    return `${prefix}-${code}`;
  }
  return code;
}

/**
 * Format serial numbers for display
 */
export function formatSerialNumber(serialNumber: string): string {
  // Add common formatting patterns for serial numbers
  if (serialNumber.length === 12 && /^[A-Z0-9]+$/.test(serialNumber)) {
    return serialNumber.replace(/(.{4})(.{4})(.{4})/, '$1-$2-$3');
  }
  return serialNumber;
}

/**
 * Format dates relative to now
 */
export function formatRelativeDate(date: string | Date): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  return formatDistanceToNow(dateObj, { addSuffix: true });
}

/**
 * Format dates for display
 */
export function formatDate(date: string | Date, formatStr: string = 'MMM d, yyyy'): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  return format(dateObj, formatStr);
}

/**
 * Format item type for display
 */
export function formatItemType(itemType: ItemType): string {
  const typeMap = {
    [ItemType.HARDWARE]: 'Hardware',
    [ItemType.SOFTWARE]: 'Software',
    [ItemType.CONSUMABLE]: 'Consumable',
    [ItemType.TOOL]: 'Tool',
    [ItemType.SPARE_PART]: 'Spare Part',
    [ItemType.KIT]: 'Kit',
    [ItemType.ACCESSORY]: 'Accessory',
    [ItemType.NETWORK_EQUIPMENT]: 'Network Equipment',
    [ItemType.CUSTOMER_PREMISES_EQUIPMENT]: 'CPE',
  };
  return typeMap[itemType] || itemType;
}

/**
 * Format item status for display
 */
export function formatItemStatus(status: ItemStatus): string {
  const statusMap = {
    [ItemStatus.AVAILABLE]: 'Available',
    [ItemStatus.RESERVED]: 'Reserved',
    [ItemStatus.ALLOCATED]: 'Allocated',
    [ItemStatus.IN_USE]: 'In Use',
    [ItemStatus.IN_REPAIR]: 'In Repair',
    [ItemStatus.RETIRED]: 'Retired',
    [ItemStatus.LOST]: 'Lost',
    [ItemStatus.QUARANTINED]: 'Quarantined',
  };
  return statusMap[status] || status;
}

/**
 * Format movement type for display
 */
export function formatMovementType(movementType: MovementType): string {
  const typeMap = {
    [MovementType.RECEIPT]: 'Receipt',
    [MovementType.ISSUE]: 'Issue',
    [MovementType.TRANSFER]: 'Transfer',
    [MovementType.ADJUSTMENT]: 'Adjustment',
    [MovementType.RETURN]: 'Return',
    [MovementType.WRITE_OFF]: 'Write Off',
    [MovementType.FOUND]: 'Found',
    [MovementType.INSTALLATION]: 'Installation',
    [MovementType.REPLACEMENT]: 'Replacement',
  };
  return typeMap[movementType] || movementType;
}

/**
 * Format PO status for display
 */
export function formatPOStatus(status: PurchaseOrderStatus): string {
  const statusMap = {
    [PurchaseOrderStatus.DRAFT]: 'Draft',
    [PurchaseOrderStatus.PENDING_APPROVAL]: 'Pending Approval',
    [PurchaseOrderStatus.APPROVED]: 'Approved',
    [PurchaseOrderStatus.SENT_TO_VENDOR]: 'Sent to Vendor',
    [PurchaseOrderStatus.PARTIALLY_RECEIVED]: 'Partially Received',
    [PurchaseOrderStatus.RECEIVED]: 'Received',
    [PurchaseOrderStatus.CANCELLED]: 'Cancelled',
    [PurchaseOrderStatus.CLOSED]: 'Closed',
  };
  return statusMap[status] || status;
}

/**
 * Format dimensions for display
 */
export function formatDimensions(
  dimensions: {
    length?: number;
    width?: number;
    height?: number;
  },
  unit: string = 'cm'
): string {
  const { length, width, height } = dimensions;
  const parts = [];

  if (length) parts.push(`L: ${length}${unit}`);
  if (width) parts.push(`W: ${width}${unit}`);
  if (height) parts.push(`H: ${height}${unit}`);

  return parts.join(' × ');
}

/**
 * Format weight for display
 */
export function formatWeight(weight: number, unit: string = 'kg'): string {
  if (weight < 1 && unit === 'kg') {
    return `${(weight * 1000).toFixed(0)}g`;
  }
  return `${weight.toFixed(1)}${unit}`;
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';

  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

/**
 * Format percentage for display
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format duration for display
 */
export function formatDuration(days: number): string {
  if (days < 1) {
    const hours = Math.round(days * 24);
    return `${hours} hour${hours !== 1 ? 's' : ''}`;
  } else if (days < 7) {
    return `${Math.round(days)} day${Math.round(days) !== 1 ? 's' : ''}`;
  } else if (days < 30) {
    const weeks = Math.round(days / 7);
    return `${weeks} week${weeks !== 1 ? 's' : ''}`;
  } else if (days < 365) {
    const months = Math.round(days / 30);
    return `${months} month${months !== 1 ? 's' : ''}`;
  } else {
    const years = Math.round(days / 365);
    return `${years} year${years !== 1 ? 's' : ''}`;
  }
}

/**
 * Format address for display
 */
export function formatAddress(address: {
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
}): string {
  const parts = [];

  if (address.address_line1) parts.push(address.address_line1);
  if (address.address_line2) parts.push(address.address_line2);

  const cityStateParts = [];
  if (address.city) cityStateParts.push(address.city);
  if (address.state_province) cityStateParts.push(address.state_province);
  if (address.postal_code) cityStateParts.push(address.postal_code);

  if (cityStateParts.length > 0) {
    parts.push(cityStateParts.join(', '));
  }

  if (address.country) parts.push(address.country);

  return parts.join('\n');
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}
