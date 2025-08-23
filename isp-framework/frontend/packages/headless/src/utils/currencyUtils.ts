/**
 * Currency Formatting and Utilities
 * 
 * Comprehensive currency formatting, conversion, and validation utilities
 * aligned with ISP business requirements and international markets.
 */

export type SupportedCurrency = 
  | 'USD' // US Dollar
  | 'EUR' // Euro
  | 'GBP' // British Pound
  | 'CAD' // Canadian Dollar
  | 'AUD' // Australian Dollar
  | 'JPY' // Japanese Yen
  | 'CHF' // Swiss Franc
  | 'CNY' // Chinese Yuan
  | 'INR' // Indian Rupee
  | 'MXN' // Mexican Peso
  | 'BRL' // Brazilian Real
  | 'KRW' // South Korean Won
  | 'SGD' // Singapore Dollar
  | 'HKD' // Hong Kong Dollar
  | 'NOK' // Norwegian Krone
  | 'SEK' // Swedish Krona
  | 'DKK' // Danish Krone
  | 'PLN' // Polish Zloty
  | 'CZK' // Czech Koruna
  | 'HUF'; // Hungarian Forint

export type CurrencyDisplayFormat =
  | 'symbol'     // $1,234.56
  | 'code'       // USD 1,234.56
  | 'name'       // 1,234.56 US dollars
  | 'symbol-narrow' // $1,234.56 (narrow symbol)
  | 'accounting' // ($1,234.56) for negatives
  | 'compact'    // $1.2K
  | 'compact-short'; // $1K

export type CurrencyPrecision = 0 | 1 | 2 | 3 | 4;

export interface CurrencyConfig {
  currency: SupportedCurrency;
  locale?: string;
  precision?: CurrencyPrecision;
  displayFormat?: CurrencyDisplayFormat;
  showZeroDecimals?: boolean;
  useGrouping?: boolean;
  signDisplay?: 'auto' | 'never' | 'always' | 'exceptZero';
}

export interface CurrencyInfo {
  code: SupportedCurrency;
  symbol: string;
  name: string;
  decimalPlaces: number;
  locale: string;
  region: string;
}

/**
 * Currency metadata for supported currencies
 */
