/**
 * Territory Map Component
 * Focused component for displaying territory map with markers
 */

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Territory } from '../hooks/useTerritoryData';

// Dynamic imports to avoid SSR issues
const MapContainer = dynamic(() => import('react-leaflet').then((mod) => mod.MapContainer), {
  ssr: false,
});
const TileLayer = dynamic(() => import('react-leaflet').then((mod) => mod.TileLayer), {
  ssr: false,
});
const Marker = dynamic(() => import('react-leaflet').then((mod) => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((mod) => mod.Popup), { ssr: false });
const Circle = dynamic(() => import('react-leaflet').then((mod) => mod.Circle), { ssr: false });

interface TerritoryMapProps {
  territories: Territory[];
  selectedTerritory: Territory | null;
  onTerritorySelect: (territory: Territory) => void;
  mapView: 'customers' | 'penetration' | 'competition' | 'opportunities';
  className?: string;
}

export function TerritoryMap({
  territories,
  selectedTerritory,
  onTerritorySelect,
  mapView,
  className = '',
}: TerritoryMapProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const getMarkerColor = (territory: Territory): string => {
    switch (mapView) {
      case 'customers':
        return territory.totalCustomers > 15000
          ? '#10B981'
          : territory.totalCustomers > 5000
            ? '#F59E0B'
            : '#EF4444';
      case 'penetration':
        return territory.marketPenetration > 40
          ? '#10B981'
          : territory.marketPenetration > 20
            ? '#F59E0B'
            : '#EF4444';
      case 'competition':
        return territory.competition === 'low'
          ? '#10B981'
          : territory.competition === 'medium'
            ? '#F59E0B'
            : '#EF4444';
      case 'opportunities':
        const totalOpportunities = Object.values(territory.opportunities).reduce(
          (a, b) => a + b,
          0
        );
        return totalOpportunities > 15 ? '#10B981' : totalOpportunities > 8 ? '#F59E0B' : '#EF4444';
      default:
        return '#6B7280';
    }
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  if (!isClient) {
    return (
      <div className={`bg-gray-100 rounded-lg flex items-center justify-center h-96 ${className}`}>
        <div className='text-gray-500'>Loading map...</div>
      </div>
    );
  }

  const defaultCenter: [number, number] = [40.7128, -74.006];
  const defaultZoom = 10;

  return (
    <div className={`rounded-lg overflow-hidden ${className}`}>
      <MapContainer
        center={selectedTerritory?.coordinates || defaultCenter}
        zoom={defaultZoom}
        style={{ height: '400px', width: '100%' }}
        className='z-0'
      >
        <TileLayer
          url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {territories.map((territory) => (
          <div key={territory.id}>
            <Marker
              position={territory.coordinates}
              eventHandlers={{
                click: () => onTerritorySelect(territory),
              }}
            >
              <Popup>
                <div className='p-2'>
                  <h3 className='font-semibold text-gray-900'>{territory.name}</h3>
                  <p className='text-gray-600 text-sm'>{territory.region} Region</p>

                  <div className='mt-2 space-y-1 text-sm'>
                    <div className='flex justify-between'>
                      <span>Customers:</span>
                      <span className='font-medium'>
                        {territory.totalCustomers.toLocaleString()}
                      </span>
                    </div>
                    <div className='flex justify-between'>
                      <span>Revenue:</span>
                      <span className='font-medium'>
                        {formatCurrency(territory.monthlyRevenue)}
                      </span>
                    </div>
                    <div className='flex justify-between'>
                      <span>Penetration:</span>
                      <span className='font-medium'>{territory.marketPenetration}%</span>
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>

            <Circle
              center={territory.coordinates}
              radius={territory.radius * 1000}
              pathOptions={{
                fillColor: getMarkerColor(territory),
                fillOpacity: 0.2,
                color: getMarkerColor(territory),
                weight: 2,
                opacity: selectedTerritory?.id === territory.id ? 1 : 0.5,
              }}
            />
          </div>
        ))}
      </MapContainer>
    </div>
  );
}
