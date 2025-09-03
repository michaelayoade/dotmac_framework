/**
 * Container Management Configuration
 * Defines the configuration for service container oversight (read-only + restart)
 */

import { ManagementPageConfig } from '@dotmac/patterns';
import {
  Container,
  Activity,
  Cpu,
  MemoryStick,
  RefreshCw,
  Download,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { ContainerDetailDrawer } from '../components/containers/ContainerDetailDrawer';
import { StatusBadge } from '../components/common/StatusBadge';
import { ResourceUsageBar } from '../components/common/ResourceUsageBar';
import { formatBytes, formatDuration } from '@dotmac/utils';

export const containerManagementConfig: ManagementPageConfig = {
  title: 'Container Management',
  entity: 'containers',
  description: 'Monitor and manage service containers across your infrastructure',
  apiEndpoint: '/api/admin/containers',

  metrics: [
    {
      name: 'Running Containers',
      value: '0',
      icon: Container,
      description: 'active services',
      color: 'success',
    },
    {
      name: 'CPU Usage',
      value: '0%',
      icon: Cpu,
      trend: {
        value: '+5%',
        positive: false,
      },
      description: 'average across all',
      color: 'secondary',
    },
    {
      name: 'Memory Usage',
      value: '0 GB',
      icon: MemoryStick,
      trend: {
        value: '+2%',
        positive: false,
      },
      description: 'total allocated',
      color: 'warning',
    },
    {
      name: 'Restarts (24h)',
      value: '0',
      icon: RefreshCw,
      description: 'automatic restarts',
      color: 'primary',
    },
  ],

  tableColumns: [
    {
      key: 'name',
      label: 'Container',
      sortable: true,
      sticky: true,
      width: 200,
    },
    {
      key: 'image',
      label: 'Image',
      formatter: (value: string) => {
        const parts = value.split(':');
        return parts.length > 1 ? `${parts[0]}:${parts[1].substring(0, 8)}...` : value;
      },
    },
    {
      key: 'status',
      label: 'Status',
      component: StatusBadge,
      filterable: true,
    },
    {
      key: 'uptime',
      label: 'Uptime',
      sortable: true,
      formatter: (value: number) => formatDuration(value * 1000),
    },
    {
      key: 'cpu_usage',
      label: 'CPU',
      component: ResourceUsageBar,
      sortable: true,
    },
    {
      key: 'memory_usage',
      label: 'Memory',
      component: ResourceUsageBar,
      sortable: true,
    },
    {
      key: 'memory_limit',
      label: 'Memory Limit',
      formatter: (value: number) => formatBytes(value),
    },
    {
      key: 'network_io',
      label: 'Network I/O',
      formatter: (value: any) => `${formatBytes(value?.rx || 0)} / ${formatBytes(value?.tx || 0)}`,
    },
    {
      key: 'restart_count',
      label: 'Restarts',
      sortable: true,
    },
    {
      key: 'health_status',
      label: 'Health',
      component: StatusBadge,
      filterable: true,
    },
    {
      key: 'node',
      label: 'Node',
      filterable: true,
    },
    {
      key: 'service_name',
      label: 'Service',
      filterable: true,
    },
  ],

  actions: [
    {
      label: 'Refresh',
      icon: RefreshCw,
      action: 'refresh',
      variant: 'primary',
    },
    {
      label: 'Export Logs',
      icon: Download,
      action: 'export_logs',
      variant: 'secondary',
      permission: 'containers:logs',
    },
  ],

  bulkActions: [
    {
      label: 'Restart',
      action: 'bulk_restart',
      icon: RefreshCw,
      permission: 'containers:restart',
      confirmMessage: 'Restart selected containers? This may cause brief service interruption.',
    },
    {
      label: 'Scale',
      action: 'bulk_scale',
      icon: Activity,
      permission: 'containers:scale',
    },
  ],

  filters: [
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { label: 'Running', value: 'running' },
        { label: 'Stopped', value: 'stopped' },
        { label: 'Paused', value: 'paused' },
        { label: 'Restarting', value: 'restarting' },
        { label: 'Dead', value: 'dead' },
      ],
    },
    {
      key: 'health_status',
      label: 'Health',
      type: 'select',
      options: [
        { label: 'Healthy', value: 'healthy' },
        { label: 'Unhealthy', value: 'unhealthy' },
        { label: 'Starting', value: 'starting' },
        { label: 'Unknown', value: 'unknown' },
      ],
    },
    {
      key: 'service_name',
      label: 'Service',
      type: 'select',
      options: [
        { label: 'ISP Framework', value: 'isp-framework' },
        { label: 'Management Platform', value: 'management-platform' },
        { label: 'Database', value: 'database' },
        { label: 'Cache', value: 'cache' },
        { label: 'Message Queue', value: 'message-queue' },
        { label: 'Load Balancer', value: 'load-balancer' },
        { label: 'Monitoring', value: 'monitoring' },
      ],
    },
    {
      key: 'node',
      label: 'Node',
      type: 'select',
      options: [], // Will be populated from API
    },
    {
      key: 'cpu_usage_range',
      label: 'CPU Usage',
      type: 'select',
      options: [
        { label: 'Low (0-25%)', value: '0-25' },
        { label: 'Medium (26-50%)', value: '26-50' },
        { label: 'High (51-75%)', value: '51-75' },
        { label: 'Critical (76-100%)', value: '76-100' },
      ],
    },
    {
      key: 'memory_usage_range',
      label: 'Memory Usage',
      type: 'select',
      options: [
        { label: 'Low (0-25%)', value: '0-25' },
        { label: 'Medium (26-50%)', value: '26-50' },
        { label: 'High (51-75%)', value: '51-75' },
        { label: 'Critical (76-100%)', value: '76-100' },
      ],
    },
  ],

  searchPlaceholder: 'Search containers by name, image, or service...',

  detailComponent: ContainerDetailDrawer,
  // No create/edit components - read-only for MVP

  emptyState: {
    title: 'No containers found',
    description: 'Container services are not currently running or visible to this interface.',
  },

  permissions: {
    read: 'containers:read',
    bulk: 'containers:restart', // Only restart permission for bulk operations
  },
};
