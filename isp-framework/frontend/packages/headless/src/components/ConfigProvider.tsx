/**
 * Configuration Provider
 * Manages environment configuration, feature flags, and runtime settings
 * Provides centralized configuration management across the application
 */

import React, { ReactNode, createContext, useContext, useEffect, useMemo, useCallback } from 'react';
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { secureStorage } from '../utils/secureStorage';

// Configuration interfaces
export interface EnvironmentConfig {
  NODE_ENV: 'development' | 'production' | 'staging' | 'test';
  API_BASE_URL: string;
  WS_BASE_URL: string;
  CDN_BASE_URL: string;
  SENTRY_DSN?: string;
  ANALYTICS_ID?: string;
  
  // Feature flags
  FEATURES: {
    realTimeNotifications: boolean;
    advancedAnalytics: boolean;
    networkTopology: boolean;
    mobileApp: boolean;
    apiV2: boolean;
    experimentalUI: boolean;
    debugMode: boolean;
  };
  
  // API configuration
  API: {
    timeout: number;
    retries: number;
    rateLimit: {
      enabled: boolean;
      requests: number;
      window: number; // seconds
    };
    endpoints: {
      auth: string;
      billing: string;
      identity: string;
      services: string;
      network: string;
      support: string;
      analytics: string;
      files: string;
    };
  };
  
  // Real-time configuration
  REALTIME: {
    enabled: boolean;
    protocol: 'websocket' | 'sse';
    reconnectAttempts: number;
    heartbeatInterval: number; // seconds
    connectionTimeout: number; // seconds
  };
  
  // Security settings
  SECURITY: {
    sessionTimeout: number; // minutes
    maxLoginAttempts: number;
    passwordPolicy: {
      minLength: number;
      requireNumbers: boolean;
      requireSymbols: boolean;
      requireUppercase: boolean;
      requireLowercase: boolean;
    };
    mfaRequired: boolean;
    deviceTracking: boolean;
    csrfProtection: boolean;
  };
  
  // UI/UX settings
  UI: {
    theme: 'light' | 'dark' | 'auto';
    compactMode: boolean;
    animations: boolean;
    soundEffects: boolean;
    autoSave: boolean;
    autoSaveInterval: number; // seconds
    pagination: {
      defaultPageSize: number;
      pageSizeOptions: number[];
    };
    notifications: {
      position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
      maxVisible: number;
      defaultDuration: number; // seconds
    };
  };
  
  // Performance settings
  PERFORMANCE: {
    cacheEnabled: boolean;
    cacheTTL: number; // seconds
    lazyLoading: boolean;
    prefetching: boolean;
    compression: boolean;
    bundleAnalysis: boolean;
  };
  
  // Analytics and monitoring
  MONITORING: {
    enabled: boolean;
    errorReporting: boolean;
    performanceMonitoring: boolean;
    userAnalytics: boolean;
    debugLogging: boolean;
    logLevel: 'debug' | 'info' | 'warn' | 'error';
  };
  
  // Tenant-specific overrides
  TENANT_OVERRIDES: Record<string, Partial<EnvironmentConfig>>;
}

// Runtime configuration that can be updated
export interface RuntimeConfig {
  lastUpdated: Date;
  version: string;
  maintenanceMode: boolean;
  announcementBanner?: {
    message: string;
    type: 'info' | 'warning' | 'error' | 'success';
    dismissible: boolean;
    expiresAt?: Date;
  };
  featureFlags: Record<string, boolean>;
  experimentalFeatures: Record<string, any>;
  remoteConfigVersion: string;
}

// Configuration store interface
interface ConfigState {
  // Environment configuration (loaded at startup)
  environment: EnvironmentConfig | null;
  
  // Runtime configuration (can be updated remotely)
  runtime: RuntimeConfig | null;
  
  // Tenant-specific configuration
  tenantConfig: Partial<EnvironmentConfig> | null;
  
  // Loading and error state
  isLoading: boolean;
  error: string | null;
  lastSync: Date | null;
  
  // Configuration cache
  cache: Map<string, any>;
}

interface ConfigActions {
  // Initialization
  loadEnvironmentConfig: (config: Partial<EnvironmentConfig>) => void;
  loadRuntimeConfig: () => Promise<void>;
  loadTenantConfig: (tenantId: string) => Promise<void>;
  
