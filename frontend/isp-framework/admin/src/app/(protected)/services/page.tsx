import { Suspense } from 'react';
import AdminLayout from '../../../components/layout/AdminLayout';
import { ServicesManagement } from '../../../components/services/ServicesManagement';
import type { ServiceType, ServiceStatus } from '../../../types/billing';

interface SearchParams {
  page?: string;
  search?: string;
  status?: string;
  category?: string;
  type?: string;
  pageSize?: string;
}

export default function ServicesPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Service Management</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Manage service plans, provisioning workflows, and lifecycle automation
            </p>
          </div>
          <div className='flex gap-3'>
            <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
              Create Service Plan
            </button>
            <button className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium'>
              Import Services
            </button>
          </div>
        </div>

        <Suspense
          key={JSON.stringify(searchParams)}
          fallback={
            <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
              <div className='lg:col-span-3 space-y-4'>
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
              <div className='space-y-4'>
                <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                  <div className='animate-pulse space-y-3'>
                    <div className='h-6 bg-gray-200 rounded'></div>
                    <div className='h-4 bg-gray-200 rounded w-3/4'></div>
                    <div className='h-4 bg-gray-200 rounded w-1/2'></div>
                  </div>
                </div>
              </div>
            </div>
          }
        >
          <ServicesContent searchParams={searchParams} />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

async function ServicesContent({ searchParams }: { searchParams: SearchParams }) {
  try {
    const data = await getServices(searchParams);

    return (
      <ServicesManagement
        services={data.services}
        categories={data.categories}
        workflows={data.workflows}
        totalCount={data.total}
        currentPage={Number(searchParams.page) || 1}
        pageSize={Number(searchParams.pageSize) || 20}
      />
    );
  } catch (error) {
    return (
      <div className='bg-white rounded-lg shadow p-6'>
        <div className='text-center'>
          <p className='text-red-600'>Failed to load services</p>
          <p className='text-sm text-gray-500 mt-2'>Please try refreshing the page</p>
        </div>
      </div>
    );
  }
}

