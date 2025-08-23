/**
 * Performance Monitoring System
 *
 * Monitors component performance, Web Vitals, and provides
 * actionable insights for optimization
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  getCLS,
  getFCP,
  getFID,
  getLCP,
  getTTFB,
  Metric,
  onCLS,
  onFCP,
  onFID,
  onLCP,
  onTTFB,
} from 'web-vitals';

// Performance metric types
export interface PerformanceMetrics {
  // Web Vitals
  cls?: number; // Cumulative Layout Shift
  fcp?: number; // First Contentful Paint
  fid?: number; // First Input Delay
  lcp?: number; // Largest Contentful Paint
  ttfb?: number; // Time to First Byte

  // Component-specific metrics
  renderTime?: number; // Component render time
  mountTime?: number; // Time to mount
  updateCount?: number; // Number of re-renders
  memoryUsage?: number; // Memory usage (if available)

  // Custom metrics
  [key: string]: number | undefined;
}

export interface PerformanceReport {
  componentName: string;
  metrics: PerformanceMetrics;
  timestamp: Date;
  warnings: PerformanceWarning[];
  recommendations: string[];
}

export interface PerformanceWarning {
  metric: string;
  value: number;
  threshold: number;
  severity: 'low' | 'medium' | 'high';
  message: string;
}

export interface PerformanceThresholds {
  cls: number;
  fcp: number;
  fid: number;
  lcp: number;
  ttfb: number;
  renderTime: number;
  memoryUsage: number;
}

// Default performance thresholds based on Web Vitals
const DEFAULT_THRESHOLDS: PerformanceThresholds = {
  cls: 0.1, // Good: ≤ 0.1
  fcp: 1800, // Good: ≤ 1.8s
  fid: 100, // Good: ≤ 100ms
  lcp: 2500, // Good: ≤ 2.5s
  ttfb: 800, // Good: ≤ 800ms
  renderTime: 16, // 60fps = ~16ms per frame
  memoryUsage: 50 * 1024 * 1024, // 50MB
};

export interface PerformanceMonitorProps {
  children: React.ReactNode;
  componentName?: string;
  thresholds?: Partial<PerformanceThresholds>;
  onReport?: (report: PerformanceReport) => void;
  enableWebVitals?: boolean;
  enableComponentMetrics?: boolean;
  reportInterval?: number; // milliseconds
  disabled?: boolean;
}

export function PerformanceMonitor({
  children,
  componentName = 'UnknownComponent',
  thresholds = {},
  onReport,
  enableWebVitals = true,
  enableComponentMetrics = true,
  reportInterval = 30000, // 30 seconds
  disabled = false,
}: PerformanceMonitorProps) {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({});
  const [updateCount, setUpdateCount] = useState(0);
  const mountTimeRef = useRef<number>();
  const renderStartTimeRef = useRef<number>();
  const reportIntervalRef = useRef<NodeJS.Timeout>();

  const finalThresholds = { ...DEFAULT_THRESHOLDS, ...thresholds };

  // Component performance tracking
  useEffect(() => {
    if (disabled || !enableComponentMetrics) return;

    mountTimeRef.current = performance.now();

    return () => {
      // Cleanup
      if (reportIntervalRef.current) {
        clearInterval(reportIntervalRef.current);
      }
    };
  }, [disabled, enableComponentMetrics]);

  // Track render performance
  useEffect(() => {
    if (disabled || !enableComponentMetrics) return;

    const renderEndTime = performance.now();
    if (renderStartTimeRef.current) {
      const renderTime = renderEndTime - renderStartTimeRef.current;
      setMetrics((prev) => ({
        ...prev,
        renderTime,
        updateCount: updateCount + 1,
      }));
    }

    setUpdateCount((prev) => prev + 1);
  });

  // Measure render start time
  renderStartTimeRef.current = performance.now();

  // Web Vitals monitoring
  useEffect(() => {
    if (disabled || !enableWebVitals) return;

    const handleMetric = (metric: Metric) => {
      setMetrics((prev) => ({
        ...prev,
        [metric.name.toLowerCase()]: metric.value,
      }));
    };

    // Set up Web Vitals listeners
    onCLS(handleMetric);
    onFCP(handleMetric);
    onFID(handleMetric);
    onLCP(handleMetric);
    onTTFB(handleMetric);

    // Get current metrics immediately
    getCLS(handleMetric);
    getFCP(handleMetric);
    getFID(handleMetric);
    getLCP(handleMetric);
    getTTFB(handleMetric);
  }, [disabled, enableWebVitals]);

  // Memory usage tracking
  useEffect(() => {
    if (disabled || !enableComponentMetrics) return;

    const trackMemory = () => {
      if ('memory' in performance) {
        const memInfo = (performance as any).memory;
        setMetrics((prev) => ({
          ...prev,
          memoryUsage: memInfo.usedJSHeapSize,
        }));
      }
    };

    trackMemory();
    const memoryInterval = setInterval(trackMemory, 5000); // Every 5 seconds

    return () => clearInterval(memoryInterval);
  }, [disabled, enableComponentMetrics]);

  // Generate performance report
  const generateReport = useCallback((): PerformanceReport => {
    const warnings: PerformanceWarning[] = [];
    const recommendations: string[] = [];

    // Check thresholds and generate warnings
    Object.entries(finalThresholds).forEach(([metric, threshold]) => {
      const value = metrics[metric as keyof PerformanceMetrics];
      if (value && value > threshold) {
        let severity: 'low' | 'medium' | 'high' = 'low';
        let message = '';

        switch (metric) {
          case 'cls':
            severity = value > 0.25 ? 'high' : value > 0.1 ? 'medium' : 'low';
            message = `Cumulative Layout Shift is ${value.toFixed(3)}. Minimize unexpected layout shifts.`;
            recommendations.push(
              'Ensure images and ads have dimensions, avoid inserting content above existing content'
            );
            break;
          case 'fcp':
            severity = value > 3000 ? 'high' : value > 1800 ? 'medium' : 'low';
            message = `First Contentful Paint is ${value.toFixed(0)}ms. Optimize loading performance.`;
            recommendations.push(
              'Optimize fonts, reduce server response time, eliminate render-blocking resources'
            );
            break;
          case 'fid':
            severity = value > 300 ? 'high' : value > 100 ? 'medium' : 'low';
            message = `First Input Delay is ${value.toFixed(0)}ms. Improve interactivity.`;
            recommendations.push(
              'Break up long tasks, use code splitting, minimize JavaScript execution time'
            );
            break;
          case 'lcp':
            severity = value > 4000 ? 'high' : value > 2500 ? 'medium' : 'low';
            message = `Largest Contentful Paint is ${value.toFixed(0)}ms. Speed up largest element loading.`;
            recommendations.push(
              'Optimize images, preload important resources, minimize CSS and JavaScript'
            );
            break;
          case 'renderTime':
            severity = value > 32 ? 'high' : value > 16 ? 'medium' : 'low';
            message = `Component render time is ${value.toFixed(2)}ms. Consider optimization.`;
            recommendations.push(
              'Use React.memo, useMemo, useCallback, or virtualization for large lists'
            );
            break;
          case 'memoryUsage':
            severity =
              value > 100 * 1024 * 1024 ? 'high' : value > 50 * 1024 * 1024 ? 'medium' : 'low';
            message = `Memory usage is ${(value / 1024 / 1024).toFixed(1)}MB. Monitor for memory leaks.`;
            recommendations.push(
              'Check for memory leaks, optimize data structures, clean up event listeners'
            );
            break;
          default:
            message = `${metric} is ${value} (threshold: ${threshold})`;
        }

        warnings.push({
          metric,
          value,
          threshold,
          severity,
          message,
        });
      }
    });

    // Additional recommendations based on metrics
    if (metrics.updateCount && metrics.updateCount > 10) {
      recommendations.push(
        'High number of re-renders detected. Consider memoization or state optimization.'
      );
    }

    return {
      componentName,
      metrics,
      timestamp: new Date(),
      warnings,
      recommendations,
    };
  }, [componentName, metrics, finalThresholds]);

  // Periodic reporting
  useEffect(() => {
    if (disabled || !onReport) return;

    reportIntervalRef.current = setInterval(() => {
      const report = generateReport();
      onReport(report);
    }, reportInterval);

    return () => {
      if (reportIntervalRef.current) {
        clearInterval(reportIntervalRef.current);
      }
    };
  }, [disabled, onReport, reportInterval, generateReport]);

  // Report on unmount
  useEffect(() => {
    return () => {
      if (onReport && !disabled) {
        const report = generateReport();
        onReport(report);
      }
    };
  }, [onReport, disabled, generateReport]);

  if (disabled) {
    return <>{children}</>;
  }

  return <>{children}</>;
}

// Hook for accessing performance metrics
export function usePerformanceMetrics(componentName: string) {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({});
  const [isTracking, setIsTracking] = useState(false);
  const startTimeRef = useRef<number>();

  const startTracking = useCallback(() => {
    startTimeRef.current = performance.now();
    setIsTracking(true);
  }, []);

  const stopTracking = useCallback(() => {
    if (startTimeRef.current) {
      const endTime = performance.now();
      const renderTime = endTime - startTimeRef.current;

      setMetrics((prev) => ({
        ...prev,
        renderTime,
      }));

      setIsTracking(false);
    }
  }, []);

  const addCustomMetric = useCallback((key: string, value: number) => {
    setMetrics((prev) => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  return {
    metrics,
    isTracking,
    startTracking,
    stopTracking,
    addCustomMetric,
  };
}

// HOC for automatic performance monitoring
export function withPerformanceMonitoring<P extends object>(
  Component: React.ComponentType<P>,
  options: Omit<PerformanceMonitorProps, 'children'> = {}
) {
  const WrappedComponent = React.forwardRef<any, P>((props, ref) => {
    const componentName =
      options.componentName || Component.displayName || Component.name || 'Anonymous';

    return (
      <PerformanceMonitor {...options} componentName={componentName}>
        <Component {...props} ref={ref} />
      </PerformanceMonitor>
    );
  });

  WrappedComponent.displayName = `withPerformanceMonitoring(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

// Performance metrics aggregator
export class PerformanceAggregator {
  private reports: PerformanceReport[] = [];
  private listeners: ((report: PerformanceReport) => void)[] = [];

  addReport(report: PerformanceReport) {
    this.reports.push(report);
    this.listeners.forEach((listener) => listener(report));

    // Keep only last 1000 reports to prevent memory issues
    if (this.reports.length > 1000) {
      this.reports = this.reports.slice(-1000);
    }
  }

  onReport(listener: (report: PerformanceReport) => void) {
    this.listeners.push(listener);

    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  getReports(componentName?: string, limit?: number): PerformanceReport[] {
    let filtered = this.reports;

    if (componentName) {
      filtered = filtered.filter((report) => report.componentName === componentName);
    }

    if (limit) {
      filtered = filtered.slice(-limit);
    }

    return filtered;
  }

  getAverageMetrics(componentName?: string): PerformanceMetrics {
    const reports = this.getReports(componentName);
    if (reports.length === 0) return {};

    const aggregated: Record<string, number[]> = {};

    reports.forEach((report) => {
      Object.entries(report.metrics).forEach(([key, value]) => {
        if (typeof value === 'number') {
          if (!aggregated[key]) {
            aggregated[key] = [];
          }
          aggregated[key].push(value);
        }
      });
    });

    const averages: PerformanceMetrics = {};

    Object.entries(aggregated).forEach(([key, values]) => {
      averages[key] = values.reduce((sum, val) => sum + val, 0) / values.length;
    });

    return averages;
  }

  clear() {
    this.reports = [];
  }
}

// Global performance aggregator instance
export const performanceAggregator = new PerformanceAggregator();
