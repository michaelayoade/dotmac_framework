'use client';

import { Suspense, useState } from 'react';
import { AdminLayout } from '../../../components/layout/AdminLayout';
import { CustomersTable } from '../../../components/customers/CustomersTable';
import { AddCustomerButton } from '../../../components/customers/AddCustomerButton';
import { CustomerDensityHeatmap } from '@dotmac/mapping';

interface SearchParams {
  page?: string;
  search?: string;
  status?: string;
  planType?: string;
  paymentStatus?: string;
  pageSize?: string;
}

// Mock customer data with geographic coordinates for mapping
const mockMappedCustomers = [
  {
    id: 'CUST-001',
    name: 'John Doe',
    coordinates: { latitude: 47.6062, longitude: -122.3321 },
    serviceType: 'residential' as const,
    plan: 'Fiber 100Mbps',
    speed: 100,
    monthlyRevenue: 79.99,
    installDate: new Date('2023-06-15'),
    status: 'active' as const,
    satisfaction: 8.5,
  },
  {
    id: 'CUST-002',
    name: 'Jane Smith',
    coordinates: { latitude: 47.6205, longitude: -122.3212 },
    serviceType: 'business' as const,
    plan: 'Business 500Mbps',
    speed: 500,
    monthlyRevenue: 199.99,
    installDate: new Date('2023-08-20'),
    status: 'active' as const,
    satisfaction: 9.2,
  },
  {
    id: 'CUST-003',
    name: 'Michael Johnson',
    coordinates: { latitude: 47.6101, longitude: -122.2015 },
    serviceType: 'enterprise' as const,
    plan: 'Enterprise 1Gbps',
    speed: 1000,
    monthlyRevenue: 499.99,
    installDate: new Date('2023-03-10'),
    status: 'suspended' as const,
    satisfaction: 6.5,
  },
  {
    id: 'CUST-004',
    name: 'Sarah Wilson',
    coordinates: { latitude: 47.637, longitude: -122.3572 },
    serviceType: 'residential' as const,
    plan: 'Fiber 200Mbps',
    speed: 200,
    monthlyRevenue: 99.99,
    installDate: new Date('2024-01-18'),
    status: 'active' as const,
    satisfaction: 7.8,
  },
  {
    id: 'CUST-005',
    name: 'Robert Garcia',
    coordinates: { latitude: 47.6512, longitude: -122.3501 },
    serviceType: 'residential' as const,
    plan: 'Basic 50Mbps',
    speed: 50,
    monthlyRevenue: 49.99,
    installDate: new Date('2023-01-05'),
    status: 'inactive' as const,
    satisfaction: 5.2,
  },
  {
    id: 'CUST-006',
    name: 'Emily Chen',
    coordinates: { latitude: 47.674, longitude: -122.1215 },
    serviceType: 'business' as const,
    plan: 'Business 1Gbps',
    speed: 1000,
    monthlyRevenue: 299.99,
    installDate: new Date('2023-09-12'),
    status: 'active' as const,
    satisfaction: 8.9,
  },
];

