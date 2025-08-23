'use client';

import { clsx } from 'clsx';
import dynamic from 'next/dynamic';
import React, { useEffect, useState, useCallback, useMemo } from 'react';

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

interface WorkOrderRoutingMapProps extends Omit<BaseMapProps, 'children'> {
  technicians: Technician[];
  workOrders: WorkOrder[];
  onTechnicianSelect?: (technician: Technician) => void;
  onWorkOrderSelect?: (workOrder: WorkOrder) => void;
  onRouteOptimize?: (technicianId: string, workOrderIds: string[]) => void;
  showOptimizedRoutes?: boolean;
  showTrafficData?: boolean;
  routingAlgorithm?: 'nearest' | 'priority' | 'balanced' | 'time_window';
  className?: string;
}

interface OptimizedRoute {
  technicianId: string;
  workOrderSequence: string[];
  coordinates: Coordinates[];
  totalDistance: number;
  estimatedTime: number;
  estimatedCost: number;
}

interface RouteStats {
  totalWorkOrders: number;
  assignedOrders: number;
  unassignedOrders: number;
  totalDistance: number;
  estimatedTime: number;
  efficiencyScore: number;
}

export function WorkOrderRoutingMap({
  technicians,
  workOrders,
  onTechnicianSelect,
  onWorkOrderSelect,
  onRouteOptimize,
  showOptimizedRoutes = true,
  showTrafficData = false,
  routingAlgorithm = 'balanced',
  className,
  ...mapProps
}: WorkOrderRoutingMapProps) {
  const [selectedTechnician, setSelectedTechnician] = useState<Technician | null>(null);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<WorkOrder | null>(null);
  const [optimizedRoutes, setOptimizedRoutes] = useState<OptimizedRoute[]>([]);
  const [isOptimizing, setIsOptimizing] = useState(false);

  // Calculate distance between two coordinates (Haversine formula)
  const calculateDistance = useCallback((coord1: Coordinates, coord2: Coordinates): number => {
    const R = 6371; // Earth's radius in km
    const dLat = ((coord2.latitude - coord1.latitude) * Math.PI) / 180;
    const dLon = ((coord2.longitude - coord1.longitude) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((coord1.latitude * Math.PI) / 180) *
        Math.cos((coord2.latitude * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }, []);

  // Estimate travel time based on distance and traffic conditions
  const estimateTravelTime = useCallback(
    (distance: number, trafficMultiplier: number = 1): number => {
      const baseSpeed = 30; // km/h average urban speed
      const adjustedSpeed = baseSpeed / trafficMultiplier;
      return (distance / adjustedSpeed) * 60; // Convert to minutes
    },
    []
  );

  // Group work orders by priority and status
  const workOrderGroups = useMemo(() => {
    const unassigned = workOrders.filter((wo) => wo.status === 'pending');
    const assigned = workOrders.filter((wo) => wo.status === 'assigned');
    const inProgress = workOrders.filter((wo) => wo.status === 'in-progress');

    // Sort by priority within each group
    const sortByPriority = (orders: WorkOrder[]) => {
      const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
      return orders.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
    };

    return {
      unassigned: sortByPriority(unassigned),
      assigned: sortByPriority(assigned),
      inProgress: sortByPriority(inProgress),
    };
  }, [workOrders]);

  // Optimize routes using selected algorithm
  const optimizeRoutes = useCallback(async () => {
    setIsOptimizing(true);

    try {
      const routes: OptimizedRoute[] = [];

      for (const technician of technicians.filter(
        (t) => t.status === 'available' || t.status === 'on-job'
      )) {
        // Get relevant work orders for this technician
        const eligibleOrders = workOrderGroups.unassigned.filter(
          (wo) => !wo.type || technician.skills.includes(wo.type)
        );

        if (eligibleOrders.length === 0) continue;

        // Apply routing algorithm
        let orderedWorkOrders: WorkOrder[] = [];

        switch (routingAlgorithm) {
          case 'nearest':
            orderedWorkOrders = optimizeByNearest(technician, eligibleOrders);
            break;
          case 'priority':
            orderedWorkOrders = optimizeByPriority(technician, eligibleOrders);
            break;
          case 'time_window':
            orderedWorkOrders = optimizeByTimeWindow(technician, eligibleOrders);
            break;
          case 'balanced':
          default:
            orderedWorkOrders = optimizeBalanced(technician, eligibleOrders);
            break;
        }

        if (orderedWorkOrders.length === 0) continue;

        // Calculate route coordinates and metrics
        const coordinates = [
          technician.coordinates,
          ...orderedWorkOrders
            .map((wo) => wo.coordinates)
            .filter((coord): coord is Coordinates => coord !== undefined),
        ];

        if (coordinates.length < 2) continue; // Need at least start and one destination
        let totalDistance = 0;
        let estimatedTime = 0;

        for (let i = 0; i < coordinates.length - 1; i++) {
          const coord1 = coordinates[i];
          const coord2 = coordinates[i + 1];
          if (!coord1 || !coord2) continue;

          const distance = calculateDistance(coord1, coord2);
          const travelTime = estimateTravelTime(distance);

          totalDistance += distance;
          estimatedTime += travelTime;

          // Add estimated work time
          if (i > 0) {
            estimatedTime += orderedWorkOrders[i - 1]?.estimatedDuration || 0;
          }
        }

        const estimatedCost = (estimatedTime / 60) * 50; // $50/hour labor cost

        routes.push({
          technicianId: technician.id,
          workOrderSequence: orderedWorkOrders.map((wo) => wo.id),
          coordinates,
          totalDistance,
          estimatedTime,
          estimatedCost,
        });
      }

      setOptimizedRoutes(routes);
    } catch (error) {
      console.error('Route optimization failed:', error);
    } finally {
      setIsOptimizing(false);
    }
  }, [technicians, workOrderGroups, routingAlgorithm, calculateDistance, estimateTravelTime]);

  // Routing algorithms
  const optimizeByNearest = useCallback(
    (technician: Technician, orders: WorkOrder[]): WorkOrder[] => {
      const result: WorkOrder[] = [];
      const remaining = [...orders];
      let currentPosition = technician.coordinates;

      while (remaining.length > 0) {
        let nearestIndex = 0;
        const firstOrderCoords = remaining[0]?.coordinates;
        if (!firstOrderCoords) break;

        let minDistance = calculateDistance(currentPosition, firstOrderCoords);

        for (let i = 1; i < remaining.length; i++) {
          const orderCoords = remaining[i]?.coordinates;
          if (!orderCoords) continue;

          const distance = calculateDistance(currentPosition, orderCoords);
          if (distance < minDistance) {
            minDistance = distance;
            nearestIndex = i;
          }
        }

        const selectedOrder = remaining.splice(nearestIndex, 1)[0];
        if (!selectedOrder?.coordinates) break;

        result.push(selectedOrder);
        currentPosition = selectedOrder.coordinates;
      }

      return result.slice(0, 8); // Limit to 8 orders per technician
    },
    [calculateDistance]
  );

  const optimizeByPriority = useCallback(
    (technician: Technician, orders: WorkOrder[]): WorkOrder[] => {
      // Sort by priority first, then by distance
      return orders
        .map((order) => ({
          order,
          distance: calculateDistance(technician.coordinates, order.coordinates),
        }))
        .sort((a, b) => {
          const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
          const priorityDiff = priorityOrder[a.order.priority] - priorityOrder[b.order.priority];
          return priorityDiff !== 0 ? priorityDiff : a.distance - b.distance;
        })
        .slice(0, 8)
        .map((item) => item.order);
    },
    [calculateDistance]
  );

  const optimizeByTimeWindow = useCallback(
    (technician: Technician, orders: WorkOrder[]): WorkOrder[] => {
      // Filter orders with scheduled times and sort by time
      const scheduledOrders = orders
        .filter((order) => order.scheduledTime)
        .sort((a, b) => a.scheduledTime!.getTime() - b.scheduledTime!.getTime());

      return scheduledOrders.slice(0, 6);
    },
    []
  );

  const optimizeBalanced = useCallback(
    (technician: Technician, orders: WorkOrder[]): WorkOrder[] => {
      // Balanced approach considering priority, distance, and time
      return orders
        .map((order) => {
          const distance = calculateDistance(technician.coordinates, order.coordinates);
          const priorityScore = { critical: 100, high: 75, medium: 50, low: 25 }[order.priority];
          const distanceScore = Math.max(0, 100 - distance * 10); // Closer = higher score
          const timeScore = order.scheduledTime ? 80 : 40; // Scheduled orders get bonus

          const totalScore = priorityScore * 0.5 + distanceScore * 0.3 + timeScore * 0.2;

          return { order, score: totalScore, distance };
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 8)
        .map((item) => item.order);
    },
    [calculateDistance]
  );

  // Calculate route statistics
  const routeStats = useMemo((): RouteStats => {
    const totalDistance = optimizedRoutes.reduce((sum, route) => sum + route.totalDistance, 0);
    const estimatedTime = optimizedRoutes.reduce((sum, route) => sum + route.estimatedTime, 0);
    const assignedOrders = optimizedRoutes.reduce(
      (sum, route) => sum + route.workOrderSequence.length,
      0
    );

    const efficiencyScore = workOrders.length > 0 ? (assignedOrders / workOrders.length) * 100 : 0;

    return {
      totalWorkOrders: workOrders.length,
      assignedOrders,
      unassignedOrders: workOrders.length - assignedOrders,
      totalDistance,
      estimatedTime,
      efficiencyScore,
    };
  }, [optimizedRoutes, workOrders]);

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

  const handleOptimizeClick = useCallback(() => {
    optimizeRoutes();
  }, [optimizeRoutes]);

  const getWorkOrderColor = useCallback((workOrder: WorkOrder) => {
    const priorityColors = {
      critical: '#DC2626',
      high: '#EF4444',
      medium: '#F59E0B',
      low: '#6B7280',
    };
    return priorityColors[workOrder.priority];
  }, []);

  const getTechnicianRouteColor = useCallback(
    (technicianId: string) => {
      const colors = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EF4444', '#06B6D4'];
      const index = technicians.findIndex((t) => t.id === technicianId);
      return colors[index % colors.length];
    },
    [technicians]
  );

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className={clsx('relative w-full h-full', className)}>
      <BaseMap {...mapProps} className='w-full h-full'>
        {/* Technicians */}
        <LayerGroup>
          {technicians.map((technician) => (
            <Marker
              key={technician.id}
              position={[technician.coordinates.latitude, technician.coordinates.longitude]}
              eventHandlers={{
                click: () => handleTechnicianClick(technician),
              }}
            >
              <Popup>
                <div className='p-3 min-w-48'>
                  <h4 className='font-bold text-gray-900 mb-2'>{technician.name}</h4>
                  <div className='text-sm text-gray-600 space-y-1'>
                    <div>
                      <strong>Status:</strong>{' '}
                      <span className='capitalize'>{technician.status}</span>
                    </div>
                    <div>
                      <strong>Skills:</strong> {technician.skills.join(', ')}
                    </div>
                    {technician.territory && (
                      <div>
                        <strong>Territory:</strong> {technician.territory}
                      </div>
                    )}
                  </div>

                  {/* Route information */}
                  {optimizedRoutes.find((r) => r.technicianId === technician.id) && (
                    <div className='mt-3 pt-2 border-t border-gray-200'>
                      {(() => {
                        const route = optimizedRoutes.find(
                          (r) => r.technicianId === technician.id
                        )!;
                        return (
                          <div className='text-xs text-gray-600'>
                            <div>
                              <strong>Assigned Orders:</strong> {route.workOrderSequence.length}
                            </div>
                            <div>
                              <strong>Total Distance:</strong> {route.totalDistance.toFixed(1)} km
                            </div>
                            <div>
                              <strong>Estimated Time:</strong> {formatTime(route.estimatedTime)}
                            </div>
                            <div>
                              <strong>Estimated Cost:</strong> ${route.estimatedCost.toFixed(0)}
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </LayerGroup>

        {/* Work Orders */}
        <LayerGroup>
          {workOrders.map((workOrder) => {
            const color = getWorkOrderColor(workOrder);

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
                  <div className='p-3 min-w-48'>
                    <h4 className='font-bold text-gray-900 mb-2'>Work Order #{workOrder.id}</h4>
                    <div className='text-sm text-gray-600 space-y-1'>
                      <div>
                        <strong>Type:</strong> <span className='capitalize'>{workOrder.type}</span>
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
                        <strong>Duration:</strong> {formatTime(workOrder.estimatedDuration)}
                      </div>
                      {workOrder.scheduledTime && (
                        <div>
                          <strong>Scheduled:</strong> {workOrder.scheduledTime.toLocaleString()}
                        </div>
                      )}
                      <div>
                        <strong>Description:</strong> {workOrder.description}
                      </div>
                    </div>
                  </div>
                </Popup>
              </Circle>
            );
          })}
        </LayerGroup>

        {/* Optimized Routes */}
        {showOptimizedRoutes &&
          optimizedRoutes.map((route) => {
            const color = getTechnicianRouteColor(route.technicianId);
            const coordinates: [number, number][] = route.coordinates.map((coord) => [
              coord.latitude,
              coord.longitude,
            ]);

            return (
              <Polyline
                key={`route-${route.technicianId}`}
                positions={coordinates}
                pathOptions={{
                  color,
                  weight: 4,
                  opacity: 0.8,
                }}
              />
            );
          })}
      </BaseMap>

      {/* Controls */}
      <div className='absolute top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Route Optimization</h4>

        <div className='space-y-2 mb-3'>
          <select
            value={routingAlgorithm}
            onChange={(e) => setOptimizedRoutes([])} // Clear routes when algorithm changes
            className='w-full px-2 py-1 text-sm border border-gray-300 rounded'
          >
            <option value='balanced'>Balanced</option>
            <option value='nearest'>Nearest First</option>
            <option value='priority'>Priority First</option>
            <option value='time_window'>Time Windows</option>
          </select>
        </div>

        <button
          onClick={handleOptimizeClick}
          disabled={isOptimizing}
          className={clsx(
            'w-full px-3 py-2 text-sm rounded transition-colors',
            isOptimizing
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          )}
        >
          {isOptimizing ? 'Optimizing...' : 'Optimize Routes'}
        </button>
      </div>

      {/* Route Statistics */}
      <div className='absolute top-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-2'>Route Statistics</h4>

        <div className='grid grid-cols-2 gap-3 mb-2'>
          <div className='text-center'>
            <div className='text-lg font-bold text-blue-600'>
              {routeStats.efficiencyScore.toFixed(0)}%
            </div>
            <div className='text-xs text-gray-600'>Efficiency</div>
          </div>
          <div className='text-center'>
            <div className='text-lg font-bold text-green-600'>
              {routeStats.totalDistance.toFixed(0)} km
            </div>
            <div className='text-xs text-gray-600'>Distance</div>
          </div>
        </div>

        <div className='space-y-1 text-xs'>
          <div className='flex justify-between'>
            <span>Total Orders:</span>
            <span className='font-semibold'>{routeStats.totalWorkOrders}</span>
          </div>
          <div className='flex justify-between'>
            <span>Assigned:</span>
            <span className='font-semibold text-green-600'>{routeStats.assignedOrders}</span>
          </div>
          <div className='flex justify-between'>
            <span>Unassigned:</span>
            <span className='font-semibold text-red-600'>{routeStats.unassignedOrders}</span>
          </div>
          <div className='flex justify-between'>
            <span>Est. Time:</span>
            <span className='font-semibold'>{formatTime(routeStats.estimatedTime)}</span>
          </div>
        </div>
      </div>

      {/* Work Order Summary */}
      <div className='absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-2'>Work Orders by Priority</h4>
        <div className='grid grid-cols-2 gap-2 text-xs'>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-red-600'></div>
            <span>Critical: {workOrders.filter((wo) => wo.priority === 'critical').length}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-red-400'></div>
            <span>High: {workOrders.filter((wo) => wo.priority === 'high').length}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-yellow-500'></div>
            <span>Medium: {workOrders.filter((wo) => wo.priority === 'medium').length}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-gray-500'></div>
            <span>Low: {workOrders.filter((wo) => wo.priority === 'low').length}</span>
          </div>
        </div>
      </div>

      {/* Technician Legend */}
      {optimizedRoutes.length > 0 && (
        <div className='absolute bottom-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
          <h4 className='text-xs font-semibold text-gray-900 mb-2'>Technician Routes</h4>
          <div className='space-y-1'>
            {optimizedRoutes.map((route) => {
              const technician = technicians.find((t) => t.id === route.technicianId);
              const color = getTechnicianRouteColor(route.technicianId);

              return (
                <div key={route.technicianId} className='flex items-center space-x-2 text-xs'>
                  <div className='w-3 h-3 rounded-full' style={{ backgroundColor: color }}></div>
                  <span>{technician?.name || route.technicianId}</span>
                  <span className='text-gray-500'>({route.workOrderSequence.length})</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkOrderRoutingMap;
