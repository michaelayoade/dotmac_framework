'use client';

import { Badge, Button, Card } from '@dotmac/ui';
import {
  Award,
  BarChart3,
  Building,
  Calendar,
  DollarSign,
  Download,
  Mail,
  MapPin,
  Phone,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react';

import { ResellerLayout } from '../layout/ResellerLayout';

// Mock data for reseller dashboard
const mockResellerData = {
  profile: {
    id: 'RSL-001',
    name: 'TechNet Solutions',
    email: 'contact@technet.com',
    phone: '+1 (555) 987-6543',
    territory: 'Northeast Region',
    joinDate: '2023-01-15',
    status: 'active',
    tier: 'gold',
  },
  metrics: {
    totalCustomers: 247,
    activeCustomers: 231,
    monthlyRecurringRevenue: 45750,
    commissionEarned: 6862.5,
    conversionRate: 23.5,
    customerChurn: 2.1,
  },
  commissions: {
    thisMonth: 6862.5,
    lastMonth: 5940.25,
    ytd: 67342.75,
    pending: 2145.8,
    paid: 65196.95,
  },
  customers: [
    {
      id: 'CUST-101',
      name: 'Acme Corp',
      email: 'admin@acme.com',
      plan: 'Enterprise 500/500',
      mrr: 299.99,
      status: 'active',
      joinDate: '2024-03-15',
    },
    {
      id: 'CUST-102',
      name: 'Local Cafe',
      email: 'owner@localcafe.com',
      plan: 'Business 100/100',
      mrr: 79.99,
      status: 'active',
      joinDate: '2024-03-10',
    },
    {
      id: 'CUST-103',
      name: 'Home Office',
      email: 'user@homeoffice.com',
      plan: 'Residential 50/50',
      mrr: 49.99,
      status: 'pending',
      joinDate: '2024-03-20',
    },
  ],
  targets: {
    monthly: {
      target: 20,
      achieved: 14,
      remaining: 6,
    },
    revenue: {
      target: 50000,
      achieved: 45750,
      remaining: 4250,
    },
  },
  recentActivity: [
    {
      id: 'ACT-001',
      type: 'customer_signup',
      description: 'New customer: Acme Corp signed up for Enterprise plan',
      timestamp: '2024-03-15T10:30:00Z',
    },
    {
      id: 'ACT-002',
      type: 'commission_paid',
      description: 'Commission payment of $5,940.25 processed',
      timestamp: '2024-03-01T09:00:00Z',
    },
    {
      id: 'ACT-003',
      type: 'customer_upgrade',
      description: 'Local Cafe upgraded to Business plan',
      timestamp: '2024-02-28T14:45:00Z',
    },
  ],
};

export function ResellerDashboardComplete() {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'pending':
        return 'warning';
      case 'suspended':
        return 'danger';
      default:
        return 'default';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'gold':
        return 'warning';
      case 'silver':
        return 'secondary';
      case 'bronze':
        return 'primary';
      default:
        return 'default';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <ResellerLayout>
      <div className='space-y-6'>
        {/* Header */}
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='font-bold text-2xl text-gray-900'>Reseller Dashboard</h1>
            <p className='mt-1 text-gray-600'>Welcome back, {mockResellerData.profile.name}</p>
          </div>
          <div className='flex items-center space-x-3'>
            <Badge variant={getTierColor(mockResellerData.profile.tier)} size='lg'>
              <Award className='mr-1 h-4 w-4' />
              {mockResellerData.profile.tier.toUpperCase()} Partner
            </Badge>
            <Badge variant={getStatusColor(mockResellerData.profile.status)}>
              {mockResellerData.profile.status.toUpperCase()}
            </Badge>
          </div>
        </div>

        {/* Key Metrics */}
        <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
          <Card>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Total Customers</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  {mockResellerData.metrics.totalCustomers}
                </p>
                <p className='mt-1 text-green-600 text-sm'>
                  {mockResellerData.metrics.activeCustomers} active
                </p>
              </div>
              <div className='rounded-full bg-blue-100 p-3'>
                <Users className='h-6 w-6 text-blue-600' />
              </div>
            </div>
          </Card>

          <Card>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Monthly Revenue</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  {formatCurrency(mockResellerData.metrics.monthlyRecurringRevenue)}
                </p>
                <p className='mt-1 text-green-600 text-sm'>+12.5% from last month</p>
              </div>
              <div className='rounded-full bg-green-100 p-3'>
                <DollarSign className='h-6 w-6 text-green-600' />
              </div>
            </div>
          </Card>

          <Card>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Commission Earned</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  {formatCurrency(mockResellerData.commissions.thisMonth)}
                </p>
                <p className='mt-1 text-blue-600 text-sm'>This month</p>
              </div>
              <div className='rounded-full bg-purple-100 p-3'>
                <TrendingUp className='h-6 w-6 text-purple-600' />
              </div>
            </div>
          </Card>

          <Card>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Conversion Rate</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  {mockResellerData.metrics.conversionRate}%
                </p>
                <p className='mt-1 text-green-600 text-sm'>Above average</p>
              </div>
              <div className='rounded-full bg-orange-100 p-3'>
                <Target className='h-6 w-6 text-orange-600' />
              </div>
            </div>
          </Card>
        </div>

        {/* Targets & Commission Details */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          <Card
            header={
              <div className='flex items-center justify-between'>
                <h3 className='font-semibold text-gray-900 text-lg'>Monthly Targets</h3>
                <Calendar className='h-5 w-5 text-gray-400' />
              </div>
            }
          >
            <div className='space-y-6'>
              <div>
                <div className='mb-2 flex justify-between text-sm'>
                  <span className='font-medium text-gray-700'>Customer Acquisitions</span>
                  <span className='text-gray-500'>
                    {mockResellerData.targets.monthly.achieved} /{' '}
                    {mockResellerData.targets.monthly.target}
                  </span>
                </div>
                <div className='w-full bg-gray-200 rounded-full h-2'>
                  <div
                    className='bg-green-600 h-2 rounded-full'
                    style={{
                      width: `${(mockResellerData.targets.monthly.achieved / mockResellerData.targets.monthly.target) * 100}%`,
                    }}
                  />
                </div>
                <p className='mt-1 text-gray-500 text-xs'>
                  {mockResellerData.targets.monthly.remaining} more needed to reach target
                </p>
              </div>

              <div>
                <div className='mb-2 flex justify-between text-sm'>
                  <span className='font-medium text-gray-700'>Revenue Target</span>
                  <span className='text-gray-500'>
                    {formatCurrency(mockResellerData.targets.revenue.achieved)} /{' '}
                    {formatCurrency(mockResellerData.targets.revenue.target)}
                  </span>
                </div>
                <div className='w-full bg-gray-200 rounded-full h-2'>
                  <div
                    className='bg-blue-600 h-2 rounded-full'
                    style={{
                      width: `${(mockResellerData.targets.revenue.achieved / mockResellerData.targets.revenue.target) * 100}%`,
                    }}
                  />
                </div>
                <p className='mt-1 text-gray-500 text-xs'>
                  {formatCurrency(mockResellerData.targets.revenue.remaining)} remaining
                </p>
              </div>
            </div>
          </Card>

          <Card
            header={
              <div className='flex items-center justify-between'>
                <h3 className='font-semibold text-gray-900 text-lg'>Commission Summary</h3>
                <BarChart3 className='h-5 w-5 text-gray-400' />
              </div>
            }
          >
            <div className='space-y-4'>
              <div className='flex items-center justify-between'>
                <span className='font-medium text-gray-700 text-sm'>This Month</span>
                <span className='font-bold text-green-600 text-lg'>
                  {formatCurrency(mockResellerData.commissions.thisMonth)}
                </span>
              </div>

              <div className='flex items-center justify-between'>
                <span className='font-medium text-gray-700 text-sm'>Last Month</span>
                <span className='text-gray-900 text-sm'>
                  {formatCurrency(mockResellerData.commissions.lastMonth)}
                </span>
              </div>

              <div className='border-t pt-4'>
                <div className='flex items-center justify-between'>
                  <span className='font-medium text-gray-700 text-sm'>Year to Date</span>
                  <span className='font-bold text-gray-900 text-lg'>
                    {formatCurrency(mockResellerData.commissions.ytd)}
                  </span>
                </div>
              </div>

              <div className='grid grid-cols-2 gap-4 border-t pt-4'>
                <div>
                  <p className='text-gray-500 text-xs'>Pending</p>
                  <p className='font-medium text-yellow-600'>
                    {formatCurrency(mockResellerData.commissions.pending)}
                  </p>
                </div>
                <div>
                  <p className='text-gray-500 text-xs'>Paid</p>
                  <p className='font-medium text-green-600'>
                    {formatCurrency(mockResellerData.commissions.paid)}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Recent Customers & Activity */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-3'>
          <div className='lg:col-span-2'>
            <Card
              header={
                <div className='flex items-center justify-between'>
                  <h3 className='font-semibold text-gray-900 text-lg'>Recent Customers</h3>
                  <Button variant='outline' size='sm'>
                    <Users className='mr-2 h-4 w-4' />
                    View All
                  </Button>
                </div>
              }
            >
              <div className='space-y-4'>
                {mockResellerData.customers.map((customer) => (
                  <div
                    key={customer.id}
                    className='flex items-center justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50'
                  >
                    <div className='flex-1'>
                      <div className='flex items-center justify-between'>
                        <h4 className='font-medium text-gray-900'>{customer.name}</h4>
                        <Badge variant={getStatusColor(customer.status)} size='sm'>
                          {customer.status}
                        </Badge>
                      </div>
                      <p className='mt-1 text-gray-500 text-sm'>{customer.email}</p>
                      <div className='mt-2 flex items-center text-gray-600 text-sm'>
                        <span className='font-medium'>{customer.plan}</span>
                        <span className='mx-2'>•</span>
                        <span>{formatCurrency(customer.mrr)}/month</span>
                        <span className='mx-2'>•</span>
                        <span>Joined {formatDate(customer.joinDate)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <Card header={<h3 className='font-semibold text-gray-900 text-lg'>Recent Activity</h3>}>
            <div className='space-y-4'>
              {mockResellerData.recentActivity.map((activity) => (
                <div key={activity.id} className='flex items-start space-x-3'>
                  <div className='flex-shrink-0'>
                    <div className='mt-2 h-2 w-2 rounded-full bg-blue-600' />
                  </div>
                  <div className='flex-1'>
                    <p className='text-gray-900 text-sm'>{activity.description}</p>
                    <p className='mt-1 text-gray-500 text-xs'>{formatDate(activity.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Profile & Territory Info */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          <Card
            header={<h3 className='font-semibold text-gray-900 text-lg'>Profile Information</h3>}
          >
            <div className='space-y-4'>
              <div className='grid grid-cols-2 gap-4'>
                <div>
                  <p className='font-medium text-gray-700 text-sm'>Company</p>
                  <p className='mt-1 text-gray-900 text-sm'>{mockResellerData.profile.name}</p>
                </div>
                <div>
                  <p className='font-medium text-gray-700 text-sm'>Partner ID</p>
                  <p className='mt-1 text-gray-900 text-sm'>{mockResellerData.profile.id}</p>
                </div>
              </div>

              <div className='grid grid-cols-1 gap-4'>
                <div className='flex items-center space-x-2'>
                  <Mail className='h-4 w-4 text-gray-400' />
                  <span className='text-gray-900 text-sm'>{mockResellerData.profile.email}</span>
                </div>
                <div className='flex items-center space-x-2'>
                  <Phone className='h-4 w-4 text-gray-400' />
                  <span className='text-gray-900 text-sm'>{mockResellerData.profile.phone}</span>
                </div>
                <div className='flex items-center space-x-2'>
                  <MapPin className='h-4 w-4 text-gray-400' />
                  <span className='text-gray-900 text-sm'>
                    {mockResellerData.profile.territory}
                  </span>
                </div>
                <div className='flex items-center space-x-2'>
                  <Building className='h-4 w-4 text-gray-400' />
                  <span className='text-gray-900 text-sm'>
                    Partner since {formatDate(mockResellerData.profile.joinDate)}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          <Card header={<h3 className='font-semibold text-gray-900 text-lg'>Quick Actions</h3>}>
            <div className='space-y-3'>
              <Button variant='primary' fullWidth>
                <Users className='mr-2 h-4 w-4' />
                Add New Customer
              </Button>

              <Button variant='outline' fullWidth>
                <Download className='mr-2 h-4 w-4' />
                Download Commission Report
              </Button>

              <Button variant='outline' fullWidth>
                <BarChart3 className='mr-2 h-4 w-4' />
                View Analytics
              </Button>

              <Button variant='ghost' fullWidth>
                <Target className='mr-2 h-4 w-4' />
                Marketing Materials
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </ResellerLayout>
  );
}
