'use client';

import React, {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { secureTokenManager } from '../../lib/auth/secureTokenManager';
import { sessionManager } from '../../lib/auth/sessionManager';
import { SessionWarningDialog } from './SessionWarningDialog';

interface User {
  id: string;
  name: string;
  email: string;
  accountNumber: string;
  portalType: 'customer';
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { email: string; password: string; portalId?: string }) => Promise<{
    success: boolean;
    error?: string;
  }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

interface SecureAuthProviderProps {
  children: ReactNode;
}

export function SecureAuthProvider({ children }: SecureAuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showSessionWarning, setShowSessionWarning] = useState(false);
  const [sessionTimeLeft, setSessionTimeLeft] = useState(0);

  const refreshUser = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await secureTokenManager.getCurrentUser();

      if (response.success && response.user) {
        setUser(response.user);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('[SecureAuthProvider] Failed to refresh user:', error);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(
    async (credentials: { email: string; password: string; portalId?: string }) => {
      try {
        setIsLoading(true);
        const response = await secureTokenManager.login(credentials);

        if (response.success && response.user) {
          setUser(response.user);
          setIsAuthenticated(true);
          return { success: true };
        } else {
          setUser(null);
          setIsAuthenticated(false);
          return {
            success: false,
            error: response.error || 'Login failed',
          };
        }
      } catch (error) {
        console.error('[SecureAuthProvider] Login error:', error);
        setUser(null);
        setIsAuthenticated(false);
        return {
          success: false,
          error: 'Network error during login',
        };
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      setIsLoading(true);
      await secureTokenManager.logout();
      setUser(null);
      setIsAuthenticated(false);
    } catch (error) {
      console.error('[SecureAuthProvider] Logout error:', error);
      // Clear state even if logout fails
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Session management handlers
  const handleSessionWarning = useCallback((timeLeft: number) => {
    setSessionTimeLeft(timeLeft);
    setShowSessionWarning(true);
  }, []);

  const handleSessionTimeout = useCallback(async () => {
    setShowSessionWarning(false);
    console.warn('[SecureAuthProvider] Session expired due to inactivity');
    await logout();
  }, [logout]);

  const handleExtendSession = useCallback(() => {
    sessionManager.extendSession();
    setShowSessionWarning(false);
  }, []);

  const handleLogoutNow = useCallback(async () => {
    setShowSessionWarning(false);
    await logout();
  }, [logout]);

  // Initialize authentication state on mount
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Set up token refresh interval
  useEffect(() => {
    if (!isAuthenticated) return;

    // Refresh token every 14 minutes (assuming 15-minute expiry)
    const refreshInterval = setInterval(
      async () => {
        try {
          const response = await secureTokenManager.refreshToken();
          if (!response.success) {
            console.warn('[SecureAuthProvider] Token refresh failed, user may need to re-login');
            await refreshUser();
          }
        } catch (error) {
          console.error('[SecureAuthProvider] Token refresh error:', error);
          await refreshUser();
        }
      },
      14 * 60 * 1000
    ); // 14 minutes

    return () => clearInterval(refreshInterval);
  }, [isAuthenticated, refreshUser]);

  // Handle page visibility change - refresh user when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isAuthenticated) {
        refreshUser();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [isAuthenticated, refreshUser]);

  // Set up session management
  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const unsubscribe = sessionManager.addListener({
      onWarning: handleSessionWarning,
      onTimeout: handleSessionTimeout,
      onActivity: () => {
        // User became active after being idle, refresh user state
        refreshUser();
      },
    });

    return unsubscribe;
  }, [isAuthenticated, handleSessionWarning, handleSessionTimeout, refreshUser]);

  const contextValue: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
      <SessionWarningDialog
        isOpen={showSessionWarning}
        timeLeft={sessionTimeLeft}
        onExtend={handleExtendSession}
        onLogout={handleLogoutNow}
      />
    </AuthContext.Provider>
  );
}

export function useSecureAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useSecureAuth must be used within a SecureAuthProvider');
  }

  return context;
}

// Hook for checking authentication status
export function useAuthenticationStatus() {
  const { isAuthenticated, isLoading, user } = useSecureAuth();

  return {
    isAuthenticated,
    isLoading,
    user,
    hasValidSession: isAuthenticated && user !== null,
  };
}

// Hook for authentication actions
export function useAuthActions() {
  const { login, logout, refreshUser } = useSecureAuth();

  return {
    login,
    logout,
    refreshUser,
  };
}
