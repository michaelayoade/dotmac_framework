'use client';

import { clsx } from 'clsx';
import dynamic from 'next/dynamic';
import React, { useEffect, useState, useCallback, useRef } from 'react';

import type { BaseMapProps, MapConfig, Coordinates } from '../types';

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(() => import('react-leaflet').then((mod) => mod.MapContainer), {
  ssr: false,
});

const TileLayer = dynamic(() => import('react-leaflet').then((mod) => mod.TileLayer), {
  ssr: false,
});

// Default configuration for maps
const defaultMapConfig: MapConfig = {
  defaultCenter: { latitude: 39.8283, longitude: -98.5795 }, // Center of US
  defaultZoom: 6,
  minZoom: 2,
  maxZoom: 18,
  theme: {
    primary: '#3B82F6',
    secondary: '#6B7280',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#06B6D4',
    background: '#F9FAFB',
    text: '#1F2937',
  },
  tileLayerUrl: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
};

interface BaseMapState {
  isClient: boolean;
  mapInstance: any;
  center: Coordinates;
  zoom: number;
  bounds?: [[number, number], [number, number]];
}

export function BaseMap({ className, config, onMapReady, children, ...props }: BaseMapProps) {
  const [state, setState] = useState<BaseMapState>({
    isClient: false,
    mapInstance: null,
    center: defaultMapConfig.defaultCenter,
    zoom: defaultMapConfig.defaultZoom,
  });

  const mapRef = useRef<any>(null);
  const finalConfig = { ...defaultMapConfig, ...config };

  useEffect(() => {
    setState((prev) => ({ ...prev, isClient: true }));
  }, []);

  const handleMapCreated = useCallback(
    (map: any) => {
      mapRef.current = map;
      setState((prev) => ({ ...prev, mapInstance: map }));

      if (onMapReady) {
        onMapReady(map);
      }

      // Add custom controls and event listeners
      map.on('zoomend', (e: any) => {
        setState((prev) => ({ ...prev, zoom: map.getZoom() }));
      });

      map.on('moveend', (e: any) => {
        const center = map.getCenter();
        setState((prev) => ({
          ...prev,
          center: { latitude: center.lat, longitude: center.lng },
        }));
      });
    },
    [onMapReady]
  );

  const mapClasses = clsx(
    'w-full h-full rounded-lg overflow-hidden',
    'border border-gray-200',
    'shadow-sm',
    className
  );

  if (!state.isClient) {
    return (
      <div className={mapClasses}>
        <div className='w-full h-full bg-gray-100 flex items-center justify-center'>
          <div className='text-gray-500'>Loading map...</div>
        </div>
      </div>
    );
  }

  return (
    <div className={mapClasses}>
      <MapContainer
        center={[finalConfig.defaultCenter.latitude, finalConfig.defaultCenter.longitude]}
        zoom={finalConfig.defaultZoom}
        minZoom={finalConfig.minZoom}
        maxZoom={finalConfig.maxZoom}
        scrollWheelZoom={true}
        zoomControl={true}
        attributionControl={true}
        className='w-full h-full'
        ref={(mapInstance) => {
          if (mapInstance && mapRef.current !== mapInstance) {
            handleMapCreated(mapInstance);
          }
        }}
        {...props}
      >
        <TileLayer
          url={finalConfig.tileLayerUrl!}
          attribution={finalConfig.attribution}
          maxZoom={finalConfig.maxZoom}
        />
        {children}
      </MapContainer>
    </div>
  );
}

// HOC for adding common map functionality
export function withMapFeatures<T extends object>(WrappedComponent: React.ComponentType<T>) {
  return function MapFeaturesWrapper(props: T) {
    const [mapInstance, setMapInstance] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);

    const handleMapReady = useCallback((map: any) => {
      setMapInstance(map);
      setIsLoading(false);
    }, []);

    return (
      <WrappedComponent
        {...props}
        mapInstance={mapInstance}
        isMapLoading={isLoading}
        onMapReady={handleMapReady}
      />
    );
  };
}

export default BaseMap;
