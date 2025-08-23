/**
 * CSS Custom Properties Generator
 * 
 * Generates CSS custom properties from design tokens
 * Supports runtime theme switching and responsive breakpoints
 */

import { DesignTokens, ThemeName, themes } from '../tokens/design-tokens';

export interface CSSCustomProperties {
  [key: string]: string | number;
}

export interface ThemeCSS {
  light: string;
  dark: string;
  highContrast: string;
}

class ThemeGenerator {
  private tokensToCSSProperties(tokens: DesignTokens, prefix: string = '--'): CSSCustomProperties {
    const cssProperties: CSSCustomProperties = {};
    
    // Convert colors
    this.flattenObject(tokens.colors, `${prefix}color`, cssProperties);
    
    // Convert typography
    this.flattenObject(tokens.typography, `${prefix}font`, cssProperties);
    
    // Convert spacing
    Object.entries(tokens.spacing).forEach(([key, value]) => {
      cssProperties[`${prefix}spacing-${key.replace('.', '-')}`] = value;
    });
    
    // Convert border radius
    Object.entries(tokens.borderRadius).forEach(([key, value]) => {
      cssProperties[`${prefix}radius-${key}`] = value;
    });
    
    // Convert shadows
    Object.entries(tokens.shadows).forEach(([key, value]) => {
      cssProperties[`${prefix}shadow-${key}`] = value;
    });
    
    // Convert breakpoints
    Object.entries(tokens.breakpoints).forEach(([key, value]) => {
      cssProperties[`${prefix}breakpoint-${key}`] = value;
    });
    
    // Convert z-index
    Object.entries(tokens.zIndex).forEach(([key, value]) => {
      cssProperties[`${prefix}z-${key}`] = value;
    });
    
    // Convert transitions
    this.flattenObject(tokens.transitions, `${prefix}transition`, cssProperties);
    
    return cssProperties;
  }
  
  private flattenObject(
    obj: any, 
    prefix: string, 
    result: CSSCustomProperties, 
    separator: string = '-'
  ): void {
    Object.entries(obj).forEach(([key, value]) => {
      const cssKey = `${prefix}${separator}${key.replace('.', '-')}`;
      
      if (typeof value === 'object' && value !== null) {
        this.flattenObject(value, cssKey, result, separator);
      } else {
        result[cssKey] = value as string | number;
      }
    });
  }
  
  private cssPropertiesToString(properties: CSSCustomProperties): string {
    return Object.entries(properties)
      .map(([key, value]) => `  ${key}: ${value};`)
      .join('\n');
  }
  
  generateThemeCSS(): ThemeCSS {
    const lightProperties = this.tokensToCSSProperties(themes.light);
    const darkProperties = this.tokensToCSSProperties(themes.dark);
    const highContrastProperties = this.tokensToCSSProperties(themes.highContrast);
    
    return {
      light: this.cssPropertiesToString(lightProperties),
      dark: this.cssPropertiesToString(darkProperties),
      highContrast: this.cssPropertiesToString(highContrastProperties),
    };
  }
  
  generateFullCSS(): string {
    const themeCSS = this.generateThemeCSS();
    
    return `
/* ISP Management Platform Design System */
/* Auto-generated CSS custom properties */

:root {
${themeCSS.light}
}

[data-theme="dark"] {
${themeCSS.dark}
}

[data-theme="high-contrast"] {
${themeCSS.highContrast}
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
${themeCSS.dark}
  }
}

@media (prefers-contrast: high) {
  :root:not([data-theme]) {
${themeCSS.highContrast}
  }
}

/* Responsive utility classes */
${this.generateResponsiveUtilities()}

/* Component base styles */
${this.generateComponentBaseStyles()}

/* Accessibility utilities */
${this.generateA11yUtilities()}
`;
  }
  
  private generateResponsiveUtilities(): string {
    const breakpoints = themes.light.breakpoints;
    
    let css = '/* Responsive breakpoint utilities */\n';
    
    Object.entries(breakpoints).forEach(([key, value]) => {
      css += `
@media (min-width: ${value}) {
  .${key}\\:block { display: block !important; }
  .${key}\\:hidden { display: none !important; }
  .${key}\\:flex { display: flex !important; }
  .${key}\\:grid { display: grid !important; }
  .${key}\\:inline { display: inline !important; }
  .${key}\\:inline-block { display: inline-block !important; }
}`;
    });
    
    return css;
  }
  
