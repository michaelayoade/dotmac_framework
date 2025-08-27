'use client';

import React, { useState, useEffect } from 'react';
import { useAuthToken } from '../../hooks/useSSRSafeStorage';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Search,
  Plus,
  Settings,
  Users,
  DollarSign,
  Server,
  AlertTriangle,
  CheckCircle,
  MoreHorizontal,
  PlayCircle,
  PauseCircle,
  StopCircle,
  RefreshCw,
} from 'lucide-react';

interface Tenant {
  id: string;
  tenantId: string;
  name: string;
  displayName: string;
  description?: string;
  primaryContactEmail: string;
  primaryContactName: string;
  status: string;
  subscriptionTier: string;
  billingCycle: string;
  createdAt: string;
  updatedAt: string;
  maxCustomers: number;
  maxServices: number;
  maxStorageGb: number;
  customDomain?: string;
  isActive: boolean;
  canBeManaged: boolean;
}

interface TenantListResponse {
  tenants: Tenant[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

interface OnboardingRequest {
  tenantInfo: {
    name: string;
    displayName: string;
    description: string;
    primaryContactEmail: string;
    primaryContactName: string;
    businessPhone?: string;
    subscriptionTier: string;
    billingCycle: string;
    maxCustomers: number;
    maxServices: number;
    maxStorageGb: number;
    customDomain?: string;
  };
  preferredCloudProvider: string;
  preferredRegion: string;
  instanceSize: string;
  enabledFeatures: string[];
  brandingConfig?: Record<string, any>;
  specialRequirements?: string;
}

export function TenantManagement() {
  const [authToken, , tokenLoading] = useAuthToken();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [showOnboardingDialog, setShowOnboardingDialog] = useState(false);
  const [onboardingData, setOnboardingData] = useState<Partial<OnboardingRequest>>({
    tenantInfo: {
      name: '',
      displayName: '',
      description: '',
      primaryContactEmail: '',
      primaryContactName: '',
      subscriptionTier: 'standard',
      billingCycle: 'monthly',
      maxCustomers: 1000,
      maxServices: 10000,
      maxStorageGb: 100,
    },
    preferredCloudProvider: 'aws',
    preferredRegion: 'us-east-1',
    instanceSize: 'medium',
    enabledFeatures: ['customer_portal', 'billing_automation'],
  });

  useEffect(() => {
    if (authToken && !tokenLoading) {
      fetchTenants();
    }
  }, [authToken, tokenLoading, currentPage, searchQuery, statusFilter, tierFilter]);

  const fetchTenants = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString(),
      });

      if (searchQuery) params.append('search', searchQuery);
      if (statusFilter) params.append('status', statusFilter);
      if (tierFilter) params.append('subscription_tier', tierFilter);

      const response = await fetch(`/api/v1/master-admin/tenants?${params}`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch tenants');
      }