  // Runtime updates
  updateRuntimeConfig: (updates: Partial<RuntimeConfig>) => void;
  updateFeatureFlag: (flag: string, enabled: boolean) => void;
  toggleMaintenanceMode: (enabled: boolean, message?: string) => void;
  
  // Feature flag utilities
  isFeatureEnabled: (feature: string) => boolean;
  getFeatureConfig: <T = any>(feature: string, defaultValue?: T) => T;
  
  // Configuration utilities
  getConfig: <T = any>(path: string, defaultValue?: T) => T;
  setConfig: (path: string, value: any) => void;
  
  // Cache management
  setCacheValue: (key: string, value: any, ttl?: number) => void;
  getCacheValue: <T = any>(key: string) => T | null;
  clearCache: () => void;
  
  // Sync and refresh
  syncWithRemote: () => Promise<void>;
  reset: () => void;
}

type ConfigStore = ConfigState & ConfigActions;

// Default configuration
const defaultEnvironmentConfig: EnvironmentConfig = {
  NODE_ENV: 'development',
  API_BASE_URL: '/api/v1',
  WS_BASE_URL: '/ws',
  CDN_BASE_URL: '/cdn',
  
  FEATURES: {
    realTimeNotifications: true,
    advancedAnalytics: true,
    networkTopology: true,
    mobileApp: false,
    apiV2: false,
    experimentalUI: false,
    debugMode: false,
  },
  
  API: {
    timeout: 30000,
    retries: 3,
    rateLimit: {
      enabled: true,
      requests: 1000,
      window: 60,
    },
    endpoints: {
      auth: '/auth',
      billing: '/billing',
      identity: '/identity',
      services: '/services',
      network: '/network',
      support: '/support',
      analytics: '/analytics',
      files: '/files',
    },
  },
  
  REALTIME: {
    enabled: true,
    protocol: 'websocket',
    reconnectAttempts: 5,
    heartbeatInterval: 30,
    connectionTimeout: 10,
  },
  
  SECURITY: {
    sessionTimeout: 480, // 8 hours
    maxLoginAttempts: 5,
    passwordPolicy: {
      minLength: 8,
      requireNumbers: true,
      requireSymbols: true,
      requireUppercase: true,
      requireLowercase: true,
    },
    mfaRequired: false,
    deviceTracking: true,
    csrfProtection: true,
  },
  
  UI: {
    theme: 'light',
    compactMode: false,
    animations: true,
    soundEffects: true,
    autoSave: true,
    autoSaveInterval: 30,
    pagination: {
      defaultPageSize: 25,
      pageSizeOptions: [10, 25, 50, 100],
    },
    notifications: {
      position: 'top-right',
      maxVisible: 5,
      defaultDuration: 5,
    },
  },
  
  PERFORMANCE: {
    cacheEnabled: true,
    cacheTTL: 300, // 5 minutes
    lazyLoading: true,
    prefetching: true,
    compression: true,
    bundleAnalysis: false,
  },
  
  MONITORING: {
    enabled: true,
    errorReporting: true,
    performanceMonitoring: true,
    userAnalytics: false,
    debugLogging: false,
    logLevel: 'info',
  },
  
  TENANT_OVERRIDES: {},
};

