/**
 * Comprehensive Input Sanitization for DotMac Portal Ecosystem
 *
 * This module provides robust input sanitization to prevent XSS, injection attacks,
 * and other security vulnerabilities across all portal applications.
 *
 * Features:
 * - HTML/Script tag removal and encoding
 * - SQL injection prevention
 * - Path traversal protection
 * - Email validation and sanitization
 * - Phone number sanitization
 * - Special character handling
 * - Configurable sanitization rules
 */

import DOMPurify from 'dompurify';

export interface SanitizationConfig {
  allowedTags?: string[];
  allowedAttributes?: string[];
  maxLength?: number;
  stripWhitespace?: boolean;
  preserveNewlines?: boolean;
  allowEmptyValues?: boolean;
  customValidators?: Array<(input: string) => string>;
}

export interface SanitizationResult {
  sanitized: string;
  wasModified: boolean;
  violations: string[];
  isValid: boolean;
}

export class InputSanitizer {
  private static instance: InputSanitizer;
  private config: Required<SanitizationConfig>;

  constructor(config?: SanitizationConfig) {
    this.config = {
      allowedTags: [],
      allowedAttributes: [],
      maxLength: 1000,
      stripWhitespace: true,
      preserveNewlines: false,
      allowEmptyValues: false,
      customValidators: [],
      ...config,
    };
  }

  /**
   * Get singleton instance
   */
  static getInstance(config?: SanitizationConfig): InputSanitizer {
    if (!InputSanitizer.instance) {
      InputSanitizer.instance = new InputSanitizer(config);
    }
    return InputSanitizer.instance;
  }

  /**
   * Sanitize general text input
   */
  sanitizeText(input: string, config?: Partial<SanitizationConfig>): SanitizationResult {
    const workingConfig = { ...this.config, ...config };
    const original = input;
    let sanitized = input;
    const violations: string[] = [];

    // Handle null/undefined
    if (input == null) {
      sanitized = workingConfig.allowEmptyValues ? '' : '';
      return {
        sanitized,
        wasModified: false,
        violations: workingConfig.allowEmptyValues ? [] : ['Empty value not allowed'],
        isValid: workingConfig.allowEmptyValues,
      };
    }

    // Convert to string
    sanitized = String(sanitized);

    // Check length limit
    if (workingConfig.maxLength && sanitized.length > workingConfig.maxLength) {
      sanitized = sanitized.substring(0, workingConfig.maxLength);
      violations.push(`Input truncated to ${workingConfig.maxLength} characters`);
    }

    // Remove dangerous patterns
    const dangerousPatterns = [
      // Script tags
      /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
      // Event handlers
      /on\w+\s*=\s*["']?[^"']*["']?/gi,
      // JavaScript URLs
      /javascript:/gi,
      // Data URLs
      /data:/gi,
      // Vbscript
      /vbscript:/gi,
      // SQL injection patterns
      /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)/gi,
      // Path traversal
      /\.\.[\/\\]/g,
      // HTML entities that could be malicious
      /&#x?[0-9a-f]+;?/gi,
    ];

    dangerousPatterns.forEach((pattern, index) => {
      if (pattern.test(sanitized)) {
        sanitized = sanitized.replace(pattern, '');
        violations.push(`Removed dangerous pattern ${index + 1}`);
      }
    });

    // Use DOMPurify for HTML sanitization
    if (workingConfig.allowedTags.length > 0) {
      const purifiedInput = DOMPurify.sanitize(sanitized, {
        ALLOWED_TAGS: workingConfig.allowedTags,
        ALLOWED_ATTR: workingConfig.allowedAttributes,
        KEEP_CONTENT: true,
        RETURN_DOM_FRAGMENT: false,
        RETURN_DOM_IMPORT: false,
      });

      if (purifiedInput !== sanitized) {
        sanitized = purifiedInput;
        violations.push('HTML content sanitized');
      }
    } else {
      // If no HTML allowed, escape all HTML
      const escaped = this.escapeHtml(sanitized);
      if (escaped !== sanitized) {
        sanitized = escaped;
        violations.push('HTML characters escaped');
      }
    }

