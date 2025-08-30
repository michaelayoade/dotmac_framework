/**
 * @dotmac/utils - Consolidated utilities for the DotMac Framework
 *
 * This package consolidates common utilities from across the monorepo
 * to eliminate code duplication and provide a single source of truth.
 */

// Input sanitization (consolidated from security and headless packages)
export * from './sanitization';
export {
  InputSanitizer,
  sanitizer,
  sanitizeInput,
  sanitizeEmail,
  sanitizePhone,
  sanitizeURL,
  sanitizeFilePath,
  // Legacy API compatibility
  cleanInput,
  sanitizeHtml,
} from './sanitization';

// Validation utilities (consolidated Zod schemas)
export * from './validation';
export {
  commonSchemas,
  ispSchemas,
  FormValidator,
  validateEmail,
  validatePhone,
  validateURL,
  validateCustomer,
  validateService,
  validateInvoice,
} from './validation';

// Formatting utilities (consolidated from multiple packages)
export * from './formatting';
export {
  cn,
  formatFileSize,
  formatCurrency,
  formatPercentage,
  formatPhoneNumber,
  formatDate,
  formatDateTime,
  formatRelativeTime,
  truncate,
  capitalize,
  titleCase,
  kebabCase,
  camelCase,
  generateId,
  generateUUID,
  formatMACAddress,
  formatIPAddress,
  formatBandwidth,
  formatUsage,
} from './formatting';

// Storage utilities (consolidated from headless and primitives)
export * from './storage';
export {
  safeLocalStorage,
  safeSessionStorage,
  getStorageItem,
  setStorageItem,
  removeStorageItem,
  useLocalStorage,
  useSessionStorage,
  usePersistedState,
  clearAllStorage,
  getStorageKeys,
  getStorageSize,
  setExpiringStorageItem,
  getExpiringStorageItem,
  createStorageCache,
} from './storage';

// Re-export types for convenience
export type {
  Customer,
  Service,
  Invoice,
  ValidationResult,
  FormValidationResult,
} from './validation';

export type {
  SanitizationConfig,
  SanitizationResult,
} from './sanitization';

export type {
  StorageInterface,
} from './storage';
