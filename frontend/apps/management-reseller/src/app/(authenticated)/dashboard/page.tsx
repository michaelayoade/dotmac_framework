'use client';

import { useState, useEffect } from 'react';
import { 
  Users, 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  Activity,
  MapPin,
  Award,
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
  BarChart3,
  UserCheck,
  Zap,
} from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';

interface ChannelMetrics {
  total_partners: number;
  active_partners: number;
  pending_applications: number;
  total_sales_volume: number;
  monthly_sales_volume: number;
  total_commissions_paid: number;
  pending_commission_payouts: number;
  average_partner_performance: number;
  territory_coverage: number;
  partner_satisfaction: number;
  top_performers: Array<{
    partner_id: string;
    partner_name: string;
    sales_amount: number;
    commission_earned: number;
    tier: string;
  }>;
  recent_activities: Array<{
    id: string;
    type: 'PARTNER_ONBOARDED' | 'COMMISSION_PAID' | 'TERRITORY_ASSIGNED' | 'DISPUTE_RAISED';
    description: string;
    timestamp: string;
    partner_name?: string;
  }>;
  tier_distribution: Array<{
    tier: string;
    count: number;
    percentage: number;
  }>;
  performance_trends: Array<{
    month: string;
    sales_volume: number;
    partner_count: number;
    commission_paid: number;
  }>;
}

