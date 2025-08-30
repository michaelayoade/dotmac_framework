/**
 * Universal Authentication Provider
 *
 * Provides authentication context and state management across all portals
 * Handles portal-aware authentication, session management, and security features
 */

'use client';

import React, {
  createContext,
  useContext,
  useEffect,
  useReducer,
  useCallback,
  useMemo
} from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import type {
  AuthProviderProps,
  AuthContextValue,
  User,
  PortalVariant,
  PortalConfig,
  LoginError,
  Session,
} from '../types';

import { useAuth } from '../hooks/useAuth';
import { getPortalConfig, generatePortalCSS } from '../config/portal-configs';
import { TokenManager } from '../services/TokenManager';
import { SessionManager } from '../services/SessionManager';

// Create contexts
const AuthContext = createContext<AuthContextValue | null>(null);
const PortalContext = createContext<{
  config: PortalConfig;
  variant: PortalVariant;
} | null>(null);

// Auth state reducer
type AuthAction =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: LoginError | null }
  | { type: 'SET_SESSION'; payload: Session | null }
  | { type: 'CLEAR_AUTH' };

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: LoginError | null;
  session: Session | null;
}

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload, error: null };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_SESSION':
      return { ...state, session: action.payload };
    case 'CLEAR_AUTH':
      return {
        user: null,
        isLoading: false,
        error: null,
        session: null,
      };
    default:
      return state;
  }
}

// Query client singleton
let queryClient: QueryClient;
const getQueryClient = () => {
  if (!queryClient) {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 5 * 60 * 1000, // 5 minutes
          gcTime: 10 * 60 * 1000, // 10 minutes
          retry: (failureCount, error) => {
            // Don't retry on auth errors
            if (String(error).includes('401') || String(error).includes('403')) {
              return false;
            }
            return failureCount < 2;
          },
        },
        mutations: {
          retry: false,
        },
      },
    });
  }
  return queryClient;
};

// Token and session managers
const tokenManager = new TokenManager();
const sessionManager = new SessionManager();

/**
 * Inner Auth Provider Component
 * Contains the actual authentication logic
 */
function InnerAuthProvider({
  children,
  portalVariant,
  config: customConfig,
  onAuthStateChange,
  onError
}: AuthProviderProps) {
  // Portal configuration
  const portalConfig = useMemo(() => ({
    ...getPortalConfig(portalVariant),
    ...customConfig,
  }), [portalVariant, customConfig]);

  // Auth state
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    isLoading: true,
    error: null,
    session: null,
  });

  // Use auth hook with portal variant
  const auth = useAuth(portalVariant);

  // Sync auth hook state with local state
  useEffect(() => {
    dispatch({ type: 'SET_USER', payload: auth.user });
    dispatch({ type: 'SET_LOADING', payload: auth.isLoading });
    dispatch({ type: 'SET_ERROR', payload: auth.error });
    dispatch({ type: 'SET_SESSION', payload: auth.session });
  }, [auth.user, auth.isLoading, auth.error, auth.session]);

  // Apply portal theming
  useEffect(() => {
    const css = generatePortalCSS(portalVariant);
    const styleElement = document.createElement('style');
    styleElement.id = 'dotmac-auth-theme';
    styleElement.textContent = css;

    // Remove existing theme
    const existingStyle = document.getElementById('dotmac-auth-theme');
    if (existingStyle) {
      existingStyle.remove();
    }

    document.head.appendChild(styleElement);

    // Set page title if configured
    if (portalConfig.branding.companyName) {
      document.title = portalConfig.name;
    }

    // Set favicon if configured
    if (portalConfig.branding.favicon) {
      const favicon = document.querySelector('link[rel="icon"]') as HTMLLinkElement;
      if (favicon) {
        favicon.href = portalConfig.branding.favicon;
      }
    }

    // Cleanup on unmount
    return () => {
      const styleToRemove = document.getElementById('dotmac-auth-theme');
      if (styleToRemove) {
        styleToRemove.remove();
      }
    };
  }, [portalVariant, portalConfig]);

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      dispatch({ type: 'SET_LOADING', payload: true });

      try {
        // Check if we have stored tokens
        if (await tokenManager.hasValidTokens()) {
          // Try to restore user session
          const storedSession = await sessionManager.getCurrentSession();
          if (storedSession && !sessionManager.isSessionExpired(storedSession)) {
            // Session is valid, auth hook will automatically fetch user data
            dispatch({ type: 'SET_SESSION', payload: storedSession });
          } else {
            // Session expired, clear tokens
            await tokenManager.clearTokens();
            await sessionManager.clearSession();
          }
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        dispatch({ type: 'SET_ERROR', payload: {
          code: 'INIT_ERROR',
          message: 'Failed to initialize authentication',
        }});
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    initializeAuth();
  }, []);

  // Handle authentication state changes
  useEffect(() => {
    if (onAuthStateChange) {
      onAuthStateChange(state.user, !!state.user);
    }
  }, [state.user, onAuthStateChange]);

  // Handle errors
  useEffect(() => {
    if (state.error && onError) {
      onError(state.error);
    }
  }, [state.error, onError]);

  // Session timeout handling
  useEffect(() => {
    if (!state.session || !state.user) return;

    const timeoutMs = portalConfig.features.sessionTimeout * 60 * 1000; // Convert to milliseconds
    const sessionStart = new Date(state.session.createdAt).getTime();
    const timeRemaining = sessionStart + timeoutMs - Date.now();

    if (timeRemaining <= 0) {
      // Session already expired
      auth.logout();
      return;
    }

    // Set timeout for automatic logout
    const timeoutId = setTimeout(() => {
      auth.logout();
      dispatch({ type: 'SET_ERROR', payload: {
        code: 'SESSION_TIMEOUT',
        message: 'Your session has expired. Please log in again.',
      }});
    }, timeRemaining);

    // Warn user before session expires (5 minutes before)
    const warningTime = Math.max(0, timeRemaining - 5 * 60 * 1000);
    const warningTimeoutId = setTimeout(() => {
      dispatch({ type: 'SET_ERROR', payload: {
        code: 'SESSION_WARNING',
        message: 'Your session will expire in 5 minutes. Please save your work.',
      }});
    }, warningTime);

    return () => {
      clearTimeout(timeoutId);
      clearTimeout(warningTimeoutId);
    };
  }, [state.session, state.user, portalConfig.features.sessionTimeout, auth]);

  // Enhanced auth context value
  const contextValue: AuthContextValue = useMemo(() => ({
    ...auth,
    user: state.user,
    isLoading: state.isLoading,
    error: state.error,
    session: state.session,
    portal: portalConfig,
  }), [auth, state, portalConfig]);

  const portalContextValue = useMemo(() => ({
    config: portalConfig,
    variant: portalVariant,
  }), [portalConfig, portalVariant]);

  return (
    <PortalContext.Provider value={portalContextValue}>
      <AuthContext.Provider value={contextValue}>
        {children}
      </AuthContext.Provider>
    </PortalContext.Provider>
  );
}

