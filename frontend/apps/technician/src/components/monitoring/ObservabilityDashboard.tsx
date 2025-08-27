/**
 * Observability Dashboard Component
 * Real-time monitoring and analytics dashboard for development and debugging
 */

import React, { useState, useEffect, useMemo } from 'react';
import { observabilitySystem } from '../../lib/monitoring/observability-system';
import { performanceMonitor } from '../../lib/performance/performance-monitor';

interface DashboardProps {
  isVisible: boolean;
  onClose: () => void;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: 'green' | 'yellow' | 'red' | 'blue';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, unit, trend, color = 'blue' }) => {
  const colorClasses = {
    green: 'border-green-500 bg-green-50 text-green-700',
    yellow: 'border-yellow-500 bg-yellow-50 text-yellow-700',
    red: 'border-red-500 bg-red-50 text-red-700',
    blue: 'border-blue-500 bg-blue-50 text-blue-700',
  };

  const trendIcons = {
    up: '↗️',
    down: '↘️',
    stable: '→',
  };

  return (
    <div className={`p-4 border-2 rounded-lg ${colorClasses[color]}`}>
      <div className="flex justify-between items-start">
        <h3 className="font-semibold text-sm">{title}</h3>
        {trend && <span className="text-lg">{trendIcons[trend]}</span>}
      </div>
      <div className="mt-2">
        <span className="text-2xl font-bold">{value}</span>
        {unit && <span className="text-sm ml-1">{unit}</span>}
      </div>
    </div>
  );
};

interface LogEntryProps {
  level: string;
  message: string;
  timestamp: number;
  context?: any;
}

