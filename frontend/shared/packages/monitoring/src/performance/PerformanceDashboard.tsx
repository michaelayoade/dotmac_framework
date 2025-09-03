import React, { useState, useEffect } from 'react';
import {
  usePerformanceMonitor,
  useMemoryMonitor,
  useFPSMonitor,
  useBundleMonitor,
  useCoreWebVitals,
  usePerformanceAlerts,
  getPerformanceMonitor,
} from './PerformanceHooks';

interface PerformanceCardProps {
  title: string;
  value: string | number;
  unit?: string;
  status: 'good' | 'warning' | 'critical';
  description?: string;
}

const PerformanceCard: React.FC<PerformanceCardProps> = ({
  title,
  value,
  unit = '',
  status,
  description,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'good':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className={`p-4 rounded-lg border ${getStatusColor()}`}>
      <div className='flex items-center justify-between'>
        <h3 className='text-sm font-medium'>{title}</h3>
        <div
          className={`w-3 h-3 rounded-full ${
            status === 'good'
              ? 'bg-green-500'
              : status === 'warning'
                ? 'bg-yellow-500'
                : 'bg-red-500'
          }`}
        />
      </div>
      <div className='mt-2'>
        <span className='text-2xl font-bold'>{value}</span>
        {unit && <span className='text-sm ml-1'>{unit}</span>}
      </div>
      {description && <p className='text-xs mt-1 opacity-75'>{description}</p>}
    </div>
  );
};

