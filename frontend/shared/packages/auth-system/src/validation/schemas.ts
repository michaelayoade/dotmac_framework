/**
 * Validation schemas for authentication system
 * Portal-aware Zod schemas with comprehensive validation rules
 */

import { z } from 'zod';
import type { PortalVariant, LoginCredentials } from '../types';
import { getPortalConfig } from '../config/portal-configs';

// Base validation schemas
const emailSchema = z
  .string()
  .email('Please enter a valid email address')
  .min(3, 'Email must be at least 3 characters')
  .max(254, 'Email must be less than 254 characters')
  .toLowerCase()
  .trim();

const passwordSchema = z
  .string()
  .min(1, 'Password is required')
  .max(128, 'Password must be less than 128 characters');

// Portal ID validation (Customer portal)
const portalIdSchema = z
  .string()
  .regex(/^[A-Z0-9]{8}$/, 'Portal ID must be 8 characters (letters A-Z, numbers 0-9)')
  .length(8, 'Portal ID must be exactly 8 characters')
  .transform((val) => val.toUpperCase());

// Account number validation (Customer portal)
const accountNumberSchema = z
  .string()
  .regex(/^\d{6,12}$/, 'Account number must be 6-12 digits')
  .min(6, 'Account number must be at least 6 digits')
  .max(12, 'Account number must be no more than 12 digits');

// Partner code validation (Reseller portal)
const partnerCodeSchema = z
  .string()
  .regex(/^[A-Z]{2,4}\d{3,6}$/, 'Invalid partner code format')
  .min(5, 'Partner code must be at least 5 characters')
  .max(10, 'Partner code must be no more than 10 characters')
  .transform((val) => val.toUpperCase());

// MFA code validation
const mfaCodeSchema = z
  .string()
  .regex(/^\d{6}$/, 'MFA code must be 6 digits')
  .length(6, 'MFA code must be exactly 6 digits');

// API key validation
const apiKeySchema = z
  .string()
  .min(32, 'API key must be at least 32 characters')
  .max(128, 'API key must be no more than 128 characters')
  .regex(/^[A-Za-z0-9_-]+$/, 'API key contains invalid characters');

/**
 * Create portal-specific password validation schema
 */
function createPasswordSchema(portalVariant: PortalVariant) {
  const config = getPortalConfig(portalVariant);
  const requirements = config.validation.password;

  let schema = z
    .string()
    .min(requirements.minLength, `Password must be at least ${requirements.minLength} characters`)
    .max(
      requirements.maxLength,
      `Password must be no more than ${requirements.maxLength} characters`
    );

  if (requirements.requireUppercase) {
    schema = schema.regex(/[A-Z]/, 'Password must contain at least one uppercase letter');
  }

  if (requirements.requireLowercase) {
    schema = schema.regex(/[a-z]/, 'Password must contain at least one lowercase letter');
  }

  if (requirements.requireNumbers) {
    schema = schema.regex(/\d/, 'Password must contain at least one number');
  }

  if (requirements.requireSymbols) {
    schema = schema.regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character');
  }

  // Check against banned passwords
  if (requirements.bannedPasswords?.length) {
    schema = schema.refine(
      (val) => !requirements.bannedPasswords!.includes(val.toLowerCase()),
      'This password is too common and cannot be used'
    );
  }

  return schema;
}

/**
 * Create portal-specific email validation schema
 */
function createEmailSchema(portalVariant: PortalVariant) {
  const config = getPortalConfig(portalVariant);
  const emailConfig = config.validation.email;

  if (!emailConfig) {
    return emailSchema.optional();
  }

  let schema = emailSchema;

  // Domain restrictions
  if (emailConfig.domains?.length) {
    schema = schema.refine(
      (val) => {
        const domain = val.split('@')[1];
        return emailConfig.domains!.includes(domain);
      },
      `Email must be from one of these domains: ${emailConfig.domains!.join(', ')}`
    );
  }

  // Blocked domains
  if (emailConfig.blockedDomains?.length) {
    schema = schema.refine((val) => {
      const domain = val.split('@')[1];
      return !emailConfig.blockedDomains!.includes(domain);
    }, 'This email domain is not allowed');
  }

  return emailConfig.required ? schema : schema.optional();
}

