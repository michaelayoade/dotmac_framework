/**
 * Secure authentication store using Zustand with enhanced security
 */

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { User } from '../types';
import { csrfProtection } from '../utils/csrfProtection';
import { secureStorage } from '../utils/secureStorage';

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  sessionId: string | null;
  mfaRequired: boolean;
  mfaVerified: boolean;
  lastActivity: number | null;
}

export interface AuthActions {
  setAuth: (user: User, sessionId?: string, csrfToken?: string) => Promise<void>;
  clearAuth: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
  requireMFA: () => void;
  completeMFA: () => void;
  updateLastActivity: () => void;
  isSessionValid: () => boolean;
}

type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  sessionId: null,
  mfaRequired: false,
  mfaVerified: false,
  lastActivity: null,
};

// Session timeout in milliseconds (30 minutes)
const SESSION_TIMEOUT = 30 * 60 * 1000;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setAuth: async (user, sessionId, csrfToken) => {
        // Initialize CSRF protection if token provided
        if (csrfToken) {
          csrfProtection.storeToken(csrfToken);
        } else {
          await csrfProtection.initialize();
        }

        // Generate session ID if not provided
        const currentSessionId =
          sessionId || crypto.getRandomValues(new Uint32Array(1))[0].toString(36);

        set({
          user,
          isAuthenticated: true,
          sessionId: currentSessionId,
          mfaRequired: user.mfaEnabled || false,
          mfaVerified: !user.mfaEnabled, // If MFA not enabled, consider it verified
          lastActivity: Date.now(),
        });
      },

      clearAuth: async () => {
        try {
          // Clear CSRF protection
          csrfProtection.clearToken();

          // Clear all secure storage (non-sensitive data only)
          secureStorage.clear();

          // NOTE: Actual token clearing must be done via server actions
          // Tokens are in httpOnly cookies and cannot be cleared client-side

          set(initialState);
        } catch (_error) {
          // Still reset state even if cleanup fails
          set(initialState);
        }
      },

      updateUser: (updates) => {
        const { user } = get();
        if (user) {
          set({
            user: { ...user, ...updates },
            lastActivity: Date.now(),
          });
        }
      },

      requireMFA: () => {
        set({ mfaRequired: true, mfaVerified: false });
      },

      completeMFA: () => {
        set({ mfaVerified: true, lastActivity: Date.now() });
      },

      updateLastActivity: () => {
        set({ lastActivity: Date.now() });
      },

      isSessionValid: () => {
        const { lastActivity, isAuthenticated } = get();

        if (!isAuthenticated || !lastActivity) {
          return false;
        }

        // Check session timeout
        const now = Date.now();
        const timeSinceLastActivity = now - lastActivity;

        return timeSinceLastActivity < SESSION_TIMEOUT;
      },
    }),
    {
      name: 'dotmac-session-state',
      storage: createJSONStorage(() => {
        // Use secure storage wrapper
        return {
          getItem: (name) => secureStorage.getItem(name),
          setItem: (name, value) => secureStorage.setItem(name, value),
          removeItem: (name) => secureStorage.removeItem(name),
        };
      }),
      partialize: (state) => ({
        // Only store non-sensitive session data
        user: state.user
          ? {
              ...state.user,
              // Remove sensitive fields from persistence
              password: undefined,
              tempPassword: undefined,
            }
          : null,
        isAuthenticated: state.isAuthenticated,
        sessionId: state.sessionId,
        mfaRequired: state.mfaRequired,
        mfaVerified: state.mfaVerified,
        lastActivity: state.lastActivity,
      }),
      onRehydrateStorage: () => (state) => {
        // Validate session on rehydration
        if (state?.isSessionValid && !state.isSessionValid()) {
          state.clearAuth?.();
        }
      },
    }
  )
);
