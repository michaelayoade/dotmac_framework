/**
 * Comprehensive Authentication Provider
 * Manages authentication state, session management, and security features
 * Integrates with stores and provides context to the entire application
 */

import React, { ReactNode, useEffect, useCallback, createContext, useContext } from 'react';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useNotificationsStore } from '../stores/notificationsStore';
import { getApiClient } from '../api/client';
import type { User } from '../types';

// Auth context interface
interface AuthContextValue {
  // Authentication state
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Session management
  sessionId: string | null;
  sessionExpiry: Date | null;
  lastActivity: Date | null;
  
  // MFA state
  mfaRequired: boolean;
  mfaVerified: boolean;
  mfaSetupRequired: boolean;
  
  // Authentication actions
  login: (credentials: LoginCredentials) => Promise<LoginResult>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  
  // MFA actions
  setupMFA: (method: MFAMethod) => Promise<MFASetupResult>;
  verifyMFA: (code: string, method?: MFAMethod) => Promise<void>;
  disableMFA: (currentPassword: string) => Promise<void>;
  
  // Session management
  extendSession: () => void;
  checkSessionValidity: () => boolean;
  forceLogout: (reason?: string) => void;
  
  // User management
  updateProfile: (updates: Partial<UserProfile>) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  updatePreferences: (preferences: UserPreferences) => Promise<void>;
  
  // Security features
  enableDeviceTracking: () => Promise<void>;
  revokeAllSessions: () => Promise<void>;
  getActiveDevices: () => Promise<UserDevice[]>;
  revokeDevice: (deviceId: string) => Promise<void>;
  
  // Utility functions
  hasPermission: (permission: string) => boolean;
  hasRole: (role: UserRole) => boolean;
  getPortalType: () => PortalType | null;
}

// Types
interface LoginCredentials {
  email?: string;
  portalId?: string;
  password: string;
  rememberMe?: boolean;
  deviceFingerprint?: string;
}

interface LoginResult {
  success: boolean;
  user?: User;
  mfaRequired?: boolean;
  setupRequired?: boolean;
  error?: string;
}

interface MFASetupResult {
  qrCode?: string;
  backupCodes?: string[];
  secret?: string;
}

interface UserProfile {
  name: string;
  email: string;
  phone?: string;
  avatar?: string;
  timezone: string;
  language: string;
}

interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    email: boolean;
    push: boolean;
    sms: boolean;
  };
  dashboard: {
    layout: string;
    widgets: string[];
  };
  security: {
    sessionTimeout: number;
    deviceTracking: boolean;
    loginNotifications: boolean;
  };
}

interface UserDevice {
  id: string;
  name: string;
  type: 'desktop' | 'mobile' | 'tablet';
  browser: string;
  lastSeen: Date;
  location?: string;
  current: boolean;
}

type UserRole = 'admin' | 'manager' | 'technician' | 'support' | 'customer' | 'reseller';
type PortalType = 'admin' | 'customer' | 'reseller' | 'technician';
type MFAMethod = 'totp' | 'sms' | 'email';

// Props interface
interface AuthProviderProps {
  children: ReactNode;
  enableDeviceTracking?: boolean;
  enableSessionExtension?: boolean;
  sessionWarningMinutes?: number;
  maxSessionDuration?: number; // minutes
  apiBaseUrl?: string;
}

// Create context
const AuthContext = createContext<AuthContextValue | null>(null);

// Hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export function AuthProvider({
  children,
  enableDeviceTracking = true,
  enableSessionExtension = true,
  sessionWarningMinutes = 5,
  maxSessionDuration = 480, // 8 hours
  apiBaseUrl,
}: AuthProviderProps) {
  // Store integration
  const authStore = useAuthStore();
  const tenantStore = useTenantStore();
  const notificationsStore = useNotificationsStore();

  // Session monitoring state
  const [sessionWarningShown, setSessionWarningShown] = React.useState(false);
  const [sessionExtensionTimer, setSessionExtensionTimer] = React.useState<NodeJS.Timeout | null>(null);

  // API client
  const apiClient = getApiClient();

  // Authentication actions
  const login = useCallback(async (credentials: LoginCredentials): Promise<LoginResult> => {
    try {
      authStore.setLoading(true);
      
      const response = await apiClient.auth.login({
        email: credentials.email,
        portalId: credentials.portalId,
        password: credentials.password,
        rememberMe: credentials.rememberMe,
        deviceFingerprint: credentials.deviceFingerprint || generateDeviceFingerprint(),
      });

      if (response.data.success) {
        const { user, sessionId, csrfToken, mfaRequired } = response.data;

        // Set authentication state
        await authStore.setAuth(user, sessionId, csrfToken);

        // Handle MFA requirement
        if (mfaRequired) {
          authStore.requireMFA();
          return { success: true, mfaRequired: true };
        }

        // Load tenant context
        if (user.tenant_id) {
          await tenantStore.setCurrentTenant(
            { id: user.tenant_id, name: user.company || 'Unknown' } as any,
            user
          );
        }

        // Add login notification
        notificationsStore.addNotification({
          type: 'security',
          severity: 'info',
          title: 'Login Successful',
          message: `Welcome back, ${user.name}!`,
          category: 'authentication',
          source: 'auth_system',
          persistent: false,
        });

        return { success: true, user };
      } else {
        return { success: false, error: response.data.error || 'Login failed' };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      authStore.setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      authStore.setLoading(false);
    }
  }, [authStore, tenantStore, notificationsStore, apiClient]);

  const logout = useCallback(async () => {
    try {
      // Call logout API
      await apiClient.auth.logout();

      // Clear all state
      await authStore.clearAuth();
      tenantStore.clearTenant();
      
      // Add logout notification
      notificationsStore.addNotification({
        type: 'system',
        severity: 'info',
        title: 'Logged Out',
        message: 'You have been successfully logged out.',
        category: 'authentication',
        source: 'auth_system',
        persistent: false,
      });

      // Clear session monitoring
      if (sessionExtensionTimer) {
        clearTimeout(sessionExtensionTimer);
        setSessionExtensionTimer(null);
      }
      setSessionWarningShown(false);

    } catch (error) {
      console.error('Logout error:', error);
      // Force clear local state even if API call fails
      await authStore.clearAuth();
      tenantStore.clearTenant();
    }
  }, [authStore, tenantStore, notificationsStore, apiClient, sessionExtensionTimer]);

  const refreshToken = useCallback(async () => {
    try {
      const response = await apiClient.auth.refreshToken();
      
      if (response.data.success) {
        const { user, sessionId, csrfToken } = response.data;
        await authStore.setAuth(user, sessionId, csrfToken);
        authStore.updateLastActivity();
      } else {
        await forceLogout('Token refresh failed');
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      await forceLogout('Session expired');
    }
  }, [authStore, apiClient]);

  // MFA actions
  const setupMFA = useCallback(async (method: MFAMethod): Promise<MFASetupResult> => {
    const response = await apiClient.auth.setupMFA({ method });
    return response.data;
  }, [apiClient]);

  const verifyMFA = useCallback(async (code: string, method?: MFAMethod) => {
    const response = await apiClient.auth.verifyMFA({ code, method });
    
    if (response.data.success) {
      authStore.completeMFA();
      
      // Add MFA success notification
      notificationsStore.addNotification({
        type: 'security',
        severity: 'success',
        title: 'MFA Verified',
        message: 'Multi-factor authentication completed successfully.',
        category: 'authentication',
        source: 'auth_system',
        persistent: false,
      });
    } else {
      throw new Error(response.data.error || 'MFA verification failed');
    }
  }, [authStore, notificationsStore, apiClient]);

  const disableMFA = useCallback(async (currentPassword: string) => {
    await apiClient.auth.disableMFA({ currentPassword });
    
    // Update user state
    if (authStore.user) {
      authStore.updateUser({ mfaEnabled: false });
    }

    notificationsStore.addNotification({
      type: 'security',
      severity: 'warning',
      title: 'MFA Disabled',
      message: 'Multi-factor authentication has been disabled for your account.',
      category: 'security',
      source: 'auth_system',
      persistent: true,
    });
  }, [authStore, notificationsStore, apiClient]);

  // Session management
  const extendSession = useCallback(() => {
    authStore.updateLastActivity();
    setSessionWarningShown(false);
    
    // Reset session extension timer
    if (sessionExtensionTimer) {
      clearTimeout(sessionExtensionTimer);
    }
    
    if (enableSessionExtension) {
      const timer = setTimeout(() => {
        if (authStore.isSessionValid()) {
          refreshToken();
        }
      }, 15 * 60 * 1000); // Refresh 15 minutes before expiry
      
      setSessionExtensionTimer(timer);
    }
  }, [authStore, refreshToken, enableSessionExtension, sessionExtensionTimer]);

  const checkSessionValidity = useCallback(() => {
    return authStore.isSessionValid();
  }, [authStore]);

  const forceLogout = useCallback(async (reason?: string) => {
    if (reason) {
      notificationsStore.addNotification({
        type: 'security',
        severity: 'warning',
        title: 'Session Ended',
        message: reason,
        category: 'authentication',
        source: 'auth_system',
        persistent: true,
      });
    }
    
    await logout();
  }, [logout, notificationsStore]);

  // User management
  const updateProfile = useCallback(async (updates: Partial<UserProfile>) => {
    const response = await apiClient.identity.updateProfile(updates);
    
    if (response.data.success) {
      authStore.updateUser(updates);
      
      notificationsStore.addNotification({
        type: 'system',
        severity: 'success',
        title: 'Profile Updated',
        message: 'Your profile has been updated successfully.',
        category: 'account',
        source: 'user_management',
        persistent: false,
      });
    }
  }, [authStore, notificationsStore, apiClient]);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    await apiClient.auth.changePassword({ currentPassword, newPassword });
    
    notificationsStore.addNotification({
      type: 'security',
      severity: 'success',
      title: 'Password Changed',
      message: 'Your password has been updated successfully.',
      category: 'security',
      source: 'auth_system',
      persistent: false,
    });
  }, [notificationsStore, apiClient]);

  const updatePreferences = useCallback(async (preferences: UserPreferences) => {
    await apiClient.identity.updatePreferences(preferences);
    
    if (authStore.user) {
      authStore.updateUser({ preferences });
    }
  }, [authStore, apiClient]);

  // Security features
  const enableDeviceTrackingFunc = useCallback(async () => {
    await apiClient.auth.enableDeviceTracking();
    
    if (authStore.user) {
      authStore.updateUser({ deviceTrackingEnabled: true });
    }
  }, [authStore, apiClient]);

  const revokeAllSessions = useCallback(async () => {
    await apiClient.auth.revokeAllSessions();
    await forceLogout('All sessions have been revoked');
  }, [apiClient, forceLogout]);

  const getActiveDevices = useCallback(async (): Promise<UserDevice[]> => {
    const response = await apiClient.auth.getActiveDevices();
    return response.data.devices;
  }, [apiClient]);

  const revokeDevice = useCallback(async (deviceId: string) => {
    await apiClient.auth.revokeDevice({ deviceId });
    
    notificationsStore.addNotification({
      type: 'security',
      severity: 'info',
      title: 'Device Revoked',
      message: 'Device access has been revoked successfully.',
      category: 'security',
      source: 'auth_system',
      persistent: false,
    });
  }, [notificationsStore, apiClient]);

  // Utility functions
  const hasPermission = useCallback((permission: string) => {
    return authStore.user?.permissions?.includes(permission) || false;
  }, [authStore.user]);

  const hasRole = useCallback((role: UserRole) => {
    return authStore.user?.role === role;
  }, [authStore.user]);

  const getPortalType = useCallback((): PortalType | null => {
    return authStore.user?.portal || null;
  }, [authStore.user]);

  // Session monitoring effects
  useEffect(() => {
    if (!authStore.isAuthenticated || !enableSessionExtension) return;

    const checkSession = () => {
      const timeUntilExpiry = authStore.getTimeUntilExpiry?.() || 0;
      const warningTime = sessionWarningMinutes * 60 * 1000;

      if (timeUntilExpiry <= warningTime && !sessionWarningShown && timeUntilExpiry > 0) {
        setSessionWarningShown(true);
        
        notificationsStore.addNotification({
          type: 'system',
          severity: 'warning',
          title: 'Session Expiring Soon',
          message: `Your session will expire in ${Math.ceil(timeUntilExpiry / 60000)} minutes.`,
          category: 'session',
          source: 'auth_system',
          persistent: true,
          actions: [
            {
              id: 'extend_session',
              label: 'Extend Session',
              type: 'primary',
              action: extendSession,
            },
          ],
        });
      }

      if (timeUntilExpiry <= 0) {
        forceLogout('Your session has expired');
      }
    };

    const interval = setInterval(checkSession, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [
    authStore.isAuthenticated,
    enableSessionExtension,
    sessionWarningMinutes,
    sessionWarningShown,
    extendSession,
    forceLogout,
    notificationsStore,
    authStore,
  ]);

  // Auto token refresh
  useEffect(() => {
    if (!authStore.isAuthenticated) return;

    const interval = setInterval(() => {
      if (authStore.isSessionValid()) {
        refreshToken();
      }
    }, 10 * 60 * 1000); // Refresh every 10 minutes

    return () => clearInterval(interval);
  }, [authStore.isAuthenticated, refreshToken, authStore]);

  // Activity tracking
  useEffect(() => {
    if (!authStore.isAuthenticated) return;

    const trackActivity = () => {
      authStore.updateLastActivity();
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, trackActivity);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, trackActivity);
      });
    };
  }, [authStore.isAuthenticated, authStore]);

  // Context value
  const contextValue: AuthContextValue = {
    // Authentication state
    user: authStore.user,
    isAuthenticated: authStore.isAuthenticated,
    isLoading: authStore.isLoading || false,
    error: authStore.error || null,
    
    // Session management
    sessionId: authStore.sessionId,
    sessionExpiry: authStore.sessionExpiry || null,
    lastActivity: authStore.lastActivity ? new Date(authStore.lastActivity) : null,
    
    // MFA state
    mfaRequired: authStore.mfaRequired,
    mfaVerified: authStore.mfaVerified,
    mfaSetupRequired: authStore.user?.mfaEnabled === false,
    
    // Authentication actions
    login,
    logout,
    refreshToken,
    
    // MFA actions
    setupMFA,
    verifyMFA,
    disableMFA,
    
    // Session management
    extendSession,
    checkSessionValidity,
    forceLogout,
    
    // User management
    updateProfile,
    changePassword,
    updatePreferences,
    
    // Security features
    enableDeviceTracking: enableDeviceTrackingFunc,
    revokeAllSessions,
    getActiveDevices,
    revokeDevice,
    
    // Utility functions
    hasPermission,
    hasRole,
    getPortalType,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Helper function to generate device fingerprint
function generateDeviceFingerprint(): string {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  ctx?.fillText('Device fingerprint', 2, 2);
  
  const fingerprint = {
    userAgent: navigator.userAgent,
    language: navigator.language,
    platform: navigator.platform,
    screen: `${screen.width}x${screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    canvas: canvas.toDataURL(),
  };

  return btoa(JSON.stringify(fingerprint));
}

export { AuthProvider, useAuth };