/**
 * Portal-specific login credential schemas
 */
export const LOGIN_SCHEMAS: Record<PortalVariant, z.ZodSchema<any>> = {
  'management-admin': z
    .object({
      email: emailSchema,
      password: z.string().min(1, 'Password is required'),
      mfaCode: mfaCodeSchema.optional(),
      rememberMe: z.boolean().default(false),
      rememberDevice: z.boolean().default(false),
    })
    .refine((data) => {
      // MFA validation will be handled at runtime based on user settings
      return true;
    }),

  customer: z
    .object({
      email: emailSchema.optional(),
      portalId: portalIdSchema.optional(),
      accountNumber: accountNumberSchema.optional(),
      password: z.string().min(1, 'Password is required'),
      mfaCode: mfaCodeSchema.optional(),
      rememberMe: z.boolean().default(false),
      rememberDevice: z.boolean().default(false),
    })
    .refine(
      (data) => {
        // At least one login method must be provided
        const hasEmail = data.email && data.email.length > 0;
        const hasPortalId = data.portalId && data.portalId.length > 0;
        const hasAccountNumber = data.accountNumber && data.accountNumber.length > 0;

        return hasEmail || hasPortalId || hasAccountNumber;
      },
      {
        message: 'Please provide either email, Portal ID, or account number',
        path: ['email'], // Show error on email field
      }
    ),

  admin: z.object({
    email: emailSchema,
    password: z.string().min(1, 'Password is required'),
    mfaCode: mfaCodeSchema.optional(),
    rememberMe: z.boolean().default(false),
    rememberDevice: z.boolean().default(false),
  }),

  reseller: z
    .object({
      email: emailSchema.optional(),
      partnerCode: partnerCodeSchema.optional(),
      password: z.string().min(1, 'Password is required'),
      mfaCode: mfaCodeSchema.optional(),
      rememberMe: z.boolean().default(false),
      rememberDevice: z.boolean().default(false),
    })
    .refine(
      (data) => {
        // Either email or partner code required
        const hasEmail = data.email && data.email.length > 0;
        const hasPartnerCode = data.partnerCode && data.partnerCode.length > 0;

        return hasEmail || hasPartnerCode;
      },
      {
        message: 'Please provide either email or partner code',
        path: ['email'],
      }
    ),

  technician: z.object({
    email: emailSchema,
    password: z.string().min(1, 'Password is required'),
    mfaCode: mfaCodeSchema.optional(),
    rememberMe: z.boolean().default(false),
    rememberDevice: z.boolean().default(false),
  }),

  'management-reseller': z.object({
    email: emailSchema,
    password: z.string().min(1, 'Password is required'),
    mfaCode: mfaCodeSchema.optional(),
    rememberMe: z.boolean().default(false),
    rememberDevice: z.boolean().default(false),
  }),

  'tenant-portal': z.object({
    email: emailSchema,
    password: z.string().min(1, 'Password is required'),
    mfaCode: mfaCodeSchema.optional(),
    rememberMe: z.boolean().default(false),
    rememberDevice: z.boolean().default(false),
  }),
};

/**
 * Password change validation schema
 */
export const passwordChangeSchema = (portalVariant: PortalVariant) =>
  z
    .object({
      currentPassword: z.string().min(1, 'Current password is required'),
      newPassword: createPasswordSchema(portalVariant),
      confirmPassword: z.string().min(1, 'Please confirm your new password'),
    })
    .refine((data) => data.newPassword === data.confirmPassword, {
      message: 'Passwords do not match',
      path: ['confirmPassword'],
    })
    .refine((data) => data.currentPassword !== data.newPassword, {
      message: 'New password must be different from current password',
      path: ['newPassword'],
    });

/**
 * Password reset request schema
 */
