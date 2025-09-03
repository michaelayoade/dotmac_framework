// Migrated to use unified ErrorBoundary from @dotmac/providers
export { ErrorBoundary } from '@dotmac/providers';

// Legacy exports for backward compatibility
export const withErrorBoundary = ErrorBoundary;
export const AsyncErrorBoundary = ErrorBoundary;
export const RouteErrorBoundary = ErrorBoundary;
export const ComponentErrorBoundary = ErrorBoundary;
