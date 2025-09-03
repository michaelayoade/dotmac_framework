/**
 * Device Management Configuration
 * Defines the complete configuration for device management pages
 */

import { ManagementPageConfig } from '@dotmac/patterns';
import {
  Server,
  CheckCircle,
  AlertTriangle,
  Wrench,
  Plus,
  Upload,
  Download,
  Wifi,
  Activity,
  MapPin,
  Clock,
} from 'lucide-react';
import { DeviceDetailDrawer } from '../components/devices/DeviceDetailDrawer';
import { CreateDeviceDrawer } from '../components/devices/CreateDeviceDrawer';
import { EditDeviceDrawer } from '../components/devices/EditDeviceDrawer';
import { StatusBadge } from '../components/common/StatusBadge';
import { formatDistance, formatBytes } from '@dotmac/utils';

export const deviceManagementConfig: ManagementPageConfig = {
  title: 'Device Management',
  entity: 'devices',
  description: 'Monitor and manage network infrastructure devices',
  apiEndpoint: '/api/admin/devices',

  metrics: [
    {
      name: 'Total Devices',
      value: '0',
      icon: Server,
      description: 'registered devices',
      color: 'primary',
    },
    {
      name: 'Online',
      value: '0',
      icon: CheckCircle,
      trend: {
        value: '+5%',
        positive: true,
      },
      description: 'active now',
      color: 'success',
    },
    {
      name: 'Alerts',
      value: '0',
      icon: AlertTriangle,
      description: 'need attention',
      color: 'warning',
    },
    {
      name: 'Maintenance',
      value: '0',
      icon: Wrench,
      description: 'scheduled',
      color: 'secondary',
    },
  ],

  tableColumns: [
    {
      key: 'hostname',
      label: 'Device',
      sortable: true,
      sticky: true,
      width: 200,
    },
    {
      key: 'device_type',
      label: 'Type',
      filterable: true,
      formatter: (value: string) => value.replace('_', ' ').toUpperCase(),
    },
    {
      key: 'status',
      label: 'Status',
      component: StatusBadge,
      filterable: true,
    },
    {
      key: 'management_ip',
      label: 'Management IP',
      sortable: true,
    },
    {
      key: 'location',
      label: 'Location',
      filterable: true,
      formatter: (value: any) => value?.name || 'Unknown',
    },
    {
      key: 'uptime',
      label: 'Uptime',
      sortable: true,
      formatter: (value: number) => formatDistance(value),
    },
    {
      key: 'cpu_usage',
      label: 'CPU Usage',
      formatter: (value: number) => `${Math.round(value)}%`,
    },
    {
      key: 'memory_usage',
      label: 'Memory',
      formatter: (value: number) => formatBytes(value),
    },
    {
      key: 'last_seen',
      label: 'Last Seen',
      sortable: true,
      formatter: (value: string) => new Date(value).toLocaleString(),
    },
  ],

  actions: [
    {
      label: 'Add Device',
      icon: Plus,
      action: 'create',
      variant: 'primary',
      permission: 'devices:create',
    },
    {
      label: 'Bulk Import',
      icon: Upload,
      action: 'import',
      variant: 'secondary',
      permission: 'devices:import',
    },
    {
      label: 'Export',
      icon: Download,
      action: 'export',
      variant: 'secondary',
    },
  ],

  bulkActions: [
    {
      label: 'Update Firmware',
      action: 'bulk_firmware_update',
      icon: Upload,
      permission: 'devices:firmware',
      confirmMessage: 'Are you sure you want to update firmware for selected devices?',
    },
    {
      label: 'Restart',
      action: 'bulk_restart',
      icon: Activity,
      permission: 'devices:restart',
      confirmMessage: 'Are you sure you want to restart selected devices?',
    },
    {
      label: 'Delete',
      action: 'bulk_delete',
      icon: AlertTriangle,
      permission: 'devices:delete',
      confirmMessage: 'Are you sure you want to delete selected devices? This cannot be undone.',
    },
  ],

  filters: [
    {
      key: 'device_type',
      label: 'Device Type',
      type: 'select',
      options: [
        { label: 'Router', value: 'router' },
        { label: 'Switch', value: 'switch' },
        { label: 'Access Point', value: 'access_point' },
        { label: 'Firewall', value: 'firewall' },
        { label: 'Load Balancer', value: 'load_balancer' },
        { label: 'ONT', value: 'ont' },
        { label: 'Server', value: 'server' },
      ],
    },
    {
      key: 'status',
      label: 'Status',
      type: 'select',
      options: [
        { label: 'Online', value: 'online' },
        { label: 'Offline', value: 'offline' },
        { label: 'Degraded', value: 'degraded' },
        { label: 'Maintenance', value: 'maintenance' },
        { label: 'Error', value: 'error' },
      ],
    },
    {
      key: 'location_id',
      label: 'Location',
      type: 'select',
      options: [], // Will be populated from API
    },
    {
      key: 'vendor',
      label: 'Vendor',
      type: 'select',
      options: [
        { label: 'Cisco', value: 'cisco' },
        { label: 'Juniper', value: 'juniper' },
        { label: 'Ubiquiti', value: 'ubiquiti' },
        { label: 'HPE', value: 'hpe' },
        { label: 'Dell', value: 'dell' },
        { label: 'Mikrotik', value: 'mikrotik' },
        { label: 'Adtran', value: 'adtran' },
      ],
    },
    {
      key: 'management_ip',
      label: 'Management IP',
      type: 'text',
      placeholder: 'e.g. 192.168.1.0/24',
    },
    {
      key: 'last_seen_range',
      label: 'Last Seen',
      type: 'daterange',
    },
  ],

  searchPlaceholder: 'Search devices by hostname, IP, or model...',

  detailComponent: DeviceDetailDrawer,
  createComponent: CreateDeviceDrawer,
  editComponent: EditDeviceDrawer,

  emptyState: {
    title: 'No devices found',
    description: 'Start by adding your network infrastructure devices to monitor and manage them.',
    action: {
      label: 'Add First Device',
      icon: Plus,
      action: 'create',
    },
  },

  permissions: {
    read: 'devices:read',
    create: 'devices:create',
    edit: 'devices:edit',
    delete: 'devices:delete',
    bulk: 'devices:bulk',
  },
};
