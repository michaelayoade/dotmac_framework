/**
 * @dotmac/patterns - Template & Foundation Components
 *
 * Production-ready portal templates with shared component foundation
 */

// Templates
export { ManagementPageTemplate } from './templates/ManagementPageTemplate';

export { DashboardTemplate } from './templates/DashboardTemplate';

export { WorkflowTemplate, useWorkflow } from './templates/WorkflowTemplate';

// Template Factories
export {
  createManagementPage,
  createDashboardPage,
  createWorkflowPage,
  createAdminManagementPage,
  createCustomerDashboard,
  createResellerDashboard,
  createTechnicianWorkflow,
  createManagementDashboard,
  createStandardMetrics,
  createStandardFilters,
  PORTAL_THEMES,
  type PortalType,
  type PortalTheme,
  type TemplateFactoryOptions,
  type CreateManagementPageOptions,
  type CreateDashboardPageOptions,
  type CreateWorkflowPageOptions,
} from './factories/templateFactories';

// Shared Primitives
export {
  SidePanelDrawer,
  useSidePanel,
  FilterToolbar,
  SavedViews,
  type SidePanelDrawerProps,
  type SidePanelAction,
  type FilterToolbarProps,
  type FilterValue,
  type SavedViewsProps,
} from './primitives';

// Layout Components
export {
  LayoutProvider,
  LayoutRoot,
  LayoutHeader,
  LayoutSidebar,
  LayoutMain,
  LayoutFooter,
  LayoutContainer,
  LayoutGrid,
  AppLayout,
  useLayout,
} from './composition/Layout';

// Theming
export {
  PortalThemeProvider,
  usePortalTheme,
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
  importTheme,
  type PortalThemeProviderProps,
  type PortalThemeContextValue,
} from './theming';

// Type Definitions
export {
  BaseTemplateConfigSchema,
  ManagementPageConfigSchema,
  DashboardConfigSchema,
  WorkflowConfigSchema,
  ActionConfigSchema,
  FilterConfigSchema,
  SavedViewConfigSchema,
  ChartConfigSchema,
  MetricConfigSchema,
  WorkflowStepConfigSchema,
  TemplateConfigSchemas,
  isManagementPageConfig,
  isDashboardConfig,
  isWorkflowConfig,
  validateTemplateConfig,
  type BaseTemplateConfig,
  type ManagementPageConfig,
  type DashboardConfig,
  type WorkflowConfig,
  type ActionConfig,
  type FilterConfig,
  type SavedViewConfig,
  type ChartConfig,
  type MetricConfig,
  type WorkflowStepConfig,
  type TemplateState,
  type TemplateContextValue,
} from './types/templates';

// Version
export const VERSION = '1.0.0';
