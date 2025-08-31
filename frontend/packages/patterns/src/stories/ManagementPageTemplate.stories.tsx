/**
 * Management Page Template Stories
 */

import type { Meta, StoryObj } from '@storybook/react';
import { action } from '@storybook/addon-actions';
import { within, userEvent, expect } from '@storybook/test';
import { ManagementPageTemplate } from '../templates/ManagementPageTemplate';
import { PortalThemeProvider } from '../theming/PortalThemeProvider';
import { ManagementPageConfig } from '../types/templates';

const meta = {
  title: 'Templates/ManagementPageTemplate',
  component: ManagementPageTemplate,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'A comprehensive management page template with metrics, filters, and actions. Supports all portal types with customizable theming and density settings.',
      },
    },
  },
  decorators: [
    (Story, context) => (
      <PortalThemeProvider 
        portal={context.args.config?.portal || 'admin'}
        initialDensity={context.args.config?.density || 'comfortable'}
      >
        <div className="min-h-screen bg-background">
          <Story />
        </div>
      </PortalThemeProvider>
    ),
  ],
  argTypes: {
    config: {
      control: { type: 'object' },
      description: 'Configuration object for the management page template',
    },
    className: {
      control: { type: 'text' },
      description: 'Additional CSS classes',
    },
  },
} satisfies Meta<typeof ManagementPageTemplate>;

export default meta;
type Story = StoryObj<typeof meta>;

// Base configuration
const baseConfig: ManagementPageConfig = {
  type: 'management',
  title: 'Customer Management',
  description: 'Manage customer accounts, billing, and services',
  portal: 'admin',
  showBreadcrumbs: true,
  showHeader: true,
  showSidebar: false,
  maxWidth: 'none',
  padding: true,
  theme: 'auto',
  density: 'comfortable',
  metrics: [
    {
      key: 'total-customers',
      title: 'Total Customers',
      value: 2847,
      format: 'number',
      precision: 0,
      size: 'md',
      icon: 'Users',
      color: '#3b82f6',
      change: {
        value: 12.5,
        type: 'increase',
        period: 'this month'
      }
    },
    {
      key: 'active-services',
      title: 'Active Services',
      value: 1923,
      format: 'number',
      precision: 0,
      size: 'md',
      icon: 'Activity',
      color: '#10b981',
      change: {
        value: 8.2,
        type: 'increase',
        period: 'this month'
      }
    },
    {
      key: 'monthly-revenue',
      title: 'Monthly Revenue',
      value: 485920,
      format: 'currency',
      precision: 0,
      size: 'md',
      icon: 'DollarSign',
      color: '#8b5cf6',
      change: {
        value: 15.8,
        type: 'increase',
        period: 'vs last month'
      }
    },
    {
      key: 'support-tickets',
      title: 'Open Tickets',
      value: 23,
      format: 'number',
      precision: 0,
      size: 'md',
      icon: 'HelpCircle',
      color: '#ef4444',
      change: {
        value: -18.5,
        type: 'decrease',
        period: 'this week'
      }
    }
  ],
  filters: [
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { value: 'active', label: 'Active', disabled: false },
        { value: 'inactive', label: 'Inactive', disabled: false },
        { value: 'pending', label: 'Pending', disabled: false },
        { value: 'suspended', label: 'Suspended', disabled: false }
      ],
      defaultValue: 'active'
    },
    {
      key: 'customer_type',
      label: 'Customer Type',
      type: 'multiselect',
      options: [
        { value: 'residential', label: 'Residential', disabled: false },
        { value: 'business', label: 'Business', disabled: false },
        { value: 'enterprise', label: 'Enterprise', disabled: false }
      ]
    },
    {
      key: 'date_range',
      label: 'Date Range',
      type: 'dateRange',
      defaultValue: {
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        end: new Date()
      }
    },
    {
      key: 'revenue_range',
      label: 'Monthly Revenue',
      type: 'number',
      validation: {
        min: 0,
        max: 100000
      }
    }
  ],
  actions: [
    {
      key: 'create-customer',
      label: 'Add Customer',
      variant: 'primary',
      icon: 'Plus',
      disabled: false,
      loading: false,
      permissions: [],
      onClick: action('create-customer')
    },
    {
      key: 'bulk-import',
      label: 'Import CSV',
      variant: 'outline',
      icon: 'Upload',
      disabled: false,
      loading: false,
      permissions: [],
      onClick: action('bulk-import')
    },
    {
      key: 'export-data',
      label: 'Export',
      variant: 'outline',
      icon: 'Download',
      disabled: false,
      loading: false,
      permissions: [],
      onClick: action('export-data')
    }
  ],
  showMetrics: true,
  showFilters: true,
  showActions: true,
  showExport: true,
  showSearch: true,
  showSavedViews: true,
  enableBulkActions: true,
  enableColumnConfig: true,
  refreshInterval: 30000,
  autoRefresh: true,
  savedViews: [
    {
      id: 'active-customers',
      name: 'Active Customers',
      filters: { status: 'active' },
      isDefault: true,
      isPublic: false,
      createdBy: 'admin',
      createdAt: new Date('2024-01-01')
    },
    {
      id: 'high-value',
      name: 'High Value Customers',
      filters: { 
        status: 'active',
        revenue_range: { min: 1000 }
      },
      isDefault: false,
      isPublic: true,
      createdBy: 'manager',
      createdAt: new Date('2024-01-15')
    }
  ]
};

