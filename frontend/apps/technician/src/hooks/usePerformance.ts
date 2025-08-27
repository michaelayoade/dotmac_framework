/**
 * Performance Hook
 * React hook for performance monitoring and optimization
 */

import { useEffect, useCallback, useRef, useState, useMemo } from 'react';
import { performanceMonitor } from '../lib/performance/monitoring';
import { 
  debounce, 
  throttle, 
  memoizeWithTTL,
  frameRateMonitor,
  memoryManager
} from '../lib/performance/optimization';

interface PerformanceMetrics {
  renderCount: number;
  lastRenderTime: number;
  averageRenderTime: number;
  memoryUsage?: {
    used: number;
    total: number;
    limit: number;
  };
  fps?: number;
}

interface UsePerformanceOptions {
  trackRenders?: boolean;
  trackMemory?: boolean;
  trackFPS?: boolean;
  componentName?: string;
  debounceMs?: number;
  throttleMs?: number;
}

export function usePerformance(options: UsePerformanceOptions = {}) {
  const {
    trackRenders = true,
    trackMemory = false,
    trackFPS = false,
    componentName = 'UnknownComponent',
    debounceMs = 300,
    throttleMs = 100,
  } = options;

  const renderCount = useRef(0);
  const renderTimes = useRef<number[]>([]);
  const startTime = useRef<number>(0);
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    renderCount: 0,
    lastRenderTime: 0,
    averageRenderTime: 0,
  });

  // Track component renders
  useEffect(() => {
    if (trackRenders) {
      const endTime = performance.now();
      const renderTime = endTime - startTime.current;
      
      renderCount.current++;
      renderTimes.current.push(renderTime);
      
      // Keep only last 100 render times
      if (renderTimes.current.length > 100) {
        renderTimes.current = renderTimes.current.slice(-100);
      }

      const averageRenderTime = renderTimes.current.reduce((a, b) => a + b, 0) / renderTimes.current.length;

      performanceMonitor.recordMetric({
        name: 'component_render',
        value: renderTime,
        timestamp: Date.now(),
        context: {
          componentName,
          renderCount: renderCount.current,
        },
        tags: ['component-performance'],
      });

      setMetrics(prev => ({
        ...prev,
        renderCount: renderCount.current,
        lastRenderTime: renderTime,
        averageRenderTime,
      }));
    }

    startTime.current = performance.now();
  });

  // Track memory usage
  useEffect(() => {
    if (!trackMemory) return;

    const updateMemoryUsage = () => {
      const memoryUsage = memoryManager.getMemoryUsage();
      if (memoryUsage) {
        setMetrics(prev => ({ ...prev, memoryUsage }));
        
        performanceMonitor.recordMetric({
          name: 'memory_usage',
          value: memoryUsage.used,
          timestamp: Date.now(),
          context: {
            componentName,
            total: memoryUsage.total,
            limit: memoryUsage.limit,
            percentage: (memoryUsage.used / memoryUsage.limit) * 100,
          },
          tags: ['memory-tracking'],
        });
      }
    };

    const interval = setInterval(updateMemoryUsage, 5000); // Every 5 seconds
    memoryManager.addTimer(interval);
    updateMemoryUsage();

    return () => clearInterval(interval);
  }, [trackMemory, componentName]);

  // Track FPS
  useEffect(() => {
    if (!trackFPS) return;

    frameRateMonitor.start();
    
    const fpsInterval = setInterval(() => {
      // FPS is automatically recorded by frameRateMonitor
      // We just trigger a re-render to update UI if needed
      const lastFPSMetric = performanceMonitor.getReport().customMetrics
        .filter(m => m.name === 'fps')
        .pop();
      
      if (lastFPSMetric) {
        setMetrics(prev => ({ ...prev, fps: lastFPSMetric.value }));
      }
    }, 1000);

    memoryManager.addTimer(fpsInterval);

    return () => {
      frameRateMonitor.stop();
      clearInterval(fpsInterval);
    };
  }, [trackFPS]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      memoryManager.cleanup();
    };
  }, []);

  // Performance utilities
  const measureOperation = useCallback(<T,>(
    operationName: string,
    operation: () => T,
    metadata?: Record<string, any>
  ): T => {
    return performanceMonitor.measureComponentRender(
      `${componentName}_${operationName}`,
      operation,
      metadata
    );
  }, [componentName]);

  const measureAsyncOperation = useCallback(<T,>(
    operationName: string,
    operation: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> => {
    return performanceMonitor.measureAsyncOperation(
      `${componentName}_${operationName}`,
      operation,
      metadata
    );
  }, [componentName]);

  const recordUserAction = useCallback((
    type: 'CLICK' | 'NAVIGATION' | 'FORM_SUBMIT' | 'API_CALL' | 'SEARCH' | 'SCAN',
    element?: string,
    metadata?: Record<string, any>
  ) => {
    performanceMonitor.recordUserAction({
      type,
      element,
      page: window.location.pathname,
      timestamp: Date.now(),
      success: true,
      metadata,
    });
  }, []);

  const startTiming = useCallback((id: string, name: string, metadata?: Record<string, any>) => {
    performanceMonitor.startTiming(`${componentName}_${id}`, name, metadata);
  }, [componentName]);

  const endTiming = useCallback((id: string, metadata?: Record<string, any>) => {
    return performanceMonitor.endTiming(`${componentName}_${id}`, metadata);
  }, [componentName]);

  // Optimization utilities
  const debouncedCallback = useCallback(<T extends (...args: any[]) => any>(
    callback: T,
    deps: any[] = []
  ): T => {
    return useCallback(
      debounce(callback, debounceMs),
      deps
    ) as T;
  }, [debounceMs]);

  const throttledCallback = useCallback(<T extends (...args: any[]) => any>(
    callback: T,
    deps: any[] = []
  ): T => {
    return useCallback(
      throttle(callback, throttleMs),
      deps
    ) as T;
  }, [throttleMs]);

  const memoizedValue = useCallback(<T>(
    computeValue: () => T,
    deps: any[],
    ttl?: number
  ): T => {
    const memoizedCompute = memoizeWithTTL(computeValue, ttl);
    return useMemo(memoizedCompute, deps);
  }, []);

  const isSlowRender = metrics.lastRenderTime > 16; // Slower than 60fps
  const isHighMemoryUsage = metrics.memoryUsage 
    ? (metrics.memoryUsage.used / metrics.memoryUsage.limit) > 0.8 
    : false;
  const isLowFPS = metrics.fps !== undefined ? metrics.fps < 30 : false;

  return {
    // Metrics
    metrics,
    isSlowRender,
    isHighMemoryUsage,
    isLowFPS,
    
    // Measurement utilities
    measureOperation,
    measureAsyncOperation,
    recordUserAction,
    startTiming,
    endTiming,
    
    // Optimization utilities
    debouncedCallback,
    throttledCallback,
    memoizedValue,
  };
}