// Enhanced mock function for services data
async function getServices(searchParams: SearchParams) {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 400));

  const page = Number(searchParams.page) || 1;
  const pageSize = Number(searchParams.pageSize) || 20;

  const mockServices = [
    {
      id: 'SVC-001',
      name: 'Fiber 100Mbps Residential',
      category: 'Internet',
      type: 'residential' as ServiceType,
      status: 'active' as ServiceStatus,
      description: 'High-speed fiber internet for residential customers',
      pricing: {
        monthly: 79.99,
        setup: 99.99,
        currency: 'USD',
      },
      specifications: {
        downloadSpeed: 100,
        uploadSpeed: 100,
        dataLimit: null,
        technology: 'Fiber Optic',
      },
      provisioning: {
        method: 'automated',
        estimatedTime: '24 hours',
        requiresTechnician: false,
      },
      availability: {
        regions: ['California', 'Texas', 'New York'],
        coverage: 85,
      },
      metrics: {
        activeSubscriptions: 1234,
        monthlyRevenue: 98666.66,
        customerSatisfaction: 4.6,
        churnRate: 2.1,
      },
      lifecycle: {
        createdAt: '2023-01-15T09:00:00Z',
        updatedAt: '2024-01-15T10:30:00Z',
        version: '1.2',
        deprecated: false,
      },
      dependencies: ['Network Infrastructure', 'ONT Device'],
      tags: ['popular', 'residential', 'fiber'],
    },
    {
      id: 'SVC-002',
      name: 'Business 500Mbps',
      category: 'Internet',
      type: 'business' as ServiceType,
      status: 'active' as ServiceStatus,
      description: 'Professional internet service with SLA guarantee',
      pricing: {
        monthly: 199.99,
        setup: 199.99,
        currency: 'USD',
      },
      specifications: {
        downloadSpeed: 500,
        uploadSpeed: 500,
        dataLimit: null,
        technology: 'Fiber Optic',
        sla: '99.9%',
      },
      provisioning: {
        method: 'manual',
        estimatedTime: '72 hours',
        requiresTechnician: true,
      },
      availability: {
        regions: ['California', 'Texas', 'New York', 'Florida'],
        coverage: 78,
      },
      metrics: {
        activeSubscriptions: 456,
        monthlyRevenue: 91194.44,
        customerSatisfaction: 4.8,
        churnRate: 1.3,
      },
      lifecycle: {
        createdAt: '2023-03-20T11:15:00Z',
        updatedAt: '2024-01-10T14:20:00Z',
        version: '2.1',
        deprecated: false,
      },
      dependencies: ['Network Infrastructure', 'Business ONT', 'SLA Monitoring'],
      tags: ['business', 'sla', 'priority'],
    },
    {
      id: 'SVC-003',
      name: 'Enterprise 1Gbps',
      category: 'Internet',
      type: 'enterprise' as ServiceType,
      status: 'active' as ServiceStatus,
      description: 'Enterprise-grade connectivity with dedicated support',
      pricing: {
        monthly: 499.99,
        setup: 499.99,
        currency: 'USD',
      },
      specifications: {
        downloadSpeed: 1000,
        uploadSpeed: 1000,
        dataLimit: null,
        technology: 'Dedicated Fiber',
        sla: '99.95%',
      },
      provisioning: {
        method: 'manual',
        estimatedTime: '5-7 days',
        requiresTechnician: true,
      },
      availability: {
        regions: ['California', 'Texas', 'New York'],
        coverage: 45,
      },
      metrics: {
        activeSubscriptions: 89,
        monthlyRevenue: 44499.11,
        customerSatisfaction: 4.9,
        churnRate: 0.8,
      },
      lifecycle: {
        createdAt: '2023-05-10T14:30:00Z',
        updatedAt: '2024-01-12T09:15:00Z',
        version: '1.0',
        deprecated: false,
      },
      dependencies: [
        'Dedicated Infrastructure',
        'Enterprise ONT',
        'SLA Monitoring',
        'Dedicated Support',
      ],
      tags: ['enterprise', 'dedicated', 'premium'],
    },
    {
      id: 'SVC-004',
      name: 'VoIP Business Phone',
      category: 'Voice',
      type: 'business' as ServiceType,
      status: 'active' as ServiceStatus,
      description: 'Cloud-based business phone system with advanced features',
      pricing: {
        monthly: 29.99,
        setup: 0,
        currency: 'USD',
      },
      specifications: {
        channels: 'Unlimited',
        features: ['Call forwarding', 'Voicemail', 'Conference', 'Auto-attendant'],
        technology: 'VoIP',
      },
      provisioning: {
        method: 'automated',
        estimatedTime: '2 hours',
        requiresTechnician: false,
      },
      availability: {
        regions: ['All Regions'],
        coverage: 100,
      },
      metrics: {
        activeSubscriptions: 678,
        monthlyRevenue: 20332.22,
        customerSatisfaction: 4.4,
        churnRate: 3.2,
      },
      lifecycle: {
        createdAt: '2023-08-05T08:45:00Z',
        updatedAt: '2024-01-08T16:30:00Z',
        version: '1.5',
        deprecated: false,
      },
      dependencies: ['VoIP Infrastructure', 'SIP Phones'],
      tags: ['voip', 'business', 'cloud'],
    },
    {
      id: 'SVC-005',
      name: 'Legacy DSL 25Mbps',
      category: 'Internet',
      type: 'residential',
      status: 'deprecated',
      description: 'Legacy DSL service - being phased out',
      pricing: {
        monthly: 39.99,
        setup: 49.99,
        currency: 'USD',
      },
      specifications: {
        downloadSpeed: 25,
        uploadSpeed: 3,
        dataLimit: 500,
        technology: 'DSL',
      },
      provisioning: {
        method: 'manual',
        estimatedTime: '48 hours',
        requiresTechnician: true,
      },
      availability: {
        regions: ['Rural Areas'],
        coverage: 15,
      },
      metrics: {
        activeSubscriptions: 234,
        monthlyRevenue: 9357.66,
        customerSatisfaction: 3.2,
        churnRate: 8.7,
      },
      lifecycle: {
        createdAt: '2022-01-01T00:00:00Z',
        updatedAt: '2023-12-15T10:00:00Z',
        version: '1.0',
        deprecated: true,
        deprecationDate: '2024-12-31T23:59:59Z',
      },
      dependencies: ['DSL Infrastructure', 'DSL Modem'],
      tags: ['legacy', 'deprecated', 'dsl'],
    },
  ];

  const categories = [
    {
      id: 'internet',
      name: 'Internet Services',
      count: mockServices.filter((s) => s.category === 'Internet').length,
    },
    {
      id: 'voice',
      name: 'Voice Services',
      count: mockServices.filter((s) => s.category === 'Voice').length,
    },
    { id: 'tv', name: 'TV Services', count: 0 },
    { id: 'security', name: 'Security Services', count: 0 },
  ];

  const workflows = [
    {
      id: 'WF-001',
      name: 'Standard Residential Provisioning',
      type: 'provisioning',
      status: 'active' as ServiceStatus,
      steps: [
        { id: 1, name: 'Customer Validation', automated: true, duration: '5 minutes' },
        { id: 2, name: 'Address Verification', automated: true, duration: '2 minutes' },
        { id: 3, name: 'Service Assignment', automated: true, duration: '1 minute' },
        { id: 4, name: 'Equipment Dispatch', automated: false, duration: '4-6 hours' },
        { id: 5, name: 'Installation Schedule', automated: false, duration: '24-48 hours' },
        { id: 6, name: 'Service Activation', automated: true, duration: '10 minutes' },
      ],
      metrics: {
        avgCompletionTime: '32 hours',
        successRate: 94.5,
        executionsLastMonth: 156,
      },
    },
    {
      id: 'WF-002',
      name: 'Business Service Provisioning',
      type: 'provisioning',
      status: 'active' as ServiceStatus,
      steps: [
        { id: 1, name: 'Business Validation', automated: true, duration: '10 minutes' },
        { id: 2, name: 'Credit Check', automated: true, duration: '15 minutes' },
        { id: 3, name: 'Site Survey Schedule', automated: false, duration: '24-48 hours' },
        { id: 4, name: 'Service Design', automated: false, duration: '2-3 days' },
        { id: 5, name: 'Equipment Procurement', automated: false, duration: '3-5 days' },
        { id: 6, name: 'Installation & Testing', automated: false, duration: '1-2 days' },
        { id: 7, name: 'Service Activation', automated: true, duration: '30 minutes' },
      ],
      metrics: {
        avgCompletionTime: '8.5 days',
        successRate: 91.2,
        executionsLastMonth: 45,
      },
    },
  ];

  // Apply filters
  let filtered = mockServices;

  if (searchParams.search) {
    const query = searchParams.search.toLowerCase();
    filtered = filtered.filter(
      (service) =>
        service.name.toLowerCase().includes(query) ||
        service.description.toLowerCase().includes(query) ||
        service.category.toLowerCase().includes(query) ||
        service.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  }

  if (searchParams.status) {
    filtered = filtered.filter((service) => service.status === searchParams.status);
  }

  if (searchParams.category) {
    filtered = filtered.filter(
      (service) => service.category.toLowerCase() === searchParams.category!.toLowerCase()
    );
  }

  if (searchParams.type) {
    filtered = filtered.filter((service) => service.type === searchParams.type);
  }

  // Pagination
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const services = filtered.slice(startIndex, endIndex);

  return {
    services,
    categories,
    workflows,
    total: filtered.length,
  };
}
