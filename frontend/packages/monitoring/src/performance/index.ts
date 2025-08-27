import React from 'react';
import { usePerformanceMonitor } from './PerformanceHooks';

// Performance Monitor
export { PerformanceMonitor } from './PerformanceMonitor';
export type { 
  PerformanceMetrics, 
  PerformanceBudget, 
  PerformanceAlert 
} from './PerformanceMonitor';

// Performance Hooks
export {
  initializePerformanceMonitor,
  getPerformanceMonitor,
  usePerformanceMonitor,
  useRenderMetrics,
  useInteractionMetrics,
  useMemoryMonitor,
  useFPSMonitor,
  useBundleMonitor,
  useCoreWebVitals,
  usePerformanceAlerts
} from './PerformanceHooks';

// Performance Dashboard
export { PerformanceDashboard } from './PerformanceDashboard';

// Performance Optimizer
export { PerformanceOptimizer } from './PerformanceOptimizer';
export type { OptimizationRule, OptimizationSuggestion } from './PerformanceOptimizer';

// Default performance budgets for different application types
export const PERFORMANCE_BUDGETS = {
  STRICT: {
    renderTime: 10,
    interactionTime: 50,
    memoryUsage: 50 * 1024 * 1024, // 50MB
    bundleSize: 1 * 1024 * 1024, // 1MB
    networkLatency: 300,
    errorRate: 1,
    fps: 55
  },
  MODERATE: {
    renderTime: 16,
    interactionTime: 100,
    memoryUsage: 100 * 1024 * 1024, // 100MB
    bundleSize: 2 * 1024 * 1024, // 2MB
    networkLatency: 500,
    errorRate: 3,
    fps: 50
  },
  RELAXED: {
    renderTime: 33,
    interactionTime: 200,
    memoryUsage: 200 * 1024 * 1024, // 200MB
    bundleSize: 5 * 1024 * 1024, // 5MB
    networkLatency: 1000,
    errorRate: 5,
    fps: 30
  }
};

// Utility functions
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
};

export const getPerformanceGrade = (
  metric: number, 
  thresholds: { good: number; poor: number }
): 'A' | 'B' | 'C' | 'D' | 'F' => {
  if (metric <= thresholds.good) return 'A';
  if (metric <= thresholds.good * 1.2) return 'B';
  if (metric <= thresholds.poor) return 'C';
  if (metric <= thresholds.poor * 1.5) return 'D';
  return 'F';
};

// React component wrapper for performance monitoring
export const withPerformanceMonitoring = <P extends object>(
  Component: React.ComponentType<P>,
  componentName: string
) => {
  return React.forwardRef<any, P>((props, ref) => {
    const { measureRender } = usePerformanceMonitor(componentName);
    
    return measureRender(() => (
      <Component {...props} ref={ref} />
    ));
  });
};

// HOC for measuring component render performance
export const measureComponentPerformance = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  displayName?: string
) => {
  const MeasuredComponent = (props: P) => {
    const componentName = displayName || WrappedComponent.displayName || WrappedComponent.name || 'Component';
    const { measureRender } = usePerformanceMonitor(componentName);

    const [renderCount, setRenderCount] = React.useState(0);
    
    React.useEffect(() => {
      setRenderCount(prev => prev + 1);
    });

    return measureRender(() => {
      performance.mark(`${componentName}-render-${renderCount}-start`);
      const result = <WrappedComponent {...props} />;
      performance.mark(`${componentName}-render-${renderCount}-end`);
      performance.measure(
        `${componentName}-render-${renderCount}`,
        `${componentName}-render-${renderCount}-start`,
        `${componentName}-render-${renderCount}-end`
      );
      return result;
    });
  };

  MeasuredComponent.displayName = `withPerformanceMonitoring(${displayName || WrappedComponent.displayName || WrappedComponent.name})`;
  
  return MeasuredComponent;
};

// Performance testing utilities
export const performanceTest = {
  render: async (component: () => JSX.Element, iterations = 100) => {
    const times: number[] = [];
    
    for (let i = 0; i < iterations; i++) {
      const start = performance.now();
      component();
      const end = performance.now();
      times.push(end - start);
    }
    
    return {
      average: times.reduce((a, b) => a + b, 0) / times.length,
      median: times.sort((a, b) => a - b)[Math.floor(times.length / 2)],
      min: Math.min(...times),
      max: Math.max(...times),
      p95: times.sort((a, b) => a - b)[Math.floor(times.length * 0.95)],
      p99: times.sort((a, b) => a - b)[Math.floor(times.length * 0.99)]
    };
  },
  
  memory: () => {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return {
        used: memory.usedJSHeapSize,
        total: memory.totalJSHeapSize,
        limit: memory.jsHeapSizeLimit
      };
    }
    return null;
  },
  
  timing: () => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (!navigation) return null;
    
    return {
      dns: navigation.domainLookupEnd - navigation.domainLookupStart,
      tcp: navigation.connectEnd - navigation.connectStart,
      request: navigation.responseStart - navigation.requestStart,
      response: navigation.responseEnd - navigation.responseStart,
      dom: navigation.domContentLoadedEventEnd - navigation.navigationStart,
      load: navigation.loadEventEnd - navigation.navigationStart
    };
  }
};