// Server Component - data fetching happens on the server
export default function CustomersPage() {
  const [activeView, setActiveView] = useState<'table' | 'map'>('table');
  const [searchParams, setSearchParams] = useState<SearchParams>({});

  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Customer Management</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Comprehensive customer management with advanced filtering and analytics
            </p>
          </div>
          <div className='flex gap-3'>
            <div className='flex bg-gray-100 rounded-lg p-1'>
              <button
                onClick={() => setActiveView('table')}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeView === 'table'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                📊 Table View
              </button>
              <button
                onClick={() => setActiveView('map')}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeView === 'map'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                🗺️ Geographic View
              </button>
            </div>
            <AddCustomerButton />
            <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
              Import Customers
            </button>
          </div>
        </div>

        {activeView === 'map' ? (
          <div className='bg-white rounded-lg shadow'>
            <div className='p-6 border-b border-gray-200'>
              <h2 className='text-lg font-semibold text-gray-900'>
                Customer Geographic Distribution
              </h2>
              <p className='text-sm text-gray-600 mt-1'>
                Analyze customer density, revenue distribution, and satisfaction patterns across
                service areas
              </p>
            </div>
            <div className='h-[600px] bg-gray-50'>
              <CustomerDensityHeatmap
                customers={mockMappedCustomers}
                heatmapType='density'
                gridSize={0.01}
                className='h-full'
                config={{
                  defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
                  defaultZoom: 11,
                }}
              />
            </div>
            <div className='p-4 bg-gray-50 border-t border-gray-200'>
              <div className='grid grid-cols-1 md:grid-cols-4 gap-4 text-sm'>
                <div className='text-center'>
                  <div className='font-semibold text-blue-600'>{mockMappedCustomers.length}</div>
                  <div className='text-gray-600'>Total Customers</div>
                </div>
                <div className='text-center'>
                  <div className='font-semibold text-green-600'>
                    {mockMappedCustomers.filter((c) => c.status === 'active').length}
                  </div>
                  <div className='text-gray-600'>Active Customers</div>
                </div>
                <div className='text-center'>
                  <div className='font-semibold text-purple-600'>
                    ${mockMappedCustomers.reduce((sum, c) => sum + c.monthlyRevenue, 0).toFixed(0)}
                  </div>
                  <div className='text-gray-600'>Monthly Revenue</div>
                </div>
                <div className='text-center'>
                  <div className='font-semibold text-yellow-600'>
                    {(
                      mockMappedCustomers.reduce((sum, c) => sum + (c.satisfaction || 0), 0) /
                      mockMappedCustomers.length
                    ).toFixed(1)}
                  </div>
                  <div className='text-gray-600'>Avg Satisfaction</div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Suspense
            key={JSON.stringify(searchParams)}
            fallback={
              <div className='space-y-4'>
                <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                  <div className='animate-pulse space-y-4'>
                    <div className='h-10 bg-gray-200 rounded'></div>
                    <div className='h-8 bg-gray-200 rounded w-1/3'></div>
                  </div>
                </div>
                <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
                  <div className='animate-pulse p-6'>
                    <div className='space-y-3'>
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className='h-16 bg-gray-200 rounded'></div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            }
          >
            <CustomersDataTable searchParams={searchParams} />
          </Suspense>
        )}
      </div>
    </AdminLayout>
  );
}

// Async component for data fetching
async function CustomersDataTable({ searchParams }: { searchParams: SearchParams }) {
  try {
    const data = await getCustomers(searchParams);

    return (
      <CustomersTable
        customers={data.customers}
        totalCount={data.total}
        currentPage={Number(searchParams.page) || 1}
        pageSize={Number(searchParams.pageSize) || 20}
      />
    );
  } catch (error) {
    return (
      <div className='bg-white rounded-lg shadow p-6'>
        <div className='text-center'>
          <p className='text-red-600'>Failed to load customers</p>
          <p className='text-sm text-gray-500 mt-2'>Please try refreshing the page</p>
        </div>
      </div>
    );
  }
}

