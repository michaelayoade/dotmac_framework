/**
 * Territory List Component
 * Displays territories in a list format with key metrics
 */

import { motion } from 'framer-motion';
import { Activity, Building, DollarSign, MapPin, Target, TrendingUp, Users } from 'lucide-react';
import type { Territory } from '../hooks/useTerritoryData';

interface TerritoryListProps {
  territories: Territory[];
  selectedTerritory: Territory | null;
  onTerritorySelect: (territory: Territory) => void;
  className?: string;
}

export function TerritoryList({
  territories,
  selectedTerritory,
  onTerritorySelect,
  className = '',
}: TerritoryListProps) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getCompetitionColor = (level: string): string => {
    switch (level) {
      case 'low':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'high':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getGrowthColor = (rate: number): string => {
    if (rate > 10) return 'text-green-600';
    if (rate > 5) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {territories.map((territory, index) => (
        <motion.div
          key={territory.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
          className={`bg-white rounded-lg border p-4 cursor-pointer transition-all hover:shadow-md ${
            selectedTerritory?.id === territory.id
              ? 'ring-2 ring-blue-500 border-blue-500'
              : 'border-gray-200'
          }`}
          onClick={() => onTerritorySelect(territory)}
        >
          {/* Header */}
          <div className='flex items-start justify-between mb-3'>
            <div>
              <h3 className='text-lg font-semibold text-gray-900'>{territory.name}</h3>
              <p className='text-gray-600 text-sm flex items-center mt-1'>
                <MapPin className='w-4 h-4 mr-1' />
                {territory.region} Region
              </p>
            </div>
            <div className='text-right'>
              <div className='text-2xl font-bold text-gray-900'>
                {formatCurrency(territory.monthlyRevenue)}
              </div>
              <div className='text-sm text-gray-600'>Monthly Revenue</div>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className='grid grid-cols-4 gap-4 mb-3'>
            <div className='text-center'>
              <div className='flex items-center justify-center mb-1'>
                <Users className='w-4 h-4 text-blue-600' />
              </div>
              <div className='font-semibold text-gray-900'>
                {territory.totalCustomers.toLocaleString()}
              </div>
              <div className='text-xs text-gray-600'>Customers</div>
            </div>

            <div className='text-center'>
              <div className='flex items-center justify-center mb-1'>
                <Target className='w-4 h-4 text-green-600' />
              </div>
              <div className='font-semibold text-gray-900'>{territory.marketPenetration}%</div>
              <div className='text-xs text-gray-600'>Penetration</div>
            </div>

            <div className='text-center'>
              <div className='flex items-center justify-center mb-1'>
                <TrendingUp className={`w-4 h-4 ${getGrowthColor(territory.growthRate)}`} />
              </div>
              <div className={`font-semibold ${getGrowthColor(territory.growthRate)}`}>
                +{territory.growthRate}%
              </div>
              <div className='text-xs text-gray-600'>Growth</div>
            </div>

            <div className='text-center'>
              <div className='flex items-center justify-center mb-1'>
                <Building className='w-4 h-4 text-purple-600' />
              </div>
              <div className='font-semibold text-gray-900'>
                {territory.households.toLocaleString()}
              </div>
              <div className='text-xs text-gray-600'>Households</div>
            </div>
          </div>

          {/* Bottom Row */}
          <div className='flex items-center justify-between pt-3 border-t border-gray-100'>
            <div className='flex items-center space-x-4'>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getCompetitionColor(territory.competition)}`}
              >
                {territory.competition} Competition
              </span>

              <div className='text-sm text-gray-600'>
                <Activity className='w-4 h-4 inline mr-1' />
                {territory.activeProspects} prospects
              </div>
            </div>

            <div className='text-sm text-gray-500'>
              Updated {new Date(territory.lastUpdated).toLocaleDateString()}
            </div>
          </div>
        </motion.div>
      ))}

      {territories.length === 0 && (
        <div className='text-center py-8 text-gray-500'>
          <MapPin className='w-12 h-12 mx-auto mb-4 text-gray-300' />
          <p>No territories found matching your criteria.</p>
        </div>
      )}
    </div>
  );
}
