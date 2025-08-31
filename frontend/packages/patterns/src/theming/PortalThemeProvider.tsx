/**
 * Portal Theme Provider
 * Context provider for portal-aware theming with density settings
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { trackAction } from '@dotmac/monitoring/observability';
import { withComponentRegistration } from '@dotmac/registry';
import { PORTAL_THEMES, PortalTheme, PortalType } from '../factories/templateFactories';

export interface PortalThemeContextValue {
  portal: PortalType;
  theme: PortalTheme;
  density: 'compact' | 'comfortable' | 'spacious';
  colorMode: 'light' | 'dark' | 'auto';
  reducedMotion: boolean;
  highContrast: boolean;
  updateTheme: (updates: Partial<PortalTheme>) => void;
  setDensity: (density: 'compact' | 'comfortable' | 'spacious') => void;
  setColorMode: (mode: 'light' | 'dark' | 'auto') => void;
  setReducedMotion: (enabled: boolean) => void;
  setHighContrast: (enabled: boolean) => void;
  resetTheme: () => void;
}

const PortalThemeContext = createContext<PortalThemeContextValue | null>(null);

export function usePortalTheme() {
  const context = useContext(PortalThemeContext);
  if (!context) {
    throw new Error('usePortalTheme must be used within a PortalThemeProvider');
  }
  return context;
}

export interface PortalThemeProviderProps {
  children: React.ReactNode;
  portal: PortalType;
  initialTheme?: Partial<PortalTheme>;
  initialDensity?: 'compact' | 'comfortable' | 'spacious';
  initialColorMode?: 'light' | 'dark' | 'auto';
  persistPreferences?: boolean;
  className?: string;
  'data-testid'?: string;
}

function PortalThemeProviderImpl({
  children,
  portal,
  initialTheme = {},
  initialDensity,
  initialColorMode = 'auto',
  persistPreferences = true,
  className = '',
  'data-testid': testId = 'portal-theme-provider'
}: PortalThemeProviderProps) {
  // Get base theme for portal
  const baseTheme = PORTAL_THEMES[portal];
  
  // State management
  const [theme, setTheme] = useState<PortalTheme>({ 
    ...baseTheme, 
    ...initialTheme 
  });
  const [density, setDensityState] = useState<'compact' | 'comfortable' | 'spacious'>(
    initialDensity || baseTheme.density
  );
  const [colorMode, setColorModeState] = useState<'light' | 'dark' | 'auto'>(initialColorMode);
  const [reducedMotion, setReducedMotionState] = useState(false);
  const [highContrast, setHighContrastState] = useState(false);

  // Load persisted preferences
  useEffect(() => {
    if (!persistPreferences) return;

    const storageKey = `portal-theme-${portal}`;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const preferences = JSON.parse(stored);
        
        if (preferences.theme) {
          setTheme(prev => ({ ...prev, ...preferences.theme }));
        }
        if (preferences.density) {
          setDensityState(preferences.density);
        }
        if (preferences.colorMode) {
          setColorModeState(preferences.colorMode);
        }
        if (typeof preferences.reducedMotion === 'boolean') {
          setReducedMotionState(preferences.reducedMotion);
        }
        if (typeof preferences.highContrast === 'boolean') {
          setHighContrastState(preferences.highContrast);
        }
      }
    } catch (error) {
      console.warn('Failed to load theme preferences:', error);
    }
  }, [portal, persistPreferences]);

  // Persist preferences
  const persistPreferencesToStorage = useCallback((updates: any) => {
    if (!persistPreferences) return;

    const storageKey = `portal-theme-${portal}`;
    try {
      const current = localStorage.getItem(storageKey);
      const preferences = current ? JSON.parse(current) : {};
      const updated = { ...preferences, ...updates };
      localStorage.setItem(storageKey, JSON.stringify(updated));
    } catch (error) {
      console.warn('Failed to persist theme preferences:', error);
    }
  }, [portal, persistPreferences]);

  // Detect system preferences
  useEffect(() => {
    // Detect color scheme preference
    if (colorMode === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const updateColorScheme = () => {
        document.documentElement.setAttribute(
          'data-color-mode',
          mediaQuery.matches ? 'dark' : 'light'
        );
      };
      
      updateColorScheme();
      mediaQuery.addEventListener('change', updateColorScheme);
      
      return () => mediaQuery.removeEventListener('change', updateColorScheme);
    } else {
      document.documentElement.setAttribute('data-color-mode', colorMode);
    }
  }, [colorMode]);

  useEffect(() => {
    // Detect reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateReducedMotion = () => {
      const shouldReduce = mediaQuery.matches || reducedMotion;
      document.documentElement.setAttribute(
        'data-reduced-motion',
        shouldReduce ? 'reduce' : 'no-preference'
      );
    };
    
    updateReducedMotion();
    mediaQuery.addEventListener('change', updateReducedMotion);
    
    return () => mediaQuery.removeEventListener('change', updateReducedMotion);
  }, [reducedMotion]);

  useEffect(() => {
    // Detect high contrast preference
    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    const updateHighContrast = () => {
      const shouldUseHighContrast = mediaQuery.matches || highContrast;
      document.documentElement.setAttribute(
        'data-high-contrast',
        shouldUseHighContrast ? 'high' : 'normal'
      );
    };
    
    updateHighContrast();
    mediaQuery.addEventListener('change', updateHighContrast);
    
    return () => mediaQuery.removeEventListener('change', updateHighContrast);
  }, [highContrast]);

  // Apply theme CSS variables
  useEffect(() => {
    const root = document.documentElement;
    
    // Set portal type
    root.setAttribute('data-portal', portal);
    
    // Set density
    root.setAttribute('data-density', density);
    
    // Set CSS variables
    root.style.setProperty('--theme-primary', theme.primary);
    root.style.setProperty('--theme-secondary', theme.secondary);
    root.style.setProperty('--theme-accent', theme.accent);
    root.style.setProperty('--theme-border-radius', 
      theme.borderRadius === 'none' ? '0' :
      theme.borderRadius === 'sm' ? '0.125rem' :
      theme.borderRadius === 'md' ? '0.375rem' :
      theme.borderRadius === 'lg' ? '0.5rem' : '0.375rem'
    );

    // Density-specific spacing
    const spacingMultiplier = 
      density === 'compact' ? 0.75 :
      density === 'spacious' ? 1.25 : 1;
    
    root.style.setProperty('--theme-spacing-multiplier', spacingMultiplier.toString());
    
    // Spacing scale based on density
    const baseSpacing = {
      tight: { xs: 2, sm: 4, md: 8, lg: 16, xl: 24 },
      normal: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 },
      loose: { xs: 6, sm: 12, md: 24, lg: 32, xl: 48 }
    };
    
    const spacing = baseSpacing[theme.spacing] || baseSpacing.normal;
    Object.entries(spacing).forEach(([size, value]) => {
      root.style.setProperty(
        `--theme-spacing-${size}`,
        `${Math.round(value * spacingMultiplier)}px`
      );
    });

  }, [portal, theme, density]);

  // Context methods
  const updateTheme = useCallback((updates: Partial<PortalTheme>) => {
    setTheme(prev => ({ ...prev, ...updates }));
    persistPreferencesToStorage({ theme: updates });
    
    try {
      trackAction('theme_update', 'personalization', { portal, updates: Object.keys(updates) });
    } catch {}
  }, [portal, persistPreferencesToStorage]);

  const setDensity = useCallback((newDensity: 'compact' | 'comfortable' | 'spacious') => {
    setDensityState(newDensity);
    persistPreferencesToStorage({ density: newDensity });
    
    try {
      trackAction('density_change', 'personalization', { portal, density: newDensity });
    } catch {}
  }, [portal, persistPreferencesToStorage]);

  const setColorMode = useCallback((mode: 'light' | 'dark' | 'auto') => {
    setColorModeState(mode);
    persistPreferencesToStorage({ colorMode: mode });
    
    try {
      trackAction('color_mode_change', 'personalization', { portal, mode });
    } catch {}
  }, [portal, persistPreferencesToStorage]);

  const setReducedMotion = useCallback((enabled: boolean) => {
    setReducedMotionState(enabled);
    persistPreferencesToStorage({ reducedMotion: enabled });
    
    try {
      trackAction('reduced_motion_toggle', 'accessibility', { portal, enabled });
    } catch {}
  }, [portal, persistPreferencesToStorage]);

  const setHighContrast = useCallback((enabled: boolean) => {
    setHighContrastState(enabled);
    persistPreferencesToStorage({ highContrast: enabled });
    
    try {
      trackAction('high_contrast_toggle', 'accessibility', { portal, enabled });
    } catch {}
  }, [portal, persistPreferencesToStorage]);

  const resetTheme = useCallback(() => {
    const defaultTheme = PORTAL_THEMES[portal];
    setTheme(defaultTheme);
    setDensityState(defaultTheme.density);
    setColorModeState('auto');
    setReducedMotionState(false);
    setHighContrastState(false);
    
    if (persistPreferences) {
      const storageKey = `portal-theme-${portal}`;
      localStorage.removeItem(storageKey);
    }
    
    try {
      trackAction('theme_reset', 'personalization', { portal });
    } catch {}
  }, [portal, persistPreferences]);

  // Context value
  const contextValue: PortalThemeContextValue = {
    portal,
    theme,
    density,
    colorMode,
    reducedMotion,
    highContrast,
    updateTheme,
    setDensity,
    setColorMode,
    setReducedMotion,
    setHighContrast,
    resetTheme
  };

  // Generate CSS classes
  const themeClasses = clsx(
    // Portal-specific classes
    `portal-${portal}`,
    
    // Density classes
    `density-${density}`,
    
    // Color mode classes
    `color-mode-${colorMode}`,
    
    // Accessibility classes
    reducedMotion && 'reduced-motion',
    highContrast && 'high-contrast',
    
    // Theme variation classes
    `theme-${theme.borderRadius}`,
    `spacing-${theme.spacing}`,
    
    className
  );

  return (
    <PortalThemeContext.Provider value={contextValue}>
      <div 
        className={themeClasses}
        data-testid={testId}
        data-portal={portal}
        data-density={density}
        data-color-mode={colorMode}
        data-reduced-motion={reducedMotion ? 'reduce' : 'no-preference'}
        data-high-contrast={highContrast ? 'high' : 'normal'}
      >
        {children}
      </div>
    </PortalThemeContext.Provider>
  );
}

export const PortalThemeProvider = withComponentRegistration(PortalThemeProviderImpl, {
  name: 'PortalThemeProvider',
  category: 'provider',
  portal: 'shared',
  version: '1.0.0',
  description: 'Context provider for portal-aware theming with density settings',
});

export default PortalThemeProvider;
