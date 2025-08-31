/**
 * IPAM (IP Address Management) Configuration
 * Defines the configuration for IP address and subnet management
 */

import { ManagementPageConfig } from '@dotmac/patterns';
import { 
  Network, 
  Globe, 
  Shield, 
  Zap, 
  Plus, 
  Download,
  Upload,
  Activity,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { IPAMDetailDrawer } from '../components/ipam/IPAMDetailDrawer';
import { CreateSubnetDrawer } from '../components/ipam/CreateSubnetDrawer';
import { ReserveIPDrawer } from '../components/ipam/ReserveIPDrawer';
import { StatusBadge } from '../components/common/StatusBadge';
import { UtilizationBar } from '../components/common/UtilizationBar';

export const ipamManagementConfig: ManagementPageConfig = {
  title: 'IP Address Management',
  entity: 'subnets',
  description: 'Manage IP address allocation and subnet utilization across your network',
  apiEndpoint: '/api/admin/ipam/subnets',
  
  metrics: [
    {
      name: 'Total Subnets',
      value: '0',
      icon: Network,
      description: 'managed subnets',
      color: 'primary'
    },
    {
      name: 'IP Utilization',
      value: '0%',
      icon: Activity,
      trend: {
        value: '+2.3%',
        positive: true
      },
      description: 'average usage',
      color: 'secondary'
    },
    {
      name: 'Available IPs',
      value: '0',
      icon: CheckCircle,
      description: 'ready for allocation',
      color: 'success'
    },
    {
      name: 'Reservations',
      value: '0',
      icon: Shield,
      description: 'reserved addresses',
      color: 'warning'
    }
  ],

  tableColumns: [
    {
      key: 'subnet',
      label: 'Subnet',
      sortable: true,
      sticky: true,
      width: 200
    },
    {
      key: 'description',
      label: 'Description',
      width: 250
    },
    {
      key: 'vlan_id',
      label: 'VLAN',
      sortable: true,
      filterable: true,
      formatter: (value: number) => value ? `VLAN ${value}` : 'Untagged'
    },
    {
      key: 'utilization',
      label: 'Utilization',
      component: UtilizationBar,
      sortable: true
    },
    {
      key: 'total_ips',
      label: 'Total IPs',
      sortable: true,
      formatter: (value: number) => value.toLocaleString()
    },
    {
      key: 'used_ips',
      label: 'Used',
      sortable: true,
      formatter: (value: number) => value.toLocaleString()
    },
    {
      key: 'available_ips',
      label: 'Available',
      sortable: true,
      formatter: (value: number) => value.toLocaleString()
    },
    {
      key: 'dhcp_enabled',
      label: 'DHCP',
      component: StatusBadge,
      filterable: true
    },
    {
      key: 'gateway',
      label: 'Gateway',
      sortable: true
    },
    {
      key: 'dns_servers',
      label: 'DNS',
      formatter: (value: string[]) => value?.join(', ') || 'None'
    },
    {
      key: 'location',
      label: 'Location',
      filterable: true,
      formatter: (value: any) => value?.name || 'Unassigned'
    }
  ],

  actions: [
    {
      label: 'Create Subnet',
      icon: Plus,
      action: 'create',
      variant: 'primary',
      permission: 'ipam:create'
    },
    {
      label: 'Reserve IP',
      icon: Shield,
      action: 'reserve_ip',
      variant: 'secondary',
      permission: 'ipam:reserve'
    },
    {
      label: 'Import Subnets',
      icon: Upload,
      action: 'import',
      variant: 'secondary',
      permission: 'ipam:import'
    },
    {
      label: 'Export',
      icon: Download,
      action: 'export',
      variant: 'secondary'
    }
  ],

  bulkActions: [
    {
      label: 'Update DHCP',
      action: 'bulk_dhcp_update',
      icon: Activity,
      permission: 'ipam:dhcp',
      confirmMessage: 'Update DHCP configuration for selected subnets?'
    },
    {
      label: 'Scan Utilization',
      action: 'bulk_scan',
      icon: Network,
      permission: 'ipam:scan'
    },
    {
      label: 'Delete',
      action: 'bulk_delete',
      icon: AlertCircle,
      permission: 'ipam:delete',
      confirmMessage: 'Delete selected subnets? This will remove all IP allocations.'
    }
  ],

  filters: [
    {
      key: 'vlan_id',
      label: 'VLAN',
      type: 'number',
      placeholder: 'VLAN ID'
    },
    {
      key: 'dhcp_enabled',
      label: 'DHCP Status',
      type: 'select',
      options: [
        { label: 'DHCP Enabled', value: 'true' },
        { label: 'DHCP Disabled', value: 'false' }
      ]
    },
    {
      key: 'utilization_range',
      label: 'Utilization',
      type: 'select',
      options: [
        { label: 'Low (0-25%)', value: '0-25' },
        { label: 'Medium (26-50%)', value: '26-50' },
        { label: 'High (51-75%)', value: '51-75' },
        { label: 'Critical (76-100%)', value: '76-100' }
      ]
    },
    {
      key: 'location_id',
      label: 'Location',
      type: 'select',
      options: [] // Will be populated from API
    },
    {
      key: 'subnet_type',
      label: 'Type',
      type: 'select',
      options: [
        { label: 'Management', value: 'management' },
        { label: 'Customer', value: 'customer' },
        { label: 'Infrastructure', value: 'infrastructure' },
        { label: 'DMZ', value: 'dmz' },
        { label: 'Guest', value: 'guest' }
      ]
    },
    {
      key: 'ip_version',
      label: 'IP Version',
      type: 'select',
      options: [
        { label: 'IPv4', value: '4' },
        { label: 'IPv6', value: '6' }
      ]
    }
  ],

  searchPlaceholder: 'Search subnets by CIDR, description, or gateway...',

  detailComponent: IPAMDetailDrawer,
  createComponent: CreateSubnetDrawer,
  editComponent: ReserveIPDrawer, // Custom component for IP reservations

  emptyState: {
    title: 'No subnets configured',
    description: 'Start by creating your network subnets to manage IP address allocation.',
    action: {
      label: 'Create First Subnet',
      icon: Plus,
      action: 'create'
    }
  },

  permissions: {
    read: 'ipam:read',
    create: 'ipam:create',
    edit: 'ipam:edit',
    delete: 'ipam:delete',
    bulk: 'ipam:bulk'
  }
};