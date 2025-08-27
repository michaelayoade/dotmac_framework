/**
 * Secure Authentication Store
 * Replaces the insecure authStore with proper security practices
 */

import { create } from 'zustand';
import { createSecureAuthManager, type AuthResponse } from '../lib/secure-auth';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'operator' | 'viewer';
  permissions: string[];
}

interface SecureAuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isSessionValid: boolean;
  lastActivity: number;
  
  // Actions
  login: (credentials: { email: string; password: string; mfaCode?: string }) => Promise<AuthResponse>;
  logout: () => Promise<void>;
  validateSession: () => Promise<boolean>;
  clearError: () => void;
  updateActivity: () => void;
  
  // Permission helpers
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
  
  // Internal
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

// Create secure auth manager instance
const secureAuth = createSecureAuthManager();

export const useSecureAuthStore = create<SecureAuthState>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  isSessionValid: false,
  lastActivity: Date.now(),
  
  // Actions
  login: async (credentials) => {
    const { setLoading, setError, setUser } = get();
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await secureAuth.login(credentials);
      
      if (result.success && result.user) {
        setUser(result.user);
        set({ isAuthenticated: true, isSessionValid: true });
        get().updateActivity();
      } else {
        setError(result.error || 'Authentication failed');
      }
      
      return result;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Network error';
      setError(errorMessage);
      return { success: false, error: errorMessage };
      
    } finally {
      setLoading(false);
    }
  },
  
  logout: async () => {
    const { setUser } = get();
    
    try {
      await secureAuth.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear state regardless of server response
      setUser(null);
      set({ 
        isAuthenticated: false, 
        isSessionValid: false, 
        error: null 
      });
    }
  },
  
  validateSession: async () => {
    try {
      const isValid = await secureAuth.validateSession();
      set({ isSessionValid: isValid });
      
      if (!isValid) {
        // Clear user state if session is invalid
        get().setUser(null);
        set({ isAuthenticated: false });
      } else {
        get().updateActivity();
      }
      
      return isValid;
      
    } catch (error) {
      console.error('Session validation error:', error);
      set({ isSessionValid: false });
      return false;
    }
  },
  
  clearError: () => {
    set({ error: null });
  },
  
  updateActivity: () => {
    set({ lastActivity: Date.now() });
  },
  
  // Permission helpers
  hasPermission: (permission: string) => {
    const { user, isAuthenticated } = get();
    return isAuthenticated && user?.permissions?.includes(permission) || false;
  },
  
  hasRole: (role: string) => {
    const { user, isAuthenticated } = get();
    return isAuthenticated && user?.role === role || false;
  },
  
  hasAnyPermission: (permissions: string[]) => {
    const { user, isAuthenticated } = get();
    if (!isAuthenticated || !user?.permissions) return false;
    return permissions.some(permission => user.permissions.includes(permission));
  },
  
  hasAllPermissions: (permissions: string[]) => {
    const { user, isAuthenticated } = get();
    if (!isAuthenticated || !user?.permissions) return false;
    return permissions.every(permission => user.permissions.includes(permission));
  },
  
  // Internal setters
  setUser: (user) => {
    set({ user });
  },
  
  setLoading: (loading) => {
    set({ isLoading: loading });
  },
  
  setError: (error) => {
    set({ error });
  },
}));

// Set up session monitoring
if (typeof window !== 'undefined') {
  // Listen for session timeout events
  window.addEventListener('session-timeout', () => {
    useSecureAuthStore.getState().logout();
    // Optionally show a notification
    window.dispatchEvent(new CustomEvent('show-notification', {
      detail: {
        type: 'warning',
        message: 'Your session has expired due to inactivity. Please log in again.',
      }
    }));
  });
  
  // Listen for session invalid events
  window.addEventListener('session-invalid', () => {
    useSecureAuthStore.getState().logout();
    window.dispatchEvent(new CustomEvent('show-notification', {
      detail: {
        type: 'error',
        message: 'Your session is no longer valid. Please log in again.',
      }
    }));
  });
  
  // Validate session on app load
  useSecureAuthStore.getState().validateSession();
  
  // Set up periodic session validation (every 5 minutes)
  setInterval(() => {
    const { isAuthenticated } = useSecureAuthStore.getState();
    if (isAuthenticated) {
      useSecureAuthStore.getState().validateSession();
    }
  }, 5 * 60 * 1000); // 5 minutes
}

// Export default auth store
export default useSecureAuthStore;