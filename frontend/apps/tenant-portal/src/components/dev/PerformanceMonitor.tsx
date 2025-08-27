/**
 * Performance Monitor Component
 * Development tool for monitoring and analyzing performance metrics
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { 
  getPerformanceMonitor,
  type PerformanceReport,
  measurePerformance,
  markPerformance,
  measureBetween
} from '@/lib/performance-monitoring';
import { getRequestCache } from '@/lib/caching-strategies';
import { AssetPerformanceMonitor } from '@/lib/asset-optimization';
import { AccessibleButton } from '@/components/ui/AccessibleForm';

// Only show in development
const isDev = process.env.NODE_ENV === 'development';

interface PerformanceMonitorProps {
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function PerformanceMonitorComponent({
  position = 'bottom-left',
  autoRefresh = true,
  refreshInterval = 5000,
}: PerformanceMonitorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [assetMetrics, setAssetMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'performance' | 'cache' | 'assets'>('performance');

  // Only render in development
  if (!isDev) return null;

  const refreshMetrics = useCallback(async () => {
    setIsLoading(true);
    try {
      const monitor = getPerformanceMonitor();
      const cache = getRequestCache();
      
      // Get performance report
      const performanceReport = monitor.generateReport();
      setReport(performanceReport);
      
      // Get cache stats
      const stats = cache.getStats();
      setCacheStats(stats);
      
      // Get asset metrics
      const assets = AssetPerformanceMonitor.monitorAssetLoading();
      setAssetMetrics(assets);
    } catch (error) {
      console.error('Failed to refresh performance metrics:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      refreshMetrics();
    }
  }, [isOpen, refreshMetrics]);

  useEffect(() => {
    if (autoRefresh && isOpen) {
      const interval = setInterval(refreshMetrics, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, isOpen, refreshInterval, refreshMetrics]);

  const getPositionClasses = () => {
    const base = 'fixed z-50';
    switch (position) {
      case 'bottom-right':
        return `${base} bottom-4 right-4`;
      case 'bottom-left':
        return `${base} bottom-4 left-4`;
      case 'top-right':
        return `${base} top-4 right-4`;
      case 'top-left':
        return `${base} top-4 left-4`;
      default:
        return `${base} bottom-4 left-4`;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className={getPositionClasses()}>
      {!isOpen && (
        <AccessibleButton
          onClick={() => setIsOpen(true)}
          variant="secondary"
          className="rounded-full w-12 h-12 shadow-lg border-2 border-purple-500"
          aria-label="Open performance monitor"
        >
          <span className="text-lg">⚡</span>
        </AccessibleButton>
      )}

      {isOpen && (
        <div className="bg-white border border-gray-300 rounded-lg shadow-xl max-w-lg w-96 max-h-[500px] overflow-hidden">
          {/* Header */}
          <div className="bg-purple-600 text-white p-3 flex justify-between items-center">
            <h3 className="font-semibold text-sm">Performance Monitor</h3>
            <div className="flex gap-2">
              <AccessibleButton
                onClick={refreshMetrics}
                disabled={isLoading}
                variant="ghost"
                size="sm"
                className="text-white hover:bg-purple-700 px-2 py-1"
              >
                {isLoading ? '...' : '🔄'}
              </AccessibleButton>
              <AccessibleButton
                onClick={() => setIsOpen(false)}
                variant="ghost"
                size="sm"
                className="text-white hover:bg-purple-700 px-2 py-1"
              >
                ✕
              </AccessibleButton>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b bg-gray-50">
            {[
              { key: 'performance', label: 'Performance' },
              { key: 'cache', label: 'Cache' },
              { key: 'assets', label: 'Assets' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSelectedTab(tab.key as any)}
                className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                  selectedTab === tab.key
                    ? 'bg-white border-b-2 border-purple-500 text-purple-600'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="p-3 overflow-y-auto max-h-80">
            {isLoading && (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600 mx-auto mb-2"></div>
                <div className="text-xs text-gray-600">Loading metrics...</div>
              </div>
            )}

            {!isLoading && selectedTab === 'performance' && report && (
              <div className="space-y-4">
                {/* Score */}
                <div className="text-center">
                  <div className={`inline-block px-3 py-1 rounded-full text-lg font-bold ${getScoreColor(report.score)}`}>
                    {report.score}/100
                  </div>
                  <div className="text-xs text-gray-600 mt-1">Performance Score</div>
                </div>

                {/* Core Web Vitals */}
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">Core Web Vitals</h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {report.metrics.lcp && (
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="font-medium">LCP</div>
                        <div className={report.status.lcp === 'good' ? 'text-green-600' : 'text-red-600'}>
                          {formatTime(report.metrics.lcp)}
                        </div>
                      </div>
                    )}
                    {report.metrics.fid && (
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="font-medium">FID</div>
                        <div className={report.status.fid === 'good' ? 'text-green-600' : 'text-red-600'}>
                          {formatTime(report.metrics.fid)}
                        </div>
                      </div>
                    )}
                    {report.metrics.cls && (
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="font-medium">CLS</div>
                        <div className={report.status.cls === 'good' ? 'text-green-600' : 'text-red-600'}>
                          {report.metrics.cls.toFixed(3)}
                        </div>
                      </div>
                    )}
                    {report.metrics.fcp && (
                      <div className="bg-gray-50 p-2 rounded">
                        <div className="font-medium">FCP</div>
                        <div className="text-gray-700">
                          {formatTime(report.metrics.fcp)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Recommendations */}
                {report.recommendations.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">Recommendations</h4>
                    <div className="space-y-1 max-h-24 overflow-y-auto">
                      {report.recommendations.map((rec, index) => (
                        <div key={index} className="text-xs text-gray-600 bg-yellow-50 p-2 rounded">
                          {rec}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {!isLoading && selectedTab === 'cache' && cacheStats && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {(cacheStats.hitRate * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-600">Cache Hit Rate</div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-green-50 p-2 rounded">
                    <div className="font-medium text-green-700">Hits</div>
                    <div className="text-lg font-bold">{cacheStats.hits}</div>
                  </div>
                  <div className="bg-red-50 p-2 rounded">
                    <div className="font-medium text-red-700">Misses</div>
                    <div className="text-lg font-bold">{cacheStats.misses}</div>
                  </div>
                  <div className="bg-blue-50 p-2 rounded">
                    <div className="font-medium text-blue-700">Sets</div>
                    <div className="text-lg font-bold">{cacheStats.sets}</div>
                  </div>
                  <div className="bg-gray-50 p-2 rounded">
                    <div className="font-medium text-gray-700">Memory</div>
                    <div className="text-lg font-bold">{cacheStats.memoryUsage}</div>
                  </div>
                </div>
              </div>
            )}

            {!isLoading && selectedTab === 'assets' && assetMetrics && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="text-xl font-bold text-green-600">
                    {formatBytes(assetMetrics.totalAssetSize)}
                  </div>
                  <div className="text-xs text-gray-600">Total Asset Size</div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span>Compression Ratio:</span>
                    <span className="font-mono">
                      {(assetMetrics.imageCompressionRatio * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span>Font Load Time:</span>
                    <span className="font-mono">
                      {formatTime(assetMetrics.fontLoadTime)}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span>Cache Hit Rate:</span>
                    <span className="font-mono">
                      {(assetMetrics.cacheHitRate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span>Loading Time:</span>
                    <span className="font-mono">
                      {formatTime(assetMetrics.loadingTime)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Export Button */}
            <div className="pt-3 border-t mt-4">
              <AccessibleButton
                onClick={() => {
                  const data = {
                    performance: report,
                    cache: cacheStats,
                    assets: assetMetrics,
                    timestamp: new Date().toISOString(),
                  };
                  
                  console.log('Performance Data Export:', data);
                  
                  if (navigator.clipboard) {
                    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
                      .then(() => console.log('Performance data copied to clipboard'))
                      .catch(console.error);
                  }
                }}
                variant="secondary"
                size="sm"
                className="w-full text-xs"
              >
                Export Data
              </AccessibleButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Hook for programmatic access
export function usePerformanceMonitoring() {
  const [metrics, setMetrics] = useState<PerformanceReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refreshMetrics = useCallback(async () => {
    if (!isDev) return null;
    
    setIsLoading(true);
    try {
      const monitor = getPerformanceMonitor();
      const report = monitor.generateReport();
      setMetrics(report);
      return report;
    } catch (error) {
      console.error('Failed to get performance metrics:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const measureFunction = useCallback(<T,>(
    name: string,
    fn: () => T | Promise<T>
  ): T | Promise<T> => {
    if (!isDev) return fn();
    return measurePerformance(name, fn);
  }, []);

  const markPoint = useCallback((name: string) => {
    if (isDev) {
      markPerformance(name);
    }
  }, []);

  const measureDuration = useCallback((
    startMark: string,
    endMark: string,
    measureName: string
  ): number => {
    if (!isDev) return 0;
    return measureBetween(startMark, endMark, measureName);
  }, []);

  return {
    metrics,
    isLoading,
    refreshMetrics,
    measureFunction,
    markPoint,
    measureDuration,
    isDevMode: isDev,
  };
}