// Default story
export const Default: Story = {
  args: {
    config: baseConfig,
    onAction: action('onAction'),
    onExport: action('onExport')
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    
    // Test that key elements are present
    await expect(canvas.getByText('Customer Management')).toBeInTheDocument();
    await expect(canvas.getByText('Total Customers')).toBeInTheDocument();
    await expect(canvas.getByText('2,847')).toBeInTheDocument();
    await expect(canvas.getByText('Add Customer')).toBeInTheDocument();
  },
};

// Loading state
// Loading and error states are managed internally by the template via callbacks

// Compact density
export const CompactDensity: Story = {
  args: {
    ...Default.args,
    config: {
      ...baseConfig,
      density: 'compact',
    },
  },
};

// Spacious density
export const SpaciousDensity: Story = {
  args: {
    ...Default.args,
    config: {
      ...baseConfig,
      density: 'spacious',
    },
  },
};

// Reseller portal variant
export const ResellerPortal: Story = {
  args: {
    ...Default.args,
    config: {
      ...baseConfig,
      portal: 'reseller',
      title: 'Partner Management',
      description: 'Manage your partner network and commissions',
      metrics: [
        {
          key: 'total-partners',
          title: 'Total Partners',
          value: 156,
          format: 'number',
          icon: 'Users',
          color: '#7c3aed',
          precision: 0,
          size: 'md'
        },
        {
          key: 'commission-earned',
          title: 'Commission Earned',
          value: 28450,
          format: 'currency',
          icon: 'TrendingUp',
          color: '#10b981',
          precision: 0,
          size: 'md'
        },
        {
          key: 'territory-coverage',
          title: 'Territory Coverage',
          value: 78.5,
          format: 'percentage',
          icon: 'MapPin',
          color: '#3b82f6',
          precision: 1,
          size: 'md'
        }
      ]
    },
  },
};

// Customer portal variant
export const CustomerPortal: Story = {
  args: {
    ...Default.args,
    config: {
      ...baseConfig,
      portal: 'customer',
      title: 'Account Overview',
      description: 'View your account details and service status',
      showBulkActions: false,
      showSavedViews: false,
      metrics: [
        {
          key: 'service-status',
          title: 'Service Status',
          value: 'Active',
          format: 'number',
          icon: 'Wifi',
          color: '#10b981'
        },
        {
          key: 'data-usage',
          title: 'Data Usage',
          value: 245 * 1024 * 1024 * 1024, // 245 GB
          format: 'bytes',
          icon: 'BarChart3',
          color: '#3b82f6'
        },
        {
          key: 'monthly-bill',
          title: 'Current Bill',
          value: 89.99,
          format: 'currency',
          icon: 'CreditCard',
          color: '#8b5cf6'
        }
      ],
      actions: [
        {
          key: 'pay-bill',
          label: 'Pay Bill',
          variant: 'primary',
          icon: 'CreditCard',
          disabled: false,
          loading: false,
          permissions: [],
          onClick: action('pay-bill')
        },
        {
          key: 'view-usage',
          label: 'Usage Details',
          variant: 'outline',
          icon: 'BarChart3',
          disabled: false,
          loading: false,
          permissions: [],
          onClick: action('view-usage')
        }
      ]
    },
  },
};

