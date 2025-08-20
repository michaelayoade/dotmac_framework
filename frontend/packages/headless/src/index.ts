/**
 * DotMac Headless UI Package
 *
 * Provides headless hooks and logic for building DotMac platform interfaces
 */

// Re-export query client utilities
export { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// API Client and Configuration
export * from './api';
// Components
export * from './components';
export * from './config/ConfigProvider';
// Configuration and Theming
export * from './config/framework.config';
export * from './config/ThemeProvider';
export * from './config/theme.config';
// Hooks
export * from './hooks';
export * from './hooks/useFormatting';
// Stores
export * from './stores';
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
} from './types';
// Security utilities
export * from './utils';
// CSP utilities and nonce provider
export * from './utils/csp';
export * from './components/NonceProvider';
