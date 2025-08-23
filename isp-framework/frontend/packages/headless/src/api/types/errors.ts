/**
 * Comprehensive Error Response Types
 * Standardized error handling for all API clients with detailed error classification
 */

// Base error response structure
export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    field_errors?: FieldError[];
    context?: ErrorContext;
    suggestions?: string[];
  };
  timestamp: string;
  trace_id?: string;
  request_id?: string;
}

// Field-specific validation errors
export interface FieldError {
  field: string;
  code: string;
  message: string;
  value?: any;
}

// Error context information
export interface ErrorContext {
  user_id?: string;
  tenant_id?: string;
  endpoint: string;
  method: string;
  user_agent?: string;
  ip_address?: string;
}

// Error categories
export type ErrorCategory =
  | 'authentication'
  | 'authorization' 
  | 'validation'
  | 'not_found'
  | 'conflict'
  | 'rate_limit'
  | 'server_error'
  | 'network_error'
  | 'timeout'
  | 'maintenance'
  | 'business_logic'
  | 'external_service';

// Specific error codes with detailed information
export interface ErrorCodeDefinition {
  code: string;
  category: ErrorCategory;
  message: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  recoverable: boolean;
  retry_after?: number; // seconds
  documentation_url?: string;
}

// Common error codes used across the ISP platform
export const ERROR_CODES: Record<string, ErrorCodeDefinition> = {
  // Authentication errors
  INVALID_CREDENTIALS: {
    code: 'INVALID_CREDENTIALS',
    category: 'authentication',
    message: 'Invalid login credentials',
    description: 'The provided email/password combination is incorrect',
    severity: 'medium',
    recoverable: true
  },
  TOKEN_EXPIRED: {
    code: 'TOKEN_EXPIRED',
    category: 'authentication',
    message: 'Authentication token has expired',
    description: 'The access token is no longer valid and needs to be refreshed',
    severity: 'medium',
    recoverable: true
  },
  TOKEN_INVALID: {
    code: 'TOKEN_INVALID',
    category: 'authentication',
    message: 'Authentication token is invalid',
    description: 'The provided token is malformed or not recognized',
    severity: 'high',
    recoverable: false
  },
  MFA_REQUIRED: {
    code: 'MFA_REQUIRED',
    category: 'authentication',
    message: 'Multi-factor authentication required',
    description: 'This account requires MFA verification to proceed',
    severity: 'medium',
    recoverable: true
  },
  ACCOUNT_LOCKED: {
    code: 'ACCOUNT_LOCKED',
    category: 'authentication',
    message: 'Account has been locked',
    description: 'Account locked due to multiple failed login attempts',
    severity: 'high',
    recoverable: false
  },

  // Authorization errors
  INSUFFICIENT_PERMISSIONS: {
    code: 'INSUFFICIENT_PERMISSIONS',
    category: 'authorization',
    message: 'Insufficient permissions to perform this action',
    description: 'User does not have the required role or permission',
    severity: 'medium',
    recoverable: false
  },
  TENANT_ACCESS_DENIED: {
    code: 'TENANT_ACCESS_DENIED',
    category: 'authorization',
    message: 'Access denied for this tenant',
    description: 'User is not authorized to access resources in this tenant',
    severity: 'high',
    recoverable: false
  },
  RESOURCE_FORBIDDEN: {
    code: 'RESOURCE_FORBIDDEN',
    category: 'authorization',
    message: 'Access to this resource is forbidden',
    description: 'User does not have access to this specific resource',
    severity: 'medium',
    recoverable: false
  },

  // Validation errors
  INVALID_REQUEST_FORMAT: {
    code: 'INVALID_REQUEST_FORMAT',
    category: 'validation',
    message: 'Invalid request format',
    description: 'Request body is malformed or missing required fields',
    severity: 'medium',
    recoverable: true
  },
  VALIDATION_FAILED: {
    code: 'VALIDATION_FAILED',
    category: 'validation',
    message: 'Input validation failed',
    description: 'One or more fields contain invalid values',
    severity: 'medium',
    recoverable: true
  },
  INVALID_EMAIL_FORMAT: {
    code: 'INVALID_EMAIL_FORMAT',
    category: 'validation',
    message: 'Invalid email format',
    description: 'The provided email address is not in a valid format',
    severity: 'low',
    recoverable: true
  },
  PASSWORD_TOO_WEAK: {
    code: 'PASSWORD_TOO_WEAK',
    category: 'validation',
    message: 'Password does not meet security requirements',
    description: 'Password must be at least 8 characters with mixed case, numbers, and symbols',
    severity: 'medium',
    recoverable: true
  },

  // Resource errors
  RESOURCE_NOT_FOUND: {
    code: 'RESOURCE_NOT_FOUND',
    category: 'not_found',
    message: 'Requested resource not found',
    description: 'The specified resource does not exist or has been deleted',
    severity: 'medium',
    recoverable: false
  },
  CUSTOMER_NOT_FOUND: {
    code: 'CUSTOMER_NOT_FOUND',
    category: 'not_found',
    message: 'Customer not found',
    description: 'No customer exists with the provided ID',
    severity: 'medium',
    recoverable: false
  },
  SERVICE_NOT_FOUND: {
    code: 'SERVICE_NOT_FOUND',
    category: 'not_found',
    message: 'Service not found',
    description: 'The requested service does not exist',
    severity: 'medium',
    recoverable: false
  },

  // Conflict errors
  RESOURCE_ALREADY_EXISTS: {
    code: 'RESOURCE_ALREADY_EXISTS',
    category: 'conflict',
    message: 'Resource already exists',
    description: 'A resource with the same identifier already exists',
    severity: 'medium',
    recoverable: true
  },
  EMAIL_ALREADY_REGISTERED: {
    code: 'EMAIL_ALREADY_REGISTERED',
    category: 'conflict',
    message: 'Email address already registered',
    description: 'An account with this email address already exists',
    severity: 'medium',
    recoverable: true
  },
  CONCURRENT_MODIFICATION: {
    code: 'CONCURRENT_MODIFICATION',
    category: 'conflict',
    message: 'Resource was modified by another user',
    description: 'The resource has been updated since you last viewed it',
    severity: 'medium',
    recoverable: true,
    retry_after: 5
  },

  // Rate limiting
  RATE_LIMIT_EXCEEDED: {
    code: 'RATE_LIMIT_EXCEEDED',
    category: 'rate_limit',
    message: 'Rate limit exceeded',
    description: 'Too many requests sent in a given time frame',
    severity: 'medium',
    recoverable: true,
    retry_after: 60
  },
  QUOTA_EXCEEDED: {
    code: 'QUOTA_EXCEEDED',
    category: 'rate_limit',
    message: 'API quota exceeded',
    description: 'Monthly or daily API quota has been exceeded',
    severity: 'high',
    recoverable: false
  },

  // Server errors
  INTERNAL_SERVER_ERROR: {
    code: 'INTERNAL_SERVER_ERROR',
    category: 'server_error',
    message: 'Internal server error occurred',
    description: 'An unexpected error occurred on the server',
    severity: 'critical',
    recoverable: true,
    retry_after: 30
  },
  DATABASE_CONNECTION_ERROR: {
    code: 'DATABASE_CONNECTION_ERROR',
    category: 'server_error',
    message: 'Database connection error',
    description: 'Unable to connect to the database',
    severity: 'critical',
    recoverable: true,
    retry_after: 60
  },
  SERVICE_UNAVAILABLE: {
    code: 'SERVICE_UNAVAILABLE',
    category: 'server_error',
    message: 'Service temporarily unavailable',
    description: 'The service is temporarily down for maintenance',
    severity: 'high',
    recoverable: true,
    retry_after: 300
  },

  // Network errors
  CONNECTION_TIMEOUT: {
    code: 'CONNECTION_TIMEOUT',
    category: 'timeout',
    message: 'Request timeout',
    description: 'The request took too long to complete',
    severity: 'medium',
    recoverable: true,
    retry_after: 10
  },
  NETWORK_ERROR: {
    code: 'NETWORK_ERROR',
    category: 'network_error',
    message: 'Network connection error',
    description: 'Unable to establish network connection',
    severity: 'medium',
    recoverable: true,
    retry_after: 15
  },

  // Business logic errors
  INSUFFICIENT_BALANCE: {
    code: 'INSUFFICIENT_BALANCE',
    category: 'business_logic',
    message: 'Insufficient account balance',
    description: 'Account balance is insufficient to complete this transaction',
    severity: 'medium',
    recoverable: false
  },
  SERVICE_LIMIT_REACHED: {
    code: 'SERVICE_LIMIT_REACHED',
    category: 'business_logic',
    message: 'Service limit reached',
    description: 'Maximum number of services for this plan has been reached',
    severity: 'medium',
    recoverable: false
  },
  BILLING_CYCLE_IN_PROGRESS: {
    code: 'BILLING_CYCLE_IN_PROGRESS',
    category: 'business_logic',
    message: 'Billing cycle currently in progress',
    description: 'Changes cannot be made during active billing cycle',
    severity: 'medium',
    recoverable: true,
    retry_after: 3600
  },

  // File upload errors
  FILE_TOO_LARGE: {
    code: 'FILE_TOO_LARGE',
    category: 'validation',
    message: 'File size exceeds limit',
    description: 'The uploaded file is larger than the maximum allowed size',
    severity: 'medium',
    recoverable: true
  },
  UNSUPPORTED_FILE_TYPE: {
    code: 'UNSUPPORTED_FILE_TYPE',
    category: 'validation',
    message: 'Unsupported file type',
    description: 'The file type is not supported for this operation',
    severity: 'medium',
    recoverable: true
  },
  VIRUS_DETECTED: {
    code: 'VIRUS_DETECTED',
    category: 'validation',
    message: 'Security threat detected in file',
    description: 'The uploaded file contains a potential security threat',
    severity: 'high',
    recoverable: false
  },

  // External service errors
  PAYMENT_GATEWAY_ERROR: {
    code: 'PAYMENT_GATEWAY_ERROR',
    category: 'external_service',
    message: 'Payment processing error',
    description: 'Unable to process payment through payment gateway',
    severity: 'high',
    recoverable: true,
    retry_after: 60
  },
  EMAIL_SERVICE_ERROR: {
    code: 'EMAIL_SERVICE_ERROR',
    category: 'external_service',
    message: 'Email delivery failed',
    description: 'Unable to send email through email service provider',
    severity: 'medium',
    recoverable: true,
    retry_after: 300
  },
  SMS_SERVICE_ERROR: {
    code: 'SMS_SERVICE_ERROR',
    category: 'external_service',
    message: 'SMS delivery failed',
    description: 'Unable to send SMS through SMS service provider',
    severity: 'medium',
    recoverable: true,
    retry_after: 300
  }
};

