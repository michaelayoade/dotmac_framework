/**
 * Secure authentication store using Zustand with enhanced security
 */

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { User } from '../types';
import { csrfProtection } from '../utils/csrfProtection';
import { secureStorage } from '../utils/secureStorage';
import { type TokenPair, tokenManager } from '../utils/tokenManager';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  sessionId: string | null;
  mfaRequired: boolean;
  mfaVerified: boolean;
  lastActivity: number | null;
}

interface AuthActions {
  setAuth: (
    user: User,
    tokenPair: TokenPair,
    sessionId?: string,
    csrfToken?: string
  ) => Promise<void>;
  clearAuth: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
  refreshTokens: (
    apiRefreshFunction: (refreshToken: string) => Promise<TokenPair>
  ) => Promise<boolean>;
  getValidToken: () => Promise<string | null>;
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

      setAuth: async (user, tokenPair, sessionId, _csrfToken) => {
        // Store tokens securely
        tokenManager.setTokens(tokenPair, csrfToken);

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
          // Clear all tokens and CSRF protection
          tokenManager.clearTokens();
          csrfProtection.clearToken();

          // Clear all secure storage
          secureStorage.clear();

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

      refreshTokens: async (apiRefreshFunction) => {
        try {
          const result = await tokenManager.refreshTokens(apiRefreshFunction);
          if (result) {
            set({ lastActivity: Date.now() });
            return true;
          }

          // Refresh failed, clear auth
          await get().clearAuth();
          return false;
        } catch (_error) {
          await get().clearAuth();
          return false;
        }
      },

      getValidToken: async () => {
        try {
          const { isSessionValid } = get();

          // Check session validity
          if (!isSessionValid()) {
            await get().clearAuth();
            return null;
          }

          // Get token from token manager (handles validation and refresh)
          const token = tokenManager.getAccessToken();

          if (token) {
            // Update last activity
            set({ lastActivity: Date.now() });
            return token;
          }

          return null;
        } catch (_error) {
          return null;
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
        const { lastActivity, _isAuthenticated } = get();

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
      name: 'dotmac-auth-session',
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
