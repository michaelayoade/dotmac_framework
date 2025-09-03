import type { ManagementPageConfig } from '@dotmac/patterns/templates';

export const ticketsConfig: ManagementPageConfig = {
  type: 'management',
  title: 'Support Tickets',
  description: 'Create and manage your support tickets',
  portal: 'customer',
  showFilters: true,
  showActions: true,
  metrics: [
    { key: 'open', title: 'Open', value: 0, format: 'number', precision: 0, color: '#ef4444' },
    { key: 'urgent', title: 'Urgent', value: 0, format: 'number', precision: 0, color: '#f97316' },
    {
      key: 'avgResponse',
      title: 'Avg Response (h)',
      value: 0,
      format: 'number',
      precision: 1,
      color: '#2563eb',
    },
    {
      key: 'resolved',
      title: 'Resolved (30d)',
      value: 0,
      format: 'number',
      precision: 0,
      color: '#10b981',
    },
  ],
  filters: [
    {
      key: 'priority',
      label: 'Priority',
      type: 'select',
      options: [
        { value: 'low', label: 'Low' },
        { value: 'medium', label: 'Medium' },
        { value: 'high', label: 'High' },
      ],
    },
    {
      key: 'category',
      label: 'Category',
      type: 'select',
      options: [
        { value: 'billing', label: 'Billing' },
        { value: 'service', label: 'Service' },
        { value: 'technical', label: 'Technical' },
      ],
    },
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { value: 'open', label: 'Open' },
        { value: 'pending', label: 'Pending' },
        { value: 'resolved', label: 'Resolved' },
      ],
    },
  ],
  actions: [{ key: 'new-ticket', label: 'New Ticket', variant: 'primary' }],
};
