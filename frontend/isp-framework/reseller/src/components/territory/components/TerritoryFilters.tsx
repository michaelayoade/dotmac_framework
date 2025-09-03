/**
 * Territory Filters Component
 * Advanced filtering controls for territory data
 */

import { motion } from 'framer-motion';
import { Building2, DollarSign, RotateCcw, Target, TrendingUp, Users, Zap } from 'lucide-react';
import { useMemo } from 'react';
import type {
  Territory,
  TerritoryFilters as TerritoryFiltersType,
} from '../hooks/useTerritoryData';

interface TerritoryFiltersProps {
  filters: TerritoryFiltersType;
  onFiltersChange: (updates: Partial<TerritoryFiltersType>) => void;
  territories: Territory[];
}

export function TerritoryFilters({ filters, onFiltersChange, territories }: TerritoryFiltersProps) {
  // Get unique regions from territories for filter options
  const availableRegions = useMemo(() => {
    const regions = territories.map((t) => t.region);
    return [...new Set(regions)].sort();
  }, [territories]);

  // Reset filters
  const resetFilters = () => {
    onFiltersChange({
      searchTerm: '',
      sortBy: 'revenue',
      region: undefined,
      competitionLevel: undefined,
    });
  };

  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.searchTerm) count++;
    if (filters.region) count++;
    if (filters.competitionLevel) count++;
    return count;
  }, [filters]);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className='mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200'
    >
      <div className='flex items-center justify-between mb-4'>
        <h3 className='text-lg font-semibold text-gray-900 flex items-center'>
          <Target className='w-5 h-5 mr-2 text-blue-600' />
          Advanced Filters
          {activeFilterCount > 0 && (
            <span className='ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full'>
              {activeFilterCount} active
            </span>
          )}
        </h3>

        {activeFilterCount > 0 && (
          <button
            onClick={resetFilters}
            className='flex items-center space-x-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors'
          >
            <RotateCcw className='w-4 h-4' />
            <span>Reset</span>
          </button>
        )}
      </div>

      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
        {/* Region Filter */}
        <div className='space-y-2'>
          <label className='flex items-center text-sm font-medium text-gray-700'>
            <Building2 className='w-4 h-4 mr-2 text-gray-500' />
            Region
          </label>
          <select
            value={filters.region || ''}
            onChange={(e) => onFiltersChange({ region: e.target.value || undefined })}
            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white'
          >
            <option value=''>All Regions</option>
            {availableRegions.map((region) => (
              <option key={region} value={region}>
                {region}
              </option>
            ))}
          </select>
        </div>

        {/* Competition Level Filter */}
        <div className='space-y-2'>
          <label className='flex items-center text-sm font-medium text-gray-700'>
            <Zap className='w-4 h-4 mr-2 text-gray-500' />
            Competition Level
          </label>
          <select
            value={filters.competitionLevel || ''}
            onChange={(e) =>
              onFiltersChange({
                competitionLevel: (e.target.value as any) || undefined,
              })
            }
            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white'
          >
            <option value=''>All Levels</option>
            <option value='low'>Low Competition</option>
            <option value='medium'>Medium Competition</option>
            <option value='high'>High Competition</option>
          </select>
        </div>

        {/* Sort By Filter */}
        <div className='space-y-2'>
          <label className='flex items-center text-sm font-medium text-gray-700'>
            <TrendingUp className='w-4 h-4 mr-2 text-gray-500' />
            Sort By
          </label>
          <select
            value={filters.sortBy}
            onChange={(e) => onFiltersChange({ sortBy: e.target.value as any })}
            className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white'
          >
            <option value='name'>Territory Name</option>
            <option value='revenue'>Monthly Revenue</option>
            <option value='growth'>Growth Rate</option>
            <option value='penetration'>Market Penetration</option>
          </select>
        </div>

        {/* Quick Filter Stats */}
        <div className='space-y-2'>
          <label className='flex items-center text-sm font-medium text-gray-700'>
            <Users className='w-4 h-4 mr-2 text-gray-500' />
            Quick Stats
          </label>
          <div className='grid grid-cols-2 gap-2'>
            <div className='p-2 bg-white rounded border text-center'>
              <div className='text-xs text-gray-500'>Total</div>
              <div className='font-semibold text-blue-600'>{territories.length}</div>
            </div>
            <div className='p-2 bg-white rounded border text-center'>
              <div className='text-xs text-gray-500'>Revenue</div>
              <div className='font-semibold text-green-600'>
                ${(territories.reduce((sum, t) => sum + t.monthlyRevenue, 0) / 1000000).toFixed(1)}M
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Filter Options */}
      <div className='mt-4 pt-4 border-t border-gray-200'>
        <h4 className='text-sm font-medium text-gray-700 mb-3'>Filter by Performance</h4>
        <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
          {/* Revenue Range Quick Filters */}
          <div className='space-y-2'>
            <label className='text-xs font-medium text-gray-600 uppercase tracking-wide'>
              Revenue Range
            </label>
            <div className='flex flex-wrap gap-2'>
              {[
                { label: '< $500K', range: [0, 500000] },
                { label: '$500K - $1M', range: [500000, 1000000] },
                { label: '> $1M', range: [1000000, Infinity] },
              ].map(({ label, range }) => {
                const isActive = territories.some(
                  (t) => t.monthlyRevenue >= range[0] && t.monthlyRevenue < range[1]
                );
                return (
                  <button
                    key={label}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                      isActive
                        ? 'bg-green-100 border-green-300 text-green-700'
                        : 'bg-gray-100 border-gray-300 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Growth Rate Quick Filters */}
          <div className='space-y-2'>
            <label className='text-xs font-medium text-gray-600 uppercase tracking-wide'>
              Growth Rate
            </label>
            <div className='flex flex-wrap gap-2'>
              {[
                { label: 'High Growth (>15%)', threshold: 15 },
                { label: 'Medium Growth (5-15%)', threshold: 5 },
                { label: 'Low Growth (<5%)', threshold: 0 },
              ].map(({ label, threshold }) => {
                const count = territories.filter((t) =>
                  threshold === 15
                    ? t.growthRate > 15
                    : threshold === 5
                      ? t.growthRate >= 5 && t.growthRate <= 15
                      : t.growthRate < 5
                ).length;
                return (
                  <button
                    key={label}
                    className='px-3 py-1 text-xs rounded-full border bg-gray-100 border-gray-300 text-gray-600 hover:bg-gray-200 transition-colors'
                  >
                    {label} ({count})
                  </button>
                );
              })}
            </div>
          </div>

          {/* Market Penetration Quick Filters */}
          <div className='space-y-2'>
            <label className='text-xs font-medium text-gray-600 uppercase tracking-wide'>
              Market Penetration
            </label>
            <div className='flex flex-wrap gap-2'>
              {[
                { label: 'High (>40%)', threshold: 40 },
                { label: 'Medium (20-40%)', threshold: 20 },
                { label: 'Low (<20%)', threshold: 0 },
              ].map(({ label, threshold }) => {
                const count = territories.filter((t) =>
                  threshold === 40
                    ? t.marketPenetration > 40
                    : threshold === 20
                      ? t.marketPenetration >= 20 && t.marketPenetration <= 40
                      : t.marketPenetration < 20
                ).length;
                return (
                  <button
                    key={label}
                    className='px-3 py-1 text-xs rounded-full border bg-gray-100 border-gray-300 text-gray-600 hover:bg-gray-200 transition-colors'
                  >
                    {label} ({count})
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Filter Summary */}
      <div className='mt-4 pt-4 border-t border-gray-200'>
        <div className='flex items-center justify-between text-sm text-gray-600'>
          <span>
            Showing {territories.length} territories
            {filters.searchTerm && ` matching "${filters.searchTerm}"`}
            {filters.region && ` in ${filters.region}`}
            {filters.competitionLevel && ` with ${filters.competitionLevel} competition`}
          </span>
          <span className='text-xs'>
            Sorted by {filters.sortBy.replace(/([A-Z])/g, ' $1').toLowerCase()}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
