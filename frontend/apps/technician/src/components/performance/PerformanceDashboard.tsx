'use client';

import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Database, 
  Wifi, 
  Battery, 
  Clock, 
  Zap, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  Info,
  Trash2,
  Settings
} from 'lucide-react';
import { motion } from 'framer-motion';
import { performanceMonitor } from '../../lib/performance/performance-monitor';
import { databaseOptimizer } from '../../lib/performance/database-optimization';
import { syncOptimizer } from '../../lib/performance/sync-optimization';
import { advancedSyncManager } from '../../lib/sync/advanced-sync-manager';
import { featureFlags } from '../../lib/config/environment';

interface PerformanceDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PerformanceDashboard({ isOpen, onClose }: PerformanceDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'vitals' | 'database' | 'sync' | 'network'>('overview');
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isOpen) {
      // Initial load
      loadPerformanceData();
      
      // Set up refresh interval
      const interval = setInterval(loadPerformanceData, 5000); // Every 5 seconds
      setRefreshInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [isOpen]);

  const loadPerformanceData = async () => {
    try {
      const [
        webVitals,
        dbStats,
        syncStats,
        syncMetrics
      ] = await Promise.all([
        performanceMonitor.getPerformanceSummary(),
        databaseOptimizer.getDatabaseStats(),
        syncOptimizer.getPerformanceStats(),
        advancedSyncManager.getSyncMetrics()
      ]);

      setPerformanceData({
        webVitals,
        database: dbStats,
        sync: syncStats,
        syncManager: syncMetrics,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Failed to load performance data:', error);
    }
  };

  const clearCaches = () => {
    databaseOptimizer.clearCache();
    advancedSyncManager.clearSyncQueue();
    loadPerformanceData();
  };

  const exportPerformanceReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      webVitals: performanceData?.webVitals,
      database: performanceData?.database,
      sync: performanceData?.sync,
      syncManager: performanceData?.syncManager,
      userAgent: navigator.userAgent,
      connection: (navigator as any).connection?.effectiveType || 'unknown',
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-report-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isOpen || !featureFlags.isDebugLoggingEnabled()) {
    return null;
  }

  const getScoreColor = (score: number, reverse = false) => {
    if (reverse) score = 100 - score;
    if (score >= 80) return 'text-green-600 bg-green-50';
    if (score >= 60) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatMs = (ms: number) => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-5/6 flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <Activity className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">Performance Dashboard</h2>
            {performanceData?.timestamp && (
              <span className="text-sm text-gray-500">
                Last updated: {new Date(performanceData.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={exportPerformanceReport}
              className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 border border-blue-300 rounded"
            >
              Export Report
            </button>
            <button
              onClick={clearCaches}
              className="px-3 py-1 text-sm text-orange-600 hover:text-orange-700 border border-orange-300 rounded"
            >
              Clear Caches
            </button>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          {[
            { id: 'overview', label: 'Overview', icon: TrendingUp },
            { id: 'vitals', label: 'Web Vitals', icon: Zap },
            { id: 'database', label: 'Database', icon: Database },
            { id: 'sync', label: 'Sync', icon: Wifi },
            { id: 'network', label: 'Network', icon: Activity },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium ${
                activeTab === tab.id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-blue-600">Page Load</p>
                      <p className="text-2xl font-bold text-blue-900">
                        {performanceData?.webVitals?.webVitals?.find((v: any) => v.name === 'LCP')?.value 
                          ? formatMs(performanceData.webVitals.webVitals.find((v: any) => v.name === 'LCP').value)
                          : 'N/A'}
                      </p>
                    </div>
                    <Clock className="w-8 h-8 text-blue-600" />
                  </div>
                </div>

                <div className="bg-green-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-green-600">DB Cache Hit Rate</p>
                      <p className="text-2xl font-bold text-green-900">
                        {performanceData?.database?.cacheHitRate 
                          ? `${Math.round(performanceData.database.cacheHitRate * 100)}%`
                          : 'N/A'}
                      </p>
                    </div>
                    <Database className="w-8 h-8 text-green-600" />
                  </div>
                </div>

                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-purple-600">Sync Success Rate</p>
                      <p className="text-2xl font-bold text-purple-900">
                        {performanceData?.sync?.successRate 
                          ? `${Math.round(performanceData.sync.successRate * 100)}%`
                          : 'N/A'}
                      </p>
                    </div>
                    <Wifi className="w-8 h-8 text-purple-600" />
                  </div>
                </div>

                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-orange-600">Memory Usage</p>
                      <p className="text-2xl font-bold text-orange-900">
                        {performanceData?.webVitals?.memoryUsage?.used 
                          ? formatBytes(performanceData.webVitals.memoryUsage.used)
                          : 'N/A'}
                      </p>
                    </div>
                    <Battery className="w-8 h-8 text-orange-600" />
                  </div>
                </div>
              </div>

              {/* System Status */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Connection</span>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        navigator.onLine ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {navigator.onLine ? 'Online' : 'Offline'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Sync Status</span>
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        performanceData?.syncManager?.pending === 0 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {performanceData?.syncManager?.pending === 0 ? 'Synced' : `${performanceData?.syncManager?.pending || 0} pending`}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Database Entries</span>
                      <span className="text-sm text-gray-900">
                        {performanceData?.database?.cacheEntries || 0} cached
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Cache Size</span>
                      <span className="text-sm text-gray-900">
                        {performanceData?.database?.cacheSize ? formatBytes(performanceData.database.cacheSize) : '0 B'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'vitals' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Core Web Vitals</h3>
              {performanceData?.webVitals?.webVitals?.map((vital: any) => (
                <div key={vital.name} className="bg-white border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-gray-900">{vital.name}</h4>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      vital.rating === 'good' ? 'bg-green-100 text-green-800' :
                      vital.rating === 'needs-improvement' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {vital.rating}
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-gray-900 mb-1">
                    {formatMs(vital.value)}
                  </div>
                  <div className="text-sm text-gray-500">
                    Connection: {vital.connection || 'unknown'}
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'database' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Database Performance</h3>
                <button
                  onClick={() => databaseOptimizer.clearCache()}
                  className="flex items-center space-x-1 px-3 py-1 text-sm text-red-600 hover:text-red-700 border border-red-300 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Clear Cache</span>
                </button>
              </div>

              {/* Query Performance */}
              <div className="bg-white border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-4">Query Performance</h4>
                <div className="space-y-2">
                  {Object.entries(performanceData?.database?.queryStats || {}).map(([query, stats]: [string, any]) => (
                    <div key={query} className="flex items-center justify-between py-2 border-b last:border-b-0">
                      <span className="text-sm text-gray-600">{query}</span>
                      <div className="text-right">
                        <div className="text-sm font-medium text-gray-900">{formatMs(stats.avgTime)}</div>
                        <div className="text-xs text-gray-500">{stats.count} queries</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Index Suggestions */}
              {Object.keys(performanceData?.database?.indexSuggestions || {}).length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <Info className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-900 mb-2">Index Suggestions</h4>
                      {Object.entries(performanceData.database.indexSuggestions).map(([table, indexes]: [string, any]) => (
                        <div key={table} className="mb-2">
                          <span className="text-sm font-medium text-blue-800">{table}:</span>
                          <span className="text-sm text-blue-700 ml-2">{indexes.join(', ')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'sync' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Synchronization Performance</h3>

              {/* Sync Strategy */}
              <div className="bg-white border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-4">Current Strategy</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Strategy:</span>
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      {performanceData?.sync?.currentStrategy || 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Connection:</span>
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      {performanceData?.sync?.connectionSpeed || 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Battery:</span>
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      {Math.round(performanceData?.sync?.batteryLevel * 100) || 0}%
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Total Syncs:</span>
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      {performanceData?.sync?.totalSyncs || 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Sync Queue */}
              <div className="bg-white border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-4">Sync Queue Status</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Pending:</span>
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      {performanceData?.syncManager?.pendingItems || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Conflicts:</span>
                    <span className="ml-2 text-sm font-medium text-orange-600">
                      {performanceData?.syncManager?.conflictItems || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Errors:</span>
                    <span className="ml-2 text-sm font-medium text-red-600">
                      {performanceData?.syncManager?.errorItems || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Sync Rate:</span>
                    <span className="ml-2 text-sm font-medium text-gray-900">
                      {Math.round(performanceData?.syncManager?.syncRate || 0)} items/min
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'network' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Network Performance</h3>
              
              <div className="bg-white border rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-4">Connection Information</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Status</span>
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      navigator.onLine ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {navigator.onLine ? 'Online' : 'Offline'}
                    </span>
                  </div>
                  {(navigator as any).connection && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Type</span>
                        <span className="text-sm text-gray-900">
                          {(navigator as any).connection.effectiveType || 'Unknown'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Downlink</span>
                        <span className="text-sm text-gray-900">
                          {(navigator as any).connection.downlink || 'Unknown'} Mbps
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">RTT</span>
                        <span className="text-sm text-gray-900">
                          {(navigator as any).connection.rtt || 'Unknown'} ms
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Resource Counts */}
              {performanceData?.webVitals?.resourceCounts && (
                <div className="bg-white border rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-4">Resource Loading</h4>
                  <div className="space-y-2">
                    {Object.entries(performanceData.webVitals.resourceCounts).map(([type, count]: [string, any]) => (
                      <div key={type} className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 capitalize">{type}</span>
                        <span className="text-sm text-gray-900">{count} resources</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}