const CURRENCY_INFO: Record<SupportedCurrency, CurrencyInfo> = {
  USD: { code: 'USD', symbol: '$', name: 'US Dollar', decimalPlaces: 2, locale: 'en-US', region: 'North America' },
  EUR: { code: 'EUR', symbol: '€', name: 'Euro', decimalPlaces: 2, locale: 'de-DE', region: 'Europe' },
  GBP: { code: 'GBP', symbol: '£', name: 'British Pound', decimalPlaces: 2, locale: 'en-GB', region: 'Europe' },
  CAD: { code: 'CAD', symbol: 'CA$', name: 'Canadian Dollar', decimalPlaces: 2, locale: 'en-CA', region: 'North America' },
  AUD: { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', decimalPlaces: 2, locale: 'en-AU', region: 'Oceania' },
  JPY: { code: 'JPY', symbol: '¥', name: 'Japanese Yen', decimalPlaces: 0, locale: 'ja-JP', region: 'Asia' },
  CHF: { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', decimalPlaces: 2, locale: 'de-CH', region: 'Europe' },
  CNY: { code: 'CNY', symbol: '¥', name: 'Chinese Yuan', decimalPlaces: 2, locale: 'zh-CN', region: 'Asia' },
  INR: { code: 'INR', symbol: '₹', name: 'Indian Rupee', decimalPlaces: 2, locale: 'hi-IN', region: 'Asia' },
  MXN: { code: 'MXN', symbol: 'MX$', name: 'Mexican Peso', decimalPlaces: 2, locale: 'es-MX', region: 'North America' },
  BRL: { code: 'BRL', symbol: 'R$', name: 'Brazilian Real', decimalPlaces: 2, locale: 'pt-BR', region: 'South America' },
  KRW: { code: 'KRW', symbol: '₩', name: 'South Korean Won', decimalPlaces: 0, locale: 'ko-KR', region: 'Asia' },
  SGD: { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar', decimalPlaces: 2, locale: 'en-SG', region: 'Asia' },
  HKD: { code: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar', decimalPlaces: 2, locale: 'en-HK', region: 'Asia' },
  NOK: { code: 'NOK', symbol: 'kr', name: 'Norwegian Krone', decimalPlaces: 2, locale: 'nb-NO', region: 'Europe' },
  SEK: { code: 'SEK', symbol: 'kr', name: 'Swedish Krona', decimalPlaces: 2, locale: 'sv-SE', region: 'Europe' },
  DKK: { code: 'DKK', symbol: 'kr', name: 'Danish Krone', decimalPlaces: 2, locale: 'da-DK', region: 'Europe' },
  PLN: { code: 'PLN', symbol: 'zł', name: 'Polish Zloty', decimalPlaces: 2, locale: 'pl-PL', region: 'Europe' },
  CZK: { code: 'CZK', symbol: 'Kč', name: 'Czech Koruna', decimalPlaces: 2, locale: 'cs-CZ', region: 'Europe' },
  HUF: { code: 'HUF', symbol: 'Ft', name: 'Hungarian Forint', decimalPlaces: 0, locale: 'hu-HU', region: 'Europe' }
};

/**
 * Main CurrencyUtils class
 */
export class CurrencyUtils {
  private static defaultConfig: CurrencyConfig = {
    currency: 'USD',
    locale: 'en-US',
    precision: 2,
    displayFormat: 'symbol',
    showZeroDecimals: true,
    useGrouping: true,
    signDisplay: 'auto'
  };

  /**
   * Set global default currency configuration
   */
  static setDefaultConfig(config: Partial<CurrencyConfig>): void {
    this.defaultConfig = { ...this.defaultConfig, ...config };
  }

  /**
   * Get currency information
   */
  static getCurrencyInfo(currency: SupportedCurrency): CurrencyInfo {
    return CURRENCY_INFO[currency];
  }

  /**
   * Get all supported currencies
   */
  static getSupportedCurrencies(): CurrencyInfo[] {
    return Object.values(CURRENCY_INFO);
  }

  /**
   * Format currency amount with full configuration support
   */
  static format(
    amount: number | string | null | undefined,
    config: Partial<CurrencyConfig> = {}
  ): string {
    const numericAmount = this.parseAmount(amount);
    if (numericAmount === null) return 'Invalid Amount';

    const finalConfig = { ...this.defaultConfig, ...config };
    const currencyInfo = CURRENCY_INFO[finalConfig.currency];
    const locale = finalConfig.locale || currencyInfo.locale;
    const precision = finalConfig.precision ?? currencyInfo.decimalPlaces;

    try {
      // Handle compact formats
      if (finalConfig.displayFormat === 'compact' || finalConfig.displayFormat === 'compact-short') {
        return this.formatCompact(numericAmount, finalConfig);
      }

      const formatter = new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: finalConfig.currency,
        minimumFractionDigits: finalConfig.showZeroDecimals ? precision : 0,
        maximumFractionDigits: precision,
        useGrouping: finalConfig.useGrouping,
        signDisplay: finalConfig.signDisplay,
        currencyDisplay: this.mapDisplayFormat(finalConfig.displayFormat),
        notation: finalConfig.displayFormat === 'accounting' ? 'standard' : 'standard'
      });

      let formatted = formatter.format(numericAmount);

      // Handle accounting format for negatives
      if (finalConfig.displayFormat === 'accounting' && numericAmount < 0) {
        formatted = formatted.replace('-', '');
        formatted = `(${formatted})`;
      }

      return formatted;
    } catch (error) {
      // Fallback formatting
      return this.formatFallback(numericAmount, finalConfig);
    }
  }

  /**
   * Format compact currency (e.g., $1.2K, $1M)
   */
  private static formatCompact(amount: number, config: CurrencyConfig): string {
    const absAmount = Math.abs(amount);
    const isNegative = amount < 0;
    const currencyInfo = CURRENCY_INFO[config.currency];
    
    let value: number;
    let suffix: string;

    if (absAmount >= 1e12) {
      value = absAmount / 1e12;
      suffix = 'T';
    } else if (absAmount >= 1e9) {
      value = absAmount / 1e9;
      suffix = 'B';
    } else if (absAmount >= 1e6) {
      value = absAmount / 1e6;
      suffix = 'M';
    } else if (absAmount >= 1e3) {
      value = absAmount / 1e3;
      suffix = 'K';
    } else {
      return this.format(amount, { ...config, displayFormat: 'symbol' });
    }

    const precision = value >= 10 ? 0 : 1;
    const formattedValue = value.toFixed(precision).replace(/\.0$/, '');
    const sign = isNegative ? '-' : '';
    
    return `${sign}${currencyInfo.symbol}${formattedValue}${suffix}`;
  }

  /**
   * Map display format to Intl.NumberFormat currencyDisplay
   */
  private static mapDisplayFormat(format?: CurrencyDisplayFormat): 'symbol' | 'narrowSymbol' | 'code' | 'name' {
    switch (format) {
      case 'code':
        return 'code';
      case 'name':
        return 'name';
      case 'symbol-narrow':
        return 'narrowSymbol';
      default:
        return 'symbol';
    }
  }

  /**
   * Fallback formatting when Intl.NumberFormat fails
   */
  private static formatFallback(amount: number, config: CurrencyConfig): string {
    const currencyInfo = CURRENCY_INFO[config.currency];
    const precision = config.precision ?? currencyInfo.decimalPlaces;
    const isNegative = amount < 0;
    const absAmount = Math.abs(amount);
    
    let formattedAmount = absAmount.toFixed(precision);
    
    // Add thousand separators
    if (config.useGrouping) {
      const parts = formattedAmount.split('.');
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      formattedAmount = parts.join('.');
    }
    
    // Add currency symbol
    const symbol = currencyInfo.symbol;
    let result = `${symbol}${formattedAmount}`;
    
    // Handle negative amounts
    if (isNegative) {
      if (config.displayFormat === 'accounting') {
        result = `(${result})`;
      } else {
        result = `-${result}`;
      }
    }
    
    return result;
  }

  /**
   * Parse amount from various input types
   */
  static parseAmount(input: number | string | null | undefined): number | null {
    if (input === null || input === undefined) return null;
    
    if (typeof input === 'number') {
      return isNaN(input) || !isFinite(input) ? null : input;
    }
    
    if (typeof input === 'string') {
      // Remove currency symbols, spaces, and other non-numeric characters except decimal point and minus sign
      const cleaned = input
        .replace(/[^\d.-]/g, '')
        .replace(/^-?/, match => match); // Keep only the first minus sign
      
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? null : parsed;
    }
    
    return null;
  }

  /**
   * Validate currency amount
   */
  static validate(
    amount: number | string | null | undefined,
    options: {
      min?: number;
      max?: number;
      allowNegative?: boolean;
      allowZero?: boolean;
    } = {}
  ): { isValid: boolean; errors: string[] } {
    const { min, max, allowNegative = false, allowZero = true } = options;
    const errors: string[] = [];
    
    const numericAmount = this.parseAmount(amount);
    
    if (numericAmount === null) {
      errors.push('Invalid amount format');
      return { isValid: false, errors };
    }
    
    if (!allowNegative && numericAmount < 0) {
      errors.push('Amount cannot be negative');
    }
    
    if (!allowZero && numericAmount === 0) {
      errors.push('Amount cannot be zero');
    }
    
    if (min !== undefined && numericAmount < min) {
      errors.push(`Amount must be at least ${this.format(min)}`);
    }
    
    if (max !== undefined && numericAmount > max) {
      errors.push(`Amount must not exceed ${this.format(max)}`);
    }
    
    return { isValid: errors.length === 0, errors };
  }

  /**
   * Calculate percentage of total
   */
  static calculatePercentage(
    amount: number | string,
    total: number | string,
    precision: number = 1
  ): string {
    const numericAmount = this.parseAmount(amount);
    const numericTotal = this.parseAmount(total);
    
    if (numericAmount === null || numericTotal === null || numericTotal === 0) {
      return '0%';
    }
    
    const percentage = (numericAmount / numericTotal) * 100;
    return `${percentage.toFixed(precision)}%`;
  }

  /**
   * Add two currency amounts
   */
  static add(...amounts: (number | string | null | undefined)[]): number {
    return amounts.reduce((sum, amount) => {
      const parsed = this.parseAmount(amount);
      return sum + (parsed || 0);
    }, 0);
  }

  /**
   * Subtract currency amounts
   */
  static subtract(
    minuend: number | string | null | undefined,
    ...subtrahends: (number | string | null | undefined)[]
  ): number {
    const baseAmount = this.parseAmount(minuend) || 0;
    const totalSubtraction = subtrahends.reduce((sum, amount) => {
      const parsed = this.parseAmount(amount);
      return sum + (parsed || 0);
    }, 0);
    
    return baseAmount - totalSubtraction;
  }

  /**
   * Multiply currency amount by a factor
   */
  static multiply(
    amount: number | string | null | undefined,
    factor: number
  ): number {
    const numericAmount = this.parseAmount(amount);
    return (numericAmount || 0) * factor;
  }

  /**
   * Divide currency amount by a divisor
   */
  static divide(
    amount: number | string | null | undefined,
    divisor: number
  ): number {
    const numericAmount = this.parseAmount(amount);
    return divisor !== 0 ? (numericAmount || 0) / divisor : 0;
  }

  /**
   * Apply percentage to currency amount
   */
  static applyPercentage(
    amount: number | string | null | undefined,
    percentage: number
  ): number {
    const numericAmount = this.parseAmount(amount);
    return (numericAmount || 0) * (percentage / 100);
  }

  /**
   * Round to currency precision
   */
  static round(
    amount: number | string | null | undefined,
    currency: SupportedCurrency = 'USD'
  ): number {
    const numericAmount = this.parseAmount(amount);
    if (numericAmount === null) return 0;
    
    const precision = CURRENCY_INFO[currency].decimalPlaces;
    const factor = Math.pow(10, precision);
    
    return Math.round(numericAmount * factor) / factor;
  }

  /**
   * Convert to cents/smallest unit (for API/database storage)
   */
  static toCents(
    amount: number | string | null | undefined,
    currency: SupportedCurrency = 'USD'
  ): number {
    const numericAmount = this.parseAmount(amount);
    if (numericAmount === null) return 0;
    
    const precision = CURRENCY_INFO[currency].decimalPlaces;
    const factor = Math.pow(10, precision);
    
    return Math.round(numericAmount * factor);
  }

  /**
   * Convert from cents/smallest unit
   */
  static fromCents(
    cents: number,
    currency: SupportedCurrency = 'USD'
  ): number {
    const precision = CURRENCY_INFO[currency].decimalPlaces;
    const factor = Math.pow(10, precision);
    
    return cents / factor;
  }

  /**
   * Format currency range
   */
  static formatRange(
    minAmount: number | string | null | undefined,
    maxAmount: number | string | null | undefined,
    config: Partial<CurrencyConfig> = {},
    separator: string = ' - '
  ): string {
    const minFormatted = this.format(minAmount, config);
    const maxFormatted = this.format(maxAmount, config);
    
    return `${minFormatted}${separator}${maxFormatted}`;
  }

  /**
   * Get currency symbol only
   */
  static getSymbol(currency: SupportedCurrency): string {
    return CURRENCY_INFO[currency].symbol;
  }

  /**
   * Compare two currency amounts
   */
  static compare(
    amount1: number | string | null | undefined,
    amount2: number | string | null | undefined
  ): -1 | 0 | 1 {
    const num1 = this.parseAmount(amount1) || 0;
    const num2 = this.parseAmount(amount2) || 0;
    
    if (num1 < num2) return -1;
    if (num1 > num2) return 1;
    return 0;
  }

  /**
   * Check if amount is zero
   */
  static isZero(amount: number | string | null | undefined): boolean {
    const parsed = this.parseAmount(amount);
    return parsed === 0;
  }

  /**
   * Check if amount is positive
   */
  static isPositive(amount: number | string | null | undefined): boolean {
    const parsed = this.parseAmount(amount);
    return parsed !== null && parsed > 0;
  }

  /**
   * Check if amount is negative
   */
  static isNegative(amount: number | string | null | undefined): boolean {
    const parsed = this.parseAmount(amount);
    return parsed !== null && parsed < 0;
  }
}

/**
 * ISP-specific currency utilities
 */
export const ISPCurrencyUtils = {
  /**
   * Format for invoice line items
   */
  formatLineItem: (amount: number | string | null | undefined, currency: SupportedCurrency = 'USD') =>
    CurrencyUtils.format(amount, { currency, precision: 2, displayFormat: 'symbol' }),

  /**
   * Format for invoice totals (with emphasis)
   */
  formatTotal: (amount: number | string | null | undefined, currency: SupportedCurrency = 'USD') =>
    CurrencyUtils.format(amount, { currency, precision: 2, displayFormat: 'symbol', showZeroDecimals: true }),

  /**
   * Format for payment amounts
   */
  formatPayment: (amount: number | string | null | undefined, currency: SupportedCurrency = 'USD') =>
    CurrencyUtils.format(amount, { currency, precision: 2, displayFormat: 'symbol' }),

  /**
   * Format for service pricing
   */
  formatServicePrice: (amount: number | string | null | undefined, currency: SupportedCurrency = 'USD', period?: string) => {
    const formatted = CurrencyUtils.format(amount, { currency, precision: 2 });
    return period ? `${formatted}/${period}` : formatted;
  },

  /**
   * Calculate tax amount
   */
  calculateTax: (amount: number | string | null | undefined, taxRate: number) => {
    return CurrencyUtils.applyPercentage(amount, taxRate);
  },

  /**
   * Calculate discount amount
   */
  calculateDiscount: (amount: number | string | null | undefined, discountRate: number) => {
    return CurrencyUtils.applyPercentage(amount, discountRate);
  },

  /**
   * Calculate invoice total with tax and discount
   */
  calculateInvoiceTotal: (
    subtotal: number | string | null | undefined,
    taxRate: number = 0,
    discountRate: number = 0
  ): { subtotal: number; taxAmount: number; discountAmount: number; total: number } => {
    const numericSubtotal = CurrencyUtils.parseAmount(subtotal) || 0;
    const discountAmount = CurrencyUtils.applyPercentage(numericSubtotal, discountRate);
    const discountedAmount = numericSubtotal - discountAmount;
    const taxAmount = CurrencyUtils.applyPercentage(discountedAmount, taxRate);
    const total = discountedAmount + taxAmount;

    return {
      subtotal: numericSubtotal,
      taxAmount,
      discountAmount,
      total
    };
  },

  /**
   * Format for dashboard metrics
   */
  formatMetric: (amount: number | string | null | undefined, currency: SupportedCurrency = 'USD') =>
    CurrencyUtils.format(amount, { currency, displayFormat: 'compact' }),

  /**
   * Validate payment amount
   */
  validatePayment: (
    amount: number | string | null | undefined,
    maxAmount?: number | string | null | undefined
  ) => {
    return CurrencyUtils.validate(amount, {
      min: 0.01,
      max: maxAmount ? CurrencyUtils.parseAmount(maxAmount) || undefined : undefined,
      allowNegative: false,
      allowZero: false
    });
  }
};

// Convenience exports
export const formatCurrency = CurrencyUtils.format;
export const parseCurrency = CurrencyUtils.parseAmount;
export const validateCurrency = CurrencyUtils.validate;
export const getCurrencyInfo = CurrencyUtils.getCurrencyInfo;
export const getSupportedCurrencies = CurrencyUtils.getSupportedCurrencies;

export default CurrencyUtils;