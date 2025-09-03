/**
 * Reseller Sales Management Page
 * Kanban pipeline with quote/order drawer using ManagementPageTemplate
 */

'use client';

import React, { useState, useCallback } from 'react';
import { ManagementPageTemplate, ManagementPageConfig } from '@dotmac/patterns/templates';
import { KanbanBoard, KanbanColumn, KanbanCard } from '@dotmac/patterns/templates/KanbanBoard';
import { Card, Button, Badge, Drawer, Input, Select } from '@dotmac/primitives';
import {
  Plus,
  DollarSign,
  TrendingUp,
  Users,
  FileText,
  Calendar,
  Phone,
  Mail,
  Download,
} from 'lucide-react';

// Custom sales pipeline component
function SalesPipelineSection({ data, isLoading }: { data?: any; isLoading: boolean }) {
  const [selectedDeal, setSelectedDeal] = useState<KanbanCard | null>(null);

  const handleCardMove = useCallback(
    (cardId: string, sourceColumn: string, destColumn: string, destIndex: number) => {
      // Emit observability event
      const event = new CustomEvent('ui.action.deal-move', {
        detail: {
          dealId: cardId,
          from: sourceColumn,
          to: destColumn,
          timestamp: new Date().toISOString(),
        },
      });
      window.dispatchEvent(event);

      // API call to update deal stage would go here
      // TODO: Implement API call to update deal stage
    },
    []
  );

  const handleCardClick = useCallback((card: KanbanCard) => {
    setSelectedDeal(card);
  }, []);

  if (isLoading) {
    return <div className='h-96 bg-gray-100 rounded-lg animate-pulse' />;
  }

  const columns: KanbanColumn[] = [
    {
      id: 'leads',
      title: 'New Leads',
      color: '#3B82F6',
      cards: data?.pipeline?.leads || [
        {
          id: 'lead-1',
          title: 'TechCorp ISP Setup',
          description: 'Enterprise internet services for new office location',
          value: 25000,
          priority: 'high' as const,
          assignee: { id: '1', name: 'John Doe' },
          dueDate: '2024-09-15',
          tags: ['enterprise', 'urgent'],
        },
      ],
      allowAdd: true,
      limit: 10,
    },
    {
      id: 'qualified',
      title: 'Qualified',
      color: '#10B981',
      cards: data?.pipeline?.qualified || [
        {
          id: 'qual-1',
          title: 'SmallBiz Internet',
          description: 'Basic business internet package',
          value: 8500,
          priority: 'medium' as const,
          assignee: { id: '2', name: 'Jane Smith' },
          dueDate: '2024-09-20',
        },
      ],
      allowAdd: true,
    },
    {
      id: 'proposal',
      title: 'Proposal Sent',
      color: '#F59E0B',
      cards: data?.pipeline?.proposal || [
        {
          id: 'prop-1',
          title: 'Regional ISP Expansion',
          description: 'Infrastructure upgrade for growing company',
          value: 45000,
          priority: 'high' as const,
          assignee: { id: '1', name: 'John Doe' },
          dueDate: '2024-09-10',
        },
      ],
    },
    {
      id: 'negotiation',
      title: 'Negotiation',
      color: '#EF4444',
      cards: data?.pipeline?.negotiation || [],
      allowAdd: false,
    },
    {
      id: 'closed-won',
      title: 'Closed Won',
      color: '#22C55E',
      cards: data?.pipeline?.closedWon || [],
      allowDrop: true,
      allowAdd: false,
    },
    {
      id: 'closed-lost',
      title: 'Closed Lost',
      color: '#6B7280',
      cards: data?.pipeline?.closedLost || [],
      allowDrop: true,
      allowAdd: false,
    },
  ];

  return (
    <div className='space-y-6'>
      <KanbanBoard
        columns={columns}
        onCardMove={handleCardMove}
        onCardClick={handleCardClick}
        showAddCard={true}
        showColumnLimits={true}
      />

      {/* Deal Detail Drawer */}
      {selectedDeal && (
        <Drawer
          isOpen={!!selectedDeal}
          onClose={() => setSelectedDeal(null)}
          title='Deal Details'
          size='lg'
        >
          <div className='space-y-6'>
            <div className='border-b pb-4'>
              <h2 className='text-xl font-semibold'>{selectedDeal.title}</h2>
              <p className='text-gray-600'>{selectedDeal.description}</p>
            </div>

            <div className='grid grid-cols-2 gap-4'>
              <div className='space-y-3'>
                <div className='flex items-center gap-2'>
                  <DollarSign className='w-4 h-4' />
                  <span className='font-medium'>Value:</span>
                  <span>${selectedDeal.value?.toLocaleString()}</span>
                </div>

                <div className='flex items-center gap-2'>
                  <Calendar className='w-4 h-4' />
                  <span className='font-medium'>Due Date:</span>
                  <span>{selectedDeal.dueDate}</span>
                </div>

                <div className='flex items-center gap-2'>
                  <Users className='w-4 h-4' />
                  <span className='font-medium'>Assignee:</span>
                  <span>{selectedDeal.assignee?.name}</span>
                </div>
              </div>

              <div className='space-y-3'>
                <div className='flex items-center gap-2'>
                  <span className='font-medium'>Priority:</span>
                  <Badge variant={selectedDeal.priority === 'high' ? 'destructive' : 'secondary'}>
                    {selectedDeal.priority}
                  </Badge>
                </div>

                <div className='flex flex-wrap gap-1'>
                  {selectedDeal.tags?.map((tag) => (
                    <Badge key={tag} variant='outline'>
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            <div className='flex gap-3'>
              <Button onClick={() => setSelectedDeal(null)}>
                <FileText className='w-4 h-4 mr-2' />
                Generate Quote
              </Button>
              <Button variant='outline'>
                <Phone className='w-4 h-4 mr-2' />
                Call Customer
              </Button>
              <Button variant='outline'>
                <Mail className='w-4 h-4 mr-2' />
                Send Email
              </Button>
            </div>
          </div>
        </Drawer>
      )}
    </div>
  );
}

const managementConfig: ManagementPageConfig = {
  title: 'Sales Pipeline',
  entity: 'deals',
  description: 'Manage your sales pipeline with Kanban board and deal tracking',
  apiEndpoint: '/api/reseller/sales/deals',
  metrics: [
    {
      id: 'total-pipeline',
      label: 'Total Pipeline',
      value: '$2.4M',
      change: '+$320K',
      trend: 'up' as const,
      icon: DollarSign,
      description: 'Total value of all active deals',
    },
    {
      id: 'deals-in-progress',
      label: 'Active Deals',
      value: '47',
      change: '+8',
      trend: 'up' as const,
      icon: TrendingUp,
      description: 'Deals currently in pipeline',
    },
    {
      id: 'avg-deal-size',
      label: 'Avg Deal Size',
      value: '$18.5K',
      change: '+$2.1K',
      trend: 'up' as const,
      icon: FileText,
      description: 'Average value per deal',
    },
    {
      id: 'close-rate',
      label: 'Close Rate',
      value: '28.4%',
      change: '+3.2%',
      trend: 'up' as const,
      icon: Users,
      description: 'Percentage of deals won',
    },
  ],
  tableColumns: [
    { key: 'title', label: 'Deal Name', sortable: true },
    {
      key: 'value',
      label: 'Value',
      sortable: true,
      formatter: (val) => `$${val?.toLocaleString()}`,
    },
    {
      key: 'stage',
      label: 'Stage',
      component: ({ value }) => <Badge variant='outline'>{value}</Badge>,
    },
    { key: 'assignee', label: 'Assignee' },
    { key: 'dueDate', label: 'Due Date', sortable: true },
    {
      key: 'priority',
      label: 'Priority',
      component: ({ value }) => (
        <Badge variant={value === 'high' ? 'destructive' : 'secondary'}>{value}</Badge>
      ),
    },
  ],
  actions: [
    {
      label: 'New Deal',
      icon: Plus,
      action: 'create',
      variant: 'primary',
      permission: 'reseller:deals:create',
    },
    {
      label: 'Export Pipeline',
      icon: Download,
      action: 'export',
      variant: 'secondary',
    },
  ],
  bulkActions: [
    {
      label: 'Update Stage',
      action: 'bulk-update-stage',
      icon: TrendingUp,
      permission: 'reseller:deals:edit',
    },
  ],
  filters: [
    {
      key: 'stage',
      label: 'Stage',
      type: 'select',
      options: [
        { label: 'New Leads', value: 'leads' },
        { label: 'Qualified', value: 'qualified' },
        { label: 'Proposal', value: 'proposal' },
        { label: 'Negotiation', value: 'negotiation' },
        { label: 'Closed Won', value: 'closed-won' },
        { label: 'Closed Lost', value: 'closed-lost' },
      ],
    },
    {
      key: 'priority',
      label: 'Priority',
      type: 'select',
      options: [
        { label: 'High', value: 'high' },
        { label: 'Medium', value: 'medium' },
        { label: 'Low', value: 'low' },
      ],
    },
    {
      key: 'assignee',
      label: 'Assignee',
      type: 'select',
      options: [
        { label: 'John Doe', value: '1' },
        { label: 'Jane Smith', value: '2' },
      ],
    },
  ],
  searchPlaceholder: 'Search deals...',
  emptyState: {
    title: 'No deals found',
    description: 'Start by creating your first deal or adjusting your filters',
    action: {
      label: 'Create Deal',
      icon: Plus,
      action: 'create',
    },
  },
  permissions: {
    read: 'reseller:deals:read',
    create: 'reseller:deals:create',
    edit: 'reseller:deals:edit',
    delete: 'reseller:deals:delete',
  },
};

export default function SalesPage() {
  return (
    <div className='space-y-6'>
      {/* Pipeline Section */}
      <Card className='p-6'>
        <div className='mb-4'>
          <h2 className='text-lg font-semibold'>Sales Pipeline</h2>
          <p className='text-sm text-gray-600'>Drag and drop deals between stages</p>
        </div>
        <SalesPipelineSection data={{}} isLoading={false} />
      </Card>

      {/* Management Template for List View */}
      <ManagementPageTemplate config={managementConfig} portal='reseller' />
    </div>
  );
}
