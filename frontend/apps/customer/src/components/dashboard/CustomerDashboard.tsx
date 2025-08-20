'use client';

import { useCustomerDashboard, usePortalAuth } from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/customer';
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  CreditCard,
  Download,
  Globe,
  MessageSquare,
  TrendingUp,
  Upload,
  Wifi,
} from 'lucide-react';

import { CustomerLayout } from '../layout/CustomerLayout';

// Mock data - in real app this would come from API
const _mockCustomerData = {
  account: {
    id: 'CUST-001',
    name: 'John Doe',
    accountNumber: 'ACC-123456',
    serviceAddress: '123 Main St, City, State 12345',
    phone: '+1 (555) 123-4567',
    email: 'john.doe@email.com',
  },
  services: [
    {
      id: 'SVC-001',
      name: 'Fiber Internet 100/100',
      type: 'internet',
      status: 'active',
      speed: { download: 100, upload: 100 },
      usage: { current: 450, limit: 1000, unit: 'GB' },
      monthlyPrice: 79.99,
      installDate: '2024-01-15',
    },
    {
      id: 'SVC-002',
      name: 'Basic Phone Service',
      type: 'phone',
      status: 'active',
      monthlyPrice: 29.99,
      features: ['Unlimited Local', 'Voicemail', 'Caller ID'],
    },
  ],
  billing: {
    currentBalance: 0,
    nextBillDate: '2024-02-15',
    nextBillAmount: 109.98,
    lastPayment: {
      amount: 109.98,
      date: '2024-01-15',
      method: 'Auto Pay',
    },
    paymentMethod: 'Credit Card ending in 1234',
  },
  networkStatus: {
    connectionStatus: 'connected',
    currentSpeed: { download: 98.5, upload: 99.2 },
    uptime: 99.8,
    lastOutage: null,
    signalStrength: 'excellent',
  },
  supportTickets: [
    {
      id: 'TICK-001',
      subject: 'Slow internet speeds',
      status: 'resolved',
      priority: 'medium',
      createdDate: '2024-01-10',
      resolvedDate: '2024-01-12',
    },
  ],
};

