/**
 * Universal Authentication Hook
 *
 * Provides comprehensive authentication functionality across all portals
 * with portal-aware behavior, security features, and session management
 */

import { useCallback, useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  AuthHookReturn,
  AuthState,
  LoginCredentials,
  LoginResponse,
  LoginError,
  User,
  PortalVariant,
  PortalConfig,
  Session,
  MfaSetup,
  MfaVerification,
  PasswordChangeRequest,
  PasswordResetRequest,
  AuthEvent,
  RateLimitStatus,
  ValidationResult,
} from '../types';

import { AuthApiClient } from '../services/AuthApiClient';
import { TokenManager } from '../services/TokenManager';
import { SessionManager } from '../services/SessionManager';
import { RateLimiter } from '../services/RateLimiter';
import { SecurityService } from '../services/SecurityService';
import { validateLoginCredentials, validatePasswordStrength } from '../validation/schemas';
import { getPortalConfig } from '../config/portal-configs';

// API client singleton
const authApi = new AuthApiClient();
const tokenManager = new TokenManager();
const sessionManager = new SessionManager();
const rateLimiter = new RateLimiter();
const securityService = new SecurityService();

export function useAuth(portalVariant?: PortalVariant): AuthHookReturn {
  const queryClient = useQueryClient();

  // Local state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<LoginError | null>(null);
  const [portalConfig, setPortalConfig] = useState<PortalConfig | null>(null);

  // Initialize portal configuration
  useEffect(() => {
    if (portalVariant) {
      setPortalConfig(getPortalConfig(portalVariant));
    }
  }, [portalVariant]);

  // Current user query
  const {
    data: user,
    isLoading: isUserLoading,
    error: userError,
    refetch: refetchUser,
  } = useQuery({
    queryKey: ['auth', 'user'],
    queryFn: async (): Promise<User | null> => {
      const token = await tokenManager.getValidToken();
      if (!token) return null;

      try {
        const response = await authApi.getCurrentUser();
        return response.data || null;
      } catch (error) {
        // Token might be invalid, clear it
        await tokenManager.clearTokens();
        return null;
      }
    },
    enabled: Boolean(tokenManager.hasTokens),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error) => {
      // Don't retry on auth errors
      return failureCount < 2 && !String(error).includes('401');
    },
  });

  // Current session query
  const { data: session } = useQuery({
    queryKey: ['auth', 'session'],
    queryFn: async (): Promise<Session | null> => {
      return sessionManager.getCurrentSession();
    },
    enabled: !!user,
    staleTime: 1 * 60 * 1000, // 1 minute
  });

  // Authentication state
  const isAuthenticated = !!user;
  const permissions = user?.permissions || [];
  const role = user?.role || null;

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials): Promise<LoginResponse> => {
      setError(null);

      // Rate limiting check
      const rateLimitCheck = await rateLimiter.checkLimit('login');
      if (!rateLimitCheck.allowed) {
        throw {
          code: 'RATE_LIMITED',
          message: `Too many login attempts. Please try again in ${rateLimitCheck.retryAfter} seconds.`,
          retryAfter: rateLimitCheck.retryAfter,
        } as LoginError;
      }

      // Security checks
      const securityCheck = await securityService.validateLoginAttempt({
        ...credentials,
        portalType: portalVariant!,
        ipAddress: await securityService.getClientIP(),
        userAgent: navigator.userAgent,
      });

      if (!securityCheck.allowed) {
        throw {
          code: securityCheck.reason,
          message: securityCheck.message,
        } as LoginError;
      }

      // Perform login
      const response = await authApi.login(credentials);

      // Store tokens and session
      if (response.data?.tokens) {
        await tokenManager.setTokens({
          accessToken: response.data.tokens.accessToken,
          refreshToken: response.data.tokens.refreshToken,
          expiresAt: response.data.tokens.expiresAt,
        });
      }

      if (response.data?.session) {
        await sessionManager.setCurrentSession(response.data.session as any);
      }

      // Record successful login
      await rateLimiter.recordAttempt('login', true);
      await securityService.recordEvent({
        type: 'login_success',
        userId: response.data?.user?.id || 'unknown',
        portalType: credentials.portalType!,
        ipAddress: await securityService.getClientIP(),
        userAgent: navigator.userAgent,
        metadata: {
          loginMethod: credentials.email ? 'email' :
                     credentials.portalId ? 'portal_id' :
                     credentials.accountNumber ? 'account_number' :
                     credentials.partnerCode ? 'partner_code' : 'unknown'
        },
        success: true,
        timestamp: new Date(),
      });

      return response.data || {} as any;
    },
    onError: async (error: LoginError, variables) => {
      // Record failed login
      await rateLimiter.recordAttempt('login', false);
      await securityService.recordEvent({
        type: 'login_failure',
        portalType: variables.portalType!,
        ipAddress: await securityService.getClientIP(),
        userAgent: navigator.userAgent,
        metadata: {
          errorCode: error.code,
          loginMethod: variables.email ? 'email' : 'other',
        },
        success: false,
        errorCode: error.code,
        timestamp: new Date(),
      });

      setError(error);
    },
    onSuccess: () => {
      // Invalidate and refetch auth-related queries
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: async () => {
      try {
        await authApi.logout();
      } catch (error) {
        // Continue with logout even if API call fails
        console.warn('Logout API call failed:', error);
      }

      // Clear local data
      await tokenManager.clearTokens();
      await sessionManager.clearSession();

      // Record logout event
      if (user) {
        await securityService.recordEvent({
          type: 'logout',
          userId: user.id,
          portalType: portalVariant!,
          ipAddress: await securityService.getClientIP(),
          userAgent: navigator.userAgent,
          success: true,
          timestamp: new Date(),
        });
      }
    },
    onSuccess: () => {
      // Clear all cached data
      queryClient.clear();
      setError(null);
    },
  });

  // Token refresh mutation
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const refreshToken = await tokenManager.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await authApi.refreshToken(refreshToken);

      await tokenManager.setTokens({
        accessToken: response.data.tokens.accessToken,
        refreshToken: response.data.tokens.refreshToken,
        expiresAt: response.data.tokens.expiresAt,
      });

      return response.data;
    },
    onError: async () => {
      // Refresh failed, clear tokens and redirect to login
      await tokenManager.clearTokens();
      await sessionManager.clearSession();
      queryClient.clear();
    },
  });

  // Auto token refresh
  useEffect(() => {
    if (!isAuthenticated) return;

    const cleanup = tokenManager.setupAutoRefresh(async () => {
      try {
        await refreshMutation.mutateAsync();
      } catch (error) {
        console.error('Auto refresh failed:', error);
      }
    });

    return cleanup;
  }, [isAuthenticated, refreshMutation]);

  // Action implementations
  const login = useCallback(
    async (credentials: LoginCredentials): Promise<LoginResponse> => {
      setIsLoading(true);
      try {
        const response = await loginMutation.mutateAsync(credentials);
        return response;
      } finally {
        setIsLoading(false);
      }
    },
    [loginMutation]
  );

  const logout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      await logoutMutation.mutateAsync();
    } finally {
      setIsLoading(false);
    }
  }, [logoutMutation]);

  const refreshToken = useCallback(async (): Promise<void> => {
    await refreshMutation.mutateAsync();
  }, [refreshMutation]);

  const updateUser = useCallback(
    async (updates: Partial<User>): Promise<User> => {
      const response = await authApi.updateProfile(updates);

      // Update cached user data
      queryClient.setQueryData(['auth', 'user'], response.data);

      return response.data;
    },
    [queryClient]
  );

  const changePassword = useCallback(
    async (request: PasswordChangeRequest): Promise<void> => {
      await authApi.changePassword(request);

      // Record password change event
      if (user) {
        await securityService.recordEvent({
          type: 'password_change',
          userId: user.id,
          portalType: portalVariant!,
          ipAddress: await securityService.getClientIP(),
          userAgent: navigator.userAgent,
          success: true,
          timestamp: new Date(),
        });
      }
    },
    [user, portalVariant]
  );

  const resetPassword = useCallback(
    async (request: PasswordResetRequest): Promise<void> => {
      await authApi.resetPassword(request);

      // Record password reset event
      await securityService.recordEvent({
        type: 'password_reset',
        portalType: portalVariant!,
        ipAddress: await securityService.getClientIP(),
        userAgent: navigator.userAgent,
        metadata: {
          email: request.email,
          portalId: request.portalId,
          accountNumber: request.accountNumber,
        },
        success: true,
        timestamp: new Date(),
      });
    },
    [portalVariant]
  );

  const setupMfa = useCallback(
    async (type: 'totp' | 'sms' | 'email'): Promise<MfaSetup> => {
      const response = await authApi.setupMfa(type);

      // Record MFA setup event
      if (user) {
        await securityService.recordEvent({
          type: 'mfa_setup',
          userId: user.id,
          portalType: portalVariant!,
          ipAddress: await securityService.getClientIP(),
          userAgent: navigator.userAgent,
          metadata: { mfaType: type },
          success: true,
          timestamp: new Date(),
        });
      }

      return response.data;
    },
    [user, portalVariant]
  );

  const verifyMfa = useCallback(
    async (verification: MfaVerification): Promise<boolean> => {
      const response = await authApi.verifyMfa(verification);

      // Record MFA verification event
      if (user) {
        await securityService.recordEvent({
          type: 'mfa_verification',
          userId: user.id,
          portalType: portalVariant!,
          ipAddress: await securityService.getClientIP(),
          userAgent: navigator.userAgent,
          metadata: {
            method: verification.method,
            success: response.data.verified,
          },
          success: response.data.verified,
          timestamp: new Date(),
        });
      }

      return response.data.verified;
    },
    [user, portalVariant]
  );

  const getSessions = useCallback(async (): Promise<Session[]> => {
    const response = await authApi.getSessions();
    return response.data;
  }, []);

  const terminateSession = useCallback(
    async (sessionId: string): Promise<void> => {
      await authApi.terminateSession(sessionId);

      // Invalidate session cache
      queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] });

      // Record session termination
      if (user) {
        await securityService.recordEvent({
          type: 'session_terminated',
          userId: user.id,
          sessionId,
          portalType: portalVariant!,
          ipAddress: await securityService.getClientIP(),
          userAgent: navigator.userAgent,
          success: true,
          timestamp: new Date(),
        });
      }
    },
    [queryClient, user, portalVariant]
  );

  const terminateAllSessions = useCallback(async (): Promise<void> => {
    await authApi.terminateAllSessions();

    // Clear current session and redirect to login
    await tokenManager.clearTokens();
    await sessionManager.clearSession();
    queryClient.clear();
  }, [queryClient]);

  // Permission helpers
  const hasPermission = useCallback(
    (permission: string): boolean => {
      return permissions.includes(permission);
    },
    [permissions]
  );

  const hasRole = useCallback(
    (roleOrRoles: string | string[]): boolean => {
      if (!role) return false;

      if (Array.isArray(roleOrRoles)) {
        return roleOrRoles.includes(role);
      }

      return role === roleOrRoles;
    },
    [role]
  );

  const hasAnyRole = useCallback(
    (roles: string[]): boolean => {
      return role ? roles.includes(role) : false;
    },
    [role]
  );

  // Portal helpers
  const getPortalConfig = useCallback((): PortalConfig | null => {
    return portalConfig;
  }, [portalConfig]);

  const getLoginMethods = useCallback((): string[] => {
    return portalConfig?.loginMethods || [];
  }, [portalConfig]);

  const isMfaRequired = useCallback((): boolean => {
    return portalConfig?.features.mfaRequired || false;
  }, [portalConfig]);

  const canAccessPortal = useCallback(
    (portalType: PortalVariant): boolean => {
      return user?.portalAccess?.includes(portalType) || false;
    },
    [user]
  );

  // Validation helpers
  const validateCredentials = useCallback(
    (credentials: LoginCredentials): ValidationResult => {
      if (!portalVariant) {
        return { isValid: false, errors: ['Portal variant not specified'] };
      }

      const result = validateLoginCredentials(credentials, portalVariant);
      return {
        isValid: result.success,
        errors: result.success ? [] : Object.values(result.errors).flat(),
      };
    },
    [portalVariant]
  );

  const validatePassword = useCallback(
    (password: string): ValidationResult => {
      if (!portalVariant) {
        return { isValid: false, errors: ['Portal variant not specified'] };
      }

      const result = validatePasswordStrength(password, portalVariant);
      return {
        isValid: result.isValid,
        errors: result.feedback,
      };
    },
    [portalVariant]
  );

  // Rate limiting
  const getRateLimitStatus = useCallback(async (): Promise<RateLimitStatus | null> => {
    return rateLimiter.getStatus('login');
  }, []);

  // Security
  const getSecurityEvents = useCallback(async (): Promise<AuthEvent[]> => {
    if (!user) return [];
    return securityService.getUserEvents(user.id);
  }, [user]);

  const reportSuspiciousActivity = useCallback(
    async (details: Record<string, any>): Promise<void> => {
      await securityService.recordEvent({
        type: 'suspicious_activity',
        userId: user?.id,
        portalType: portalVariant!,
        ipAddress: await securityService.getClientIP(),
        userAgent: navigator.userAgent,
        metadata: details,
        success: false,
        timestamp: new Date(),
      });
    },
    [user, portalVariant]
  );

  // Combined state
  const authState: AuthState = {
    user: user || null,
    isAuthenticated,
    isLoading: isLoading || isUserLoading || loginMutation.isPending || logoutMutation.isPending,
    error,
    portal: portalConfig,
    session: session || null,
    permissions,
    role,
  };

  return {
    ...authState,
    // Actions
    login,
    logout,
    refreshToken,
    updateUser,
    changePassword,
    resetPassword,
    setupMfa,
    verifyMfa,
    getSessions,
    terminateSession,
    terminateAllSessions,

    // Permission helpers
    hasPermission,
    hasRole,
    hasAnyRole,

    // Portal helpers
    getPortalConfig,
    getLoginMethods,
    isMfaRequired,
    canAccessPortal,

    // Validation helpers
    validateCredentials,
    validatePassword,

    // Rate limiting
    getRateLimitStatus,

    // Security
    getSecurityEvents,
    reportSuspiciousActivity,
  };
}
