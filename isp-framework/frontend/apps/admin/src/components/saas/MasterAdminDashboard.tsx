'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Server,
  Users,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Building,
  Globe,
  Shield,
} from 'lucide-react';

interface PlatformMetrics {
  totalTenants: number;
  activeTenants: number;
  pendingTenants: number;
  suspendedTenants: number;
  totalRevenueMonthly: number;
  totalRevenueAnnual: number;
  avgRevenuePerTenant: number;
  totalInfrastructureCost: number;
  platformMargin: number;
  totalApiRequests: number;
  avgResponseTimeMs: number;
  overallUptimePercentage: number;
  activeDeployments: number;
  pendingDeployments: number;
  failedDeployments: number;
}

interface TenantHealthSummary {
  tenantId: string;
  tenantName: string;
  status: string;
  healthScore: number;
  uptimePercentage?: number;
  lastHealthCheck: string;
  activeAlerts: number;
  criticalIssues: number;
  monthlyRevenue: number;
  monthlyyCost: number;
  customersUtilization: number;
  storageUtilization: number;
  avgResponseTimeMs?: number;
  errorRate?: number;
}

interface InfrastructureOverview {
  totalInstances: number;
  runningInstances: number;
  stoppedInstances: number;
  cloudDistribution: Record<string, number>;
  regionDistribution: Record<string, number>;
  totalCpuCores: number;
  totalMemoryGb: number;
  totalStorageGb: number;
  totalMonthlyCost: number;
  costByProvider: Record<string, number>;
  costTrendPercentage: number;
}

interface PlatformOverview {
  metrics: PlatformMetrics;
  tenantHealth: TenantHealthSummary[];
  infrastructure: InfrastructureOverview;
  recentTenantSignups: number;
  recentChurnRate: number;
  platformHealthScore: number;
  activeIncidents: number;
  generatedAt: string;
}