const LogEntry: React.FC<LogEntryProps> = ({ level, message, timestamp, context }) => {
  const levelColors = {
    debug: 'text-gray-600 bg-gray-100',
    info: 'text-blue-600 bg-blue-100',
    warn: 'text-yellow-600 bg-yellow-100',
    error: 'text-red-600 bg-red-100',
  };

  return (
    <div className="py-2 px-3 border-b border-gray-200 text-sm">
      <div className="flex items-center gap-2">
        <span className={`px-2 py-1 rounded text-xs font-medium ${levelColors[level as keyof typeof levelColors] || levelColors.info}`}>
          {level.toUpperCase()}
        </span>
        <span className="text-gray-500 text-xs">
          {new Date(timestamp).toLocaleTimeString()}
        </span>
        <span className="flex-1">{message}</span>
      </div>
      {context && (
        <div className="mt-1 pl-16 text-xs text-gray-600">
          <pre className="overflow-hidden">{JSON.stringify(context, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export const ObservabilityDashboard: React.FC<DashboardProps> = ({ isVisible, onClose }) => {
  const [summary, setSummary] = useState<any>(null);
  const [performanceStats, setPerformanceStats] = useState<any>(null);
  const [recentLogs, setRecentLogs] = useState<any[]>([]);
  const [recentEvents, setRecentEvents] = useState<any[]>([]);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'performance' | 'logs' | 'events' | 'errors'>('overview');

  useEffect(() => {
    if (!isVisible) return;

    const updateData = () => {
      try {
        // Get observability summary
        const currentSummary = observabilitySystem.getMetricsSummary();
        setSummary(currentSummary);

        // Get performance stats
        const perfStats = performanceMonitor.getPerformanceStats();
        setPerformanceStats(perfStats);

        // Get exported data for logs and events
        const exportedData = observabilitySystem.exportData();
        setRecentLogs(exportedData.logs.slice(-50)); // Last 50 logs
        setRecentEvents(exportedData.userEvents.slice(-30)); // Last 30 events

      } catch (error) {
        console.error('Failed to update observability dashboard:', error);
      }
    };

    updateData();
    const interval = setInterval(updateData, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, [isVisible]);

  const overviewMetrics = useMemo(() => {
    if (!summary || !performanceStats) return [];

    return [
      {
        title: 'Total Metrics',
        value: summary.totalMetrics || 0,
        color: 'blue' as const,
      },
      {
        title: 'Error Count',
        value: summary.totalErrors || 0,
        color: summary.totalErrors > 0 ? 'red' as const : 'green' as const,
      },
      {
        title: 'Avg Load Time',
        value: performanceStats.averageLoadTime ? Math.round(performanceStats.averageLoadTime) : 0,
        unit: 'ms',
        color: performanceStats.averageLoadTime > 2000 ? 'red' as const : 
               performanceStats.averageLoadTime > 1000 ? 'yellow' as const : 'green' as const,
      },
      {
        title: 'Memory Usage',
        value: performanceStats.memoryUsage ? Math.round(performanceStats.memoryUsage / 1024 / 1024) : 0,
        unit: 'MB',
        color: 'blue' as const,
      },
      {
        title: 'API Calls',
        value: summary.metricsSummary?.find((m: any) => m.name === 'api_call_count')?.count || 0,
        color: 'green' as const,
      },
      {
        title: 'User Events',
        value: summary.totalUserEvents || 0,
        color: 'blue' as const,
      },
    ];
  }, [summary, performanceStats]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-6xl h-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
          <h1 className="text-xl font-bold">📊 Observability Dashboard</h1>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-300 text-xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-4">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'performance', label: 'Performance' },
              { key: 'logs', label: 'Logs' },
              { key: 'events', label: 'Events' },
              { key: 'errors', label: 'Errors' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSelectedTab(tab.key as any)}
                className={`py-3 px-1 border-b-2 font-medium text-sm ${
                  selectedTab === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="p-4 overflow-auto h-full">
          {selectedTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-4">System Overview</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {overviewMetrics.map((metric, index) => (
                    <MetricCard key={index} {...metric} />
                  ))}
                </div>
              </div>

              {summary?.metricsSummary && (
                <div>
                  <h3 className="text-lg font-semibold mb-4">Top Metrics</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {summary.metricsSummary.slice(0, 6).map((metric: any, index: number) => (
                        <div key={index} className="bg-white p-3 rounded border">
                          <h4 className="font-medium text-sm">{metric.name}</h4>
                          <div className="mt-1 space-y-1 text-xs text-gray-600">
                            <div>Count: {metric.count}</div>
                            <div>Avg: {Math.round(metric.avg * 100) / 100}</div>
                            <div>Min: {metric.min} | Max: {metric.max}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {selectedTab === 'performance' && performanceStats && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold">Performance Metrics</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Load Time"
                  value={Math.round(performanceStats.averageLoadTime || 0)}
                  unit="ms"
                  color={performanceStats.averageLoadTime > 2000 ? 'red' : 'green'}
                />
                <MetricCard
                  title="Render Time"
                  value={Math.round(performanceStats.averageRenderTime || 0)}
                  unit="ms"
                  color={performanceStats.averageRenderTime > 100 ? 'yellow' : 'green'}
                />
                <MetricCard
                  title="API Response"
                  value={Math.round(performanceStats.averageApiTime || 0)}
                  unit="ms"
                  color={performanceStats.averageApiTime > 1000 ? 'red' : 'green'}
                />
                <MetricCard
                  title="Memory"
                  value={Math.round((performanceStats.memoryUsage || 0) / 1024 / 1024)}
                  unit="MB"
                />
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold mb-3">Performance Details</h3>
                <pre className="text-xs bg-white p-3 rounded border overflow-auto">
                  {JSON.stringify(performanceStats, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {selectedTab === 'logs' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">Recent Logs</h2>
                <span className="text-sm text-gray-500">
                  Showing last {recentLogs.length} entries
                </span>
              </div>
              
              <div className="bg-gray-50 rounded-lg border max-h-96 overflow-auto">
                {recentLogs.length > 0 ? (
                  recentLogs.map((log, index) => (
                    <LogEntry key={index} {...log} />
                  ))
                ) : (
                  <div className="p-4 text-gray-500 text-center">No logs available</div>
                )}
              </div>
            </div>
          )}

          {selectedTab === 'events' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold">User Events</h2>
                <span className="text-sm text-gray-500">
                  Showing last {recentEvents.length} events
                </span>
              </div>
              
              <div className="bg-gray-50 rounded-lg border max-h-96 overflow-auto">
                {recentEvents.length > 0 ? (
                  recentEvents.map((event, index) => (
                    <div key={index} className="py-2 px-3 border-b border-gray-200 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 bg-blue-100 text-blue-600 rounded text-xs font-medium">
                          {event.type}
                        </span>
                        <span className="text-gray-500 text-xs">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="flex-1">{event.action}</span>
                        {event.target && (
                          <span className="text-xs text-gray-600">→ {event.target}</span>
                        )}
                      </div>
                      {event.data && (
                        <div className="mt-1 pl-16 text-xs text-gray-600">
                          {JSON.stringify(event.data)}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-gray-500 text-center">No events recorded</div>
                )}
              </div>
            </div>
          )}

          {selectedTab === 'errors' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Error Events</h2>
              <div className="bg-red-50 rounded-lg border border-red-200 p-4">
                <p className="text-red-700 text-sm">
                  Error tracking is enabled. Errors will appear here as they occur.
                </p>
                {summary?.totalErrors > 0 && (
                  <div className="mt-2 text-red-600 font-medium">
                    Total Errors: {summary.totalErrors}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-100 p-3 border-t">
          <div className="flex justify-between items-center text-xs text-gray-600">
            <span>
              Session: {summary?.sessionId?.slice(-8) || 'Unknown'}
            </span>
            <span>
              Last Updated: {new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ObservabilityDashboard;