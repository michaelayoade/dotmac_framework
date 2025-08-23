/**
 * Comprehensive State Management Orchestrator
 * Coordinates between all stores and provides unified state management
 */

import { useAuthStore } from './authStore';
import { useTenantStore } from './tenantStore';
import { useAppStore } from './appStore';
import { useNotificationsStore } from './notificationsStore';

// State manager interface
export interface StateManagerInterface {
  // Store accessors
  auth: ReturnType<typeof useAuthStore>;
  tenant: ReturnType<typeof useTenantStore>;
  app: ReturnType<typeof useAppStore>;
  notifications: ReturnType<typeof useNotificationsStore>;
  
  // Unified actions
  initialize: () => Promise<void>;
  reset: () => Promise<void>;
  syncStores: () => void;
  
  // Cross-store operations
  handleUserLogin: (user: any, tenant: any) => Promise<void>;
  handleUserLogout: () => Promise<void>;
  handleTenantSwitch: (tenantId: string) => Promise<void>;
  
  // State validation
  validateState: () => {
    isValid: boolean;
    errors: string[];
  };
  
  // Debug utilities
  getStateSnapshot: () => Record<string, any>;
  restoreFromSnapshot: (snapshot: Record<string, any>) => void;
}

/**
 * Create State Manager Instance
 * Provides orchestrated access to all stores
 */
export function createStateManager(): StateManagerInterface {
  // Access all stores
  const authStore = useAuthStore.getState();
  const tenantStore = useTenantStore.getState();
  const appStore = useAppStore.getState();
  const notificationsStore = useNotificationsStore.getState();

  return {
    // Store accessors
    get auth() { return useAuthStore.getState(); },
    get tenant() { return useTenantStore.getState(); },
    get app() { return useAppStore.getState(); },
    get notifications() { return useNotificationsStore.getState(); },

    // Unified actions
    initialize: async () => {
      try {
        // Initialize app store with default state
        appStore.updateUI({ sidebarOpen: true });
        
        // Setup notification preferences if not set
        if (!notificationsStore.preferences.enabled) {
          notificationsStore.updatePreferences({
            enabled: true,
            sound: true,
            desktop: true,
          });
        }

        // Setup cross-store subscriptions
        subscribeToStoreChanges();
        
        console.log('State management initialized successfully');
      } catch (error) {
        console.error('Failed to initialize state management:', error);
        throw error;
      }
    },

    reset: async () => {
      try {
        // Reset all stores to initial state
        await authStore.clearAuth();
        tenantStore.clearTenant();
        appStore.resetAllContexts();
        notificationsStore.dismissAll();
        
        console.log('State management reset successfully');
      } catch (error) {
        console.error('Failed to reset state management:', error);
        throw error;
      }
    },

    syncStores: () => {
      // Sync authentication state across stores
      const { user, isAuthenticated } = authStore;
      const { currentTenant } = tenantStore;

      // Update app store with user context
      if (isAuthenticated && user) {
        appStore.updatePreferences({
          theme: user.preferences?.theme || 'light',
          language: user.preferences?.language || 'en',
          timezone: user.preferences?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
        });
      }

      // Sync notification preferences with user settings
      if (user?.preferences?.notifications) {
        notificationsStore.updatePreferences({
          enabled: user.preferences.notifications.enabled ?? true,
          sound: user.preferences.notifications.sound ?? true,
          desktop: user.preferences.notifications.desktop ?? true,
          email: user.preferences.notifications.email ?? false,
        });
      }

      // Update tenant branding in app if available
      if (currentTenant) {
        const branding = tenantStore.getTenantBranding();
        if (branding.primaryColor) {
          document.documentElement.style.setProperty('--primary-color', branding.primaryColor);
        }
        if (branding.secondaryColor) {
          document.documentElement.style.setProperty('--secondary-color', branding.secondaryColor);
        }
      }
    },

    // Cross-store operations
    handleUserLogin: async (user, tenant) => {
      try {
        // Set authentication state
        await authStore.setAuth(user);
        
        // Set tenant context if provided
        if (tenant) {
          tenantStore.setCurrentTenant(tenant, user);
        }
        
        // Add welcome notification
        notificationsStore.addNotification({
          type: 'system',
          severity: 'success',
          title: 'Welcome Back!',
          message: `Successfully logged in as ${user.name}`,
          category: 'authentication',
          source: 'state_manager',
          persistent: false,
        });
        
        // Sync all stores
        this.syncStores();
        
        console.log('User login handled successfully');
      } catch (error) {
        console.error('Failed to handle user login:', error);
        throw error;
      }
    },

    handleUserLogout: async () => {
      try {
        // Add logout notification before clearing state
        notificationsStore.addNotification({
          type: 'system',
          severity: 'info',
          title: 'Logged Out',
          message: 'You have been successfully logged out',
          category: 'authentication',
          source: 'state_manager',
          persistent: false,
        });
        
        // Clear all user-specific state
        await authStore.clearAuth();
        tenantStore.clearTenant();
        appStore.resetAllContexts();
        
        // Reset to default preferences
        appStore.updatePreferences({
          theme: 'light',
          language: 'en',
          compactMode: false,
        });
        
        // Disconnect real-time notifications
        notificationsStore.disconnect();
        
        console.log('User logout handled successfully');
      } catch (error) {
        console.error('Failed to handle user logout:', error);
        throw error;
      }
    },

    handleTenantSwitch: async (tenantId) => {
      try {
        // Switch tenant
        await tenantStore.switchTenant(tenantId);
        
        // Load tenant-specific configurations
        const newTenant = tenantStore.currentTenant;
        if (newTenant) {
          // Update app preferences with tenant defaults
          const tenantSettings = newTenant.settings;
          if (tenantSettings) {
            appStore.updatePreferences({
              ...appStore.preferences,
              ...tenantSettings.defaultUserPreferences,
            });
          }
          
          // Apply tenant branding
          this.syncStores();
          
          // Add tenant switch notification
          notificationsStore.addNotification({
            type: 'system',
            severity: 'info',
            title: 'Tenant Switched',
            message: `Switched to ${newTenant.tenant.name}`,
            category: 'tenant',
            source: 'state_manager',
            persistent: false,
          });
        }
        
        console.log('Tenant switch handled successfully');
      } catch (error) {
        console.error('Failed to handle tenant switch:', error);
        throw error;
      }
    },

    // State validation
    validateState: () => {
      const errors: string[] = [];
      
      // Validate authentication state consistency
      const { user, isAuthenticated, sessionId } = authStore;
      if (isAuthenticated && !user) {
        errors.push('Authenticated but no user data available');
      }
      if (isAuthenticated && !sessionId) {
        errors.push('Authenticated but no session ID available');
      }
      
      // Validate tenant state consistency
      const { currentTenant } = tenantStore;
      if (isAuthenticated && user?.tenant_id && !currentTenant) {
        errors.push('User has tenant ID but no tenant context loaded');
      }
      
      // Validate session expiry
      if (isAuthenticated && !authStore.isSessionValid()) {
        errors.push('Session has expired');
      }
      
      return {
        isValid: errors.length === 0,
        errors,
      };
    },

    // Debug utilities
    getStateSnapshot: () => ({
      auth: {
        isAuthenticated: authStore.isAuthenticated,
        user: authStore.user,
        sessionId: authStore.sessionId,
        mfaRequired: authStore.mfaRequired,
        mfaVerified: authStore.mfaVerified,
      },
      tenant: {
        currentTenant: tenantStore.currentTenant,
        availableTenants: tenantStore.availableTenants,
        isLoading: tenantStore.isLoading,
      },
      app: {
        ui: appStore.ui,
        preferences: appStore.preferences,
      },
      notifications: {
        notifications: notificationsStore.notifications.slice(0, 10), // Limit for debugging
        unreadCount: notificationsStore.unreadCount,
        realtime: notificationsStore.realtime,
      },
      timestamp: new Date().toISOString(),
    }),

    restoreFromSnapshot: (snapshot) => {
      try {
        // This is a simplified restore - in production you'd want more validation
        const { auth, tenant, app, notifications } = snapshot;
        
        if (auth) {
          if (auth.isAuthenticated && auth.user) {
            authStore.setAuth(auth.user, auth.sessionId);
          }
        }
        
        if (tenant && tenant.currentTenant) {
          tenantStore.setCurrentTenant(tenant.currentTenant.tenant, tenant.currentTenant.user);
        }
        
        if (app) {
          if (app.preferences) {
            appStore.updatePreferences(app.preferences);
          }
          if (app.ui) {
            appStore.updateUI(app.ui);
          }
        }
        
        console.log('State restored from snapshot');
      } catch (error) {
        console.error('Failed to restore state from snapshot:', error);
        throw error;
      }
    },
  };
}

