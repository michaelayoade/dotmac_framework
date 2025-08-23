'use client';

import { clsx } from 'clsx';
import dynamic from 'next/dynamic';
import React, { useEffect, useState, useCallback, useMemo } from 'react';

import type { Customer, HeatmapPoint, Coordinates, BaseMapProps, MarketAnalysis } from '../types';

import { BaseMap } from './BaseMap';

// Dynamically import Leaflet components
const Circle = dynamic(() => import('react-leaflet').then((mod) => mod.Circle), { ssr: false });
const Polygon = dynamic(() => import('react-leaflet').then((mod) => mod.Polygon), { ssr: false });
const LayerGroup = dynamic(() => import('react-leaflet').then((mod) => mod.LayerGroup), {
  ssr: false,
});

interface CustomerDensityHeatmapProps extends Omit<BaseMapProps, 'children'> {
  customers: Customer[];
  marketAnalysis?: MarketAnalysis[];
  onAreaSelect?: (area: { bounds: Coordinates[]; customers: Customer[]; metrics: any }) => void;
  heatmapType?: 'density' | 'revenue' | 'churn' | 'satisfaction';
  gridSize?: number; // Size of grid cells in degrees
  showCompetitorData?: boolean;
  demographicOverlay?: boolean;
  className?: string;
}

interface GridCell {
  bounds: Coordinates[];
  center: Coordinates;
  customers: Customer[];
  density: number;
  revenue: number;
  avgSatisfaction: number;
  churnRate: number;
  serviceTypes: Record<string, number>;
  demographics: {
    residential: number;
    business: number;
    enterprise: number;
  };
}

interface HeatmapLayer {
  density: boolean;
  revenue: boolean;
  satisfaction: boolean;
  churn: boolean;
  competitors: boolean;
  demographics: boolean;
}

