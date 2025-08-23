/**
 * Date and Time Utilities
 * 
 * Comprehensive date/time formatting and manipulation utilities
 * aligned with ISP business requirements and internationalization.
 */

import { format, parseISO, isValid, differenceInDays, differenceInHours, differenceInMinutes, addDays, addMonths, startOfMonth, endOfMonth, startOfDay, endOfDay } from 'date-fns';
import { enUS, es, fr, de } from 'date-fns/locale';

export type DateFormat = 
  | 'short'      // 12/31/2023
  | 'medium'     // Dec 31, 2023
  | 'long'       // December 31, 2023
  | 'full'       // Sunday, December 31, 2023
  | 'iso'        // 2023-12-31
  | 'api'        // 2023-12-31T23:59:59.999Z
  | 'display'    // Dec 31, 2023 at 11:59 PM
  | 'billing'    // Invoice: 2023-12-31
  | 'compact';   // 12/31/23

export type TimeFormat =
  | 'short'      // 11:59 PM
  | 'medium'     // 11:59:59 PM
  | 'long'       // 11:59:59 PM EST
  | '24hour'     // 23:59
  | '24hour-sec' // 23:59:59
  | 'iso'        // T23:59:59.999Z
  | 'timestamp'; // Unix timestamp

export type RelativeTimeFormat =
  | 'short'      // 2d ago
  | 'long'       // 2 days ago
  | 'precise';   // 2 days, 3 hours ago

export type SupportedLocale = 'en-US' | 'es-ES' | 'fr-FR' | 'de-DE';

const localeMap = {
  'en-US': enUS,
  'es-ES': es,
  'fr-FR': fr,
  'de-DE': de,
};

/**
 * Main DateTimeUtils class with comprehensive formatting options
 */
export class DateTimeUtils {
  private static defaultLocale: SupportedLocale = 'en-US';
  private static defaultTimezone = 'America/New_York'; // ISP default timezone

  /**
   * Set global default locale
   */
  static setDefaultLocale(locale: SupportedLocale): void {
    this.defaultLocale = locale;
  }

  /**
   * Set global default timezone
   */
  static setDefaultTimezone(timezone: string): void {
    this.defaultTimezone = timezone;
  }

  /**
   * Parse date from various input formats
   */
  static parseDate(input: string | Date | number | null | undefined): Date | null {
    if (!input) return null;
    
    try {
      if (input instanceof Date) {
        return isValid(input) ? input : null;
      }
      
      if (typeof input === 'number') {
        return new Date(input);
      }
      
      if (typeof input === 'string') {
        // Handle ISO strings
        if (input.includes('T') || input.includes('Z')) {
          const parsed = parseISO(input);
          return isValid(parsed) ? parsed : null;
        }
        
        // Handle other string formats
        const parsed = new Date(input);
        return isValid(parsed) ? parsed : null;
      }
    } catch {
      return null;
    }
    
    return null;
  }

  /**
   * Format date with specified format and locale
   */
  static formatDate(
    date: string | Date | number | null | undefined,
    formatType: DateFormat = 'medium',
    locale: SupportedLocale = this.defaultLocale
  ): string {
    const parsedDate = this.parseDate(date);
    if (!parsedDate) return 'Invalid Date';

    const localeObj = localeMap[locale];

    try {
      switch (formatType) {
        case 'short':
          return format(parsedDate, 'M/d/yyyy', { locale: localeObj });
        case 'medium':
          return format(parsedDate, 'MMM d, yyyy', { locale: localeObj });
        case 'long':
          return format(parsedDate, 'MMMM d, yyyy', { locale: localeObj });
        case 'full':
          return format(parsedDate, 'EEEE, MMMM d, yyyy', { locale: localeObj });
        case 'iso':
          return format(parsedDate, 'yyyy-MM-dd');
        case 'api':
          return parsedDate.toISOString();
        case 'display':
          return format(parsedDate, 'MMM d, yyyy \'at\' h:mm a', { locale: localeObj });
        case 'billing':
          return format(parsedDate, 'yyyy-MM-dd');
        case 'compact':
          return format(parsedDate, 'M/d/yy', { locale: localeObj });
        default:
          return format(parsedDate, 'MMM d, yyyy', { locale: localeObj });
      }
    } catch {
      return 'Format Error';
    }
  }

