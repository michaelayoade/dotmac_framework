/**
 * Universal Dashboard Components Package
 * Production-ready, portal-agnostic components for DRY architecture
 *
 * @package @dotmac/dashboard
 * @version 1.0.0
 * @description Universal Dashboard Components - Portal-Agnostic DRY Architecture
 */

// Core Components (DRY - base components only)
export { ActivityFeed, createActivity, ACTIVITY_TEMPLATES } from './components/ActivityFeed/ActivityFeed';
export { MetricsCard, createMetric, createPercentageMetric, createCountMetric, createCurrencyMetric, METRICS_TEMPLATES } from './components/MetricsCard/MetricsCard';
export { ResourceUsageChart, createResourceMetric, createResourceMetrics, RESOURCE_CONFIGS } from './components/ResourceUsageChart/ResourceUsageChart';
export { EntityManagementTable, createTableColumn, createStatusColumn, createEntityAction, TABLE_CONFIGS } from './components/EntityManagementTable/EntityManagementTable';

// Enhanced Components (Leverage existing systems)
export { EnhancedChart, getDefaultChartConfig, CHART_PRESETS } from './components/EnhancedChart/EnhancedChart';
export { RealTimeMetricsCard, getMetricsTransformer, METRICS_CONFIGS } from './components/RealTimeMetricsCard/RealTimeMetricsCard';
export { RealTimeActivityFeed, getPortalEventTypes, getPortalActivityConfig } from './components/RealTimeActivityFeed/RealTimeActivityFeed';
export { DashboardLayout } from './components/DashboardLayout/DashboardLayout';


// Types
export type {
  Activity,
  ResourceMetrics,
  TableColumn,
  EntityAction,
  MetricsCardData,
  ActivityFeedConfig,
  ChartTimeframe,
  PortalVariant,
  DashboardTheme
} from './types';

// Utilities
export { cn } from './utils/cn';
