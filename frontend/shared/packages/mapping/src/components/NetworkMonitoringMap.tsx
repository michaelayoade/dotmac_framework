'use client';

import { clsx } from 'clsx';
import dynamic from 'next/dynamic';
import React, { useEffect, useState, useCallback, useMemo } from 'react';

import type { NetworkDevice, Incident, Coordinates, BaseMapProps, HeatmapPoint } from '../types';

import { BaseMap } from './BaseMap';

// Dynamically import Leaflet components
const Marker = dynamic(() => import('react-leaflet').then((mod) => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((mod) => mod.Popup), { ssr: false });
const Circle = dynamic(() => import('react-leaflet').then((mod) => mod.Circle), { ssr: false });
const Polygon = dynamic(() => import('react-leaflet').then((mod) => mod.Polygon), { ssr: false });
const LayerGroup = dynamic(() => import('react-leaflet').then((mod) => mod.LayerGroup), {
  ssr: false,
});

interface NetworkMonitoringMapProps extends Omit<BaseMapProps, 'children'> {
  devices: NetworkDevice[];
  incidents?: Incident[];
  onDeviceSelect?: (device: NetworkDevice) => void;
  onIncidentSelect?: (incident: Incident) => void;
  showHealthHeatmap?: boolean;
  showUtilizationOverlay?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  alertThreshold?: number; // Utilization percentage threshold
  className?: string;
}

interface NetworkAlert {
  id: string;
  deviceId: string;
  type: 'utilization' | 'offline' | 'latency' | 'packet_loss';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: Date;
  acknowledged: boolean;
}

interface MonitoringLayer {
  devices: boolean;
  incidents: boolean;
  heatmap: boolean;
  utilization: boolean;
  alerts: boolean;
}

export function NetworkMonitoringMap({
  devices,
  incidents = [],
  onDeviceSelect,
  onIncidentSelect,
  showHealthHeatmap = true,
  showUtilizationOverlay = false,
  autoRefresh = true,
  refreshInterval = 5000,
  alertThreshold = 80,
  className,
  ...mapProps
}: NetworkMonitoringMapProps) {
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [networkAlerts, setNetworkAlerts] = useState<NetworkAlert[]>([]);
  const [layerVisibility, setLayerVisibility] = useState<MonitoringLayer>({
    devices: true,
    incidents: true,
    heatmap: showHealthHeatmap,
    utilization: showUtilizationOverlay,
    alerts: true,
  });
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Generate network alerts based on device status and thresholds
  const generateAlerts = useCallback(() => {
    const alerts: NetworkAlert[] = [];

    devices.forEach((device) => {
      // Utilization alerts
      if (device.utilization > alertThreshold) {
        alerts.push({
          id: `util-${device.id}`,
          deviceId: device.id,
          type: 'utilization',
          severity:
            device.utilization > 95 ? 'critical' : device.utilization > 90 ? 'high' : 'medium',
          message: `High utilization: ${device.utilization.toFixed(1)}%`,
          timestamp: new Date(),
          acknowledged: false,
        });
      }

      // Offline alerts
      if (device.status === 'offline') {
        alerts.push({
          id: `offline-${device.id}`,
          deviceId: device.id,
          type: 'offline',
          severity: 'critical',
          message: 'Device offline',
          timestamp: new Date(Date.now() - Math.random() * 3600000), // Random time in last hour
          acknowledged: false,
        });
      }

      // Warning status alerts
      if (device.status === 'warning') {
        alerts.push({
          id: `warn-${device.id}`,
          deviceId: device.id,
          type: 'latency',
          severity: 'medium',
          message: 'Performance degradation detected',
          timestamp: new Date(Date.now() - Math.random() * 1800000), // Random time in last 30 min
          acknowledged: false,
        });
      }
    });

    return alerts;
  }, [devices, alertThreshold]);

  // Network health statistics
  const networkHealth = useMemo(() => {
    const total = devices.length;
    const online = devices.filter((d) => d.status === 'online').length;
    const warning = devices.filter((d) => d.status === 'warning').length;
    const critical = devices.filter((d) => d.status === 'critical').length;
    const offline = devices.filter((d) => d.status === 'offline').length;

    const avgUtilization = devices.reduce((sum, d) => sum + d.utilization, 0) / total;
    const totalCapacity = devices.reduce((sum, d) => sum + d.capacity, 0);
    const usedCapacity = devices.reduce((sum, d) => sum + (d.capacity * d.utilization) / 100, 0);

    const activeIncidents = incidents.filter((i) => i.status === 'active').length;
    const criticalIncidents = incidents.filter(
      (i) => i.severity === 'critical' && i.status === 'active'
    ).length;

    return {
      total,
      online,
      warning,
      critical,
      offline,
      healthScore: ((online + warning * 0.5) / total) * 100,
      avgUtilization,
      totalCapacity,
      usedCapacity,
      utilizationPercentage: (usedCapacity / totalCapacity) * 100,
      activeIncidents,
      criticalIncidents,
    };
  }, [devices, incidents]);

  // Device marker styling based on status and utilization
  const getDeviceStyle = useCallback(
    (device: NetworkDevice) => {
      const baseStyles = {
        router: { size: 12, strokeWidth: 2 },
        switch: { size: 10, strokeWidth: 2 },
        'fiber-node': { size: 14, strokeWidth: 2 },
        tower: { size: 16, strokeWidth: 3 },
        pop: { size: 18, strokeWidth: 3 },
        core: { size: 20, strokeWidth: 4 },
      };

      const statusColors = {
        online: '#10B981',
        warning: '#F59E0B',
        critical: '#EF4444',
        offline: '#6B7280',
      };

      const base = baseStyles[device.type] || baseStyles.router;
      const utilizationBonus = Math.floor(device.utilization / 20) * 2;

      return {
        radius: base.size + utilizationBonus,
        color: statusColors[device.status],
        weight: base.strokeWidth,
        fillOpacity: device.utilization > alertThreshold ? 0.8 : 0.6,
      };
    },
    [alertThreshold]
  );

  // Incident area styling
  const getIncidentStyle = useCallback((incident: Incident) => {
    const severityColors = {
      low: '#3B82F6',
      medium: '#F59E0B',
      high: '#EF4444',
      critical: '#DC2626',
    };

    const statusOpacity = {
      active: 0.4,
      investigating: 0.3,
      resolved: 0.1,
    };

    return {
      color: severityColors[incident.severity],
      fillColor: severityColors[incident.severity],
      fillOpacity: statusOpacity[incident.status],
      weight: incident.severity === 'critical' ? 3 : 2,
      dashArray: incident.status === 'resolved' ? '10, 10' : undefined,
    };
  }, []);

  // Generate heatmap data for network health
  const heatmapData = useMemo(() => {
    if (!showHealthHeatmap) return [];

    return devices.map((device) => ({
      coordinates: device.coordinates,
      value:
        device.status === 'online'
          ? device.utilization
          : device.status === 'warning'
            ? 50
            : device.status === 'critical'
              ? 80
              : 0,
      weight:
        device.type === 'core' ? 3 : device.type === 'pop' ? 2.5 : device.type === 'tower' ? 2 : 1,
      metadata: { deviceId: device.id, status: device.status },
    }));
  }, [devices, showHealthHeatmap]);

  const handleDeviceClick = useCallback(
    (device: NetworkDevice) => {
      setSelectedDevice(device);
      if (onDeviceSelect) {
        onDeviceSelect(device);
      }
    },
    [onDeviceSelect]
  );

  const handleIncidentClick = useCallback(
    (incident: Incident) => {
      setSelectedIncident(incident);
      if (onIncidentSelect) {
        onIncidentSelect(incident);
      }
    },
    [onIncidentSelect]
  );

  const toggleLayer = useCallback((layer: keyof MonitoringLayer) => {
    setLayerVisibility((prev) => ({
      ...prev,
      [layer]: !prev[layer],
    }));
  }, []);

  // Auto-refresh functionality
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (autoRefresh && refreshInterval > 0) {
      interval = setInterval(() => {
        setLastUpdate(new Date());
        setNetworkAlerts(generateAlerts());
      }, refreshInterval);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, refreshInterval, generateAlerts]);

  // Initialize alerts
  useEffect(() => {
    setNetworkAlerts(generateAlerts());
  }, [generateAlerts]);

  const formatUptime = (lastUpdate: Date) => {
    const diffMs = Date.now() - lastUpdate.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ${diffHours % 24}h`;
    if (diffHours > 0) return `${diffHours}h ${diffMins % 60}m`;
    return `${diffMins}m`;
  };

  return (
    <div className={clsx('relative w-full h-full', className)}>
      <BaseMap {...mapProps} className='w-full h-full'>
        {/* Network Devices */}
        {layerVisibility.devices && (
          <LayerGroup>
            {devices.map((device) => {
              const style = getDeviceStyle(device);
              const deviceAlerts = networkAlerts.filter((alert) => alert.deviceId === device.id);

              return (
                <Circle
                  key={device.id}
                  center={[device.coordinates.latitude, device.coordinates.longitude]}
                  radius={style.radius * 50} // Scale for map visibility
                  pathOptions={style}
                  eventHandlers={{
                    click: () => handleDeviceClick(device),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-64'>
                      <div className='flex items-center justify-between mb-2'>
                        <h4 className='font-bold text-gray-900'>{device.name}</h4>
                        <div
                          className={clsx(
                            'px-2 py-1 text-xs rounded-full',
                            device.status === 'online'
                              ? 'bg-green-100 text-green-800'
                              : device.status === 'warning'
                                ? 'bg-yellow-100 text-yellow-800'
                                : device.status === 'critical'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-gray-100 text-gray-800'
                          )}
                        >
                          {device.status.toUpperCase()}
                        </div>
                      </div>

                      <div className='text-sm text-gray-600 space-y-1 mb-3'>
                        <div>
                          <strong>Type:</strong> {device.type.replace('-', ' ').toUpperCase()}
                        </div>
                        <div>
                          <strong>Capacity:</strong> {device.capacity.toLocaleString()} Mbps
                        </div>
                        <div>
                          <strong>Utilization:</strong>
                          <span
                            className={clsx(
                              'ml-1 font-semibold',
                              device.utilization > alertThreshold
                                ? 'text-red-600'
                                : device.utilization > 70
                                  ? 'text-yellow-600'
                                  : 'text-green-600'
                            )}
                          >
                            {device.utilization.toFixed(1)}%
                          </span>
                        </div>
                        <div>
                          <strong>Connections:</strong> {device.connections.length}
                        </div>
                        <div>
                          <strong>Last Update:</strong> {formatUptime(device.lastUpdate)}
                        </div>
                      </div>

                      {deviceAlerts.length > 0 && (
                        <div className='border-t border-gray-200 pt-2'>
                          <div className='text-xs font-semibold text-red-600 mb-1'>
                            Active Alerts:
                          </div>
                          {deviceAlerts.map((alert) => (
                            <div key={alert.id} className='text-xs text-red-600'>
                              • {alert.message}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </Popup>
                </Circle>
              );
            })}
          </LayerGroup>
        )}

        {/* Incidents */}
        {layerVisibility.incidents && incidents.length > 0 && (
          <LayerGroup>
            {incidents.map((incident) => {
              const style = getIncidentStyle(incident);
              const coordinates: [number, number][] = incident.affectedArea.map((coord) => [
                coord.latitude,
                coord.longitude,
              ]);

              return (
                <Polygon
                  key={incident.id}
                  positions={
                    coordinates.length > 0
                      ? coordinates
                      : [
                          [
                            incident.coordinates.latitude - 0.01,
                            incident.coordinates.longitude - 0.01,
                          ],
                          [
                            incident.coordinates.latitude - 0.01,
                            incident.coordinates.longitude + 0.01,
                          ],
                          [
                            incident.coordinates.latitude + 0.01,
                            incident.coordinates.longitude + 0.01,
                          ],
                          [
                            incident.coordinates.latitude + 0.01,
                            incident.coordinates.longitude - 0.01,
                          ],
                        ]
                  }
                  pathOptions={style}
                  eventHandlers={{
                    click: () => handleIncidentClick(incident),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-64'>
                      <div className='flex items-center justify-between mb-2'>
                        <h4 className='font-bold text-gray-900'>Incident #{incident.id}</h4>
                        <div
                          className={clsx(
                            'px-2 py-1 text-xs rounded-full',
                            incident.severity === 'critical'
                              ? 'bg-red-100 text-red-800'
                              : incident.severity === 'high'
                                ? 'bg-orange-100 text-orange-800'
                                : incident.severity === 'medium'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-blue-100 text-blue-800'
                          )}
                        >
                          {incident.severity.toUpperCase()}
                        </div>
                      </div>

                      <div className='text-sm text-gray-600 space-y-1'>
                        <div>
                          <strong>Type:</strong> <span className='capitalize'>{incident.type}</span>
                        </div>
                        <div>
                          <strong>Status:</strong>{' '}
                          <span className='capitalize'>{incident.status}</span>
                        </div>
                        <div>
                          <strong>Affected Customers:</strong>{' '}
                          {incident.affectedCustomers.toLocaleString()}
                        </div>
                        <div>
                          <strong>Est. Revenue Loss:</strong> $
                          {incident.estimatedRevenueLoss.toLocaleString()}
                        </div>
                        <div>
                          <strong>Start Time:</strong> {incident.startTime.toLocaleString()}
                        </div>
                        {incident.endTime && (
                          <div>
                            <strong>End Time:</strong> {incident.endTime.toLocaleString()}
                          </div>
                        )}
                        {incident.cause && (
                          <div>
                            <strong>Cause:</strong> {incident.cause}
                          </div>
                        )}
                        {incident.resolution && (
                          <div>
                            <strong>Resolution:</strong> {incident.resolution}
                          </div>
                        )}
                      </div>
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </LayerGroup>
        )}
      </BaseMap>

      {/* Layer Controls */}
      <div className='absolute top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Monitoring Layers</h4>
        <div className='space-y-2 text-sm'>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.devices}
              onChange={() => toggleLayer('devices')}
              className='rounded border-gray-300'
            />
            <span>Network Devices</span>
          </label>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.incidents}
              onChange={() => toggleLayer('incidents')}
              className='rounded border-gray-300'
            />
            <span>Incidents</span>
          </label>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.alerts}
              onChange={() => toggleLayer('alerts')}
              className='rounded border-gray-300'
            />
            <span>Alerts</span>
          </label>
        </div>
        <div className='mt-3 pt-2 border-t border-gray-200 text-xs text-gray-600'>
          Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
          <br />
          Last update: {lastUpdate.toLocaleTimeString()}
        </div>
      </div>

      {/* Network Health Dashboard */}
      <div className='absolute top-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Network Health</h4>

        <div className='grid grid-cols-2 gap-3 mb-3'>
          <div className='text-center'>
            <div
              className={clsx(
                'text-2xl font-bold',
                networkHealth.healthScore > 90
                  ? 'text-green-600'
                  : networkHealth.healthScore > 70
                    ? 'text-yellow-600'
                    : 'text-red-600'
              )}
            >
              {networkHealth.healthScore.toFixed(0)}%
            </div>
            <div className='text-xs text-gray-600'>Health Score</div>
          </div>
          <div className='text-center'>
            <div
              className={clsx(
                'text-2xl font-bold',
                networkHealth.utilizationPercentage > 80
                  ? 'text-red-600'
                  : networkHealth.utilizationPercentage > 60
                    ? 'text-yellow-600'
                    : 'text-green-600'
              )}
            >
              {networkHealth.utilizationPercentage.toFixed(0)}%
            </div>
            <div className='text-xs text-gray-600'>Utilization</div>
          </div>
        </div>

        <div className='space-y-1 text-xs'>
          <div className='flex justify-between'>
            <span>Online:</span>
            <span className='font-semibold text-green-600'>{networkHealth.online}</span>
          </div>
          <div className='flex justify-between'>
            <span>Warning:</span>
            <span className='font-semibold text-yellow-600'>{networkHealth.warning}</span>
          </div>
          <div className='flex justify-between'>
            <span>Critical:</span>
            <span className='font-semibold text-red-600'>{networkHealth.critical}</span>
          </div>
          <div className='flex justify-between'>
            <span>Offline:</span>
            <span className='font-semibold text-gray-600'>{networkHealth.offline}</span>
          </div>
        </div>
      </div>

      {/* Active Alerts Panel */}
      {layerVisibility.alerts && networkAlerts.length > 0 && (
        <div className='absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3 max-w-sm'>
          <div className='flex items-center justify-between mb-2'>
            <h4 className='text-sm font-semibold text-gray-900'>Active Alerts</h4>
            <span className='bg-red-100 text-red-800 px-2 py-1 text-xs rounded-full'>
              {networkAlerts.filter((a) => !a.acknowledged).length}
            </span>
          </div>

          <div className='max-h-40 overflow-y-auto space-y-1'>
            {networkAlerts.slice(0, 5).map((alert) => {
              const device = devices.find((d) => d.id === alert.deviceId);
              return (
                <div
                  key={alert.id}
                  className={clsx(
                    'p-2 rounded text-xs',
                    alert.severity === 'critical'
                      ? 'bg-red-50 border border-red-200'
                      : alert.severity === 'high'
                        ? 'bg-orange-50 border border-orange-200'
                        : alert.severity === 'medium'
                          ? 'bg-yellow-50 border border-yellow-200'
                          : 'bg-blue-50 border border-blue-200'
                  )}
                >
                  <div className='font-semibold'>{device?.name || alert.deviceId}</div>
                  <div className='text-gray-600'>{alert.message}</div>
                  <div className='text-gray-500'>{alert.timestamp.toLocaleTimeString()}</div>
                </div>
              );
            })}
            {networkAlerts.length > 5 && (
              <div className='text-xs text-gray-500 text-center py-1'>
                +{networkAlerts.length - 5} more alerts
              </div>
            )}
          </div>
        </div>
      )}

      {/* Incident Summary */}
      {incidents.length > 0 && (
        <div className='absolute bottom-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
          <h4 className='text-sm font-semibold text-gray-900 mb-2'>Incidents</h4>
          <div className='grid grid-cols-2 gap-3 text-xs'>
            <div>
              <span className='text-gray-600'>Active:</span>
              <span className='ml-1 font-semibold text-red-600'>
                {networkHealth.activeIncidents}
              </span>
            </div>
            <div>
              <span className='text-gray-600'>Critical:</span>
              <span className='ml-1 font-semibold text-red-800'>
                {networkHealth.criticalIncidents}
              </span>
            </div>
            <div>
              <span className='text-gray-600'>Resolved:</span>
              <span className='ml-1 font-semibold text-green-600'>
                {incidents.filter((i) => i.status === 'resolved').length}
              </span>
            </div>
            <div>
              <span className='text-gray-600'>Total:</span>
              <span className='ml-1 font-semibold text-gray-900'>{incidents.length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default NetworkMonitoringMap;