// Technician portal variant
export const TechnicianPortal: Story = {
  args: {
    ...Default.args,
    config: {
      ...baseConfig,
      portal: 'technician',
      title: 'Work Orders',
      description: 'Manage your assigned work orders and schedules',
      metrics: [
        {
          key: 'assigned-orders',
          title: 'Assigned Orders',
          value: 8,
          format: 'number',
          icon: 'Clipboard',
          color: '#dc2626',
          precision: 0,
          size: 'md'
        },
        {
          key: 'completed-today',
          title: 'Completed Today',
          value: 3,
          format: 'number',
          icon: 'CheckCircle',
          color: '#10b981',
          precision: 0,
          size: 'md'
        },
        {
          key: 'efficiency-rating',
          title: 'Efficiency Rating',
          value: 92.5,
          format: 'percentage',
          icon: 'Star',
          color: '#f59e0b',
          precision: 1,
          size: 'md'
        }
      ],
      actions: [
        {
          key: 'check-in',
          label: 'Check In',
          variant: 'primary',
          icon: 'MapPin',
          disabled: false,
          loading: false,
          permissions: [],
          onClick: action('check-in')
        },
        {
          key: 'report-issue',
          label: 'Report Issue',
          variant: 'outline',
          icon: 'AlertTriangle',
          disabled: false,
          loading: false,
          permissions: [],
          onClick: action('report-issue')
        }
      ]
    },
  },
};

// Minimal configuration
export const MinimalConfig: Story = {
  args: {
    ...Default.args,
    config: {
      type: 'management',
      title: 'Simple Page',
      portal: 'admin',
      showBreadcrumbs: true,
      showHeader: true,
      showSidebar: false,
      maxWidth: 'none',
      padding: true,
      theme: 'auto',
      density: 'comfortable',
      metrics: [],
      filters: [],
      actions: [],
      showMetrics: false,
      showFilters: false,
      showActions: false,
      showExport: false,
      showSearch: false,
      showSavedViews: false,
      enableBulkActions: false,
      enableColumnConfig: false,
      savedViews: []
    },
  },
};

// Interactive playground
export const InteractivePlayground: Story = {
  args: Default.args,
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const user = userEvent.setup();
    
    // Test search functionality
    const searchInput = canvas.getByPlaceholderText('Search...');
    await user.type(searchInput, 'test search');
    
    // Test filter interaction
    const statusFilter = canvas.getByLabelText('Status');
    await user.selectOptions(statusFilter, 'active');
    
    // Test action button
    const addButton = canvas.getByText('Add Customer');
    await user.click(addButton);
    
    // Test advanced filters toggle
    const advancedButton = canvas.getByText('Advanced');
    await user.click(advancedButton);
    
    // Test export functionality
    const exportButton = canvas.getByText('Export');
    await user.click(exportButton);
  },
};

// Accessibility testing
export const AccessibilityTest: Story = {
  args: Default.args,
  parameters: {
    a11y: {
      config: {
        rules: [
          {
            id: 'color-contrast',
            enabled: true,
          },
          {
            id: 'keyboard-navigation',
            enabled: true,
          },
          {
            id: 'focus-management',
            enabled: true,
          },
        ],
      },
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    
    // Test keyboard navigation
    const firstButton = canvas.getByText('Add Customer');
    firstButton.focus();
    
    // Verify ARIA labels
    await expect(canvas.getByLabelText('Search')).toBeInTheDocument();
    await expect(canvas.getByRole('main')).toBeInTheDocument();
    
    // Test screen reader announcements
    const statusElements = canvas.getAllByRole('status');
    expect(statusElements.length).toBeGreaterThan(0);
  },
};

// Performance testing
export const PerformanceTest: Story = {
  args: {
    ...Default.args,
    config: {
      ...baseConfig,
      metrics: Array.from({ length: 20 }, (_, i) => ({
        key: `metric-${i}`,
        title: `Metric ${i + 1}`,
        value: Math.floor(Math.random() * 10000),
        format: 'number' as const,
        icon: 'BarChart3',
        color: '#3b82f6',
        precision: 0,
        size: 'md'
      })),
      filters: Array.from({ length: 10 }, (_, i) => ({
        key: `filter-${i}`,
        label: `Filter ${i + 1}`,
        type: 'select' as const,
        options: Array.from({ length: 5 }, (_, j) => ({
          value: `option-${j}`,
          label: `Option ${j + 1}`,
          disabled: false
        }))
      }))
    },
  },
  parameters: {
    docs: {
      description: {
        story: 'Performance test with many metrics and filters to ensure the template handles large datasets efficiently.',
      },
    },
  },
};
