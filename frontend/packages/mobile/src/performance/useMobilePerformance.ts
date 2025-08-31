/**
 * React Hook for Mobile Performance Optimization
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { MobilePerformanceManager, PerformanceConfig, PerformanceMetrics, BatteryStatus } from './MobilePerformanceManager';

export function useMobilePerformance(config: Partial<PerformanceConfig> = {}) {
  const [manager] = useState(() => new MobilePerformanceManager(config));
  const [metrics, setMetrics] = useState<PerformanceMetrics>(() => manager.getMetrics());
  const [batteryStatus, setBatteryStatus] = useState<BatteryStatus | null>(() => manager.getBatteryStatus());
  const [isLowPowerMode, setIsLowPowerMode] = useState(() => manager.isLowPowerModeActive());

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(manager.getMetrics());
      setBatteryStatus(manager.getBatteryStatus());
      setIsLowPowerMode(manager.isLowPowerModeActive());
    }, 1000);

    return () => {
      clearInterval(interval);
      manager.destroy();
    };
  }, [manager]);

  const preloadImages = useCallback(async (sources: string[]) => {
    return manager.preloadImages(sources);
  }, [manager]);

  const optimizeForBattery = useCallback((enable: boolean) => {
    manager.optimizeForBattery(enable);
  }, [manager]);

  const setAdaptiveQuality = useCallback((enable: boolean) => {
    manager.setAdaptiveQuality(enable);
  }, [manager]);

  return {
    metrics,
    batteryStatus,
    isLowPowerMode,
    preloadImages,
    optimizeForBattery,
    setAdaptiveQuality,
    manager
  };
}

export function useLazyLoading(threshold = 100) {
  const [manager] = useState(() => new MobilePerformanceManager());
  const [observer] = useState(() => manager.createLazyLoader(threshold));
  const elementsRef = useRef<Set<Element>>(new Set());

  const observe = useCallback((element: Element) => {
    if (element && !elementsRef.current.has(element)) {
      observer.observe(element);
      elementsRef.current.add(element);
    }
  }, [observer]);

  const unobserve = useCallback((element: Element) => {
    if (element && elementsRef.current.has(element)) {
      observer.unobserve(element);
      elementsRef.current.delete(element);
    }
  }, [observer]);

  useEffect(() => {
    return () => {
      observer.disconnect();
      manager.destroy();
    };
  }, [observer, manager]);

  return { observe, unobserve };
}

export function useImageOptimization() {
  const { metrics, isLowPowerMode } = useMobilePerformance();
  
  const getOptimalImageUrl = useCallback((
    baseUrl: string,
    width: number,
    height: number,
    quality: 'low' | 'medium' | 'high' | 'auto' = 'auto'
  ): string => {
    // Determine quality based on performance metrics
    let finalQuality = quality;
    
    if (quality === 'auto') {
      if (isLowPowerMode || metrics.networkType === 'slow-2g' || metrics.networkType === '2g') {
        finalQuality = 'low';
      } else if (metrics.networkType === '3g' || metrics.fps < 30) {
        finalQuality = 'medium';
      } else {
        finalQuality = 'high';
      }
    }

    // Apply device pixel ratio
    const dpr = Math.min(window.devicePixelRatio || 1, isLowPowerMode ? 1 : 2);
    const optimizedWidth = Math.round(width * dpr);
    const optimizedHeight = Math.round(height * dpr);

    // Quality mapping
    const qualityValues = {
      low: 60,
      medium: 80,
      high: 95
    };

    // Build optimized URL (assuming image service supports these params)
    const params = new URLSearchParams({
      w: optimizedWidth.toString(),
      h: optimizedHeight.toString(),
      q: qualityValues[finalQuality].toString(),
      f: 'webp'
    });

    return `${baseUrl}?${params.toString()}`;
  }, [metrics, isLowPowerMode]);

  const shouldPreload = useCallback((priority: 'high' | 'medium' | 'low' = 'medium'): boolean => {
    if (isLowPowerMode) return priority === 'high';
    if (metrics.networkType === 'slow-2g' || metrics.networkType === '2g') return priority === 'high';
    if (metrics.networkType === '3g') return priority !== 'low';
    return true;
  }, [metrics, isLowPowerMode]);

  return {
    getOptimalImageUrl,
    shouldPreload,
    isLowPowerMode,
    networkType: metrics.networkType
  };
}

export function useBatteryOptimization() {
  const { batteryStatus, isLowPowerMode } = useMobilePerformance();

  const shouldReduceActivity = useCallback((): boolean => {
    if (!batteryStatus) return false;
    
    return (
      isLowPowerMode ||
      (batteryStatus.level < 30 && !batteryStatus.charging) ||
      (batteryStatus.level < 50 && batteryStatus.dischargingTime < 3600000) // < 1 hour
    );
  }, [batteryStatus, isLowPowerMode]);

  const getRecommendedUpdateInterval = useCallback((baseInterval: number): number => {
    if (!batteryStatus) return baseInterval;
    
    if (isLowPowerMode) return baseInterval * 4;
    if (batteryStatus.level < 30) return baseInterval * 2;
    if (batteryStatus.level < 50) return baseInterval * 1.5;
    
    return baseInterval;
  }, [batteryStatus, isLowPowerMode]);

  const shouldSkipAnimation = useCallback((): boolean => {
    return shouldReduceActivity() || isLowPowerMode;
  }, [shouldReduceActivity, isLowPowerMode]);

  return {
    batteryStatus,
    isLowPowerMode,
    shouldReduceActivity,
    getRecommendedUpdateInterval,
    shouldSkipAnimation
  };
}