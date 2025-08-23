/**
 * Input Validation and Sanitization Module
 *
 * Provides comprehensive input validation, sanitization, and XSS protection
 * for React components in the DotMac platform
 */

import DOMPurify from 'dompurify';
import CryptoJS from 'crypto-js';
import { z } from 'zod';

// Validation rule types
export interface ValidationRule {
  name: string;
  test: (value: string) => boolean;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface SanitizationOptions {
  allowedTags?: string[];
  allowedAttributes?: Record<string, string[]>;
  stripTags?: boolean;
  encodeEntities?: boolean;
  removeScripts?: boolean;
  validateUrls?: boolean;
}

export interface ValidationResult {
  isValid: boolean;
  sanitizedValue: string;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  metadata: ValidationMetadata;
}

export interface ValidationError {
  rule: string;
  message: string;
  originalValue: string;
  position?: number;
}

export interface ValidationWarning {
  rule: string;
  message: string;
  severity: 'low' | 'medium' | 'high';
}

export interface ValidationMetadata {
  originalLength: number;
  sanitizedLength: number;
  rulesApplied: string[];
  processingTime: number;
  hash: string;
}

// Predefined validation rules
export const CommonValidationRules = {
  // XSS Prevention Rules
  NO_SCRIPT_TAGS: {
    name: 'no-script-tags',
    test: (value: string) => !/<script[\s\S]*?>[\s\S]*?<\/script>/gi.test(value),
    message: 'Script tags are not allowed',
    severity: 'error' as const,
  },

  NO_EVENT_HANDLERS: {
    name: 'no-event-handlers',
    test: (value: string) => !/on\w+\s*=/gi.test(value),
    message: 'Event handlers are not allowed',
    severity: 'error' as const,
  },

  NO_JAVASCRIPT_URLS: {
    name: 'no-javascript-urls',
    test: (value: string) => !/javascript\s*:/gi.test(value),
    message: 'JavaScript URLs are not allowed',
    severity: 'error' as const,
  },

  NO_DATA_URLS: {
    name: 'no-data-urls',
    test: (value: string) => !/data\s*:/gi.test(value),
    message: 'Data URLs are not allowed for security reasons',
    severity: 'warning' as const,
  },

  // Content Validation Rules
  NO_HTML_COMMENTS: {
    name: 'no-html-comments',
    test: (value: string) => !/<!--[\s\S]*?-->/g.test(value),
    message: 'HTML comments are not allowed',
    severity: 'warning' as const,
  },

  NO_EXTERNAL_REFERENCES: {
    name: 'no-external-references',
    test: (value: string) =>
      !/https?:\/\/(?!localhost|127\.0\.0\.1|192\.168\.|10\.|172\.)/gi.test(value),
    message: 'External URLs detected - ensure they are trusted',
    severity: 'info' as const,
  },

  // Length and Format Rules
  MAX_LENGTH: (max: number): ValidationRule => ({
    name: `max-length-${max}`,
    test: (value: string) => value.length <= max,
    message: `Input exceeds maximum length of ${max} characters`,
    severity: 'error' as const,
  }),

  MIN_LENGTH: (min: number): ValidationRule => ({
    name: `min-length-${min}`,
    test: (value: string) => value.length >= min,
    message: `Input must be at least ${min} characters`,
    severity: 'error' as const,
  }),

  EMAIL_FORMAT: {
    name: 'email-format',
    test: (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    message: 'Invalid email format',
    severity: 'error' as const,
  },

  PHONE_FORMAT: {
    name: 'phone-format',
    test: (value: string) => /^[\+]?[1-9][\d]{0,15}$/.test(value.replace(/[\s\-\(\)]/g, '')),
    message: 'Invalid phone number format',
    severity: 'error' as const,
  },

  URL_FORMAT: {
    name: 'url-format',
    test: (value: string) => {
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message: 'Invalid URL format',
    severity: 'error' as const,
  },
};

// Zod-based validation schemas
export const ValidationSchemas = {
  SafeText: z
    .string()
    .max(1000)
    .refine((val) => !/<script/gi.test(val), 'Script tags not allowed')
    .refine((val) => !/on\w+=/gi.test(val), 'Event handlers not allowed')
    .refine((val) => !/javascript:/gi.test(val), 'JavaScript URLs not allowed'),

  SafeHTML: z
    .string()
    .max(10000)
    .refine((val) => !/<script/gi.test(val), 'Script tags not allowed')
    .refine((val) => !/javascript:/gi.test(val), 'JavaScript URLs not allowed'),

  Email: z.string().email(),
  Phone: z.string().regex(/^[\+]?[1-9][\d]{0,15}$/, 'Invalid phone format'),
  URL: z.string().url(),

  SecurePassword: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
      'Password must contain uppercase, lowercase, number, and special character'
    ),
};

export class InputValidator {
  private rules: ValidationRule[] = [];
  private sanitizationOptions: SanitizationOptions = {
    stripTags: true,
    encodeEntities: true,
    removeScripts: true,
    validateUrls: true,
  };

  constructor(rules: ValidationRule[] = [], options: SanitizationOptions = {}) {
    this.rules = rules;
    this.sanitizationOptions = { ...this.sanitizationOptions, ...options };
  }

  /**
   * Add validation rule
   */
  addRule(rule: ValidationRule): this {
    this.rules.push(rule);
    return this;
  }

  /**
   * Add multiple validation rules
   */
  addRules(rules: ValidationRule[]): this {
    this.rules.push(...rules);
    return this;
  }

  /**
   * Validate and sanitize input
   */
  validate(input: string): ValidationResult {
    const startTime = Date.now();
    const originalValue = input;
    const originalLength = input.length;

    let sanitizedValue = input;
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];
    const rulesApplied: string[] = [];

    try {
      // Step 1: Apply sanitization
      sanitizedValue = this.sanitizeInput(sanitizedValue);
      rulesApplied.push('sanitization');

      // Step 2: Apply validation rules
      for (const rule of this.rules) {
        rulesApplied.push(rule.name);

        if (!rule.test(sanitizedValue)) {
          if (rule.severity === 'error') {
            errors.push({
              rule: rule.name,
              message: rule.message,
              originalValue,
            });
          } else {
            warnings.push({
              rule: rule.name,
              message: rule.message,
              severity: rule.severity === 'warning' ? 'medium' : 'low',
            });
          }
        }
      }

      // Step 3: Generate metadata
      const processingTime = Date.now() - startTime;
      const hash = CryptoJS.SHA256(sanitizedValue).toString();

      const metadata: ValidationMetadata = {
        originalLength,
        sanitizedLength: sanitizedValue.length,
        rulesApplied,
        processingTime,
        hash,
      };

      return {
        isValid: errors.length === 0,
        sanitizedValue,
        errors,
        warnings,
        metadata,
      };
    } catch (error) {
      return {
        isValid: false,
        sanitizedValue: '',
        errors: [
          {
            rule: 'validation-error',
            message: error instanceof Error ? error.message : 'Unknown validation error',
            originalValue,
          },
        ],
        warnings: [],
        metadata: {
          originalLength,
          sanitizedLength: 0,
          rulesApplied: [],
          processingTime: Date.now() - startTime,
          hash: '',
        },
      };
    }
  }

  /**
   * Sanitize input using DOMPurify and custom rules
   */
  private sanitizeInput(input: string): string {
    let sanitized = input;

    // Configure DOMPurify
    const purifyConfig: any = {
      ALLOWED_TAGS: this.sanitizationOptions.allowedTags || [],
      ALLOWED_ATTR: this.sanitizationOptions.allowedAttributes || {},
      KEEP_CONTENT: !this.sanitizationOptions.stripTags,
    };

    // Remove script tags if specified
    if (this.sanitizationOptions.removeScripts) {
      sanitized = sanitized.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
      sanitized = sanitized.replace(/javascript\s*:/gi, '');
      sanitized = sanitized.replace(/on\w+\s*=/gi, '');
    }

    // Encode HTML entities if specified
    if (this.sanitizationOptions.encodeEntities) {
      sanitized = sanitized
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
    }

    // Use DOMPurify for comprehensive sanitization
    if (typeof window !== 'undefined') {
      sanitized = DOMPurify.sanitize(sanitized, purifyConfig) as unknown as string;
    }

    // Validate URLs if specified
    if (this.sanitizationOptions.validateUrls) {
      sanitized = this.sanitizeUrls(sanitized);
    }

    return sanitized.trim();
  }

  /**
   * Sanitize URLs in the input
   */
  private sanitizeUrls(input: string): string {
    const urlRegex = /(https?:\/\/[^\s<>"{}|\\^`[\]]+)/gi;

    return input.replace(urlRegex, (url) => {
      try {
        const urlObj = new URL(url);

        // Block dangerous protocols
        if (!['http:', 'https:'].includes(urlObj.protocol)) {
          return '[BLOCKED URL]';
        }

        // Block localhost in production (optional)
        if (
          process.env.NODE_ENV === 'production' &&
          (urlObj.hostname === 'localhost' ||
            urlObj.hostname === '127.0.0.1' ||
            urlObj.hostname.startsWith('192.168.') ||
            urlObj.hostname.startsWith('10.') ||
            urlObj.hostname.startsWith('172.'))
        ) {
          return '[LOCAL URL BLOCKED]';
        }

        return url;
      } catch {
        return '[INVALID URL]';
      }
    });
  }

  /**
   * Create validator with predefined rules for common use cases
   */
  static forTextInput(maxLength = 1000): InputValidator {
    return new InputValidator([
      CommonValidationRules.NO_SCRIPT_TAGS,
      CommonValidationRules.NO_EVENT_HANDLERS,
      CommonValidationRules.NO_JAVASCRIPT_URLS,
      CommonValidationRules.MAX_LENGTH(maxLength),
    ]);
  }

  static forEmail(): InputValidator {
    return new InputValidator([
      CommonValidationRules.NO_SCRIPT_TAGS,
      CommonValidationRules.EMAIL_FORMAT,
      CommonValidationRules.MAX_LENGTH(255),
    ]);
  }

  static forPassword(): InputValidator {
    return new InputValidator([
      CommonValidationRules.MIN_LENGTH(8),
      CommonValidationRules.MAX_LENGTH(128),
    ]);
  }

  static forURL(): InputValidator {
    return new InputValidator([
      CommonValidationRules.NO_SCRIPT_TAGS,
      CommonValidationRules.URL_FORMAT,
      CommonValidationRules.MAX_LENGTH(2048),
    ]);
  }

  static forHTMLContent(): InputValidator {
    return new InputValidator(
      [
        CommonValidationRules.NO_SCRIPT_TAGS,
        CommonValidationRules.NO_EVENT_HANDLERS,
        CommonValidationRules.NO_JAVASCRIPT_URLS,
        CommonValidationRules.MAX_LENGTH(50000),
      ],
      {
        stripTags: false,
        allowedTags: ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'h1', 'h2', 'h3'],
        allowedAttributes: {
          a: ['href', 'title'],
        },
      }
    );
  }
}
