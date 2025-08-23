/**
 * Authentication API Client
 * Handles all authentication-related API calls including login, logout, token refresh,
 * password reset, MFA, and session management
 */

import { BaseApiClient } from './BaseApiClient';
import type { ApiResponse, PaginatedResponse } from '../types/api';

// Authentication interfaces
export interface LoginCredentials {
  email?: string;
  portalId?: string;
  accountNumber?: string;
  partnerCode?: string;
  password: string;
  portal: 'admin' | 'customer' | 'reseller' | 'technician';
  rememberMe?: boolean;
  mfaToken?: string;
}

export interface AuthResponse {
  user: {
    id: string;
    email: string;
    name: string;
    role: string;
    permissions: string[];
    portal: string;
    tenant_id: string;
    last_login?: string;
  };
  tokens: {
    access_token: string;
    refresh_token: string;
    expires_at: number;
    token_type: 'Bearer';
  };
  tenant: {
    id: string;
    name: string;
    plan: string;
    features: string[];
  };
  session: {
    id: string;
    expires_at: number;
    ip_address: string;
    user_agent: string;
  };
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  token_type: 'Bearer';
}

export interface PasswordResetRequest {
  email: string;
  portal: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface MFASetupRequest {
  method: 'totp' | 'sms' | 'email';
  phone?: string;
}

export interface MFASetupResponse {
  secret?: string;
  qr_code?: string;
  backup_codes: string[];
}

export interface MFAVerifyRequest {
  token: string;
  method: 'totp' | 'sms' | 'email';
}

export interface SessionData {
  id: string;
  user_id: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_activity: string;
  expires_at: string;
  active: boolean;
}

export interface ApiKeyData {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used?: string;
  expires_at?: string;
}

export interface CreateApiKeyRequest {
  name: string;
  scopes: string[];
  expires_in_days?: number;
}

export class AuthApiClient extends BaseApiClient {
  constructor(baseURL: string, defaultHeaders: Record<string, string> = {}) {
    super(baseURL, defaultHeaders, 'AuthAPI');
  }

  /**
   * Authenticate user with various credential types
   */
  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthResponse>> {
    return this.request<AuthResponse>('POST', '/auth/login', credentials);
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<ApiResponse<RefreshTokenResponse>> {
    return this.request<RefreshTokenResponse>('POST', '/auth/refresh', {
      refresh_token: refreshToken
    });
  }

  /**
   * Logout and invalidate session
   */
  async logout(): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/logout');
  }

  /**
   * Get current authenticated user info
   */
  async getCurrentUser(): Promise<ApiResponse<AuthResponse['user']>> {
    return this.request<AuthResponse['user']>('GET', '/me');
  }

  /**
   * Update user profile information
   */
  async updateProfile(updates: {
    name?: string;
    email?: string;
    phone?: string;
    timezone?: string;
    locale?: string;
  }): Promise<ApiResponse<AuthResponse['user']>> {
    return this.request<AuthResponse['user']>('PUT', '/me', updates);
  }

  /**
   * Request password reset email
   */
  async requestPasswordReset(request: PasswordResetRequest): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/password/reset', request);
  }

  /**
   * Confirm password reset with token
   */
  async confirmPasswordReset(request: PasswordResetConfirm): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/password/confirm', request);
  }

  /**
   * Change password for authenticated user
   */
  async changePassword(request: ChangePasswordRequest): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/password/change', request);
  }

  /**
   * Setup Multi-Factor Authentication
   */
  async setupMFA(request: MFASetupRequest): Promise<ApiResponse<MFASetupResponse>> {
    return this.request<MFASetupResponse>('POST', '/auth/mfa/setup', request);
  }

  /**
   * Verify MFA token
   */
  async verifyMFA(request: MFAVerifyRequest): Promise<ApiResponse<{ verified: boolean }>> {
    return this.request<{ verified: boolean }>('POST', '/auth/mfa/verify', request);
  }

  /**
   * Disable MFA for user
   */
  async disableMFA(password: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/mfa/disable', { password });
  }

  /**
   * Get MFA backup codes
   */
  async getMFABackupCodes(): Promise<ApiResponse<{ codes: string[] }>> {
    return this.request<{ codes: string[] }>('GET', '/auth/mfa/backup-codes');
  }

  /**
   * Regenerate MFA backup codes
   */
  async regenerateMFABackupCodes(): Promise<ApiResponse<{ codes: string[] }>> {
    return this.request<{ codes: string[] }>('POST', '/auth/mfa/backup-codes/regenerate');
  }

  /**
   * Get user's active sessions
   */
  async getSessions(): Promise<ApiResponse<SessionData[]>> {
    return this.request<SessionData[]>('GET', '/auth/sessions');
  }

  /**
   * Revoke a specific session
   */
  async revokeSession(sessionId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('DELETE', `/auth/sessions/${sessionId}`);
  }

  /**
   * Revoke all sessions except current
   */
  async revokeAllSessions(): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/sessions/revoke-all');
  }

  /**
   * Get user's API keys
   */
  async getApiKeys(): Promise<ApiResponse<ApiKeyData[]>> {
    return this.request<ApiKeyData[]>('GET', '/auth/api-keys');
  }

  /**
   * Create new API key
   */
  async createApiKey(request: CreateApiKeyRequest): Promise<ApiResponse<ApiKeyData & { key: string }>> {
    return this.request<ApiKeyData & { key: string }>('POST', '/auth/api-keys', request);
  }

  /**
   * Revoke an API key
   */
  async revokeApiKey(keyId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('DELETE', `/auth/api-keys/${keyId}`);
  }

  /**
   * Validate API key (for server-side validation)
   */
  async validateApiKey(key: string): Promise<ApiResponse<{ valid: boolean; scopes: string[] }>> {
    return this.request<{ valid: boolean; scopes: string[] }>('POST', '/auth/api-keys/validate', {
      key
    });
  }

  /**
   * Check if email is available
   */
  async checkEmailAvailable(email: string): Promise<ApiResponse<{ available: boolean }>> {
    return this.request<{ available: boolean }>('POST', '/auth/check-email', { email });
  }

  /**
   * Verify email address
   */
  async verifyEmail(token: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/verify-email', { token });
  }

  /**
   * Resend email verification
   */
  async resendEmailVerification(): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('POST', '/auth/verify-email/resend');
  }

  /**
   * Get authentication audit log
   */
  async getAuthAuditLog(params?: {
    page?: number;
    limit?: number;
    start_date?: string;
    end_date?: string;
    action?: string;
  }): Promise<PaginatedResponse<{
    id: string;
    user_id: string;
    action: string;
    ip_address: string;
    user_agent: string;
    success: boolean;
    details?: Record<string, any>;
    created_at: string;
  }>> {
    return this.request<PaginatedResponse<any>>('GET', '/auth/audit-log', null, { params });
  }

  /**
   * Get available scopes for API keys
   */
  async getAvailableScopes(): Promise<ApiResponse<{
    scopes: Array<{
      name: string;
      description: string;
      category: string;
    }>;
  }>> {
    return this.request<any>('GET', '/auth/scopes');
  }
}