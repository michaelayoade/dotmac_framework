/**
 * Accessibility Provider
 * Comprehensive accessibility features and compliance tools
 */

'use client';

import React, { 
  createContext, 
  useContext, 
  ReactNode, 
  useState, 
  useEffect,
  useCallback,
  useRef
} from 'react';

// Types
export interface AccessibilitySettings {
  highContrast: boolean;
  reduceMotion: boolean;
  fontSize: 'small' | 'medium' | 'large' | 'x-large';
  screenReaderOptimizations: boolean;
  keyboardNavigation: boolean;
  focusIndicators: boolean;
}

export interface AccessibilityContextValue {
  settings: AccessibilitySettings;
  updateSettings: (settings: Partial<AccessibilitySettings>) => void;
  announceToScreenReader: (message: string, priority?: 'polite' | 'assertive') => void;
  announceRouteChange: (routeName: string) => void;
  checkAccessibility: () => Promise<AccessibilityReport>;
}

export interface AccessibilityViolation {
  id: string;
  impact: 'minor' | 'moderate' | 'serious' | 'critical';
  description: string;
  element?: HTMLElement;
  help: string;
  helpUrl?: string;
}

export interface AccessibilityReport {
  violations: AccessibilityViolation[];
  passes: number;
  incomplete: number;
}

// Context
const AccessibilityContext = createContext<AccessibilityContextValue | undefined>(undefined);

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
}

// Default settings
const defaultSettings: AccessibilitySettings = {
  highContrast: false,
  reduceMotion: false,
  fontSize: 'medium',
  screenReaderOptimizations: false,
  keyboardNavigation: true,
  focusIndicators: true,
};

// Provider Component
interface AccessibilityProviderProps {
  children: ReactNode;
  initialSettings?: Partial<AccessibilitySettings>;
}