export function CustomerDensityHeatmap({
  customers,
  marketAnalysis = [],
  onAreaSelect,
  heatmapType = 'density',
  gridSize = 0.01, // ~1km at mid-latitudes
  showCompetitorData = false,
  demographicOverlay = false,
  className,
  ...mapProps
}: CustomerDensityHeatmapProps) {
  const [selectedCell, setSelectedCell] = useState<GridCell | null>(null);
  const [layerVisibility, setLayerVisibility] = useState<HeatmapLayer>({
    density: true,
    revenue: false,
    satisfaction: false,
    churn: false,
    competitors: showCompetitorData,
    demographics: demographicOverlay,
  });
  const [currentHeatmapType, setCurrentHeatmapType] = useState<string>(heatmapType);

  // Calculate grid bounds based on customer locations
  const gridBounds = useMemo(() => {
    if (customers.length === 0) return null;

    const lats = customers.map((c) => c.coordinates.latitude);
    const lngs = customers.map((c) => c.coordinates.longitude);

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    // Add padding
    const padding = gridSize * 2;

    return {
      minLat: minLat - padding,
      maxLat: maxLat + padding,
      minLng: minLng - padding,
      maxLng: maxLng + padding,
    };
  }, [customers, gridSize]);

  // Generate grid cells with customer data
  const gridCells = useMemo(() => {
    if (!gridBounds || customers.length === 0) return [];

    const cells: GridCell[] = [];

    for (let lat = gridBounds.minLat; lat < gridBounds.maxLat; lat += gridSize) {
      for (let lng = gridBounds.minLng; lng < gridBounds.maxLng; lng += gridSize) {
        const bounds: Coordinates[] = [
          { latitude: lat, longitude: lng },
          { latitude: lat, longitude: lng + gridSize },
          { latitude: lat + gridSize, longitude: lng + gridSize },
          { latitude: lat + gridSize, longitude: lng },
        ];

        const center: Coordinates = {
          latitude: lat + gridSize / 2,
          longitude: lng + gridSize / 2,
        };

        // Find customers in this cell
        const cellCustomers = customers.filter(
          (customer) =>
            customer.coordinates.latitude >= lat &&
            customer.coordinates.latitude < lat + gridSize &&
            customer.coordinates.longitude >= lng &&
            customer.coordinates.longitude < lng + gridSize
        );

        if (cellCustomers.length === 0) continue;

        // Calculate metrics for this cell
        const density = cellCustomers.length;
        const revenue = cellCustomers
          .filter((c) => c.status === 'active')
          .reduce((sum, c) => sum + c.monthlyRevenue, 0);

        const satisfactionScores = cellCustomers
          .filter((c) => c.satisfaction !== undefined)
          .map((c) => c.satisfaction!);
        const avgSatisfaction =
          satisfactionScores.length > 0
            ? satisfactionScores.reduce((sum, s) => sum + s, 0) / satisfactionScores.length
            : 0;

        // Simplified churn calculation (cancelled customers in last 30 days)
        const recentCancellations = cellCustomers.filter(
          (c) =>
            c.status === 'cancelled' &&
            Date.now() - c.installDate.getTime() < 30 * 24 * 60 * 60 * 1000
        ).length;
        const churnRate = (recentCancellations / cellCustomers.length) * 100;

        // Service type breakdown
        const serviceTypes = cellCustomers.reduce(
          (acc, c) => {
            acc[c.serviceType] = (acc[c.serviceType] || 0) + 1;
            return acc;
          },
          {} as Record<string, number>
        );

        // Demographics breakdown
        const demographics = {
          residential: serviceTypes.residential || 0,
          business: serviceTypes.business || 0,
          enterprise: serviceTypes.enterprise || 0,
        };

        cells.push({
          bounds,
          center,
          customers: cellCustomers,
          density,
          revenue,
          avgSatisfaction,
          churnRate,
          serviceTypes,
          demographics,
        });
      }
    }

    return cells;
  }, [gridBounds, customers, gridSize]);

  // Calculate color intensity for heatmap
  const getHeatmapColor = useCallback(
    (cell: GridCell) => {
      let value: number;
      let maxValue: number;

      switch (currentHeatmapType) {
        case 'density':
          value = cell.density;
          maxValue = Math.max(...gridCells.map((c) => c.density));
          break;
        case 'revenue':
          value = cell.revenue;
          maxValue = Math.max(...gridCells.map((c) => c.revenue));
          break;
        case 'satisfaction':
          value = cell.avgSatisfaction;
          maxValue = 10; // Satisfaction scale is 1-10
          break;
        case 'churn':
          value = cell.churnRate;
          maxValue = Math.max(...gridCells.map((c) => c.churnRate));
          break;
        default:
          value = cell.density;
          maxValue = Math.max(...gridCells.map((c) => c.density));
      }

      const intensity = maxValue > 0 ? value / maxValue : 0;

      // Color gradient based on heatmap type
      const getColor = (intensity: number) => {
        switch (currentHeatmapType) {
          case 'density':
            return `rgba(59, 130, 246, ${intensity * 0.7})`; // Blue gradient
          case 'revenue':
            return `rgba(16, 185, 129, ${intensity * 0.7})`; // Green gradient
          case 'satisfaction':
            // Invert for satisfaction (high satisfaction = green, low = red)
            const satisfactionIntensity = value / 10;
            return satisfactionIntensity > 0.7
              ? `rgba(16, 185, 129, 0.7)`
              : satisfactionIntensity > 0.4
                ? `rgba(245, 158, 11, 0.7)`
                : `rgba(239, 68, 68, 0.7)`;
          case 'churn':
            return `rgba(239, 68, 68, ${intensity * 0.7})`; // Red gradient
          default:
            return `rgba(59, 130, 246, ${intensity * 0.7})`;
        }
      };

      return {
        fillColor: getColor(intensity),
        color: getColor(intensity),
        fillOpacity: Math.max(intensity, 0.1),
        weight: 1,
      };
    },
    [currentHeatmapType, gridCells]
  );

  // Market penetration and opportunity analysis
  const marketMetrics = useMemo(() => {
    const totalCells = gridCells.length;
    const activeCells = gridCells.filter((cell) => cell.density > 0).length;
    const highValueCells = gridCells.filter((cell) => cell.revenue > 5000).length;
    const lowSatisfactionCells = gridCells.filter((cell) => cell.avgSatisfaction < 7).length;
    const highChurnCells = gridCells.filter((cell) => cell.churnRate > 10).length;

    const totalRevenue = gridCells.reduce((sum, cell) => sum + cell.revenue, 0);
    const avgDensity = gridCells.reduce((sum, cell) => sum + cell.density, 0) / totalCells;
    const avgSatisfaction = gridCells
      .filter((cell) => cell.avgSatisfaction > 0)
      .reduce((sum, cell, _, arr) => sum + cell.avgSatisfaction / arr.length, 0);

    return {
      totalCells,
      activeCells,
      penetrationRate: (activeCells / totalCells) * 100,
      highValueCells,
      lowSatisfactionCells,
      highChurnCells,
      totalRevenue,
      avgDensity,
      avgSatisfaction,
    };
  }, [gridCells]);

  const handleCellClick = useCallback(
    (cell: GridCell) => {
      setSelectedCell(cell);
      if (onAreaSelect) {
        onAreaSelect({
          bounds: cell.bounds,
          customers: cell.customers,
          metrics: {
            density: cell.density,
            revenue: cell.revenue,
            avgSatisfaction: cell.avgSatisfaction,
            churnRate: cell.churnRate,
            serviceTypes: cell.serviceTypes,
            demographics: cell.demographics,
          },
        });
      }
    },
    [onAreaSelect]
  );

  const toggleLayer = useCallback((layer: keyof HeatmapLayer) => {
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
        {/* Density Heatmap Grid */}
        {layerVisibility.density && (
          <LayerGroup>
            {gridCells.map((cell, index) => {
              const style = getHeatmapColor(cell);
              const coordinates: [number, number][] = cell.bounds.map((coord) => [
                coord.latitude,
                coord.longitude,
              ]);

              return (
                <Polygon
                  key={`cell-${index}`}
                  positions={coordinates}
                  pathOptions={style}
                  eventHandlers={{
                    click: () => handleCellClick(cell),
                  }}
                />
              );
            })}
          </LayerGroup>
        )}

        {/* Customer Points (for reference) */}
        <LayerGroup>
          {customers
            .filter((c) => c.status === 'active')
            .slice(0, 1000) // Limit for performance
            .map((customer) => (
              <Circle
                key={customer.id}
                center={[customer.coordinates.latitude, customer.coordinates.longitude]}
                radius={20}
                pathOptions={{
                  color:
                    customer.serviceType === 'enterprise'
                      ? '#8B5CF6'
                      : customer.serviceType === 'business'
                        ? '#10B981'
                        : '#3B82F6',
                  fillOpacity: 0.8,
                  weight: 1,
                }}
              />
            ))}
        </LayerGroup>

        {/* Competitor Locations */}
        {layerVisibility.competitors && marketAnalysis.length > 0 && (
          <LayerGroup>
            {marketAnalysis.flatMap((analysis) =>
              analysis.competitorData.map((competitor, index) => (
                <Circle
                  key={`competitor-${analysis.territoryId}-${index}`}
                  center={[competitor.coordinates.latitude, competitor.coordinates.longitude]}
                  radius={200}
                  pathOptions={{
                    color: '#EF4444',
                    fillColor: '#EF4444',
                    fillOpacity: 0.3,
                    weight: 2,
                    dashArray: '5, 5',
                  }}
                />
              ))
            )}
          </LayerGroup>
        )}
      </BaseMap>

      {/* Heatmap Type Selector */}
      <div className='absolute top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Heatmap Type</h4>
        <div className='space-y-2'>
          {[
            { key: 'density', label: 'Customer Density', color: 'bg-blue-500' },
            { key: 'revenue', label: 'Revenue', color: 'bg-green-500' },
            { key: 'satisfaction', label: 'Satisfaction', color: 'bg-yellow-500' },
            { key: 'churn', label: 'Churn Rate', color: 'bg-red-500' },
          ].map((type) => (
            <button
              key={type.key}
              onClick={() => setCurrentHeatmapType(type.key)}
              className={clsx(
                'w-full flex items-center space-x-2 px-3 py-2 text-sm rounded transition-colors',
                currentHeatmapType === type.key
                  ? 'bg-gray-100 text-gray-900 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              )}
            >
              <div className={clsx('w-3 h-3 rounded-full', type.color)}></div>
              <span>{type.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Layer Controls */}
      <div className='absolute top-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Map Layers</h4>
        <div className='space-y-2 text-sm'>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.density}
              onChange={() => toggleLayer('density')}
              className='rounded border-gray-300'
            />
            <span>Heatmap Grid</span>
          </label>
          <label className='flex items-center space-x-2 cursor-pointer'>
            <input
              type='checkbox'
              checked={layerVisibility.competitors}
              onChange={() => toggleLayer('competitors')}
              className='rounded border-gray-300'
            />
            <span>Competitors</span>
          </label>
        </div>
      </div>

      {/* Market Metrics Dashboard */}
      <div className='absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-sm font-semibold text-gray-900 mb-3'>Market Analysis</h4>

        <div className='grid grid-cols-2 gap-3 mb-3'>
          <div className='text-center'>
            <div className='text-lg font-bold text-blue-600'>
              {marketMetrics.penetrationRate.toFixed(1)}%
            </div>
            <div className='text-xs text-gray-600'>Market Penetration</div>
          </div>
          <div className='text-center'>
            <div className='text-lg font-bold text-green-600'>
              {formatCurrency(marketMetrics.totalRevenue)}
            </div>
            <div className='text-xs text-gray-600'>Total Revenue</div>
          </div>
        </div>

        <div className='space-y-1 text-xs'>
          <div className='flex justify-between'>
            <span>Active Areas:</span>
            <span className='font-semibold'>
              {marketMetrics.activeCells} / {marketMetrics.totalCells}
            </span>
          </div>
          <div className='flex justify-between'>
            <span>High Value Areas:</span>
            <span className='font-semibold text-green-600'>{marketMetrics.highValueCells}</span>
          </div>
          <div className='flex justify-between'>
            <span>Satisfaction Issues:</span>
            <span className='font-semibold text-yellow-600'>
              {marketMetrics.lowSatisfactionCells}
            </span>
          </div>
          <div className='flex justify-between'>
            <span>High Churn Areas:</span>
            <span className='font-semibold text-red-600'>{marketMetrics.highChurnCells}</span>
          </div>
          <div className='flex justify-between'>
            <span>Avg Density:</span>
            <span className='font-semibold'>{marketMetrics.avgDensity.toFixed(1)}</span>
          </div>
          <div className='flex justify-between'>
            <span>Avg Satisfaction:</span>
            <span className='font-semibold'>{marketMetrics.avgSatisfaction.toFixed(1)}/10</span>
          </div>
        </div>
      </div>

      {/* Selected Cell Details */}
      {selectedCell && (
        <div className='absolute bottom-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3 max-w-sm'>
          <div className='flex items-center justify-between mb-2'>
            <h4 className='text-sm font-semibold text-gray-900'>Area Details</h4>
            <button
              onClick={() => setSelectedCell(null)}
              className='text-gray-400 hover:text-gray-600'
            >
              ×
            </button>
          </div>

          <div className='space-y-2 text-xs'>
            <div className='flex justify-between'>
              <span>Customers:</span>
              <span className='font-semibold'>{selectedCell.density}</span>
            </div>
            <div className='flex justify-between'>
              <span>Revenue:</span>
              <span className='font-semibold text-green-600'>
                {formatCurrency(selectedCell.revenue)}
              </span>
            </div>
            <div className='flex justify-between'>
              <span>Avg Satisfaction:</span>
              <span
                className={clsx(
                  'font-semibold',
                  selectedCell.avgSatisfaction > 7
                    ? 'text-green-600'
                    : selectedCell.avgSatisfaction > 4
                      ? 'text-yellow-600'
                      : 'text-red-600'
                )}
              >
                {selectedCell.avgSatisfaction.toFixed(1)}/10
              </span>
            </div>
            <div className='flex justify-between'>
              <span>Churn Rate:</span>
              <span
                className={clsx(
                  'font-semibold',
                  selectedCell.churnRate < 5
                    ? 'text-green-600'
                    : selectedCell.churnRate < 15
                      ? 'text-yellow-600'
                      : 'text-red-600'
                )}
              >
                {selectedCell.churnRate.toFixed(1)}%
              </span>
            </div>
          </div>

          <div className='mt-3 pt-2 border-t border-gray-200'>
            <div className='text-xs font-semibold text-gray-900 mb-1'>Service Types:</div>
            <div className='space-y-1 text-xs'>
              <div className='flex justify-between'>
                <span>Residential:</span>
                <span>{selectedCell.demographics.residential}</span>
              </div>
              <div className='flex justify-between'>
                <span>Business:</span>
                <span>{selectedCell.demographics.business}</span>
              </div>
              <div className='flex justify-between'>
                <span>Enterprise:</span>
                <span>{selectedCell.demographics.enterprise}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className='absolute top-1/2 right-4 transform -translate-y-1/2 bg-white rounded-lg shadow-lg border border-gray-200 p-3'>
        <h4 className='text-xs font-semibold text-gray-900 mb-2'>Intensity Scale</h4>
        <div className='flex flex-col space-y-1'>
          <div className='flex items-center space-x-2'>
            <div
              className='w-4 h-2 bg-gradient-to-r from-transparent to-current opacity-70'
              style={{
                color:
                  currentHeatmapType === 'density'
                    ? '#3B82F6'
                    : currentHeatmapType === 'revenue'
                      ? '#10B981'
                      : currentHeatmapType === 'satisfaction'
                        ? '#F59E0B'
                        : '#EF4444',
              }}
            ></div>
            <span className='text-xs'>High</span>
          </div>
          <div className='flex items-center space-x-2'>
            <div className='w-4 h-2 bg-gray-300 opacity-50'></div>
            <span className='text-xs'>Low</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CustomerDensityHeatmap;