export const passwordResetRequestSchema = (portalVariant: PortalVariant) => {
  const config = getPortalConfig(portalVariant);

  if (portalVariant === 'customer') {
    return z
      .object({
        email: emailSchema.optional(),
        portalId: portalIdSchema.optional(),
        accountNumber: accountNumberSchema.optional(),
      })
      .refine(
        (data) => {
          const hasEmail = data.email && data.email.length > 0;
          const hasPortalId = data.portalId && data.portalId.length > 0;
          const hasAccountNumber = data.accountNumber && data.accountNumber.length > 0;

          return hasEmail || hasPortalId || hasAccountNumber;
        },
        {
          message: 'Please provide either email, Portal ID, or account number',
          path: ['email'],
        }
      );
  }

  return z.object({
    email: createEmailSchema(portalVariant),
  });
};

/**
 * Password reset confirmation schema
 */
export const passwordResetConfirmSchema = (portalVariant: PortalVariant) =>
  z
    .object({
      token: z.string().min(1, 'Reset token is required'),
      newPassword: createPasswordSchema(portalVariant),
      confirmPassword: z.string().min(1, 'Please confirm your new password'),
    })
    .refine((data) => data.newPassword === data.confirmPassword, {
      message: 'Passwords do not match',
      path: ['confirmPassword'],
    });

/**
 * MFA setup schema
 */
export const mfaSetupSchema = z.object({
  type: z.enum(['totp', 'sms', 'email']),
  phoneNumber: z.string().optional(),
  verificationCode: mfaCodeSchema,
});

/**
 * MFA verification schema
 */
export const mfaVerificationSchema = z.object({
  code: mfaCodeSchema,
  method: z.enum(['totp', 'sms', 'email', 'backup_code']),
  rememberDevice: z.boolean().default(false),
});

/**
 * User profile update schema
 */
export const userProfileUpdateSchema = z.object({
  firstName: z.string().min(1, 'First name is required').max(50, 'First name too long').optional(),
  lastName: z.string().min(1, 'Last name is required').max(50, 'Last name too long').optional(),
  email: emailSchema.optional(),
  phoneNumber: z
    .string()
    .regex(/^\+?[1-9]\d{1,14}$/, 'Please enter a valid phone number')
    .optional(),
  avatar: z.string().url('Please enter a valid image URL').optional(),
  preferences: z
    .object({
      language: z.string().optional(),
      timezone: z.string().optional(),
      emailNotifications: z.boolean().optional(),
      smsNotifications: z.boolean().optional(),
      theme: z.enum(['light', 'dark', 'system']).optional(),
    })
    .optional(),
});

/**
 * Session management schema
 */
export const sessionTerminationSchema = z.object({
  sessionId: z.string().min(1, 'Session ID is required'),
  reason: z.enum(['user_logout', 'admin_terminated', 'security_violation', 'expired']).optional(),
});

/**
 * API key creation schema
 */
export const apiKeyCreateSchema = z.object({
  name: z.string().min(1, 'API key name is required').max(100, 'Name too long'),
  description: z.string().max(500, 'Description too long').optional(),
  permissions: z.array(z.string()).min(1, 'At least one permission required'),
  expiresAt: z.date().optional(),
  ipRestrictions: z.array(z.string()).optional(),
});

/**
 * Validate login credentials for a specific portal
 */
export function validateLoginCredentials(
  credentials: LoginCredentials,
  portalVariant: PortalVariant
):
  | { success: true; data: LoginCredentials }
  | { success: false; errors: Record<string, string[]> } {
  try {
    const schema = LOGIN_SCHEMAS[portalVariant];
    const validated = schema.parse(credentials);

    return { success: true, data: validated };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: Record<string, string[]> = {};

      error.issues.forEach((err: any) => {
        const path = err.path.join('.');
        if (!errors[path]) {
          errors[path] = [];
        }
        errors[path].push(err.message);
      });

      return { success: false, errors };
    }

    return {
      success: false,
      errors: { form: ['Validation failed'] },
    };
  }
}

/**
 * Validate password strength for a specific portal
 */