// Hook for monitoring specific operations
export function useOperationTracking(operationName: string, componentName?: string) {
  const timingId = useRef<string | null>(null);

  const startOperation = useCallback((metadata?: Record<string, any>) => {
    const id = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    timingId.current = id;
    
    performanceMonitor.startTiming(
      componentName ? `${componentName}_${id}` : id,
      operationName,
      metadata
    );
  }, [operationName, componentName]);

  const endOperation = useCallback((metadata?: Record<string, any>) => {
    if (timingId.current) {
      const duration = performanceMonitor.endTiming(
        componentName ? `${componentName}_${timingId.current}` : timingId.current,
        metadata
      );
      timingId.current = null;
      return duration;
    }
    return null;
  }, [componentName]);

  const measureOperation = useCallback(<T,>(
    operation: () => T,
    metadata?: Record<string, any>
  ): T => {
    startOperation(metadata);
    try {
      const result = operation();
      endOperation({ ...metadata, success: true });
      return result;
    } catch (error) {
      endOperation({ ...metadata, success: false, error: error.message });
      throw error;
    }
  }, [startOperation, endOperation]);

  const measureAsyncOperation = useCallback(<T,>(
    operation: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> => {
    startOperation(metadata);
    return operation()
      .then((result) => {
        endOperation({ ...metadata, success: true });
        return result;
      })
      .catch((error) => {
        endOperation({ ...metadata, success: false, error: error.message });
        throw error;
      });
  }, [startOperation, endOperation]);

  return {
    startOperation,
    endOperation,
    measureOperation,
    measureAsyncOperation,
  };
}

// Hook for bundle analysis
export function useBundleAnalysis() {
  const [bundleInfo, setBundleInfo] = useState<{
    totalSize: number;
    resources: Array<{ name: string; size: number; type: string }>;
  } | null>(null);

  useEffect(() => {
    const analyzeBundleSize = async () => {
      const { analyzeBundleSize: analyze } = await import('../lib/performance/optimization');
      const info = await analyze();
      setBundleInfo(info);
    };

    // Delay analysis until after initial render
    const timer = setTimeout(analyzeBundleSize, 1000);
    return () => clearTimeout(timer);
  }, []);

  return bundleInfo;
}