// Enhanced mock function with comprehensive customer data
async function getCustomers(searchParams: SearchParams) {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 300));

  const page = Number(searchParams.page) || 1;
  const pageSize = Number(searchParams.pageSize) || 20;

  const mockCustomers = [
    {
      id: 'CUST-001',
      name: 'John Doe',
      email: 'john.doe@example.com',
      phone: '+1 (555) 123-4567',
      status: 'active' as const,
      plan: 'Fiber 100Mbps',
      planType: 'residential' as const,
      monthlyRevenue: 79.99,
      address: {
        street: '123 Main St',
        city: 'San Francisco',
        state: 'CA',
        zip: '94105',
      },
      lastLogin: '2024-01-15T10:30:00Z',
      dataUsage: {
        current: 250,
        limit: 1000,
        unit: 'GB' as const,
      },
      paymentStatus: 'current' as const,
      tags: ['premium', 'referral'],
      createdAt: '2023-06-15T09:00:00Z',
      updatedAt: '2024-01-15T10:30:00Z',
    },
    {
      id: 'CUST-002',
      name: 'Jane Smith',
      email: 'jane.smith@businesscorp.com',
      phone: '+1 (555) 234-5678',
      status: 'active' as const,
      plan: 'Business 500Mbps',
      planType: 'business' as const,
      monthlyRevenue: 199.99,
      address: {
        street: '456 Oak Avenue',
        city: 'Austin',
        state: 'TX',
        zip: '73301',
      },
      lastLogin: '2024-01-14T15:45:00Z',
      dataUsage: {
        current: 800,
        limit: 5000,
        unit: 'GB' as const,
      },
      paymentStatus: 'current' as const,
      tags: ['business', 'high-value'],
      createdAt: '2023-08-20T11:15:00Z',
      updatedAt: '2024-01-14T15:45:00Z',
    },
    {
      id: 'CUST-003',
      name: 'Michael Johnson',
      email: 'michael.j@startup.io',
      phone: '+1 (555) 345-6789',
      status: 'suspended' as const,
      plan: 'Enterprise 1Gbps',
      planType: 'enterprise' as const,
      monthlyRevenue: 499.99,
      address: {
        street: '789 Tech Blvd',
        city: 'Seattle',
        state: 'WA',
        zip: '98101',
      },
      lastLogin: '2024-01-10T08:20:00Z',
      dataUsage: {
        current: 2.5,
        limit: 10,
        unit: 'TB' as const,
      },
      paymentStatus: 'overdue' as const,
      tags: ['enterprise', 'suspended'],
      createdAt: '2023-03-10T14:30:00Z',
      updatedAt: '2024-01-12T09:15:00Z',
    },
    {
      id: 'CUST-004',
      name: 'Sarah Wilson',
      email: 'sarah.wilson@email.com',
      phone: '+1 (555) 456-7890',
      status: 'pending' as const,
      plan: 'Fiber 200Mbps',
      planType: 'residential' as const,
      monthlyRevenue: 99.99,
      address: {
        street: '321 Elm Street',
        city: 'Denver',
        state: 'CO',
        zip: '80202',
      },
      lastLogin: null,
      dataUsage: {
        current: 0,
        limit: 2000,
        unit: 'GB' as const,
      },
      paymentStatus: 'pending' as const,
      tags: ['new-customer'],
      createdAt: '2024-01-18T16:00:00Z',
      updatedAt: '2024-01-18T16:00:00Z',
    },
    {
      id: 'CUST-005',
      name: 'Robert Garcia',
      coordinates: { latitude: 47.6512, longitude: -122.3501 },
      email: 'robert.garcia@family.com',
      phone: '+1 (555) 567-8901',
      status: 'inactive' as const,
      plan: 'Basic 50Mbps',
      planType: 'residential' as const,
      monthlyRevenue: 49.99,
      address: {
        street: '654 Pine Road',
        city: 'Phoenix',
        state: 'AZ',
        zip: '85001',
      },
      lastLogin: '2023-12-20T12:00:00Z',
      dataUsage: {
        current: 150,
        limit: 500,
        unit: 'GB' as const,
      },
      paymentStatus: 'current' as const,
      tags: ['family-plan'],
      createdAt: '2023-01-05T10:45:00Z',
      updatedAt: '2023-12-20T12:00:00Z',
    },
    {
      id: 'CUST-006',
      name: 'Emily Chen',
      email: 'emily.chen@techstart.com',
      phone: '+1 (555) 678-9012',
      status: 'active' as const,
      plan: 'Business 1Gbps',
      planType: 'business' as const,
      monthlyRevenue: 299.99,
      address: {
        street: '987 Innovation Way',
        city: 'San Jose',
        state: 'CA',
        zip: '95110',
      },
      lastLogin: '2024-01-16T09:30:00Z',
      dataUsage: {
        current: 1.2,
        limit: 5,
        unit: 'TB' as const,
      },
      paymentStatus: 'current' as const,
      tags: ['business', 'tech'],
      createdAt: '2023-09-12T13:20:00Z',
      updatedAt: '2024-01-16T09:30:00Z',
    },
  ];

  // Apply filters based on search parameters
  let filtered = mockCustomers;

  if (searchParams.search) {
    const query = searchParams.search.toLowerCase();
    filtered = filtered.filter(
      (customer) =>
        customer.name.toLowerCase().includes(query) ||
        customer.email.toLowerCase().includes(query) ||
        customer.phone.includes(query) ||
        customer.id.toLowerCase().includes(query) ||
        customer.address.city.toLowerCase().includes(query)
    );
  }

  if (searchParams.status) {
    filtered = filtered.filter((customer) => customer.status === searchParams.status);
  }

  if (searchParams.planType) {
    filtered = filtered.filter((customer) => customer.planType === searchParams.planType);
  }

  if (searchParams.paymentStatus) {
    filtered = filtered.filter((customer) => customer.paymentStatus === searchParams.paymentStatus);
  }

  // Pagination
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const customers = filtered.slice(startIndex, endIndex);

  return {
    customers,
    total: filtered.length,
  };
}