export default function DashboardPage() {
  const { user, canViewAnalytics } = useManagementAuth();
  const [metrics, setMetrics] = useState<ChannelMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeframe, setTimeframe] = useState<'week' | 'month' | 'quarter' | 'year'>('month');

  useEffect(() => {
    // Mock data - in production, fetch from management platform API
    const mockMetrics: ChannelMetrics = {
      total_partners: 247,
      active_partners: 198,
      pending_applications: 12,
      total_sales_volume: 15650000,
      monthly_sales_volume: 2340000,
      total_commissions_paid: 1870000,
      pending_commission_payouts: 156000,
      average_partner_performance: 87.3,
      territory_coverage: 73.2,
      partner_satisfaction: 91.5,
      top_performers: [
        {
          partner_id: 'partner_001',
          partner_name: 'TechConnect Solutions',
          sales_amount: 485000,
          commission_earned: 58200,
          tier: 'DIAMOND',
        },
        {
          partner_id: 'partner_002',
          partner_name: 'Network Pro Services',
          sales_amount: 423000,
          commission_earned: 50760,
          tier: 'PLATINUM',
        },
        {
          partner_id: 'partner_003',
          partner_name: 'Digital Wave Communications',
          sales_amount: 389000,
          commission_earned: 42779,
          tier: 'PLATINUM',
        },
        {
          partner_id: 'partner_004',
          partner_name: 'Metro Fiber Solutions',
          sales_amount: 367000,
          commission_earned: 40370,
          tier: 'GOLD',
        },
        {
          partner_id: 'partner_005',
          partner_name: 'Connectivity First',
          sales_amount: 345000,
          commission_earned: 37950,
          tier: 'GOLD',
        },
      ],
      recent_activities: [
        {
          id: '1',
          type: 'PARTNER_ONBOARDED',
          description: 'New partner completed onboarding process',
          timestamp: '2024-01-22T10:30:00Z',
          partner_name: 'Rural Connect ISP',
        },
        {
          id: '2',
          type: 'COMMISSION_PAID',
          description: 'Monthly commission payout processed',
          timestamp: '2024-01-22T09:15:00Z',
          partner_name: 'TechConnect Solutions',
        },
        {
          id: '3',
          type: 'TERRITORY_ASSIGNED',
          description: 'Territory assignment updated',
          timestamp: '2024-01-21T16:45:00Z',
          partner_name: 'Network Pro Services',
        },
        {
          id: '4',
          type: 'DISPUTE_RAISED',
          description: 'Commission dispute requires review',
          timestamp: '2024-01-21T14:20:00Z',
          partner_name: 'Metro Fiber Solutions',
        },
      ],
      tier_distribution: [
        { tier: 'BRONZE', count: 87, percentage: 35.2 },
        { tier: 'SILVER', count: 79, percentage: 32.0 },
        { tier: 'GOLD', count: 52, percentage: 21.1 },
        { tier: 'PLATINUM', count: 24, percentage: 9.7 },
        { tier: 'DIAMOND', count: 5, percentage: 2.0 },
      ],
      performance_trends: [
        {
          month: 'Sep 23',
          sales_volume: 1980000,
          partner_count: 235,
          commission_paid: 228000,
        },
        {
          month: 'Oct 23',
          sales_volume: 2120000,
          partner_count: 240,
          commission_paid: 248000,
        },
        {
          month: 'Nov 23',
          sales_volume: 2250000,
          partner_count: 244,
          commission_paid: 267000,
        },
        {
          month: 'Dec 23',
          sales_volume: 2180000,
          partner_count: 247,
          commission_paid: 251000,
        },
        {
          month: 'Jan 24',
          sales_volume: 2340000,
          partner_count: 247,
          commission_paid: 278000,
        },
      ],
    };

    // Simulate API call delay
    setTimeout(() => {
      setMetrics(mockMetrics);
      setIsLoading(false);
    }, 1000);
  }, [timeframe]);

  if (isLoading || !metrics) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (value: number) => `${value.toFixed(1)}%`;

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'bronze': return 'tier-bronze';
      case 'silver': return 'tier-silver';
      case 'gold': return 'tier-gold';
      case 'platinum': return 'tier-platinum';
      case 'diamond': return 'tier-diamond';
      default: return 'tier-bronze';
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'PARTNER_ONBOARDED': return <UserCheck className="h-4 w-4 text-green-600" />;
      case 'COMMISSION_PAID': return <DollarSign className="h-4 w-4 text-blue-600" />;
      case 'TERRITORY_ASSIGNED': return <MapPin className="h-4 w-4 text-purple-600" />;
      case 'DISPUTE_RAISED': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default: return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const keyMetrics = [
    {
      name: 'Active Partners',
      value: metrics.active_partners.toLocaleString(),
      total: metrics.total_partners.toLocaleString(),
      icon: Users,
      trend: { value: '+12.3%', positive: true },
      description: `of ${metrics.total_partners} total`,
    },
    {
      name: 'Monthly Sales',
      value: formatCurrency(metrics.monthly_sales_volume),
      icon: TrendingUp,
      trend: { value: '+18.7%', positive: true },
      description: 'this month',
    },
    {
      name: 'Pending Payouts',
      value: formatCurrency(metrics.pending_commission_payouts),
      icon: DollarSign,
      trend: { value: '-5.2%', positive: false },
      description: 'awaiting approval',
    },
    {
      name: 'Territory Coverage',
      value: formatPercent(metrics.territory_coverage),
      icon: MapPin,
      trend: { value: '+3.1%', positive: true },
      description: 'geographic coverage',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Channel Management Dashboard
          </h2>
          <p className="text-gray-600">
            Welcome back, {user?.name}. Here's your reseller network overview.
          </p>
        </div>

        <div className="flex space-x-3">
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value as any)}
            className="management-input w-32"
          >
            <option value="week">Last Week</option>
            <option value="month">Last Month</option>
            <option value="quarter">Last Quarter</option>
            <option value="year">This Year</option>
          </select>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {keyMetrics.map((metric) => (
          <div key={metric.name} className="metric-card">
            <div className="flex items-center justify-between">
              <div>
                <div className="metric-value">{metric.value}</div>
                <div className="metric-label">{metric.name}</div>
              </div>
              <metric.icon className="h-8 w-8 text-management-500" />
            </div>
            <div className={`metric-trend ${metric.trend.positive ? 'positive' : 'negative'}`}>
              {metric.trend.positive ? (
                <TrendingUp className="h-4 w-4 mr-1" />
              ) : (
                <TrendingDown className="h-4 w-4 mr-1" />
              )}
              {metric.trend.value} {metric.description}
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {/* Pending Actions */}
          <div className="management-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Target className="h-5 w-5 mr-2 text-management-500" />
                Pending Actions
              </h3>
              <span className="text-sm text-gray-500">{metrics.pending_applications + 2} items</span>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center">
                  <Clock className="h-5 w-5 text-yellow-600 mr-3" />
                  <div>
                    <div className="font-medium text-gray-900">
                      {metrics.pending_applications} Partner Applications
                    </div>
                    <div className="text-sm text-gray-600">Require review and approval</div>
                  </div>
                </div>
                <button className="management-button-primary text-sm px-3 py-1">
                  Review
                </button>
              </div>

              <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center">
                  <DollarSign className="h-5 w-5 text-blue-600 mr-3" />
                  <div>
                    <div className="font-medium text-gray-900">
                      {formatCurrency(metrics.pending_commission_payouts)} Commission Payouts
                    </div>
                    <div className="text-sm text-gray-600">Ready for processing</div>
                  </div>
                </div>
                <button className="management-button-primary text-sm px-3 py-1">
                  Process
                </button>
              </div>

              <div className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center">
                  <AlertTriangle className="h-5 w-5 text-red-600 mr-3" />
                  <div>
                    <div className="font-medium text-gray-900">
                      2 Commission Disputes
                    </div>
                    <div className="text-sm text-gray-600">Require investigation</div>
                  </div>
                </div>
                <button className="management-button-primary text-sm px-3 py-1">
                  Resolve
                </button>
              </div>
            </div>
          </div>
        </div>

        <div>
          {/* Partner Tier Distribution */}
          <div className="management-card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Award className="h-5 w-5 mr-2 text-management-500" />
              Partner Distribution
            </h3>
            
            <div className="space-y-3">
              {metrics.tier_distribution.map((tier) => (
                <div key={tier.tier} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <span className={`${getTierColor(tier.tier)} mr-3`}>
                      {tier.tier}
                    </span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-900 mr-2">
                      {tier.count}
                    </span>
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-management-500 h-2 rounded-full"
                        style={{ width: `${tier.percentage}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 ml-2 w-10 text-right">
                      {tier.percentage.toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Performance & Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Performers */}
        <div className="management-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Trophy className="h-5 w-5 mr-2 text-management-500" />
              Top Performers
            </h3>
            <button className="text-management-600 hover:text-management-700 text-sm font-medium">
              View All
            </button>
          </div>

          <div className="space-y-3">
            {metrics.top_performers.map((partner, index) => (
              <div key={partner.partner_id} className="partner-card">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex items-center justify-center w-8 h-8 bg-management-100 rounded-full text-management-700 font-bold text-sm mr-3">
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{partner.partner_name}</div>
                      <div className="text-sm text-gray-500">
                        {formatCurrency(partner.sales_amount)} sales
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-commission-600">
                      {formatCurrency(partner.commission_earned)}
                    </div>
                    <span className={getTierColor(partner.tier)}>
                      {partner.tier}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="management-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Activity className="h-5 w-5 mr-2 text-management-500" />
              Recent Activity
            </h3>
            <button className="text-management-600 hover:text-management-700 text-sm font-medium">
              View All
            </button>
          </div>

          <div className="space-y-4">
            {metrics.recent_activities.map((activity) => (
              <div key={activity.id} className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-1">
                  {getActivityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">{activity.description}</p>
                  {activity.partner_name && (
                    <p className="text-sm text-gray-500">{activity.partner_name}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      {canViewAnalytics() && (
        <div className="management-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <BarChart3 className="h-5 w-5 mr-2 text-management-500" />
              Channel Performance Trends
            </h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {metrics.performance_trends.slice(-3).map((trend, index) => (
              <div key={trend.month} className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(trend.sales_volume)}
                </div>
                <div className="text-sm text-gray-600">{trend.month} Sales</div>
                <div className="text-sm text-commission-600 mt-1">
                  {formatCurrency(trend.commission_paid)} commissions
                </div>
                <div className="text-xs text-gray-500">
                  {trend.partner_count} active partners
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Missing Trophy import
function Trophy({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
    </svg>
  );
}