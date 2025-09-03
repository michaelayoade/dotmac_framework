import { AppearanceSettings } from '../types';

export const getDefaultAppearanceSettings = (): AppearanceSettings => ({
  theme: {
    mode: 'system',
    primaryColor: '#3b82f6',
    accentColor: '#8b5cf6',
    fontSize: 'medium',
    compactMode: false,
    animations: true,
  },
  accessibility: {
    highContrast: false,
    reducedMotion: false,
    screenReader: false,
    keyboardNavigation: true,
    focusIndicators: true,
  },
  layout: {
    sidebarCollapsed: false,
    density: 'comfortable',
    showTooltips: true,
  },
});

export const validateAppearanceSettings = (
  settings: Partial<AppearanceSettings>
): Record<string, string> => {
  const errors: Record<string, string> = {};

  // Validate theme settings
  if (settings.theme) {
    if (settings.theme.mode && !['light', 'dark', 'system'].includes(settings.theme.mode)) {
      errors['theme.mode'] = 'Invalid theme mode';
    }

    if (
      settings.theme.fontSize &&
      !['small', 'medium', 'large'].includes(settings.theme.fontSize)
    ) {
      errors['theme.fontSize'] = 'Invalid font size';
    }

    if (settings.theme.primaryColor && !isValidHexColor(settings.theme.primaryColor)) {
      errors['theme.primaryColor'] = 'Invalid primary color format';
    }

    if (settings.theme.accentColor && !isValidHexColor(settings.theme.accentColor)) {
      errors['theme.accentColor'] = 'Invalid accent color format';
    }
  }

  // Validate layout settings
  if (settings.layout) {
    if (
      settings.layout.density &&
      !['compact', 'comfortable', 'spacious'].includes(settings.layout.density)
    ) {
      errors['layout.density'] = 'Invalid layout density';
    }
  }

  return errors;
};

export const isValidHexColor = (color: string): boolean => {
  const hexColorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
  return hexColorRegex.test(color);
};

export const hexToRgb = (hex: string): { r: number; g: number; b: number } | null => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
};

export const rgbToHex = (r: number, g: number, b: number): string => {
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
};

export const getContrastRatio = (color1: string, color2: string): number => {
  const getLuminance = (hex: string): number => {
    const rgb = hexToRgb(hex);
    if (!rgb) return 0;

    const { r, g, b } = rgb;
    const [rs, gs, bs] = [r, g, b].map((c) => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });

    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  };

  const l1 = getLuminance(color1);
  const l2 = getLuminance(color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
};

export const isAccessibleContrast = (
  foreground: string,
  background: string,
  level: 'AA' | 'AAA' = 'AA'
): boolean => {
  const ratio = getContrastRatio(foreground, background);
  return level === 'AA' ? ratio >= 4.5 : ratio >= 7;
};

export const generateColorVariations = (baseColor: string): Record<string, string> => {
  const rgb = hexToRgb(baseColor);
  if (!rgb) return { base: baseColor };

  const { r, g, b } = rgb;

  return {
    50: rgbToHex(
      Math.min(255, Math.floor(r + (255 - r) * 0.95)),
      Math.min(255, Math.floor(g + (255 - g) * 0.95)),
      Math.min(255, Math.floor(b + (255 - b) * 0.95))
    ),
    100: rgbToHex(
      Math.min(255, Math.floor(r + (255 - r) * 0.85)),
      Math.min(255, Math.floor(g + (255 - g) * 0.85)),
      Math.min(255, Math.floor(b + (255 - b) * 0.85))
    ),
    200: rgbToHex(
      Math.min(255, Math.floor(r + (255 - r) * 0.7)),
      Math.min(255, Math.floor(g + (255 - g) * 0.7)),
      Math.min(255, Math.floor(b + (255 - b) * 0.7))
    ),
    300: rgbToHex(
      Math.min(255, Math.floor(r + (255 - r) * 0.45)),
      Math.min(255, Math.floor(g + (255 - g) * 0.45)),
      Math.min(255, Math.floor(b + (255 - b) * 0.45))
    ),
    400: rgbToHex(
      Math.min(255, Math.floor(r + (255 - r) * 0.25)),
      Math.min(255, Math.floor(g + (255 - g) * 0.25)),
      Math.min(255, Math.floor(b + (255 - b) * 0.25))
    ),
    500: baseColor,
    600: rgbToHex(Math.floor(r * 0.85), Math.floor(g * 0.85), Math.floor(b * 0.85)),
    700: rgbToHex(Math.floor(r * 0.7), Math.floor(g * 0.7), Math.floor(b * 0.7)),
    800: rgbToHex(Math.floor(r * 0.55), Math.floor(g * 0.55), Math.floor(b * 0.55)),
    900: rgbToHex(Math.floor(r * 0.4), Math.floor(g * 0.4), Math.floor(b * 0.4)),
  };
};