// Error handling utilities
export interface ErrorHandlingOptions {
  showUserFriendlyMessage?: boolean;
  retryAutomatically?: boolean;
  logError?: boolean;
  showSuggestions?: boolean;
}

// Client-side error wrapper
export class ApiError extends Error {
  public readonly code: string;
  public readonly category: ErrorCategory;
  public readonly severity: ErrorCodeDefinition['severity'];
  public readonly recoverable: boolean;
  public readonly retryAfter?: number;
  public readonly traceId?: string;
  public readonly requestId?: string;
  public readonly fieldErrors?: FieldError[];
  public readonly context?: ErrorContext;
  public readonly timestamp: string;
  public readonly suggestions?: string[];

  constructor(errorResponse: ErrorResponse) {
    const definition = ERROR_CODES[errorResponse.error.code] || {
      code: errorResponse.error.code,
      category: 'server_error' as ErrorCategory,
      message: errorResponse.error.message,
      description: 'Unknown error occurred',
      severity: 'medium' as const,
      recoverable: true
    };

    super(definition.message);
    
    this.name = 'ApiError';
    this.code = errorResponse.error.code;
    this.category = definition.category;
    this.severity = definition.severity;
    this.recoverable = definition.recoverable;
    this.retryAfter = definition.retry_after;
    this.traceId = errorResponse.trace_id;
    this.requestId = errorResponse.request_id;
    this.fieldErrors = errorResponse.error.field_errors;
    this.context = errorResponse.error.context;
    this.timestamp = errorResponse.timestamp;
    this.suggestions = errorResponse.error.suggestions;
  }

