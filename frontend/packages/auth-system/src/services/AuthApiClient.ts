/**
 * Authentication API Client
 *
 * Handles all authentication-related API communication with the backend
 * Provides type-safe methods for login, logout, user management, and security operations
 */

import type {
  LoginCredentials,
  LoginResponse,
  User,
  MfaSetup,
  MfaVerification,
  PasswordChangeRequest,
  PasswordResetRequest,
  Session,
  ApiResponse,
} from '../types';

interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
}

export class AuthApiClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || this.getDefaultBaseUrl();
    this.timeout = 30000; // 30 seconds
  }

  private getDefaultBaseUrl(): string {
    if (typeof window === 'undefined') {
      return 'http://localhost:8000'; // SSR fallback
    }

    // Auto-detect API endpoint based on environment
    const { protocol, hostname } = window.location;

    // Development environment detection
    if (hostname === 'localhost' || hostname.startsWith('127.') || hostname.includes('dev')) {
      return `${protocol}//${hostname}:8000`;
    }

    // Production environment - same origin by default
    return `${protocol}//${hostname}/api`;
  }

  private async request<T = any>(
    endpoint: string,
    config: RequestConfig = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    const { method = 'GET', headers = {}, body, timeout = this.timeout } = config;

    // Default headers
    const defaultHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...headers,
    };

    // Add authorization header if we have a token
    const accessToken = await this.getAccessToken();
    if (accessToken) {
      defaultHeaders.Authorization = `Bearer ${accessToken}`;
    }

    // Add CSRF token if available
    const csrfToken = await this.getCsrfToken();
    if (csrfToken) {
      defaultHeaders['X-CSRF-Token'] = csrfToken;
    }

    // Request configuration
    const requestConfig: RequestInit = {
      method,
      headers: defaultHeaders,
      credentials: 'include', // Include cookies for session management
    };

    // Add body for non-GET requests
    if (body && method !== 'GET') {
      requestConfig.body = JSON.stringify(body);
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    requestConfig.signal = controller.signal;

    try {
      const response = await fetch(url, requestConfig);
      clearTimeout(timeoutId);

      // Parse response
      let data: any;
      const contentType = response.headers.get('Content-Type') || '';

      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      // Handle error responses
      if (!response.ok) {
        throw {
          code: data?.error?.code || `HTTP_${response.status}`,
          message: data?.error?.message || `HTTP ${response.status}: ${response.statusText}`,
          details: data?.error?.details,
          status: response.status,
        };
      }

      return {
        success: true,
        data,
        meta: {
          rateLimit: this.parseRateLimitHeaders(response) || undefined,
        },
      };
    } catch (error) {
      clearTimeout(timeoutId);

      if ((error as any).name === 'AbortError') {
        throw {
          code: 'REQUEST_TIMEOUT',
          message: `Request timed out after ${timeout}ms`,
        };
      }

      if ((error as any).code) {
        throw error; // Re-throw API errors
      }

      // Network or other errors
      throw {
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to authentication service',
        details: (error as any).message,
      };
    }
  }

  private parseRateLimitHeaders(response: Response) {
    const limit = response.headers.get('X-RateLimit-Limit');
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const reset = response.headers.get('X-RateLimit-Reset');

    if (!limit || !remaining || !reset) return undefined;

    return {
      limit: parseInt(limit, 10),
      remaining: parseInt(remaining, 10),
      resetTime: new Date(parseInt(reset, 10) * 1000),
    };
  }

  private async getAccessToken(): Promise<string | null> {
    // This would typically get the token from secure storage
    if (typeof window === 'undefined') return null;

    try {
      // Try to get from secure storage first (implementation would depend on TokenManager)
      const stored = localStorage.getItem('auth_token');
      return stored ? JSON.parse(stored).accessToken : null;
    } catch {
      return null;
    }
  }

  private async getCsrfToken(): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    try {
      const stored = localStorage.getItem('csrf_token');
      return stored || null;
    } catch {
      return null;
    }
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<ApiResponse<LoginResponse>> {
    return this.request<LoginResponse>('/v1/auth/login', {
      method: 'POST',
      body: credentials,
    });
  }

  async logout(): Promise<ApiResponse<void>> {
    return this.request<void>('/v1/auth/logout', {
      method: 'POST',
    });
  }

  async refreshToken(refreshToken: string): Promise<ApiResponse<{ tokens: any }>> {
    return this.request<{ tokens: any }>('/v1/auth/refresh', {
      method: 'POST',
      body: { refreshToken },
    });
  }

  // User management endpoints
  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request<User>('/v1/auth/me');
  }

  async updateProfile(updates: Partial<User>): Promise<ApiResponse<User>> {
    return this.request<User>('/v1/auth/profile', {
      method: 'PATCH',
      body: updates,
    });
  }

  // Password management endpoints
  async changePassword(request: PasswordChangeRequest): Promise<ApiResponse<void>> {
    return this.request<void>('/v1/auth/password/change', {
      method: 'POST',
      body: request,
    });
  }

  async resetPassword(request: PasswordResetRequest): Promise<ApiResponse<void>> {
    if (request.token && request.newPassword) {
      // Confirm password reset
      return this.request<void>('/v1/auth/password/reset/confirm', {
        method: 'POST',
        body: {
          token: request.token,
          newPassword: request.newPassword,
        },
      });
    } else {
      // Request password reset
      return this.request<void>('/v1/auth/password/reset/request', {
        method: 'POST',
        body: {
          email: request.email,
          portalId: request.portalId,
          accountNumber: request.accountNumber,
        },
      });
    }
  }

  // MFA endpoints
  async setupMfa(type: 'totp' | 'sms' | 'email'): Promise<ApiResponse<MfaSetup>> {
    return this.request<MfaSetup>('/v1/auth/mfa/setup', {
      method: 'POST',
      body: { type },
    });
  }

  async verifyMfa(verification: MfaVerification): Promise<ApiResponse<{ verified: boolean }>> {
    return this.request<{ verified: boolean }>('/v1/auth/mfa/verify', {
      method: 'POST',
      body: verification,
    });
  }

  async disableMfa(): Promise<ApiResponse<void>> {
    return this.request<void>('/v1/auth/mfa/disable', {
      method: 'POST',
    });
  }

  async generateBackupCodes(): Promise<ApiResponse<{ codes: string[] }>> {
    return this.request<{ codes: string[] }>('/v1/auth/mfa/backup-codes', {
      method: 'POST',
    });
  }

  // Session management endpoints
  async getSessions(): Promise<ApiResponse<Session[]>> {
    return this.request<Session[]>('/v1/auth/sessions');
  }

  async terminateSession(sessionId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/v1/auth/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async terminateAllSessions(): Promise<ApiResponse<void>> {
    return this.request<void>('/v1/auth/sessions', {
      method: 'DELETE',
    });
  }

  // Security endpoints
  async getSecurityEvents(limit = 50, offset = 0): Promise<ApiResponse<{
    events: any[];
    total: number;
  }>> {
    return this.request(`/v1/auth/security/events?limit=${limit}&offset=${offset}`);
  }

  async reportSuspiciousActivity(details: Record<string, any>): Promise<ApiResponse<void>> {
    return this.request<void>('/v1/auth/security/report', {
      method: 'POST',
      body: details,
    });
  }

  async validateSession(): Promise<ApiResponse<{ valid: boolean }>> {
    return this.request<{ valid: boolean }>('/v1/auth/validate');
  }

  // Portal-specific endpoints
  async getPortalConfig(portalType: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/portals/${portalType}/config`);
  }

  async switchPortal(portalType: string): Promise<ApiResponse<{ redirectUrl: string }>> {
    return this.request<{ redirectUrl: string }>('/v1/auth/portal/switch', {
      method: 'POST',
      body: { portalType },
    });
  }

  // Customer portal specific endpoints
  async validatePortalId(portalId: string): Promise<ApiResponse<{
    valid: boolean;
    customerId?: string;
    accountInfo?: any;
  }>> {
    return this.request(`/v1/auth/portal-id/validate`, {
      method: 'POST',
      body: { portalId },
    });
  }

  async validateAccountNumber(accountNumber: string): Promise<ApiResponse<{
    valid: boolean;
    customerId?: string;
    accountInfo?: any;
  }>> {
    return this.request(`/v1/auth/account-number/validate`, {
      method: 'POST',
      body: { accountNumber },
    });
  }

  // Reseller portal specific endpoints
  async validatePartnerCode(partnerCode: string): Promise<ApiResponse<{
    valid: boolean;
    resellerId?: string;
    territory?: any;
  }>> {
    return this.request(`/v1/auth/partner-code/validate`, {
      method: 'POST',
      body: { partnerCode },
    });
  }

  // API key management (for programmatic access)
  async createApiKey(name: string, permissions: string[]): Promise<ApiResponse<{
    keyId: string;
    key: string;
    expiresAt?: Date;
  }>> {
    return this.request('/v1/auth/api-keys', {
      method: 'POST',
      body: { name, permissions },
    });
  }

  async listApiKeys(): Promise<ApiResponse<{
    id: string;
    name: string;
    permissions: string[];
    createdAt: Date;
    lastUsed?: Date;
    expiresAt?: Date;
  }[]>> {
    return this.request('/v1/auth/api-keys');
  }

  async revokeApiKey(keyId: string): Promise<ApiResponse<void>> {
    return this.request(`/v1/auth/api-keys/${keyId}`, {
      method: 'DELETE',
    });
  }

  // Health check endpoint
  async healthCheck(): Promise<ApiResponse<{
    status: string;
    timestamp: Date;
    version?: string;
  }>> {
    return this.request('/health');
  }

  // Rate limit status
  async getRateLimitStatus(): Promise<ApiResponse<{
    limit: number;
    remaining: number;
    resetTime: Date;
  }>> {
    return this.request('/v1/auth/rate-limit');
  }

  // CSRF token endpoint
  async getCsrfTokenFromServer(): Promise<ApiResponse<{ token: string }>> {
    return this.request<{ token: string }>('/v1/auth/csrf-token');
  }

  // Initialize CSRF protection
  async initializeCsrf(): Promise<void> {
    try {
      const response = await this.getCsrfTokenFromServer();
      if (response.success && response.data) {
        localStorage.setItem('csrf_token', response.data.token);
      }
    } catch (error) {
      console.warn('Failed to initialize CSRF token:', error);
    }
  }
}
