/**
 * Comprehensive State Management Exports
 * Centralized access to all application stores with typed interfaces
 */

export * from './authStore';
export * from './tenantStore';
export * from './appStore';
export * from './notificationsStore';

// Re-export store hooks for convenience
export { useAuthStore } from './authStore';
export { useTenantStore } from './tenantStore';
export { useAppStore } from './appStore';
export { useNotificationsStore } from './notificationsStore';

// Re-export types for external use
export type {
  // Auth store types
  AuthState,
  AuthActions,
} from './authStore';

export type {
  // Tenant store types
  TenantState,
  TenantContext,
  TenantPermissions,
} from './tenantStore';

export type {
  // App store types
  FilterState,
  PaginationState,
  SelectionState,
  LoadingState,
  UIState,
  MetricsState,
} from './appStore';

export type {
  // Notifications store types
  NotificationData,
  NotificationAction,
  NotificationFilters,
  NotificationPreferences,
  RealtimeConnectionState,
} from './notificationsStore';
