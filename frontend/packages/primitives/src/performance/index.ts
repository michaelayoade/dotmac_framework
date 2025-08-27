/**
 * Performance monitoring and optimization utilities
 */

// Performance monitoring components
export { BundleAnalyzer } from './BundleAnalyzer';
export { PerformanceMonitor } from './PerformanceMonitor';

// Types
export type { 
  BundleMetric, 
  BundleAnalysisProps 
} from './BundleAnalyzer';

export type { 
  PerformanceMetrics, 
  PerformanceThresholds, 
  PerformanceMonitorProps 
} from './PerformanceMonitor';

// Performance utilities
export { 
  measurePerformance,
  withPerformanceTracking,
  usePerformanceMetrics,
  optimizeBundle
} from './utils/performance-utils';

// Web Vitals helpers
export {
  getCLS,
  getFCP,
  getFID,
  getLCP,
  getTTFB,
  onCLS,
  onFCP,
  onFID,
  onLCP,
  onTTFB
} from './utils/web-vitals';