/**
 * Design System Utilities
 * Helper functions and utilities for consistent styling
 */

import { cn } from '@dotmac/primitives/utils';
import { colors, spacing, borderRadius, shadows } from './tokens';

// Color utilities
export const colorUtils = {
  // Get color value by path (e.g., 'primary.500')
  getColor: (path: string): string => {
    const keys = path.split('.');
    let value: any = colors;

    for (const key of keys) {
      value = value[key];
      if (value === undefined) {
        console.warn(`Color path "${path}" not found`);
        return colors.gray[500];
      }
    }

    return value;
  },

  // Get semantic colors for status
  getStatusColor: (status: string): string => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'paid':
      case 'completed':
      case 'success':
        return colors.success[500];
      case 'pending':
      case 'processing':
      case 'warning':
        return colors.warning[500];
      case 'error':
      case 'failed':
      case 'overdue':
      case 'suspended':
        return colors.error[500];
      case 'info':
      case 'draft':
        return colors.info[500];
      default:
        return colors.gray[500];
    }
  },

  // Check color contrast ratio
  getContrastRatio: (color1: string, color2: string): number => {
    // Simplified contrast ratio calculation
    // In production, you'd use a proper color library
    const getLuminance = (color: string): number => {
      // Very basic luminance calculation for hex colors
      const hex = color.replace('#', '');
      const r = parseInt(hex.substr(0, 2), 16) / 255;
      const g = parseInt(hex.substr(2, 2), 16) / 255;
      const b = parseInt(hex.substr(4, 2), 16) / 255;

      const [rs, gs, bs] = [r, g, b].map((c) => {
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });

      return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    };

    const l1 = getLuminance(color1);
    const l2 = getLuminance(color2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);

    return (lighter + 0.05) / (darker + 0.05);
  },

  // Generate color variations
  generateColorScale: (baseColor: string, steps: number = 9) => {
    // This is a simplified implementation
    // In production, you'd use a proper color library like chroma-js
    const scale: Record<number, string> = {};
    const baseStep = Math.floor(steps / 2);

    for (let i = 0; i < steps; i++) {
      const weight = (i + 1) * 100;
      scale[weight] = baseColor; // Simplified - would generate actual variations
    }

    return scale;
  },
};

// Spacing utilities
export const spacingUtils = {
  // Get spacing value by key
  getSpacing: (key: keyof typeof spacing): string => {
    return spacing[key];
  },

  // Generate responsive spacing
  getResponsiveSpacing: (base: keyof typeof spacing, scale: number = 1.5) => {
    const baseValue = parseFloat(spacing[base]);
    return {
      sm: `${baseValue}rem`,
      md: `${baseValue * scale}rem`,
      lg: `${baseValue * scale * scale}rem`,
    };
  },

  // Convert spacing to CSS custom properties
  toCSSCustomProperties: () => {
    return Object.entries(spacing).reduce(
      (acc, [key, value]) => {
        acc[`--spacing-${key}`] = value;
        return acc;
      },
      {} as Record<string, string>
    );
  },
};

// Typography utilities
export const typographyUtils = {
  // Generate font size with line height
  getFontSize: (size: string) => {
    const sizeMap: Record<string, { fontSize: string; lineHeight: string }> = {
      xs: { fontSize: '0.75rem', lineHeight: '1rem' },
      sm: { fontSize: '0.875rem', lineHeight: '1.25rem' },
      base: { fontSize: '1rem', lineHeight: '1.5rem' },
      lg: { fontSize: '1.125rem', lineHeight: '1.75rem' },
      xl: { fontSize: '1.25rem', lineHeight: '1.75rem' },
      '2xl': { fontSize: '1.5rem', lineHeight: '2rem' },
      '3xl': { fontSize: '1.875rem', lineHeight: '2.25rem' },
      '4xl': { fontSize: '2.25rem', lineHeight: '2.5rem' },
    };

    return sizeMap[size] || sizeMap.base;
  },

  // Generate responsive typography
  getResponsiveTypography: (baseSizes: Record<string, string>) => {
    return Object.entries(baseSizes).reduce(
      (acc, [breakpoint, size]) => {
        acc[breakpoint] = typographyUtils.getFontSize(size);
        return acc;
      },
      {} as Record<string, { fontSize: string; lineHeight: string }>
    );
  },

  // Truncate text utilities
  getTruncateClass: (lines: number = 1): string => {
    if (lines === 1) {
      return 'truncate';
    }
    return `line-clamp-${lines}`;
  },
};

