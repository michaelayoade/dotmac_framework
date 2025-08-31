/**
 * Reseller Projects Management Page
 * Partner milestones using ManagementPageTemplate
 */

'use client';

import React from 'react';
import { ManagementPageTemplate, ManagementPageConfig } from '@dotmac/patterns/templates';
import { Badge, Progress } from '@dotmac/primitives';
import { 
  Plus, 
  Briefcase, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Users,
  Calendar,
  Target,
  Download
} from 'lucide-react';

// Custom milestone component for table
function MilestoneProgress({ value, row }: { value: any; row: any }) {
  const percentage = (row.completedMilestones / row.totalMilestones) * 100;
  
  return (
    <div className="space-y-2">
      <Progress value={percentage} className="h-2" />
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{row.completedMilestones}/{row.totalMilestones} completed</span>
        <span>{Math.round(percentage)}%</span>
      </div>
    </div>
  );
}

// Project status badge component
function ProjectStatusBadge({ value }: { value: string }) {
  const statusConfig = {
    'planning': { variant: 'secondary' as const, color: 'bg-gray-100 text-gray-700' },
    'active': { variant: 'default' as const, color: 'bg-blue-100 text-blue-700' },
    'on-track': { variant: 'default' as const, color: 'bg-green-100 text-green-700' },
    'at-risk': { variant: 'destructive' as const, color: 'bg-yellow-100 text-yellow-700' },
    'delayed': { variant: 'destructive' as const, color: 'bg-red-100 text-red-700' },
    'completed': { variant: 'default' as const, color: 'bg-green-100 text-green-700' },
    'cancelled': { variant: 'secondary' as const, color: 'bg-gray-100 text-gray-700' }
  };

  const config = statusConfig[value as keyof typeof statusConfig] || statusConfig.planning;
  
  return (
    <Badge variant={config.variant} className={config.color}>
      {value.replace('-', ' ').toUpperCase()}
    </Badge>
  );
}

// Priority badge component  
function PriorityBadge({ value }: { value: string }) {
  const priorityConfig = {
    low: 'bg-gray-100 text-gray-700',
    medium: 'bg-yellow-100 text-yellow-700', 
    high: 'bg-red-100 text-red-700',
    critical: 'bg-red-200 text-red-800'
  };

  return (
    <Badge variant="outline" className={priorityConfig[value as keyof typeof priorityConfig]}>
      {value.toUpperCase()}
    </Badge>
  );
}

const managementConfig: ManagementPageConfig = {
  title: 'Partner Projects',
  entity: 'projects',
  description: 'Track project progress and partner milestones',
  apiEndpoint: '/api/reseller/projects',
  metrics: [
    {
      id: 'active-projects',
      label: 'Active Projects',
      value: '23',
      change: '+4',
      trend: 'up' as const,
      icon: Briefcase,
      description: 'Currently active partner projects'
    },
    {
      id: 'completed-milestones',
      label: 'Completed Milestones',
      value: '187',
      change: '+24',
      trend: 'up' as const,
      icon: CheckCircle,
      description: 'Milestones completed this month'
    },
    {
      id: 'on-track-projects',
      label: 'On Track',
      value: '18',
      change: '0',
      trend: 'neutral' as const,
      icon: Target,
      description: 'Projects meeting timeline'
    },
    {
      id: 'at-risk-projects', 
      label: 'At Risk',
      value: '5',
      change: '+2',
      trend: 'down' as const,
      icon: AlertTriangle,
      description: 'Projects needing attention'
    }
  ],
  tableColumns: [
    { 
      key: 'name', 
      label: 'Project Name', 
      sortable: true,
      sticky: true
    },
    { 
      key: 'partner', 
      label: 'Partner', 
      sortable: true 
    },
    { 
      key: 'status', 
      label: 'Status', 
      component: ProjectStatusBadge,
      filterable: true
    },
    { 
      key: 'priority', 
      label: 'Priority', 
      component: PriorityBadge,
      filterable: true 
    },
    { 
      key: 'milestones', 
      label: 'Milestone Progress', 
      component: MilestoneProgress,
      width: 200
    },
    { 
      key: 'startDate', 
      label: 'Start Date', 
      sortable: true,
      formatter: (date) => new Date(date).toLocaleDateString()
    },
    { 
      key: 'targetDate', 
      label: 'Target Date', 
      sortable: true,
      formatter: (date) => new Date(date).toLocaleDateString()
    },
    { 
      key: 'budget', 
      label: 'Budget', 
      sortable: true,
      formatter: (value) => `$${value?.toLocaleString()}`
    }
  ],
  actions: [
    {
      label: 'New Project',
      icon: Plus,
      action: 'create',
      variant: 'primary',
      permission: 'reseller:projects:create'
    },
    {
      label: 'Export Projects',
      icon: Download,
      action: 'export',
      variant: 'secondary'
    }
  ],
  bulkActions: [
    {
      label: 'Update Status',
      action: 'bulk-update-status',
      icon: Clock,
      permission: 'reseller:projects:edit'
    },
    {
      label: 'Assign to Partner',
      action: 'bulk-assign-partner', 
      icon: Users,
      permission: 'reseller:projects:assign'
    }
  ],
  filters: [
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { label: 'Planning', value: 'planning' },
        { label: 'Active', value: 'active' },
        { label: 'On Track', value: 'on-track' },
        { label: 'At Risk', value: 'at-risk' },
        { label: 'Delayed', value: 'delayed' },
        { label: 'Completed', value: 'completed' },
        { label: 'Cancelled', value: 'cancelled' }
      ]
    },
    {
      key: 'priority',
      label: 'Priority', 
      type: 'select',
      options: [
        { label: 'Low', value: 'low' },
        { label: 'Medium', value: 'medium' },
        { label: 'High', value: 'high' },
        { label: 'Critical', value: 'critical' }
      ]
    },
    {
      key: 'partner',
      label: 'Partner',
      type: 'select',
      options: [
        { label: 'TechCorp', value: 'techcorp' },
        { label: 'NetSolutions', value: 'netsolutions' },
        { label: 'ISP Partners Inc', value: 'isppartners' },
        { label: 'ConnectPro', value: 'connectpro' }
      ]
    },
    {
      key: 'dateRange',
      label: 'Date Range',
      type: 'daterange'
    }
  ],
  searchPlaceholder: 'Search projects by name, partner, or milestone...',
  emptyState: {
    title: 'No projects found',
    description: 'Create your first project to start tracking partner milestones',
    action: {
      label: 'Create Project',
      icon: Plus,
      action: 'create'
    }
  },
  permissions: {
    read: 'reseller:projects:read',
    create: 'reseller:projects:create', 
    edit: 'reseller:projects:edit',
    delete: 'reseller:projects:delete',
    bulk: 'reseller:projects:bulk'
  }
};

export default function ProjectsPage() {
  return (
    <ManagementPageTemplate 
      config={managementConfig} 
      portal="reseller"
      className="max-w-7xl mx-auto"
    />
  );
}

export const metadata = {
  title: 'Projects - Reseller Portal',
  description: 'Track project progress and partner milestones'
};