/**
 * Main Auth Provider Component
 * Wraps the app with QueryClient and auth context
 */
export function AuthProvider(props: AuthProviderProps) {
  return (
    <QueryClientProvider client={getQueryClient()}>
      <InnerAuthProvider {...props} />
    </QueryClientProvider>
  );
}

/**
 * Hook to access authentication context
 */
export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}

/**
 * Hook to access portal context
 */
export function usePortalContext() {
  const context = useContext(PortalContext);
  if (!context) {
    throw new Error('usePortalContext must be used within an AuthProvider');
  }
  return context;
}

/**
 * Protected Route Component
 * Renders children only if user is authenticated and has required permissions
 */
export function ProtectedRoute({
  children,
  requiredPermissions = [],
  requiredRole,
  fallback = <div>Access Denied</div>,
  redirectTo,
}: {
  children: React.ReactNode;
  requiredPermissions?: string[];
  requiredRole?: string | string[];
  fallback?: React.ReactNode;
  redirectTo?: string;
}) {
  const { isAuthenticated, isLoading, hasPermission, hasRole } = useAuthContext();

  // Show loading while checking authentication
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    if (redirectTo && typeof window !== 'undefined') {
      window.location.href = redirectTo;
      return null;
    }
    return fallback;
  }

  // Check required permissions
  const hasRequiredPermissions = requiredPermissions.every(permission =>
    hasPermission(permission)
  );

  if (!hasRequiredPermissions) {
    return fallback;
  }

  // Check required role
  if (requiredRole) {
    const hasRequiredRole = Array.isArray(requiredRole)
      ? hasRole(requiredRole)
      : hasRole([requiredRole]);

    if (!hasRequiredRole) {
      return fallback;
    }
  }

  return <>{children}</>;
}

/**
 * Conditional Render Component
 * Renders children based on authentication state and permissions
 */
export function AuthGuard({
  children,
  fallback,
  requireAuth = true,
  requiredPermissions = [],
  requiredRole,
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  requireAuth?: boolean;
  requiredPermissions?: string[];
  requiredRole?: string | string[];
}) {
  const { isAuthenticated, hasPermission, hasRole } = useAuthContext();

  // Check authentication requirement
  if (requireAuth && !isAuthenticated) {
    return fallback ? <>{fallback}</> : null;
  }

  if (!requireAuth && isAuthenticated) {
    return fallback ? <>{fallback}</> : null;
  }

  // Check permissions if authenticated
  if (isAuthenticated) {
    const hasRequiredPermissions = requiredPermissions.every(permission =>
      hasPermission(permission)
    );

    if (!hasRequiredPermissions) {
      return fallback ? <>{fallback}</> : null;
    }

    if (requiredRole) {
      const hasRequiredRole = Array.isArray(requiredRole)
        ? hasRole(requiredRole)
        : hasRole([requiredRole]);

      if (!hasRequiredRole) {
        return fallback ? <>{fallback}</> : null;
      }
    }
  }

  return <>{children}</>;
}

/**
 * Portal Switcher Component
 * Allows switching between different portals (if user has access)
 */
export function PortalSwitcher({
  availablePortals,
  onPortalSwitch,
  className = '',
}: {
  availablePortals: PortalVariant[];
  onPortalSwitch: (portalVariant: PortalVariant) => void;
  className?: string;
}) {
  const { user, canAccessPortal } = useAuthContext();
  const { variant: currentPortal } = usePortalContext();

  if (!user || availablePortals.length <= 1) {
    return null;
  }

  const accessiblePortals = availablePortals.filter(portal =>
    portal !== currentPortal && canAccessPortal(portal)
  );

  if (accessiblePortals.length === 0) {
    return null;
  }

  return (
    <div className={`portal-switcher ${className}`}>
      <label className="block text-sm font-medium text-gray-700">
        Switch Portal
      </label>
      <select
        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
        onChange={(e) => onPortalSwitch(e.target.value as PortalVariant)}
        value={currentPortal}
      >
        <option value={currentPortal}>
          {getPortalConfig(currentPortal).name} (Current)
        </option>
        {accessiblePortals.map(portal => (
          <option key={portal} value={portal}>
            {getPortalConfig(portal).name}
          </option>
        ))}
      </select>
    </div>
  );
}

// Re-export the auth hook for convenience
export { useAuth } from '../hooks/useAuth';