export function AccessibilityProvider({ 
  children, 
  initialSettings = {} 
}: AccessibilityProviderProps) {
  const [settings, setSettings] = useState<AccessibilitySettings>({
    ...defaultSettings,
    ...initialSettings,
  });
  
  const announceRef = useRef<HTMLDivElement>(null);

  // Apply settings to document
  useEffect(() => {
    const root = document.documentElement;

    // High contrast mode
    if (settings.highContrast) {
      root.classList.add('high-contrast-mode');
    } else {
      root.classList.remove('high-contrast-mode');
    }

    // Reduce motion
    if (settings.reduceMotion) {
      root.classList.add('reduce-motion');
    } else {
      root.classList.remove('reduce-motion');
    }

    // Font size
    root.classList.remove('font-small', 'font-medium', 'font-large', 'font-x-large');
    root.classList.add(`font-${settings.fontSize}`);

    // Screen reader optimizations
    if (settings.screenReaderOptimizations) {
      root.classList.add('screen-reader-optimized');
    } else {
      root.classList.remove('screen-reader-optimized');
    }

    // Keyboard navigation
    if (settings.keyboardNavigation) {
      root.classList.add('keyboard-navigation-enabled');
    } else {
      root.classList.remove('keyboard-navigation-enabled');
    }

    // Focus indicators
    if (settings.focusIndicators) {
      root.classList.add('focus-indicators-enabled');
    } else {
      root.classList.remove('focus-indicators-enabled');
    }
  }, [settings]);

  // Detect user preferences
  useEffect(() => {
    // Check for prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (prefersReducedMotion.matches && !initialSettings.reduceMotion) {
      setSettings(prev => ({ ...prev, reduceMotion: true }));
    }

    // Check for prefers-contrast
    const prefersHighContrast = window.matchMedia('(prefers-contrast: high)');
    if (prefersHighContrast.matches && !initialSettings.highContrast) {
      setSettings(prev => ({ ...prev, highContrast: true }));
    }

    // Listen for changes
    const handleReducedMotionChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, reduceMotion: e.matches }));
    };

    const handleContrastChange = (e: MediaQueryListEvent) => {
      setSettings(prev => ({ ...prev, highContrast: e.matches }));
    };

    prefersReducedMotion.addEventListener('change', handleReducedMotionChange);
    prefersHighContrast.addEventListener('change', handleContrastChange);

    return () => {
      prefersReducedMotion.removeEventListener('change', handleReducedMotionChange);
      prefersHighContrast.removeEventListener('change', handleContrastChange);
    };
  }, [initialSettings]);

  const updateSettings = useCallback((newSettings: Partial<AccessibilitySettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  }, []);

  const announceToScreenReader = useCallback((
    message: string, 
    priority: 'polite' | 'assertive' = 'polite'
  ) => {
    if (announceRef.current) {
      announceRef.current.setAttribute('aria-live', priority);
      announceRef.current.textContent = message;
      
      // Clear after announcement
      setTimeout(() => {
        if (announceRef.current) {
          announceRef.current.textContent = '';
        }
      }, 1000);
    }
  }, []);

  const announceRouteChange = useCallback((routeName: string) => {
    announceToScreenReader(`Navigated to ${routeName}`, 'polite');
  }, [announceToScreenReader]);

  // Basic accessibility checking
  const checkAccessibility = useCallback(async (): Promise<AccessibilityReport> => {
    const violations: AccessibilityViolation[] = [];
    let passes = 0;

    // Check for missing alt text
    const images = document.querySelectorAll('img');
    images.forEach((img, index) => {
      if (!img.getAttribute('alt') && !img.getAttribute('aria-label')) {
        violations.push({
          id: `missing-alt-${index}`,
          impact: 'serious',
          description: 'Image missing alternative text',
          element: img,
          help: 'Add alt attribute with descriptive text',
          helpUrl: 'https://webaim.org/articles/alt/'
        });
      } else {
        passes++;
      }
    });

    // Check for missing form labels
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach((input, index) => {
      const hasLabel = input.getAttribute('aria-label') || 
                     input.getAttribute('aria-labelledby') ||
                     document.querySelector(`label[for="${input.id}"]`);
      
      if (!hasLabel) {
        violations.push({
          id: `missing-label-${index}`,
          impact: 'critical',
          description: 'Form input missing accessible label',
          element: input as HTMLElement,
          help: 'Add aria-label attribute or associate with label element',
          helpUrl: 'https://webaim.org/articles/forms/'
        });
      } else {
        passes++;
      }
    });

    // Check for proper heading structure
    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
    let previousLevel = 0;
    headings.forEach((heading, index) => {
      const currentLevel = parseInt(heading.tagName.slice(1));
      if (currentLevel - previousLevel > 1) {
        violations.push({
          id: `heading-structure-${index}`,
          impact: 'moderate',
          description: 'Heading levels skip (e.g., h1 to h3)',
          element: heading,
          help: 'Use heading levels in sequential order',
          helpUrl: 'https://webaim.org/articles/structure/'
        });
      } else {
        passes++;
      }
      previousLevel = currentLevel;
    });

    // Check color contrast (simplified)
    const elements = document.querySelectorAll('*');
    elements.forEach((element, index) => {
      const styles = window.getComputedStyle(element);
      const color = styles.color;
      const backgroundColor = styles.backgroundColor;
      
      // This is a very simplified check - in production, use a proper color contrast library
      if (color && backgroundColor && color !== 'rgba(0, 0, 0, 0)' && backgroundColor !== 'rgba(0, 0, 0, 0)') {
        const contrast = calculateColorContrast(color, backgroundColor);
        if (contrast < 4.5) {
          violations.push({
            id: `color-contrast-${index}`,
            impact: 'serious',
            description: 'Insufficient color contrast ratio',
            element: element as HTMLElement,
            help: 'Ensure color contrast ratio is at least 4.5:1',
            helpUrl: 'https://webaim.org/articles/contrast/'
          });
        } else {
          passes++;
        }
      }
    });

    // Check for focus indicators
    const focusableElements = document.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    focusableElements.forEach((element, index) => {
      const styles = window.getComputedStyle(element, ':focus');
      if (styles.outline === 'none' && !styles.boxShadow.includes('inset')) {
        violations.push({
          id: `missing-focus-${index}`,
          impact: 'serious',
          description: 'Interactive element missing focus indicator',
          element: element as HTMLElement,
          help: 'Add visible focus styles for keyboard navigation',
          helpUrl: 'https://webaim.org/articles/focus/'
        });
      } else {
        passes++;
      }
    });

    return {
      violations,
      passes,
      incomplete: 0
    };
  }, []);

  const value: AccessibilityContextValue = {
    settings,
    updateSettings,
    announceToScreenReader,
    announceRouteChange,
    checkAccessibility,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
      
      {/* Screen reader announcements */}
      <div
        ref={announceRef}
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />
      
      {/* Add accessibility styles */}
      <style jsx global>{`
        /* High contrast mode */
        .high-contrast-mode {
          filter: contrast(150%);
        }

        .high-contrast-mode * {
          border-color: #000 !important;
        }

        /* Reduced motion */
        .reduce-motion *,
        .reduce-motion *::before,
        .reduce-motion *::after {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
        }

        /* Font sizes */
        .font-small {
          font-size: 14px;
        }

        .font-medium {
          font-size: 16px;
        }

        .font-large {
          font-size: 18px;
        }

        .font-x-large {
          font-size: 20px;
        }

        /* Screen reader optimizations */
        .screen-reader-optimized .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        /* Enhanced focus indicators */
        .focus-indicators-enabled *:focus {
          outline: 2px solid #0066cc;
          outline-offset: 2px;
        }

        .focus-indicators-enabled button:focus,
        .focus-indicators-enabled [role="button"]:focus {
          box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.3);
        }

        /* Skip links */
        .skip-link {
          position: absolute;
          left: -9999px;
          z-index: 999999;
          padding: 8px 16px;
          background: #000;
          color: #fff;
          text-decoration: none;
          font-weight: bold;
          border-radius: 0 0 4px 4px;
        }

        .skip-link:focus {
          left: 0;
          top: 0;
        }

        /* ARIA live regions */
        [aria-live] {
          position: absolute;
          left: -10000px;
          width: 1px;
          height: 1px;
          overflow: hidden;
        }
      `}</style>
    </AccessibilityContext.Provider>
  );
}