export const applyThemeToDOM = (settings: AppearanceSettings): void => {
  const root = document.documentElement;

  // Apply theme mode
  root.classList.remove('light', 'dark');
  if (settings.theme.mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.classList.add(prefersDark ? 'dark' : 'light');
  } else {
    root.classList.add(settings.theme.mode);
  }

  // Apply primary color variations
  const primaryVariations = generateColorVariations(settings.theme.primaryColor);
  Object.entries(primaryVariations).forEach(([shade, color]) => {
    root.style.setProperty(`--color-primary-${shade}`, color);
  });

  // Apply accent color variations
  const accentVariations = generateColorVariations(settings.theme.accentColor);
  Object.entries(accentVariations).forEach(([shade, color]) => {
    root.style.setProperty(`--color-accent-${shade}`, color);
  });

  // Apply font size
  const fontSizeMap = {
    small: '14px',
    medium: '16px',
    large: '18px',
  };
  root.style.setProperty('--font-size-base', fontSizeMap[settings.theme.fontSize]);

  // Apply compact mode
  root.classList.toggle('compact-mode', settings.theme.compactMode);

  // Apply animations
  root.classList.toggle('no-animations', !settings.theme.animations);

  // Apply accessibility settings
  root.classList.toggle('high-contrast', settings.accessibility.highContrast);
  root.classList.toggle('reduced-motion', settings.accessibility.reducedMotion);
  root.classList.toggle('focus-indicators', settings.accessibility.focusIndicators);

  // Apply layout settings
  const densityMap = {
    compact: '0.75rem',
    comfortable: '1rem',
    spacious: '1.5rem',
  };
  root.style.setProperty('--spacing-base', densityMap[settings.layout.density]);
};

export const getSystemThemePreference = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

export const watchSystemThemeChanges = (
  callback: (theme: 'light' | 'dark') => void
): (() => void) => {
  if (typeof window === 'undefined') return () => {};

  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = (e: MediaQueryListEvent) => {
    callback(e.matches ? 'dark' : 'light');
  };

  mediaQuery.addEventListener('change', handler);
  return () => mediaQuery.removeEventListener('change', handler);
};

export const exportAppearanceSettings = (settings: AppearanceSettings): string => {
  const exportData = {
    ...settings,
    exportedAt: new Date().toISOString(),
    version: '1.0.0',
  };

  return JSON.stringify(exportData, null, 2);
};

export const importAppearanceSettings = (jsonString: string): AppearanceSettings | null => {
  try {
    const importData = JSON.parse(jsonString);

    // Validate structure
    if (!importData.theme || !importData.accessibility || !importData.layout) {
      throw new Error('Invalid settings format');
    }

    // Validate imported settings
    const errors = validateAppearanceSettings(importData);
    if (Object.keys(errors).length > 0) {
      throw new Error('Invalid settings values');
    }

    return {
      theme: importData.theme,
      accessibility: importData.accessibility,
      layout: importData.layout,
    };
  } catch (error) {
    console.error('Failed to import appearance settings:', error);
    return null;
  }
};

export const generateCSS = (settings: AppearanceSettings): string => {
  const primaryVariations = generateColorVariations(settings.theme.primaryColor);
  const accentVariations = generateColorVariations(settings.theme.accentColor);

  const fontSizeMap = {
    small: '14px',
    medium: '16px',
    large: '18px',
  };

  const densityMap = {
    compact: '0.75rem',
    comfortable: '1rem',
    spacious: '1.5rem',
  };

  return `
:root {
  /* Primary Colors */
  ${Object.entries(primaryVariations)
    .map(([shade, color]) => `  --color-primary-${shade}: ${color};`)
    .join('\n')}

  /* Accent Colors */
  ${Object.entries(accentVariations)
    .map(([shade, color]) => `  --color-accent-${shade}: ${color};`)
    .join('\n')}

  /* Typography */
  --font-size-base: ${fontSizeMap[settings.theme.fontSize]};

  /* Spacing */
  --spacing-base: ${densityMap[settings.layout.density]};
}

/* Theme Classes */
.light {
  --background: #ffffff;
  --foreground: #0f172a;
}

.dark {
  --background: #0f172a;
  --foreground: #f8fafc;
}

/* Accessibility */
${
  settings.accessibility.highContrast
    ? `
.high-contrast {
  filter: contrast(1.5);
}
`
    : ''
}

${
  settings.accessibility.reducedMotion
    ? `
.reduced-motion *,
.reduced-motion *::before,
.reduced-motion *::after {
  animation-duration: 0.01ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.01ms !important;
}
`
    : ''
}

${
  settings.accessibility.focusIndicators
    ? `
.focus-indicators *:focus {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}
`
    : ''
}

/* Compact Mode */
${
  settings.theme.compactMode
    ? `
.compact-mode {
  --spacing-base: calc(var(--spacing-base) * 0.75);
}
`
    : ''
}

/* No Animations */
${
  !settings.theme.animations
    ? `
.no-animations *,
.no-animations *::before,
.no-animations *::after {
  animation-duration: 0.01ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.01ms !important;
}
`
    : ''
}
  `.trim();
};