  /**
   * Get user-friendly error message
   */
  getUserFriendlyMessage(): string {
    const definition = ERROR_CODES[this.code];
    if (!definition) return this.message;

    switch (this.category) {
      case 'authentication':
        return 'Please check your login credentials and try again.';
      case 'authorization':
        return 'You don\'t have permission to perform this action.';
      case 'validation':
        return 'Please check your input and correct any errors.';
      case 'not_found':
        return 'The requested item could not be found.';
      case 'conflict':
        return 'This action conflicts with existing data. Please refresh and try again.';
      case 'rate_limit':
        return 'Too many requests. Please wait a moment and try again.';
      case 'server_error':
        return 'A server error occurred. Please try again later.';
      case 'network_error':
      case 'timeout':
        return 'Connection problem. Please check your internet and try again.';
      case 'business_logic':
        return this.message; // Business logic errors should show specific messages
      case 'external_service':
        return 'A third-party service is temporarily unavailable. Please try again later.';
      default:
        return 'An unexpected error occurred. Please try again.';
    }
  }

  /**
   * Check if error should trigger automatic retry
   */
  shouldRetryAutomatically(): boolean {
    return this.recoverable && this.retryAfter !== undefined && [
      'server_error',
      'network_error', 
      'timeout',
      'external_service',
      'rate_limit'
    ].includes(this.category);
  }

  /**
   * Get formatted error details for debugging
   */
  getDebugInfo(): Record<string, any> {
    return {
      code: this.code,
      category: this.category,
      severity: this.severity,
      recoverable: this.recoverable,
      retryAfter: this.retryAfter,
      traceId: this.traceId,
      requestId: this.requestId,
      timestamp: this.timestamp,
      fieldErrors: this.fieldErrors,
      context: this.context,
      suggestions: this.suggestions
    };
  }
}