export function MasterAdminDashboard() {
  const [platformData, setPlatformData] = useState<PlatformOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPlatformOverview();
  }, []);

  const fetchPlatformOverview = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/master-admin/dashboard/overview', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('authToken')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch platform overview');
      }

      const data = await response.json();
      setPlatformData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);

  const formatNumber = (num: number) => new Intl.NumberFormat('en-US').format(num);

  const getHealthScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'suspended':
        return 'bg-red-100 text-red-800';
      case 'maintenance':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <div className='animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600'></div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className='max-w-2xl mx-auto mt-8'>
        <AlertTriangle className='h-4 w-4' />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!platformData) return null;

  const { metrics, tenantHealth, infrastructure } = platformData;

  return (
    <div className='min-h-screen bg-gray-50'>
      {/* Header */}
      <div className='bg-white shadow-sm border-b'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
          <div className='flex justify-between items-center py-6'>
            <div>
              <h1 className='text-3xl font-bold text-gray-900'>Master Admin Portal</h1>
              <p className='mt-1 text-sm text-gray-500'>
                Platform operations and tenant management dashboard
              </p>
            </div>
            <div className='flex items-center space-x-4'>
              <Badge
                className={`px-3 py-1 ${getHealthScoreColor(platformData.platformHealthScore)}`}
              >
                Platform Health: {platformData.platformHealthScore}%
              </Badge>
              {platformData.activeIncidents > 0 && (
                <Badge className='bg-red-100 text-red-800'>
                  {platformData.activeIncidents} Active Incidents
                </Badge>
              )}
              <Button onClick={fetchPlatformOverview} variant='outline' size='sm'>
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'>
        {/* Key Metrics */}
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8'>
          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center'>
                <div className='flex-shrink-0'>
                  <Building className='h-8 w-8 text-blue-600' />
                </div>
                <div className='ml-4'>
                  <p className='text-sm font-medium text-gray-500'>Total Tenants</p>
                  <p className='text-2xl font-semibold text-gray-900'>
                    {formatNumber(metrics.totalTenants)}
                  </p>
                  <p className='text-xs text-green-600'>
                    +{platformData.recentTenantSignups} this month
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center'>
                <div className='flex-shrink-0'>
                  <DollarSign className='h-8 w-8 text-green-600' />
                </div>
                <div className='ml-4'>
                  <p className='text-sm font-medium text-gray-500'>Monthly Revenue</p>
                  <p className='text-2xl font-semibold text-gray-900'>
                    {formatCurrency(metrics.totalRevenueMonthly)}
                  </p>
                  <p className='text-xs text-gray-600'>{metrics.platformMargin}% margin</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center'>
                <div className='flex-shrink-0'>
                  <Server className='h-8 w-8 text-purple-600' />
                </div>
                <div className='ml-4'>
                  <p className='text-sm font-medium text-gray-500'>Infrastructure</p>
                  <p className='text-2xl font-semibold text-gray-900'>
                    {infrastructure.runningInstances}/{infrastructure.totalInstances}
                  </p>
                  <p className='text-xs text-gray-600'>Active instances</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center'>
                <div className='flex-shrink-0'>
                  <TrendingUp className='h-8 w-8 text-orange-600' />
                </div>
                <div className='ml-4'>
                  <p className='text-sm font-medium text-gray-500'>Uptime</p>
                  <p className='text-2xl font-semibold text-gray-900'>
                    {metrics.overallUptimePercentage}%
                  </p>
                  <p className='text-xs text-gray-600'>
                    Avg {metrics.avgResponseTimeMs}ms response
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue='overview' className='space-y-6'>
          <TabsList className='grid w-full grid-cols-5'>
            <TabsTrigger value='overview'>Overview</TabsTrigger>
            <TabsTrigger value='tenants'>Tenant Health</TabsTrigger>
            <TabsTrigger value='infrastructure'>Infrastructure</TabsTrigger>
            <TabsTrigger value='revenue'>Revenue</TabsTrigger>
            <TabsTrigger value='operations'>Operations</TabsTrigger>
          </TabsList>

          <TabsContent value='overview' className='space-y-6'>
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              {/* Platform Status */}
              <Card>
                <CardHeader>
                  <CardTitle>Platform Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-4'>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>Active Tenants</span>
                      <Badge className='bg-green-100 text-green-800'>{metrics.activeTenants}</Badge>
                    </div>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>Pending Deployment</span>
                      <Badge className='bg-yellow-100 text-yellow-800'>
                        {metrics.pendingDeployments}
                      </Badge>
                    </div>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>Failed Deployments</span>
                      <Badge className='bg-red-100 text-red-800'>{metrics.failedDeployments}</Badge>
                    </div>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>Churn Rate</span>
                      <span className='text-sm text-gray-600'>{platformData.recentChurnRate}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Revenue Breakdown */}
              <Card>
                <CardHeader>
                  <CardTitle>Revenue Overview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-4'>
                    <div>
                      <div className='flex justify-between items-center mb-2'>
                        <span className='text-sm font-medium'>Annual Revenue</span>
                        <span className='text-sm font-semibold'>
                          {formatCurrency(metrics.totalRevenueAnnual)}
                        </span>
                      </div>
                      <div className='w-full bg-gray-200 rounded-full h-2'>
                        <div
                          className='bg-blue-600 h-2 rounded-full'
                          style={{ width: '75%' }}
                        ></div>
                      </div>
                    </div>
                    <div>
                      <div className='flex justify-between items-center mb-2'>
                        <span className='text-sm font-medium'>Avg Revenue/Tenant</span>
                        <span className='text-sm font-semibold'>
                          {formatCurrency(metrics.avgRevenuePerTenant)}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className='flex justify-between items-center mb-2'>
                        <span className='text-sm font-medium'>Infrastructure Cost</span>
                        <span className='text-sm font-semibold text-red-600'>
                          {formatCurrency(metrics.totalInfrastructureCost)}
                        </span>
                      </div>
                    </div>
                    <div className='pt-2 border-t'>
                      <div className='flex justify-between items-center'>
                        <span className='text-sm font-medium'>Profit Margin</span>
                        <span className='text-sm font-semibold text-green-600'>
                          {metrics.platformMargin}%
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value='tenants' className='space-y-6'>
            <Card>
              <CardHeader>
                <CardTitle>Tenant Health Overview</CardTitle>
                <p className='text-sm text-gray-600'>
                  Monitor health and performance across all tenant instances
                </p>
              </CardHeader>
              <CardContent>
                <div className='overflow-x-auto'>
                  <table className='min-w-full divide-y divide-gray-200'>
                    <thead className='bg-gray-50'>
                      <tr>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Tenant
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Status
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Health Score
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Uptime
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Revenue
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Alerts
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className='bg-white divide-y divide-gray-200'>
                      {tenantHealth.map((tenant) => (
                        <tr key={tenant.tenantId} className='hover:bg-gray-50'>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            <div>
                              <div className='text-sm font-medium text-gray-900'>
                                {tenant.tenantName}
                              </div>
                              <div className='text-xs text-gray-500'>{tenant.tenantId}</div>
                            </div>
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            <Badge className={getStatusColor(tenant.status)}>{tenant.status}</Badge>
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            <Badge className={getHealthScoreColor(tenant.healthScore)}>
                              {tenant.healthScore}%
                            </Badge>
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-900'>
                            {tenant.uptimePercentage
                              ? `${tenant.uptimePercentage.toFixed(1)}%`
                              : 'N/A'}
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-900'>
                            {formatCurrency(tenant.monthlyRevenue)}
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            {tenant.activeAlerts > 0 ? (
                              <Badge className='bg-red-100 text-red-800'>
                                {tenant.activeAlerts} alerts
                              </Badge>
                            ) : (
                              <CheckCircle className='h-4 w-4 text-green-600' />
                            )}
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap text-sm font-medium'>
                            <Button variant='outline' size='sm'>
                              Manage
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value='infrastructure' className='space-y-6'>
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              {/* Cloud Distribution */}
              <Card>
                <CardHeader>
                  <CardTitle>Cloud Provider Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-4'>
                    {Object.entries(infrastructure.cloudDistribution).map(([provider, count]) => (
                      <div key={provider} className='flex items-center justify-between'>
                        <div className='flex items-center'>
                          <Globe className='h-4 w-4 text-gray-500 mr-2' />
                          <span className='text-sm font-medium capitalize'>{provider}</span>
                        </div>
                        <div className='flex items-center space-x-2'>
                          <span className='text-sm text-gray-600'>{count} instances</span>
                          <span className='text-sm text-gray-500'>
                            {formatCurrency(infrastructure.costByProvider[provider] || 0)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Resource Summary */}
              <Card>
                <CardHeader>
                  <CardTitle>Resource Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='grid grid-cols-2 gap-4'>
                    <div className='text-center'>
                      <p className='text-2xl font-semibold text-gray-900'>
                        {formatNumber(infrastructure.totalCpuCores)}
                      </p>
                      <p className='text-xs text-gray-500'>CPU Cores</p>
                    </div>
                    <div className='text-center'>
                      <p className='text-2xl font-semibold text-gray-900'>
                        {formatNumber(infrastructure.totalMemoryGb)}GB
                      </p>
                      <p className='text-xs text-gray-500'>Memory</p>
                    </div>
                    <div className='text-center'>
                      <p className='text-2xl font-semibold text-gray-900'>
                        {formatNumber(infrastructure.totalStorageGb)}GB
                      </p>
                      <p className='text-xs text-gray-500'>Storage</p>
                    </div>
                    <div className='text-center'>
                      <p className='text-2xl font-semibold text-gray-900'>
                        {formatCurrency(infrastructure.totalMonthlyCost)}
                      </p>
                      <p className='text-xs text-gray-500'>Monthly Cost</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value='revenue' className='space-y-6'>
            <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
              <Card>
                <CardHeader>
                  <CardTitle>Monthly Recurring Revenue</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='text-center'>
                    <p className='text-3xl font-bold text-green-600'>
                      {formatCurrency(metrics.totalRevenueMonthly)}
                    </p>
                    <p className='text-sm text-gray-500 mt-1'>Current MRR</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Annual Revenue</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='text-center'>
                    <p className='text-3xl font-bold text-blue-600'>
                      {formatCurrency(metrics.totalRevenueAnnual)}
                    </p>
                    <p className='text-sm text-gray-500 mt-1'>ARR</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Average per Tenant</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='text-center'>
                    <p className='text-3xl font-bold text-purple-600'>
                      {formatCurrency(metrics.avgRevenuePerTenant)}
                    </p>
                    <p className='text-sm text-gray-500 mt-1'>ARPU</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value='operations' className='space-y-6'>
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              {/* System Operations */}
              <Card>
                <CardHeader>
                  <CardTitle>System Operations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-4'>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>API Requests (Total)</span>
                      <span className='text-sm text-gray-900'>
                        {formatNumber(metrics.totalApiRequests)}
                      </span>
                    </div>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>Avg Response Time</span>
                      <span className='text-sm text-gray-900'>{metrics.avgResponseTimeMs}ms</span>
                    </div>
                    <div className='flex justify-between items-center'>
                      <span className='text-sm font-medium'>Overall Uptime</span>
                      <span className='text-sm text-green-600'>
                        {metrics.overallUptimePercentage}%
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Deployment Status */}
              <Card>
                <CardHeader>
                  <CardTitle>Deployment Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-4'>
                    <div className='flex items-center justify-between'>
                      <div className='flex items-center'>
                        <CheckCircle className='h-4 w-4 text-green-600 mr-2' />
                        <span className='text-sm font-medium'>Active</span>
                      </div>
                      <Badge className='bg-green-100 text-green-800'>
                        {metrics.activeDeployments}
                      </Badge>
                    </div>
                    <div className='flex items-center justify-between'>
                      <div className='flex items-center'>
                        <Clock className='h-4 w-4 text-yellow-600 mr-2' />
                        <span className='text-sm font-medium'>Pending</span>
                      </div>
                      <Badge className='bg-yellow-100 text-yellow-800'>
                        {metrics.pendingDeployments}
                      </Badge>
                    </div>
                    <div className='flex items-center justify-between'>
                      <div className='flex items-center'>
                        <AlertTriangle className='h-4 w-4 text-red-600 mr-2' />
                        <span className='text-sm font-medium'>Failed</span>
                      </div>
                      <Badge className='bg-red-100 text-red-800'>{metrics.failedDeployments}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
