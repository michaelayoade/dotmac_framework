/**
 * Performance Monitoring Hook
 * Tracks Core Web Vitals and custom performance metrics
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react';

interface PerformanceMetrics {
  // Core Web Vitals
  fcp?: number; // First Contentful Paint
  lcp?: number; // Largest Contentful Paint
  fid?: number; // First Input Delay
  cls?: number; // Cumulative Layout Shift
  ttfb?: number; // Time to First Byte

  // Custom metrics
  customMetrics: Record<string, number>;

  // Navigation timing
  navigationStart?: number;
  domContentLoaded?: number;
  loadComplete?: number;

  // Resource timing
  resourceCount?: number;
  totalResourceSize?: number;
}

interface PerformanceObserverConfig {
  enableCoreWebVitals?: boolean;
  enableResourceTiming?: boolean;
  enableNavigationTiming?: boolean;
  enableCustomMetrics?: boolean;
  reportingEndpoint?: string;
  reportingInterval?: number;
  enableConsoleLogging?: boolean;
}

const defaultConfig: PerformanceObserverConfig = {
  enableCoreWebVitals: true,
  enableResourceTiming: true,
  enableNavigationTiming: true,
  enableCustomMetrics: true,
  reportingInterval: 30000, // 30 seconds
  enableConsoleLogging: process.env.NODE_ENV === 'development',
};

// Composition helpers for performance monitoring
const PerformanceObservers = {
  createCoreWebVitalsObserver: (
    metrics: PerformanceMetrics,
    _config: PerformanceObserverConfig
  ) => {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        PerformanceObservers.processEntry(entry, metrics);
      }
    });

    const entryTypes = [
      'paint',
      'largest-contentful-paint',
      'first-input',
      'layout-shift',
      'navigation',
    ];
    entryTypes.forEach((type) => {
      try {
        observer.observe({ entryTypes: [type] });
      } catch (_e) {
        // Silently ignore observer type not supported
      }
    });

    return observer;
  },

  processEntry: (entry: PerformanceEntry, metrics: PerformanceMetrics): void => {
    switch (entry.entryType) {
      case 'paint':
        if (entry.name === 'first-contentful-paint') {
          metrics.fcp = entry.startTime;
        }
        break;
      case 'largest-contentful-paint':
        metrics.lcp = entry.startTime;
        break;
      case 'first-input':
        metrics.fid =
          (entry as unknown as { processingStart: number }).processingStart - entry.startTime;
        break;
      case 'layout-shift':
        if (!(entry as unknown as { hadRecentInput: boolean }).hadRecentInput) {
          metrics.cls = (metrics.cls || 0) + (entry as unknown as { value: number }).value;
        }
        break;
      case 'navigation': {
        const navEntry = entry as PerformanceNavigationTiming;
        metrics.ttfb = navEntry.responseStart - navEntry.requestStart;
        break;
      }
    }
  },

  createResourceObserver: (metrics: PerformanceMetrics) => {
    const observer = new PerformanceObserver((list) => {
      const resourceEntries = list.getEntries() as PerformanceResourceTiming[];
      metrics.resourceCount = (metrics.resourceCount || 0) + resourceEntries.length;

      const totalSize = resourceEntries.reduce((sum, entry) => sum + (entry.transferSize || 0), 0);
      metrics.totalResourceSize = (metrics.totalResourceSize || 0) + totalSize;
    });

    observer.observe({ entryTypes: ['resource'] });
    return observer;
  },

  createNavigationObserver: (metrics: PerformanceMetrics) => {
    const observer = new PerformanceObserver((list) => {
      const navEntries = list.getEntries() as PerformanceNavigationTiming[];
      for (const entry of navEntries) {
        metrics.navigationStart = entry.navigationStart;
        metrics.domContentLoaded = entry.domContentLoadedEventEnd - entry.navigationStart;
        metrics.loadComplete = entry.loadEventEnd - entry.navigationStart;
      }
    });

    observer.observe({ entryTypes: ['navigation'] });
    return observer;
  },
};

const MetricTrackers = {
  trackCustom: (
    metrics: PerformanceMetrics,
    name: string,
    value: number,
    enableLogging: boolean
  ) => {
    metrics.customMetrics[name] = value;
    if (enableLogging) {
      console.log(`📊 Custom metric tracked: ${name} = ${value}`);
    }
  },

  trackInteraction: (
    name: string,
    startTime: number | undefined,
    trackCustomMetric: (name: string, value: number) => void
  ) => {
    const endTime = performance.now();
    const duration = startTime ? endTime - startTime : endTime;
    trackCustomMetric(`interaction_${name}`, duration);
  },

  trackApiCall: (
    endpoint: string,
    duration: number,
    success: boolean,
    trackCustomMetric: (name: string, value: number) => void
  ) => {
    const cleanEndpoint = endpoint.replace(/[^a-zA-Z0-9]/g, '_');
    trackCustomMetric(`api_${cleanEndpoint}_duration`, duration);
    trackCustomMetric(`api_${cleanEndpoint}_success`, success ? 1 : 0);
  },

  trackComponentRender: (
    componentName: string,
    renderTime: number,
    trackCustomMetric: (name: string, value: number) => void
  ) => {
    trackCustomMetric(`component_${componentName}_render`, renderTime);
  },
};

export function usePerformanceMonitoring(
  config: PerformanceObserverConfig = {
    // Implementation pending
  }
) {
  const finalConfig = useMemo(() => ({ ...defaultConfig, ...config }), [config]);
  const metricsRef = useRef<PerformanceMetrics>({
    customMetrics: {
      // Implementation pending
    },
  });
  const observersRef = useRef<PerformanceObserver[]>([]);
  const reportingTimerRef = useRef<NodeJS.Timeout>();

  // Initialize performance observers
  useEffect(() => {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
      return;
    }

    const metrics = metricsRef.current;
    const observers: PerformanceObserver[] = [];

    const observerConfigs = [
      {
        enabled: finalConfig.enableCoreWebVitals,
        create: () => PerformanceObservers.createCoreWebVitalsObserver(metrics, finalConfig),
        name: 'Core Web Vitals',
      },
      {
        enabled: finalConfig.enableResourceTiming,
        create: () => PerformanceObservers.createResourceObserver(metrics),
        name: 'Resource Timing',
      },
      {
        enabled: finalConfig.enableNavigationTiming,
        create: () => PerformanceObservers.createNavigationObserver(metrics),
        name: 'Navigation Timing',
      },
    ];

    observerConfigs.forEach(({ enabled, create, name }) => {
      if (enabled) {
        try {
          const observer = create();
          observers.push(observer);
        } catch (_error) {
          if (finalConfig.enableConsoleLogging) {
            console.warn(`Failed to create ${name} observer:`, name);
          }
        }
      }
    });

    observersRef.current = observers;

    return () => {
      // Cleanup observers
      observersRef.current.forEach((observer) => observer.disconnect());
      observersRef.current = [];
    };
  }, [finalConfig]);

  // Setup reporting interval
  useEffect(() => {
    if (finalConfig.reportingInterval && finalConfig.reportingInterval > 0) {
      reportingTimerRef.current = setInterval(() => {
        reportMetrics(metricsRef.current, finalConfig);
      }, finalConfig.reportingInterval);

      return () => {
        if (reportingTimerRef.current) {
          clearInterval(reportingTimerRef.current);
        }
      };
    }
  }, [finalConfig]);

  // Custom metric tracking
  const trackCustomMetric = useCallback(
    (name: string, value: number) => {
      if (!finalConfig.enableCustomMetrics) {
        return;
      }

      MetricTrackers.trackCustom(
        metricsRef.current,
        name,
        value,
        finalConfig.enableConsoleLogging ?? false
      );
    },
    [finalConfig.enableCustomMetrics, finalConfig.enableConsoleLogging]
  );

  // Track user interaction timing
  const trackInteraction = useCallback(
    (interactionName: string, startTime?: number) => {
      MetricTrackers.trackInteraction(interactionName, startTime, trackCustomMetric);
    },
    [trackCustomMetric]
  );

  // Track API call timing
  const trackApiCall = useCallback(
    (endpoint: string, duration: number, success: boolean) => {
      MetricTrackers.trackApiCall(endpoint, duration, success, trackCustomMetric);
    },
    [trackCustomMetric]
  );

  // Track component render timing
  const trackComponentRender = useCallback(
    (componentName: string, renderTime: number) => {
      MetricTrackers.trackComponentRender(componentName, renderTime, trackCustomMetric);
    },
    [trackCustomMetric]
  );

  // Get current metrics
  const getMetrics = useCallback(() => {
    return { ...metricsRef.current };
  }, []);

  // Manual reporting trigger
  const reportNow = useCallback(() => {
    reportMetrics(metricsRef.current, finalConfig);
  }, [finalConfig]);

  return {
    trackCustomMetric,
    trackInteraction,
    trackApiCall,
    trackComponentRender,
    getMetrics,
    reportNow,
  };
}

// Helper functions to reduce complexity
function logMetric(label: string, value: number | undefined, formatter: (v: number) => string) {
  if (value !== undefined) {
    console.log(`${label}: ${formatter(value)}`);
  }
}

function logWebVitalMetrics(metrics: PerformanceMetrics) {
  logMetric('🎨 First Contentful Paint', metrics.fcp, (v) => `${v.toFixed(2)}ms`);
  logMetric('🖼️ Largest Contentful Paint', metrics.lcp, (v) => `${v.toFixed(2)}ms`);
  logMetric('👆 First Input Delay', metrics.fid, (v) => `${v.toFixed(2)}ms`);
  logMetric('📐 Cumulative Layout Shift', metrics.cls, (v) => v.toFixed(4));
  logMetric('🌐 Time to First Byte', metrics.ttfb, (v) => `${v.toFixed(2)}ms`);
}

function logLoadMetrics(metrics: PerformanceMetrics) {
  logMetric('📄 DOM Content Loaded', metrics.domContentLoaded, (v) => `${v.toFixed(2)}ms`);
  logMetric('✅ Load Complete', metrics.loadComplete, (v) => `${v.toFixed(2)}ms`);
  logMetric('📦 Resource Count', metrics.resourceCount, (v) => v.toString());
  logMetric(
    '💾 Total Resource Size',
    metrics.totalResourceSize,
    (v) => `${(v / 1024).toFixed(2)}KB`
  );
}

function logCustomMetrics(customMetrics: Record<string, unknown>) {
  if (Object.keys(customMetrics).length > 0) {
    console.log('🔧 Custom Metrics:');
    for (const [name, value] of Object.entries(customMetrics)) {
      console.log(`  ${name}: ${value}`);
    }
  }
}

function logMetricsToConsole(metrics: PerformanceMetrics) {
  logWebVitalMetrics(metrics);
  logLoadMetrics(metrics);
  logCustomMetrics(metrics.customMetrics);
}

function sendMetricsToEndpoint(
  metrics: PerformanceMetrics,
  endpoint: string,
  enableLogging: boolean
) {
  const payload = {
    timestamp: new Date().toISOString(),
    url: window.location.href,
    userAgent: navigator.userAgent,
    metrics,
  };

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch((_error) => {
    if (enableLogging) {
      console.error('Failed to send metrics to endpoint:', endpoint);
    }
  });
}

function sendMetricsToGoogleAnalytics(metrics: PerformanceMetrics) {
  const gtag = (window as any).gtag;
  if (!gtag) {
    return;
  }

  const events = [
    { metric: metrics.fcp, event: 'first_contentful_paint' },
    { metric: metrics.lcp, event: 'largest_contentful_paint' },
    { metric: metrics.fid, event: 'first_input_delay' },
    { metric: metrics.cls, event: 'cumulative_layout_shift', multiplier: 1000 },
  ];

  events.forEach(({ metric, event, multiplier = 1 }) => {
    if (metric !== undefined) {
      gtag('event', event, { value: Math.round(metric * multiplier) });
    }
  });
}

// Helper function to report metrics
function reportMetrics(metrics: PerformanceMetrics, config: PerformanceObserverConfig) {
  if (config.enableConsoleLogging) {
    logMetricsToConsole(metrics);
  }

  if (config.reportingEndpoint) {
    sendMetricsToEndpoint(metrics, config.reportingEndpoint, config.enableConsoleLogging ?? false);
  }

  if (typeof window !== 'undefined' && (window as any).gtag) {
    sendMetricsToGoogleAnalytics(metrics);
  }
}

// React component to wrap apps with performance monitoring
export const PerformanceMonitor: React.FC<{
  children: React.ReactNode;
  config?: PerformanceObserverConfig;
}> = ({ children, config }) => {
  usePerformanceMonitoring(config);
  return React.createElement(
    React.Fragment,
    {
      // Implementation pending
    },
    children
  );
};

// HOC for component performance tracking
export function withPerformanceTracking<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName?: string
) {
  const ComponentWithPerformanceTracking = (props: P) => {
    const { trackComponentRender } = usePerformanceMonitoring();
    const renderStartTime = useRef<number>();

    useEffect(() => {
      renderStartTime.current = performance.now();
    });

    useEffect(() => {
      if (renderStartTime.current) {
        const renderDuration = performance.now() - renderStartTime.current;
        trackComponentRender(
          componentName || WrappedComponent.displayName || WrappedComponent.name || 'Component',
          renderDuration
        );
      }
    });

    return React.createElement(WrappedComponent, props);
  };

  ComponentWithPerformanceTracking.displayName = `withPerformanceTracking(${componentName || WrappedComponent.displayName || WrappedComponent.name})`;

  return ComponentWithPerformanceTracking;
}

// Custom hook for API call performance tracking
export function useApiPerformanceTracking() {
  const { trackApiCall } = usePerformanceMonitoring();

  const trackApiRequest = useCallback(
    async <T>(endpoint: string, apiCall: () => Promise<T>): Promise<T> => {
      const startTime = performance.now();
      let success = false;

      try {
        const result = await apiCall();
        success = true;
        return result;
      } catch (error) {
        success = false;
        throw error;
      } finally {
        const duration = performance.now() - startTime;
        trackApiCall(endpoint, duration, success);
      }
    },
    [trackApiCall]
  );

  return { trackApiRequest };
}
