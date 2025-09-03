/**
 * Network Monitoring Dashboard
 * Real-time network performance monitoring and alerting interface
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card, Button, Badge } from '@dotmac/primitives';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Wifi,
  Server,
  Gauge,
  Zap,
} from 'lucide-react';

export interface NetworkMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  threshold: number;
  status: 'healthy' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
  timestamp: number;
}

export interface NetworkDevice {
  id: string;
  name: string;
  type: 'router' | 'switch' | 'access_point' | 'server';
  status: 'online' | 'offline' | 'degraded';
  uptime: number;
  location?: string;
  metrics: NetworkMetric[];
}

export interface NetworkMonitoringProps {
  devices: NetworkDevice[];
  onDeviceSelect?: (device: NetworkDevice) => void;
  onMetricClick?: (metric: NetworkMetric) => void;
  refreshInterval?: number;
  showAlerts?: boolean;
  className?: string;
}

export const NetworkMonitoringDashboard: React.FC<NetworkMonitoringProps> = ({
  devices = [],
  onDeviceSelect,
  onMetricClick,
  refreshInterval = 30000,
  showAlerts = true,
  className,
}) => {
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);

  // Auto-refresh functionality
  useEffect(() => {
    if (!isAutoRefresh) return;

    const interval = setInterval(() => {
      setLastRefresh(new Date());
      // Trigger refresh logic here
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [isAutoRefresh, refreshInterval]);

  // Calculate aggregate metrics
  const aggregateMetrics = useMemo(() => {
    const onlineDevices = devices.filter((d) => d.status === 'online').length;
    const totalDevices = devices.length;
    const criticalAlerts = devices.flatMap((d) =>
      d.metrics.filter((m) => m.status === 'critical')
    ).length;
    const warningAlerts = devices.flatMap((d) =>
      d.metrics.filter((m) => m.status === 'warning')
    ).length;

    return {
      availability: totalDevices > 0 ? (onlineDevices / totalDevices) * 100 : 0,
      criticalAlerts,
      warningAlerts,
      totalDevices,
      onlineDevices,
    };
  }, [devices]);

  const handleDeviceClick = (device: NetworkDevice) => {
    setSelectedDevice(device);
    onDeviceSelect?.(device);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'healthy':
        return 'text-green-500';
      case 'warning':
      case 'degraded':
        return 'text-yellow-500';
      case 'critical':
      case 'offline':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
      case 'healthy':
        return <CheckCircle className='w-4 h-4' />;
      case 'warning':
      case 'degraded':
        return <AlertTriangle className='w-4 h-4' />;
      case 'critical':
      case 'offline':
        return <AlertTriangle className='w-4 h-4' />;
      default:
        return <Clock className='w-4 h-4' />;
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className='w-3 h-3 text-green-500' />;
      case 'down':
        return <TrendingDown className='w-3 h-3 text-red-500' />;
      default:
        return <Activity className='w-3 h-3 text-gray-400' />;
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'router':
        return <Wifi className='w-5 h-5' />;
      case 'server':
        return <Server className='w-5 h-5' />;
      case 'access_point':
        return <Zap className='w-5 h-5' />;
      default:
        return <Activity className='w-5 h-5' />;
    }
  };

  return (
    <div className={`space-y-6 ${className || ''}`}>
      {/* Header and Controls */}
      <div className='flex justify-between items-center'>
        <div>
          <h2 className='text-2xl font-bold text-gray-900'>Network Monitoring</h2>
          <p className='text-sm text-gray-500'>Last updated: {lastRefresh.toLocaleTimeString()}</p>
        </div>

        <div className='flex items-center space-x-2'>
          <Button
            variant={isAutoRefresh ? 'default' : 'outline'}
            size='sm'
            onClick={() => setIsAutoRefresh(!isAutoRefresh)}
          >
            <Activity className='w-4 h-4 mr-2' />
            Auto Refresh
          </Button>

          <Button variant='outline' size='sm' onClick={() => setLastRefresh(new Date())}>
            Refresh Now
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <Card className='p-4'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-500'>Network Availability</p>
              <p className='text-2xl font-bold text-gray-900'>
                {aggregateMetrics.availability.toFixed(1)}%
              </p>
            </div>
            <Gauge className='w-8 h-8 text-blue-500' />
          </div>
        </Card>

        <Card className='p-4'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-500'>Online Devices</p>
              <p className='text-2xl font-bold text-gray-900'>
                {aggregateMetrics.onlineDevices}/{aggregateMetrics.totalDevices}
              </p>
            </div>
            <CheckCircle className='w-8 h-8 text-green-500' />
          </div>
        </Card>

        <Card className='p-4'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-500'>Critical Alerts</p>
              <p className='text-2xl font-bold text-red-600'>{aggregateMetrics.criticalAlerts}</p>
            </div>
            <AlertTriangle className='w-8 h-8 text-red-500' />
          </div>
        </Card>

        <Card className='p-4'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-500'>Warnings</p>
              <p className='text-2xl font-bold text-yellow-600'>{aggregateMetrics.warningAlerts}</p>
            </div>
            <AlertTriangle className='w-8 h-8 text-yellow-500' />
          </div>
        </Card>
      </div>

      {/* Device Grid */}
      <div className='grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6'>
        {devices.map((device) => (
          <Card
            key={device.id}
            className={`p-4 cursor-pointer hover:shadow-lg transition-shadow ${
              selectedDevice?.id === device.id ? 'ring-2 ring-blue-500' : ''
            }`}
            onClick={() => handleDeviceClick(device)}
          >
            <div className='flex items-center justify-between mb-3'>
              <div className='flex items-center space-x-2'>
                {getDeviceIcon(device.type)}
                <h3 className='font-medium text-gray-900'>{device.name}</h3>
              </div>

              <Badge
                variant={device.status === 'online' ? 'default' : 'destructive'}
                className='flex items-center space-x-1'
              >
                {getStatusIcon(device.status)}
                <span className='capitalize'>{device.status}</span>
              </Badge>
            </div>

            {device.location && <p className='text-sm text-gray-500 mb-2'>{device.location}</p>}

            <div className='space-y-2'>
              <div className='text-xs text-gray-500'>
                Uptime: {Math.floor(device.uptime / 3600)}h{' '}
                {Math.floor((device.uptime % 3600) / 60)}m
              </div>

              {/* Key Metrics */}
              <div className='space-y-1'>
                {device.metrics.slice(0, 3).map((metric) => (
                  <div
                    key={metric.id}
                    className='flex items-center justify-between text-sm cursor-pointer hover:bg-gray-50 p-1 rounded'
                    onClick={(e) => {
                      e.stopPropagation();
                      onMetricClick?.(metric);
                    }}
                  >
                    <span className='flex items-center space-x-1'>
                      <span className={getStatusColor(metric.status)}>
                        {getStatusIcon(metric.status)}
                      </span>
                      <span>{metric.name}</span>
                    </span>
                    <span className='flex items-center space-x-1'>
                      <span className='font-medium'>
                        {metric.value.toFixed(1)} {metric.unit}
                      </span>
                      {getTrendIcon(metric.trend)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Selected Device Detail */}
      {selectedDevice && (
        <Card className='p-6'>
          <div className='flex items-center justify-between mb-4'>
            <h3 className='text-lg font-medium text-gray-900'>
              {selectedDevice.name} - Detailed Metrics
            </h3>
            <Button variant='outline' size='sm' onClick={() => setSelectedDevice(null)}>
              Close
            </Button>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
            {selectedDevice.metrics.map((metric) => (
              <div
                key={metric.id}
                className='p-3 border rounded-lg hover:bg-gray-50 cursor-pointer'
                onClick={() => onMetricClick?.(metric)}
              >
                <div className='flex items-center justify-between mb-2'>
                  <span className='text-sm font-medium text-gray-900'>{metric.name}</span>
                  <span className={`flex items-center space-x-1 ${getStatusColor(metric.status)}`}>
                    {getStatusIcon(metric.status)}
                    {getTrendIcon(metric.trend)}
                  </span>
                </div>

                <div className='flex items-baseline space-x-2'>
                  <span className='text-xl font-bold text-gray-900'>{metric.value.toFixed(1)}</span>
                  <span className='text-sm text-gray-500'>{metric.unit}</span>
                </div>

                <div className='text-xs text-gray-500 mt-1'>
                  Threshold: {metric.threshold} {metric.unit}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
