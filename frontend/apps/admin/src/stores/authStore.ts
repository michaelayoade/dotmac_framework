/**
 * Centralized Authentication Store
 * Uses Zustand for secure, centralized auth state management
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'operator' | 'viewer';
  permissions: string[];
  tenantId?: string;
}

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  sessionExpiry: number | null;
  lastActivity: number;
  
  // Actions
  login: (credentials: { email: string; password: string }) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  validateSession: () => Promise<boolean>;
  clearError: () => void;
  updateLastActivity: () => void;
  
  // Permission helpers
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  
  // Session helpers
  isSessionValid: () => boolean;
  getTimeUntilExpiry: () => number;
}

// Custom storage that only uses cookies (no localStorage)
const cookieStorage = createJSONStorage(() => ({
  getItem: (name: string) => {
    if (typeof document === 'undefined') return null;
    
    try {
      // Only read non-sensitive user data from cookies
      const value = document.cookie
        .split('; ')
        .find(row => row.startsWith(`${name}=`))
        ?.split('=')[1];
      
      return value ? decodeURIComponent(value) : null;
    } catch {
      return null;
    }
  },
  setItem: (name: string, value: string) => {
    if (typeof document === 'undefined') return;
    
    try {
      // Only store non-sensitive data in cookies
      document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${7 * 24 * 60 * 60}; samesite=strict`;
    } catch (error) {
      console.warn('Failed to set cookie:', error);
    }
  },
  removeItem: (name: string) => {
    if (typeof document === 'undefined') return;
    
    document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  },
}));

export const useAuthStore = create<AuthState>()(
  persist(
    immer((set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      sessionExpiry: null,
      lastActivity: Date.now(),
      
      // Login action
      login: async (credentials) => {
        set((state) => {
          state.isLoading = true;
          state.error = null;
        });
        
        try {
          // Get CSRF token
          const csrfResponse = await fetch('/api/auth/csrf', {
            method: 'GET',
            credentials: 'include',
          });
          
          if (!csrfResponse.ok) {
            throw new Error('Failed to get CSRF token');
          }
          
          const { csrfToken } = await csrfResponse.json();
          
          // Perform login
          const response = await fetch('/api/auth/login', {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': csrfToken,
            },
            body: JSON.stringify({
              ...credentials,
              portal: 'admin',
            }),
          });
          
          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Login failed');
          }
          
          const data = await response.json();
          
          set((state) => {
            state.user = data.user;
            state.isAuthenticated = true;
            state.isLoading = false;
            state.error = null;
            state.sessionExpiry = data.expiresAt ? new Date(data.expiresAt).getTime() : null;
            state.lastActivity = Date.now();
          });
          
          return { success: true };
          
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          
          set((state) => {
            state.isLoading = false;
            state.error = errorMessage;
            state.isAuthenticated = false;
            state.user = null;
          });
          
          return { success: false, error: errorMessage };
        }
      },
      
      // Logout action
      logout: async () => {
        try {
          await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include',
          });
        } catch (error) {
          console.warn('Logout request failed:', error);
        }
        
        set((state) => {
          state.user = null;
          state.isAuthenticated = false;
          state.isLoading = false;
          state.error = null;
          state.sessionExpiry = null;
          state.lastActivity = Date.now();
        });
        
        // SECURITY: No localStorage tokens to clear - using secure cookies only
        // All authentication is handled server-side with httpOnly cookies
        
        // Redirect to login
        window.location.href = '/login';
      },
      
      // Refresh token action
      refreshToken: async () => {
        try {
          const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            credentials: 'include',
          });
          
          if (!response.ok) {
            // Refresh failed - logout user
            get().logout();
            return false;
          }
          
          const data = await response.json();
          
          set((state) => {
            state.sessionExpiry = data.expiresAt ? new Date(data.expiresAt).getTime() : null;
            state.lastActivity = Date.now();
          });
          
          return true;
        } catch (error) {
          console.error('Token refresh failed:', error);
          get().logout();
          return false;
        }
      },
      
      // Validate session action
      validateSession: async () => {
        try {
          const response = await fetch('/api/auth/validate', {
            method: 'GET',
            credentials: 'include',
          });
          
          if (response.ok) {
            const userData = await response.json();
            
            set((state) => {
              state.user = userData.user;
              state.isAuthenticated = true;
              state.lastActivity = Date.now();
            });
            
            return true;
          } else {
            // Session invalid
            set((state) => {
              state.user = null;
              state.isAuthenticated = false;
            });
            
            return false;
          }
        } catch (error) {
          console.error('Session validation failed:', error);
          
          set((state) => {
            state.user = null;
            state.isAuthenticated = false;
          });
          
          return false;
        }
      },
      
      // Clear error
      clearError: () => {
        set((state) => {
          state.error = null;
        });
      },
      
      // Update last activity
      updateLastActivity: () => {
        set((state) => {
          state.lastActivity = Date.now();
        });
      },
      
      // Permission helpers
      hasPermission: (permission: string) => {
        const { user } = get();
        return user?.permissions.includes(permission) || false;
      },
      
      hasRole: (role: string) => {
        const { user } = get();
        return user?.role === role;
      },
      
      hasAnyPermission: (permissions: string[]) => {
        const { user } = get();
        if (!user) return false;
        return permissions.some(permission => user.permissions.includes(permission));
      },
      
      // Session helpers
      isSessionValid: () => {
        const { sessionExpiry, isAuthenticated } = get();
        
        if (!isAuthenticated) return false;
        if (!sessionExpiry) return true; // No expiry set
        
        return Date.now() < sessionExpiry;
      },
      
      getTimeUntilExpiry: () => {
        const { sessionExpiry } = get();
        
        if (!sessionExpiry) return Infinity;
        return Math.max(0, sessionExpiry - Date.now());
      },
    })),
    {
      name: 'auth-store',
      storage: cookieStorage,
      // Only persist non-sensitive user data
      partialize: (state) => ({
        user: state.user ? {
          id: state.user.id,
          email: state.user.email,
          name: state.user.name,
          role: state.user.role,
          // Don't persist permissions - fetch fresh on session validation
        } : null,
        lastActivity: state.lastActivity,
      }),
    }
  )
);

// Auto-refresh token setup
let refreshInterval: NodeJS.Timeout | null = null;

export function startTokenRefresh() {
  if (refreshInterval) return;
  
  refreshInterval = setInterval(() => {
    const { isAuthenticated, isSessionValid, refreshToken } = useAuthStore.getState();
    
    if (isAuthenticated && isSessionValid()) {
      refreshToken();
    }
  }, 25 * 60 * 1000); // Refresh every 25 minutes
}

export function stopTokenRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

// Activity tracker for automatic logout
let activityTimeout: NodeJS.Timeout | null = null;
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes

export function trackActivity() {
  const { updateLastActivity, isAuthenticated, logout } = useAuthStore.getState();
  
  if (!isAuthenticated) return;
  
  updateLastActivity();
  
  // Clear existing timeout
  if (activityTimeout) {
    clearTimeout(activityTimeout);
  }
  
  // Set new timeout
  activityTimeout = setTimeout(() => {
    console.warn('Session expired due to inactivity');
    logout();
  }, INACTIVITY_TIMEOUT);
}

// Setup activity tracking
if (typeof window !== 'undefined') {
  const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
  
  events.forEach(event => {
    document.addEventListener(event, trackActivity, { passive: true });
  });
}