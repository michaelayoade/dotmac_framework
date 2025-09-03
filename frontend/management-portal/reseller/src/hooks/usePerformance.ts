import { useEffect, useRef, useState, useCallback } from 'react';
import type {
  MemoryInfo,
  ChromePerformance,
  LoadingMetrics,
  PerformanceBudget,
  PerformanceViolation,
  UseOperationTimerReturn,
  UsePerformanceBudgetReturn,
  UseMemoryMonitorReturn,
  UseBundlePerformanceReturn,
  WebVitalMetric,
  PerformancePaintTiming,
  PerformanceNavigationTiming,
  PerformanceLayoutShiftEntry,
  PerformanceFirstInputEntry,
} from '@/types/performance';
import { environmentConfig } from '@/lib/config/environment';

// Performance monitoring hook
export function usePerformanceMonitor(componentName: string) {
  const renderStartTime = useRef<number>(Date.now());
  const mountTime = useRef<number | null>(null);

  useEffect(() => {
    // Record component mount time
    mountTime.current = Date.now();
    const mountDuration = mountTime.current - renderStartTime.current;

    // Log mount performance in development
    if (environmentConfig.enableDebugLogs) {
      console.log(`[Performance] ${componentName} mounted in ${mountDuration}ms`);
    }

    // Report to performance monitoring service in production
    if (environmentConfig.isProduction && 'performance' in window) {
      window.performance.mark(`${componentName}-mount-end`);
      window.performance.measure(
        `${componentName}-mount-duration`,
        `${componentName}-mount-start`,
        `${componentName}-mount-end`
      );
    }

    return () => {
      if (process.env.NODE_ENV === 'development') {
        const unmountTime = Date.now();
        const lifetimeDuration = unmountTime - (mountTime.current || renderStartTime.current);
        console.log(`[Performance] ${componentName} unmounted after ${lifetimeDuration}ms`);
      }
    };
  }, [componentName]);

  // Mark render start
  useEffect(() => {
    renderStartTime.current = Date.now();
    if (process.env.NODE_ENV === 'production' && 'performance' in window) {
      window.performance.mark(`${componentName}-mount-start`);
    }
  });
}

// Hook for measuring expensive operations
export function useOperationTimer(): UseOperationTimerReturn {
  const timers = useRef<Map<string, number>>(new Map());

  const startTimer = useCallback((operationName: string) => {
    timers.current.set(operationName, Date.now());
  }, []);

  const endTimer = useCallback((operationName: string) => {
    const startTime = timers.current.get(operationName);
    if (!startTime) {
      console.warn(`Timer '${operationName}' was not started`);
      return 0;
    }

    const duration = Date.now() - startTime;
    timers.current.delete(operationName);

    if (environmentConfig.enableDebugLogs) {
      console.log(`[Performance] Operation '${operationName}' took ${duration}ms`);
    }

    return duration;
  }, []);

  const getTimers = useCallback(() => timers.current, []);
  const clearTimers = useCallback(() => timers.current.clear(), []);

  return { startTimer, endTimer, getTimers, clearTimers };
}

// Hook for monitoring render performance
export function useRenderTime(componentName: string, dependencies: any[] = []) {
  const renderCount = useRef(0);
  const lastRenderTime = useRef<number>(Date.now());

  useEffect(() => {
    renderCount.current += 1;
    const currentTime = Date.now();
    const timeSinceLastRender = currentTime - lastRenderTime.current;
    lastRenderTime.current = currentTime;

    if (process.env.NODE_ENV === 'development') {
      console.log(
        `[Render] ${componentName} render #${renderCount.current} (${timeSinceLastRender}ms since last render)`
      );
    }
  }, dependencies);
}

// Hook for tracking memory usage
export function useMemoryMonitor(componentName: string): UseMemoryMonitorReturn {
  const [memoryInfo, setMemoryInfo] = useState<MemoryInfo | null>(null);

  useEffect(() => {
    // Only available in Chrome
    if ('memory' in performance) {
      const chromePerf = performance as ChromePerformance;
      const memory = chromePerf.memory;
      if (memory) {
        setMemoryInfo({
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit,
        });

        if (environmentConfig.enableDebugLogs) {
          const usedMB = (memory.usedJSHeapSize / 1024 / 1024).toFixed(2);
          const totalMB = (memory.totalJSHeapSize / 1024 / 1024).toFixed(2);
          console.log(`[Memory] ${componentName} - Used: ${usedMB}MB, Total: ${totalMB}MB`);
        }
      }
    }
  }, [componentName]);

  const isSupported = 'memory' in performance;
  const getMemoryUsageMB = useCallback(() => {
    return memoryInfo ? memoryInfo.usedJSHeapSize / 1024 / 1024 : 0;
  }, [memoryInfo]);

  return { memoryInfo, isSupported, getMemoryUsageMB };
}

