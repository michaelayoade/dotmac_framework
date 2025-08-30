import React, { useEffect, useState } from 'react';
import { Card } from '@dotmac/primitives';
import { Activity, AlertTriangle, CheckCircle, Clock, Plugin } from 'lucide-react';
import { usePlugins, usePluginLifecycle } from '../hooks';
import type { PluginDashboardProps, PluginSystemHealth } from '../types';

export const PluginDashboard: React.FC<PluginDashboardProps> = ({
  showSystemMetrics = true,
  showRecentActivity = true,
  showHealthAlerts = true,
  refreshInterval = 30000 // 30 seconds
}) => {
  const { plugins, loading, error, getSystemHealth } = usePlugins();
  const { healthMonitoringActive, lastHealthCheck } = usePluginLifecycle();
  const [systemHealth, setSystemHealth] = useState<PluginSystemHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const activePlugins = plugins.filter(p => p.is_active);
  const errorPlugins = plugins.filter(p => p.status === 'error');
  const healthyPlugins = plugins.filter(p => p.healthy);

  const fetchSystemHealth = async () => {
    try {
      setHealthLoading(true);
      const health = await getSystemHealth();
      setSystemHealth(health);
    } catch (err) {
      console.error('Failed to fetch system health:', err);
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemHealth();

    const interval = setInterval(fetchSystemHealth, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loading) {
    return (
      <div className="plugin-dashboard loading">
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-gray-200 rounded-lg"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="plugin-dashboard error">
        <Card className="border-red-200 bg-red-50">
          <div className="flex items-center gap-2 p-4">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-800">Dashboard Error</h3>
              <p className="text-red-600">{error}</p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="plugin-dashboard space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Plugin className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Plugin System</h1>
        </div>

        <div className="flex items-center gap-2 text-sm text-gray-600">
          {healthMonitoringActive ? (
            <>
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span>Health monitoring active</span>
            </>
          ) : (
            <>
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <span>Health monitoring inactive</span>
            </>
          )}
        </div>
      </div>

      {/* System Metrics */}
      {showSystemMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Plugin className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Plugins</p>
                <p className="text-2xl font-bold">{plugins.length}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Active</p>
                <p className="text-2xl font-bold text-green-600">{activePlugins.length}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Activity className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Healthy</p>
                <p className="text-2xl font-bold text-yellow-600">{healthyPlugins.length}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Errors</p>
                <p className="text-2xl font-bold text-red-600">{errorPlugins.length}</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Health Alerts */}
      {showHealthAlerts && errorPlugins.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <div className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <h3 className="font-semibold text-red-800">Plugin Errors</h3>
            </div>
            <div className="space-y-2">
              {errorPlugins.slice(0, 5).map((plugin) => (
                <div key={`${plugin.metadata.domain}.${plugin.metadata.name}`}
                     className="text-sm text-red-700">
                  <span className="font-medium">{plugin.metadata.name}</span>
                  <span className="text-red-600 ml-2">in {plugin.metadata.domain}</span>
                </div>
              ))}
              {errorPlugins.length > 5 && (
                <p className="text-sm text-red-600">
                  And {errorPlugins.length - 5} more plugins with errors...
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* System Health */}
      {showSystemMetrics && systemHealth && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-4">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Activity className="h-4 w-4" />
              System Status
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Manager Status</span>
                <span className={`text-sm font-medium ${
                  systemHealth.manager.initialized && !systemHealth.manager.shutdown
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {systemHealth.manager.initialized && !systemHealth.manager.shutdown
                    ? 'Running'
                    : 'Stopped'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Registry Domains</span>
                <span className="text-sm font-medium">{systemHealth.registry.domains.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Last Updated</span>
                <span className="text-sm text-gray-500">
                  {new Date(systemHealth.manager.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Health Monitoring
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Status</span>
                <span className={`text-sm font-medium ${
                  healthMonitoringActive ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  {healthMonitoringActive ? 'Active' : 'Inactive'}
                </span>
              </div>
              {lastHealthCheck && (
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Last Check</span>
                  <span className="text-sm text-gray-500">
                    {new Date(lastHealthCheck).toLocaleTimeString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Health Score</span>
                <span className="text-sm font-medium text-green-600">
                  {Math.round((healthyPlugins.length / plugins.length) * 100)}%
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Recent Activity */}
      {showRecentActivity && (
        <Card className="p-4">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Recently Active Plugins
          </h3>
          <div className="space-y-2">
            {plugins
              .filter(p => p.last_activity)
              .sort((a, b) => new Date(b.last_activity!).getTime() - new Date(a.last_activity!).getTime())
              .slice(0, 8)
              .map((plugin) => (
                <div key={`${plugin.metadata.domain}.${plugin.metadata.name}`}
                     className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${
                      plugin.is_active ? 'bg-green-500' : 'bg-gray-400'
                    }`}></div>
                    <div>
                      <p className="font-medium text-sm">{plugin.metadata.name}</p>
                      <p className="text-xs text-gray-500">{plugin.metadata.domain}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">
                      {plugin.last_activity && new Date(plugin.last_activity).toLocaleTimeString()}
                    </p>
                    <p className="text-xs text-gray-400">
                      {plugin.success_count} success / {plugin.error_count} errors
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </Card>
      )}
    </div>
  );
};
