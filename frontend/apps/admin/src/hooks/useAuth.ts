/**
 * React Hooks for Cross-Platform Authentication
 * Provides React integration for the authentication bridge
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { authBridge, AuthState, AuthUser, LoginCredentials } from '../lib/auth-bridge';
import { monitoring } from '../lib/monitoring';

// Hook for authentication state
export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>(authBridge.getState());

  useEffect(() => {
    // Listen for auth state changes
    const handleStateChange = (newState: AuthState) => {
      setAuthState(newState);
    };

    authBridge.on('state_changed', handleStateChange);

    // Initial validation on mount
    if (authState.isAuthenticated) {
      authBridge.validateSession().catch(() => {
        // Session validation will handle logout if needed
      });
    }

    return () => {
      authBridge.off('state_changed', handleStateChange);
    };
  }, [authState.isAuthenticated]);

  const login = useCallback(async (credentials: LoginCredentials): Promise<AuthUser> => {
    monitoring.recordInteraction({
      event: 'auth_login_attempt',
      target: 'auth_system',
      metadata: { 
        portalType: credentials.portalType,
        hasPortalId: !!credentials.portalId,
      },
    });

    try {
      const user = await authBridge.login(credentials);
      
      monitoring.recordBusinessMetric({
        metric: 'auth_login_success',
        value: 1,
        dimensions: {
          portal_type: user.portalType || 'unknown',
          user_role: user.role,
        },
      });

      return user;
    } catch (error) {
      monitoring.recordBusinessMetric({
        metric: 'auth_login_failure',
        value: 1,
        dimensions: {
          portal_type: credentials.portalType || 'unknown',
          error_type: error instanceof Error ? error.constructor.name : 'unknown',
        },
      });

      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'auth_login',
        metadata: { credentials: { ...credentials, password: '[REDACTED]' } },
      });

      throw error;
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    monitoring.recordInteraction({
      event: 'auth_logout',
      target: 'auth_system',
    });

    try {
      await authBridge.logout();
      
      monitoring.recordBusinessMetric({
        metric: 'auth_logout_success',
        value: 1,
      });
    } catch (error) {
      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'auth_logout',
      });
      
      // Continue with logout even if server notification fails
    }
  }, []);

  const updateProfile = useCallback(async (updates: Partial<AuthUser>): Promise<AuthUser> => {
    monitoring.recordInteraction({
      event: 'auth_profile_update',
      target: 'auth_system',
    });

    try {
      const user = await authBridge.updateProfile(updates);
      
      monitoring.recordBusinessMetric({
        metric: 'auth_profile_update_success',
        value: 1,
      });

      return user;
    } catch (error) {
      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'auth_profile_update',
        metadata: { updates },
      });

      throw error;
    }
  }, []);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      const result = await authBridge.refreshToken();
      
      monitoring.recordBusinessMetric({
        metric: 'auth_token_refresh',
        value: 1,
        dimensions: {
          success: result.toString(),
        },
      });

      return result;
    } catch (error) {
      monitoring.recordError({
        error: error instanceof Error ? error : new Error(String(error)),
        context: 'auth_token_refresh',
      });

      return false;
    }
  }, []);

  // Memoized computed values
  const authHeader = useMemo(() => {
    return authBridge.getAuthHeader();
  }, [authState.tokens]);

  const hasPermission = useCallback((permission: string): boolean => {
    return authState.user?.permissions.includes(permission) || false;
  }, [authState.user?.permissions]);

  const hasAnyPermission = useCallback((permissions: string[]): boolean => {
    if (!authState.user?.permissions) return false;
    return permissions.some(permission => authState.user!.permissions.includes(permission));
  }, [authState.user?.permissions]);

  const hasRole = useCallback((role: string): boolean => {
    return authState.user?.role === role;
  }, [authState.user?.role]);

  const hasAnyRole = useCallback((roles: string[]): boolean => {
    return authState.user ? roles.includes(authState.user.role) : false;
  }, [authState.user?.role]);

  return {
    // State
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    error: authState.error,
    
    // Actions
    login,
    logout,
    updateProfile,
    refreshToken,
    
    // Utilities
    authHeader,
    hasPermission,
    hasAnyPermission,
    hasRole,
    hasAnyRole,
  };
}

// Hook for authentication events
export function useAuthEvents() {
  const [events, setEvents] = useState<Array<{ type: string; data: any; timestamp: number }>>([]);

  useEffect(() => {
    const eventTypes = ['login', 'logout', 'token_refreshed', 'profile_updated', 'error'];
    
    const handleEvent = (type: string) => (data: any) => {
      setEvents(prev => [{
        type,
        data,
        timestamp: Date.now(),
      }, ...prev.slice(0, 49)]); // Keep last 50 events
    };

    // Register event listeners
    const handlers = eventTypes.map(type => {
      const handler = handleEvent(type);
      authBridge.on(type, handler);
      return { type, handler };
    });

    return () => {
      // Cleanup event listeners
      handlers.forEach(({ type, handler }) => {
        authBridge.off(type, handler);
      });
    };
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    events,
    clearEvents,
  };
}

// Hook for protecting components based on permissions
export function useAuthGuard(
  requiredPermissions?: string[],
  requiredRoles?: string[],
  fallback?: React.ComponentType
) {
  const { user, isAuthenticated, hasAnyPermission, hasAnyRole } = useAuth();

  const isAuthorized = useMemo(() => {
    if (!isAuthenticated || !user) {
      return false;
    }

    if (requiredPermissions && !hasAnyPermission(requiredPermissions)) {
      return false;
    }

    if (requiredRoles && !hasAnyRole(requiredRoles)) {
      return false;
    }

    return true;
  }, [isAuthenticated, user, requiredPermissions, requiredRoles, hasAnyPermission, hasAnyRole]);

  return {
    isAuthorized,
    isAuthenticated,
    user,
    fallback,
  };
}

// Hook for session monitoring
export function useSessionMonitor(options: {
  warningThreshold?: number; // minutes before expiry to show warning
  onSessionWarning?: () => void;
  onSessionExpired?: () => void;
} = {}) {
  const { user, isAuthenticated } = useAuth();
  const [sessionStatus, setSessionStatus] = useState<{
    isExpiring: boolean;
    timeUntilExpiry: number | null;
    warningShown: boolean;
  }>({
    isExpiring: false,
    timeUntilExpiry: null,
    warningShown: false,
  });

  const warningThreshold = options.warningThreshold || 5; // 5 minutes default

  useEffect(() => {
    if (!isAuthenticated) {
      setSessionStatus({
        isExpiring: false,
        timeUntilExpiry: null,
        warningShown: false,
      });
      return;
    }

    const checkSession = () => {
      const authState = authBridge.getState();
      if (!authState.tokens) return;

      const now = Date.now();
      const expiresAt = authState.tokens.expiresAt;
      const timeUntilExpiry = Math.max(0, expiresAt - now);
      const minutesUntilExpiry = timeUntilExpiry / (1000 * 60);

      const isExpiring = minutesUntilExpiry <= warningThreshold;

      setSessionStatus(prev => {
        const newStatus = {
          isExpiring,
          timeUntilExpiry,
          warningShown: prev.warningShown || isExpiring,
        };

        // Trigger callbacks
        if (isExpiring && !prev.warningShown && options.onSessionWarning) {
          options.onSessionWarning();
        }

        if (timeUntilExpiry <= 0 && options.onSessionExpired) {
          options.onSessionExpired();
        }

        return newStatus;
      });
    };

    checkSession();
    const interval = setInterval(checkSession, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [isAuthenticated, warningThreshold, options.onSessionWarning, options.onSessionExpired]);

  const extendSession = useCallback(async (): Promise<boolean> => {
    try {
      const success = await authBridge.refreshToken();
      
      if (success) {
        setSessionStatus(prev => ({
          ...prev,
          warningShown: false,
        }));
      }

      return success;
    } catch (error) {
      return false;
    }
  }, []);

  return {
    ...sessionStatus,
    extendSession,
  };
}