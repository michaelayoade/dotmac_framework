// Main exports
export { HttpClient } from './http-client';
export { TenantResolver } from './tenant-resolver';
export { ErrorNormalizer } from './error-normalizer';
export { RetryHandler } from './retry-handler';
export { AuthInterceptor } from './auth-interceptor';

// Type exports
export type {
  HttpClientConfig,
  RequestConfig,
  ApiResponse,
  ApiError,
  HttpMethod,
  RetryConfig,
  TenantConfig
} from './types';

export type { AuthConfig } from './auth-interceptor';

// Default instance for convenience
export const httpClient = HttpClient.createFromHostname({
  timeout: 30000,
  retries: 3
}).enableAuth();

// Utility functions
export const createHttpClient = HttpClient.create;
export const createTenantClient = HttpClient.createWithTenant;
export const createAuthClient = HttpClient.createWithAuth;