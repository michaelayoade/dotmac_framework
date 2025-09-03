'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo,
  useCallback,
  useRef,
} from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { SecureAuthService } from '@/lib/secure-auth-service';
import { loginCredentialsSchema } from '@/lib/validation-schemas';
import { sanitizeEmail } from '@/lib/sanitization';
import { withAuthPerformanceTracking, logAuthStateChange } from '@/lib/auth-performance';

interface TenantUser {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
  permissions: string[];
  last_login?: Date;
}

interface TenantInfo {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  status: 'active' | 'pending' | 'suspended' | 'cancelled';
  tier: string;
  custom_domain?: string;
  primary_color?: string;
  logo_url?: string;
}

interface TenantAuthContextValue {
  user: TenantUser | null;
  tenant: TenantInfo | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { email: string; password: string; rememberMe?: boolean }) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<boolean>;
}

const TenantAuthContext = createContext<TenantAuthContextValue | null>(null);

export function useTenantAuth() {
  const context = useContext(TenantAuthContext);
  if (!context) {
    throw new Error('useTenantAuth must be used within a TenantAuthProvider');
  }
  return context;
}

export function TenantAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<TenantUser | null>(null);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Performance monitoring refs
  const renderCount = useRef(0);
  const lastAuthCheck = useRef<number>(0);

  // Track renders for debugging
  renderCount.current += 1;

  // Memoized authentication state
  const isAuthenticated = useMemo(
    () => !!user && !!tenant && tenant.status === 'active',
    [user, tenant]
  );

  // Track auth state changes for performance monitoring
  const previousState = useRef({ user, tenant, isAuthenticated });

  // Log auth state changes in development
  useEffect(() => {
    const prevState = previousState.current;
    const newState = { user, tenant, isAuthenticated };

    logAuthStateChange(prevState, newState);
    previousState.current = newState;
  }, [user, tenant, isAuthenticated]);

  // Memoized login function with performance tracking
  const login = useCallback(
    withAuthPerformanceTracking(
      'login',
      async (credentials: { email: string; password: string; rememberMe?: boolean }) => {
        setIsLoading(true);
        try {
          // Validate and sanitize input
          const validatedCredentials = loginCredentialsSchema.parse({
            email: sanitizeEmail(credentials.email),
            password: credentials.password, // Password not sanitized to preserve special characters
            rememberMe: credentials.rememberMe || false,
          });

          // Use secure authentication service
          const authResult = await SecureAuthService.login(validatedCredentials);

          if (!authResult.success) {
            throw new Error(authResult.error || 'Authentication failed');
          }

          if (authResult.requiresMFA) {
            // TODO: Handle MFA flow
            throw new Error('Multi-factor authentication required');
          }

          if (authResult.user && authResult.tenant) {
            setUser(authResult.user);
            setTenant(authResult.tenant);

            // Redirect to dashboard
            router.push('/dashboard');
          } else {
            throw new Error('Invalid authentication response');
          }
        } catch (error) {
          console.error('Login failed:', error);
          throw new Error(error instanceof Error ? error.message : 'Invalid credentials');
        } finally {
          setIsLoading(false);
        }
      }
    ),
    [router]
  );

  // Memoized logout function with performance tracking
  const logout = useCallback(
    withAuthPerformanceTracking('logout', async () => {
      try {
        // Use secure authentication service
        await SecureAuthService.logout();

        setUser(null);
        setTenant(null);

        router.push('/login');
      } catch (error) {
        console.error('Logout failed:', error);
        // Even if logout fails, clear local state and redirect
        setUser(null);
        setTenant(null);
        router.push('/login');
      }
    }),
    [router]
  );

  // Memoized refresh auth function with performance tracking
  const refreshAuth = useCallback(
    withAuthPerformanceTracking('refreshAuth', async () => {
      try {
        // Use secure authentication service
        const refreshResult = await SecureAuthService.refreshAuth();

        if (refreshResult.success && refreshResult.user && refreshResult.tenant) {
          setUser(refreshResult.user);
          setTenant(refreshResult.tenant);
          return true;
        } else {
          // Refresh failed, logout user
          await logout();
          return false;
        }
      } catch (error) {
        console.error('Auth refresh failed:', error);
        await logout();
        return false;
      }
    }),
    [logout]
  );

  // Optimized authentication check with debouncing and caching
  useEffect(() => {
    const checkAuth = async () => {
      const now = Date.now();
      const AUTH_CHECK_DEBOUNCE = 1000; // 1 second debounce

      // Debounce auth checks to prevent excessive API calls
      if (now - lastAuthCheck.current < AUTH_CHECK_DEBOUNCE) {
        return;
      }

      lastAuthCheck.current = now;
      setIsLoading(true);

      try {
        // Performance monitoring
        const startTime = performance.now();

        // Check if user is authenticated using secure service
        const isAuth = await SecureAuthService.isAuthenticated();

        if (isAuth) {
          // Only fetch user data if we don't have it or it's stale
          if (!user || !tenant) {
            const { user: currentUser, tenant: currentTenant } =
              await SecureAuthService.getCurrentUser();

            if (currentUser && currentTenant) {
              setUser(currentUser);
              setTenant(currentTenant);
            } else {
              throw new Error('Failed to get user data');
            }
          }
        } else if (pathname !== '/login' && !pathname.startsWith('/auth')) {
          // Clear stale data and redirect
          setUser(null);
          setTenant(null);
          router.push('/login');
        }

        // Performance monitoring
        const endTime = performance.now();
        if (process.env.NODE_ENV === 'development') {
          console.log(
            `Auth check completed in ${endTime - startTime}ms (render #${renderCount.current})`
          );
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        if (pathname !== '/login' && !pathname.startsWith('/auth')) {
          setUser(null);
          setTenant(null);
          router.push('/login');
        }
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [pathname, router, user, tenant]);

  // Memoized context value to prevent unnecessary re-renders of consumers
  const value = useMemo<TenantAuthContextValue>(
    () => ({
      user,
      tenant,
      isLoading,
      isAuthenticated,
      login,
      logout,
      refreshAuth,
    }),
    [user, tenant, isLoading, isAuthenticated, login, logout, refreshAuth]
  );

  return <TenantAuthContext.Provider value={value}>{children}</TenantAuthContext.Provider>;
}
