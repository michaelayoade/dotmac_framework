// Loading Components
export {
  LoadingShell,
  TextLoadingSkeleton,
  CardLoadingSkeleton,
  TableLoadingSkeleton,
  ListLoadingSkeleton
} from './components/LoadingShell';

// Error Components
export {
  ErrorShell,
  NetworkErrorShell,
  NotFoundErrorShell,
  UnauthorizedErrorShell,
  ServerErrorShell
} from './components/ErrorShell';

// Error Boundaries
export {
  StandardErrorBoundary,
  PageErrorBoundary,
  SectionErrorBoundary,
  ComponentErrorBoundary,
  withErrorBoundary
} from './components/ErrorBoundary';

// PWA Components
export {
  OfflineDetector,
  useOnlineStatus
} from './pwa/OfflineDetector';

export {
  InstallPrompt,
  useInstallPrompt
} from './pwa/InstallPrompt';

// Performance Hooks
export {
  usePerformanceMonitor
} from './hooks/usePerformanceMonitor';

// Performance Utilities
export {
  preloadResource,
  prefetchResource,
  lazyLoadImage,
  measureBundleSize,
  monitorMemoryUsage,
  prioritizeCriticalResources,
  measureFunction,
  measureAsync,
  trackComponentRender,
  debounce,
  throttle,
  reportWebVitals,
  createLoadingStrategy
} from './utils/performance-helpers';

// Standard Components Bundle
export const StandardShells = {
  Loading: LoadingShell,
  Error: ErrorShell,
  TextSkeleton: TextLoadingSkeleton,
  CardSkeleton: CardLoadingSkeleton,
  TableSkeleton: TableLoadingSkeleton,
  ListSkeleton: ListLoadingSkeleton,
  NetworkError: NetworkErrorShell,
  NotFoundError: NotFoundErrorShell,
  UnauthorizedError: UnauthorizedErrorShell,
  ServerError: ServerErrorShell,
};

// Error Boundaries Bundle
export const ErrorBoundaries = {
  Page: PageErrorBoundary,
  Section: SectionErrorBoundary,
  Component: ComponentErrorBoundary,
  Standard: StandardErrorBoundary,
  withBoundary: withErrorBoundary,
};

// PWA Features Bundle
export const PWAFeatures = {
  OfflineDetector,
  InstallPrompt,
  useOnlineStatus,
  useInstallPrompt,
};