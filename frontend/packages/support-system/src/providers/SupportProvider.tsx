/**
 * Universal Support Provider
 * Production-ready context provider for support and communication systems
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useSupportOperations, type SupportOperationsConfig, type UseSupportOperationsReturn } from '../hooks/useSupportOperations';
import type { PortalType } from '../types';

// ===== CONTEXT INTERFACES =====

interface SupportContextType extends UseSupportOperationsReturn {
  // Additional context-specific functionality
  preferences: SupportPreferences;
  updatePreferences: (prefs: Partial<SupportPreferences>) => void;

  // UI State
  ui: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    timezone: string;
    compactMode: boolean;
  };

  // Feature flags
  features: {
    ticketing: boolean;
    liveChat: boolean;
    knowledgeBase: boolean;
    fileUpload: boolean;
    videoCall: boolean;
    phoneSupport: boolean;
    analytics: boolean;
    realtime: boolean;
  };

  // Portal-specific settings
  portalConfig: {
    type: PortalType;
    permissions: string[];
    allowedActions: string[];
    maxFileSize: number;
    supportedFormats: string[];
  };
}

interface SupportPreferences {
  notifications: {
    email: boolean;
    push: boolean;
    sound: boolean;
  };
  chat: {
    showTypingIndicator: boolean;
    enableEmojis: boolean;
    autoTranslate: boolean;
  };
  tickets: {
    defaultPriority: string;
    enableAutoAssign: boolean;
    showInternalNotes: boolean;
  };
  ui: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    compactMode: boolean;
    showAvatars: boolean;
  };
}

interface SupportProviderProps {
  children: React.ReactNode;
  portalType: PortalType;
  apiBaseUrl: string;
  config?: Partial<SupportOperationsConfig>;
  queryClient?: QueryClient;
  initialPreferences?: Partial<SupportPreferences>;
  enableErrorBoundary?: boolean;
  enablePerformanceMonitoring?: boolean;
}

// ===== CONTEXT CREATION =====

const SupportContext = createContext<SupportContextType | null>(null);

// ===== ERROR BOUNDARY =====

interface SupportErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: any;
}

class SupportErrorBoundary extends React.Component<
  { children: React.ReactNode; onError?: (error: Error, errorInfo: any) => void },
  SupportErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): SupportErrorBoundaryState {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    this.setState({ errorInfo });

    if (process.env.NODE_ENV === 'development') {
      console.error('[SupportProvider] Error caught:', error, errorInfo);
    }

    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-64 p-8 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-center">
            <div className="mb-4">
              <svg className="mx-auto h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-red-900 mb-2">Support System Error</h3>
            <p className="text-red-700 mb-4">
              We're experiencing technical difficulties with the support system.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Refresh Page
            </button>
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-sm font-medium text-red-800">
                  Error Details (Development)
                </summary>
                <pre className="mt-2 text-xs text-red-700 bg-red-100 p-3 rounded overflow-auto max-h-32">
                  {this.state.error?.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// ===== DEFAULT CONFIGURATIONS =====

const getDefaultPreferences = (portalType: PortalType): SupportPreferences => ({
  notifications: {
    email: true,
    push: portalType !== 'customer', // Push notifications for staff only
    sound: true,
  },
  chat: {
    showTypingIndicator: true,
    enableEmojis: portalType === 'customer',
    autoTranslate: false,
  },
  tickets: {
    defaultPriority: 'medium',
    enableAutoAssign: portalType !== 'customer',
    showInternalNotes: portalType !== 'customer',
  },
  ui: {
    theme: 'auto',
    language: 'en',
    compactMode: false,
    showAvatars: true,
  },
});

const getPortalFeatures = (portalType: PortalType) => {
  const baseFeatures = {
    ticketing: true,
    liveChat: true,
    knowledgeBase: true,
    fileUpload: true,
    videoCall: false,
    phoneSupport: false,
    analytics: false,
    realtime: true,
  };

  switch (portalType) {
    case 'customer':
      return {
        ...baseFeatures,
        videoCall: true,
        phoneSupport: true,
      };

    case 'admin':
    case 'agent':
      return {
        ...baseFeatures,
        analytics: true,
        videoCall: true,
        phoneSupport: true,
      };

    case 'management':
      return {
        ...baseFeatures,
        analytics: true,
        videoCall: true,
        phoneSupport: true,
      };

    case 'reseller':
      return {
        ...baseFeatures,
        analytics: false,
        videoCall: false,
        phoneSupport: false,
      };

    default:
      return baseFeatures;
  }
};

const getPortalConfig = (portalType: PortalType) => {
  const baseConfig = {
    type: portalType,
    permissions: ['read'],
    allowedActions: ['view'],
    maxFileSize: 10 * 1024 * 1024, // 10MB
    supportedFormats: ['jpg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt'],
  };

  switch (portalType) {
    case 'customer':
      return {
        ...baseConfig,
        permissions: ['read', 'create', 'update_own'],
        allowedActions: ['create_ticket', 'reply_ticket', 'start_chat', 'view_kb', 'upload_file'],
        maxFileSize: 25 * 1024 * 1024, // 25MB for customers
      };

    case 'admin':
    case 'agent':
      return {
        ...baseConfig,
        permissions: ['read', 'create', 'update', 'delete', 'assign'],
        allowedActions: ['manage_tickets', 'manage_chat', 'manage_kb', 'view_analytics', 'manage_users'],
        maxFileSize: 100 * 1024 * 1024, // 100MB for staff
      };

    case 'management':
      return {
        ...baseConfig,
        permissions: ['read', 'create', 'update', 'delete', 'assign', 'admin'],
        allowedActions: ['full_access'],
        maxFileSize: 500 * 1024 * 1024, // 500MB for management
      };

    case 'reseller':
      return {
        ...baseConfig,
        permissions: ['read', 'create', 'update_own'],
        allowedActions: ['create_ticket', 'view_tickets', 'manage_customers'],
        maxFileSize: 10 * 1024 * 1024, // 10MB for resellers
      };

    default:
      return baseConfig;
  }
};

// ===== INTERNAL PROVIDER COMPONENT =====

function SupportProviderInternal({
  children,
  portalType,
  apiBaseUrl,
  config = {},
  initialPreferences = {},
  enablePerformanceMonitoring = true
}: Omit<SupportProviderProps, 'queryClient' | 'enableErrorBoundary'>) {

  const [preferences, setPreferences] = useState<SupportPreferences>(() => ({
    ...getDefaultPreferences(portalType),
    ...initialPreferences
  }));

  const supportConfig: SupportOperationsConfig = useMemo(() => ({
    portalType,
    baseUrl: apiBaseUrl,
    apiVersion: config.apiVersion || '/api/v1',
    timeout: config.timeout || 30000,
    retryAttempts: config.retryAttempts || 3,
    enableRealtime: config.enableRealtime !== false,
    enableCaching: config.enableCaching !== false,
    cacheTimeout: config.cacheTimeout || 5 * 60 * 1000,
    enableOffline: config.enableOffline || false,
    features: {
      ...getPortalFeatures(portalType),
      ...config.features
    }
  }), [portalType, apiBaseUrl, config]);

  const operations = useSupportOperations(supportConfig);

  const features = useMemo(() =>
    getPortalFeatures(portalType),
    [portalType]
  );

  const portalConfig = useMemo(() =>
    getPortalConfig(portalType),
    [portalType]
  );

  const ui = useMemo(() => ({
    theme: preferences.ui.theme,
    language: preferences.ui.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    compactMode: preferences.ui.compactMode,
  }), [preferences.ui]);

  // Preference management
  const updatePreferences = useCallback((prefs: Partial<SupportPreferences>) => {
    setPreferences(prev => {
      const updated = {
        ...prev,
        ...prefs,
        notifications: { ...prev.notifications, ...prefs.notifications },
        chat: { ...prev.chat, ...prefs.chat },
        tickets: { ...prev.tickets, ...prefs.tickets },
        ui: { ...prev.ui, ...prefs.ui },
      };

      // Save to localStorage for persistence
      try {
        localStorage.setItem('support-preferences', JSON.stringify(updated));
      } catch (error) {
        if (process.env.NODE_ENV === 'development') {
          console.warn('[SupportProvider] Failed to save preferences to localStorage:', error);
        }
      }

      return updated;
    });
  }, []);

  // Load preferences from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('support-preferences');
      if (saved) {
        const parsed = JSON.parse(saved);
        setPreferences(prev => ({ ...prev, ...parsed }));
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.warn('[SupportProvider] Failed to load preferences from localStorage:', error);
      }
    }
  }, []);

  // Performance monitoring
  useEffect(() => {
    if (!enablePerformanceMonitoring) return;

    const performanceObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        if (entry.name.includes('support')) {
          if (process.env.NODE_ENV === 'development') {
            console.info(`[SupportProvider] Performance: ${entry.name} took ${entry.duration}ms`);
          }
        }
      });
    });

    performanceObserver.observe({ entryTypes: ['measure', 'navigation'] });

    return () => performanceObserver.disconnect();
  }, [enablePerformanceMonitoring]);

  const contextValue = useMemo<SupportContextType>(() => ({
    ...operations,
    preferences,
    updatePreferences,
    ui,
    features,
    portalConfig,
  }), [
    operations,
    preferences,
    updatePreferences,
    ui,
    features,
    portalConfig,
  ]);

  return (
    <SupportContext.Provider value={contextValue}>
      {children}
    </SupportContext.Provider>
  );
}

// ===== MAIN PROVIDER COMPONENT =====

export function SupportProvider({
  children,
  queryClient,
  enableErrorBoundary = true,
  ...props
}: SupportProviderProps) {
  const defaultQueryClient = useMemo(() => new QueryClient({
    defaultOptions: {
      queries: {
        retry: 3,
        retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
        staleTime: 5 * 60 * 1000, // 5 minutes
        cacheTime: 10 * 60 * 1000, // 10 minutes
      },
    },
  }), []);

  const client = queryClient || defaultQueryClient;

  const content = (
    <QueryClientProvider client={client}>
      <SupportProviderInternal {...props}>
        {children}
      </SupportProviderInternal>
    </QueryClientProvider>
  );

  if (enableErrorBoundary) {
    return (
      <SupportErrorBoundary>
        {content}
      </SupportErrorBoundary>
    );
  }

  return content;
}

// ===== CONTEXT HOOK =====

export function useSupport(): SupportContextType {
  const context = useContext(SupportContext);
  if (!context) {
    throw new Error('useSupport must be used within a SupportProvider');
  }
  return context;
}

// ===== CONVENIENCE HOOKS =====

export function useSupportTicketing() {
  const { tickets, state } = useSupport();
  return {
    ...tickets,
    isLoading: (operation = 'tickets') => state.isLoading(`tickets.${operation}`),
    hasError: (operation = 'tickets') => state.hasError(`tickets.${operation}`),
    getError: (operation = 'tickets') => state.getError(`tickets.${operation}`),
    clearError: (operation = 'tickets') => state.clearError(`tickets.${operation}`),
  };
}

export function useSupportChat() {
  const { chat, realtime, state } = useSupport();
  return {
    ...chat,
    ...realtime,
    isLoading: (operation = 'chat') => state.isLoading(`chat.${operation}`),
    hasError: (operation = 'chat') => state.hasError(`chat.${operation}`),
    getError: (operation = 'chat') => state.getError(`chat.${operation}`),
    clearError: (operation = 'chat') => state.clearError(`chat.${operation}`),
  };
}

export function useSupportKnowledgeBase() {
  const { knowledgeBase, state } = useSupport();
  return {
    ...knowledgeBase,
    isLoading: (operation = 'kb') => state.isLoading(`kb.${operation}`),
    hasError: (operation = 'kb') => state.hasError(`kb.${operation}`),
    getError: (operation = 'kb') => state.getError(`kb.${operation}`),
    clearError: (operation = 'kb') => state.clearError(`kb.${operation}`),
  };
}

export function useSupportFileUpload() {
  const { fileUpload, state, portalConfig } = useSupport();
  return {
    ...fileUpload,
    maxFileSize: portalConfig.maxFileSize,
    supportedFormats: portalConfig.supportedFormats,
    isLoading: (operation = 'files') => state.isLoading(`files.${operation}`),
    hasError: (operation = 'files') => state.hasError(`files.${operation}`),
    getError: (operation = 'files') => state.getError(`files.${operation}`),
    clearError: (operation = 'files') => state.clearError(`files.${operation}`),
  };
}

export function useSupportAnalytics() {
  const { analytics, features, state } = useSupport();

  if (!features.analytics) {
    throw new Error('Analytics feature is not enabled for this portal type');
  }

  return {
    ...analytics,
    isLoading: (operation = 'analytics') => state.isLoading(`analytics.${operation}`),
    hasError: (operation = 'analytics') => state.hasError(`analytics.${operation}`),
    getError: (operation = 'analytics') => state.getError(`analytics.${operation}`),
    clearError: (operation = 'analytics') => state.clearError(`analytics.${operation}`),
  };
}
