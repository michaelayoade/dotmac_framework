import type { ManagementPageConfig } from '@dotmac/patterns/templates';

export const filesConfig: ManagementPageConfig = {
  type: 'management',
  title: 'My Files',
  description: 'Manage your documents and share with support',
  portal: 'customer',
  showSavedViews: true,
  showFilters: true,
  showActions: true,
  showExport: false,
  metrics: [
    { key: 'usage', title: 'Storage Used', value: 0, format: 'bytes', precision: 0, color: '#2563eb' },
    { key: 'files', title: 'Files', value: 0, format: 'number', precision: 0, color: '#10b981' },
    { key: 'shared', title: 'Shared Items', value: 0, format: 'number', precision: 0, color: '#f59e0b' },
    { key: 'downloads', title: 'Downloads (30d)', value: 0, format: 'number', precision: 0, color: '#9333ea' },
  ],
  filters: [
    { key: 'type', label: 'Type', type: 'select', options: [
      { value: 'pdf', label: 'PDF' },
      { value: 'image', label: 'Image' },
      { value: 'doc', label: 'Document' },
      { value: 'other', label: 'Other' },
    ]},
    { key: 'owner', label: 'Owner', type: 'select', options: [
      { value: 'me', label: 'Me' },
      { value: 'support', label: 'Support' },
    ]},
  ],
  actions: [
    { key: 'upload', label: 'Upload', variant: 'primary' },
    { key: 'share', label: 'Share', variant: 'secondary' },
  ],
};

