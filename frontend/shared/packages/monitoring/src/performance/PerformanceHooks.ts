import { useEffect, useRef, useState, useCallback } from 'react';
import { PerformanceMonitor, PerformanceMetrics, PerformanceBudget } from './PerformanceMonitor';

// Global performance monitor instance
let globalMonitor: PerformanceMonitor | null = null;

export const initializePerformanceMonitor = (budget: PerformanceBudget) => {
  if (!globalMonitor) {
    globalMonitor = new PerformanceMonitor(budget);
  }
  return globalMonitor;
};

export const getPerformanceMonitor = (): PerformanceMonitor | null => {
  return globalMonitor;
};

// Hook for component-level performance monitoring
export const usePerformanceMonitor = (componentName: string) => {
  const mountTimeRef = useRef<number>(0);
  const renderCountRef = useRef<number>(0);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);

  useEffect(() => {
    mountTimeRef.current = performance.now();

    if (globalMonitor) {
      performance.mark(`${componentName}-mount-start`);
    }

    return () => {
      if (globalMonitor && mountTimeRef.current) {
        const mountTime = performance.now() - mountTimeRef.current;
        performance.mark(`${componentName}-mount-end`);
        performance.measure(
          `${componentName}-mount`,
          `${componentName}-mount-start`,
          `${componentName}-mount-end`
        );

        // Record component mount time
        globalMonitor.recordError = globalMonitor.recordError.bind(globalMonitor);
      }
    };
  }, [componentName]);

  useEffect(() => {
    renderCountRef.current++;

    if (globalMonitor) {
      const currentMetrics = globalMonitor.getMetrics(componentName);
      if (currentMetrics) {
        setMetrics(currentMetrics);
      }
    }
  });

  const measureRender = useCallback(
    <T>(renderFn: () => T): T => {
      if (!globalMonitor) return renderFn();
      return globalMonitor.measureRender(componentName, renderFn);
    },
    [componentName]
  );

  const measureInteraction = useCallback(
    <T>(interactionName: string, interactionFn: () => T): T => {
      if (!globalMonitor) return interactionFn();
      return globalMonitor.measureInteraction(`${componentName}-${interactionName}`, interactionFn);
    },
    [componentName]
  );

  const measureAsync = useCallback(
    async <T>(name: string, asyncFn: () => Promise<T>): Promise<T> => {
      if (!globalMonitor) return asyncFn();
      return globalMonitor.measureAsync(`${componentName}-${name}`, asyncFn);
    },
    [componentName]
  );

  const recordError = useCallback(
    (operation: string, error: Error) => {
      if (globalMonitor) {
        globalMonitor.recordError(`${componentName}-${operation}`, error);
      }
    },
    [componentName]
  );

  return {
    metrics,
    renderCount: renderCountRef.current,
    measureRender,
    measureInteraction,
    measureAsync,
    recordError,
  };
};

// Hook for measuring render performance
export const useRenderMetrics = (componentName: string) => {
  const renderStartRef = useRef<number>(0);
  const [renderTime, setRenderTime] = useState<number>(0);
  const [renderCount, setRenderCount] = useState<number>(0);

  useEffect(() => {
    renderStartRef.current = performance.now();
    setRenderCount((prev) => prev + 1);
  });

  useEffect(() => {
    const renderEnd = performance.now();
    const currentRenderTime = renderEnd - renderStartRef.current;
    setRenderTime(currentRenderTime);

    if (globalMonitor) {
      globalMonitor.measureRender(componentName, () => currentRenderTime);
    }
  });

  return { renderTime, renderCount };
};

// Hook for measuring interaction performance
export const useInteractionMetrics = () => {
  const [interactionTimes, setInteractionTimes] = useState<Map<string, number>>(new Map());

  const measureInteraction = useCallback(<T>(name: string, fn: () => T): T => {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    const duration = end - start;

    setInteractionTimes((prev) => new Map(prev.set(name, duration)));

    if (globalMonitor) {
      globalMonitor.measureInteraction(name, () => result);
    }

    return result;
  }, []);

  const measureAsyncInteraction = useCallback(
    async <T>(name: string, fn: () => Promise<T>): Promise<T> => {
      const start = performance.now();
      const result = await fn();
      const end = performance.now();
      const duration = end - start;

      setInteractionTimes((prev) => new Map(prev.set(name, duration)));

      if (globalMonitor) {
        await globalMonitor.measureAsync(name, async () => result);
      }

      return result;
    },
    []
  );

  return {
    interactionTimes: Object.fromEntries(interactionTimes),
    measureInteraction,
    measureAsyncInteraction,
  };
};

