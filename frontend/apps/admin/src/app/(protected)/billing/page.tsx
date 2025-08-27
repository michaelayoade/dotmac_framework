import { Suspense } from 'react';
import AdminLayout from '../../../components/layout/AdminLayout';
import { BillingManagement } from '../../../components/billing/BillingManagement';
import type { InvoiceStatus, PaymentStatus, ReportStatus } from '../../../types/billing';

interface SearchParams {
  page?: string;
  search?: string;
  status?: string;
  type?: string;
  dateRange?: string;
  pageSize?: string;
  tab?: string;
}

export default function BillingPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Billing & Finance</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Comprehensive billing management, invoicing, payments, and financial reporting
            </p>
          </div>
          <div className='flex gap-3'>
            <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
              Generate Invoice
            </button>
            <button className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium'>
              Export Reports
            </button>
          </div>
        </div>

        <Suspense
          key={JSON.stringify(searchParams)}
          fallback={
            <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
              {/* Metrics Cards Skeleton */}
              <div className='lg:col-span-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
                {[...Array(4)].map((_, i) => (
                  <div key={i} className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                    <div className='animate-pulse'>
                      <div className='h-4 bg-gray-200 rounded w-3/4'></div>
                      <div className='h-8 bg-gray-200 rounded w-1/2 mt-2'></div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Main Content Skeleton */}
              <div className='lg:col-span-3 space-y-4'>
                <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                  <div className='animate-pulse space-y-4'>
                    <div className='h-6 bg-gray-200 rounded w-1/4'></div>
                    <div className='space-y-3'>
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className='h-16 bg-gray-200 rounded'></div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Sidebar Skeleton */}
              <div className='space-y-4'>
                <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                  <div className='animate-pulse space-y-3'>
                    <div className='h-6 bg-gray-200 rounded w-3/4'></div>
                    <div className='h-4 bg-gray-200 rounded w-1/2'></div>
                    <div className='h-4 bg-gray-200 rounded w-2/3'></div>
                  </div>
                </div>
              </div>
            </div>
          }
        >
          <BillingContent searchParams={searchParams} />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

async function BillingContent({ searchParams }: { searchParams: SearchParams }) {
  try {
    const data = await getBillingData(searchParams);

    return (
      <BillingManagement
        invoices={data.invoices}
        payments={data.payments}
        metrics={data.metrics}
        reports={data.reports}
        totalCount={data.total}
        currentPage={Number(searchParams.page) || 1}
        pageSize={Number(searchParams.pageSize) || 20}
        activeTab={searchParams.tab || 'invoices'}
      />
    );
  } catch (error) {
    return (
      <div className='bg-white rounded-lg shadow p-6'>
        <div className='text-center'>
          <p className='text-red-600'>Failed to load billing data</p>
          <p className='text-sm text-gray-500 mt-2'>Please try refreshing the page</p>
        </div>
      </div>
    );
  }
}

// Enhanced mock function for billing data
async function getBillingData(searchParams: SearchParams) {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 300));

  const page = Number(searchParams.page) || 1;
  const pageSize = Number(searchParams.pageSize) || 20;

  const mockInvoices = [
    {
      id: 'INV-2024-001',
      customerId: 'CUST-001',
      customerName: 'John Doe',
      customerEmail: 'john.doe@example.com',
      customerType: 'residential',
      serviceAddress: '123 Maple St, Seattle, WA 98101',
      amount: 79.99,
      tax: 7.2,
      total: 87.19,
      currency: 'USD',
      status: 'paid' as InvoiceStatus,
      dueDate: '2024-02-15T00:00:00Z',
      paidDate: '2024-02-10T14:30:00Z',
      paymentMethod: 'credit_card',
      services: [
        {
          name: 'DotMac Fiber 100/100',
          amount: 79.99,
          type: 'internet',
          speed: { download: 100, upload: 100 },
          technology: 'fiber',
        },
      ],
      billingPeriod: {
        start: '2024-02-01T00:00:00Z',
        end: '2024-02-29T23:59:59Z',
      },
      createdAt: '2024-01-31T00:00:00Z',
      updatedAt: '2024-02-10T14:30:00Z',
      tags: ['recurring', 'auto-pay', 'fiber', 'residential'],
      territory: 'Seattle Central',
      technician: 'TECH-001',
    },
    {
      id: 'INV-2024-002',
      customerId: 'CUST-002',
      customerName: 'TechCorp Solutions',
      customerEmail: 'billing@techcorp.com',
      customerType: 'business',
      serviceAddress: '789 Business Park Dr, Bellevue, WA 98004',
      amount: 299.99,
      tax: 27.0,
      total: 326.99,
      currency: 'USD',
      status: 'overdue' as InvoiceStatus,
      dueDate: '2024-02-15T00:00:00Z',
      paidDate: null,
      paymentMethod: 'bank_transfer',
      services: [
        {
          name: 'DotMac Business Pro 500/500',
          amount: 249.99,
          type: 'internet',
          speed: { download: 500, upload: 500 },
          technology: 'fiber',
          sla: '99.9%',
        },
        {
          name: 'Static IP Block (/29)',
          amount: 50.0,
          type: 'add-on',
          details: '5 usable IPs',
        },
      ],
      billingPeriod: {
        start: '2024-02-01T00:00:00Z',
        end: '2024-02-29T23:59:59Z',
      },
      createdAt: '2024-01-31T00:00:00Z',
      updatedAt: '2024-02-16T09:00:00Z',
      tags: ['business', 'overdue', 'fiber', 'static-ip'],
      territory: 'Eastside',
      technician: 'TECH-002',
      contractTerm: 24,
      escalationLevel: 1,
    },
    {
      id: 'INV-2024-003',
      customerId: 'CUST-003',
      customerName: 'Seattle Data Center LLC',
      customerEmail: 'ops@seattledc.com',
      customerType: 'enterprise',
      serviceAddress: '100 Enterprise Way, Seattle, WA 98109',
      amount: 1499.99,
      tax: 135.0,
      total: 1634.99,
      currency: 'USD',
      status: 'pending' as InvoiceStatus,
      dueDate: '2024-03-15T00:00:00Z',
      paidDate: null,
      paymentMethod: 'wire_transfer',
      services: [
        {
          name: 'DotMac Enterprise Dedicated 10Gbps',
          amount: 1299.99,
          type: 'internet',
          speed: { download: 10000, upload: 10000 },
          technology: 'dedicated_fiber',
          sla: '99.99%',
        },
        {
          name: 'BGP Routing (/24)',
          amount: 150.0,
          type: 'add-on',
          details: 'Full BGP table, AS number included',
        },
        {
          name: '24/7 NOC Monitoring',
          amount: 50.0,
          type: 'support',
          details: 'Proactive monitoring and alerts',
        },
      ],
      billingPeriod: {
        start: '2024-03-01T00:00:00Z',
        end: '2024-03-31T23:59:59Z',
      },
      createdAt: '2024-02-29T00:00:00Z',
      updatedAt: '2024-02-29T00:00:00Z',
      tags: ['enterprise', 'new', 'dedicated', 'bgp', '24x7'],
      territory: 'Downtown',
      technician: 'TECH-003',
      contractTerm: 36,
      accountManager: 'AM-001',
    },
    {
      id: 'INV-2024-004',
      customerId: 'CUST-004',
      customerName: 'Sarah Wilson',
      customerEmail: 'sarah.wilson@gmail.com',
      customerType: 'residential',
      serviceAddress: '456 Pine Ave, Redmond, WA 98052',
      amount: 49.99,
      tax: 4.5,
      total: 54.49,
      currency: 'USD',
      status: 'paid' as InvoiceStatus,
      dueDate: '2024-02-20T00:00:00Z',
      paidDate: '2024-02-18T16:20:00Z',
      paymentMethod: 'auto_pay',
      services: [
        {
          name: 'DotMac Essential 50/10',
          amount: 49.99,
          type: 'internet',
          speed: { download: 50, upload: 10 },
          technology: 'cable',
        },
      ],
      billingPeriod: {
        start: '2024-02-01T00:00:00Z',
        end: '2024-02-29T23:59:59Z',
      },
      createdAt: '2024-01-31T00:00:00Z',
      updatedAt: '2024-02-18T16:20:00Z',
      tags: ['recurring', 'auto-pay', 'cable', 'residential'],
      territory: 'Eastside',
      technician: 'TECH-002',
    },
    {
      id: 'INV-2024-005',
      customerId: 'CUST-005',
      customerName: 'Green Valley Apartments',
      customerEmail: 'management@gvapts.com',
      customerType: 'bulk',
      serviceAddress: '200 Valley View Ln, Kirkland, WA 98033',
      amount: 2499.99,
      tax: 225.0,
      total: 2724.99,
      currency: 'USD',
      status: 'paid' as InvoiceStatus,
      dueDate: '2024-02-05T00:00:00Z',
      paidDate: '2024-02-03T10:15:00Z',
      paymentMethod: 'ach',
      services: [
        {
          name: 'DotMac Bulk Internet Service',
          amount: 2199.99,
          type: 'internet',
          speed: { download: 1000, upload: 1000 },
          technology: 'fiber',
          units: 48,
          perUnit: 45.83,
        },
        {
          name: 'Property WiFi Management',
          amount: 300.0,
          type: 'managed_wifi',
          details: 'Common area WiFi and guest network',
        },
      ],
      billingPeriod: {
        start: '2024-02-01T00:00:00Z',
        end: '2024-02-29T23:59:59Z',
      },
      createdAt: '2024-01-31T00:00:00Z',
      updatedAt: '2024-02-03T10:15:00Z',
      tags: ['bulk', 'multifamily', 'fiber', 'managed-wifi'],
      territory: 'Eastside',
      technician: 'TECH-004',
      propertyManager: 'PM-001',
      unitCount: 48,
    },
  ];

  const mockPayments = [
    {
      id: 'PAY-2024-001',
      invoiceId: 'INV-2024-001',
      customerId: 'CUST-001',
      customerName: 'John Doe',
      amount: 87.19,
      currency: 'USD',
      method: 'credit_card',
      status: 'completed' as PaymentStatus,
      transactionId: 'txn_1OkjHn2eZvKYlo2C1XkQOVWT',
      gateway: 'stripe',
      processedAt: '2024-02-10T14:30:00Z',
      fees: {
        processing: 2.53,
        gateway: 0.3,
      },
      metadata: {
        last4: '4242',
        brand: 'visa',
      },
    },
    {
      id: 'PAY-2024-002',
      invoiceId: null,
      customerId: 'CUST-004',
      customerName: 'Sarah Wilson',
      amount: 99.99,
      currency: 'USD',
      method: 'bank_transfer',
      status: 'pending' as PaymentStatus,
      transactionId: 'ach_1OkjHn2eZvKYlo2C1XkQOVWT',
      gateway: 'stripe',
      processedAt: null,
      fees: {
        processing: 0.8,
        gateway: 0.0,
      },
      metadata: {
        bank_name: 'Chase Bank',
        account_last4: '1234',
      },
    },
  ];

  const metrics = {
    totalRevenue: 2456789.45,
    monthlyRecurring: 234567.89,
    outstandingAmount: 45678.9,
    collectionsRate: 94.2,
    averageInvoiceValue: 156.78,
    paymentFailureRate: 3.4,
    trends: {
      revenue: 8.5,
      collections: -2.1,
      failures: 0.8,
    },
    chartData: {
      revenue: [
        { month: 'Jan', amount: 185432 },
        { month: 'Feb', amount: 198765 },
        { month: 'Mar', amount: 212340 },
        { month: 'Apr', amount: 225670 },
        { month: 'May', amount: 234568 },
        { month: 'Jun', amount: 245679 },
      ],
      collections: [
        { month: 'Jan', rate: 96.2 },
        { month: 'Feb', rate: 94.8 },
        { month: 'Mar', rate: 95.1 },
        { month: 'Apr', rate: 93.9 },
        { month: 'May', rate: 94.2 },
        { month: 'Jun', rate: 94.2 },
      ],
      paymentMethods: [
        { method: 'Credit Card', percentage: 65, amount: 1596113.14 },
        { method: 'Bank Transfer', percentage: 25, amount: 614197.36 },
        { method: 'PayPal', percentage: 8, amount: 196543.16 },
        { method: 'Other', percentage: 2, amount: 49135.79 },
      ],
    },
  };

  const reports = [
    {
      id: 'RPT-001',
      name: 'Monthly Revenue Report',
      type: 'revenue',
      description:
        'Comprehensive revenue analysis with breakdowns by service, customer segment, and region',
      lastGenerated: '2024-02-01T09:00:00Z',
      frequency: 'monthly',
      status: 'ready' as ReportStatus,
      format: 'PDF',
      size: '2.4 MB',
    },
    {
      id: 'RPT-002',
      name: 'Aging Report',
      type: 'collections',
      description: 'Outstanding invoices categorized by age for collections management',
      lastGenerated: '2024-02-15T15:30:00Z',
      frequency: 'weekly',
      status: 'ready' as ReportStatus,
      format: 'Excel',
      size: '1.8 MB',
    },
    {
      id: 'RPT-003',
      name: 'Payment Processing Summary',
      type: 'payments',
      description: 'Payment gateway performance, fees, and failure rate analysis',
      lastGenerated: '2024-02-10T12:00:00Z',
      frequency: 'daily',
      status: 'generating' as ReportStatus,
      format: 'PDF',
      size: null,
    },
  ];

  // Apply filters
  let filteredInvoices = mockInvoices;

  if (searchParams.search) {
    const query = searchParams.search.toLowerCase();
    filteredInvoices = filteredInvoices.filter(
      (invoice) =>
        invoice.id.toLowerCase().includes(query) ||
        invoice.customerName.toLowerCase().includes(query) ||
        invoice.customerEmail.toLowerCase().includes(query)
    );
  }

  if (searchParams.status) {
    filteredInvoices = filteredInvoices.filter((invoice) => invoice.status === searchParams.status);
  }

  // Pagination
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const invoices = filteredInvoices.slice(startIndex, endIndex);

  return {
    invoices,
    payments: mockPayments,
    metrics,
    reports,
    total: filteredInvoices.length,
  };
}