  private generateComponentBaseStyles(): string {
    return `
/* Base component styles */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-default);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  line-height: var(--font-lineHeight-normal);
  transition: all var(--transition-duration-150) var(--transition-timing-inOut);
  cursor: pointer;
  border: 1px solid transparent;
  text-decoration: none;
  
  &:focus-visible {
    outline: 2px solid var(--color-border-focus);
    outline-offset: 2px;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn--primary {
  background-color: var(--color-brand-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-brand-primary);
  
  &:hover:not(:disabled) {
    background-color: var(--color-primary-700);
    border-color: var(--color-primary-700);
  }
}

.btn--secondary {
  background-color: transparent;
  color: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  
  &:hover:not(:disabled) {
    background-color: var(--color-primary-50);
  }
}

.btn--ghost {
  background-color: transparent;
  color: var(--color-text-secondary);
  border-color: transparent;
  
  &:hover:not(:disabled) {
    background-color: var(--color-surface-backgroundSecondary);
  }
}

.card {
  background-color: var(--color-surface-card);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-6);
}

.input {
  width: 100%;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-default);
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-sm);
  line-height: var(--font-lineHeight-normal);
  background-color: var(--color-surface-background);
  color: var(--color-text-primary);
  transition: border-color var(--transition-duration-150) var(--transition-timing-inOut);
  
  &:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 1px var(--color-border-focus);
  }
  
  &:disabled {
    background-color: var(--color-surface-backgroundSecondary);
    color: var(--color-text-disabled);
    cursor: not-allowed;
  }
  
  &::placeholder {
    color: var(--color-text-tertiary);
  }
}

.modal {
  background-color: var(--color-surface-modal);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-2xl);
  max-width: 90vw;
  max-height: 90vh;
  overflow: auto;
}

.overlay {
  background-color: var(--color-surface-overlay);
  backdrop-filter: blur(4px);
}

/* Network status indicators */
.status--online { color: var(--color-network-online); }
.status--offline { color: var(--color-network-offline); }
.status--maintenance { color: var(--color-network-maintenance); }
.status--degraded { color: var(--color-network-degraded); }

/* Service status indicators */
.service--active { color: var(--color-service-active); }
.service--inactive { color: var(--color-service-inactive); }
.service--suspended { color: var(--color-service-suspended); }
.service--pending { color: var(--color-service-pending); }

/* Billing status indicators */
.billing--paid { color: var(--color-billing-paid); }
.billing--unpaid { color: var(--color-billing-unpaid); }
.billing--overdue { color: var(--color-billing-overdue); }
.billing--refunded { color: var(--color-billing-refunded); }`;
  }
  
  private generateA11yUtilities(): string {
    return `
/* Accessibility utilities */
.sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}

.focus-visible {
  &:focus-visible {
    outline: 2px solid var(--color-border-focus);
    outline-offset: 2px;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .btn {
    border-width: 2px;
  }
  
  .input {
    border-width: 2px;
  }
  
  .card {
    border-width: 2px;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Print styles */
@media print {
  .btn {
    border: 1px solid #000 !important;
    background: transparent !important;
  }
  
  .modal,
  .overlay {
    position: static !important;
    box-shadow: none !important;
  }
}`;
  }
  
  generateTokensForPlatform(platform: 'web' | 'mobile' | 'email'): string {
    const tokens = themes.light;
    
    switch (platform) {
      case 'mobile':
        return this.generateMobileTokens(tokens);
      case 'email':
        return this.generateEmailTokens(tokens);
      default:
        return this.generateFullCSS();
    }
  }
  
  private generateMobileTokens(tokens: DesignTokens): string {
    // Mobile-specific token adjustments
    const mobileTokens = {
      ...tokens,
      spacing: {
        ...tokens.spacing,
        // Increase touch targets for mobile
        touchTarget: '44px',
        minTouchTarget: '44px',
      },
      typography: {
        ...tokens.typography,
        fontSize: {
          ...tokens.typography.fontSize,
          // Slightly larger base font size for mobile
          base: '1.125rem', // 18px instead of 16px
        },
      },
    };
    
    return `/* Mobile-optimized tokens */
${this.cssPropertiesToString(this.tokensToCSSProperties(mobileTokens))}

/* Mobile-specific utilities */
.touch-target {
  min-height: var(--spacing-touchTarget);
  min-width: var(--spacing-touchTarget);
}`;
  }
  
  private generateEmailTokens(tokens: DesignTokens): string {
    // Email-safe tokens (more limited)
    return `
/* Email-safe inline styles */
.email-container {
  font-family: ${tokens.typography.fontFamily.sans};
  font-size: ${tokens.typography.fontSize.base};
  line-height: ${tokens.typography.lineHeight.normal};
  color: ${tokens.colors.text.primary};
  background-color: ${tokens.colors.surface.background};
}

.email-button {
  display: inline-block;
  padding: 12px 24px;
  background-color: ${tokens.colors.brand.primary};
  color: ${tokens.colors.text.inverse};
  text-decoration: none;
  border-radius: ${tokens.borderRadius.default};
  font-weight: ${tokens.typography.fontWeight.medium};
}

.email-card {
  background-color: ${tokens.colors.surface.card};
  border: 1px solid ${tokens.colors.border.default};
  border-radius: ${tokens.borderRadius.default};
  padding: 24px;
  margin: 16px 0;
}`;
  }
}

export const themeGenerator = new ThemeGenerator();

// CSS Custom Properties Hook Data
export interface CSSVariables {
  [key: string]: string;
}

export function getCSSVariables(theme: ThemeName = 'light'): CSSVariables {
  const tokens = themes[theme];
  const generator = new ThemeGenerator();
  const properties = (generator as any).tokensToCSSProperties(tokens);
  
  return Object.fromEntries(
    Object.entries(properties).map(([key, value]) => [key, String(value)])
  );
}

export function generateThemeCSS(theme: ThemeName = 'light'): string {
  const tokens = themes[theme];
  const generator = new ThemeGenerator();
  const properties = (generator as any).tokensToCSSProperties(tokens);
  
  return (generator as any).cssPropertiesToString(properties);
}

export default ThemeGenerator;