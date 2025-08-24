'use client';

import { useCachedData, usePortalAuth } from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/reseller';
import { useState, useEffect } from 'react';
import {
  AlertCircle,
  Award,
  BarChart3,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  Mail,
  MapPin,
  Phone,
  Target,
  TrendingUp,
  UserPlus,
  Users,
  Bell,
  Lightbulb,
} from 'lucide-react';

import { ResellerLayout } from '../layout/ResellerLayout';

// Mock reseller data - in real app this would come from API
const mockResellerData = {
  partner: {
    id: 'PARTNER-001',
    name: 'TechSolutions Inc.',
    partnerCode: 'TS001',
    territory: 'Northeast Region',
    joinDate: '2023-06-15',
    status: 'active',
    tier: 'Gold',
    contact: {
      name: 'Sarah Johnson',
      email: 'sarah@techsolutions.com',
      phone: '+1 (555) 987-6543',
    },
  },
  performance: {
    customersTotal: 247,
    customersActive: 234,
    customersThisMonth: 23,
    revenue: {
      total: 487650,
      thisMonth: 45780,
      lastMonth: 42150,
      growth: 8.6,
    },
    commissions: {
      earned: 24382.5,
      pending: 2289.0,
      thisMonth: 2289.0,
      lastPayout: 22093.5,
      nextPayoutDate: '2024-02-15',
    },
    targets: {
      monthlyCustomers: { current: 23, target: 25, unit: 'customers' },
      monthlyRevenue: { current: 45780, target: 50000, unit: 'revenue' },
      quarterlyGrowth: { current: 8.6, target: 10, unit: 'percentage' },
    },
  },
  recentCustomers: [
    {
      id: 'CUST-247',
      name: 'Acme Corp',
      service: 'Fiber 500/500',
      signupDate: '2024-01-28',
      status: 'active',
      revenue: 199.99,
      commission: 20.0,
    },
    {
      id: 'CUST-246',
      name: 'Smith Consulting',
      service: 'Fiber 100/100',
      signupDate: '2024-01-25',
      status: 'pending',
      revenue: 89.99,
      commission: 9.0,
    },
    {
      id: 'CUST-245',
      name: 'Local Bakery',
      service: 'Business 50/10',
      signupDate: '2024-01-22',
      status: 'active',
      revenue: 79.99,
      commission: 8.0,
    },
  ],
  salesGoals: [
    {
      id: 'goal-1',
      title: 'Q1 New Customers',
      target: 75,
      current: 23,
      deadline: '2024-03-31',
      reward: '$500 bonus',
    },
    {
      id: 'goal-2',
      title: 'Monthly Revenue Target',
      target: 50000,
      current: 45780,
      deadline: '2024-01-31',
      reward: '2% commission boost',
    },
  ],
};

