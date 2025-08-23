'use client';

import { clsx } from 'clsx';
import dynamic from 'next/dynamic';
import React, { useEffect, useState, useCallback, useMemo } from 'react';

import type { ServiceArea, Customer, Coordinates, BaseMapProps } from '../types';

import { BaseMap } from './BaseMap';

// Dynamically import Leaflet components
const Marker = dynamic(() => import('react-leaflet').then((mod) => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((mod) => mod.Popup), { ssr: false });
const Polygon = dynamic(() => import('react-leaflet').then((mod) => mod.Polygon), { ssr: false });
const Circle = dynamic(() => import('react-leaflet').then((mod) => mod.Circle), { ssr: false });
const LayerGroup = dynamic(() => import('react-leaflet').then((mod) => mod.LayerGroup), {
  ssr: false,
});

interface ServiceCoverageMapProps extends Omit<BaseMapProps, 'children'> {
  serviceAreas: ServiceArea[];
  customers?: Customer[];
  onServiceAreaSelect?: (area: ServiceArea) => void;
  onCustomerSelect?: (customer: Customer) => void;
  showCustomers?: boolean;
  showCoverageHeatmap?: boolean;
  filterServiceType?: 'all' | 'fiber' | 'cable' | 'dsl' | 'wireless';
  className?: string;
}

interface LayerVisibility {
  serviceAreas: boolean;
  customers: boolean;
  heatmap: boolean;
  plannedAreas: boolean;
}

export function ServiceCoverageMap({
  serviceAreas,
  customers = [],
  onServiceAreaSelect,
  onCustomerSelect,
  showCustomers = true,
  showCoverageHeatmap = false,
  filterServiceType = 'all',
  className,
  ...mapProps
}: ServiceCoverageMapProps) {
  const [selectedArea, setSelectedArea] = useState<ServiceArea | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [layerVisibility, setLayerVisibility] = useState<LayerVisibility>({
    serviceAreas: true,
    customers: showCustomers,
    heatmap: showCoverageHeatmap,
    plannedAreas: true,
  });

  // Filter service areas based on selected service type
  const filteredServiceAreas = useMemo(() => {
    if (filterServiceType === 'all') return serviceAreas;
    return serviceAreas.filter((area) => area.type === filterServiceType);
  }, [serviceAreas, filterServiceType]);

  // Group service areas by service level
  const serviceAreaGroups = useMemo(() => {
    const groups = {
      full: filteredServiceAreas.filter((area) => area.serviceLevel === 'full'),
      partial: filteredServiceAreas.filter((area) => area.serviceLevel === 'partial'),
      planned: filteredServiceAreas.filter((area) => area.serviceLevel === 'planned'),
    };
    return groups;
  }, [filteredServiceAreas]);

  // Calculate coverage statistics
  const coverageStats = useMemo(() => {
    const totalHouseholds = serviceAreas.reduce((sum, area) => sum + area.households, 0);
    const coveredHouseholds = serviceAreas
      .filter((area) => area.serviceLevel !== 'planned')
      .reduce((sum, area) => sum + Math.round(area.households * (area.coverage / 100)), 0);

    const activeCustomers = customers.filter((c) => c.status === 'active').length;
    const totalRevenue = customers
      .filter((c) => c.status === 'active')
      .reduce((sum, c) => sum + c.monthlyRevenue, 0);

    return {
      totalHouseholds,
      coveredHouseholds,
      coveragePercentage: (coveredHouseholds / totalHouseholds) * 100,
      activeCustomers,
      penetrationRate: (activeCustomers / coveredHouseholds) * 100,
      totalRevenue,
    };
  }, [serviceAreas, customers]);

  const getServiceAreaColor = useCallback((area: ServiceArea) => {
    const colors = {
      fiber: '#10B981',
      cable: '#3B82F6',
      dsl: '#F59E0B',
      wireless: '#8B5CF6',
    };

    const opacity = {
      full: 0.6,
      partial: 0.4,
      planned: 0.2,
    };

    return {
      color: colors[area.type],
      fillOpacity: opacity[area.serviceLevel],
    };
  }, []);

  const getCustomerMarkerColor = useCallback((customer: Customer) => {
    const colors = {
      residential: '#3B82F6',
      business: '#10B981',
      enterprise: '#8B5CF6',
    };

    const status = {
      active: 1.0,
      suspended: 0.5,
      cancelled: 0.3,
    };

    return {
      color: colors[customer.serviceType],
      opacity: status[customer.status],
    };
  }, []);

  const handleServiceAreaClick = useCallback(
    (area: ServiceArea) => {
      setSelectedArea(area);
      if (onServiceAreaSelect) {
        onServiceAreaSelect(area);
      }
    },
    [onServiceAreaSelect]
  );

  const handleCustomerClick = useCallback(
    (customer: Customer) => {
      setSelectedCustomer(customer);
      if (onCustomerSelect) {
        onCustomerSelect(customer);
      }
    },
    [onCustomerSelect]
  );

  const toggleLayer = useCallback((layer: keyof LayerVisibility) => {
    setLayerVisibility((prev) => ({
      ...prev,
      [layer]: !prev[layer],
    }));
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className={clsx('relative w-full h-full', className)}>
      <BaseMap {...mapProps} className='w-full h-full'>
        {/* Service Areas */}
        {layerVisibility.serviceAreas && (
          <LayerGroup>
            {serviceAreaGroups.full.map((area) => {
              const style = getServiceAreaColor(area);
              const coordinates: [number, number][] = area.polygon.map((coord) => [
                coord.latitude,
                coord.longitude,
              ]);

              return (
                <Polygon
                  key={`full-${area.id}`}
                  positions={coordinates}
                  pathOptions={{
                    color: style.color,
                    fillColor: style.color,
                    fillOpacity: style.fillOpacity,
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => handleServiceAreaClick(area),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-48'>
                      <h4 className='font-bold text-gray-900 mb-2'>{area.name}</h4>
                      <div className='text-sm text-gray-600 space-y-1'>
                        <div>
                          <strong>Type:</strong> {area.type.toUpperCase()}
                        </div>
                        <div>
                          <strong>Service Level:</strong>{' '}
                          <span className='capitalize'>{area.serviceLevel}</span>
                        </div>
                        <div>
                          <strong>Max Speed:</strong> {area.maxSpeed} Mbps
                        </div>
                        <div>
                          <strong>Coverage:</strong> {area.coverage}%
                        </div>
                        <div>
                          <strong>Population:</strong> {area.population.toLocaleString()}
                        </div>
                        <div>
                          <strong>Households:</strong> {area.households.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </LayerGroup>
        )}

        {/* Partial Coverage Areas */}
        {layerVisibility.serviceAreas && (
          <LayerGroup>
            {serviceAreaGroups.partial.map((area) => {
              const style = getServiceAreaColor(area);
              const coordinates: [number, number][] = area.polygon.map((coord) => [
                coord.latitude,
                coord.longitude,
              ]);

              return (
                <Polygon
                  key={`partial-${area.id}`}
                  positions={coordinates}
                  pathOptions={{
                    color: style.color,
                    fillColor: style.color,
                    fillOpacity: style.fillOpacity,
                    weight: 2,
                    dashArray: '5, 5',
                  }}
                  eventHandlers={{
                    click: () => handleServiceAreaClick(area),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-48'>
                      <h4 className='font-bold text-gray-900 mb-2'>{area.name}</h4>
                      <div className='text-sm text-gray-600 space-y-1'>
                        <div>
                          <strong>Type:</strong> {area.type.toUpperCase()}
                        </div>
                        <div>
                          <strong>Service Level:</strong>{' '}
                          <span className='capitalize'>{area.serviceLevel}</span>
                        </div>
                        <div>
                          <strong>Max Speed:</strong> {area.maxSpeed} Mbps
                        </div>
                        <div>
                          <strong>Coverage:</strong> {area.coverage}% (Partial)
                        </div>
                        <div>
                          <strong>Population:</strong> {area.population.toLocaleString()}
                        </div>
                        <div>
                          <strong>Households:</strong> {area.households.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </LayerGroup>
        )}

        {/* Planned Areas */}
        {layerVisibility.plannedAreas && (
          <LayerGroup>
            {serviceAreaGroups.planned.map((area) => {
              const style = getServiceAreaColor(area);
              const coordinates: [number, number][] = area.polygon.map((coord) => [
                coord.latitude,
                coord.longitude,
              ]);

              return (
                <Polygon
                  key={`planned-${area.id}`}
                  positions={coordinates}
                  pathOptions={{
                    color: style.color,
                    fillColor: style.color,
                    fillOpacity: style.fillOpacity,
                    weight: 1,
                    dashArray: '10, 10',
                  }}
                  eventHandlers={{
                    click: () => handleServiceAreaClick(area),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-48'>
                      <h4 className='font-bold text-gray-900 mb-2'>{area.name}</h4>
                      <div className='text-sm text-gray-600 space-y-1'>
                        <div>
                          <strong>Type:</strong> {area.type.toUpperCase()}
                        </div>
                        <div>
                          <strong>Service Level:</strong>{' '}
                          <span className='capitalize text-yellow-600'>{area.serviceLevel}</span>
                        </div>
                        <div>
                          <strong>Planned Speed:</strong> {area.maxSpeed} Mbps
                        </div>
                        <div>
                          <strong>Target Population:</strong> {area.population.toLocaleString()}
                        </div>
                        <div>
                          <strong>Target Households:</strong> {area.households.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </LayerGroup>
        )}

        {/* Customers */}
        {layerVisibility.customers && customers.length > 0 && (
          <LayerGroup>
            {customers.map((customer) => {
              const style = getCustomerMarkerColor(customer);

              return (
                <Circle
                  key={customer.id}
                  center={[customer.coordinates.latitude, customer.coordinates.longitude]}
                  radius={50}
                  pathOptions={{
                    color: style.color,
                    fillColor: style.color,
                    fillOpacity: style.opacity,
                    weight: 1,
                  }}
                  eventHandlers={{
                    click: () => handleCustomerClick(customer),
                  }}
                >
                  <Popup>
                    <div className='p-3 min-w-48'>
                      <h4 className='font-bold text-gray-900 mb-2'>{customer.name}</h4>
                      <div className='text-sm text-gray-600 space-y-1'>
                        <div>
                          <strong>Type:</strong>{' '}
                          <span className='capitalize'>{customer.serviceType}</span>
                        </div>
                        <div>
                          <strong>Plan:</strong> {customer.plan}
                        </div>
                        <div>
                          <strong>Speed:</strong> {customer.speed} Mbps
                        </div>
                        <div>
                          <strong>Revenue:</strong> {formatCurrency(customer.monthlyRevenue)}/month
                        </div>
                        <div>
                          <strong>Status:</strong>{' '}
                          <span className='capitalize'>{customer.status}</span>
                        </div>
                        <div>
                          <strong>Install Date:</strong> {customer.installDate.toLocaleDateString()}
                        </div>
                        {customer.satisfaction && (
                          <div>
                            <strong>Satisfaction:</strong> {customer.satisfaction}/10
                          </div>
                        )}
                      </div>
                    </div>
                  </Popup>
                </Circle>
              );
            })}
          </LayerGroup>
        )}
      </BaseMap>

      {/* Layer Controls */}
      <div className='absolute top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Map Layers</h4>
        <div className='space-y-2 text-sm'>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.serviceAreas}
              onChange={() => toggleLayer('serviceAreas')}
              className='rounded border-gray-300'
            />
            <span>Service Areas</span>
          </label>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.plannedAreas}
              onChange={() => toggleLayer('plannedAreas')}
              className='rounded border-gray-300'
            />
            <span>Planned Areas</span>
          </label>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.customers}
              onChange={() => toggleLayer('customers')}
              className='rounded border-gray-300'
            />
            <span>Customers</span>
          </label>
        </div>
      </div>

      {/* Coverage Statistics */}
      <div className='absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-2'>Coverage Stats</h4>
        <div className='text-xs text-gray-600 space-y-1'>
          <div>
            <strong>Total Households:</strong> {coverageStats.totalHouseholds.toLocaleString()}
          </div>
          <div>
            <strong>Covered:</strong> {coverageStats.coveredHouseholds.toLocaleString()} (
            {coverageStats.coveragePercentage.toFixed(1)}%)
          </div>
          <div>
            <strong>Active Customers:</strong> {coverageStats.activeCustomers.toLocaleString()}
          </div>
          <div>
            <strong>Penetration:</strong> {coverageStats.penetrationRate.toFixed(1)}%
          </div>
          <div>
            <strong>Monthly Revenue:</strong> {formatCurrency(coverageStats.totalRevenue)}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className='absolute bottom-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-xs font-semibold text-gray-900 mb-2'>Service Types</h4>
        <div className='grid grid-cols-2 gap-2 text-xs'>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-green-500'></div>
            <span>Fiber</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-blue-500'></div>
            <span>Cable</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-yellow-500'></div>
            <span>DSL</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-3 h-3 rounded-full bg-purple-500'></div>
            <span>Wireless</span>
          </div>
        </div>
        <div className='mt-2 pt-2 border-t border-gray-200 text-xs'>
          <div>Solid = Full Coverage</div>
          <div>Dashed = Partial Coverage</div>
          <div>Dotted = Planned</div>
        </div>
      </div>
    </div>
  );
}

export default ServiceCoverageMap;
