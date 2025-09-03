/**
 * Project Management Configuration
 * Defines the configuration for infrastructure project management
 */

import { ManagementPageConfig } from '@dotmac/patterns';
import {
  FolderOpen,
  Calendar,
  DollarSign,
  Users,
  Plus,
  Download,
  Upload,
  Clock,
  CheckCircle,
  AlertTriangle,
  BarChart3,
} from 'lucide-react';
import { ProjectDetailDrawer } from '../components/projects/ProjectDetailDrawer';
import { CreateProjectDrawer } from '../components/projects/CreateProjectDrawer';
import { EditProjectDrawer } from '../components/projects/EditProjectDrawer';
import { StatusBadge } from '../components/common/StatusBadge';
import { ProgressBar } from '../components/common/ProgressBar';
import { formatCurrency, formatDate } from '@dotmac/utils';

export const projectManagementConfig: ManagementPageConfig = {
  title: 'Project Management',
  entity: 'projects',
  description: 'Track and manage infrastructure and deployment projects',
  apiEndpoint: '/api/admin/projects',

  metrics: [
    {
      name: 'Active Projects',
      value: '0',
      icon: FolderOpen,
      description: 'in progress',
      color: 'primary',
    },
    {
      name: 'On Schedule',
      value: '0%',
      icon: Calendar,
      trend: {
        value: '+5%',
        positive: true,
      },
      description: 'meeting deadlines',
      color: 'success',
    },
    {
      name: 'Budget Used',
      value: '$0',
      icon: DollarSign,
      trend: {
        value: '-2%',
        positive: true,
      },
      description: 'of allocated',
      color: 'secondary',
    },
    {
      name: 'Team Members',
      value: '0',
      icon: Users,
      description: 'actively assigned',
      color: 'warning',
    },
  ],

  tableColumns: [
    {
      key: 'name',
      label: 'Project',
      sortable: true,
      sticky: true,
      width: 250,
    },
    {
      key: 'status',
      label: 'Status',
      component: StatusBadge,
      filterable: true,
    },
    {
      key: 'progress',
      label: 'Progress',
      component: ProgressBar,
      sortable: true,
    },
    {
      key: 'project_type',
      label: 'Type',
      filterable: true,
      formatter: (value: string) => value.replace('_', ' ').toUpperCase(),
    },
    {
      key: 'priority',
      label: 'Priority',
      component: StatusBadge,
      filterable: true,
      sortable: true,
    },
    {
      key: 'owner',
      label: 'Project Manager',
      formatter: (value: any) => value?.name || 'Unassigned',
    },
    {
      key: 'start_date',
      label: 'Start Date',
      sortable: true,
      formatter: (value: string) => formatDate(value),
    },
    {
      key: 'due_date',
      label: 'Due Date',
      sortable: true,
      formatter: (value: string) => formatDate(value),
    },
    {
      key: 'budget_allocated',
      label: 'Budget',
      sortable: true,
      formatter: (value: number) => formatCurrency(value),
    },
    {
      key: 'budget_used_percentage',
      label: 'Budget Used',
      sortable: true,
      formatter: (value: number) => `${Math.round(value)}%`,
    },
    {
      key: 'team_size',
      label: 'Team Size',
      sortable: true,
    },
    {
      key: 'location',
      label: 'Location',
      filterable: true,
      formatter: (value: any) => value?.name || 'Multiple',
    },
  ],

  actions: [
    {
      label: 'New Project',
      icon: Plus,
      action: 'create',
      variant: 'primary',
      permission: 'projects:create',
    },
    {
      label: 'Import Projects',
      icon: Upload,
      action: 'import',
      variant: 'secondary',
      permission: 'projects:import',
    },
    {
      label: 'Export',
      icon: Download,
      action: 'export',
      variant: 'secondary',
    },
    {
      label: 'Board View',
      icon: BarChart3,
      action: 'toggle_view',
      variant: 'secondary',
    },
  ],

  bulkActions: [
    {
      label: 'Update Status',
      action: 'bulk_status_update',
      icon: CheckCircle,
      permission: 'projects:edit',
    },
    {
      label: 'Assign Team',
      action: 'bulk_assign',
      icon: Users,
      permission: 'projects:assign',
    },
    {
      label: 'Generate Reports',
      action: 'bulk_report',
      icon: BarChart3,
      permission: 'projects:reports',
    },
    {
      label: 'Archive',
      action: 'bulk_archive',
      icon: FolderOpen,
      permission: 'projects:archive',
      confirmMessage: 'Archive selected projects? They will be moved to the archive.',
    },
  ],

  filters: [
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { label: 'Planning', value: 'planning' },
        { label: 'In Progress', value: 'in_progress' },
        { label: 'On Hold', value: 'on_hold' },
        { label: 'Completed', value: 'completed' },
        { label: 'Cancelled', value: 'cancelled' },
      ],
    },
    {
      key: 'project_type',
      label: 'Type',
      type: 'select',
      options: [
        { label: 'Network Expansion', value: 'network_expansion' },
        { label: 'Infrastructure Upgrade', value: 'infrastructure_upgrade' },
        { label: 'Customer Deployment', value: 'customer_deployment' },
        { label: 'Maintenance', value: 'maintenance' },
        { label: 'Emergency Repair', value: 'emergency_repair' },
        { label: 'Fiber Installation', value: 'fiber_installation' },
      ],
    },
    {
      key: 'priority',
      label: 'Priority',
      type: 'select',
      options: [
        { label: 'Critical', value: 'critical' },
        { label: 'High', value: 'high' },
        { label: 'Medium', value: 'medium' },
        { label: 'Low', value: 'low' },
      ],
    },
    {
      key: 'owner_id',
      label: 'Project Manager',
      type: 'select',
      options: [], // Will be populated from API
    },
    {
      key: 'location_id',
      label: 'Location',
      type: 'select',
      options: [], // Will be populated from API
    },
    {
      key: 'budget_range',
      label: 'Budget Range',
      type: 'select',
      options: [
        { label: 'Under $10K', value: '0-10000' },
        { label: '$10K - $50K', value: '10000-50000' },
        { label: '$50K - $100K', value: '50000-100000' },
        { label: '$100K - $500K', value: '100000-500000' },
        { label: 'Over $500K', value: '500000+' },
      ],
    },
    {
      key: 'due_date_range',
      label: 'Due Date',
      type: 'daterange',
    },
  ],

  searchPlaceholder: 'Search projects by name, description, or location...',

  detailComponent: ProjectDetailDrawer,
  createComponent: CreateProjectDrawer,
  editComponent: EditProjectDrawer,

  emptyState: {
    title: 'No projects found',
    description: 'Start by creating your first infrastructure or deployment project.',
    action: {
      label: 'Create First Project',
      icon: Plus,
      action: 'create',
    },
  },

  permissions: {
    read: 'projects:read',
    create: 'projects:create',
    edit: 'projects:edit',
    delete: 'projects:delete',
    bulk: 'projects:bulk',
  },
};
