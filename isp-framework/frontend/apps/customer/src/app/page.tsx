'use client';

import { Suspense } from 'react';
import { CustomerDashboard } from '../components/dashboard/CustomerDashboard';
import { CustomerLayout } from '../components/layout/CustomerLayout';

// Mock customer data for demonstration
const mockCustomerData = {
  account: {
    id: 'CUST-12345',
    name: 'John Doe',
    email: 'john.doe@example.com',
    phone: '+1 (555) 123-4567',
    accountStatus: 'active' as const,
    joinDate: '2023-01-15T00:00:00Z',
    billingAddress: {
      street: '123 Main St',
      city: 'Seattle',
      state: 'WA',
      zipCode: '98101',
      country: 'US',
    },
  },
  services: [
    {
      id: 'SVC-001',
      name: 'Fiber Internet 500Mbps',
      status: 'active',
      speed: { download: 500, upload: 500 },
      monthlyRate: 79.99,
      installDate: '2023-01-20T00:00:00Z',
      nextBillingDate: '2024-03-01T00:00:00Z',
    },
  ],
  billing: {
    currentBalance: 79.99,
    nextPaymentDate: '2024-03-01T00:00:00Z',
    paymentMethod: 'Credit Card ending in 4242',
    recentInvoices: [
      {
        id: 'INV-202402',
        amount: 79.99,
        dueDate: '2024-02-01T00:00:00Z',
        status: 'paid',
      },
    ],
  },
  usage: {
    currentMonth: {
      download: 245.7, // GB
      upload: 58.3, // GB
      updated: '2024-02-20T14:30:00Z',
    },
    speedTest: {
      download: 487.3, // Mbps
      upload: 493.1, // Mbps
      ping: 12, // ms
      timestamp: '2024-02-20T09:15:00Z',
    },
  },
  support: {
    openTickets: 0,
    recentTickets: [],
  },
};

export default function CustomerHomePage() {
  return (
    <CustomerLayout>
      <div className='space-y-6'>
        {/* Welcome Header */}
        <div className='bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg p-6'>
          <h1 className='text-2xl font-bold mb-2'>
            Welcome back, {mockCustomerData.account.name}!
          </h1>
          <p className='text-blue-100'>Manage your DotMac internet service and account settings</p>
        </div>

        {/* Dashboard Content */}
        <Suspense
          fallback={
            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
              {/* Loading skeleton */}
              {[...Array(6)].map((_, i) => (
                <div key={i} className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                  <div className='animate-pulse'>
                    <div className='h-4 bg-gray-200 rounded w-3/4 mb-2'></div>
                    <div className='h-8 bg-gray-200 rounded w-1/2'></div>
                  </div>
                </div>
              ))}
            </div>
          }
        >
          <CustomerDashboard data={mockCustomerData} />
        </Suspense>
      </div>
    </CustomerLayout>
  );
}