export function ResellerDashboard() {
  const { _user, _currentPortal } = usePortalAuth();
  const [commissionData, setCommissionData] = useState<any>(null);
  const [salesOpportunities, setSalesOpportunities] = useState<any>(null);

  // In real app, these would be proper API calls
  const { data: resellerData } = useCachedData('reseller-overview', async () => mockResellerData, {
    ttl: 5 * 60 * 1000,
  });

  // Load commission intelligence
  useEffect(() => {
    if (resellerData?.partner?.id) {
      fetchCommissionIntelligence();
    }
  }, [resellerData]);

  const fetchCommissionIntelligence = async () => {
    try {
      // Get commission tracking data
      const commissionResponse = await fetch(`/api/isp/resellers/partners/${resellerData.partner.id}/intelligence/commission-tracking`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('reseller-token')}`,
        },
      });

      if (commissionResponse.ok) {
        const commissionData = await commissionResponse.json();
        setCommissionData(commissionData);
      } else {
        // Demo data
        setCommissionData({
          commission_alerts: [
            {
              type: 'commission_approved',
              priority: 'high',
              title: '$850.00 Approved for Payment',
              message: 'Great news! $850.00 in commissions have been approved and will be paid soon.',
            }
          ],
          commission_summary: {
            current_month_total: 2850.00,
            pending_amount: 1200.00,
            approved_amount: 850.00
          }
        });
      }

      // Get sales opportunities
      const opportunitiesResponse = await fetch(`/api/isp/resellers/partners/${resellerData.partner.id}/intelligence/sales-opportunities`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('reseller-token')}`,
        },
      });

      if (opportunitiesResponse.ok) {
        const opportunities = await opportunitiesResponse.json();
        setSalesOpportunities(opportunities);
      } else {
        // Demo data
        setSalesOpportunities({
          sales_opportunities: [
            {
              type: 'deal_followup',
              title: 'Pending Deals Need Attention',
              message: 'You have 2 pending deals worth $15,000 total.',
              potential_value: '$15,000',
              priority: 'high'
            }
          ]
        });
      }
    } catch (error) {
      console.error('Failed to fetch commission intelligence:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600';
      case 'pending':
        return 'text-yellow-600';
      case 'suspended':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className='h-4 w-4 text-green-600' />;
      case 'pending':
        return <Clock className='h-4 w-4 text-yellow-600' />;
      case 'suspended':
        return <AlertCircle className='h-4 w-4 text-red-600' />;
      default:
        return <AlertCircle className='h-4 w-4 text-gray-600' />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const calculateProgress = (current: number, target: number) => {
    return Math.min((current / target) * 100, 100);
  };

  if (!resellerData) {
    return (
      <div className="reseller-dashboard">
        <div className='flex h-64 items-center justify-center'>
          <div className='h-8 w-8 animate-spin rounded-full border-green-600 border-b-2' />
        </div>
      </div>
    );
  }

  return (
    <div className="reseller-dashboard">
      <div className='space-y-6'>
        {/* Welcome Header */}
        <div className='rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 p-6 text-white'>
          <div className='flex items-center justify-between'>
            <div>
              <h1 className='font-bold text-2xl'>
                Welcome back, {resellerData.partner.contact.name}!
              </h1>
              <p className='mt-1 text-green-100'>
                {resellerData.partner.name} • {resellerData.partner.territory}
              </p>
              <div className='mt-2 flex items-center space-x-4'>
                <div className='flex items-center'>
                  <Award className='mr-1 h-4 w-4' />
                  <span className='text-sm'>{resellerData.partner.tier} Partner</span>
                </div>
                <div className='flex items-center'>
                  <Target className='mr-1 h-4 w-4' />
                  <span className='text-sm'>Code: {resellerData.partner.partnerCode}</span>
                </div>
              </div>
            </div>
            <div className='text-right'>
              <div className='text-green-100 text-sm'>This Month&apos;s Commissions</div>
              <div className='font-bold text-3xl'>
                {formatCurrency(resellerData.performance.commissions.thisMonth)}
              </div>
            </div>
          </div>
        </div>

        {/* Commission Intelligence Alerts */}
        {commissionData && commissionData.commission_alerts.length > 0 && (
          <Card className='p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200'>
            <div className='flex items-center mb-3'>
              <Bell className='h-5 w-5 text-blue-600 mr-2' />
              <h3 className='font-semibold text-gray-900'>Commission Updates</h3>
            </div>
            <div className='space-y-2'>
              {commissionData.commission_alerts.slice(0, 2).map((alert: any, index: number) => (
                <div key={index} className={`p-3 rounded-lg ${
                  alert.priority === 'high' ? 'bg-green-50 border border-green-200' :
                  alert.priority === 'medium' ? 'bg-yellow-50 border border-yellow-200' :
                  'bg-blue-50 border border-blue-200'
                }`}>
                  <div className='flex items-start'>
                    <div className={`w-2 h-2 rounded-full mt-2 mr-3 ${
                      alert.priority === 'high' ? 'bg-green-500' :
                      alert.priority === 'medium' ? 'bg-yellow-500' :
                      'bg-blue-500'
                    }`}></div>
                    <div className='flex-1'>
                      <p className='font-medium text-gray-900 text-sm'>{alert.title}</p>
                      <p className='text-gray-600 text-sm'>{alert.message}</p>
                    </div>
                    {alert.priority === 'high' && (
                      <span className='ml-3 px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full'>
                        🎉 Great News!
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {commissionData.commission_summary && (
                <div className='mt-3 pt-3 border-t border-blue-200 flex justify-between text-sm'>
                  <span className='text-gray-600'>Pending:</span>
                  <span className='font-semibold text-gray-900'>{formatCurrency(commissionData.commission_summary.pending_amount)}</span>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Sales Opportunities Intelligence */}
        {salesOpportunities && salesOpportunities.sales_opportunities.length > 0 && (
          <Card className='p-4 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200'>
            <div className='flex items-center justify-between mb-3'>
              <div className='flex items-center'>
                <Lightbulb className='h-5 w-5 text-green-600 mr-2' />
                <h3 className='font-semibold text-gray-900'>Sales Opportunities</h3>
              </div>
              <span className='text-sm font-medium text-green-600 bg-green-100 px-2 py-1 rounded-full'>
                {salesOpportunities.sales_opportunities.length} opportunities
              </span>
            </div>
            <div className='space-y-2'>
              {salesOpportunities.sales_opportunities.slice(0, 2).map((opportunity: any, index: number) => (
                <div key={index} className='p-3 bg-white/60 rounded-lg border border-green-100'>
                  <div className='flex items-start justify-between'>
                    <div className='flex-1'>
                      <p className='font-medium text-gray-900 text-sm'>{opportunity.title}</p>
                      <p className='text-gray-600 text-sm'>{opportunity.message}</p>
                      {opportunity.potential_value && (
                        <p className='text-green-700 text-sm font-medium mt-1'>
                          💰 {opportunity.potential_value}
                        </p>
                      )}
                    </div>
                    <span className={`ml-3 px-2 py-1 text-xs font-medium rounded-full ${
                      opportunity.priority === 'high' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {opportunity.priority === 'high' ? '🔥 High Priority' : '📈 Medium Priority'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Key Performance Metrics */}
        <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Total Customers</p>
                <p className='font-bold text-3xl text-gray-900'>
                  {resellerData.performance.customersTotal}
                </p>
                <p className='text-gray-500 text-sm'>
                  {resellerData.performance.customersActive} active
                </p>
              </div>
              <Users className='h-8 w-8 text-green-600' />
            </div>
          </Card>

          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>New This Month</p>
                <p className='font-bold text-3xl text-gray-900'>
                  {resellerData.performance.customersThisMonth}
                </p>
                <p className='text-green-600 text-sm'>
                  {resellerData.performance.targets.monthlyCustomers.target -
                    resellerData.performance.targets.monthlyCustomers.current}{' '}
                  to goal
                </p>
              </div>
              <UserPlus className='h-8 w-8 text-blue-600' />
            </div>
          </Card>

          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Monthly Revenue</p>
                <p className='font-bold text-3xl text-gray-900'>
                  {formatCurrency(resellerData.performance.revenue.thisMonth)}
                </p>
                <p className='text-green-600 text-sm'>
                  +{resellerData.performance.revenue.growth}% vs last month
                </p>
              </div>
              <DollarSign className='h-8 w-8 text-purple-600' />
            </div>
          </Card>

          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Pending Commissions</p>
                <p className='font-bold text-3xl text-gray-900'>
                  {formatCurrency(resellerData.performance.commissions.pending)}
                </p>
                <p className='text-gray-500 text-sm'>
                  Payout on{' '}
                  {new Date(
                    resellerData.performance.commissions.nextPayoutDate
                  ).toLocaleDateString()}
                </p>
              </div>
              <TrendingUp className='h-8 w-8 text-orange-600' />
            </div>
          </Card>
        </div>

        {/* Goals Progress & Recent Customers */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          {/* Sales Goals */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Sales Goals</h3>
              <Target className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-4'>
              {resellerData.salesGoals.map((goal) => (
                <div key={goal.id} className='rounded-lg border p-4'>
                  <div className='mb-2 flex items-center justify-between'>
                    <h4 className='font-medium text-gray-900'>{goal.title}</h4>
                    <span className='text-gray-500 text-sm'>
                      {goal.title.includes('Revenue') ? formatCurrency(goal.current) : goal.current}{' '}
                      / {goal.title.includes('Revenue&apos;) ? formatCurrency(goal.target) : goal.target}
                    </span>
                  </div>
                  <div className='mb-2 h-2 w-full rounded-full bg-gray-200'>
                    <div
                      className='h-2 rounded-full bg-green-600 transition-all duration-300'
                      style={{
                        width: `${calculateProgress(goal.current, goal.target)}%`,
                      }}
                    />
                  </div>
                  <div className='flex justify-between text-gray-600 text-sm'>
                    <span>Due: {new Date(goal.deadline).toLocaleDateString()}</span>
                    <span className='font-medium text-green-600'>{goal.reward}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Recent Customers */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Recent Customers</h3>
              <Users className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-3'>
              {resellerData.recentCustomers.map((customer) => (
                <div
                  key={customer.id}
                  className='flex items-center justify-between rounded-lg border p-3'
                >
                  <div className='flex-1'>
                    <div className='mb-1 flex items-center justify-between'>
                      <h4 className='font-medium text-gray-900'>{customer.name}</h4>
                      <div className='flex items-center'>
                        {getStatusIcon(customer.status)}
                        <span
                          className={`ml-1 text-xs capitalize ${getStatusColor(customer.status)}`}
                        >
                          {customer.status}
                        </span>
                      </div>
                    </div>
                    <p className='text-gray-600 text-sm'>{customer.service}</p>
                    <div className='mt-1 flex items-center justify-between'>
                      <span className='text-gray-500 text-xs'>
                        Signed: {new Date(customer.signupDate).toLocaleDateString()}
                      </span>
                      <div className='text-sm'>
                        <span className='text-gray-600'>
                          Rev: {formatCurrency(customer.revenue)}
                        </span>
                        <span className='ml-2 text-green-600'>
                          Com: {formatCurrency(customer.commission)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <button
              type='button'
              className='mt-4 w-full font-medium text-green-600 text-sm hover:text-green-700'
            >
              View All Customers
            </button>
          </Card>
        </div>

        {/* Commission Summary & Quick Actions */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          {/* Commission Breakdown */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Commission Summary</h3>
              <DollarSign className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-4'>
              <div className='grid grid-cols-2 gap-4 rounded-lg bg-gray-50 p-4'>
                <div>
                  <p className='text-gray-600 text-sm'>Total Earned</p>
                  <p className='font-bold text-gray-900 text-xl'>
                    {formatCurrency(resellerData.performance.commissions.earned)}
                  </p>
                </div>
                <div>
                  <p className='text-gray-600 text-sm'>This Month</p>
                  <p className='font-bold text-green-600 text-xl'>
                    {formatCurrency(resellerData.performance.commissions.thisMonth)}
                  </p>
                </div>
              </div>

              <div className='grid grid-cols-2 gap-4'>
                <div className='rounded-lg border p-3 text-center'>
                  <p className='text-gray-600 text-sm'>Pending</p>
                  <p className='font-bold text-lg text-yellow-600'>
                    {formatCurrency(resellerData.performance.commissions.pending)}
                  </p>
                </div>
                <div className='rounded-lg border p-3 text-center'>
                  <p className='text-gray-600 text-sm'>Last Payout</p>
                  <p className='font-bold text-gray-900 text-lg'>
                    {formatCurrency(resellerData.performance.commissions.lastPayout)}
                  </p>
                </div>
              </div>

              <div className='border-t pt-3'>
                <p className='text-gray-600 text-sm'>Next Payout Date</p>
                <p className='font-semibold text-gray-900 text-lg'>
                  {new Date(
                    resellerData.performance.commissions.nextPayoutDate
                  ).toLocaleDateString()}
                </p>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Quick Actions</h3>
              <BarChart3 className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-3'>
              <div className='grid grid-cols-2 gap-3'>
                <button
                  type='button'
                  className='rounded-lg bg-green-600 px-4 py-3 font-medium text-sm text-white transition-colors hover:bg-green-700'
                >
                  Add Customer
                </button>
                <button
                  type='button'
                  className='rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 text-sm transition-colors hover:bg-gray-50'
                >
                  View Analytics
                </button>
                <button
                  type='button'
                  className='rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 text-sm transition-colors hover:bg-gray-50'
                >
                  Commission Report
                </button>
                <button
                  type='button'
                  className='rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 text-sm transition-colors hover:bg-gray-50'
                >
                  Marketing Tools
                </button>
              </div>

              {/* Partner Info */}
              <div className='mt-6 rounded-lg bg-green-50 p-4'>
                <h4 className='mb-2 font-medium text-green-900'>Partner Information</h4>
                <div className='space-y-1 text-green-800 text-sm'>
                  <div className='flex items-center'>
                    <Mail className='mr-2 h-4 w-4' />
                    <span>{resellerData.partner.contact.email}</span>
                  </div>
                  <div className='flex items-center'>
                    <Phone className='mr-2 h-4 w-4' />
                    <span>{resellerData.partner.contact.phone}</span>
                  </div>
                  <div className='flex items-center'>
                    <MapPin className='mr-2 h-4 w-4' />
                    <span>{resellerData.partner.territory}</span>
                  </div>
                  <div className='flex items-center'>
                    <Calendar className='mr-2 h-4 w-4' />
                    <span>
                      Partner since {new Date(resellerData.partner.joinDate).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
