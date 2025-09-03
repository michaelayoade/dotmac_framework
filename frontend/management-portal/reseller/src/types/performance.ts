/**
 * Performance monitoring types
 */

// Core Web Vitals metrics
export interface WebVitalMetric {
  name: 'CLS' | 'FID' | 'LCP' | 'FCP' | 'TTFB';
  value: number;
  entries: PerformanceEntry[];
  id?: string;
  delta?: number;
}

// Memory information from Chrome's performance.memory API
export interface MemoryInfo {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

// Extended Performance interface for Chrome-specific features
export interface ChromePerformance extends Performance {
  memory?: MemoryInfo;
}

// Loading performance metrics
export interface LoadingMetrics {
  domContentLoaded?: number;
  firstPaint?: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
}

// Performance budget configuration
export interface PerformanceBudget {
  bundleSize?: number; // KB
  renderTime?: number; // ms
  memoryUsage?: number; // MB
  firstContentfulPaint?: number; // ms
  largestContentfulPaint?: number; // ms
  cumulativeLayoutShift?: number; // score
  firstInputDelay?: number; // ms
}

// Performance violation details
export interface PerformanceViolation {
  type: keyof PerformanceBudget;
  actual: number;
  budget: number;
  severity: 'warning' | 'error';
  timestamp: number;
}

// Performance monitoring configuration
export interface PerformanceConfig {
  enabled: boolean;
  sampleRate: number; // 0-1, percentage of sessions to monitor
  reportingEndpoint?: string;
  enableDetailedMetrics: boolean;
  enableMemoryMonitoring: boolean;
  enableRenderTracking: boolean;
}

// Timer state for operation timing
export interface TimerState {
  operationName: string;
  startTime: number;
  endTime?: number;
  duration?: number;
}

// Component render metrics
export interface RenderMetrics {
  componentName: string;
  renderCount: number;
  lastRenderTime: number;
  averageRenderTime?: number;
  mountTime?: number;
  unmountTime?: number;
}

// Performance observer entry types
export interface PerformancePaintTiming extends PerformanceEntry {
  startTime: number;
}

export interface PerformanceNavigationTiming extends PerformanceEntry {
  domContentLoadedEventStart: number;
  domContentLoadedEventEnd: number;
  loadEventStart: number;
  loadEventEnd: number;
}

export interface PerformanceLayoutShiftEntry extends PerformanceEntry {
  value: number;
  hadRecentInput: boolean;
  sources: Array<{
    node: Node;
    currentRect: DOMRect;
    previousRect: DOMRect;
  }>;
}

export interface PerformanceFirstInputEntry extends PerformanceEntry {
  processingStart: number;
  cancelable: boolean;
}

// Hook return types
export interface UseOperationTimerReturn {
  startTimer: (operationName: string) => void;
  endTimer: (operationName: string) => number;
  getTimers: () => Map<string, number>;
  clearTimers: () => void;
}

export interface UsePerformanceBudgetReturn {
  violations: PerformanceViolation[];
  isWithinBudget: boolean;
  worstViolation: PerformanceViolation | null;
}

export interface UseMemoryMonitorReturn {
  memoryInfo: MemoryInfo | null;
  isSupported: boolean;
  getMemoryUsageMB: () => number;
}

export interface UseBundlePerformanceReturn {
  loadingMetrics: LoadingMetrics | null;
  isLoading: boolean;
  getMetricsSummary: () => string;
}

// Performance reporting payload
export interface PerformanceReport {
  sessionId: string;
  timestamp: number;
  url: string;
  userAgent: string;
  connectionType?: string;
  metrics: {
    webVitals?: WebVitalMetric[];
    loadingMetrics?: LoadingMetrics;
    memoryInfo?: MemoryInfo;
    customMetrics?: Record<string, number>;
  };
  violations?: PerformanceViolation[];
  context?: {
    userId?: string;
    featureFlags?: string[];
    buildVersion?: string;
  };
}

// Performance monitoring events
export type PerformanceEventType =
  | 'metric-collected'
  | 'budget-violated'
  | 'memory-warning'
  | 'render-slow'
  | 'operation-timeout';

export interface PerformanceEvent {
  type: PerformanceEventType;
  data: any;
  timestamp: number;
}

export type PerformanceEventHandler = (event: PerformanceEvent) => void;
