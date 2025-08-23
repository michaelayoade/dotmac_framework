// Main API exports
export * from './client';
// Re-export for convenience
export { getApiClient } from './client';
export * from './config';
export { checkApiHealth, initializeApi, requireApiClient } from './config';

// ISP Framework API Client
export * from './isp-client';
export { getISPApiClient, createISPApiClient } from './isp-client';

// Individual API Clients
export * from './clients/BaseApiClient';
export * from './clients/AuthApiClient';
export * from './clients/FileApiClient';
export * from './clients/AnalyticsApiClient';
export * from './clients/BillingApiClient';
export * from './clients/ComplianceApiClient';
export * from './clients/FieldOpsApiClient';
export * from './clients/IdentityApiClient';
export * from './clients/InventoryApiClient';
export * from './clients/LicensingApiClient';
export * from './clients/NetworkingApiClient';
export * from './clients/NotificationsApiClient';
export * from './clients/ResellersApiClient';
export * from './clients/ServicesApiClient';
export * from './clients/SupportApiClient';

// API Types
export * from './types/api';
export * from './types/errors';
export * from './types/services';
export * from './types/billing';

// API Manager and Utilities
export * from './manager/ApiManager';
export { createApiManager, getApiManager } from './manager/ApiManager';
export * from './utils/rateLimiting';
export { 
  rateLimiter, 
  retryHandler, 
  circuitBreaker, 
  errorRecoveryManager 
} from './utils/rateLimiting';

// Convenience re-exports
export { ApiError, ERROR_CODES } from './types/errors';
export type { 
  ErrorResponse, 
  FieldError, 
  ErrorCategory,
  ErrorCodeDefinition 
} from './types/errors';
