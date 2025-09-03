import { Suspense } from 'react';
import AdminLayout from '../../../components/layout/AdminLayout';
import { SupportManagement } from '../../../components/support/SupportManagement';
import type { TicketStatus } from '../../../types/billing';

interface SearchParams {
  page?: string;
  search?: string;
  status?: string;
  priority?: string;
  assignee?: string;
  category?: string;
  pageSize?: string;
  view?: string;
}

export default function SupportPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Support & Ticketing</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Comprehensive customer support management with automation and real-time collaboration
            </p>
          </div>
          <div className='flex gap-3'>
            <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
              Create Ticket
            </button>
            <button className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium'>
              Knowledge Base
            </button>
          </div>
        </div>

        <Suspense
          key={JSON.stringify(searchParams)}
          fallback={
            <div className='space-y-6'>
              {/* Metrics Skeleton */}
              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
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
              <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
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
            </div>
          }
        >
          <SupportContent searchParams={searchParams} />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

async function SupportContent({ searchParams }: { searchParams: SearchParams }) {
  try {
    const data = await getSupportData(searchParams);

    return (
      <SupportManagement
        tickets={data.tickets}
        agents={data.agents}
        metrics={data.metrics}
        categories={data.categories}
        automations={data.automations}
        totalCount={data.total}
        currentPage={Number(searchParams.page) || 1}
        pageSize={Number(searchParams.pageSize) || 20}
        currentView={searchParams.view || 'list'}
      />
    );
  } catch (error) {
    return (
      <div className='bg-white rounded-lg shadow p-6'>
        <div className='text-center'>
          <p className='text-red-600'>Failed to load support data</p>
          <p className='text-sm text-gray-500 mt-2'>Please try refreshing the page</p>
        </div>
      </div>
    );
  }
}

