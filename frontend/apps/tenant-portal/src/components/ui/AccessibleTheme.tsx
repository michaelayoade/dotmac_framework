/**
 * Accessible Theme System
 * Color contrast validation, theme accessibility, and WCAG compliant theming
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getContrastRatio, meetsContrastRequirement, validateColorPalette } from '@/lib/accessibility';

// ============================================================================
// THEME TYPES AND INTERFACES
// ============================================================================

export interface ColorPalette {
  // Primary colors
  primary: string;
  primaryForeground: string;
  secondary: string;
  secondaryForeground: string;
  
  // Background colors
  background: string;
  foreground: string;
  muted: string;
  mutedForeground: string;
  
  // Semantic colors
  success: string;
  successForeground: string;
  warning: string;
  warningForeground: string;
  error: string;
  errorForeground: string;
  info: string;
  infoForeground: string;
  
  // Interactive states
  border: string;
  input: string;
  ring: string;
  
  // Component-specific
  card: string;
  cardForeground: string;
  popover: string;
  popoverForeground: string;
}

export interface AccessibilitySettings {
  highContrast: boolean;
  reducedMotion: boolean;
  largeText: boolean;
  focusVisible: boolean;
  colorBlindFriendly: boolean;
}

export interface ThemeContextValue {
  palette: ColorPalette;
  accessibility: AccessibilitySettings;
  updatePalette: (updates: Partial<ColorPalette>) => void;
  updateAccessibility: (updates: Partial<AccessibilitySettings>) => void;
  validateTheme: () => ThemeValidationResult;
  resetToDefaults: () => void;
  applyHighContrastMode: () => void;
  toggleReducedMotion: () => void;
  toggleLargeText: () => void;
}

export interface ThemeValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  contrastIssues: Array<{
    combination: string;
    actualRatio: number;
    requiredRatio: number;
    severity: 'error' | 'warning';
  }>;
}

// ============================================================================
// DEFAULT THEME CONFIGURATIONS
// ============================================================================

const defaultPalette: ColorPalette = {
  primary: '#2563eb',
  primaryForeground: '#ffffff',
  secondary: '#64748b',
  secondaryForeground: '#ffffff',
  
  background: '#ffffff',
  foreground: '#0f172a',
  muted: '#f1f5f9',
  mutedForeground: '#64748b',
  
  success: '#16a34a',
  successForeground: '#ffffff',
  warning: '#eab308',
  warningForeground: '#000000',
  error: '#dc2626',
  errorForeground: '#ffffff',
  info: '#0ea5e9',
  infoForeground: '#ffffff',
  
  border: '#e2e8f0',
  input: '#ffffff',
  ring: '#2563eb',
  
  card: '#ffffff',
  cardForeground: '#0f172a',
  popover: '#ffffff',
  popoverForeground: '#0f172a',
};

const highContrastPalette: ColorPalette = {
  primary: '#000000',
  primaryForeground: '#ffffff',
  secondary: '#4a4a4a',
  secondaryForeground: '#ffffff',
  
  background: '#ffffff',
  foreground: '#000000',
  muted: '#f0f0f0',
  mutedForeground: '#000000',
  
  success: '#006400',
  successForeground: '#ffffff',
  warning: '#8b4513',
  warningForeground: '#ffffff',
  error: '#8b0000',
  errorForeground: '#ffffff',
  info: '#000080',
  infoForeground: '#ffffff',
  
  border: '#000000',
  input: '#ffffff',
  ring: '#000000',
  
  card: '#ffffff',
  cardForeground: '#000000',
  popover: '#ffffff',
  popoverForeground: '#000000',
};

const defaultAccessibility: AccessibilitySettings = {
  highContrast: false,
  reducedMotion: false,
  largeText: false,
  focusVisible: true,
  colorBlindFriendly: false,
};

// ============================================================================
// THEME CONTEXT
// ============================================================================

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function useAccessibleTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useAccessibleTheme must be used within AccessibleThemeProvider');
  }
  return context;
}

// ============================================================================
// THEME PROVIDER COMPONENT
// ============================================================================

interface AccessibleThemeProviderProps {
  children: React.ReactNode;
  initialPalette?: Partial<ColorPalette>;
  initialAccessibility?: Partial<AccessibilitySettings>;
}

export function AccessibleThemeProvider({
  children,
  initialPalette = {},
  initialAccessibility = {},
}: AccessibleThemeProviderProps) {
  const [palette, setPalette] = useState<ColorPalette>(() => ({
    ...defaultPalette,
    ...initialPalette,
  }));

  const [accessibility, setAccessibility] = useState<AccessibilitySettings>(() => ({
    ...defaultAccessibility,
    ...initialAccessibility,
  }));

  // Detect system preferences
  useEffect(() => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const prefersHighContrast = window.matchMedia('(prefers-contrast: high)').matches;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    setAccessibility(prev => ({
      ...prev,
      highContrast: prev.highContrast || prefersHighContrast,
      reducedMotion: prev.reducedMotion || prefersReducedMotion,
    }));
  }, []);

  // Apply accessibility settings to document
  useEffect(() => {
    const root = document.documentElement;
    
    // Apply high contrast mode
    if (accessibility.highContrast) {
      root.style.setProperty('--force-high-contrast', '1');
      Object.entries(highContrastPalette).forEach(([key, value]) => {
        root.style.setProperty(`--color-${key}`, value);
      });
    } else {
      root.style.removeProperty('--force-high-contrast');
      Object.entries(palette).forEach(([key, value]) => {
        root.style.setProperty(`--color-${key}`, value);
      });
    }

    // Apply reduced motion
    if (accessibility.reducedMotion) {
      root.style.setProperty('--animation-duration', '0.01ms');
      root.style.setProperty('--transition-duration', '0.01ms');
    } else {
      root.style.removeProperty('--animation-duration');
      root.style.removeProperty('--transition-duration');
    }

    // Apply large text scaling
    if (accessibility.largeText) {
      root.style.setProperty('--text-scale', '1.2');
    } else {
      root.style.removeProperty('--text-scale');
    }

    // Apply focus visible styles
    if (accessibility.focusVisible) {
      root.style.setProperty('--focus-outline-width', '2px');
      root.style.setProperty('--focus-outline-offset', '2px');
    } else {
      root.style.setProperty('--focus-outline-width', '1px');
      root.style.setProperty('--focus-outline-offset', '1px');
    }
  }, [palette, accessibility]);

  const updatePalette = useCallback((updates: Partial<ColorPalette>) => {
    setPalette(prev => ({ ...prev, ...updates }));
  }, []);

  const updateAccessibility = useCallback((updates: Partial<AccessibilitySettings>) => {
    setAccessibility(prev => ({ ...prev, ...updates }));
  }, []);

  const validateTheme = useCallback((): ThemeValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];
    const contrastIssues: Array<{
      combination: string;
      actualRatio: number;
      requiredRatio: number;
      severity: 'error' | 'warning';
    }> = [];

    const currentPalette = accessibility.highContrast ? highContrastPalette : palette;

    // Define critical color combinations that must pass WCAG AA
    const criticalCombinations = [
      { fg: 'foreground', bg: 'background', name: 'body text', required: 4.5 },
      { fg: 'primaryForeground', bg: 'primary', name: 'primary button', required: 4.5 },
      { fg: 'errorForeground', bg: 'error', name: 'error text', required: 4.5 },
      { fg: 'successForeground', bg: 'success', name: 'success text', required: 4.5 },
      { fg: 'warningForeground', bg: 'warning', name: 'warning text', required: 4.5 },
    ];

    criticalCombinations.forEach(({ fg, bg, name, required }) => {
      const fgColor = currentPalette[fg as keyof ColorPalette];
      const bgColor = currentPalette[bg as keyof ColorPalette];
      
      if (fgColor && bgColor) {
        try {
          const ratio = getContrastRatio(fgColor, bgColor);
          
          if (ratio < required) {
            contrastIssues.push({
              combination: name,
              actualRatio: Math.round(ratio * 100) / 100,
              requiredRatio: required,
              severity: ratio < 3 ? 'error' : 'warning',
            });
            
            if (ratio < 3) {
              errors.push(`${name} contrast ratio (${ratio.toFixed(2)}:1) is critically low`);
            } else {
              warnings.push(`${name} contrast ratio (${ratio.toFixed(2)}:1) doesn't meet WCAG AA standards`);
            }
          }
        } catch (error) {
          errors.push(`Invalid color format in ${name}`);
        }
      }
    });

    // Additional validations
    if (!accessibility.focusVisible) {
      warnings.push('Focus indicators are disabled, which may impact keyboard navigation');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      contrastIssues,
    };
  }, [palette, accessibility]);

  const resetToDefaults = useCallback(() => {
    setPalette(defaultPalette);
    setAccessibility(defaultAccessibility);
  }, []);

  const applyHighContrastMode = useCallback(() => {
    setAccessibility(prev => ({ ...prev, highContrast: !prev.highContrast }));
  }, []);

  const toggleReducedMotion = useCallback(() => {
    setAccessibility(prev => ({ ...prev, reducedMotion: !prev.reducedMotion }));
  }, []);

  const toggleLargeText = useCallback(() => {
    setAccessibility(prev => ({ ...prev, largeText: !prev.largeText }));
  }, []);

  const contextValue: ThemeContextValue = {
    palette: accessibility.highContrast ? highContrastPalette : palette,
    accessibility,
    updatePalette,
    updateAccessibility,
    validateTheme,
    resetToDefaults,
    applyHighContrastMode,
    toggleReducedMotion,
    toggleLargeText,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

// ============================================================================
// THEME SETTINGS COMPONENT
// ============================================================================

interface ThemeSettingsProps {
  className?: string;
}

export function ThemeSettings({ className = '' }: ThemeSettingsProps) {
  const {
    accessibility,
    applyHighContrastMode,
    toggleReducedMotion,
    toggleLargeText,
    validateTheme,
  } = useAccessibleTheme();

  const [validation, setValidation] = useState<ThemeValidationResult | null>(null);

  const handleValidation = () => {
    const result = validateTheme();
    setValidation(result);
  };

  return (
    <div className={`space-y-6 ${className}`} role="region" aria-label="Theme and accessibility settings">
      <div>
        <h3 className="text-lg font-semibold mb-4">Accessibility Settings</h3>
        
        <div className="space-y-4">
          {/* High Contrast Toggle */}
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={accessibility.highContrast}
              onChange={applyHighContrastMode}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              aria-describedby="high-contrast-description"
            />
            <div>
              <div className="font-medium">High Contrast Mode</div>
              <div id="high-contrast-description" className="text-sm text-gray-600">
                Increase color contrast for better visibility
              </div>
            </div>
          </label>

          {/* Reduced Motion Toggle */}
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={accessibility.reducedMotion}
              onChange={toggleReducedMotion}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              aria-describedby="reduced-motion-description"
            />
            <div>
              <div className="font-medium">Reduce Motion</div>
              <div id="reduced-motion-description" className="text-sm text-gray-600">
                Minimize animations and transitions
              </div>
            </div>
          </label>

          {/* Large Text Toggle */}
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={accessibility.largeText}
              onChange={toggleLargeText}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              aria-describedby="large-text-description"
            />
            <div>
              <div className="font-medium">Large Text</div>
              <div id="large-text-description" className="text-sm text-gray-600">
                Increase text size by 20% for better readability
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Theme Validation */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Theme Validation</h3>
          <button
            onClick={handleValidation}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Validate Theme
          </button>
        </div>

        {validation && (
          <div className="space-y-3">
            <div className={`p-4 rounded-md ${
              validation.isValid 
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}>
              <div className="font-medium mb-2">
                {validation.isValid ? 'Theme is accessible!' : 'Theme has accessibility issues'}
              </div>
              
              {validation.errors.length > 0 && (
                <div className="mb-2">
                  <div className="font-medium text-red-800 mb-1">Errors:</div>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {validation.errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {validation.warnings.length > 0 && (
                <div>
                  <div className="font-medium text-yellow-800 mb-1">Warnings:</div>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {validation.warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {validation.contrastIssues.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-md">
                <div className="font-medium text-yellow-800 mb-2">Contrast Issues:</div>
                <div className="space-y-2">
                  {validation.contrastIssues.map((issue, index) => (
                    <div key={index} className="text-sm">
                      <span className="font-medium">{issue.combination}:</span>{' '}
                      {issue.actualRatio}:1 (required: {issue.requiredRatio}:1)
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// COLOR CONTRAST CHECKER COMPONENT
// ============================================================================

interface ColorContrastCheckerProps {
  className?: string;
}

export function ColorContrastChecker({ className = '' }: ColorContrastCheckerProps) {
  const [foreground, setForeground] = useState('#000000');
  const [background, setBackground] = useState('#ffffff');
  const [result, setResult] = useState<{
    ratio: number;
    aaSmall: boolean;
    aaLarge: boolean;
    aaaSmall: boolean;
    aaaLarge: boolean;
  } | null>(null);

  useEffect(() => {
    try {
      const ratio = getContrastRatio(foreground, background);
      setResult({
        ratio,
        aaSmall: meetsContrastRequirement(foreground, background, 'AA', false),
        aaLarge: meetsContrastRequirement(foreground, background, 'AA', true),
        aaaSmall: meetsContrastRequirement(foreground, background, 'AAA', false),
        aaaLarge: meetsContrastRequirement(foreground, background, 'AAA', true),
      });
    } catch (error) {
      setResult(null);
    }
  }, [foreground, background]);

  return (
    <div className={`space-y-4 ${className}`} role="region" aria-label="Color contrast checker">
      <h3 className="text-lg font-semibold">Color Contrast Checker</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="foreground-color" className="block text-sm font-medium text-gray-700 mb-1">
            Foreground Color
          </label>
          <div className="flex items-center space-x-2">
            <input
              id="foreground-color"
              type="color"
              value={foreground}
              onChange={(e) => setForeground(e.target.value)}
              className="h-10 w-16 rounded border border-gray-300"
            />
            <input
              type="text"
              value={foreground}
              onChange={(e) => setForeground(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="#000000"
              pattern="^#[0-9A-Fa-f]{6}$"
            />
          </div>
        </div>

        <div>
          <label htmlFor="background-color" className="block text-sm font-medium text-gray-700 mb-1">
            Background Color
          </label>
          <div className="flex items-center space-x-2">
            <input
              id="background-color"
              type="color"
              value={background}
              onChange={(e) => setBackground(e.target.value)}
              className="h-10 w-16 rounded border border-gray-300"
            />
            <input
              type="text"
              value={background}
              onChange={(e) => setBackground(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="#ffffff"
              pattern="^#[0-9A-Fa-f]{6}$"
            />
          </div>
        </div>
      </div>

      {/* Preview */}
      <div
        className="p-4 rounded-md border"
        style={{ backgroundColor: background, color: foreground }}
      >
        <div className="text-sm">Sample small text (12px)</div>
        <div className="text-lg font-bold">Sample large text (18px bold)</div>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-gray-50 p-4 rounded-md">
          <div className="text-lg font-semibold mb-3">
            Contrast Ratio: {result.ratio.toFixed(2)}:1
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-medium mb-2">WCAG AA</div>
              <div className="space-y-1 text-sm">
                <div className={`flex items-center ${result.aaSmall ? 'text-green-600' : 'text-red-600'}`}>
                  <span className="mr-2">{result.aaSmall ? '✓' : '✗'}</span>
                  Normal text (4.5:1)
                </div>
                <div className={`flex items-center ${result.aaLarge ? 'text-green-600' : 'text-red-600'}`}>
                  <span className="mr-2">{result.aaLarge ? '✓' : '✗'}</span>
                  Large text (3:1)
                </div>
              </div>
            </div>
            
            <div>
              <div className="font-medium mb-2">WCAG AAA</div>
              <div className="space-y-1 text-sm">
                <div className={`flex items-center ${result.aaaSmall ? 'text-green-600' : 'text-red-600'}`}>
                  <span className="mr-2">{result.aaaSmall ? '✓' : '✗'}</span>
                  Normal text (7:1)
                </div>
                <div className={`flex items-center ${result.aaaLarge ? 'text-green-600' : 'text-red-600'}`}>
                  <span className="mr-2">{result.aaaLarge ? '✓' : '✗'}</span>
                  Large text (4.5:1)
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}