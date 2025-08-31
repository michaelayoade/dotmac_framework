/**
 * Theme Utilities
 * Utility functions and constants for portal-aware theming
 */

import { PortalTheme, PortalType, PORTAL_THEMES } from '../factories/templateFactories';

// Color palette utilities
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

export function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  r /= 255;
  g /= 255;
  b /= 255;
  
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h: number, s: number;
  const l = (max + min) / 2;

  if (max === min) {
    h = s = 0;
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
      default: h = 0;
    }
    h /= 6;
  }

  return { h: h * 360, s: s * 100, l: l * 100 };
}

export function adjustColor(hex: string, lightness: number, saturation?: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
  hsl.l = Math.max(0, Math.min(100, hsl.l + lightness));
  if (saturation !== undefined) {
    hsl.s = Math.max(0, Math.min(100, hsl.s + saturation));
  }
  
  return hslToHex(hsl.h, hsl.s, hsl.l);
}

function hslToHex(h: number, s: number, l: number): string {
  h = h / 360;
  s = s / 100;
  l = l / 100;
  
  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1/6) return p + (q - p) * 6 * t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
    return p;
  };

  let r: number, g: number, b: number;
  
  if (s === 0) {
    r = g = b = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }

  const toHex = (c: number): string => {
    const hex = Math.round(c * 255).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

// Color scheme generation
export function generateColorScheme(baseColor: string): {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  secondary: string;
  accent: string;
  success: string;
  warning: string;
  error: string;
  info: string;
} {
  return {
    primary: baseColor,
    primaryLight: adjustColor(baseColor, 20),
    primaryDark: adjustColor(baseColor, -20),
    secondary: adjustColor(baseColor, -10, -20),
    accent: adjustColor(baseColor, 10, 10),
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6'
  };
}

// Density-based spacing utilities
export function getDensitySpacing(density: 'compact' | 'comfortable' | 'spacious') {
  const baseSpacing = {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    '2xl': 48,
    '3xl': 64
  };

  const multiplier = {
    compact: 0.75,
    comfortable: 1,
    spacious: 1.25
  }[density];

  return Object.fromEntries(
    Object.entries(baseSpacing).map(([key, value]) => [
      key,
      Math.round(value * multiplier)
    ])
  );
}

// Component size utilities based on density
export function getDensityComponentSizes(density: 'compact' | 'comfortable' | 'spacious') {
  const sizes = {
    compact: {
      button: {
        sm: { height: 28, padding: '6px 12px', fontSize: '12px' },
        md: { height: 32, padding: '8px 16px', fontSize: '14px' },
        lg: { height: 36, padding: '10px 20px', fontSize: '16px' }
      },
      input: {
        sm: { height: 28, padding: '6px 12px', fontSize: '12px' },
        md: { height: 32, padding: '8px 12px', fontSize: '14px' },
        lg: { height: 36, padding: '10px 16px', fontSize: '16px' }
      },
      card: {
        padding: '12px',
        gap: '8px'
      }
    },
    comfortable: {
      button: {
        sm: { height: 32, padding: '8px 16px', fontSize: '13px' },
        md: { height: 40, padding: '12px 20px', fontSize: '14px' },
        lg: { height: 48, padding: '16px 24px', fontSize: '16px' }
      },
      input: {
        sm: { height: 32, padding: '8px 12px', fontSize: '13px' },
        md: { height: 40, padding: '12px 16px', fontSize: '14px' },
        lg: { height: 48, padding: '16px 20px', fontSize: '16px' }
      },
      card: {
        padding: '16px',
        gap: '12px'
      }
    },
    spacious: {
      button: {
        sm: { height: 36, padding: '10px 18px', fontSize: '14px' },
        md: { height: 48, padding: '16px 24px', fontSize: '15px' },
        lg: { height: 56, padding: '20px 28px', fontSize: '16px' }
      },
      input: {
        sm: { height: 36, padding: '10px 16px', fontSize: '14px' },
        md: { height: 48, padding: '16px 20px', fontSize: '15px' },
        lg: { height: 56, padding: '20px 24px', fontSize: '16px' }
      },
      card: {
        padding: '20px',
        gap: '16px'
      }
    }
  };

  return sizes[density];
}

// CSS custom property helpers
export function generateThemeCSS(portal: PortalType, theme?: Partial<PortalTheme>): string {
  const portalTheme = { ...PORTAL_THEMES[portal], ...theme };
  const colorScheme = generateColorScheme(portalTheme.primary);
  const spacing = getDensitySpacing(portalTheme.density);
  const componentSizes = getDensityComponentSizes(portalTheme.density);

  return `
    :root[data-portal="${portal}"] {
      /* Colors */
      --color-primary: ${colorScheme.primary};
      --color-primary-light: ${colorScheme.primaryLight};
      --color-primary-dark: ${colorScheme.primaryDark};
      --color-secondary: ${colorScheme.secondary};
      --color-accent: ${colorScheme.accent};
      --color-success: ${colorScheme.success};
      --color-warning: ${colorScheme.warning};
      --color-error: ${colorScheme.error};
      --color-info: ${colorScheme.info};
      
      /* Spacing */
      ${Object.entries(spacing).map(([key, value]) => 
        `--spacing-${key}: ${value}px;`
      ).join('\n      ')}
      
      /* Border Radius */
      --border-radius: ${
        portalTheme.borderRadius === 'none' ? '0' :
        portalTheme.borderRadius === 'sm' ? '2px' :
        portalTheme.borderRadius === 'md' ? '6px' :
        portalTheme.borderRadius === 'lg' ? '8px' : '6px'
      };
      
      /* Component Sizes */
      --button-sm-height: ${componentSizes.button.sm.height}px;
      --button-md-height: ${componentSizes.button.md.height}px;
      --button-lg-height: ${componentSizes.button.lg.height}px;
      --input-sm-height: ${componentSizes.input.sm.height}px;
      --input-md-height: ${componentSizes.input.md.height}px;
      --input-lg-height: ${componentSizes.input.lg.height}px;
      --card-padding: ${componentSizes.card.padding};
      --card-gap: ${componentSizes.card.gap};
    }
  `;
}

// Accessibility utilities
export function getContrastRatio(color1: string, color2: string): number {
  const getLuminance = (color: string): number => {
    const rgb = hexToRgb(color);
    if (!rgb) return 0;
    
    const sRGB = [rgb.r, rgb.g, rgb.b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    
    return 0.2126 * sRGB[0] + 0.7152 * sRGB[1] + 0.0722 * sRGB[2];
  };

  const l1 = getLuminance(color1);
  const l2 = getLuminance(color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

export function isAccessibleContrast(foreground: string, background: string, level: 'AA' | 'AAA' = 'AA'): boolean {
  const ratio = getContrastRatio(foreground, background);
  return level === 'AA' ? ratio >= 4.5 : ratio >= 7;
}

export function findAccessibleColor(baseColor: string, background: string, level: 'AA' | 'AAA' = 'AA'): string {
  let color = baseColor;
  const targetRatio = level === 'AA' ? 4.5 : 7;
  let adjustment = 0;
  const step = 5;
  const maxAdjustment = 80;

  while (adjustment <= maxAdjustment) {
    const lightColor = adjustColor(baseColor, adjustment);
    const darkColor = adjustColor(baseColor, -adjustment);
    
    if (getContrastRatio(lightColor, background) >= targetRatio) {
      return lightColor;
    }
    if (getContrastRatio(darkColor, background) >= targetRatio) {
      return darkColor;
    }
    
    adjustment += step;
  }

  // Fallback to black or white
  return getContrastRatio('#000000', background) > getContrastRatio('#ffffff', background) 
    ? '#000000' 
    : '#ffffff';
}

// Portal theme validation
export function validateTheme(theme: PortalTheme): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Validate colors are valid hex codes
  const colorFields: (keyof PortalTheme)[] = ['primary', 'secondary', 'accent'];
  colorFields.forEach(field => {
    if (theme[field] && !hexToRgb(theme[field] as string)) {
      errors.push(`Invalid hex color for ${field}: ${theme[field]}`);
    }
  });

  // Validate accessibility
  if (theme.primary && theme.secondary) {
    if (!isAccessibleContrast(theme.primary, theme.secondary)) {
      errors.push('Primary and secondary colors do not meet accessibility contrast requirements');
    }
  }

  // Validate enum values
  if (theme.density && !['compact', 'comfortable', 'spacious'].includes(theme.density)) {
    errors.push(`Invalid density value: ${theme.density}`);
  }

  if (theme.borderRadius && !['none', 'sm', 'md', 'lg'].includes(theme.borderRadius)) {
    errors.push(`Invalid borderRadius value: ${theme.borderRadius}`);
  }

  if (theme.spacing && !['tight', 'normal', 'loose'].includes(theme.spacing)) {
    errors.push(`Invalid spacing value: ${theme.spacing}`);
  }

  return { isValid: errors.length === 0, errors };
}

// Theme export utilities
export function exportTheme(portal: PortalType, theme: PortalTheme) {
  return {
    portal,
    theme,
    generatedAt: new Date().toISOString(),
    css: generateThemeCSS(portal, theme),
    colorScheme: generateColorScheme(theme.primary),
    spacing: getDensitySpacing(theme.density),
    componentSizes: getDensityComponentSizes(theme.density)
  };
}

export function importTheme(themeData: any): { portal: PortalType; theme: PortalTheme } | null {
  try {
    if (!themeData.portal || !themeData.theme) {
      throw new Error('Invalid theme data structure');
    }

    const validation = validateTheme(themeData.theme);
    if (!validation.isValid) {
      throw new Error(`Theme validation failed: ${validation.errors.join(', ')}`);
    }

    return {
      portal: themeData.portal,
      theme: themeData.theme
    };
  } catch (error) {
    console.error('Failed to import theme:', error);
    return null;
  }
}