'use client';

import { clsx } from 'clsx';
import dynamic from 'next/dynamic';
import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';

import type { Technician, WorkOrder, Coordinates, BaseMapProps } from '../types';

import { BaseMap } from './BaseMap';

// Dynamically import Leaflet components
const Marker = dynamic(() => import('react-leaflet').then((mod) => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((mod) => mod.Popup), { ssr: false });
const Polyline = dynamic(() => import('react-leaflet').then((mod) => mod.Polyline), { ssr: false });
const Circle = dynamic(() => import('react-leaflet').then((mod) => mod.Circle), { ssr: false });
const LayerGroup = dynamic(() => import('react-leaflet').then((mod) => mod.LayerGroup), {
  ssr: false,
});

interface TechnicianLocationTrackerProps extends Omit<BaseMapProps, 'children'> {
  technicians: Technician[];
  workOrders?: WorkOrder[];
  onTechnicianSelect?: (technician: Technician) => void;
  onWorkOrderSelect?: (workOrder: WorkOrder) => void;
  showRoutes?: boolean;
  showWorkOrders?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
  className?: string;
}

interface TechnicianTrail {
  technicianId: string;
  positions: { coordinates: Coordinates; timestamp: Date }[];
}

interface RouteOptimization {
  technicianId: string;
  workOrderIds: string[];
  optimizedRoute: Coordinates[];
  estimatedTime: number;
  totalDistance: number;
}

export function TechnicianLocationTracker({
  technicians,
  workOrders = [],
  onTechnicianSelect,
  onWorkOrderSelect,
  showRoutes = true,
  showWorkOrders = true,
  autoRefresh = true,
  refreshInterval = 30000,
  className,
  ...mapProps
}: TechnicianLocationTrackerProps) {
  const [selectedTechnician, setSelectedTechnician] = useState<Technician | null>(null);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<WorkOrder | null>(null);
  const [technicianTrails, setTechnicianTrails] = useState<TechnicianTrail[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [liveTracking, setLiveTracking] = useState<boolean>(autoRefresh);

  const refreshTimerRef = useRef<NodeJS.Timeout>();

  // Group work orders by status and priority
  const workOrderGroups = useMemo(() => {
    const groups = {
      pending: workOrders.filter((wo) => wo.status === 'pending'),
      assigned: workOrders.filter((wo) => wo.status === 'assigned'),
      inProgress: workOrders.filter((wo) => wo.status === 'in-progress'),
      completed: workOrders.filter((wo) => wo.status === 'completed'),
    };

    // Sort by priority within each group
    Object.values(groups).forEach((group) => {
      group.sort((a, b) => {
        const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      });
    });

    return groups;
  }, [workOrders]);

  // Calculate technician statistics
  const technicianStats = useMemo(() => {
    const stats = {
      total: technicians.length,
      available: technicians.filter((t) => t.status === 'available').length,
      onJob: technicians.filter((t) => t.status === 'on-job').length,
      onBreak: technicians.filter((t) => t.status === 'break').length,
      offline: technicians.filter((t) => t.status === 'offline').length,
      averageWorkload: 0,
    };

    const activeWorkOrders = workOrders.filter((wo) =>
      ['assigned', 'in-progress'].includes(wo.status)
    );
    stats.averageWorkload = activeWorkOrders.length / Math.max(stats.available + stats.onJob, 1);

    return stats;
  }, [technicians, workOrders]);

  // Get technician marker icon and color based on status
  const getTechnicianIcon = useCallback((technician: Technician) => {
    const statusColors = {
      available: '#10B981',
      'on-job': '#3B82F6',
      break: '#F59E0B',
      offline: '#6B7280',
    };

    const statusIcons = {
      available: '✓',
      'on-job': '🔧',
      break: '☕',
      offline: '❌',
    };

    return {
      color: statusColors[technician.status],
      icon: statusIcons[technician.status],
    };
  }, []);

  // Get work order marker color based on priority and status
  const getWorkOrderColor = useCallback((workOrder: WorkOrder) => {
    if (workOrder.status === 'completed') return '#10B981';
    if (workOrder.status === 'in-progress') return '#3B82F6';

    const priorityColors = {
      critical: '#DC2626',
      high: '#EF4444',
      medium: '#F59E0B',
      low: '#6B7280',
    };

    return priorityColors[workOrder.priority];
  }, []);

  // Calculate estimated travel time between two points (simplified)
  const calculateTravelTime = useCallback((from: Coordinates, to: Coordinates): number => {
    // Simple distance calculation (Haversine formula simplified)
    const R = 6371; // Earth's radius in km
    const dLat = ((to.latitude - from.latitude) * Math.PI) / 180;
    const dLon = ((to.longitude - from.longitude) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((from.latitude * Math.PI) / 180) *
        Math.cos((to.latitude * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    // Assume average speed of 30 km/h in urban areas
    return Math.round((distance / 30) * 60); // minutes
  }, []);

  // Find nearest available technician to a work order
  const findNearestTechnician = useCallback(
    (workOrder: WorkOrder) => {
      const availableTechnicians = technicians.filter(
        (t) => t.status === 'available' && (!workOrder.type || t.skills.includes(workOrder.type))
      );

      if (availableTechnicians.length === 0) return null;

      const technicianDistances = availableTechnicians.map((technician) => {
        const travelTime = calculateTravelTime(technician.coordinates, workOrder.coordinates);
        return {
          technician,
          travelTime,
        };
      });

      return technicianDistances.sort((a, b) => a.travelTime - b.travelTime)[0];
    },
    [technicians, calculateTravelTime]
  );

  const handleTechnicianClick = useCallback(
    (technician: Technician) => {
      setSelectedTechnician(technician);
      if (onTechnicianSelect) {
        onTechnicianSelect(technician);
      }
    },
    [onTechnicianSelect]
  );

  const handleWorkOrderClick = useCallback(
    (workOrder: WorkOrder) => {
      setSelectedWorkOrder(workOrder);
      if (onWorkOrderSelect) {
        onWorkOrderSelect(workOrder);
      }
    },
    [onWorkOrderSelect]
  );

  const toggleLiveTracking = useCallback(() => {
    setLiveTracking((prev) => !prev);
  }, []);

  // Auto-refresh functionality
  useEffect(() => {
    if (liveTracking && refreshInterval > 0) {
      refreshTimerRef.current = setInterval(() => {
        setLastUpdate(new Date());
        // In a real implementation, this would trigger a data refresh
      }, refreshInterval);
    } else {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    }

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [liveTracking, refreshInterval]);

  // Update technician trails (in a real app, this would come from GPS data)
  useEffect(() => {
    // Simulate trail updates for active technicians
    const activeTrails = technicians
      .filter((t) => t.status !== 'offline')
      .map((t) => ({
        technicianId: t.id,
        positions: [
          {
            coordinates: t.coordinates,
            timestamp: new Date(),
          },
        ],
      }));

    setTechnicianTrails(activeTrails);
  }, [technicians]);

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className={clsx('relative w-full h-full', className)}>
      <BaseMap {...mapProps} className='w-full h-full'>
        {/* Technicians */}
        <LayerGroup>
          {technicians.map((technician) => {
            const style = getTechnicianIcon(technician);

            return (
              <Marker
                key={technician.id}
                position={[technician.coordinates.latitude, technician.coordinates.longitude]}
                eventHandlers={{
                  click: () => handleTechnicianClick(technician),
                }}
              >
                <Popup>
                  <div className='p-3 min-w-64'>
                    <h4 className='font-bold text-gray-900 mb-2'>{technician.name}</h4>
                    <div className='text-sm text-gray-600 space-y-1'>
                      <div>
                        <strong>Status:</strong>{' '}
                        <span className='capitalize'>{technician.status}</span>
                      </div>
                      <div>
                        <strong>Skills:</strong> {technician.skills.join(', ')}
                      </div>
                      {technician.currentWorkOrder && (
                        <div>
                          <strong>Current Job:</strong> {technician.currentWorkOrder}
                        </div>
                      )}
                      {technician.territory && (
                        <div>
                          <strong>Territory:</strong> {technician.territory}
                        </div>
                      )}
                      <div>
                        <strong>Location:</strong> {technician.coordinates.latitude.toFixed(4)},{' '}
                        {technician.coordinates.longitude.toFixed(4)}
                      </div>
                    </div>
                    {technician.status === 'available' && workOrderGroups.pending.length > 0 && (
                      <div className='mt-3 pt-2 border-t border-gray-200'>
                        <div className='text-xs text-gray-600'>
                          <strong>Nearest Unassigned Jobs:</strong>
                        </div>
                        {workOrderGroups.pending.slice(0, 3).map((wo) => {
                          const travelTime = calculateTravelTime(
                            technician.coordinates,
                            wo.coordinates
                          );
                          return (
                            <div key={wo.id} className='text-xs text-gray-600 mt-1'>
                              {wo.type} - {formatTime(travelTime)} away
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </LayerGroup>

        {/* Work Orders */}
        {showWorkOrders && (
          <LayerGroup>
            {workOrders.map((workOrder) => {
              const color = getWorkOrderColor(workOrder);
              const nearestTech = findNearestTechnician(workOrder);

              return (
                <Circle
                  key={workOrder.id}
                  center={[workOrder.coordinates.latitude, workOrder.coordinates.longitude]}
                  radius={100}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: 0.6,
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => handleWorkOrderClick(workOrder),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-64'>
                      <h4 className='font-bold text-gray-900 mb-2'>Work Order #{workOrder.id}</h4>
                      <div className='text-sm text-gray-600 space-y-1'>
                        <div>
                          <strong>Type:</strong>{' '}
                          <span className='capitalize'>{workOrder.type}</span>
                        </div>
                        <div>
                          <strong>Priority:</strong>{' '}
                          <span className='capitalize'>{workOrder.priority}</span>
                        </div>
                        <div>
                          <strong>Status:</strong>{' '}
                          <span className='capitalize'>{workOrder.status}</span>
                        </div>
                        <div>
                          <strong>Address:</strong> {workOrder.address}
                        </div>
                        <div>
                          <strong>Est. Duration:</strong> {formatTime(workOrder.estimatedDuration)}
                        </div>
                        {workOrder.scheduledTime && (
                          <div>
                            <strong>Scheduled:</strong> {workOrder.scheduledTime.toLocaleString()}
                          </div>
                        )}
                        {workOrder.technicianId && (
                          <div>
                            <strong>Assigned To:</strong>{' '}
                            {technicians.find((t) => t.id === workOrder.technicianId)?.name ||
                              workOrder.technicianId}
                          </div>
                        )}
                        <div>
                          <strong>Description:</strong> {workOrder.description}
                        </div>
                      </div>
                      {nearestTech && workOrder.status === 'pending' && (
                        <div className='mt-3 pt-2 border-t border-gray-200'>
                          <div className='text-xs text-green-600'>
                            <strong>Nearest Available Technician:</strong>
                            <br />
                            {nearestTech.technician.name} - {formatTime(nearestTech.travelTime)}{' '}
                            away
                          </div>
                        </div>
                      )}
                    </div>
                  </Popup>
                </Circle>
              );
            })}
          </LayerGroup>
        )}

        {/* Technician Routes */}
        {showRoutes && (
          <LayerGroup>
            {technicians
              .filter((t) => t.route && t.route.length > 1)
              .map((technician) => (
                <Polyline
                  key={`route-${technician.id}`}
                  positions={technician.route!.map((coord) => [coord.latitude, coord.longitude])}
                  pathOptions={{
                    color: getTechnicianIcon(technician).color,
                    weight: 3,
                    opacity: 0.7,
                    dashArray: '10, 10',
                  }}
                />
              ))}
          </LayerGroup>
        )}

        {/* Technician Trails (historical path) */}
        {showRoutes && (
          <LayerGroup>
            {technicianTrails.map((trail) => {
              const technician = technicians.find((t) => t.id === trail.technicianId);
              if (!technician || trail.positions.length < 2) return null;

              return (
                <Polyline
                  key={`trail-${trail.technicianId}`}
                  positions={trail.positions.map((pos) => [
                    pos.coordinates.latitude,
                    pos.coordinates.longitude,
                  ])}
                  pathOptions={{
                    color: getTechnicianIcon(technician).color,
                    weight: 2,
                    opacity: 0.4,
                  }}
                />
              );
            })}
          </LayerGroup>
        )}
      </BaseMap>

      {/* Controls */}
      <div className='absolute top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <div className='flex items-center justify-between mb-3'>
          <h4 className='text-sm font-semibold text-gray-900'>Live Tracking</h4>
          <button
            onClick={toggleLiveTracking}
            className={clsx(
              'px-2 py-1 text-xs rounded',
              liveTracking ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
            )}
          >
            {liveTracking ? 'ON' : 'OFF'}
          </button>
        </div>
        <div className='text-xs text-gray-600'>Last update: {lastUpdate.toLocaleTimeString()}</div>
      </div>

      {/* Technician Statistics */}
      <div className='absolute top-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-2'>Team Status</h4>
        <div className='grid grid-cols-2 gap-3 text-xs'>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-green-500'></div>
            <span>Available: {technicianStats.available}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-blue-500'></div>
            <span>On Job: {technicianStats.onJob}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-yellow-500'></div>
            <span>On Break: {technicianStats.onBreak}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-gray-500'></div>
            <span>Offline: {technicianStats.offline}</span>
          </div>
        </div>
        <div className='mt-2 pt-2 border-t border-gray-200 text-xs text-gray-600'>
          <div>Avg Workload: {technicianStats.averageWorkload.toFixed(1)} jobs/tech</div>
        </div>
      </div>

      {/* Work Order Summary */}
      <div className='absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-2'>Work Orders</h4>
        <div className='grid grid-cols-2 gap-3 text-xs'>
          <div>
            <span className='text-gray-600'>Pending:</span>
            <span className='ml-1 font-semibold'>{workOrderGroups.pending.length}</span>
          </div>
          <div>
            <span className='text-gray-600'>Assigned:</span>
            <span className='ml-1 font-semibold'>{workOrderGroups.assigned.length}</span>
          </div>
          <div>
            <span className='text-gray-600'>In Progress:</span>
            <span className='ml-1 font-semibold'>{workOrderGroups.inProgress.length}</span>
          </div>
          <div>
            <span className='text-gray-600'>Completed:</span>
            <span className='ml-1 font-semibold'>{workOrderGroups.completed.length}</span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className='absolute bottom-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-xs font-semibold text-gray-900 mb-2'>Priority Levels</h4>
        <div className='space-y-1 text-xs'>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-red-600'></div>
            <span>Critical</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-red-400'></div>
            <span>High</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-yellow-500'></div>
            <span>Medium</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-gray-500'></div>
            <span>Low</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TechnicianLocationTracker;