// Enhanced mock function for support data
async function getSupportData(searchParams: SearchParams) {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 400));

  const page = Number(searchParams.page) || 1;
  const pageSize = Number(searchParams.pageSize) || 20;

  const mockTickets = [
    {
      id: 'TKT-2024-001',
      title: 'Internet connection dropping frequently',
      description:
        'Customer reports frequent internet disconnections, especially during peak hours',
      customerId: 'CUST-001',
      customerName: 'John Doe',
      customerEmail: 'john.doe@example.com',
      status: 'open' as TicketStatus,
      priority: 'high',
      category: 'connectivity',
      assigneeId: 'AGT-001',
      assigneeName: 'Sarah Wilson',
      createdAt: '2024-02-15T09:30:00Z',
      updatedAt: '2024-02-15T14:20:00Z',
      resolvedAt: null,
      firstResponseAt: '2024-02-15T10:15:00Z',
      tags: ['connectivity', 'frequent-issue'],
      channel: 'web',
      interactions: [
        {
          id: '1',
          type: 'note',
          author: 'Sarah Wilson',
          content:
            'Customer contacted regarding frequent disconnections. Initial troubleshooting suggests possible equipment issue.',
          timestamp: '2024-02-15T10:15:00Z',
          internal: false,
        },
        {
          id: '2',
          type: 'note',
          author: 'Tech Support',
          content: 'Scheduled technician visit for tomorrow 2-4 PM to replace ONT device.',
          timestamp: '2024-02-15T14:20:00Z',
          internal: true,
        },
      ],
      sla: {
        firstResponseTime: 45, // minutes
        resolutionTime: 240,
        breached: false,
      },
      satisfaction: null,
    },
    {
      id: 'TKT-2024-002',
      title: 'Billing discrepancy on latest invoice',
      description: 'Customer questions charges on invoice INV-2024-002',
      customerId: 'CUST-002',
      customerName: 'Jane Smith',
      customerEmail: 'jane.smith@businesscorp.com',
      status: 'in_progress' as TicketStatus,
      priority: 'medium',
      category: 'billing',
      assigneeId: 'AGT-002',
      assigneeName: 'Mike Johnson',
      createdAt: '2024-02-14T16:45:00Z',
      updatedAt: '2024-02-15T11:30:00Z',
      resolvedAt: null,
      firstResponseAt: '2024-02-14T17:30:00Z',
      tags: ['billing', 'invoice-query'],
      channel: 'phone',
      interactions: [
        {
          id: '1',
          type: 'note',
          author: 'Mike Johnson',
          content:
            'Customer called about billing discrepancy. Reviewing invoice charges and usage records.',
          timestamp: '2024-02-14T17:30:00Z',
          internal: false,
        },
        {
          id: '2',
          type: 'note',
          author: 'Mike Johnson',
          content: 'Found issue with pro-rated charges. Preparing credit note for $45.67',
          timestamp: '2024-02-15T11:30:00Z',
          internal: true,
        },
      ],
      sla: {
        firstResponseTime: 45,
        resolutionTime: 180,
        breached: false,
      },
      satisfaction: null,
    },
    {
      id: 'TKT-2024-003',
      title: 'Service upgrade request',
      description: 'Customer wants to upgrade from 100Mbps to 500Mbps plan',
      customerId: 'CUST-004',
      customerName: 'Sarah Wilson',
      customerEmail: 'sarah.wilson@email.com',
      status: 'resolved' as TicketStatus,
      priority: 'low',
      category: 'service_change',
      assigneeId: 'AGT-003',
      assigneeName: 'Alex Chen',
      createdAt: '2024-02-12T10:00:00Z',
      updatedAt: '2024-02-13T15:45:00Z',
      resolvedAt: '2024-02-13T15:45:00Z',
      firstResponseAt: '2024-02-12T10:30:00Z',
      tags: ['upgrade', 'plan-change'],
      channel: 'email',
      interactions: [
        {
          id: '1',
          type: 'note',
          author: 'Alex Chen',
          content: 'Service upgrade processed. New plan effective from next billing cycle.',
          timestamp: '2024-02-13T15:45:00Z',
          internal: false,
        },
      ],
      sla: {
        firstResponseTime: 30,
        resolutionTime: 120,
        breached: false,
      },
      satisfaction: {
        rating: 5,
        feedback: 'Great service, very quick resolution!',
      },
    },
    {
      id: 'TKT-2024-004',
      title: 'Equipment return process',
      description: 'Customer cancelled service and needs to return equipment',
      customerId: 'CUST-005',
      customerName: 'Robert Garcia',
      customerEmail: 'robert.garcia@family.com',
      status: 'pending' as TicketStatus,
      priority: 'low',
      category: 'equipment',
      assigneeId: null,
      assigneeName: null,
      createdAt: '2024-02-16T08:15:00Z',
      updatedAt: '2024-02-16T08:15:00Z',
      resolvedAt: null,
      firstResponseAt: null,
      tags: ['equipment', 'cancellation'],
      channel: 'web',
      interactions: [],
      sla: {
        firstResponseTime: 60,
        resolutionTime: 240,
        breached: false,
      },
      satisfaction: null,
    },
  ];

  const mockAgents = [
    {
      id: 'AGT-001',
      name: 'Sarah Wilson',
      email: 'sarah.wilson@company.com',
      role: 'Senior Support Agent',
      status: 'online',
      currentLoad: 8,
      maxLoad: 10,
      skills: ['technical', 'billing', 'escalation'],
      metrics: {
        avgFirstResponse: 25, // minutes
        avgResolutionTime: 180, // minutes
        customerSatisfaction: 4.8,
        ticketsResolved: 156,
        ticketsAssigned: 8,
      },
    },
    {
      id: 'AGT-002',
      name: 'Mike Johnson',
      email: 'mike.johnson@company.com',
      role: 'Support Agent',
      status: 'online',
      currentLoad: 6,
      maxLoad: 8,
      skills: ['billing', 'general'],
      metrics: {
        avgFirstResponse: 35,
        avgResolutionTime: 220,
        customerSatisfaction: 4.6,
        ticketsResolved: 98,
        ticketsAssigned: 6,
      },
    },
    {
      id: 'AGT-003',
      name: 'Alex Chen',
      email: 'alex.chen@company.com',
      role: 'Technical Support',
      status: 'away',
      currentLoad: 4,
      maxLoad: 10,
      skills: ['technical', 'network', 'escalation'],
      metrics: {
        avgFirstResponse: 20,
        avgResolutionTime: 150,
        customerSatisfaction: 4.9,
        ticketsResolved: 234,
        ticketsAssigned: 4,
      },
    },
  ];

  const metrics = {
    totalTickets: 1543,
    openTickets: 45,
    overdueTickets: 8,
    avgFirstResponse: 28, // minutes
    avgResolutionTime: 185, // minutes
    customerSatisfaction: 4.7,
    slaCompliance: 92.3,
    ticketVolume: {
      today: 23,
      thisWeek: 156,
      thisMonth: 678,
    },
    trends: {
      tickets: 5.2,
      satisfaction: -0.3,
      resolution: -8.5,
      sla: 2.1,
    },
    channelDistribution: [
      { channel: 'Web', count: 45, percentage: 42 },
      { channel: 'Email', count: 32, percentage: 30 },
      { channel: 'Phone', count: 24, percentage: 22 },
      { channel: 'Chat', count: 6, percentage: 6 },
    ],
    categoryBreakdown: [
      { category: 'Technical', count: 28, percentage: 35 },
      { category: 'Billing', count: 22, percentage: 28 },
      { category: 'General', count: 18, percentage: 22 },
      { category: 'Sales', count: 12, percentage: 15 },
    ],
  };

  const categories = [
    { id: 'connectivity', name: 'Connectivity Issues', count: 28, avgResolution: 180 },
    { id: 'billing', name: 'Billing & Payments', count: 22, avgResolution: 120 },
    { id: 'service_change', name: 'Service Changes', count: 18, avgResolution: 90 },
    { id: 'equipment', name: 'Equipment', count: 15, avgResolution: 240 },
    { id: 'general', name: 'General Inquiry', count: 12, avgResolution: 60 },
  ];

  const automations = [
    {
      id: 'AUTO-001',
      name: 'Priority Assignment',
      description: 'Auto-assign high priority tickets to senior agents',
      trigger: 'Ticket Created',
      condition: 'Priority = High',
      action: 'Assign to Senior Agent Pool',
      status: 'active',
      executions: 45,
      successRate: 98.2,
    },
    {
      id: 'AUTO-002',
      name: 'SLA Breach Alert',
      description: 'Send alerts when tickets approach SLA breach',
      trigger: 'Time Based',
      condition: '15 minutes before SLA breach',
      action: 'Send notification to agent and supervisor',
      status: 'active',
      executions: 23,
      successRate: 100,
    },
    {
      id: 'AUTO-003',
      name: 'Customer Satisfaction Survey',
      description: 'Send satisfaction survey after ticket resolution',
      trigger: 'Ticket Resolved',
      condition: 'Status = Resolved',
      action: 'Send email survey to customer',
      status: 'active',
      executions: 234,
      successRate: 89.5,
    },
  ];

  // Apply filters
  let filteredTickets = mockTickets;

  if (searchParams.search) {
    const query = searchParams.search.toLowerCase();
    filteredTickets = filteredTickets.filter(
      (ticket) =>
        ticket.id.toLowerCase().includes(query) ||
        ticket.title.toLowerCase().includes(query) ||
        ticket.customerName.toLowerCase().includes(query) ||
        ticket.customerEmail.toLowerCase().includes(query)
    );
  }

  if (searchParams.status) {
    filteredTickets = filteredTickets.filter((ticket) => ticket.status === searchParams.status);
  }

  if (searchParams.priority) {
    filteredTickets = filteredTickets.filter((ticket) => ticket.priority === searchParams.priority);
  }

  if (searchParams.category) {
    filteredTickets = filteredTickets.filter((ticket) => ticket.category === searchParams.category);
  }

  if (searchParams.assignee) {
    filteredTickets = filteredTickets.filter(
      (ticket) => ticket.assigneeId === searchParams.assignee
    );
  }

  // Pagination
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const tickets = filteredTickets.slice(startIndex, endIndex);

  return {
    tickets,
    agents: mockAgents,
    metrics,
    categories,
    automations,
    total: filteredTickets.length,
  };
}