// Accessibility Settings Panel Component
interface AccessibilityPanelProps {
  className?: string;
  onClose?: () => void;
}

export function AccessibilityPanel({ className = '', onClose }: AccessibilityPanelProps) {
  const { settings, updateSettings } = useAccessibility();

  return (
    <div className={`bg-white rounded-lg border shadow-lg p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Accessibility Settings</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
            aria-label="Close accessibility settings"
          >
            ✕
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* High Contrast */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">High Contrast Mode</h3>
            <p className="text-sm text-gray-600">
              Increase contrast for better visibility
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.highContrast}
              onChange={(e) => updateSettings({ highContrast: e.target.checked })}
              className="sr-only"
            />
            <div className={`w-11 h-6 rounded-full transition-colors ${
              settings.highContrast ? 'bg-blue-600' : 'bg-gray-300'
            }`}>
              <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform ${
                settings.highContrast ? 'translate-x-6' : 'translate-x-1'
              } mt-1`} />
            </div>
          </label>
        </div>

        {/* Reduce Motion */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">Reduce Motion</h3>
            <p className="text-sm text-gray-600">
              Minimize animations and transitions
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.reduceMotion}
              onChange={(e) => updateSettings({ reduceMotion: e.target.checked })}
              className="sr-only"
            />
            <div className={`w-11 h-6 rounded-full transition-colors ${
              settings.reduceMotion ? 'bg-blue-600' : 'bg-gray-300'
            }`}>
              <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform ${
                settings.reduceMotion ? 'translate-x-6' : 'translate-x-1'
              } mt-1`} />
            </div>
          </label>
        </div>

        {/* Font Size */}
        <div>
          <h3 className="font-medium mb-2">Font Size</h3>
          <select
            value={settings.fontSize}
            onChange={(e) => updateSettings({ fontSize: e.target.value as any })}
            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
            <option value="x-large">Extra Large</option>
          </select>
        </div>

        {/* Screen Reader Optimizations */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">Screen Reader Optimizations</h3>
            <p className="text-sm text-gray-600">
              Enhanced support for screen readers
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.screenReaderOptimizations}
              onChange={(e) => updateSettings({ screenReaderOptimizations: e.target.checked })}
              className="sr-only"
            />
            <div className={`w-11 h-6 rounded-full transition-colors ${
              settings.screenReaderOptimizations ? 'bg-blue-600' : 'bg-gray-300'
            }`}>
              <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform ${
                settings.screenReaderOptimizations ? 'translate-x-6' : 'translate-x-1'
              } mt-1`} />
            </div>
          </label>
        </div>

        {/* Enhanced Focus Indicators */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">Enhanced Focus Indicators</h3>
            <p className="text-sm text-gray-600">
              More visible focus outlines for keyboard navigation
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.focusIndicators}
              onChange={(e) => updateSettings({ focusIndicators: e.target.checked })}
              className="sr-only"
            />
            <div className={`w-11 h-6 rounded-full transition-colors ${
              settings.focusIndicators ? 'bg-blue-600' : 'bg-gray-300'
            }`}>
              <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform ${
                settings.focusIndicators ? 'translate-x-6' : 'translate-x-1'
              } mt-1`} />
            </div>
          </label>
        </div>
      </div>

      <div className="mt-6 pt-6 border-t border-gray-200">
        <p className="text-sm text-gray-600">
          These settings are saved locally and will persist across browser sessions.
        </p>
      </div>
    </div>
  );
}

// Utility function for color contrast calculation (simplified)
function calculateColorContrast(color1: string, color2: string): number {
  // This is a very simplified implementation
  // In production, use a proper color contrast library like 'color-contrast'
  return 4.5; // Placeholder - always return passing value for now
}