// Configuration store
const useConfigStore = create<ConfigStore>()(
  persist(
    (set, get) => ({
      environment: null,
      runtime: null,
      tenantConfig: null,
      isLoading: false,
      error: null,
      lastSync: null,
      cache: new Map(),

      loadEnvironmentConfig: (config) => {
        const mergedConfig = { ...defaultEnvironmentConfig, ...config };
        set({ environment: mergedConfig });
      },

      loadRuntimeConfig: async () => {
        try {
          set({ isLoading: true, error: null });
          
          // In a real implementation, this would fetch from a remote API
          const response = await fetch('/api/config/runtime');
          
          if (response.ok) {
            const runtimeConfig = await response.json();
            set({ runtime: runtimeConfig, lastSync: new Date() });
          } else {
            // Use default runtime config if remote fetch fails
            set({
              runtime: {
                lastUpdated: new Date(),
                version: '1.0.0',
                maintenanceMode: false,
                featureFlags: {},
                experimentalFeatures: {},
                remoteConfigVersion: 'local',
              },
              lastSync: new Date(),
            });
          }
        } catch (error) {
          console.warn('Failed to load runtime config, using defaults:', error);
          set({
            runtime: {
              lastUpdated: new Date(),
              version: '1.0.0',
              maintenanceMode: false,
              featureFlags: {},
              experimentalFeatures: {},
              remoteConfigVersion: 'local',
            },
            error: error instanceof Error ? error.message : 'Failed to load runtime config',
            lastSync: new Date(),
          });
        } finally {
          set({ isLoading: false });
        }
      },

      loadTenantConfig: async (tenantId) => {
        try {
          set({ isLoading: true, error: null });
          
          const response = await fetch(`/api/config/tenant/${tenantId}`);
          
          if (response.ok) {
            const tenantConfig = await response.json();
            set({ tenantConfig });
          }
        } catch (error) {
          console.warn('Failed to load tenant config:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to load tenant config' 
          });
        } finally {
          set({ isLoading: false });
        }
      },

      updateRuntimeConfig: (updates) => {
        set((state) => ({
          runtime: state.runtime ? { ...state.runtime, ...updates } : null,
        }));
      },

      updateFeatureFlag: (flag, enabled) => {
        set((state) => ({
          runtime: state.runtime
            ? {
                ...state.runtime,
                featureFlags: { ...state.runtime.featureFlags, [flag]: enabled },
              }
            : null,
        }));
      },

      toggleMaintenanceMode: (enabled, message) => {
        get().updateRuntimeConfig({
          maintenanceMode: enabled,
          announcementBanner: enabled
            ? {
                message: message || 'System maintenance is in progress.',
                type: 'warning',
                dismissible: false,
              }
            : undefined,
        });
      },

      isFeatureEnabled: (feature) => {
        const { environment, runtime } = get();
        
        // Check runtime feature flags first
        if (runtime?.featureFlags?.[feature] !== undefined) {
          return runtime.featureFlags[feature];
        }
        
        // Check environment features
        return environment?.FEATURES?.[feature as keyof typeof environment.FEATURES] || false;
      },

      getFeatureConfig: (feature, defaultValue = null) => {
        const { runtime } = get();
        return runtime?.experimentalFeatures?.[feature] ?? defaultValue;
      },

      getConfig: (path, defaultValue = null) => {
        const { environment, runtime, tenantConfig } = get();
        const pathParts = path.split('.');
        
        // Check tenant config first
        let value = getNestedValue(tenantConfig, pathParts);
        if (value !== undefined) return value;
        
        // Check runtime config
        value = getNestedValue(runtime, pathParts);
        if (value !== undefined) return value;
        
        // Check environment config
        value = getNestedValue(environment, pathParts);
        if (value !== undefined) return value;
        
        return defaultValue;
      },

      setConfig: (path, value) => {
        // This would typically update the runtime config
        // and potentially sync with a remote configuration service
        console.log('Setting config:', path, value);
      },

      setCacheValue: (key, value, ttl = 300) => {
        const { cache } = get();
        const newCache = new Map(cache);
        newCache.set(key, {
          value,
          expiresAt: Date.now() + (ttl * 1000),
        });
        set({ cache: newCache });
      },

      getCacheValue: (key) => {
        const { cache } = get();
        const cached = cache.get(key);
        
        if (!cached) return null;
        
        if (cached.expiresAt < Date.now()) {
          // Remove expired entry
          const newCache = new Map(cache);
          newCache.delete(key);
          set({ cache: newCache });
          return null;
        }
        
        return cached.value;
      },

      clearCache: () => {
        set({ cache: new Map() });
      },

      syncWithRemote: async () => {
        await get().loadRuntimeConfig();
      },

      reset: () => {
        set({
          environment: null,
          runtime: null,
          tenantConfig: null,
          isLoading: false,
          error: null,
          lastSync: null,
          cache: new Map(),
        });
      },
    }),
    {
      name: 'dotmac-config',
      storage: createJSONStorage(() => ({
        getItem: (name) => secureStorage.getItem(name),
        setItem: (name, value) => secureStorage.setItem(name, value),
        removeItem: (name) => secureStorage.removeItem(name),
      })),
      partialize: (state) => ({
        // Only persist environment and runtime config
        environment: state.environment,
        runtime: state.runtime,
        lastSync: state.lastSync,
        // Don't persist cache or tenant-specific config
      }),
      version: 1,
    }
  )
);

