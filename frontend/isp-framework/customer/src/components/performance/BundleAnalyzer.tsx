/**
 * Bundle Analyzer Component
 * Runtime bundle analysis and performance monitoring
 */

'use client';

import { useEffect, useState } from 'react';
import { CacheManager, networkMonitor, PerformanceMonitor } from '../../lib/utils/serviceWorker';

interface BundleMetrics {
  totalBundleSize: number;
  cacheSize: number;
  cacheQuota: number;
  networkType: string;
  isOnline: boolean;
  coreWebVitals: any;
  resourceTimings: PerformanceResourceTiming[];
}

interface BundleAnalyzerProps {
  showDetails?: boolean;
  onMetricsUpdate?: (metrics: BundleMetrics) => void;
}

export function BundleAnalyzer({ showDetails = false, onMetricsUpdate }: BundleAnalyzerProps) {
  const [metrics, setMetrics] = useState<BundleMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  useEffect(() => {
    collectMetrics();

    // Set up network status monitoring
    const cleanup = networkMonitor.onStatusChange((online) => {
      setMetrics((prev) => (prev ? { ...prev, isOnline: online } : null));
    });

    return cleanup;
  }, []);

  const collectMetrics = async () => {
    try {
      setIsLoading(true);

      const [cacheSize, cacheQuota, coreWebVitals, resourceTimings] = await Promise.all([
        CacheManager.getCacheSize(),
        CacheManager.getCacheQuota(),
        PerformanceMonitor.getCoreWebVitals(),
        PerformanceMonitor.measureResourceTiming(),
      ]);

      const totalBundleSize = resourceTimings
        .filter((resource) => resource.name.includes('_next/static'))
        .reduce((sum, resource) => sum + (resource.transferSize || 0), 0);

      const newMetrics: BundleMetrics = {
        totalBundleSize,
        cacheSize,
        cacheQuota,
        networkType: networkMonitor.getConnectionType(),
        isOnline: networkMonitor.isOnline(),
        coreWebVitals,
        resourceTimings,
      };

      setMetrics(newMetrics);
      onMetricsUpdate?.(newMetrics);
    } catch (error) {
      console.error('Failed to collect metrics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
  };

  const formatDuration = (duration: number): string => {
    return `${duration.toFixed(2)} ms`;
  };

  const getScoreColor = (score: number, thresholds: [number, number]): string => {
    if (score <= thresholds[0]) return 'text-green-600';
    if (score <= thresholds[1]) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (!showDetails && !onMetricsUpdate) return null;
  if (isLoading) {
    return (
      <div className='bg-white border rounded-lg p-4'>
        <div className='animate-pulse'>
          <div className='h-4 bg-gray-200 rounded mb-4'></div>
          <div className='space-y-2'>
            <div className='h-3 bg-gray-200 rounded'></div>
            <div className='h-3 bg-gray-200 rounded w-4/5'></div>
            <div className='h-3 bg-gray-200 rounded w-3/5'></div>
          </div>
        </div>
      </div>
    );
  }

  if (!showDetails) return null;

  return (
    <div className='bg-white border rounded-lg p-6 space-y-6'>
      <div className='flex items-center justify-between'>
        <h3 className='text-lg font-semibold'>Bundle Analysis</h3>
        <button
          onClick={collectMetrics}
          className='px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600'
        >
          Refresh
        </button>
      </div>

      {metrics && (
        <div className='space-y-4'>
          {/* Bundle Size Overview */}
          <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
            <div className='text-center p-3 bg-gray-50 rounded'>
              <div className='text-2xl font-bold text-blue-600'>
                {formatBytes(metrics.totalBundleSize)}
              </div>
              <div className='text-sm text-gray-600'>Bundle Size</div>
            </div>
            <div className='text-center p-3 bg-gray-50 rounded'>
              <div className='text-2xl font-bold text-green-600'>
                {formatBytes(metrics.cacheSize)}
              </div>
              <div className='text-sm text-gray-600'>Cache Used</div>
            </div>
            <div className='text-center p-3 bg-gray-50 rounded'>
              <div className='text-2xl font-bold text-purple-600'>
                {metrics.networkType.toUpperCase()}
              </div>
              <div className='text-sm text-gray-600'>Connection</div>
            </div>
            <div className='text-center p-3 bg-gray-50 rounded'>
              <div
                className={`text-2xl font-bold ${metrics.isOnline ? 'text-green-600' : 'text-red-600'}`}
              >
                {metrics.isOnline ? 'ONLINE' : 'OFFLINE'}
              </div>
              <div className='text-sm text-gray-600'>Status</div>
            </div>
          </div>

          {/* Core Web Vitals */}
          {metrics.coreWebVitals && Object.keys(metrics.coreWebVitals).length > 0 && (
            <div>
              <button
                onClick={() => setExpandedSection(expandedSection === 'vitals' ? null : 'vitals')}
                className='w-full text-left font-medium py-2 flex items-center justify-between'
              >
                Core Web Vitals
                <svg
                  className={`w-5 h-5 transition-transform ${expandedSection === 'vitals' ? 'rotate-180' : ''}`}
                  fill='currentColor'
                  viewBox='0 0 20 20'
                >
                  <path
                    fillRule='evenodd'
                    d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z'
                    clipRule='evenodd'
                  />
                </svg>
              </button>

              {expandedSection === 'vitals' && (
                <div className='grid grid-cols-1 md:grid-cols-3 gap-4 pt-2'>
                  {metrics.coreWebVitals.lcp && (
                    <div className='p-3 border rounded'>
                      <div className='text-sm text-gray-600'>Largest Contentful Paint</div>
                      <div
                        className={`text-xl font-bold ${getScoreColor(metrics.coreWebVitals.lcp.value, [2500, 4000])}`}
                      >
                        {formatDuration(metrics.coreWebVitals.lcp.value)}
                      </div>
                    </div>
                  )}
                  {metrics.coreWebVitals.fid && (
                    <div className='p-3 border rounded'>
                      <div className='text-sm text-gray-600'>First Input Delay</div>
                      <div
                        className={`text-xl font-bold ${getScoreColor(metrics.coreWebVitals.fid.value, [100, 300])}`}
                      >
                        {formatDuration(metrics.coreWebVitals.fid.value)}
                      </div>
                    </div>
                  )}
                  {metrics.coreWebVitals.cls && (
                    <div className='p-3 border rounded'>
                      <div className='text-sm text-gray-600'>Cumulative Layout Shift</div>
                      <div
                        className={`text-xl font-bold ${getScoreColor(metrics.coreWebVitals.cls.value * 1000, [100, 250])}`}
                      >
                        {metrics.coreWebVitals.cls.value.toFixed(3)}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Resource Breakdown */}
          <div>
            <button
              onClick={() =>
                setExpandedSection(expandedSection === 'resources' ? null : 'resources')
              }
              className='w-full text-left font-medium py-2 flex items-center justify-between'
            >
              Resource Breakdown ({metrics.resourceTimings.length} resources)
              <svg
                className={`w-5 h-5 transition-transform ${expandedSection === 'resources' ? 'rotate-180' : ''}`}
                fill='currentColor'
                viewBox='0 0 20 20'
              >
                <path
                  fillRule='evenodd'
                  d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z'
                  clipRule='evenodd'
                />
              </svg>
            </button>

            {expandedSection === 'resources' && (
              <div className='pt-2 max-h-96 overflow-y-auto'>
                <div className='space-y-1'>
                  {metrics.resourceTimings
                    .sort((a, b) => (b.transferSize || 0) - (a.transferSize || 0))
                    .slice(0, 20)
                    .map((resource, index) => (
                      <div
                        key={index}
                        className='flex items-center justify-between py-1 px-2 hover:bg-gray-50 rounded text-sm'
                      >
                        <div className='flex-1 truncate' title={resource.name}>
                          {resource.name.split('/').pop()}
                        </div>
                        <div className='flex items-center space-x-4 text-xs text-gray-600'>
                          <span>{formatBytes(resource.transferSize || 0)}</span>
                          <span>{formatDuration(resource.duration)}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>

          {/* Cache Management */}
          <div className='flex items-center justify-between pt-4 border-t'>
            <div>
              <div className='text-sm font-medium'>Cache Usage</div>
              <div className='text-xs text-gray-600'>
                {formatBytes(metrics.cacheSize)} / {formatBytes(metrics.cacheQuota)}(
                {Math.round((metrics.cacheSize / metrics.cacheQuota) * 100)}%)
              </div>
            </div>
            <button
              onClick={() => {
                CacheManager.clearAll();
                collectMetrics();
              }}
              className='px-3 py-1 text-sm text-red-600 border border-red-600 rounded hover:bg-red-50'
            >
              Clear Cache
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
