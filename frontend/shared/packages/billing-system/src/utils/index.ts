import { format } from 'date-fns';

// Re-export cn utility from canonical source
export { cn } from '@dotmac/primitives/utils';

/**
 * Currency formatting utility
 */
export const formatCurrency = (
  amount: number,
  currency: string = 'USD',
  locale: string = 'en-US'
): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

/**
 * Date formatting utilities
 */
export const formatDate = (date: Date | string, formatString: string = 'MMM dd, yyyy'): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, formatString);
};

export const formatDateShort = (date: Date | string): string => {
  return formatDate(date, 'MM/dd/yy');
};

export const formatDateLong = (date: Date | string): string => {
  return formatDate(date, 'MMMM dd, yyyy');
};

export const formatDateTime = (date: Date | string): string => {
  return formatDate(date, 'MMM dd, yyyy h:mm a');
};

/**
 * Payment status utilities
 */
export const getPaymentStatusColor = (status: string): string => {
  const statusColors: Record<string, string> = {
    completed: 'text-green-600 bg-green-50 border-green-200',
    paid: 'text-green-600 bg-green-50 border-green-200',
    pending: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    processing: 'text-blue-600 bg-blue-50 border-blue-200',
    failed: 'text-red-600 bg-red-50 border-red-200',
    overdue: 'text-red-600 bg-red-50 border-red-200',
    cancelled: 'text-gray-600 bg-gray-50 border-gray-200',
    refunded: 'text-purple-600 bg-purple-50 border-purple-200',
    draft: 'text-gray-600 bg-gray-50 border-gray-200',
    sent: 'text-blue-600 bg-blue-50 border-blue-200',
  };

  return statusColors[status?.toLowerCase() || 'draft'] || statusColors.draft;
};

export const getPaymentStatusIcon = (status: string): string => {
  const statusIcons: Record<string, string> = {
    completed: '✓',
    paid: '✓',
    pending: '⏳',
    processing: '⏳',
    failed: '✗',
    overdue: '⚠️',
    cancelled: '⛔',
    refunded: '↩️',
    draft: '📝',
    sent: '📧',
  };

  return statusIcons[status.toLowerCase()] || '❓';
};

/**
 * Payment method utilities
 */
export const formatPaymentMethod = (method: {
  type: string;
  brand?: string;
  last4?: string;
  lastFour?: string;
}): string => {
  const lastFour = method.last4 || method.lastFour || '0000';

  if (method.type === 'credit_card' && method.brand) {
    return `${method.brand} •••• ${lastFour}`;
  }

  const typeNames: Record<string, string> = {
    credit_card: 'Card',
    bank_account: 'Bank',
    paypal: 'PayPal',
    crypto: 'Crypto',
  };

  return `${typeNames[method.type] || method.type} •••• ${lastFour}`;
};

/**
 * Validation utilities
 */
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validateAmount = (amount: number, min: number = 0.01): boolean => {
  return amount >= min && amount <= 999999.99;
};

export const validateCreditCard = (cardNumber: string): boolean => {
  // Basic Luhn algorithm check
  const digits = cardNumber.replace(/\D/g, '');
  if (digits.length < 13 || digits.length > 19) return false;

  let sum = 0;
  let isEven = false;

  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = parseInt(digits.charAt(i), 10);

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  return sum % 10 === 0;
};

/**
 * Calculation utilities
 */
export const calculateTax = (amount: number, taxRate: number): number => {
  return Math.round(amount * taxRate * 100) / 100;
};

export const calculateTotal = (amount: number, tax: number): number => {
  return Math.round((amount + tax) * 100) / 100;
};

export const calculatePercentage = (value: number, total: number): number => {
  if (total === 0) return 0;
  return Math.round((value / total) * 100 * 10) / 10;
};

/**
 * Data transformation utilities
 */
export const groupByStatus = <T extends { status: string }>(items: T[]): Record<string, T[]> => {
  return items.reduce(
    (groups, item) => {
      const status = item.status;
      if (!groups[status]) {
        groups[status] = [];
      }
      groups[status].push(item);
      return groups;
    },
    {} as Record<string, T[]>
  );
};

export const sortByDate = <T extends { createdAt: Date | string }>(
  items: T[],
  direction: 'asc' | 'desc' = 'desc'
): T[] => {
  return [...items].sort((a, b) => {
    const dateA = typeof a.createdAt === 'string' ? new Date(a.createdAt) : a.createdAt;
    const dateB = typeof b.createdAt === 'string' ? new Date(b.createdAt) : b.createdAt;

    if (direction === 'asc') {
      return dateA.getTime() - dateB.getTime();
    }
    return dateB.getTime() - dateA.getTime();
  });
};

/**
 * Error handling utilities
 */
export const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as any).message);
  }

  return 'An unexpected error occurred';
};

/**
 * Portal type utilities
 */
export const getPortalFeatures = (portalType: 'admin' | 'customer' | 'reseller' | 'management') => {
  const featureMatrix = {
    admin: {
      invoiceGeneration: true,
      paymentProcessing: true,
      refunds: true,
      reporting: true,
      bulkOperations: true,
      automations: true,
      analytics: true,
    },
    customer: {
      invoiceGeneration: false,
      paymentProcessing: true,
      refunds: false,
      reporting: false,
      bulkOperations: false,
      automations: false,
      analytics: false,
    },
    reseller: {
      invoiceGeneration: true,
      paymentProcessing: true,
      refunds: true,
      reporting: true,
      bulkOperations: true,
      automations: false,
      analytics: true,
    },
    management: {
      invoiceGeneration: true,
      paymentProcessing: true,
      refunds: true,
      reporting: true,
      bulkOperations: true,
      automations: true,
      analytics: true,
    },
  };

  return featureMatrix[portalType];
};

/**
 * Search and filter utilities
 */
export const filterBySearch = <T>(
  items: T[],
  searchQuery: string,
  searchFields: (keyof T)[]
): T[] => {
  if (!searchQuery.trim()) return items;

  const query = searchQuery.toLowerCase();

  return items.filter((item) =>
    searchFields.some((field) => {
      const value = item[field];
      if (typeof value === 'string') {
        return value.toLowerCase().includes(query);
      }
      if (typeof value === 'number') {
        return value.toString().includes(query);
      }
      return false;
    })
  );
};

export const applyFilters = <T>(items: T[], filters: Record<string, any>): T[] => {
  return items.filter((item) => {
    return Object.entries(filters).every(([key, value]) => {
      if (!value || value === '') return true;

      const itemValue = (item as any)[key];

      if (Array.isArray(value)) {
        return value.includes(itemValue);
      }

      if (typeof value === 'string' && typeof itemValue === 'string') {
        return itemValue.toLowerCase().includes(value.toLowerCase());
      }

      return itemValue === value;
    });
  });
};

/**
 * Debounce utility
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;

  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};