export function CustomerDashboard() {
  const { _user, _currentPortal } = usePortalAuth();

  const { data: customerData, isLoading, isUsingMockData } = useCustomerDashboard();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'connected':
      case 'resolved':
        return 'text-green-600';
      case 'suspended':
      case 'disconnected':
        return 'text-red-600';
      case 'pending':
      case 'in_progress':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
      case 'connected':
      case 'resolved':
        return <CheckCircle className='h-5 w-5 text-green-600' />;
      case 'suspended':
      case 'disconnected':
        return <AlertCircle className='h-5 w-5 text-red-600' />;
      case 'pending':
      case 'in_progress':
        return <Clock className='h-5 w-5 text-yellow-600' />;
      default:
        return <AlertCircle className='h-5 w-5 text-gray-600' />;
    }
  };

  if (isLoading || !customerData) {
    return (
      <CustomerLayout>
        <div className='flex h-64 items-center justify-center'>
          <div className='h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2' />
        </div>
      </CustomerLayout>
    );
  }

  return (
    <CustomerLayout>
      <div className='space-y-6'>
        {/* Development indicator */}
        {isUsingMockData && process.env.NODE_ENV === 'development' ? (
          <div className='rounded-lg border border-yellow-200 bg-yellow-50 p-3'>
            <div className='flex items-center'>
              <AlertCircle className='mr-2 h-4 w-4 text-yellow-600' />
              <span className='text-sm text-yellow-800'>Using mock data - API not available</span>
            </div>
          </div>
        ) : null}
        {/* Welcome Header */}
        <div className='rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white'>
          <div className='flex items-center justify-between'>
            <div>
              <h1 className='font-bold text-2xl'>Welcome back, {customerData.account.name}!</h1>
              <p className='mt-1 text-blue-100'>Account: {customerData.account.accountNumber}</p>
            </div>
            <div className='text-right'>
              <div className='text-blue-100 text-sm'>Current Balance</div>
              <div className='font-bold text-2xl'>
                ${customerData.billing.currentBalance.toFixed(2)}
              </div>
            </div>
          </div>
        </div>

        {/* Service Status Overview */}
        <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Connection Status</p>
                <div className='mt-2 flex items-center'>
                  {getStatusIcon(customerData.networkStatus.connectionStatus)}
                  <span
                    className={`ml-2 font-semibold capitalize ${getStatusColor(customerData.networkStatus.connectionStatus)}`}
                  >
                    {customerData.networkStatus.connectionStatus}
                  </span>
                </div>
              </div>
              <Wifi className='h-8 w-8 text-blue-600' />
            </div>
          </Card>

          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Current Speed</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  {customerData.networkStatus.currentSpeed.download}
                  <span className='ml-1 text-gray-500 text-sm'>Mbps</span>
                </p>
              </div>
              <TrendingUp className='h-8 w-8 text-green-600' />
            </div>
          </Card>

          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Data Usage</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  {customerData.services[0].usage.current}
                  <span className='text-gray-500 text-sm'>
                    /{customerData.services[0].usage.limit} GB
                  </span>
                </p>
              </div>
              <Activity className='h-8 w-8 text-purple-600' />
            </div>
          </Card>

          <Card className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='font-medium text-gray-600 text-sm'>Next Bill</p>
                <p className='mt-1 font-bold text-2xl text-gray-900'>
                  ${customerData.billing.nextBillAmount}
                </p>
                <p className='text-gray-500 text-sm'>
                  Due {new Date(customerData.billing.nextBillDate).toLocaleDateString()}
                </p>
              </div>
              <CreditCard className='h-8 w-8 text-orange-600' />
            </div>
          </Card>
        </div>

        {/* Services & Network Performance */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          {/* Active Services */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Your Services</h3>
              <Globe className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-4'>
              {customerData.services.map((service) => (
                <div key={service.id} className='rounded-lg border p-4'>
                  <div className='mb-2 flex items-center justify-between'>
                    <h4 className='font-medium text-gray-900'>{service.name}</h4>
                    <div className='flex items-center'>
                      {getStatusIcon(service.status)}
                      <span className={`ml-1 text-sm capitalize ${getStatusColor(service.status)}`}>
                        {service.status}
                      </span>
                    </div>
                  </div>
                  <div className='grid grid-cols-2 gap-4 text-gray-600 text-sm'>
                    <div>
                      <span className='font-medium'>Monthly Price:</span> ${service.monthlyPrice}
                    </div>
                    {service.speed ? (
                      <div>
                        <span className='font-medium'>Speed:</span> {service.speed.download}/
                        {service.speed.upload} Mbps
                      </div>
                    ) : null}
                  </div>
                  {service.usage ? (
                    <div className='mt-3'>
                      <div className='mb-1 flex justify-between text-gray-600 text-sm'>
                        <span>Data Usage</span>
                        <span>
                          {service.usage.current} / {service.usage.limit} {service.usage.unit}
                        </span>
                      </div>
                      <div className='h-2 w-full rounded-full bg-gray-200'>
                        <div
                          className='h-2 rounded-full bg-blue-600 transition-all duration-300'
                          style={{
                            width: `${(service.usage.current / service.usage.limit) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>

          {/* Network Performance */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Network Performance</h3>
              <Activity className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-4'>
              <div className='flex items-center justify-between rounded-lg bg-gray-50 p-3'>
                <div className='flex items-center'>
                  <Download className='mr-2 h-5 w-5 text-green-600' />
                  <span className='font-medium'>Download Speed</span>
                </div>
                <span className='font-bold text-gray-900 text-lg'>
                  {customerData.networkStatus.currentSpeed.download} Mbps
                </span>
              </div>

              <div className='flex items-center justify-between rounded-lg bg-gray-50 p-3'>
                <div className='flex items-center'>
                  <Upload className='mr-2 h-5 w-5 text-blue-600' />
                  <span className='font-medium'>Upload Speed</span>
                </div>
                <span className='font-bold text-gray-900 text-lg'>
                  {customerData.networkStatus.currentSpeed.upload} Mbps
                </span>
              </div>

              <div className='flex items-center justify-between rounded-lg bg-gray-50 p-3'>
                <div className='flex items-center'>
                  <CheckCircle className='mr-2 h-5 w-5 text-green-600' />
                  <span className='font-medium'>Network Uptime</span>
                </div>
                <span className='font-bold text-gray-900 text-lg'>
                  {customerData.networkStatus.uptime}%
                </span>
              </div>

              <button
                type='button'
                className='mt-4 w-full rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'
              >
                Run Speed Test
              </button>
            </div>
          </Card>
        </div>

        {/* Recent Activity & Quick Actions */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          {/* Recent Billing */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Billing Summary</h3>
              <CreditCard className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-3'>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Last Payment</span>
                <span className='font-medium'>${customerData.billing.lastPayment.amount}</span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Payment Date</span>
                <span className='font-medium'>
                  {new Date(customerData.billing.lastPayment.date).toLocaleDateString()}
                </span>
              </div>
              <div className='flex justify-between'>
                <span className='text-gray-600'>Payment Method</span>
                <span className='font-medium'>{customerData.billing.paymentMethod}</span>
              </div>
              <div className='border-t pt-3'>
                <div className='flex justify-between text-lg'>
                  <span className='font-semibold'>Next Bill Amount</span>
                  <span className='font-bold text-blue-600'>
                    ${customerData.billing.nextBillAmount}
                  </span>
                </div>
                <p className='mt-1 text-gray-500 text-sm'>
                  Due {new Date(customerData.billing.nextBillDate).toLocaleDateString()}
                </p>
              </div>
            </div>
          </Card>

          {/* Support & Quick Actions */}
          <Card className='p-6'>
            <div className='mb-4 flex items-center justify-between'>
              <h3 className='font-semibold text-gray-900 text-lg'>Support & Actions</h3>
              <MessageSquare className='h-5 w-5 text-gray-400' />
            </div>
            <div className='space-y-3'>
              {customerData.supportTickets.length > 0 ? (
                <div className='rounded-lg bg-gray-50 p-3'>
                  <div className='flex items-center justify-between'>
                    <span className='font-medium'>Recent Ticket</span>
                    <span
                      className={`text-sm capitalize ${getStatusColor(customerData.supportTickets[0].status)}`}
                    >
                      {customerData.supportTickets[0].status}
                    </span>
                  </div>
                  <p className='mt-1 text-gray-600 text-sm'>
                    {customerData.supportTickets[0].subject}
                  </p>
                </div>
              ) : (
                <p className='text-gray-500 text-sm'>No recent support tickets</p>
              )}

              <div className='grid grid-cols-2 gap-2 pt-3'>
                <button
                  type='button'
                  className='rounded bg-blue-600 px-3 py-2 text-sm text-white transition-colors hover:bg-blue-700'
                >
                  Pay Bill
                </button>
                <button
                  type='button'
                  className='rounded border border-gray-300 px-3 py-2 text-gray-700 text-sm transition-colors hover:bg-gray-50'
                >
                  Get Support
                </button>
                <button
                  type='button'
                  className='rounded border border-gray-300 px-3 py-2 text-gray-700 text-sm transition-colors hover:bg-gray-50'
                >
                  Upgrade Service
                </button>
                <button
                  type='button'
                  className='rounded border border-gray-300 px-3 py-2 text-gray-700 text-sm transition-colors hover:bg-gray-50'
                >
                  View Bills
                </button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </CustomerLayout>
  );
}