// Component variant utilities
export const variantUtils = {
  // Button variants
  button: {
    variant: {
      primary: cn(
        'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
        'border-transparent'
      ),
      secondary: cn(
        'bg-white text-gray-900 hover:bg-gray-50 focus:ring-primary-500',
        'border-gray-300'
      ),
      outline: cn(
        'bg-transparent text-primary-600 hover:bg-primary-50 focus:ring-primary-500',
        'border-primary-600'
      ),
      ghost: cn(
        'bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-500',
        'border-transparent'
      ),
      danger: cn('bg-red-600 text-white hover:bg-red-700 focus:ring-red-500', 'border-transparent'),
    },

    size: {
      sm: cn('h-8 px-3 text-sm'),
      base: cn('h-10 px-4 text-base'),
      lg: cn('h-12 px-6 text-lg'),
    },
  },

  // Input variants
  input: {
    variant: {
      default: cn(
        'bg-white border-gray-300 text-gray-900',
        'focus:ring-primary-500 focus:border-primary-500',
        'placeholder:text-gray-400'
      ),
      error: cn(
        'bg-white border-red-300 text-gray-900',
        'focus:ring-red-500 focus:border-red-500',
        'placeholder:text-gray-400'
      ),
    },

    size: {
      sm: cn('h-8 px-3 text-sm'),
      base: cn('h-10 px-3 text-base'),
      lg: cn('h-12 px-4 text-lg'),
    },
  },

  // Badge/Status variants
  badge: {
    variant: {
      default: cn('bg-gray-100 text-gray-800'),
      primary: cn('bg-primary-100 text-primary-800'),
      success: cn('bg-green-100 text-green-800'),
      warning: cn('bg-yellow-100 text-yellow-800'),
      danger: cn('bg-red-100 text-red-800'),
      info: cn('bg-blue-100 text-blue-800'),
    },

    size: {
      sm: cn('px-2 py-1 text-xs'),
      base: cn('px-3 py-1 text-sm'),
      lg: cn('px-4 py-2 text-base'),
    },
  },
};

// Animation utilities
export const animationUtils = {
  // Fade animations
  fadeIn: cn('animate-in fade-in duration-200'),
  fadeOut: cn('animate-out fade-out duration-200'),

  // Slide animations
  slideInFromTop: cn('animate-in slide-in-from-top-2 duration-300'),
  slideInFromBottom: cn('animate-in slide-in-from-bottom-2 duration-300'),
  slideInFromLeft: cn('animate-in slide-in-from-left-2 duration-300'),
  slideInFromRight: cn('animate-in slide-in-from-right-2 duration-300'),

  // Scale animations
  scaleIn: cn('animate-in zoom-in-95 duration-200'),
  scaleOut: cn('animate-out zoom-out-95 duration-200'),

  // Combined animations
  modalEnter: cn('animate-in fade-in zoom-in-95 duration-200'),
  modalExit: cn('animate-out fade-out zoom-out-95 duration-200'),

  dropdownEnter: cn('animate-in fade-in slide-in-from-top-2 duration-200'),
  dropdownExit: cn('animate-out fade-out slide-out-to-top-2 duration-200'),
};

// Layout utilities
export const layoutUtils = {
  // Container utilities
  container: {
    sm: cn('max-w-sm mx-auto px-4'),
    md: cn('max-w-md mx-auto px-4'),
    lg: cn('max-w-lg mx-auto px-4'),
    xl: cn('max-w-xl mx-auto px-4'),
    '2xl': cn('max-w-2xl mx-auto px-4'),
    '3xl': cn('max-w-3xl mx-auto px-4'),
    '4xl': cn('max-w-4xl mx-auto px-4'),
    '5xl': cn('max-w-5xl mx-auto px-4'),
    '6xl': cn('max-w-6xl mx-auto px-4'),
    '7xl': cn('max-w-7xl mx-auto px-4'),
    full: cn('w-full px-4'),
  },

  // Grid utilities
  grid: {
    responsive: cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'),
    cards: cn('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'),
    table: cn('grid gap-1 divide-y divide-gray-200'),
  },

  // Flex utilities
  flex: {
    center: cn('flex items-center justify-center'),
    between: cn('flex items-center justify-between'),
    start: cn('flex items-center justify-start'),
    end: cn('flex items-center justify-end'),
    col: cn('flex flex-col'),
    colCenter: cn('flex flex-col items-center justify-center'),
  },
};

// Accessibility utilities
export const a11yUtils = {
  // Screen reader only content
  srOnly: cn('sr-only'),

  // Skip links
  skipLink: cn(
    'absolute left-1/2 top-4 z-50 -translate-x-1/2 -translate-y-full',
    'rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-900',
    'shadow-lg ring-1 ring-gray-300',
    'focus:translate-y-0 focus:ring-2 focus:ring-primary-500'
  ),

  // Focus rings
  focusRing: cn('focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'),

  focusRingInset: cn('focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset'),

  // High contrast mode utilities
  highContrast: {
    border: cn('border-2 border-gray-900'),
    text: cn('text-gray-900'),
    background: cn('bg-white'),
  },
};

// Responsive utilities
export const responsiveUtils = {
  // Show/hide at different breakpoints
  show: {
    sm: cn('hidden sm:block'),
    md: cn('hidden md:block'),
    lg: cn('hidden lg:block'),
    xl: cn('hidden xl:block'),
  },

  hide: {
    sm: cn('block sm:hidden'),
    md: cn('block md:hidden'),
    lg: cn('block lg:hidden'),
    xl: cn('block xl:hidden'),
  },

  // Responsive text alignment
  textAlign: {
    responsive: cn('text-center sm:text-left'),
    center: cn('text-center'),
    left: cn('text-left'),
    right: cn('text-right'),
  },
};

// Export all utilities
export const designUtils = {
  cn,
  colorUtils,
  spacingUtils,
  typographyUtils,
  variantUtils,
  animationUtils,
  layoutUtils,
  a11yUtils,
  responsiveUtils,
};
