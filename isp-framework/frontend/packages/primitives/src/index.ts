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
export * from './data-display';
export * from './error';
export * from './feedback';
export * from './forms';
export * from './layout';
export * from './navigation';
export * from './theming';
export * from './types';
export * from './ui';
export * from './utils';

// Enhanced ISP-specific components
export * from './charts/InteractiveChart';
export * from './indicators/StatusIndicators';
export * from './animations/Animations';
export * from './themes/ISPBrandTheme';

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
