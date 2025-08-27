'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, authApi } from '@/lib/api';
import { secureAuth } from '@/lib/auth-security';
import { securityMonitor, SecurityEventType } from '@/lib/security-monitor';
import { rateLimiter } from '@/lib/rate-limiting';
import { AuthContextType, User, LoginCredentials, Permission, UserRole } from '@/types/auth';

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const accessToken = await secureAuth.getAccessToken();
      if (accessToken) {
        apiClient.setAccessToken(accessToken);
        const userData = await authApi.me();
        setUser(userData);
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      await secureAuth.clearTokens();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (credentials: LoginCredentials) => {
    try {
      setIsLoading(true);
      
      // Check rate limiting for login attempts
      if (rateLimiter.isRateLimited('login')) {
        const timeUntilReset = rateLimiter.getTimeUntilReset('login');
        const remainingTime = Math.ceil(timeUntilReset / 1000 / 60); // Convert to minutes
        
        securityMonitor.logSuspicious({
          action: 'rate_limited_login_attempt',
          username: credentials.username || credentials.email,
          timeUntilReset: remainingTime,
          timestamp: new Date().toISOString(),
        });
        
        throw new Error(`Too many login attempts. Please try again in ${remainingTime} minutes.`);
      }
      
      // Record login attempt for rate limiting
      rateLimiter.recordAttempt('login');
      
      // Log login attempt
      securityMonitor.logAuth(SecurityEventType.LOGIN_ATTEMPT, false, {
        username: credentials.username || credentials.email,
        timestamp: new Date().toISOString(),
      });
      
      const response = await authApi.login(credentials);
      
      const { user: userData, access_token, refresh_token, expires_at } = response;
      
      // Store tokens securely in httpOnly cookies
      await secureAuth.setTokens({
        accessToken: access_token,
        refreshToken: refresh_token,
        expiresAt: expires_at,
      });
      
      // Set API client token
      apiClient.setAccessToken(access_token);
      
      // Update user state
      setUser(userData);
      
      // Log successful login
      securityMonitor.logAuth(SecurityEventType.LOGIN_SUCCESS, true, {
        userId: userData.id,
        tenantId: userData.tenantId,
        role: userData.role,
        timestamp: new Date().toISOString(),
      });
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      
      // Log failed login attempt
      securityMonitor.logAuth(SecurityEventType.LOGIN_FAILURE, false, {
        username: credentials.username || credentials.email,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      });
      
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      // Log logout attempt
      securityMonitor.logAuth(SecurityEventType.LOGOUT, true, {
        userId: user?.id,
        tenantId: user?.tenantId,
        timestamp: new Date().toISOString(),
      });
      
      await authApi.logout();
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      // Clear local state regardless of API call result
      setUser(null);
      await secureAuth.clearTokens();
      apiClient.setAccessToken(null);
      router.push('/login');
    }
  };

  const refreshToken = async () => {
    try {
      const newAccessToken = await secureAuth.refreshAccessToken();
      if (!newAccessToken) {
        throw new Error('Failed to refresh access token');
      }

      apiClient.setAccessToken(newAccessToken);
      
      // Log successful token refresh
      securityMonitor.logAuth(SecurityEventType.TOKEN_REFRESH, true, {
        userId: user?.id,
        tenantId: user?.tenantId,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Token refresh failed:', error);
      
      // Log failed token refresh
      securityMonitor.logAuth(SecurityEventType.TOKEN_REFRESH, false, {
        userId: user?.id,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      });
      
      logout();
      throw error;
    }
  };

  const hasPermission = (permission: Permission | Permission[]): boolean => {
    if (!user) return false;
    
    const permissions = Array.isArray(permission) ? permission : [permission];
    
    // Master admins have all permissions
    if (user.role === UserRole.MASTER_ADMIN) {
      return true;
    }
    
    // Check if user has any of the required permissions
    return permissions.some(p => user.permissions.includes(p));
  };

  const isMasterAdmin = (): boolean => {
    return user?.role === UserRole.MASTER_ADMIN;
  };

  const isAuthenticated = !!user;

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshToken,
    hasPermission,
    isMasterAdmin,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Note: Token storage now handled securely via httpOnly cookies
// No client-side token storage functions needed