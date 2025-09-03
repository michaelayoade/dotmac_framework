/**
 * Territory Content Component
 * Renders the main content area based on view mode
 */

import { motion } from 'framer-motion';
import type { Territory } from '../hooks/useTerritoryData';
import { TerritoryAnalytics } from './TerritoryAnalytics';
import { TerritoryList } from './TerritoryList';
import { TerritoryMap } from './TerritoryMap';

type ViewMode = 'map' | 'list' | 'analytics';
type MapView = 'customers' | 'penetration' | 'competition' | 'opportunities';

interface TerritoryContentProps {
  viewMode: ViewMode;
  mapView: MapView;
  onMapViewChange: (view: MapView) => void;
  territories: Territory[];
  selectedTerritory: Territory | null;
  onTerritorySelect: (territory: Territory) => void;
}

export function TerritoryContent({
  viewMode,
  mapView,
  onMapViewChange,
  territories,
  selectedTerritory,
  onTerritorySelect,
}: TerritoryContentProps) {
  return (
    <motion.div
      key={viewMode}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className='bg-white rounded-lg border border-gray-200'
    >
      {viewMode === 'map' && (
        <div className='p-6'>
          {/* Map View Controls */}
          <div className='flex items-center space-x-2 mb-4'>
            <span className='text-sm font-medium text-gray-700'>Show:</span>
            {(['customers', 'penetration', 'competition', 'opportunities'] as MapView[]).map(
              (view) => (
                <button
                  key={view}
                  onClick={() => onMapViewChange(view)}
                  className={`px-3 py-1 text-sm rounded-full capitalize ${
                    mapView === view
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {view.replace('_', ' ')}
                </button>
              )
            )}
          </div>

          <TerritoryMap
            territories={territories}
            selectedTerritory={selectedTerritory}
            onTerritorySelect={onTerritorySelect}
            mapView={mapView}
          />
        </div>
      )}

      {viewMode === 'list' && (
        <div className='p-6'>
          <TerritoryList
            territories={territories}
            selectedTerritory={selectedTerritory}
            onTerritorySelect={onTerritorySelect}
          />
        </div>
      )}

      {viewMode === 'analytics' && (
        <div className='p-6'>
          <TerritoryAnalytics territories={territories} selectedTerritory={selectedTerritory} />
        </div>
      )}
    </motion.div>
  );
}