export function validatePasswordStrength(
  password: string,
  portalVariant: PortalVariant
): { isValid: boolean; score: number; feedback: string[] } {
  const config = getPortalConfig(portalVariant);
  const requirements = config.validation.password;

  let score = 0;
  const feedback: string[] = [];

  // Length check
  if (password.length >= requirements.minLength) {
    score += 20;
  } else {
    feedback.push(`Password must be at least ${requirements.minLength} characters`);
  }

  // Character type checks
  if (requirements.requireUppercase && /[A-Z]/.test(password)) {
    score += 15;
  } else if (requirements.requireUppercase) {
    feedback.push('Add uppercase letters');
  }

  if (requirements.requireLowercase && /[a-z]/.test(password)) {
    score += 15;
  } else if (requirements.requireLowercase) {
    feedback.push('Add lowercase letters');
  }

  if (requirements.requireNumbers && /\d/.test(password)) {
    score += 15;
  } else if (requirements.requireNumbers) {
    feedback.push('Add numbers');
  }

  if (requirements.requireSymbols && /[^A-Za-z0-9]/.test(password)) {
    score += 15;
  } else if (requirements.requireSymbols) {
    feedback.push('Add special characters');
  }

  // Length bonus
  if (password.length >= requirements.minLength + 4) {
    score += 10;
  }

  // Variety bonus
  const uniqueChars = new Set(password.toLowerCase()).size;
  if (uniqueChars >= 8) {
    score += 10;
  }

  // Common patterns penalty
  if (/(.)\1{2,}/.test(password)) {
    score -= 10;
    feedback.push('Avoid repeated characters');
  }

  if (/123|abc|qwe|password|admin/i.test(password)) {
    score -= 20;
    feedback.push('Avoid common patterns');
  }

  // Banned passwords check
  if (requirements.bannedPasswords?.includes(password.toLowerCase())) {
    score = 0;
    feedback.push('This password is too common');
  }

  // Ensure score is between 0-100
  score = Math.max(0, Math.min(100, score));

  return {
    isValid: score >= 70 && feedback.length === 0,
    score,
    feedback:
      feedback.length > 0
        ? feedback
        : score >= 90
          ? ['Excellent password strength!']
          : score >= 70
            ? ['Good password strength']
            : score >= 50
              ? ['Fair password strength']
              : ['Weak password - please improve'],
  };
}

/**
 * Portal ID validation and formatting
 */
export function validatePortalId(portalId: string): {
  isValid: boolean;
  formatted: string;
  errors: string[];
} {
  const errors: string[] = [];
  let formatted = portalId.toUpperCase().trim();

  // Remove spaces and common separators
  formatted = formatted.replace(/[\s-_]/g, '');

  // Length check
  if (formatted.length !== 8) {
    errors.push('Portal ID must be exactly 8 characters');
  }

  // Character check
  if (!/^[A-Z0-9]{8}$/.test(formatted)) {
    errors.push('Portal ID can only contain letters A-Z and numbers 0-9');
  }

  // Avoid confusion with similar characters
  if (/[01OI]/.test(formatted)) {
    errors.push('Portal ID cannot contain 0, 1, O, or I to avoid confusion');
  }

  return {
    isValid: errors.length === 0,
    formatted,
    errors,
  };
}

/**
 * Account number validation and formatting
 */
export function validateAccountNumber(accountNumber: string): {
  isValid: boolean;
  formatted: string;
  errors: string[];
} {
  const errors: string[] = [];
  let formatted = accountNumber.trim().replace(/\D/g, ''); // Remove non-digits

  // Length check
  if (formatted.length < 6) {
    errors.push('Account number must be at least 6 digits');
  } else if (formatted.length > 12) {
    errors.push('Account number must be no more than 12 digits');
  }

  // Leading zeros check
  if (formatted.startsWith('0') && formatted.length > 1) {
    errors.push('Account number cannot start with zero');
  }

  return {
    isValid: errors.length === 0,
    formatted,
    errors,
  };
}
