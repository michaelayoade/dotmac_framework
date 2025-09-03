/**
 * Territory Management Component
 * Refactored using composition pattern for better maintainability
 */

'use client';

import { useState } from 'react';
import { TerritoryContent } from './components/TerritoryContent';
import { TerritoryDetailsPanel } from './components/TerritoryDetailsPanel';
import { TerritoryHeader } from './components/TerritoryHeader';
// Import focused sub-components and hooks
import { type Territory, useTerritoryData } from './hooks/useTerritoryData';

type ViewMode = 'map' | 'list' | 'analytics';
type MapView = 'customers' | 'penetration' | 'competition' | 'opportunities';

export function TerritoryManagement() {
  // Use focused data hook
  const {
    territories,
    filteredTerritories,
    isLoading,
    error,
    filters,
    updateFilters,
    refreshData,
  } = useTerritoryData();

  // Local UI state
  const [selectedTerritory, setSelectedTerritory] = useState<Territory | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('map');
  const [mapView, setMapView] = useState<MapView>('customers');
  const [showFilters, setShowFilters] = useState(false);

  if (isLoading) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='text-center py-8'>
        <div className='text-red-600 mb-4'>{error}</div>
        <button
          onClick={refreshData}
          className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      <TerritoryHeader
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        filters={filters}
        onFiltersChange={updateFilters}
        territories={territories}
        showFilters={showFilters}
        onToggleFilters={() => setShowFilters(!showFilters)}
      />

      <TerritoryContent
        viewMode={viewMode}
        mapView={mapView}
        onMapViewChange={setMapView}
        territories={filteredTerritories}
        selectedTerritory={selectedTerritory}
        onTerritorySelect={setSelectedTerritory}
      />

      {selectedTerritory && (
        <TerritoryDetailsPanel
          territory={selectedTerritory}
          onClose={() => setSelectedTerritory(null)}
        />
      )}
    </div>
  );
}