// Hook for monitoring bundle size and loading performance
export function useBundlePerformance(): UseBundlePerformanceReturn {
  const [loadingMetrics, setLoadingMetrics] = useState<LoadingMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    if (typeof window === 'undefined' || !('performance' in window)) return () => {};

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'navigation') {
          const navigation = entry as PerformanceNavigationTiming;
          setLoadingMetrics((prev) => ({
            ...prev,
            domContentLoaded:
              navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
          }));
        }

        if (entry.entryType === 'paint') {
          const paint = entry as PerformancePaintTiming;
          setLoadingMetrics((prev) => ({
            ...prev,
            [paint.name === 'first-paint' ? 'firstPaint' : 'firstContentfulPaint']: paint.startTime,
          }));
        }

        if (entry.entryType === 'largest-contentful-paint') {
          const lcp = entry as PerformancePaintTiming;
          setLoadingMetrics((prev) => ({
            ...prev,
            largestContentfulPaint: lcp.startTime,
          }));
          setIsLoading(false); // LCP is usually the last meaningful loading metric
        }
      }
    });

    observer.observe({ entryTypes: ['navigation', 'paint', 'largest-contentful-paint'] });

    return () => observer.disconnect();
  }, []);

  const getMetricsSummary = useCallback(() => {
    if (!loadingMetrics) return 'No metrics available';

    const metrics = [
      loadingMetrics.firstPaint && `FP: ${loadingMetrics.firstPaint.toFixed(0)}ms`,
      loadingMetrics.firstContentfulPaint &&
        `FCP: ${loadingMetrics.firstContentfulPaint.toFixed(0)}ms`,
      loadingMetrics.largestContentfulPaint &&
        `LCP: ${loadingMetrics.largestContentfulPaint.toFixed(0)}ms`,
      loadingMetrics.domContentLoaded && `DCL: ${loadingMetrics.domContentLoaded.toFixed(0)}ms`,
    ]
      .filter(Boolean)
      .join(', ');

    return metrics || 'Loading...';
  }, [loadingMetrics]);

  return { loadingMetrics, isLoading, getMetricsSummary };
}

// Utility for tracking Core Web Vitals
export function measureCoreWebVitals(callback: (metric: WebVitalMetric) => void): void {
  // This would typically integrate with web-vitals library
  // For now, we'll use basic Performance API measurements

  if (typeof window === 'undefined' || !('performance' in window)) return;

  // Cumulative Layout Shift (CLS)
  let clsValue = 0;
  let clsEntries: PerformanceEntry[] = [];

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType === 'layout-shift') {
        const layoutShift = entry as PerformanceLayoutShiftEntry;
        if (!layoutShift.hadRecentInput) {
          clsValue += layoutShift.value;
          clsEntries.push(entry);
        }
      }
    }
  });

  observer.observe({ entryTypes: ['layout-shift'] });

  // Report CLS after page load
  window.addEventListener('beforeunload', () => {
    callback({
      name: 'CLS',
      value: clsValue,
      entries: clsEntries,
    });
  });

  // First Input Delay (FID) - would be better with web-vitals library
  const fidObserver = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType === 'first-input') {
        const firstInput = entry as PerformanceFirstInputEntry;
        callback({
          name: 'FID',
          value: firstInput.processingStart - entry.startTime,
          entries: [entry],
        });
      }
    }
  });

  fidObserver.observe({ entryTypes: ['first-input'] });
}

// Performance budget alerts
export function usePerformanceBudget(budgets: PerformanceBudget): UsePerformanceBudgetReturn {
  const [violations, setViolations] = useState<PerformanceViolation[]>([]);

  useEffect(() => {
    const checkBudgets = () => {
      const newViolations: PerformanceViolation[] = [];

      // Check memory budget
      if (budgets.memoryUsage && 'memory' in performance) {
        const chromePerf = performance as ChromePerformance;
        const memory = chromePerf.memory;
        if (memory) {
          const usedMB = memory.usedJSHeapSize / 1024 / 1024;
          if (usedMB > budgets.memoryUsage) {
            newViolations.push({
              type: 'memoryUsage',
              actual: usedMB,
              budget: budgets.memoryUsage,
              severity: usedMB > budgets.memoryUsage * 1.5 ? 'error' : 'warning',
              timestamp: Date.now(),
            });
          }
        }
      }

      // Check render time budget using Performance API
      if (budgets.renderTime) {
        const measures = performance.getEntriesByType('measure');
        const recentRenderMeasures = measures.filter(
          (m) => m.name.includes('render') && m.startTime > Date.now() - 5000 // Last 5 seconds
        );

        for (const measure of recentRenderMeasures) {
          if (measure.duration > budgets.renderTime) {
            newViolations.push({
              type: 'renderTime',
              actual: measure.duration,
              budget: budgets.renderTime,
              severity: measure.duration > budgets.renderTime * 2 ? 'error' : 'warning',
              timestamp: Date.now(),
            });
          }
        }
      }

      setViolations(newViolations);

      if (newViolations.length > 0 && environmentConfig.enableDebugLogs) {
        console.warn('[Performance Budget] Violations detected:', newViolations);
      }
    };

    const interval = setInterval(checkBudgets, 5000); // Check every 5 seconds
    checkBudgets(); // Check immediately

    return () => clearInterval(interval);
  }, [budgets]);

  const isWithinBudget = violations.length === 0;
  const worstViolation = violations.reduce<PerformanceViolation | null>((worst, current) => {
    if (!worst) return current;
    if (current.severity === 'error' && worst.severity === 'warning') return current;
    if (current.severity === worst.severity && current.actual > worst.actual) return current;
    return worst;
  }, null);

  return { violations, isWithinBudget, worstViolation };
}
