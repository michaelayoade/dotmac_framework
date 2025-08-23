/**
 * DotMac Headless UI Package
 *
 * Provides headless hooks and logic for building DotMac platform interfaces
 */

// Re-export query client utilities
export { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// API Client and Configuration
export * from './api';
// Components (selective exports to avoid conflicts)
export {
  StandardErrorBoundary,
  withErrorBoundary as withStandardErrorBoundary,
} from './components/StandardErrorBoundary';
export { 
  ErrorBoundary,
  withErrorBoundary as withLegacyErrorBoundary,
} from './components/ErrorBoundary';
export * from './components/ErrorFallbacks';
export * from './components/MFAComponents';
export * from './components/NotificationSystem';
export * from './components/RouteGuard';
export * from './components/ISPTenantProvider';
export * from './components/RealTimeProvider';
export * from './components/RealTimeStatus';

// State Management Providers
export * from './components/AuthProvider';
export * from './components/ConfigProvider';
// Configuration and Theming
export * from './config/framework.config';
export * from './config/ThemeProvider';
export * from './config/theme.config';
// Hooks (excluding conflict-prone exports)
export {
  useApiData,
  useCachedData,
  useAuth,
  useBusinessWorkflow,
  useFormatting,
  useMFA,
  useOfflineSync,
  usePerformanceMonitoring,
  usePermissions,
  usePortalAuth,
  usePortalIdAuth,
  useISPModules,
  useISPTenant,
  useISPTenantProvider,
  useWebSocket,
  useRealTimeSync,
  useRouteProtection,
  useAppState,
} from './hooks';

// Notification hooks
export {
  useNotifications,
  useApiErrorNotifications,
  useErrorNotifications,
  useGlobalErrorListener,
  useNotificationStore,
  type NotificationType,
  type Notification,
} from './hooks/useNotifications';

// Standard error handling (preferred)
export {
  useStandardErrorHandler,
  useApiErrorHandler as useStandardApiErrorHandler,
  useFormErrorHandler,
  useDataLoadingErrorHandler,
  useRealtimeErrorHandler,
  useUploadErrorHandler,
  configureGlobalErrorHandling as configureStandardErrorHandling,
  getGlobalErrorConfig,
  type UseStandardErrorHandlerOptions,
  type UseStandardErrorHandlerReturn,
} from './hooks/useStandardErrorHandler';

// Legacy error handling (for backward compatibility)
export {
  useErrorHandler as useLegacyErrorHandler,
  useErrorBoundary as useLegacyErrorBoundary,
  useApiErrorHandler as useLegacyApiErrorHandler,
  setGlobalErrorHandler,
  type ErrorInfo as LegacyErrorInfo,
  type ErrorHandlerOptions as LegacyErrorHandlerOptions,
  type UseErrorHandlerResult as LegacyUseErrorHandlerResult,
} from './hooks/useErrorHandler';
// State Management Stores and Orchestration
export * from './stores';
export * from './stores/stateManager';

// State Management Utilities
export {
  getStateManager,
  initializeStateManagement,
  resetStateManagement,
  type StateManagerInterface,
} from './stores/stateManager';
// Types (exclude conflicting types that are exported from hooks)
export type {
  Address,
  ApiError,
  ApiResponse,
  AuthContext,
  BillingInfo,
  ChatAttachment,
  ChatMessage,
  ChatSession,
  Customer,
  CustomerService,
  DashboardMetrics,
  DeviceMetrics,
  Invoice,
  InvoiceItem,
  LoginFlow,
  NetworkAlert,
  NetworkDevice,
  PaginatedResponse,
  PortalConfig,
  PortalType,
  QueryParams,
  ServicePlan,
  Tenant,
  User,
  // Portal ID Authentication Types
  PortalAccount,
  PortalSession,
  PortalLoginCredentials,
  PortalAuthResponse,
  PortalAuthError,
  CustomerData,
  TechnicianData,
  ResellerData,
  // ISP Tenant Types
  ISPTenant,
  TenantUser,
  TenantSession,
  TenantPermissions,
  TenantBranding,
} from './types';
// Security utilities
export * from './utils';
// CSP utilities and nonce provider
export * from './utils/csp';
export * from './components/NonceProvider';
// Error handling utilities (specific exports to avoid conflicts)
export {
  ISPError,
  classifyError,
  shouldRetry,
  calculateRetryDelay,
  logError,
  deduplicateError,
  DEFAULT_ERROR_CONFIG,
  configureGlobalErrorHandling as configureISPErrorHandling,
  type ErrorHandlingConfig,
  type ErrorSeverity,
  type ErrorCategory,
  type ErrorMetadata,
} from './utils/errorUtils';

// Error handling components
export * from './components/StandardErrorBoundary';
export * from './providers/ErrorHandlingProvider';
