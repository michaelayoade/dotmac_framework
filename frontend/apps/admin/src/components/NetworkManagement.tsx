/**
 * Network Management Dashboard - Admin Portal Integration
 * Demonstrates integration of @dotmac/network package in admin portal
 */

'use client';

import React, { useState } from 'react';
import { Card } from '@dotmac/primitives';
import {
  NetworkTopologyViewer,
  GeographicView,
  useNetworkTopology,
  useGeographicData,
  useNetworkMonitoring,
  type FilterOptions,
  type LayoutOptions
} from '@dotmac/network';
import {
  Network,
  Map,
  Activity,
  Settings,
  AlertTriangle,
  Users,
  Zap
} from 'lucide-react';

interface NetworkManagementProps {
  tenantId: string;
  currentUser: {
    id: string;
    name: string;
    role: string;
  };
}

export const NetworkManagement: React.FC<NetworkManagementProps> = ({
  tenantId,
  currentUser
}) => {
  // State for view modes
  const [activeView, setActiveView] = useState<'topology' | 'geographic' | 'monitoring'>('topology');
  const [layoutOptions, setLayoutOptions] = useState<LayoutOptions>({
    algorithm: 'force',
    animate: true
  });
  const [filters, setFilters] = useState<FilterOptions>({
    show_labels: true,
    show_performance_overlay: false
  });

  // Network data hooks
  const {
    nodes,
    links,
    topology_metrics,
    critical_nodes,
    loading: topologyLoading,
    error: topologyError,
    refresh: refreshTopology
  } = useNetworkTopology({
    tenant_id: tenantId,
    auto_refresh: true,
    include_performance_metrics: true
  });

  const {
    service_areas,
    network_nodes,
    coverage_gaps,
    loading: geoLoading,
    error: geoError
  } = useGeographicData({
    tenant_id: tenantId,
    include_coverage_analysis: true
  });

  const {
    alerts,
    performance_data,
    connection_status,
    loading: monitoringLoading
  } = useNetworkMonitoring({
    tenant_id: tenantId,
    real_time: true
  });

  // Handle topology node selection
  const handleNodeClick = (node: any) => {
    console.log('Node selected:', node);
    // Could open detailed node information modal
  };

  // Handle layout change
  const handleLayoutChange = (algorithm: string) => {
    setLayoutOptions(prev => ({
      ...prev,
      algorithm: algorithm as any
    }));
  };

  // Handle filter changes
  const togglePerformanceOverlay = () => {
    setFilters(prev => ({
      ...prev,
      show_performance_overlay: !prev.show_performance_overlay
    }));
  };

  return (
    <div className="network-management space-y-6">
      {/* Header with view controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Network Management</h1>
          <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setActiveView('topology')}
              className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
                activeView === 'topology'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Network className="h-4 w-4" />
              <span>Topology</span>
            </button>
            <button
              onClick={() => setActiveView('geographic')}
              className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
                activeView === 'geographic'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Map className="h-4 w-4" />
              <span>Geographic</span>
            </button>
            <button
              onClick={() => setActiveView('monitoring')}
              className={`px-3 py-2 text-sm font-medium rounded-md flex items-center space-x-2 ${
                activeView === 'monitoring'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Activity className="h-4 w-4" />
              <span>Monitoring</span>
            </button>
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`h-2 w-2 rounded-full ${
              connection_status === 'connected' ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-sm text-gray-600">
              {connection_status === 'connected' ? 'Live' : 'Disconnected'}
            </span>
          </div>

          {alerts.length > 0 && (
            <div className="flex items-center space-x-2 text-red-600">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm font-medium">{alerts.length} alerts</span>
            </div>
          )}
        </div>
      </div>

      {/* Network statistics cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Nodes</p>
              <p className="text-2xl font-bold text-gray-900">{nodes.length}</p>
            </div>
            <Network className="h-8 w-8 text-blue-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Links</p>
              <p className="text-2xl font-bold text-gray-900">
                {links.filter(link => link.status === 'active').length}
              </p>
            </div>
            <Zap className="h-8 w-8 text-green-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Critical Nodes</p>
              <p className="text-2xl font-bold text-gray-900">{critical_nodes?.length || 0}</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-yellow-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Service Areas</p>
              <p className="text-2xl font-bold text-gray-900">{service_areas.length}</p>
            </div>
            <Users className="h-8 w-8 text-purple-600" />
          </div>
        </Card>
      </div>

      {/* Main content area based on active view */}
      <div className="min-h-96">
        {activeView === 'topology' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Network Topology</h2>
              <div className="flex items-center space-x-4">
                <select
                  value={layoutOptions.algorithm}
                  onChange={(e) => handleLayoutChange(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="force">Force Layout</option>
                  <option value="hierarchical">Hierarchical</option>
                  <option value="circular">Circular</option>
                  <option value="grid">Grid</option>
                </select>

                <button
                  onClick={togglePerformanceOverlay}
                  className={`px-3 py-2 text-sm rounded-md ${
                    filters.show_performance_overlay
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Performance Overlay
                </button>
              </div>
            </div>

            {topologyLoading ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-gray-500">Loading topology...</div>
              </div>
            ) : topologyError ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-red-500">Error loading topology: {topologyError}</div>
              </div>
            ) : (
              <div className="h-96">
                <NetworkTopologyViewer
                  nodes={nodes}
                  links={links}
                  layout={layoutOptions}
                  filters={filters}
                  interactive={true}
                  show_controls={true}
                  show_legends={true}
                  on_node_click={handleNodeClick}
                  className="w-full h-full"
                />
              </div>
            )}
          </Card>
        )}

        {activeView === 'geographic' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Geographic View</h2>
              <div className="text-sm text-gray-600">
                {coverage_gaps.length} coverage gaps identified
              </div>
            </div>

            {geoLoading ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-gray-500">Loading geographic data...</div>
              </div>
            ) : geoError ? (
              <div className="h-96 flex items-center justify-center">
                <div className="text-red-500">Error loading geographic data: {geoError}</div>
              </div>
            ) : (
              <div className="h-96">
                <GeographicView
                  service_areas={service_areas}
                  network_nodes={network_nodes}
                  coverage_gaps={coverage_gaps}
                  show_coverage_overlay={true}
                  show_network_overlay={true}
                  interactive={true}
                  on_node_click={handleNodeClick}
                  className="w-full h-full"
                />
              </div>
            )}
          </Card>
        )}

        {activeView === 'monitoring' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Active Alerts</h2>
              <div className="space-y-3">
                {alerts.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">No active alerts</div>
                ) : (
                  alerts.slice(0, 5).map((alert) => (
                    <div key={alert.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <AlertTriangle className={`h-5 w-5 ${
                        alert.severity === 'critical' ? 'text-red-500' :
                        alert.severity === 'error' ? 'text-orange-500' :
                        alert.severity === 'warning' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{alert.message}</p>
                        <p className="text-xs text-gray-500">{new Date(alert.timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>

            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Performance Metrics</h2>
              <div className="space-y-4">
                {topology_metrics && (
                  <>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Network Density</span>
                      <span className="text-sm font-medium">
                        {(topology_metrics.basic_stats.density * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Connectivity</span>
                      <span className={`text-sm font-medium ${
                        topology_metrics.basic_stats.is_connected ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {topology_metrics.basic_stats.is_connected ? 'Connected' : 'Fragmented'}
                      </span>
                    </div>
                    {topology_metrics.degree_stats && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Avg Connections</span>
                        <span className="text-sm font-medium">
                          {topology_metrics.degree_stats.average_degree.toFixed(1)}
                        </span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};