  /**
   * Format time with specified format and locale
   */
  static formatTime(
    date: string | Date | number | null | undefined,
    formatType: TimeFormat = 'short',
    locale: SupportedLocale = this.defaultLocale
  ): string {
    const parsedDate = this.parseDate(date);
    if (!parsedDate) return 'Invalid Time';

    const localeObj = localeMap[locale];

    try {
      switch (formatType) {
        case 'short':
          return format(parsedDate, 'h:mm a', { locale: localeObj });
        case 'medium':
          return format(parsedDate, 'h:mm:ss a', { locale: localeObj });
        case 'long':
          return format(parsedDate, 'h:mm:ss a zzz', { locale: localeObj });
        case '24hour':
          return format(parsedDate, 'HH:mm');
        case '24hour-sec':
          return format(parsedDate, 'HH:mm:ss');
        case 'iso':
          return format(parsedDate, "'T'HH:mm:ss.SSSxxx");
        case 'timestamp':
          return parsedDate.getTime().toString();
        default:
          return format(parsedDate, 'h:mm a', { locale: localeObj });
      }
    } catch {
      return 'Format Error';
    }
  }

  /**
   * Format date and time together
   */
  static formatDateTime(
    date: string | Date | number | null | undefined,
    dateFormat: DateFormat = 'medium',
    timeFormat: TimeFormat = 'short',
    locale: SupportedLocale = this.defaultLocale,
    separator = ' at '
  ): string {
    const dateStr = this.formatDate(date, dateFormat, locale);
    const timeStr = this.formatTime(date, timeFormat, locale);
    
    if (dateStr === 'Invalid Date' || timeStr === 'Invalid Time') {
      return 'Invalid DateTime';
    }
    
    return `${dateStr}${separator}${timeStr}`;
  }

  /**
   * Format relative time (e.g., "2 days ago", "in 5 minutes")
   */
  static formatRelativeTime(
    date: string | Date | number | null | undefined,
    formatType: RelativeTimeFormat = 'long',
    locale: SupportedLocale = this.defaultLocale
  ): string {
    const parsedDate = this.parseDate(date);
    if (!parsedDate) return 'Unknown';

    const now = new Date();
    const diffInMinutes = differenceInMinutes(now, parsedDate);
    const diffInHours = differenceInHours(now, parsedDate);
    const diffInDays = differenceInDays(now, parsedDate);

    const isPast = diffInMinutes > 0;
    const suffix = isPast ? (formatType === 'short' ? '' : ' ago') : (formatType === 'short' ? '' : ' from now');
    const prefix = isPast ? '' : (formatType === 'short' ? 'in ' : '');

    const absDays = Math.abs(diffInDays);
    const absHours = Math.abs(diffInHours);
    const absMinutes = Math.abs(diffInMinutes);

    if (formatType === 'short') {
      if (absDays > 0) return `${prefix}${absDays}d${suffix}`;
      if (absHours > 0) return `${prefix}${absHours}h${suffix}`;
      if (absMinutes > 0) return `${prefix}${absMinutes}m${suffix}`;
      return 'now';
    }

    if (formatType === 'precise') {
      const parts = [];
      if (absDays > 0) parts.push(`${absDays} day${absDays !== 1 ? 's' : ''}`);
      if (absHours % 24 > 0) parts.push(`${absHours % 24} hour${(absHours % 24) !== 1 ? 's' : ''}`);
      if (parts.length === 0 && absMinutes > 0) parts.push(`${absMinutes} minute${absMinutes !== 1 ? 's' : ''}`);
      
      if (parts.length === 0) return 'just now';
      return `${prefix}${parts.join(', ')}${suffix}`;
    }

    // Default 'long' format
    if (absDays >= 1) {
      return `${prefix}${absDays} day${absDays !== 1 ? 's' : ''}${suffix}`;
    }
    if (absHours >= 1) {
      return `${prefix}${absHours} hour${absHours !== 1 ? 's' : ''}${suffix}`;
    }
    if (absMinutes >= 1) {
      return `${prefix}${absMinutes} minute${absMinutes !== 1 ? 's' : ''}${suffix}`;
    }
    return 'just now';
  }

  /**
   * Get duration between two dates
   */
  static getDuration(
    startDate: string | Date | number | null | undefined,
    endDate: string | Date | number | null | undefined,
    format: 'days' | 'hours' | 'minutes' | 'auto' = 'auto'
  ): string {
    const start = this.parseDate(startDate);
    const end = this.parseDate(endDate);
    
    if (!start || !end) return 'Unknown duration';

    const diffInMinutes = Math.abs(differenceInMinutes(end, start));
    const diffInHours = Math.abs(differenceInHours(end, start));
    const diffInDays = Math.abs(differenceInDays(end, start));

    switch (format) {
      case 'days':
        return `${diffInDays} day${diffInDays !== 1 ? 's' : ''}`;
      case 'hours':
        return `${diffInHours} hour${diffInHours !== 1 ? 's' : ''}`;
      case 'minutes':
        return `${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''}`;
      case 'auto':
        if (diffInDays >= 1) return `${diffInDays} day${diffInDays !== 1 ? 's' : ''}`;
        if (diffInHours >= 1) return `${diffInHours} hour${diffInHours !== 1 ? 's' : ''}`;
        return `${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''}`;
      default:
        return `${diffInDays} days`;
    }
  }