// Hook for memory monitoring
export const useMemoryMonitor = () => {
  const [memoryUsage, setMemoryUsage] = useState<{
    used: number;
    total: number;
    percentage: number;
  } | null>(null);

  useEffect(() => {
    const updateMemoryUsage = () => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        const used = memory.usedJSHeapSize;
        const total = memory.jsHeapSizeLimit;
        const percentage = (used / total) * 100;

        setMemoryUsage({ used, total, percentage });

        // Alert if memory usage is high
        if (percentage > 80) {
          console.warn(`High memory usage detected: ${percentage.toFixed(2)}%`);
        }
      }
    };

    updateMemoryUsage();
    const interval = setInterval(updateMemoryUsage, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return memoryUsage;
};

// Hook for FPS monitoring
export const useFPSMonitor = () => {
  const [fps, setFPS] = useState<number>(60);
  const frameCountRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(performance.now());
  const rafRef = useRef<number>();

  useEffect(() => {
    const measureFPS = () => {
      frameCountRef.current++;
      const now = performance.now();

      if (now - lastTimeRef.current >= 1000) {
        const currentFPS = Math.round((frameCountRef.current * 1000) / (now - lastTimeRef.current));
        setFPS(currentFPS);
        frameCountRef.current = 0;
        lastTimeRef.current = now;

        // Alert if FPS is low
        if (currentFPS < 30) {
          console.warn(`Low FPS detected: ${currentFPS} fps`);
        }
      }

      rafRef.current = requestAnimationFrame(measureFPS);
    };

    rafRef.current = requestAnimationFrame(measureFPS);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  return fps;
};

// Hook for bundle size monitoring
export const useBundleMonitor = () => {
  const [bundleSize, setBundleSize] = useState<{
    totalSize: number;
    compressedSize: number;
    assets: Array<{ name: string; size: number; type: string }>;
  } | null>(null);

  useEffect(() => {
    const measureBundleSize = () => {
      if ('getEntriesByType' in performance) {
        const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
        let totalSize = 0;
        let compressedSize = 0;
        const assets: Array<{ name: string; size: number; type: string }> = [];

        resources.forEach((resource) => {
          if (
            resource.name.includes('.js') ||
            resource.name.includes('.css') ||
            resource.name.includes('.woff')
          ) {
            const size = resource.transferSize || resource.decodedBodySize || 0;
            const compressedResourceSize = resource.encodedBodySize || size;

            totalSize += size;
            compressedSize += compressedResourceSize;

            assets.push({
              name: resource.name.split('/').pop() || resource.name,
              size,
              type: resource.name.includes('.js')
                ? 'javascript'
                : resource.name.includes('.css')
                  ? 'stylesheet'
                  : resource.name.includes('.woff')
                    ? 'font'
                    : 'other',
            });
          }
        });

        setBundleSize({ totalSize, compressedSize, assets });
      }
    };

    // Delay measurement to allow all resources to load
    const timer = setTimeout(measureBundleSize, 2000);
    return () => clearTimeout(timer);
  }, []);

  return bundleSize;
};

// Hook for Core Web Vitals monitoring
export const useCoreWebVitals = () => {
  const [vitals, setVitals] = useState<{
    fcp: number | null; // First Contentful Paint
    lcp: number | null; // Largest Contentful Paint
    fid: number | null; // First Input Delay
    cls: number | null; // Cumulative Layout Shift
    ttfb: number | null; // Time to First Byte
  }>({
    fcp: null,
    lcp: null,
    fid: null,
    cls: null,
    ttfb: null,
  });

  useEffect(() => {
    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        switch (entry.entryType) {
          case 'paint':
            if (entry.name === 'first-contentful-paint') {
              setVitals((prev) => ({ ...prev, fcp: entry.startTime }));
            }
            break;
          case 'largest-contentful-paint':
            setVitals((prev) => ({ ...prev, lcp: entry.startTime }));
            break;
          case 'first-input':
            setVitals((prev) => ({
              ...prev,
              fid: (entry as any).processingStart - entry.startTime,
            }));
            break;
          case 'layout-shift':
            if (!(entry as any).hadRecentInput) {
              setVitals((prev) => ({ ...prev, cls: (prev.cls || 0) + (entry as any).value }));
            }
            break;
          case 'navigation':
            const navEntry = entry as PerformanceNavigationTiming;
            setVitals((prev) => ({
              ...prev,
              ttfb: navEntry.responseStart - navEntry.requestStart,
            }));
            break;
        }
      });
    });

    try {
      observer.observe({
        entryTypes: [
          'paint',
          'largest-contentful-paint',
          'first-input',
          'layout-shift',
          'navigation',
        ],
      });
    } catch (error) {
      console.warn('Some performance metrics may not be available in this browser');
    }

    return () => observer.disconnect();
  }, []);

  return vitals;
};

// Hook for performance alerts
export const usePerformanceAlerts = () => {
  const [alerts, setAlerts] = useState<
    Array<{
      type: string;
      message: string;
      severity: 'info' | 'warning' | 'error';
      timestamp: Date;
    }>
  >([]);

  useEffect(() => {
    if (!globalMonitor) return;

    const handleBudgetExceeded = (alert: any) => {
      setAlerts((prev) => [
        ...prev,
        {
          type: 'budget',
          message: `${alert.metric} exceeded budget: ${alert.value.toFixed(2)}ms (limit: ${alert.threshold}ms)`,
          severity: alert.severity === 'critical' ? 'error' : 'warning',
          timestamp: alert.timestamp,
        },
      ]);
    };

    const handleLongTask = (task: any) => {
      setAlerts((prev) => [
        ...prev,
        {
          type: 'longtask',
          message: `Long task detected: ${task.duration.toFixed(2)}ms`,
          severity: 'warning',
          timestamp: new Date(),
        },
      ]);
    };

    const handleError = (error: any) => {
      setAlerts((prev) => [
        ...prev,
        {
          type: 'error',
          message: `Error in ${error.operation}: ${error.error}`,
          severity: 'error',
          timestamp: error.timestamp,
        },
      ]);
    };

    globalMonitor.on('budgetExceeded', handleBudgetExceeded);
    globalMonitor.on('longTask', handleLongTask);
    globalMonitor.on('error', handleError);

    return () => {
      globalMonitor?.off('budgetExceeded', handleBudgetExceeded);
      globalMonitor?.off('longTask', handleLongTask);
      globalMonitor?.off('error', handleError);
    };
  }, []);

  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  return { alerts, clearAlerts };
};
