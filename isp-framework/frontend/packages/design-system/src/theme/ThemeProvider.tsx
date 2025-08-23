/**
 * Theme Provider with Dark/Light Mode Toggle
 * 
 * Comprehensive theme management system supporting:
 * - Light/Dark/High Contrast themes
 * - System preference detection
 * - User preference persistence
 * - Smooth theme transitions
 * - SSR support
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { ThemeName, themes, DesignTokens } from '../tokens/design-tokens';
import { themeGenerator } from '../css/theme-generator';

export interface ThemeContextValue {
  theme: ThemeName;
  systemTheme: 'light' | 'dark';
  effectiveTheme: ThemeName;
  tokens: DesignTokens;
  setTheme: (theme: ThemeName | 'system') => void;
  toggleTheme: () => void;
  isDark: boolean;
  isLight: boolean;
  isHighContrast: boolean;
  isSystemTheme: boolean;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: ThemeName | 'system';
  enableTransitions?: boolean;
  storageKey?: string;
  enableSystemDetection?: boolean;
  enableHighContrastDetection?: boolean;
  onThemeChange?: (theme: ThemeName) => void;
}

const STORAGE_KEY = 'isp-theme-preference';
const TRANSITION_CLASS = 'theme-transitioning';

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  enableTransitions = true,
  storageKey = STORAGE_KEY,
  enableSystemDetection = true,
  enableHighContrastDetection = true,
  onThemeChange,
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<ThemeName | 'system'>(defaultTheme);
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>('light');
  const [mounted, setMounted] = useState(false);

  // Get effective theme (resolve 'system' to actual theme)
  const getEffectiveTheme = (): ThemeName => {
    if (theme === 'system') {
      if (enableHighContrastDetection && 
          typeof window !== 'undefined' && 
          window.matchMedia?.('(prefers-contrast: high)').matches) {
        return 'highContrast';
      }
      return systemTheme;
    }
    return theme;
  };

  const effectiveTheme = getEffectiveTheme();
  const tokens = themes[effectiveTheme];

  // Initialize theme from storage and system
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored && (stored === 'system' || Object.keys(themes).includes(stored))) {
        setThemeState(stored as ThemeName | 'system');
      }
    } catch (error) {
      console.warn('Failed to read theme from localStorage:', error);
    }

    setMounted(true);
  }, [storageKey]);

  // System theme detection
  useEffect(() => {
    if (!enableSystemDetection || typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const updateSystemTheme = () => {
      setSystemTheme(mediaQuery.matches ? 'dark' : 'light');
    };

    updateSystemTheme();
    
    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', updateSystemTheme);
      return () => mediaQuery.removeEventListener('change', updateSystemTheme);
    } 
    // Legacy browsers
    else {
      mediaQuery.addListener(updateSystemTheme);
      return () => mediaQuery.removeListener(updateSystemTheme);
    }
  }, [enableSystemDetection]);

  // Apply theme to document
  useEffect(() => {
    if (!mounted || typeof document === 'undefined') return;

    const root = document.documentElement;
    const previousTheme = root.getAttribute('data-theme');

    // Add transition class for smooth theme switching
    if (enableTransitions && previousTheme && previousTheme !== effectiveTheme) {
      root.classList.add(TRANSITION_CLASS);
      
      const removeTransition = () => {
        root.classList.remove(TRANSITION_CLASS);
        root.removeEventListener('transitionend', removeTransition);
      };
      
      root.addEventListener('transitionend', removeTransition);
      
      // Fallback in case transitionend doesn't fire
      setTimeout(removeTransition, 300);
    }

    // Set theme attribute
    root.setAttribute('data-theme', effectiveTheme);
    
    // Set color-scheme for better browser defaults
    root.style.colorScheme = effectiveTheme === 'dark' ? 'dark' : 'light';

    // Call theme change callback
    onThemeChange?.(effectiveTheme);
  }, [effectiveTheme, mounted, enableTransitions, onThemeChange]);

  // Theme switching functions
  const setTheme = (newTheme: ThemeName | 'system') => {
    setThemeState(newTheme);
    
    try {
      if (newTheme === 'system') {
        localStorage.removeItem(storageKey);
      } else {
        localStorage.setItem(storageKey, newTheme);
      }
    } catch (error) {
      console.warn('Failed to save theme to localStorage:', error);
    }
  };

  const toggleTheme = () => {
    if (theme === 'system') {
      // If using system theme, switch to opposite of current system theme
      setTheme(systemTheme === 'dark' ? 'light' : 'dark');
    } else if (effectiveTheme === 'light') {
      setTheme('dark');
    } else if (effectiveTheme === 'dark') {
      setTheme('highContrast');
    } else {
      setTheme('light');
    }
  };

  const contextValue: ThemeContextValue = {
    theme: theme === 'system' ? 'system' as ThemeName : theme,
    systemTheme,
    effectiveTheme,
    tokens,
    setTheme,
    toggleTheme,
    isDark: effectiveTheme === 'dark',
    isLight: effectiveTheme === 'light',
    isHighContrast: effectiveTheme === 'highContrast',
    isSystemTheme: theme === 'system',
  };

  // Don't render until mounted to avoid hydration mismatch
  if (!mounted) {
    return <ThemeHydrationFallback>{children}</ThemeHydrationFallback>;
  }

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

// Fallback component to prevent hydration mismatch
function ThemeHydrationFallback({ children }: { children: ReactNode }) {
  return <div style={{ visibility: 'hidden' }}>{children}</div>;
}

// Hook to use theme context
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
}

// Theme toggle component
export interface ThemeToggleProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'button' | 'switch' | 'dropdown';
  showLabel?: boolean;
  showIcon?: boolean;
  className?: string;
}

export function ThemeToggle({ 
  size = 'md', 
  variant = 'button',
  showLabel = false,
  showIcon = true,
  className = '',
}: ThemeToggleProps) {
  const { effectiveTheme, toggleTheme, isDark, isLight, isHighContrast } = useTheme();

  const getIcon = () => {
    if (isDark) return '🌙';
    if (isHighContrast) return '🔆';
    return '☀️';
  };

  const getLabel = () => {
    if (isDark) return 'Dark mode';
    if (isHighContrast) return 'High contrast';
    return 'Light mode';
  };

  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-base',
    lg: 'w-12 h-12 text-lg',
  };

  if (variant === 'dropdown') {
    return <ThemeDropdown />;
  }

  if (variant === 'switch') {
    return (
      <label className={`theme-switch ${className}`}>
        <input
          type="checkbox"
          checked={isDark}
          onChange={toggleTheme}
          className="sr-only"
        />
        <span className="switch-track">
          <span className="switch-thumb">
            {showIcon && <span className="switch-icon">{getIcon()}</span>}
          </span>
        </span>
        {showLabel && <span className="switch-label">{getLabel()}</span>}
      </label>
    );
  }

  return (
    <button
      onClick={toggleTheme}
      className={`theme-toggle btn btn--ghost ${sizeClasses[size]} ${className}`}
      title={`Switch to ${isDark ? 'light' : isLight ? 'dark' : 'light'} mode`}
      aria-label={getLabel()}
    >
      {showIcon && <span className="theme-icon">{getIcon()}</span>}
      {showLabel && <span className="theme-label">{getLabel()}</span>}
    </button>
  );
}

// Advanced theme dropdown
function ThemeDropdown() {
  const { theme, setTheme, systemTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  const options = [
    { value: 'light', label: 'Light', icon: '☀️' },
    { value: 'dark', label: 'Dark', icon: '🌙' },
    { value: 'highContrast', label: 'High Contrast', icon: '🔆' },
    { value: 'system', label: `System (${systemTheme})`, icon: '💻' },
  ];

  return (
    <div className="theme-dropdown">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="theme-dropdown-trigger btn btn--ghost"
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <span className="theme-dropdown-icon">
          {theme === 'system' ? '💻' : options.find(opt => opt.value === theme)?.icon}
        </span>
        <span className="theme-dropdown-label">Theme</span>
        <span className="theme-dropdown-chevron">▼</span>
      </button>

      {isOpen && (
        <>
          <div 
            className="theme-dropdown-overlay" 
            onClick={() => setIsOpen(false)}
          />
          <div className="theme-dropdown-menu" role="menu">
            {options.map(option => (
              <button
                key={option.value}
                onClick={() => {
                  setTheme(option.value as ThemeName | 'system');
                  setIsOpen(false);
                }}
                className={`theme-dropdown-item ${theme === option.value ? 'active' : ''}`}
                role="menuitem"
              >
                <span className="theme-option-icon">{option.icon}</span>
                <span className="theme-option-label">{option.label}</span>
                {theme === option.value && <span className="theme-option-check">✓</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// HOC for theme-aware components
export function withTheme<P extends object>(
  Component: React.ComponentType<P & { theme: ThemeContextValue }>
) {
  return function ThemedComponent(props: P) {
    const theme = useTheme();
    return <Component {...props} theme={theme} />;
  };
}

// Utility hook for theme-based conditional rendering
export function useThemeValue<T>(values: Partial<Record<ThemeName, T>>): T | undefined {
  const { effectiveTheme } = useTheme();
  return values[effectiveTheme];
}

// CSS injection for theme transitions and base styles
export function ThemeStyles() {
  return (
    <style jsx global>{`
      :root {
        --theme-transition-duration: 0.2s;
        --theme-transition-timing: cubic-bezier(0.4, 0, 0.2, 1);
      }

      .${TRANSITION_CLASS} *,
      .${TRANSITION_CLASS} *::before,
      .${TRANSITION_CLASS} *::after {
        transition: 
          background-color var(--theme-transition-duration) var(--theme-transition-timing),
          border-color var(--theme-transition-duration) var(--theme-transition-timing),
          color var(--theme-transition-duration) var(--theme-transition-timing),
          fill var(--theme-transition-duration) var(--theme-transition-timing),
          stroke var(--theme-transition-duration) var(--theme-transition-timing),
          box-shadow var(--theme-transition-duration) var(--theme-transition-timing) !important;
      }

      .theme-toggle {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius-default);
        transition: all var(--transition-duration-150) var(--transition-timing-inOut);
      }

      .theme-switch {
        display: inline-flex;
        align-items: center;
        gap: var(--spacing-2);
        cursor: pointer;
      }

      .switch-track {
        position: relative;
        width: 3rem;
        height: 1.5rem;
        background-color: var(--color-neutral-300);
        border-radius: var(--radius-full);
        transition: background-color var(--theme-transition-duration) var(--theme-transition-timing);
      }

      [data-theme="dark"] .switch-track {
        background-color: var(--color-primary-600);
      }

      .switch-thumb {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 1.25rem;
        height: 1.25rem;
        background-color: white;
        border-radius: var(--radius-full);
        transition: transform var(--theme-transition-duration) var(--theme-transition-timing);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
      }

      [data-theme="dark"] .switch-thumb {
        transform: translateX(1.5rem);
      }

      .theme-dropdown {
        position: relative;
        display: inline-block;
      }

      .theme-dropdown-trigger {
        display: flex;
        align-items: center;
        gap: var(--spacing-2);
      }

      .theme-dropdown-overlay {
        position: fixed;
        inset: 0;
        z-index: var(--z-dropdown);
      }

      .theme-dropdown-menu {
        position: absolute;
        top: 100%;
        right: 0;
        min-width: 12rem;
        background-color: var(--color-surface-card);
        border: 1px solid var(--color-border-default);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        z-index: calc(var(--z-dropdown) + 1);
        overflow: hidden;
      }

      .theme-dropdown-item {
        width: 100%;
        display: flex;
        align-items: center;
        gap: var(--spacing-3);
        padding: var(--spacing-2) var(--spacing-3);
        background: none;
        border: none;
        text-align: left;
        cursor: pointer;
        transition: background-color var(--transition-duration-150) var(--transition-timing-inOut);
      }

      .theme-dropdown-item:hover {
        background-color: var(--color-surface-backgroundSecondary);
      }

      .theme-dropdown-item.active {
        background-color: var(--color-primary-50);
        color: var(--color-primary-700);
      }

      [data-theme="dark"] .theme-dropdown-item.active {
        background-color: var(--color-primary-900);
        color: var(--color-primary-200);
      }

      .theme-option-check {
        margin-left: auto;
        color: var(--color-primary-600);
      }

      /* High contrast adjustments */
      @media (prefers-contrast: high) {
        .theme-toggle,
        .theme-dropdown-item {
          border: 1px solid currentColor;
        }
      }

      /* Reduced motion support */
      @media (prefers-reduced-motion: reduce) {
        .${TRANSITION_CLASS} *,
        .${TRANSITION_CLASS} *::before,
        .${TRANSITION_CLASS} *::after,
        .switch-track,
        .switch-thumb {
          transition: none !important;
        }
      }
    `}</style>
  );
}

export default ThemeProvider;