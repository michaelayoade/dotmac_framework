'use client';

import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { Button } from '../../ui/Button';
import {
  Router,
  Map,
  Activity,
  Network,
  Wifi,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { useISPModules, useRealTime } from '@dotmac/headless';

export function NetworkManagement() {
  const { useNetworkDevices, useNetworkMonitoring, useNetworkTopology, useIPAM } = useISPModules();

  // Real-time WebSocket data
  const {
    isConnected: wsConnected,
    deviceUpdates,
    networkAlerts,
    connectionQuality,
  } = useRealTime();

  // Real-time network data from ISP Framework
  const { data: devices, isLoading: devicesLoading } = useNetworkDevices({
    limit: 100,
    status: 'all',
  });

  const { data: monitoring, isLoading: monitoringLoading } = useNetworkMonitoring();
  const { data: topology } = useNetworkTopology();
  const { data: ipamData } = useIPAM({ summary: true });

  // Calculate metrics from real data
  const totalDevices = devices?.data?.length || 0;
  const onlineDevices =
    devices?.data?.filter((device: any) => device.status === 'online')?.length || 0;
  const deviceUptime = totalDevices > 0 ? ((onlineDevices / totalDevices) * 100).toFixed(1) : '0.0';
  const allocatedIPs = ipamData?.data?.allocated_count || 0;
  const recentDeviceUpdates = deviceUpdates.slice(0, 5);
  const activeAlerts = networkAlerts.filter((alert: any) => !alert.resolved).length;

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <div>
          <div className='flex items-center space-x-3'>
            <h1 className='text-2xl font-bold text-gray-900'>Network Management</h1>
            {wsConnected && (
              <div className='flex items-center space-x-2'>
                <div className='flex items-center px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full'>
                  <Zap className='w-3 h-3 mr-1' />
                  Live
                </div>
                {activeAlerts > 0 && (
                  <div className='flex items-center px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-full'>
                    <AlertTriangle className='w-3 h-3 mr-1' />
                    {activeAlerts} Alerts
                  </div>
                )}
              </div>
            )}
          </div>
          <p className='text-gray-600'>
            Network infrastructure, IPAM, device monitoring, and RADIUS integration
            {wsConnected && (
              <span
                className={`ml-2 text-xs ${
                  connectionQuality === 'excellent'
                    ? 'text-green-600'
                    : connectionQuality === 'good'
                      ? 'text-blue-600'
                      : 'text-orange-600'
                }`}
              >
                • Real-time updates ({connectionQuality})
              </span>
            )}
          </p>
        </div>
        <div className='flex items-center space-x-2'>
          <Button variant='outline'>
            <Activity className='w-4 h-4 mr-2' />
            View Alerts
          </Button>
          <Button>
            <Wifi className='w-4 h-4 mr-2' />
            Network Scan
          </Button>
        </div>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6 text-center'>
            <Router className='w-12 h-12 text-blue-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Network Devices</h3>
            <p className='text-3xl font-bold text-blue-600'>
              {devicesLoading ? '...' : totalDevices}
            </p>
            <p className='text-sm text-gray-500'>
              {onlineDevices} online, {totalDevices - onlineDevices} offline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Network className='w-12 h-12 text-green-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>IP Addresses</h3>
            <p className='text-3xl font-bold text-green-600'>{allocatedIPs.toLocaleString()}</p>
            <p className='text-sm text-gray-500'>IPs allocated via IPAM</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Activity className='w-12 h-12 text-orange-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Network Health</h3>
            <p className='text-3xl font-bold text-orange-600'>
              {monitoringLoading ? '...' : `${deviceUptime}%`}
            </p>
            <p className='text-sm text-gray-500'>Overall uptime</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Map className='w-12 h-12 text-purple-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Topology Nodes</h3>
            <p className='text-3xl font-bold text-purple-600'>
              {topology?.data?.nodes?.length || 0}
            </p>
            <p className='text-sm text-gray-500'>Network topology elements</p>
          </CardContent>
        </Card>
      </div>

      {/* Real-time updates section */}
      {wsConnected && (recentDeviceUpdates.length > 0 || networkAlerts.length > 0) && (
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
          {/* Recent Device Updates */}
          {recentDeviceUpdates.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center'>
                  <Zap className='w-5 h-5 mr-2 text-green-500' />
                  Real-Time Device Updates
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-3 max-h-64 overflow-y-auto'>
                  {recentDeviceUpdates.map((update: any, index: number) => (
                    <div
                      key={index}
                      className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
                    >
                      <div className='flex items-center space-x-3'>
                        <div
                          className={`w-2 h-2 rounded-full ${
                            update.status === 'online'
                              ? 'bg-green-500'
                              : update.status === 'offline'
                                ? 'bg-red-500'
                                : 'bg-yellow-500'
                          }`}
                        />
                        <div>
                          <p className='font-medium text-sm'>{update.device_name}</p>
                          <p className='text-xs text-gray-500'>{update.ip_address}</p>
                        </div>
                      </div>
                      <div className='text-right'>
                        <p
                          className={`text-xs font-medium ${
                            update.status === 'online'
                              ? 'text-green-600'
                              : update.status === 'offline'
                                ? 'text-red-600'
                                : 'text-yellow-600'
                          }`}
                        >
                          {update.status.toUpperCase()}
                        </p>
                        <p className='text-xs text-gray-400'>
                          {new Date(update.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Network Alerts */}
          {networkAlerts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center'>
                  <AlertTriangle className='w-5 h-5 mr-2 text-orange-500' />
                  Network Alerts ({activeAlerts} active)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-3 max-h-64 overflow-y-auto'>
                  {networkAlerts.slice(0, 10).map((alert: any, index: number) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border-l-4 ${
                        alert.severity === 'critical'
                          ? 'border-red-500 bg-red-50'
                          : alert.severity === 'warning'
                            ? 'border-yellow-500 bg-yellow-50'
                            : 'border-blue-500 bg-blue-50'
                      }`}
                    >
                      <div className='flex items-start justify-between'>
                        <div className='flex-1'>
                          <p className='font-medium text-sm'>{alert.title}</p>
                          <p className='text-xs text-gray-600 mt-1'>{alert.description}</p>
                          <p className='text-xs text-gray-500 mt-1'>
                            {alert.device_name} • {new Date(alert.timestamp).toLocaleString()}
                          </p>
                        </div>
                        <div
                          className={`px-2 py-1 text-xs font-medium rounded-full ${
                            alert.severity === 'critical'
                              ? 'bg-red-100 text-red-800'
                              : alert.severity === 'warning'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {alert.severity}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Real-time device status grid */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center'>
              <Router className='w-5 h-5 mr-2' />
              Network Devices
            </CardTitle>
          </CardHeader>
          <CardContent>
            {devicesLoading ? (
              <div className='space-y-3'>
                {[...Array(5)].map((_, i) => (
                  <div key={i} className='h-12 bg-gray-100 rounded animate-pulse' />
                ))}
              </div>
            ) : (
              <div className='space-y-3 max-h-80 overflow-y-auto'>
                {devices?.data?.slice(0, 10).map((device: any) => (
                  <div
                    key={device.id}
                    className='flex items-center justify-between p-3 border rounded-lg'
                  >
                    <div className='flex items-center space-x-3'>
                      <div
                        className={`w-3 h-3 rounded-full ${
                          device.status === 'online'
                            ? 'bg-green-500'
                            : device.status === 'offline'
                              ? 'bg-red-500'
                              : 'bg-yellow-500'
                        }`}
                      />
                      <div>
                        <p className='font-medium'>{device.name}</p>
                        <p className='text-sm text-gray-500'>
                          {device.type} - {device.ip_address}
                        </p>
                      </div>
                    </div>
                    <div className='text-right'>
                      <p
                        className={`text-sm font-medium ${
                          device.status === 'online'
                            ? 'text-green-600'
                            : device.status === 'offline'
                              ? 'text-red-600'
                              : 'text-yellow-600'
                        }`}
                      >
                        {device.status === 'online' && (
                          <CheckCircle className='w-4 h-4 inline mr-1' />
                        )}
                        {device.status === 'offline' && (
                          <AlertTriangle className='w-4 h-4 inline mr-1' />
                        )}
                        {device.status === 'warning' && <Clock className='w-4 h-4 inline mr-1' />}
                        {device.status.toUpperCase()}
                      </p>
                      <p className='text-xs text-gray-500'>
                        Last seen: {new Date(device.last_seen).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {devices?.data?.length === 0 && (
                  <div className='text-center py-8 text-gray-500'>
                    No network devices found. Check your network configuration.
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className='flex items-center'>
              <Activity className='w-5 h-5 mr-2' />
              Network Monitoring
            </CardTitle>
          </CardHeader>
          <CardContent>
            {monitoringLoading ? (
              <div className='text-center py-8'>
                <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto'></div>
                <p className='text-gray-500 mt-2'>Loading monitoring data...</p>
              </div>
            ) : (
              <div className='space-y-4'>
                <div className='grid grid-cols-2 gap-4'>
                  <div className='bg-blue-50 p-4 rounded-lg'>
                    <h4 className='font-medium text-blue-900'>Bandwidth Usage</h4>
                    <p className='text-2xl font-bold text-blue-600'>
                      {monitoring?.data?.bandwidth_utilization || '0'}%
                    </p>
                  </div>
                  <div className='bg-green-50 p-4 rounded-lg'>
                    <h4 className='font-medium text-green-900'>Latency</h4>
                    <p className='text-2xl font-bold text-green-600'>
                      {monitoring?.data?.average_latency || '0'}ms
                    </p>
                  </div>
                  <div className='bg-orange-50 p-4 rounded-lg'>
                    <h4 className='font-medium text-orange-900'>Packet Loss</h4>
                    <p className='text-2xl font-bold text-orange-600'>
                      {monitoring?.data?.packet_loss || '0'}%
                    </p>
                  </div>
                  <div className='bg-purple-50 p-4 rounded-lg'>
                    <h4 className='font-medium text-purple-900'>Active Sessions</h4>
                    <p className='text-2xl font-bold text-purple-600'>
                      {monitoring?.data?.active_sessions || '0'}
                    </p>
                  </div>
                </div>
                <div className='pt-4 border-t'>
                  <p className='text-sm text-gray-600'>
                    Last updated:{' '}
                    {monitoring?.data?.last_updated
                      ? new Date(monitoring.data.last_updated).toLocaleString()
                      : 'Never'}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className='flex items-center'>
            <Map className='w-5 h-5 mr-2' />
            Network Topology
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className='text-center py-8 text-gray-500'>
            <Map className='w-16 h-16 mx-auto mb-4 text-gray-300' />
            <p className='text-lg font-medium mb-2'>Network Topology Visualization</p>
            <p className='text-sm'>
              Interactive network topology map integrates with ISP Framework networking module
            </p>
            <p className='text-xs mt-2'>
              Nodes: {topology?.data?.nodes?.length || 0} | Connections:{' '}
              {topology?.data?.edges?.length || 0}
            </p>
            <Button className='mt-4' variant='outline'>
              View Full Topology
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