const MetricsChart: React.FC<{
  data: Array<{ timestamp: number; value: number }>;
  title: string;
  color: string;
}> = ({ data, title, color }) => {
  const maxValue = Math.max(...data.map((d) => d.value));
  const minValue = Math.min(...data.map((d) => d.value));
  const range = maxValue - minValue || 1;

  return (
    <div className='p-4 bg-white rounded-lg border'>
      <h3 className='text-sm font-medium mb-3'>{title}</h3>
      <div className='h-32 flex items-end space-x-1'>
        {data.map((point, index) => {
          const height = ((point.value - minValue) / range) * 100;
          return (
            <div key={index} className='flex-1 relative group'>
              <div
                className={`${color} rounded-t transition-all duration-300 hover:opacity-80`}
                style={{ height: `${Math.max(height, 2)}%` }}
              />
              <div className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity'>
                {point.value.toFixed(1)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const AlertsPanel: React.FC = () => {
  const { alerts, clearAlerts } = usePerformanceAlerts();

  if (alerts.length === 0) {
    return (
      <div className='p-4 bg-green-50 border border-green-200 rounded-lg'>
        <p className='text-green-800 text-sm'>✅ No performance issues detected</p>
      </div>
    );
  }

  return (
    <div className='space-y-2'>
      <div className='flex items-center justify-between'>
        <h3 className='font-medium'>Performance Alerts</h3>
        <button onClick={clearAlerts} className='text-sm text-gray-500 hover:text-gray-700'>
          Clear All
        </button>
      </div>
      {alerts.slice(-5).map((alert, index) => (
        <div
          key={index}
          className={`p-3 rounded border-l-4 ${
            alert.severity === 'error'
              ? 'bg-red-50 border-red-500 text-red-700'
              : alert.severity === 'warning'
                ? 'bg-yellow-50 border-yellow-500 text-yellow-700'
                : 'bg-blue-50 border-blue-500 text-blue-700'
          }`}
        >
          <div className='flex items-center justify-between'>
            <span className='text-sm font-medium'>{alert.type.toUpperCase()}</span>
            <span className='text-xs opacity-75'>{alert.timestamp.toLocaleTimeString()}</span>
          </div>
          <p className='text-sm mt-1'>{alert.message}</p>
        </div>
      ))}
    </div>
  );
};

const BundleAnalyzer: React.FC = () => {
  const bundleData = useBundleMonitor();

  if (!bundleData) {
    return (
      <div className='p-4 bg-gray-50 rounded-lg'>
        <p className='text-gray-600'>Loading bundle analysis...</p>
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const sortedAssets = bundleData.assets.sort((a, b) => b.size - a.size);

  return (
    <div className='p-4 bg-white rounded-lg border'>
      <h3 className='font-medium mb-3'>Bundle Analysis</h3>
      <div className='grid grid-cols-2 gap-4 mb-4'>
        <div className='text-center p-3 bg-blue-50 rounded'>
          <div className='text-lg font-bold text-blue-600'>{formatBytes(bundleData.totalSize)}</div>
          <div className='text-sm text-blue-500'>Total Size</div>
        </div>
        <div className='text-center p-3 bg-green-50 rounded'>
          <div className='text-lg font-bold text-green-600'>
            {formatBytes(bundleData.compressedSize)}
          </div>
          <div className='text-sm text-green-500'>Compressed</div>
        </div>
      </div>
      <div className='space-y-2'>
        <h4 className='text-sm font-medium'>Largest Assets</h4>
        {sortedAssets.slice(0, 5).map((asset, index) => (
          <div
            key={index}
            className='flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0'
          >
            <div className='flex items-center'>
              <div
                className={`w-3 h-3 rounded-full mr-2 ${
                  asset.type === 'javascript'
                    ? 'bg-yellow-500'
                    : asset.type === 'stylesheet'
                      ? 'bg-blue-500'
                      : asset.type === 'font'
                        ? 'bg-purple-500'
                        : 'bg-gray-500'
                }`}
              />
              <span className='text-sm truncate max-w-48'>{asset.name}</span>
            </div>
            <span className='text-sm text-gray-600'>{formatBytes(asset.size)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const PerformanceDashboard: React.FC = () => {
  const memoryUsage = useMemoryMonitor();
  const fps = useFPSMonitor();
  const vitals = useCoreWebVitals();
  const [historicalData, setHistoricalData] = useState<{
    fps: Array<{ timestamp: number; value: number }>;
    memory: Array<{ timestamp: number; value: number }>;
  }>({
    fps: [],
    memory: [],
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const timestamp = Date.now();

      setHistoricalData((prev) => ({
        fps: [...prev.fps.slice(-29), { timestamp, value: fps }],
        memory: [
          ...prev.memory.slice(-29),
          {
            timestamp,
            value: memoryUsage?.percentage || 0,
          },
        ],
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, [fps, memoryUsage]);

  const getVitalStatus = (
    vital: number | null,
    thresholds: { good: number; poor: number }
  ): 'good' | 'warning' | 'critical' => {
    if (vital === null) return 'warning';
    if (vital <= thresholds.good) return 'good';
    if (vital <= thresholds.poor) return 'warning';
    return 'critical';
  };

  return (
    <div className='p-6 bg-gray-50 min-h-screen'>
      <div className='max-w-7xl mx-auto'>
        <div className='mb-6'>
          <h1 className='text-2xl font-bold text-gray-900'>Performance Dashboard</h1>
          <p className='text-gray-600'>Real-time application performance metrics</p>
        </div>

        {/* Core Web Vitals */}
        <div className='grid grid-cols-1 md:grid-cols-5 gap-4 mb-6'>
          <PerformanceCard
            title='First Contentful Paint'
            value={vitals.fcp?.toFixed(0) || 'N/A'}
            unit='ms'
            status={getVitalStatus(vitals.fcp, { good: 1800, poor: 3000 })}
            description='Time to first content render'
          />
          <PerformanceCard
            title='Largest Contentful Paint'
            value={vitals.lcp?.toFixed(0) || 'N/A'}
            unit='ms'
            status={getVitalStatus(vitals.lcp, { good: 2500, poor: 4000 })}
            description='Time to largest content render'
          />
          <PerformanceCard
            title='First Input Delay'
            value={vitals.fid?.toFixed(0) || 'N/A'}
            unit='ms'
            status={getVitalStatus(vitals.fid, { good: 100, poor: 300 })}
            description='Time to first interaction'
          />
          <PerformanceCard
            title='Cumulative Layout Shift'
            value={vitals.cls?.toFixed(3) || 'N/A'}
            unit=''
            status={getVitalStatus(vitals.cls, { good: 0.1, poor: 0.25 })}
            description='Visual stability score'
          />
          <PerformanceCard
            title='Time to First Byte'
            value={vitals.ttfb?.toFixed(0) || 'N/A'}
            unit='ms'
            status={getVitalStatus(vitals.ttfb, { good: 800, poor: 1800 })}
            description='Server response time'
          />
        </div>

        {/* Real-time Metrics */}
        <div className='grid grid-cols-1 md:grid-cols-3 gap-4 mb-6'>
          <PerformanceCard
            title='Frames Per Second'
            value={fps}
            unit='fps'
            status={fps >= 50 ? 'good' : fps >= 30 ? 'warning' : 'critical'}
            description='Animation smoothness'
          />
          <PerformanceCard
            title='Memory Usage'
            value={memoryUsage?.percentage.toFixed(1) || 'N/A'}
            unit='%'
            status={
              !memoryUsage
                ? 'warning'
                : memoryUsage.percentage < 60
                  ? 'good'
                  : memoryUsage.percentage < 80
                    ? 'warning'
                    : 'critical'
            }
            description={`${memoryUsage ? Math.round(memoryUsage.used / 1024 / 1024) : 0}MB used`}
          />
          <PerformanceCard
            title='JavaScript Heap'
            value={memoryUsage ? Math.round(memoryUsage.used / 1024 / 1024) : 'N/A'}
            unit='MB'
            status={
              !memoryUsage
                ? 'warning'
                : memoryUsage.used / 1024 / 1024 < 50
                  ? 'good'
                  : memoryUsage.used / 1024 / 1024 < 100
                    ? 'warning'
                    : 'critical'
            }
            description='JavaScript memory consumption'
          />
        </div>

        {/* Charts */}
        <div className='grid grid-cols-1 md:grid-cols-2 gap-4 mb-6'>
          <MetricsChart data={historicalData.fps} title='FPS Over Time' color='bg-blue-500' />
          <MetricsChart
            data={historicalData.memory}
            title='Memory Usage Over Time'
            color='bg-purple-500'
          />
        </div>

        {/* Bundle Analysis and Alerts */}
        <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
          <BundleAnalyzer />
          <AlertsPanel />
        </div>
      </div>
    </div>
  );
};

export default PerformanceDashboard;
