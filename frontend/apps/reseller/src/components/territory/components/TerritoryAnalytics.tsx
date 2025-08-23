/**
 * Territory Analytics Component
 * Comprehensive analytics and insights for territory performance
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Users,
  DollarSign,
  Target,
  Zap,
  Building2,
  Wifi,
  BarChart3,
  PieChart,
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Territory } from '../hooks/useTerritoryData';

interface TerritoryAnalyticsProps {
  territories: Territory[];
  selectedTerritory: Territory | null;
}

interface AnalyticsMetric {
  label: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: string;
  trend?: 'up' | 'down' | 'stable';
}

interface PerformanceSegment {
  name: string;
  count: number;
  percentage: number;
  color: string;
  territories: Territory[];
}

export function TerritoryAnalytics({ territories, selectedTerritory }: TerritoryAnalyticsProps) {
  // Calculate aggregate metrics
  const aggregateMetrics = useMemo((): AnalyticsMetric[] => {
    const totalRevenue = territories.reduce((sum, t) => sum + t.monthlyRevenue, 0);
    const totalCustomers = territories.reduce((sum, t) => sum + t.totalCustomers, 0);
    const totalProspects = territories.reduce((sum, t) => sum + t.activeProspects, 0);
    const avgGrowthRate =
      territories.reduce((sum, t) => sum + t.growthRate, 0) / territories.length;
    const avgPenetration =
      territories.reduce((sum, t) => sum + t.marketPenetration, 0) / territories.length;
    const avgServiceability =
      territories.reduce((sum, t) => sum + t.serviceability, 0) / territories.length;

    return [
      {
        label: 'Total Monthly Revenue',
        value: `$${(totalRevenue / 1000000).toFixed(2)}M`,
        change: 12.5,
        icon: <DollarSign className='w-6 h-6' />,
        color: 'text-green-600',
        trend: 'up',
      },
      {
        label: 'Total Customers',
        value: totalCustomers.toLocaleString(),
        change: 8.3,
        icon: <Users className='w-6 h-6' />,
        color: 'text-blue-600',
        trend: 'up',
      },
      {
        label: 'Active Prospects',
        value: totalProspects.toLocaleString(),
        change: -2.1,
        icon: <Target className='w-6 h-6' />,
        color: 'text-orange-600',
        trend: 'down',
      },
      {
        label: 'Average Growth Rate',
        value: `${avgGrowthRate.toFixed(1)}%`,
        change: 1.8,
        icon: <TrendingUp className='w-6 h-6' />,
        color: 'text-purple-600',
        trend: 'up',
      },
      {
        label: 'Market Penetration',
        value: `${avgPenetration.toFixed(1)}%`,
        change: 0.7,
        icon: <PieChart className='w-6 h-6' />,
        color: 'text-indigo-600',
        trend: 'up',
      },
      {
        label: 'Serviceability',
        value: `${avgServiceability.toFixed(1)}%`,
        change: 2.3,
        icon: <Wifi className='w-6 h-6' />,
        color: 'text-teal-600',
        trend: 'up',
      },
    ];
  }, [territories]);

  // Performance segmentation
  const performanceSegments = useMemo((): PerformanceSegment[] => {
    const highPerformers = territories.filter((t) => t.growthRate > 15 && t.marketPenetration > 35);
    const goodPerformers = territories.filter(
      (t) =>
        (t.growthRate > 10 && t.growthRate <= 15) ||
        (t.marketPenetration > 25 && t.marketPenetration <= 35)
    );
    const averagePerformers = territories.filter(
      (t) =>
        (t.growthRate > 5 && t.growthRate <= 10) ||
        (t.marketPenetration > 15 && t.marketPenetration <= 25)
    );
    const underPerformers = territories.filter(
      (t) => t.growthRate <= 5 && t.marketPenetration <= 15
    );

    const total = territories.length;

    return [
      {
        name: 'High Performers',
        count: highPerformers.length,
        percentage: (highPerformers.length / total) * 100,
        color: 'bg-green-500',
        territories: highPerformers,
      },
      {
        name: 'Good Performers',
        count: goodPerformers.length,
        percentage: (goodPerformers.length / total) * 100,
        color: 'bg-blue-500',
        territories: goodPerformers,
      },
      {
        name: 'Average Performers',
        count: averagePerformers.length,
        percentage: (averagePerformers.length / total) * 100,
        color: 'bg-yellow-500',
        territories: averagePerformers,
      },
      {
        name: 'Under Performers',
        count: underPerformers.length,
        percentage: (underPerformers.length / total) * 100,
        color: 'bg-red-500',
        territories: underPerformers,
      },
    ];
  }, [territories]);

  // Competition analysis
  const competitionAnalysis = useMemo(() => {
    const lowCompetition = territories.filter((t) => t.competition === 'low');
    const mediumCompetition = territories.filter((t) => t.competition === 'medium');
    const highCompetition = territories.filter((t) => t.competition === 'high');

    return [
      {
        level: 'Low Competition',
        count: lowCompetition.length,
        color: 'bg-green-400',
        territories: lowCompetition,
      },
      {
        level: 'Medium Competition',
        count: mediumCompetition.length,
        color: 'bg-yellow-400',
        territories: mediumCompetition,
      },
      {
        level: 'High Competition',
        count: highCompetition.length,
        color: 'bg-red-400',
        territories: highCompetition,
      },
    ];
  }, [territories]);

  // Service type distribution
  const serviceDistribution = useMemo(() => {
    const totalTerritories = territories.length;
    const fiberAvg = territories.reduce((sum, t) => sum + t.services.fiber, 0) / totalTerritories;
    const cableAvg = territories.reduce((sum, t) => sum + t.services.cable, 0) / totalTerritories;
    const dslAvg = territories.reduce((sum, t) => sum + t.services.dsl, 0) / totalTerritories;

    return [
      { service: 'Fiber', percentage: fiberAvg, color: 'bg-blue-500' },
      { service: 'Cable', percentage: cableAvg, color: 'bg-green-500' },
      { service: 'DSL', percentage: dslAvg, color: 'bg-orange-500' },
    ];
  }, [territories]);

  // Top performing territories
  const topTerritories = useMemo(() => {
    return [...territories].sort((a, b) => b.monthlyRevenue - a.monthlyRevenue).slice(0, 5);
  }, [territories]);

  // Opportunities summary
  const opportunitiesSummary = useMemo(() => {
    const totalNewDevelopments = territories.reduce(
      (sum, t) => sum + t.opportunities.newDevelopments,
      0
    );
    const totalBusinessParks = territories.reduce(
      (sum, t) => sum + t.opportunities.businessParks,
      0
    );
    const totalCompetitorWeakness = territories.reduce(
      (sum, t) => sum + t.opportunities.competitorWeakness,
      0
    );

    return [
      {
        type: 'New Developments',
        count: totalNewDevelopments,
        icon: <Building2 className='w-5 h-5' />,
        color: 'text-green-600',
      },
      {
        type: 'Business Parks',
        count: totalBusinessParks,
        icon: <Building2 className='w-5 h-5' />,
        color: 'text-blue-600',
      },
      {
        type: 'Competitor Weakness',
        count: totalCompetitorWeakness,
        icon: <Zap className='w-5 h-5' />,
        color: 'text-orange-600',
      },
    ];
  }, [territories]);

  if (selectedTerritory) {
    // Show detailed analytics for selected territory
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className='space-y-6'
      >
        <div className='flex items-center justify-between'>
          <h3 className='text-xl font-bold text-gray-900'>{selectedTerritory.name} Analytics</h3>
          <span className='px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full'>
            {selectedTerritory.region}
          </span>
        </div>

        {/* Territory-specific metrics */}
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
          <div className='bg-gradient-to-r from-green-50 to-green-100 p-6 rounded-lg border border-green-200'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-lg font-semibold text-green-800'>Monthly Revenue</h4>
                <p className='text-2xl font-bold text-green-600'>
                  ${(selectedTerritory.monthlyRevenue / 1000).toFixed(0)}K
                </p>
              </div>
              <DollarSign className='w-8 h-8 text-green-600' />
            </div>
          </div>

          <div className='bg-gradient-to-r from-blue-50 to-blue-100 p-6 rounded-lg border border-blue-200'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-lg font-semibold text-blue-800'>Growth Rate</h4>
                <p className='text-2xl font-bold text-blue-600'>{selectedTerritory.growthRate}%</p>
              </div>
              <TrendingUp className='w-8 h-8 text-blue-600' />
            </div>
          </div>

          <div className='bg-gradient-to-r from-purple-50 to-purple-100 p-6 rounded-lg border border-purple-200'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-lg font-semibold text-purple-800'>Market Penetration</h4>
                <p className='text-2xl font-bold text-purple-600'>
                  {selectedTerritory.marketPenetration}%
                </p>
              </div>
              <Target className='w-8 h-8 text-purple-600' />
            </div>
          </div>
        </div>

        {/* Territory details grid */}
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
          {/* Demographics */}
          <div className='bg-white p-6 rounded-lg border border-gray-200'>
            <h4 className='text-lg font-semibold text-gray-900 mb-4'>Customer Demographics</h4>
            <div className='space-y-3'>
              {Object.entries(selectedTerritory.demographics).map(([type, percentage]) => (
                <div key={type} className='flex items-center justify-between'>
                  <span className='text-gray-700 capitalize'>{type}</span>
                  <div className='flex items-center space-x-2'>
                    <div className='w-20 bg-gray-200 rounded-full h-2'>
                      <div
                        className='bg-blue-500 h-2 rounded-full'
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className='text-sm font-medium text-gray-900'>{percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Service Distribution */}
          <div className='bg-white p-6 rounded-lg border border-gray-200'>
            <h4 className='text-lg font-semibold text-gray-900 mb-4'>Service Distribution</h4>
            <div className='space-y-3'>
              {Object.entries(selectedTerritory.services).map(([service, percentage]) => (
                <div key={service} className='flex items-center justify-between'>
                  <span className='text-gray-700 capitalize'>{service}</span>
                  <div className='flex items-center space-x-2'>
                    <div className='w-20 bg-gray-200 rounded-full h-2'>
                      <div
                        className={`h-2 rounded-full ${
                          service === 'fiber'
                            ? 'bg-blue-500'
                            : service === 'cable'
                              ? 'bg-green-500'
                              : 'bg-orange-500'
                        }`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className='text-sm font-medium text-gray-900'>{percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  // Show overall analytics
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className='space-y-6'
    >
      <div className='flex items-center justify-between'>
        <h3 className='text-xl font-bold text-gray-900'>Territory Portfolio Analytics</h3>
        <div className='flex items-center space-x-2 text-sm text-gray-600'>
          <Activity className='w-4 h-4' />
          <span>Live Data • Updated {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
        {aggregateMetrics.map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className='bg-white p-6 rounded-lg border border-gray-200 hover:shadow-md transition-shadow'
          >
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>{metric.label}</p>
                <p className='text-2xl font-bold text-gray-900'>{metric.value}</p>
                {metric.change && (
                  <div
                    className={`flex items-center space-x-1 text-sm ${
                      metric.trend === 'up'
                        ? 'text-green-600'
                        : metric.trend === 'down'
                          ? 'text-red-600'
                          : 'text-gray-600'
                    }`}
                  >
                    {metric.trend === 'up' && <TrendingUp className='w-4 h-4' />}
                    {metric.trend === 'down' && <TrendingDown className='w-4 h-4' />}
                    <span>{Math.abs(metric.change)}% vs last month</span>
                  </div>
                )}
              </div>
              <div className={`${metric.color} opacity-80`}>{metric.icon}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Performance and Competition Analysis */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Performance Segmentation */}
        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <h4 className='text-lg font-semibold text-gray-900 mb-4 flex items-center'>
            <BarChart3 className='w-5 h-5 mr-2 text-blue-600' />
            Performance Segmentation
          </h4>
          <div className='space-y-4'>
            {performanceSegments.map((segment) => (
              <div key={segment.name} className='flex items-center justify-between'>
                <div className='flex items-center space-x-3'>
                  <div className={`w-4 h-4 rounded ${segment.color}`} />
                  <span className='text-gray-700'>{segment.name}</span>
                </div>
                <div className='text-right'>
                  <div className='text-sm font-medium text-gray-900'>
                    {segment.count} territories
                  </div>
                  <div className='text-xs text-gray-500'>{segment.percentage.toFixed(1)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Competition Analysis */}
        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <h4 className='text-lg font-semibold text-gray-900 mb-4 flex items-center'>
            <Zap className='w-5 h-5 mr-2 text-orange-600' />
            Competition Analysis
          </h4>
          <div className='space-y-4'>
            {competitionAnalysis.map((analysis) => (
              <div key={analysis.level} className='flex items-center justify-between'>
                <div className='flex items-center space-x-3'>
                  <div className={`w-4 h-4 rounded ${analysis.color}`} />
                  <span className='text-gray-700'>{analysis.level}</span>
                </div>
                <div className='text-right'>
                  <div className='text-sm font-medium text-gray-900'>
                    {analysis.count} territories
                  </div>
                  <div className='text-xs text-gray-500'>
                    {((analysis.count / territories.length) * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Performers and Opportunities */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Top Performing Territories */}
        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <h4 className='text-lg font-semibold text-gray-900 mb-4 flex items-center'>
            <CheckCircle className='w-5 h-5 mr-2 text-green-600' />
            Top Revenue Territories
          </h4>
          <div className='space-y-3'>
            {topTerritories.map((territory, index) => (
              <div
                key={territory.id}
                className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
              >
                <div className='flex items-center space-x-3'>
                  <div className='w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium'>
                    {index + 1}
                  </div>
                  <div>
                    <div className='font-medium text-gray-900'>{territory.name}</div>
                    <div className='text-sm text-gray-500'>{territory.region}</div>
                  </div>
                </div>
                <div className='text-right'>
                  <div className='font-semibold text-green-600'>
                    ${(territory.monthlyRevenue / 1000).toFixed(0)}K
                  </div>
                  <div className='text-xs text-gray-500'>{territory.growthRate}% growth</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Opportunities Summary */}
        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <h4 className='text-lg font-semibold text-gray-900 mb-4 flex items-center'>
            <AlertCircle className='w-5 h-5 mr-2 text-orange-600' />
            Growth Opportunities
          </h4>
          <div className='space-y-4'>
            {opportunitiesSummary.map((opportunity) => (
              <div
                key={opportunity.type}
                className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
              >
                <div className='flex items-center space-x-3'>
                  <div className={opportunity.color}>{opportunity.icon}</div>
                  <span className='text-gray-700'>{opportunity.type}</span>
                </div>
                <div className='text-lg font-semibold text-gray-900'>{opportunity.count}</div>
              </div>
            ))}
          </div>
          <div className='mt-4 pt-4 border-t border-gray-200'>
            <p className='text-sm text-gray-600'>
              Total potential opportunities across all territories
            </p>
          </div>
        </div>
      </div>

      {/* Service Distribution Across Portfolio */}
      <div className='bg-white p-6 rounded-lg border border-gray-200'>
        <h4 className='text-lg font-semibold text-gray-900 mb-4 flex items-center'>
          <Wifi className='w-5 h-5 mr-2 text-teal-600' />
          Service Technology Distribution
        </h4>
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
          {serviceDistribution.map((service) => (
            <div key={service.service} className='text-center'>
              <div className='mx-auto w-24 h-24 rounded-full border-8 border-gray-200 flex items-center justify-center mb-3'>
                <div
                  className={`w-16 h-16 rounded-full ${service.color} flex items-center justify-center text-white font-bold text-lg`}
                >
                  {service.percentage.toFixed(0)}%
                </div>
              </div>
              <h5 className='font-medium text-gray-900'>{service.service}</h5>
              <p className='text-sm text-gray-600'>Average across territories</p>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
