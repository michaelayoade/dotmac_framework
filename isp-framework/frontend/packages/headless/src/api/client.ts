/**
 * Type-safe API client for DotMac platform with enhanced security
 */

import type {
  ApiError,
  ApiResponse,
  ChatSession,
  Customer,
  DashboardMetrics,
  Invoice,
  NetworkAlert,
  NetworkDevice,
  PaginatedResponse,
  QueryParams,
  ServicePlan,
  User,
} from '../types';
import { csrfProtection } from '../utils/csrfProtection';
import { getBackendEndpoint } from './endpoint-mapping';

// Constants to avoid duplication
const AUTH_REQUIRED_ERROR = 'Unauthorized - authentication required';

import { inputSanitizer } from '../utils/sanitization';
import { type TokenPair, tokenManager } from '../utils/tokenManager';

export interface ApiClientConfig {
  baseUrl: string;
  apiKey?: string;
  tenantId?: string;
  timeout?: number;
  retryAttempts?: number;
  onUnauthorized?: () => void;
  onError?: (error: ApiError) => void;
}

export class ApiClient {
  private config: ApiClientConfig &
    Required<
      Pick<ApiClientConfig, 'baseUrl' | 'timeout' | 'retryAttempts' | 'onUnauthorized' | 'onError'>
    >;

  constructor(config: ApiClientConfig) {
    this.config = {
      baseUrl: config.baseUrl,
      apiKey: config.apiKey ?? undefined,
      tenantId: config.tenantId ?? undefined,
      timeout: config.timeout ?? 10000,
      retryAttempts: config.retryAttempts ?? 3,
      onUnauthorized:
        config.onUnauthorized ??
        (() => {
          // Implementation pending
        }),
      onError:
        config.onError ??
        (() => {
          // Implementation pending
        }),
    } as ApiClientConfig &
      Required<
        Pick<
          ApiClientConfig,
          'baseUrl' | 'timeout' | 'retryAttempts' | 'onUnauthorized' | 'onError'
        >
      >;
  }

  setAuthToken() {
    // Method implementation pending
  }

  clearAuthToken() {
    tokenManager.clearTokens();
  }

  private sanitizeBody(body: unknown): BodyInit | null {
    if (!body) {
      return null;
    }

    if (typeof body === 'string') {
      try {
        const parsed = JSON.parse(body);
        const sanitized = inputSanitizer.sanitizeFormData(parsed);
        return JSON.stringify(sanitized);
      } catch {
        return inputSanitizer.sanitizeText(body);
      }
    }

    // For non-string bodies (FormData, Blob, etc.)
    if (body instanceof FormData || body instanceof Blob || body instanceof ArrayBuffer) {
      return body as BodyInit;
    }

    // For objects, stringify them
    return JSON.stringify(body);
  }