/**
 * Setup Cross-Store Subscriptions
 * Establishes reactive relationships between stores
 */
function subscribeToStoreChanges() {
  // Subscribe to auth changes
  useAuthStore.subscribe(
    (state) => ({ isAuthenticated: state.isAuthenticated, user: state.user }),
    ({ isAuthenticated, user }) => {
      const stateManager = createStateManager();
      
      // Sync stores when authentication changes
      if (isAuthenticated && user) {
        stateManager.syncStores();
      }
      
      // Clear tenant when user logs out
      if (!isAuthenticated) {
        useTenantStore.getState().clearTenant();
      }
    }
  );

  // Subscribe to tenant changes
  useTenantStore.subscribe(
    (state) => state.currentTenant,
    (currentTenant) => {
      const stateManager = createStateManager();
      
      // Apply branding when tenant changes
      if (currentTenant) {
        stateManager.syncStores();
      }
    }
  );

  // Subscribe to app theme changes
  useAppStore.subscribe(
    (state) => state.preferences.theme,
    (theme) => {
      // Apply theme to document
      document.documentElement.setAttribute('data-theme', theme);
      
      // Store theme preference
      localStorage.setItem('theme-preference', theme);
    }
  );
}

// Singleton state manager instance
let stateManagerInstance: StateManagerInterface | null = null;

/**
 * Get State Manager Singleton
 * Returns the global state manager instance
 */
export function getStateManager(): StateManagerInterface {
  if (!stateManagerInstance) {
    stateManagerInstance = createStateManager();
  }
  return stateManagerInstance;
}

/**
 * Initialize Global State Management
 * Call this once at app startup
 */
export const initializeStateManagement = async (): Promise<void> => {
  const stateManager = getStateManager();
  await stateManager.initialize();
};

/**
 * Reset Global State Management
 * Call this to completely reset all state
 */
export async function resetStateManagement(): Promise<void> {
  const stateManager = getStateManager();
  await stateManager.reset();
}

// Export types for external use
export type { StateManagerInterface };