      const data: TenantListResponse = await response.json();
      setTenants(data.tenants);
      setTotalCount(data.totalCount);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (tenantId: string, newStatus: string, reason?: string) => {
    try {
      const response = await fetch(`/api/v1/master-admin/tenants/${tenantId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ status: newStatus, reason }),
      });

      if (!response.ok) {
        throw new Error('Failed to update tenant status');
      }

      // Refresh the tenants list
      fetchTenants();
    } catch (err) {
      console.error('Error updating tenant status:', err);
    }
  };

  const handleOnboarding = async () => {
    try {
      const response = await fetch('/api/v1/master-admin/tenants/onboard', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(onboardingData),
      });

      if (!response.ok) {
        throw new Error('Failed to initiate tenant onboarding');
      }

      const result = await response.json();
      console.log('Onboarding initiated:', result);

      setShowOnboardingDialog(false);
      fetchTenants();
    } catch (err) {
      console.error('Error initiating onboarding:', err);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'provisioning':
        return 'bg-blue-100 text-blue-800';
      case 'suspended':
        return 'bg-red-100 text-red-800';
      case 'maintenance':
        return 'bg-purple-100 text-purple-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return <CheckCircle className='h-4 w-4' />;
      case 'pending':
        return <RefreshCw className='h-4 w-4' />;
      case 'provisioning':
        return <RefreshCw className='h-4 w-4 animate-spin' />;
      case 'suspended':
        return <PauseCircle className='h-4 w-4' />;
      case 'maintenance':
        return <Settings className='h-4 w-4' />;
      case 'cancelled':
        return <StopCircle className='h-4 w-4' />;
      case 'failed':
        return <AlertTriangle className='h-4 w-4' />;
      default:
        return <RefreshCw className='h-4 w-4' />;
    }
  };

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex justify-between items-center'>
        <div>
          <h2 className='text-2xl font-bold text-gray-900'>Tenant Management</h2>
          <p className='text-gray-600'>Manage ISP customer tenants and onboarding workflows</p>
        </div>
        <Dialog open={showOnboardingDialog} onOpenChange={setShowOnboardingDialog}>
          <DialogTrigger asChild>
            <Button className='flex items-center space-x-2'>
              <Plus className='h-4 w-4' />
              <span>Onboard Tenant</span>
            </Button>
          </DialogTrigger>
          <DialogContent className='max-w-2xl max-h-screen overflow-y-auto'>
            <DialogHeader>
              <DialogTitle>Tenant Onboarding</DialogTitle>
              <DialogDescription>
                Set up a new ISP customer with their DotMac instance
              </DialogDescription>
            </DialogHeader>
            <div className='space-y-4 py-4'>
              {/* Basic Information */}
              <div className='space-y-3'>
                <h4 className='font-semibold'>Basic Information</h4>
                <div className='grid grid-cols-2 gap-3'>
                  <div>
                    <Label>Internal Name</Label>
                    <Input
                      value={onboardingData.tenantInfo?.name || ''}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            name: e.target.value,
                          },
                        })
                      }
                      placeholder='metro-isp-solutions'
                    />
                  </div>
                  <div>
                    <Label>Display Name</Label>
                    <Input
                      value={onboardingData.tenantInfo?.displayName || ''}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            displayName: e.target.value,
                          },
                        })
                      }
                      placeholder='Metro ISP Solutions'
                    />
                  </div>
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea
                    value={onboardingData.tenantInfo?.description || ''}
                    onChange={(e) =>
                      setOnboardingData({
                        ...onboardingData,
                        tenantInfo: {
                          ...onboardingData.tenantInfo!,
                          description: e.target.value,
                        },
                      })
                    }
                    placeholder='Mid-size ISP serving metropolitan area'
                  />
                </div>
                <div className='grid grid-cols-2 gap-3'>
                  <div>
                    <Label>Primary Contact Name</Label>
                    <Input
                      value={onboardingData.tenantInfo?.primaryContactName || ''}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            primaryContactName: e.target.value,
                          },
                        })
                      }
                      placeholder='John Smith'
                    />
                  </div>
                  <div>
                    <Label>Primary Contact Email</Label>
                    <Input
                      type='email'
                      value={onboardingData.tenantInfo?.primaryContactEmail || ''}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            primaryContactEmail: e.target.value,
                          },
                        })
                      }
                      placeholder='john@metroisp.com'
                    />
                  </div>
                </div>
              </div>

              {/* Subscription Settings */}
              <div className='space-y-3'>
                <h4 className='font-semibold'>Subscription Settings</h4>
                <div className='grid grid-cols-2 gap-3'>
                  <div>
                    <Label>Subscription Tier</Label>
                    <Select
                      value={onboardingData.tenantInfo?.subscriptionTier || 'standard'}
                      onValueChange={(value) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            subscriptionTier: value,
                          },
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value='starter'>Starter</SelectItem>
                        <SelectItem value='standard'>Standard</SelectItem>
                        <SelectItem value='premium'>Premium</SelectItem>
                        <SelectItem value='enterprise'>Enterprise</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Billing Cycle</Label>
                    <Select
                      value={onboardingData.tenantInfo?.billingCycle || 'monthly'}
                      onValueChange={(value) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            billingCycle: value,
                          },
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value='monthly'>Monthly</SelectItem>
                        <SelectItem value='annual'>Annual</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Infrastructure Settings */}
              <div className='space-y-3'>
                <h4 className='font-semibold'>Infrastructure Settings</h4>
                <div className='grid grid-cols-3 gap-3'>
                  <div>
                    <Label>Cloud Provider</Label>
                    <Select
                      value={onboardingData.preferredCloudProvider || 'aws'}
                      onValueChange={(value) =>
                        setOnboardingData({
                          ...onboardingData,
                          preferredCloudProvider: value,
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value='aws'>AWS</SelectItem>
                        <SelectItem value='azure'>Azure</SelectItem>
                        <SelectItem value='gcp'>Google Cloud</SelectItem>
                        <SelectItem value='digitalocean'>DigitalOcean</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Region</Label>
                    <Select
                      value={onboardingData.preferredRegion || 'us-east-1'}
                      onValueChange={(value) =>
                        setOnboardingData({
                          ...onboardingData,
                          preferredRegion: value,
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value='us-east-1'>US East (Virginia)</SelectItem>
                        <SelectItem value='us-west-2'>US West (Oregon)</SelectItem>
                        <SelectItem value='eu-west-1'>EU West (Ireland)</SelectItem>
                        <SelectItem value='ap-southeast-1'>Asia Pacific (Singapore)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Instance Size</Label>
                    <Select
                      value={onboardingData.instanceSize || 'medium'}
                      onValueChange={(value) =>
                        setOnboardingData({
                          ...onboardingData,
                          instanceSize: value,
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value='small'>Small</SelectItem>
                        <SelectItem value='medium'>Medium</SelectItem>
                        <SelectItem value='large'>Large</SelectItem>
                        <SelectItem value='xlarge'>Extra Large</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Resource Limits */}
              <div className='space-y-3'>
                <h4 className='font-semibold'>Resource Limits</h4>
                <div className='grid grid-cols-3 gap-3'>
                  <div>
                    <Label>Max Customers</Label>
                    <Input
                      type='number'
                      value={onboardingData.tenantInfo?.maxCustomers || 1000}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            maxCustomers: parseInt(e.target.value) || 1000,
                          },
                        })
                      }
                    />
                  </div>
                  <div>
                    <Label>Max Services</Label>
                    <Input
                      type='number'
                      value={onboardingData.tenantInfo?.maxServices || 10000}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            maxServices: parseInt(e.target.value) || 10000,
                          },
                        })
                      }
                    />
                  </div>
                  <div>
                    <Label>Storage (GB)</Label>
                    <Input
                      type='number'
                      value={onboardingData.tenantInfo?.maxStorageGb || 100}
                      onChange={(e) =>
                        setOnboardingData({
                          ...onboardingData,
                          tenantInfo: {
                            ...onboardingData.tenantInfo!,
                            maxStorageGb: parseInt(e.target.value) || 100,
                          },
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant='outline' onClick={() => setShowOnboardingDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleOnboarding}>Start Onboarding</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className='p-4'>
          <div className='flex flex-wrap gap-4 items-center'>
            <div className='flex-1 min-w-0'>
              <div className='relative'>
                <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
                <Input
                  placeholder='Search tenants...'
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className='pl-10'
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className='w-48'>
                <SelectValue placeholder='Filter by status' />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value=''>All statuses</SelectItem>
                <SelectItem value='active'>Active</SelectItem>
                <SelectItem value='pending'>Pending</SelectItem>
                <SelectItem value='provisioning'>Provisioning</SelectItem>
                <SelectItem value='suspended'>Suspended</SelectItem>
                <SelectItem value='maintenance'>Maintenance</SelectItem>
              </SelectContent>
            </Select>
            <Select value={tierFilter} onValueChange={setTierFilter}>
              <SelectTrigger className='w-48'>
                <SelectValue placeholder='Filter by tier' />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value=''>All tiers</SelectItem>
                <SelectItem value='starter'>Starter</SelectItem>
                <SelectItem value='standard'>Standard</SelectItem>
                <SelectItem value='premium'>Premium</SelectItem>
                <SelectItem value='enterprise'>Enterprise</SelectItem>
              </SelectContent>
            </Select>
            <Button variant='outline' onClick={fetchTenants}>
              <RefreshCw className='h-4 w-4 mr-2' />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tenants Table */}
      <Card>
        <CardHeader>
          <CardTitle>Tenants ({totalCount})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className='flex items-center justify-center h-64'>
              <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
            </div>
          ) : error ? (
            <div className='text-center py-12'>
              <AlertTriangle className='h-12 w-12 text-red-500 mx-auto mb-4' />
              <p className='text-gray-600'>{error}</p>
              <Button onClick={fetchTenants} className='mt-4'>
                Try Again
              </Button>
            </div>
          ) : (
            <div className='overflow-x-auto'>
              <table className='min-w-full divide-y divide-gray-200'>
                <thead className='bg-gray-50'>
                  <tr>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Tenant
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Contact
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Status
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Subscription
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Limits
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Created
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className='bg-white divide-y divide-gray-200'>
                  {tenants.map((tenant) => (
                    <tr key={tenant.id} className='hover:bg-gray-50'>
                      <td className='px-6 py-4 whitespace-nowrap'>
                        <div>
                          <div className='text-sm font-medium text-gray-900'>
                            {tenant.displayName}
                          </div>
                          <div className='text-xs text-gray-500'>{tenant.tenantId}</div>
                          {tenant.customDomain && (
                            <div className='text-xs text-blue-600'>{tenant.customDomain}</div>
                          )}
                        </div>
                      </td>
                      <td className='px-6 py-4 whitespace-nowrap'>
                        <div>
                          <div className='text-sm text-gray-900'>{tenant.primaryContactName}</div>
                          <div className='text-xs text-gray-500'>{tenant.primaryContactEmail}</div>
                        </div>
                      </td>
                      <td className='px-6 py-4 whitespace-nowrap'>
                        <Badge className={getStatusColor(tenant.status)}>
                          <div className='flex items-center space-x-1'>
                            {getStatusIcon(tenant.status)}
                            <span className='capitalize'>{tenant.status}</span>
                          </div>
                        </Badge>
                      </td>
                      <td className='px-6 py-4 whitespace-nowrap'>
                        <div className='text-sm text-gray-900 capitalize'>
                          {tenant.subscriptionTier}
                        </div>
                        <div className='text-xs text-gray-500 capitalize'>
                          {tenant.billingCycle}
                        </div>
                      </td>
                      <td className='px-6 py-4 whitespace-nowrap'>
                        <div className='text-xs space-y-1'>
                          <div className='flex items-center'>
                            <Users className='h-3 w-3 mr-1' />
                            {tenant.maxCustomers.toLocaleString()}
                          </div>
                          <div className='flex items-center'>
                            <Server className='h-3 w-3 mr-1' />
                            {tenant.maxStorageGb}GB
                          </div>
                        </div>
                      </td>
                      <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                        {formatDate(tenant.createdAt)}
                      </td>
                      <td className='px-6 py-4 whitespace-nowrap text-sm font-medium'>
                        <div className='flex items-center space-x-2'>
                          {tenant.status === 'active' && (
                            <Button
                              variant='outline'
                              size='sm'
                              onClick={() =>
                                handleStatusUpdate(
                                  tenant.tenantId,
                                  'suspended',
                                  'Administrative suspension'
                                )
                              }
                            >
                              <PauseCircle className='h-3 w-3' />
                            </Button>
                          )}
                          {tenant.status === 'suspended' && (
                            <Button
                              variant='outline'
                              size='sm'
                              onClick={() =>
                                handleStatusUpdate(tenant.tenantId, 'active', 'Reactivation')
                              }
                            >
                              <PlayCircle className='h-3 w-3' />
                            </Button>
                          )}
                          <Button variant='outline' size='sm'>
                            <Settings className='h-3 w-3' />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalCount > pageSize && (
        <div className='flex items-center justify-between'>
          <p className='text-sm text-gray-700'>
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, totalCount)} of {totalCount} results
          </p>
          <div className='flex space-x-2'>
            <Button
              variant='outline'
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <Button
              variant='outline'
              onClick={() =>
                setCurrentPage(Math.min(Math.ceil(totalCount / pageSize), currentPage + 1))
              }
              disabled={currentPage >= Math.ceil(totalCount / pageSize)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
