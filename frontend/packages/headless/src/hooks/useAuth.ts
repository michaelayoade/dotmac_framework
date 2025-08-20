/**
 * Secure authentication hook with automatic token refresh and role-based access
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';

import { getApiClient } from '../api/client';
import { useAuthRateLimit } from '../middleware/rateLimiting';
import { useAuthStore } from '../stores/authStore';
import type { User } from '../types';
import { csrfProtection } from '../utils/csrfProtection';
import { tokenManager } from '../utils/tokenManager';

export interface UseAuthOptions {
  redirectOnLogout?: string;
  autoRefresh?: boolean;
  refreshThreshold?: number; // Minutes before expiry to refresh
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  permissions: string[];
  role: string | null;
  tenantId: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface UseAuthResult extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
  isRole: (role: string) => boolean;
  updateUser: (updates: Partial<User>) => void;
}

export function useAuth(
  options: UseAuthOptions = {
    // Implementation pending
  }
): UseAuthResult {
  const { redirectOnLogout = '/login', autoRefresh = true, _refreshThreshold = 5 } = options;

  const rateLimit = useAuthRateLimit();

  const queryClient = useQueryClient();
  const apiClient = getApiClient();

  const {
    user,
    isAuthenticated,
    setAuth,
    clearAuth,
    updateUser,
    getValidToken,
    refreshTokens,
    isSessionValid,
  } = useAuthStore();

  const [isLoading, setIsLoading] = useState(false);

  // Query current user data
  const { data: userData, isLoading: isUserLoading } = useQuery({
    queryKey: ['auth', 'user'],
    queryFn: async () => {
      const validToken = await getValidToken();
      if (!validToken) {
        throw new Error('No valid authentication token');
      }

      const response = await apiClient.getCurrentUser();
      return response.data;
    },
    enabled: isAuthenticated && isSessionValid(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error) => {
      // Don't retry on auth errors
      if (error instanceof Error && error.message.includes('Unauthorized')) {
        return false;
      }
      return failureCount < 2;
    },
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      // Check rate limiting before attempting login
      const rateLimitCheck = rateLimit.checkLimit('login');
      if (!rateLimitCheck.allowed) {
        const error = new Error(
          `Too many login attempts. Please try again in ${rateLimitCheck.retryAfter} seconds.`
        );
        (error as unknown).code = 'RATE_LIMITED';
        (error as unknown).retryAfter = rateLimitCheck.retryAfter;
        throw error;
      }

      // Initialize CSRF protection before login
      await csrfProtection.initialize();

      const response = await apiClient.login({
        email: credentials.email,
        password: credentials.password,
        portal: 'admin', // This would be determined based on current portal
      });
      return response.data;
    },
    onSuccess: async (data) => {
      // Record successful login attempt
      rateLimit.recordAttempt('login', true);

      const tokenPair = {
        accessToken: data.token,
        refreshToken: data.refreshToken,
        expiresAt: Date.now() + 15 * 60 * 1000, // 15 minutes default
      };

      await setAuth(data.user, tokenPair, data.sessionId, data.csrfToken);
    },
    onError: async (error: unknown) => {
      // Record failed login attempt (unless rate limited)
      if (error.code !== 'RATE_LIMITED') {
        rateLimit.recordAttempt('login', false);
      }

      await clearAuth();
    },
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: async () => {
      try {
        await apiClient.logout();
      } catch (_error) {
        // Error handling intentionally empty
      }
    },
    onSettled: async () => {
      await clearAuth();
      queryClient.clear();

      // Redirect to login page
      if (typeof window !== 'undefined' && redirectOnLogout) {
        window.location.href = redirectOnLogout;
      }
    },
  });

  // Token refresh mutation
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const success = await refreshTokens(apiClient.refreshToken.bind(apiClient));
      if (!success) {
        throw new Error('Token refresh failed');
      }
      return success;
    },
    onError: async (_error) => {
      await clearAuth();

      if (typeof window !== 'undefined' && redirectOnLogout) {
        window.location.href = redirectOnLogout;
      }
    },
  });

  // Auto-refresh setup using token manager
  useEffect(() => {
    if (!autoRefresh || !isAuthenticated) {
      return;
    }

    // Set up automatic token refresh
    return tokenManager.setupAutoRefresh(apiClient.refreshToken.bind(apiClient), async () => {
      await clearAuth();

      if (typeof window !== 'undefined' && redirectOnLogout) {
        window.location.href = redirectOnLogout;
      }
    });
  }, [autoRefresh, isAuthenticated, apiClient, clearAuth, redirectOnLogout]);

  // Auth state is now initialized automatically by the auth store using secure storage

  // Update user data when fetched
  useEffect(() => {
    if (userData && userData.id !== user?.id) {
      updateUser(userData);
    }
  }, [userData, user?.id, updateUser]);

  // Helper functions
  const hasPermission = useCallback(
    (permission: string): boolean => {
      return user?.permissions?.includes(permission) ?? false;
    },
    [user?.permissions]
  );

  const hasRole = useCallback(
    (role: string): boolean => {
      return user?.role === role;
    },
    [user?.role]
  );

  const hasAnyRole = useCallback(
    (roles: string[]): boolean => {
      return user?.role ? roles.includes(user.role) : false;
    },
    [user?.role]
  );

  const isRole = useCallback(
    (role: string): boolean => {
      return user?.role === role;
    },
    [user?.role]
  );

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      setIsLoading(true);
      try {
        await loginMutation.mutateAsync(credentials);
      } finally {
        setIsLoading(false);
      }
    },
    [loginMutation]
  );

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await logoutMutation.mutateAsync();
    } finally {
      setIsLoading(false);
    }
  }, [logoutMutation]);

  const refreshToken = useCallback(async () => {
    await refreshMutation.mutateAsync();
  }, [refreshMutation]);

  return {
    user: userData || user,
    isAuthenticated,
    isLoading: isLoading || isUserLoading || loginMutation.isPending || logoutMutation.isPending,
    permissions: user?.permissions || [],
    role: user?.role || null,
    tenantId: user?.tenantId || null,
    login,
    logout,
    refreshToken,
    hasPermission,
    hasRole,
    hasAnyRole,
    isRole,
    updateUser,
  };
}
