import type { ManagementPageConfig } from '@dotmac/patterns/templates';

export const projectsConfig: ManagementPageConfig = {
  type: 'management',
  title: 'Projects',
  description: 'Track installation and upgrade projects',
  portal: 'customer',
  showFilters: true,
  showActions: true,
  metrics: [
    { key: 'active', title: 'Active', value: 0, format: 'number', precision: 0, color: '#2563eb' },
    { key: 'onSchedule', title: 'On Schedule', value: 0.9, format: 'percentage', precision: 0, color: '#10b981' },
    { key: 'technicians', title: 'Technicians', value: 0, format: 'number', precision: 0, color: '#f59e0b' },
    { key: 'pendingTasks', title: 'Pending Tasks', value: 0, format: 'number', precision: 0, color: '#ef4444' },
  ],
  filters: [
    { key: 'status', label: 'Status', type: 'select', options: [
      { value: 'planning', label: 'Planning' },
      { value: 'inprogress', label: 'In Progress' },
      { value: 'completed', label: 'Completed' },
    ]},
  ],
  actions: [
    { key: 'new-request', label: 'New Service Request', variant: 'primary' },
  ],
};