    // Whitespace handling
    if (workingConfig.stripWhitespace) {
      const trimmed = sanitized.trim();
      if (!workingConfig.preserveNewlines) {
        sanitized = trimmed.replace(/\s+/g, ' ');
      } else {
        sanitized = trimmed;
      }
    }

    // Apply custom validators
    workingConfig.customValidators.forEach((validator, index) => {
      try {
        const validatedInput = validator(sanitized);
        if (validatedInput !== sanitized) {
          sanitized = validatedInput;
          violations.push(`Custom validator ${index + 1} applied`);
        }
      } catch (error) {
        violations.push(
          `Custom validator ${index + 1} failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    });

    return {
      sanitized,
      wasModified: sanitized !== original,
      violations,
      isValid: violations.length === 0,
    };
  }

  /**
   * Sanitize email addresses
   */
  sanitizeEmail(email: string): SanitizationResult {
    const emailRegex =
      /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    const violations: string[] = [];

    const textResult = this.sanitizeText(email, {
      maxLength: 254,
      stripWhitespace: true,
      allowEmptyValues: false,
    });

    let { sanitized } = textResult;
    violations.push(...textResult.violations);

    // Convert to lowercase for email
    sanitized = sanitized.toLowerCase();

    // Validate email format
    if (!emailRegex.test(sanitized)) {
      violations.push('Invalid email format');
      return {
        sanitized: '',
        wasModified: true,
        violations,
        isValid: false,
      };
    }

    return {
      sanitized,
      wasModified: textResult.wasModified || sanitized !== email,
      violations,
      isValid:
        violations.filter((v) => !v.includes('Applied') && !v.includes('sanitized')).length === 0,
    };
  }

  /**
   * Sanitize phone numbers
   */
  sanitizePhone(phone: string): SanitizationResult {
    const violations: string[] = [];
    let sanitized = String(phone || '');

    // Remove all non-digit characters except + and spaces
    const cleaned = sanitized.replace(/[^\d\+\s\-\(\)]/g, '');
    if (cleaned !== sanitized) {
      violations.push('Removed non-phone characters');
      sanitized = cleaned;
    }

    // Basic phone validation (10-15 digits)
    const digitsOnly = sanitized.replace(/\D/g, '');
    if (digitsOnly.length < 10 || digitsOnly.length > 15) {
      violations.push('Invalid phone number length');
      return {
        sanitized: '',
        wasModified: true,
        violations,
        isValid: false,
      };
    }

    return {
      sanitized,
      wasModified: cleaned !== phone,
      violations,
      isValid: violations.length === 0,
    };
  }

  /**
   * Sanitize numerical input
   */
  sanitizeNumber(
    input: string | number,
    options?: { min?: number; max?: number; decimals?: number }
  ): SanitizationResult {
    const violations: string[] = [];
    let sanitized = String(input || '');

    // Remove non-numeric characters
    const numericOnly = sanitized.replace(/[^0-9.-]/g, '');
    if (numericOnly !== sanitized) {
      violations.push('Removed non-numeric characters');
      sanitized = numericOnly;
    }

    const number = parseFloat(sanitized);
    if (isNaN(number)) {
      return {
        sanitized: '',
        wasModified: true,
        violations: [...violations, 'Invalid number format'],
        isValid: false,
      };
    }

    // Apply constraints
    let constrainedNumber = number;
    if (options?.min !== undefined && constrainedNumber < options.min) {
      constrainedNumber = options.min;
      violations.push(`Value increased to minimum: ${options.min}`);
    }

    if (options?.max !== undefined && constrainedNumber > options.max) {
      constrainedNumber = options.max;
      violations.push(`Value decreased to maximum: ${options.max}`);
    }

    // Handle decimals
    if (options?.decimals !== undefined) {
      constrainedNumber = parseFloat(constrainedNumber.toFixed(options.decimals));
      if (constrainedNumber !== number) {
        violations.push(`Rounded to ${options.decimals} decimal places`);
      }
    }

    return {
      sanitized: constrainedNumber.toString(),
      wasModified: constrainedNumber !== number,
      violations,
      isValid: violations.filter((v) => !v.includes('Rounded')).length === 0,
    };
  }

  /**
   * Sanitize file paths
   */
  sanitizePath(path: string): SanitizationResult {
    const violations: string[] = [];
    let sanitized = String(path || '');

    // Remove path traversal attempts
    const dangerous = /(\.\.[\/\\]|[<>:"|?*])/g;
    if (dangerous.test(sanitized)) {
      sanitized = sanitized.replace(dangerous, '');
      violations.push('Removed path traversal attempts');
    }

    // Remove null bytes
    if (sanitized.includes('\0')) {
      sanitized = sanitized.replace(/\0/g, '');
      violations.push('Removed null bytes');
    }

    return {
      sanitized,
      wasModified: sanitized !== path,
      violations,
      isValid: violations.length === 0,
    };
  }

  /**
   * Batch sanitize an object's properties
   */
  sanitizeObject<T extends Record<string, any>>(
    obj: T,
    fieldConfigs: Record<
      keyof T,
      SanitizationConfig & { type?: 'text' | 'email' | 'phone' | 'number' | 'path' }
    >
  ): { sanitized: T; violations: Record<keyof T, string[]>; isValid: boolean } {
    const sanitized = { ...obj };
    const violations: Record<keyof T, string[]> = {} as Record<keyof T, string[]>;
    let isValid = true;

    for (const [key, config] of Object.entries(fieldConfigs) as [keyof T, any][]) {
      if (!(key in obj)) continue;

      const value = obj[key];
      let result: SanitizationResult;

      switch (config.type) {
        case 'email':
          result = this.sanitizeEmail(value);
          break;
        case 'phone':
          result = this.sanitizePhone(value);
          break;
        case 'number':
          result = this.sanitizeNumber(value, config);
          break;
        case 'path':
          result = this.sanitizePath(value);
          break;
        default:
          result = this.sanitizeText(value, config);
      }

      sanitized[key] = result.sanitized as T[keyof T];
      violations[key] = result.violations;

      if (!result.isValid) {
        isValid = false;
      }
    }

    return { sanitized, violations, isValid };
  }

  /**
   * HTML escape utility
   */
  private escapeHtml(text: string): string {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
      '/': '&#x2F;',
    };

    return text.replace(/[&<>"'/]/g, (s) => map[s]);
  }
}

// Export default instance
export const defaultSanitizer = InputSanitizer.getInstance({
  maxLength: 1000,
  stripWhitespace: true,
  allowEmptyValues: false,
});

// Convenient functions for common use cases
export const sanitizeText = (input: string, config?: SanitizationConfig) =>
  defaultSanitizer.sanitizeText(input, config);

export const sanitizeEmail = (email: string) => defaultSanitizer.sanitizeEmail(email);

export const sanitizePhone = (phone: string) => defaultSanitizer.sanitizePhone(phone);

export const sanitizeNumber = (
  input: string | number,
  options?: { min?: number; max?: number; decimals?: number }
) => defaultSanitizer.sanitizeNumber(input, options);

export const sanitizePath = (path: string) => defaultSanitizer.sanitizePath(path);

export const sanitizeObject = <T extends Record<string, any>>(
  obj: T,
  fieldConfigs: Record<
    keyof T,
    SanitizationConfig & { type?: 'text' | 'email' | 'phone' | 'number' | 'path' }
  >
) => defaultSanitizer.sanitizeObject(obj, fieldConfigs);