  /**
   * Check if a date is within a specific range
   */
  static isWithinRange(
    date: string | Date | number | null | undefined,
    startDate: string | Date | number | null | undefined,
    endDate: string | Date | number | null | undefined
  ): boolean {
    const targetDate = this.parseDate(date);
    const start = this.parseDate(startDate);
    const end = this.parseDate(endDate);

    if (!targetDate || !start || !end) return false;
    
    return targetDate >= start && targetDate <= end;
  }

  /**
   * Generate date ranges for billing periods
   */
  static getBillingPeriod(
    periodType: 'monthly' | 'quarterly' | 'yearly',
    referenceDate: string | Date | number | null | undefined = new Date()
  ): { start: Date; end: Date; label: string } | null {
    const date = this.parseDate(referenceDate);
    if (!date) return null;

    switch (periodType) {
      case 'monthly':
        const monthStart = startOfMonth(date);
        const monthEnd = endOfMonth(date);
        return {
          start: monthStart,
          end: monthEnd,
          label: this.formatDate(monthStart, 'long')
        };
      
      case 'quarterly':
        const quarterMonth = Math.floor(date.getMonth() / 3) * 3;
        const quarterStart = startOfMonth(new Date(date.getFullYear(), quarterMonth, 1));
        const quarterEnd = endOfMonth(addMonths(quarterStart, 2));
        return {
          start: quarterStart,
          end: quarterEnd,
          label: `Q${Math.floor(quarterMonth / 3) + 1} ${date.getFullYear()}`
        };
      
      case 'yearly':
        const yearStart = new Date(date.getFullYear(), 0, 1);
        const yearEnd = new Date(date.getFullYear(), 11, 31, 23, 59, 59, 999);
        return {
          start: yearStart,
          end: yearEnd,
          label: date.getFullYear().toString()
        };
    }
  }

  /**
   * Calculate next due date for invoices
   */
  static calculateNextDueDate(
    issueDate: string | Date | number | null | undefined,
    paymentTerms: number = 30
  ): Date | null {
    const issue = this.parseDate(issueDate);
    if (!issue) return null;
    
    return addDays(issue, paymentTerms);
  }

  /**
   * Check if invoice/payment is overdue
   */
  static isOverdue(dueDate: string | Date | number | null | undefined): boolean {
    const due = this.parseDate(dueDate);
    if (!due) return false;
    
    return new Date() > endOfDay(due);
  }

  /**
   * Get days until due date (negative if overdue)
   */
  static getDaysUntilDue(dueDate: string | Date | number | null | undefined): number | null {
    const due = this.parseDate(dueDate);
    if (!due) return null;
    
    return differenceInDays(due, startOfDay(new Date()));
  }

  /**
   * Format for invoice numbers and similar
   */
  static formatInvoiceDate(date: string | Date | number | null | undefined): string {
    return this.formatDate(date, 'billing');
  }

  /**
   * Get business hours status
   */
  static isBusinessHours(
    date: string | Date | number | null | undefined = new Date(),
    startHour = 9,
    endHour = 17,
    timezone?: string
  ): boolean {
    const targetDate = this.parseDate(date);
    if (!targetDate) return false;

    // Convert to target timezone if provided
    let checkDate = targetDate;
    if (timezone && timezone !== 'UTC') {
      try {
        checkDate = new Date(targetDate.toLocaleString('en-US', { timeZone: timezone }));
      } catch {
        // Fallback to original date if timezone conversion fails
      }
    }

    const hour = checkDate.getHours();
    const day = checkDate.getDay(); // 0 = Sunday, 6 = Saturday

    // Check if it's a weekday (Monday to Friday)
    const isWeekday = day >= 1 && day <= 5;
    
    // Check if it's within business hours
    const isWorkingHours = hour >= startHour && hour < endHour;

    return isWeekday && isWorkingHours;
  }

