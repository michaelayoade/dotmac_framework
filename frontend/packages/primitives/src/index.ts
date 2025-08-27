/**
 * @dotmac/primitives - Unstyled, composable UI primitives for DotMac platform
 *
 * This package provides headless UI components that can be styled with any design system.
 * Components are built with accessibility, composition, and flexibility in mind.
 */

export { Slot } from '@radix-ui/react-slot';
// Re-export common utilities
export { cva, type VariantProps } from 'class-variance-authority';
export { clsx } from 'clsx';
// Export what's actually implemented
export * from './composition';
export * from './data-display';
// Export table components explicitly
export { 
  Table, 
  TableCell, 
  TableFooter, 
  TableHeader, 
  TableRow, 
  TableBody,
  TableCaption,
  TableHead
} from './data-display/TableComponents';
export * from './error';
export * from './feedback';
export * from './forms';
export * from './layout';
// Export Modal explicitly
export { VirtualizedTable } from './performance/VirtualizedTable';
export { Modal } from './layout/Modal';
export * from './navigation';
// Export navigation hooks specifically
export { useNavigation } from './navigation/Navigation';
// Export toast hooks from notification system
export { useToast } from './feedback/NotificationSystem';
// Export modal hooks
export { useModal, useModalContext } from './feedback/hooks';
// Export notification provider
export { NotificationProvider } from './feedback/NotificationSystem';
export * from './theming';
export * from './types';
export * from './ui';
// Export utils excluding conflicting form utilities
export * from './utils/bundle-optimization';
export * from './utils/performance';
export * from './utils/ssr';
export * from './utils/accessibility';

// Performance monitoring
export * from './performance';
// Note: createValidationRules and validationPatterns exported from forms

// Enhanced ISP-specific components (security-hardened & WCAG 2.1 AA compliant)
export * from './charts/InteractiveChart';
export * from './indicators/StatusIndicators';

// Export ErrorBoundary explicitly to avoid conflicts with error/ErrorBoundary
export { ErrorBoundary as ComponentErrorBoundary } from './components/ErrorBoundary';
export * from './utils/security';
// Export a11y utilities with specific exports to avoid conflicts
export { 
  announceToScreenReader, 
  generateChartDescription,
  useKeyboardNavigation as useA11yKeyboardNavigation,
  ARIA_ROLES as ARIA_LABELS,
  ARIA_ROLES as A11Y_ROLES,
  ARIA_ROLES
} from './utils/a11y';
export * from './utils/a11y-testing';
export * from './types/chart';
export * from './types/status';
export * from './animations/Animations';
export * from './themes/ISPBrandTheme';
export * from './security/CSRFProtection';

// Version info
export const version = '1.0.0';

// Default configurations
export const defaultConfig = {
  toast: {
    duration: 5000,
    position: 'top-right' as const,
  },
  table: {
    pageSize: 10,
    showPagination: true,
  },
  chart: {
    responsive: true,
    height: 300,
  },
  form: {
    layout: 'vertical' as const,
    size: 'md' as const,
  },
  modal: {
    closeOnOverlayClick: true,
    closeOnEscape: true,
  },
} as const;
