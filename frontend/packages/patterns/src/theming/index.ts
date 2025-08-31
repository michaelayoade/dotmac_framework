/**
 * Theming Index
 * Export all theming utilities and components
 */

export { 
  PortalThemeProvider,
  usePortalTheme,
  type PortalThemeProviderProps,
  type PortalThemeContextValue
} from './PortalThemeProvider';

export {
  hexToRgb,
  rgbToHsl,
  adjustColor,
  generateColorScheme,
  getDensitySpacing,
  getDensityComponentSizes,
  generateThemeCSS,
  getContrastRatio,
  isAccessibleContrast,
  findAccessibleColor,
  validateTheme,
  exportTheme,
  importTheme
} from './themeUtilities';