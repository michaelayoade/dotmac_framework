import { useState, useEffect, useCallback } from 'react';

interface PerformanceMetrics {
  fcp: number | null; // First Contentful Paint
  lcp: number | null; // Largest Contentful Paint
  fid: number | null; // First Input Delay
  cls: number | null; // Cumulative Layout Shift
  ttfb: number | null; // Time to First Byte
  domContentLoaded: number | null;
  loadComplete: number | null;
}

interface PerformanceBudget {
  fcp: number;
  lcp: number;
  fid: number;
  cls: number;
  ttfb: number;
}

const DEFAULT_BUDGET: PerformanceBudget = {
  fcp: 1800, // 1.8s
  lcp: 2500, // 2.5s
  fid: 100,  // 100ms
  cls: 0.1,  // 0.1
  ttfb: 800, // 800ms
};

export const usePerformanceMonitor = (budget: Partial<PerformanceBudget> = {}) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fcp: null,
    lcp: null,
    fid: null,
    cls: null,
    ttfb: null,
    domContentLoaded: null,
    loadComplete: null,
  });

  const [budgetViolations, setBudgetViolations] = useState<string[]>([]);
  const performanceBudget = { ...DEFAULT_BUDGET, ...budget };

  const checkBudgetViolations = useCallback((currentMetrics: PerformanceMetrics) => {
    const violations: string[] = [];

    if (currentMetrics.fcp && currentMetrics.fcp > performanceBudget.fcp) {
      violations.push(`FCP exceeded budget: ${currentMetrics.fcp}ms > ${performanceBudget.fcp}ms`);
    }
    if (currentMetrics.lcp && currentMetrics.lcp > performanceBudget.lcp) {
      violations.push(`LCP exceeded budget: ${currentMetrics.lcp}ms > ${performanceBudget.lcp}ms`);
    }
    if (currentMetrics.fid && currentMetrics.fid > performanceBudget.fid) {
      violations.push(`FID exceeded budget: ${currentMetrics.fid}ms > ${performanceBudget.fid}ms`);
    }
    if (currentMetrics.cls && currentMetrics.cls > performanceBudget.cls) {
      violations.push(`CLS exceeded budget: ${currentMetrics.cls} > ${performanceBudget.cls}`);
    }
    if (currentMetrics.ttfb && currentMetrics.ttfb > performanceBudget.ttfb) {
      violations.push(`TTFB exceeded budget: ${currentMetrics.ttfb}ms > ${performanceBudget.ttfb}ms`);
    }

    setBudgetViolations(violations);
  }, [performanceBudget]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('performance' in window)) return;

    const updateMetrics = (newMetrics: Partial<PerformanceMetrics>) => {
      setMetrics(prev => {
        const updated = { ...prev, ...newMetrics };
        checkBudgetViolations(updated);
        return updated;
      });
    };

    // Navigation Timing API
    const getNavigationTiming = () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navigation) {
        updateMetrics({
          ttfb: navigation.responseStart - navigation.fetchStart,
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
          loadComplete: navigation.loadEventEnd - navigation.fetchStart,
        });
      }
    };

    // Performance Observer for Web Vitals
    const observePerformance = () => {
      try {
        // First Contentful Paint
        new PerformanceObserver((entryList) => {
          for (const entry of entryList.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
              updateMetrics({ fcp: entry.startTime });
            }
          }
        }).observe({ entryTypes: ['paint'] });

        // Largest Contentful Paint
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries();
          const lastEntry = entries[entries.length - 1] as any;
          if (lastEntry) {
            updateMetrics({ lcp: lastEntry.startTime });
          }
        }).observe({ entryTypes: ['largest-contentful-paint'] });

        // First Input Delay
        new PerformanceObserver((entryList) => {
          for (const entry of entryList.getEntries()) {
            const fidEntry = entry as any;
            if (fidEntry.processingStart) {
              updateMetrics({ fid: fidEntry.processingStart - fidEntry.startTime });
            }
          }
        }).observe({ entryTypes: ['first-input'] });

        // Cumulative Layout Shift
        let clsValue = 0;
        new PerformanceObserver((entryList) => {
          for (const entry of entryList.getEntries()) {
            const clsEntry = entry as any;
            if (!clsEntry.hadRecentInput) {
              clsValue += clsEntry.value;
              updateMetrics({ cls: clsValue });
            }
          }
        }).observe({ entryTypes: ['layout-shift'] });

      } catch (error) {
        console.warn('Performance Observer not supported or failed:', error);
      }
    };

    // Wait for page load to get navigation timing
    if (document.readyState === 'complete') {
      getNavigationTiming();
    } else {
      window.addEventListener('load', getNavigationTiming);
    }

    observePerformance();

    return () => {
      window.removeEventListener('load', getNavigationTiming);
    };
  }, [checkBudgetViolations]);

  const reportMetrics = useCallback(() => {
    // Report to analytics service
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('performance:metrics', {
        detail: {
          metrics,
          budgetViolations,
          timestamp: new Date().toISOString(),
          url: window.location.href,
        }
      }));
    }
  }, [metrics, budgetViolations]);

  const getPerformanceScore = useCallback((): number => {
    let score = 100;
    const weights = { fcp: 15, lcp: 25, fid: 25, cls: 25, ttfb: 10 };

    Object.entries(weights).forEach(([metric, weight]) => {
      const value = metrics[metric as keyof PerformanceMetrics];
      const budget = performanceBudget[metric as keyof PerformanceBudget];
      
      if (value !== null && value > budget) {
        const violation = Math.min((value / budget - 1) * 100, weight);
        score -= violation;
      }
    });

    return Math.max(0, Math.round(score));
  }, [metrics, performanceBudget]);

  return {
    metrics,
    budgetViolations,
    performanceScore: getPerformanceScore(),
    reportMetrics,
    budget: performanceBudget,
  };
};