  /**
   * Create date range options for filters
   */
  static getDateRangeOptions(): Array<{ label: string; value: string; start: Date; end: Date }> {
    const now = new Date();
    const today = startOfDay(now);
    const yesterday = startOfDay(addDays(now, -1));
    const thisWeekStart = startOfDay(addDays(now, -now.getDay()));
    const lastWeekStart = startOfDay(addDays(thisWeekStart, -7));
    const thisMonthStart = startOfMonth(now);
    const lastMonthStart = startOfMonth(addDays(thisMonthStart, -1));

    return [
      {
        label: 'Today',
        value: 'today',
        start: today,
        end: endOfDay(now)
      },
      {
        label: 'Yesterday',
        value: 'yesterday',
        start: yesterday,
        end: endOfDay(yesterday)
      },
      {
        label: 'This Week',
        value: 'this_week',
        start: thisWeekStart,
        end: endOfDay(now)
      },
      {
        label: 'Last Week',
        value: 'last_week',
        start: lastWeekStart,
        end: endOfDay(addDays(thisWeekStart, -1))
      },
      {
        label: 'This Month',
        value: 'this_month',
        start: thisMonthStart,
        end: endOfDay(now)
      },
      {
        label: 'Last Month',
        value: 'last_month',
        start: lastMonthStart,
        end: endOfMonth(lastMonthStart)
      },
      {
        label: 'Last 30 Days',
        value: 'last_30_days',
        start: addDays(today, -30),
        end: endOfDay(now)
      },
      {
        label: 'Last 90 Days',
        value: 'last_90_days',
        start: addDays(today, -90),
        end: endOfDay(now)
      }
    ];
  }
}

/**
 * Convenience functions for common use cases
 */

export const formatDate = DateTimeUtils.formatDate;
export const formatTime = DateTimeUtils.formatTime;
export const formatDateTime = DateTimeUtils.formatDateTime;
export const formatRelativeTime = DateTimeUtils.formatRelativeTime;
export const parseDate = DateTimeUtils.parseDate;
export const isOverdue = DateTimeUtils.isOverdue;
export const getDaysUntilDue = DateTimeUtils.getDaysUntilDue;
export const getBillingPeriod = DateTimeUtils.getBillingPeriod;
export const calculateNextDueDate = DateTimeUtils.calculateNextDueDate;
export const isBusinessHours = DateTimeUtils.isBusinessHours;
export const getDateRangeOptions = DateTimeUtils.getDateRangeOptions;

/**
 * ISP-specific date utilities
 */
export const ISPDateUtils = {
  /**
   * Format for service activation dates
   */
  formatServiceDate: (date: string | Date | number | null | undefined) =>
    DateTimeUtils.formatDateTime(date, 'medium', 'short'),

  /**
   * Format for billing cycle dates
   */
  formatBillingCycle: (startDate: string | Date | number | null | undefined, endDate: string | Date | number | null | undefined) => {
    const start = DateTimeUtils.formatDate(startDate, 'short');
    const end = DateTimeUtils.formatDate(endDate, 'short');
    return `${start} - ${end}`;
  },

  /**
   * Get next billing date for recurring services
   */
  getNextBillingDate: (
    lastBillingDate: string | Date | number | null | undefined,
    billingCycle: 'monthly' | 'quarterly' | 'yearly'
  ): Date | null => {
    const lastDate = DateTimeUtils.parseDate(lastBillingDate);
    if (!lastDate) return null;

    switch (billingCycle) {
      case 'monthly':
        return addMonths(lastDate, 1);
      case 'quarterly':
        return addMonths(lastDate, 3);
      case 'yearly':
        return addMonths(lastDate, 12);
      default:
        return null;
    }
  },

  /**
   * Calculate service uptime duration
   */
  calculateUptime: (
    serviceStartDate: string | Date | number | null | undefined,
    downtime: { start: Date; end: Date }[] = []
  ): { totalDays: number; uptimePercentage: number; formattedDuration: string } => {
    const start = DateTimeUtils.parseDate(serviceStartDate);
    if (!start) return { totalDays: 0, uptimePercentage: 0, formattedDuration: '0 days' };

    const now = new Date();
    const totalDays = differenceInDays(now, start);
    
    const downtimeMinutes = downtime.reduce((total, period) => {
      return total + differenceInMinutes(period.end, period.start);
    }, 0);

    const totalMinutes = totalDays * 24 * 60;
    const uptimeMinutes = totalMinutes - downtimeMinutes;
    const uptimePercentage = totalMinutes > 0 ? (uptimeMinutes / totalMinutes) * 100 : 0;

    return {
      totalDays,
      uptimePercentage: Math.max(0, Math.min(100, uptimePercentage)),
      formattedDuration: DateTimeUtils.getDuration(start, now)
    };
  }
};

export default DateTimeUtils;