  private buildHeaders(
    method: string,
    options: RequestInit = {
      // Implementation pending
    }
  ): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache',
      ...((options.headers as Record<string, string>) || {}),
    };

    const authToken = tokenManager.getAccessToken();
    if (authToken) {
      headers.Authorization = `Bearer ${authToken}`;
    }

    if (this.config.apiKey) {
      headers['X-API-Key'] = this.config.apiKey;
    }

    if (this.config.tenantId) {
      headers['X-Tenant-ID'] = this.config.tenantId;
    }

    if (csrfProtection.requiresProtection(method)) {
      Object.assign(headers, csrfProtection.getHeaders());
    }

    return headers;
  }

  private async handleUnauthorized<T>(
    attempt: number,
    url: string,
    requestOptions: RequestInit
  ): Promise<T> {
    if (attempt !== 0) {
      throw new Error(AUTH_REQUIRED_ERROR);
    }

    const refreshToken = tokenManager.getRefreshToken();
    if (!refreshToken) {
      throw new Error(AUTH_REQUIRED_ERROR);
    }

    try {
      const newTokens = await this.refreshToken(refreshToken);
      if (!newTokens) {
        throw new Error('Token refresh failed');
      }

      const newAuthToken = tokenManager.getAccessToken();
      if (!newAuthToken) {
        throw new Error('No access token after refresh');
      }

      const headers = { ...requestOptions.headers } as Record<string, string>;
      headers.Authorization = `Bearer ${newAuthToken}`;
      const retryResponse = await fetch(url, { ...requestOptions, headers });

      if (retryResponse.ok) {
        return (await retryResponse.json()) as T;
      }
      throw new Error('Retry after refresh failed');
    } catch (_error) {
      tokenManager.clearTokens();
      this.config.onUnauthorized();
      throw new Error(AUTH_REQUIRED_ERROR);
    }
  }

  private async handleErrorResponse(response: Response): Promise<never> {
    const errorData = await response.json().catch(() => ({}));
    const apiError: ApiError = {
      code: errorData.code || `HTTP_${response.status}`,
      message: errorData.message || response.statusText,
      details: errorData.details,
      traceId: errorData.traceId,
    };
    this.config.onError(apiError);
    throw new Error(apiError.message);
  }

  private shouldRetry(error: Error): boolean {
    return !(error.message === 'Unauthorized' || error.name === 'AbortError');
  }

  private async wait(attempt: number): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, 2 ** attempt * 1000));
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {
      // Implementation pending
    }
  ): Promise<T> {
    const method = options.method || 'GET';
    const backendEndpoint = getBackendEndpoint(`${method} ${endpoint}`);
    const url = `${this.config.baseUrl}${backendEndpoint}`;
    const sanitizedBody = this.sanitizeBody(options.body);
    const headers = this.buildHeaders(method, options);

    const requestOptions: RequestInit = {
      ...options,
      method,
      headers,
      body: sanitizedBody,
      signal: AbortSignal.timeout(this.config.timeout),
      credentials: 'same-origin',
    };

    let lastError: Error = new Error('Request failed');

    for (let attempt = 0; attempt <= this.config.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, requestOptions);

        if (!response.ok) {
          if (response.status === 401) {
            return await this.handleUnauthorized<T>(attempt, url, requestOptions);
          }
          await this.handleErrorResponse(response);
        }

        return (await response.json()) as T;
      } catch (error) {
        lastError = error as Error;

        if (!this.shouldRetry(lastError)) {
          throw lastError;
        }

        if (attempt < this.config.retryAttempts) {
          await this.wait(attempt);
        }
      }
    }

    throw lastError;
  }

  // Authentication
  async login(credentials: {
    email?: string;
    portalId?: string;
    accountNumber?: string;
    partnerCode?: string;
    password: string;
    portal: string;
  }): Promise<ApiResponse<{ user: User; token: string; refreshToken: string; tenant: unknown }>> {
    return this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async refreshToken(refreshToken: string): Promise<TokenPair> {
    const response = await this.request<
      ApiResponse<{ accessToken: string; refreshToken: string; expiresAt: number }>
    >('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refreshToken }),
    });

    return {
      accessToken: response.data.accessToken,
      refreshToken: response.data.refreshToken,
      expiresAt: response.data.expiresAt,
    };
  }

  async logout(): Promise<ApiResponse<Record<string, never>>> {
    return this.request('/api/v1/auth/logout', {
      method: 'POST',
    });
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request('/api/v1/auth/me');
  }

  // Customers
  async getCustomers(params?: QueryParams): Promise<PaginatedResponse<Customer>> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }

    const query = searchParams.toString();
    return this.request(`/api/v1/customers${query ? `?${query}` : ''}`);
  }

  async getCustomer(id: string): Promise<ApiResponse<Customer>> {
    return this.request(`/api/v1/customers/${id}`);
  }

  async createCustomer(
    customer: Omit<Customer, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<ApiResponse<Customer>> {
    return this.request('/api/v1/customers', {
      method: 'POST',
      body: JSON.stringify(customer),
    });
  }

  async updateCustomer(id: string, updates: Partial<Customer>): Promise<ApiResponse<Customer>> {
    return this.request(`/api/v1/customers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteCustomer(id: string): Promise<ApiResponse<Record<string, never>>> {
    return this.request(`/api/v1/customers/${id}`, {
      method: 'DELETE',
    });
  }

  // Billing
  async getInvoices(
    customerId?: string,
    params?: QueryParams
  ): Promise<PaginatedResponse<Invoice>> {
    const searchParams = new URLSearchParams();
    if (customerId) {
      searchParams.append('customerId', customerId);
    }
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }

    const query = searchParams.toString();
    return this.request(`/api/v1/billing/invoices${query ? `?${query}` : ''}`);
  }

  async getInvoice(id: string): Promise<ApiResponse<Invoice>> {
    return this.request(`/api/v1/billing/invoices/${id}`);
  }

  async createInvoice(
    invoice: Omit<Invoice, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<ApiResponse<Invoice>> {
    return this.request('/api/v1/billing/invoices', {
      method: 'POST',
      body: JSON.stringify(invoice),
    });
  }

  async payInvoice(
    id: string,
    paymentData: { method: string; amount: number }
  ): Promise<ApiResponse<Invoice>> {
    return this.request(`/api/v1/billing/invoices/${id}/pay`, {
      method: 'POST',
      body: JSON.stringify(paymentData),
    });
  }

  // Network Management
  async getNetworkDevices(params?: QueryParams): Promise<PaginatedResponse<NetworkDevice>> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }

    const query = searchParams.toString();
    return this.request(`/api/v1/network/devices${query ? `?${query}` : ''}`);
  }

  async getNetworkDevice(id: string): Promise<ApiResponse<NetworkDevice>> {
    return this.request(`/api/v1/network/devices/${id}`);
  }

  async updateNetworkDevice(
    id: string,
    updates: Partial<NetworkDevice>
  ): Promise<ApiResponse<NetworkDevice>> {
    return this.request(`/api/v1/network/devices/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async getNetworkAlerts(params?: QueryParams): Promise<PaginatedResponse<NetworkAlert>> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }

    const query = searchParams.toString();
    return this.request(`/api/v1/network/alerts${query ? `?${query}` : ''}`);
  }

  async acknowledgeAlert(id: string): Promise<ApiResponse<NetworkAlert>> {
    return this.request(`/api/v1/network/alerts/${id}/acknowledge`, {
      method: 'POST',
    });
  }

  async resolveAlert(id: string, resolution?: string): Promise<ApiResponse<NetworkAlert>> {
    return this.request(`/api/v1/network/alerts/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution }),
    });
  }

  // Live Chat
  async getChatSessions(params?: QueryParams): Promise<PaginatedResponse<ChatSession>> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }

    const query = searchParams.toString();
    return this.request(`/api/v1/chat/sessions${query ? `?${query}` : ''}`);
  }

  async getChatSession(id: string): Promise<ApiResponse<ChatSession>> {
    return this.request(`/api/v1/chat/sessions/${id}`);
  }

  async createChatSession(customerId: string, subject?: string): Promise<ApiResponse<ChatSession>> {
    return this.request('/api/v1/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ customerId, subject }),
    });
  }

  async closeChatSession(
    id: string,
    rating?: number,
    feedback?: string
  ): Promise<ApiResponse<ChatSession>> {
    return this.request(`/api/v1/chat/sessions/${id}/close`, {
      method: 'POST',
      body: JSON.stringify({ rating, feedback }),
    });
  }

  // Service Plans
  async getServicePlans(params?: QueryParams): Promise<PaginatedResponse<ServicePlan>> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value));
        }
      });
    }

    const query = searchParams.toString();
    return this.request(`/api/v1/services/plans${query ? `?${query}` : ''}`);
  }

  async getServicePlan(id: string): Promise<ApiResponse<ServicePlan>> {
    return this.request(`/api/v1/services/plans/${id}`);
  }

  // Dashboard
  async getDashboardMetrics(): Promise<ApiResponse<DashboardMetrics>> {
    return this.request('/api/v1/dashboard/metrics');
  }

  // File uploads
  async uploadFile(file: File, purpose: string): Promise<ApiResponse<{ url: string; id: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('purpose', purpose);

    return this.request('/api/v1/files/upload', {
      method: 'POST',
      body: formData,
      headers: {
        // Implementation pending
      }, // Let browser set Content-Type for FormData
    });
  }

  // Customer Portal APIs
  async getCustomerDashboard(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/dashboard');
  }

  async getCustomerServices(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/services');
  }

  async getCustomerBilling(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/billing');
  }

  async getCustomerUsage(period?: string): Promise<ApiResponse<unknown>> {
    const query = period ? `?period=${period}` : '';
    return this.request(`/api/v1/customer/usage${query}`);
  }

  async getCustomerDocuments(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/documents');
  }

  async getCustomerSupportTickets(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/support/tickets');
  }

  async createSupportTicket(data: unknown): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/support/tickets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async replySupportTicket(ticketId: string, message: string): Promise<ApiResponse<unknown>> {
    return this.request(`/api/v1/customer/support/tickets/${ticketId}/reply`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async runSpeedTest(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/services/speed-test', {
      method: 'POST',
    });
  }

  async requestServiceUpgrade(upgradeId: string): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/customer/services/upgrade', {
      method: 'POST',
      body: JSON.stringify({ upgradeId }),
    });
  }

  // Admin Portal APIs
  async getAdminDashboard(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/admin/dashboard');
  }

  async getSystemAlerts(): Promise<ApiResponse<any[]>> {
    return this.request('/api/v1/admin/system/alerts');
  }

  async getNetworkStatus(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/admin/network/status');
  }

  // Reseller Portal APIs
  async getResellerDashboard(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/reseller/dashboard');
  }

  async getResellerCommissions(): Promise<ApiResponse<unknown>> {
    return this.request('/api/v1/reseller/commissions');
  }

  async getResellerCustomers(): Promise<ApiResponse<any[]>> {
    return this.request('/api/v1/reseller/customers');
  }
}

// Create a default client instance
let defaultClient: ApiClient | null = null;

export function createApiClient(config: ApiClientConfig): ApiClient {
  const client = new ApiClient(config);
  if (!defaultClient) {
    defaultClient = client;
  }
  return client;
}

export function getApiClient(): ApiClient {
  if (!defaultClient) {
    throw new Error('API client not initialized. Call createApiClient() first.');
  }
  return defaultClient;
}