// Context interface
interface ConfigContextValue {
  // Configuration access
  config: EnvironmentConfig | null;
  runtimeConfig: RuntimeConfig | null;
  isLoading: boolean;
  error: string | null;
  
  // Feature flags
  isFeatureEnabled: (feature: string) => boolean;
  getFeatureConfig: <T = any>(feature: string, defaultValue?: T) => T;
  
  // Configuration utilities
  getConfig: <T = any>(path: string, defaultValue?: T) => T;
  
  // Runtime management
  updateFeatureFlag: (flag: string, enabled: boolean) => void;
  toggleMaintenanceMode: (enabled: boolean, message?: string) => void;
  
  // Cache utilities
  setCacheValue: (key: string, value: any, ttl?: number) => void;
  getCacheValue: <T = any>(key: string) => T | null;
  clearCache: () => void;
  
  // Sync utilities
  syncWithRemote: () => Promise<void>;
  lastSync: Date | null;
}

// Create context
const ConfigContext = createContext<ConfigContextValue | null>(null);

// Hook to use config context
export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
};

// Provider props
interface ConfigProviderProps {
  children: ReactNode;
  initialConfig?: Partial<EnvironmentConfig>;
  enableRemoteSync?: boolean;
  syncInterval?: number; // minutes
  tenantId?: string;
}

export function ConfigProvider({
  children,
  initialConfig,
  enableRemoteSync = true,
  syncInterval = 15,
  tenantId,
}: ConfigProviderProps) {
  const store = useConfigStore();

  // Initialize environment configuration
  useEffect(() => {
    if (initialConfig) {
      store.loadEnvironmentConfig(initialConfig);
    }
  }, [initialConfig, store]);

  // Load runtime configuration on mount
  useEffect(() => {
    store.loadRuntimeConfig();
  }, [store]);

  // Load tenant-specific configuration
  useEffect(() => {
    if (tenantId) {
      store.loadTenantConfig(tenantId);
    }
  }, [tenantId, store]);

  // Setup periodic sync with remote
  useEffect(() => {
    if (!enableRemoteSync || syncInterval <= 0) return;

    const interval = setInterval(() => {
      store.syncWithRemote();
    }, syncInterval * 60 * 1000);

    return () => clearInterval(interval);
  }, [enableRemoteSync, syncInterval, store]);

  // Cache cleanup
  useEffect(() => {
    const cleanup = setInterval(() => {
      // Clean up expired cache entries
      const now = Date.now();
      const newCache = new Map();
      
      for (const [key, cached] of store.cache.entries()) {
        if (cached.expiresAt > now) {
          newCache.set(key, cached);
        }
      }
      
      if (newCache.size !== store.cache.size) {
        useConfigStore.setState({ cache: newCache });
      }
    }, 5 * 60 * 1000); // Every 5 minutes

    return () => clearInterval(cleanup);
  }, [store.cache]);

  // Context value
  const contextValue: ConfigContextValue = useMemo(
    () => ({
      config: store.environment,
      runtimeConfig: store.runtime,
      isLoading: store.isLoading,
      error: store.error,
      
      isFeatureEnabled: store.isFeatureEnabled,
      getFeatureConfig: store.getFeatureConfig,
      getConfig: store.getConfig,
      
      updateFeatureFlag: store.updateFeatureFlag,
      toggleMaintenanceMode: store.toggleMaintenanceMode,
      
      setCacheValue: store.setCacheValue,
      getCacheValue: store.getCacheValue,
      clearCache: store.clearCache,
      
      syncWithRemote: store.syncWithRemote,
      lastSync: store.lastSync,
    }),
    [store]
  );

  return (
    <ConfigContext.Provider value={contextValue}>
      {children}
    </ConfigContext.Provider>
  );
}

// Utility function to get nested object values
function getNestedValue(obj: any, path: string[]): any {
  if (!obj) return undefined;
  
  let current = obj;
  for (const key of path) {
    if (current[key] === undefined) return undefined;
    current = current[key];
  }
  return current;
}

export { ConfigProvider, useConfig };