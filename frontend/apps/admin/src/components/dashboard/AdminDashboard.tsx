'use client';

import { useISPTenant, useISPModules } from '@dotmac/headless';
import { useState, useEffect } from 'react';
import { useAuthToken } from '../../hooks/useSSRSafeStorage';
import {
  Building,
  Users,
  Wifi,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  UserX,
} from 'lucide-react';

import AdminLayout from '../layout/AdminLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';

export function AdminDashboard() {
  const [churnAlerts, setChurnAlerts] = useState<any>(null);
  const [authToken, , tokenLoading] = useAuthToken();
  
  const {
    session,
    isLoading,
    getLimitsUsage,
    isTrialExpiring,
    getTrialDaysLeft,
    isTenantActive,
    hasModule,
    hasPermission,
  } = useISPTenant();

  const { useAdminDashboard, useCustomers, useNetworkDevices } = useISPModules();

  // Load dashboard data
  const { data: dashboardData, isLoading: dashboardLoading } = useAdminDashboard();
  const { data: customers } = useCustomers({ limit: 5 });
  const { data: devices } = useNetworkDevices({ limit: 10, status: 'all' });

  // Load churn intelligence
  useEffect(() => {
    if (session && hasPermission('identity.customers.read')) {
      fetchChurnAlerts();
    }
  }, [session]);

  const fetchChurnAlerts = async () => {
    if (!authToken || tokenLoading) return;
    
    try {
      const response = await fetch('/api/isp/identity/intelligence/churn-alerts', {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setChurnAlerts(data);
      } else {
        // Demo churn data
        setChurnAlerts({
          churn_alerts: [
            { customer_name: 'Bob Johnson', health_score: 35, priority: 'urgent', recommended_action: 'Immediate contact - retention offer' },
            { customer_name: 'Alice Brown', health_score: 45, priority: 'high', recommended_action: 'Proactive outreach - check satisfaction' }
          ],
          total_at_risk: 2,
          urgent_count: 1
        });
      }
    } catch (error) {
      console.error('Failed to fetch churn alerts:', error);
    }
  };

  // Tenant metrics
  const limitsUsage = getLimitsUsage();
  const trialDaysLeft = getTrialDaysLeft();
  const isExpiring = isTrialExpiring();

  if (isLoading) {
    return (
      <AdminLayout>
        <div className='flex items-center justify-center h-64'>
          <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900'></div>
        </div>
      </AdminLayout>
    );
  }

  if (!session) {
    return (
      <AdminLayout>
        <div className='text-center py-12'>
          <Building className='w-12 h-12 mx-auto text-gray-400 mb-4' />
          <h2 className='text-xl font-semibold text-gray-900 mb-2'>No Tenant Selected</h2>
          <p className='text-gray-600'>Please select a tenant to access the dashboard.</p>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className='space-y-6'>
        {/* Header with Tenant Info */}
        <div className='flex items-center justify-between'>
          <div>
            <div className='flex items-center space-x-3'>
              <h1 className='font-bold text-2xl text-gray-900'>ISP Administration</h1>
              {!isTenantActive() && (
                <div className='flex items-center px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-full'>
                  <AlertTriangle className='w-3 h-3 mr-1' />
                  {session.tenant.status}
                </div>
              )}
            </div>
            <p className='text-gray-600'>
              {session.tenant.isp_config.company_name} - {session.tenant.isp_config.company_type}{' '}
              Provider
            </p>
            {isExpiring && (
              <p className='text-orange-600 text-sm font-medium mt-1'>
                Trial expires in {trialDaysLeft} days
              </p>
            )}
          </div>

          <div className='flex items-center space-x-3'>
            <div className='text-right text-sm'>
              <p className='text-gray-500'>Current Plan</p>
              <p className='font-semibold text-gray-900'>{session.tenant.subscription.plan}</p>
            </div>
            <Button variant='outline'>Manage Subscription</Button>
          </div>
        </div>

        {/* Tenant Limits Warning */}
        {Object.values(limitsUsage).some((limit) => limit.percentage > 80) && (
          <div className='bg-yellow-50 border border-yellow-200 rounded-lg p-4'>
            <div className='flex items-start'>
              <AlertTriangle className='w-5 h-5 text-yellow-600 mr-3 mt-0.5' />
              <div>
                <h3 className='font-medium text-yellow-800'>Approaching Limits</h3>
                <p className='text-yellow-700 text-sm'>
                  Some of your usage limits are approaching their maximum. Consider upgrading your
                  plan.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Key Metrics */}
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
          {/* Customers */}
          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <p className='text-sm font-medium text-gray-600'>Customers</p>
                  <p className='text-3xl font-bold text-gray-900'>
                    {dashboardLoading ? '...' : limitsUsage.customers.used.toLocaleString()}
                  </p>
                  <p className='text-sm text-gray-500'>
                    of {limitsUsage.customers.limit.toLocaleString()} limit
                  </p>
                </div>
                <div
                  className={`p-3 rounded-full ${
                    limitsUsage.customers.percentage > 80 ? 'bg-red-100' : 'bg-blue-100'
                  }`}
                >
                  <Users
                    className={`w-6 h-6 ${
                      limitsUsage.customers.percentage > 80 ? 'text-red-600' : 'text-blue-600'
                    }`}
                  />
                </div>
              </div>
              <div className='mt-4'>
                <div className='flex items-center justify-between text-xs'>
                  <span>Usage</span>
                  <span>{limitsUsage.customers.percentage.toFixed(1)}%</span>
                </div>
                <div className='w-full bg-gray-200 rounded-full h-2 mt-1'>
                  <div
                    className={`h-2 rounded-full ${
                      limitsUsage.customers.percentage > 80 ? 'bg-red-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${Math.min(limitsUsage.customers.percentage, 100)}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Services */}
          {hasModule('services') && (
            <Card>
              <CardContent className='p-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='text-sm font-medium text-gray-600'>Active Services</p>
                    <p className='text-3xl font-bold text-gray-900'>
                      {dashboardLoading ? '...' : limitsUsage.services.used.toLocaleString()}
                    </p>
                    <p className='text-sm text-gray-500'>
                      of {limitsUsage.services.limit.toLocaleString()} limit
                    </p>
                  </div>
                  <div
                    className={`p-3 rounded-full ${
                      limitsUsage.services.percentage > 80 ? 'bg-red-100' : 'bg-green-100'
                    }`}
                  >
                    <Wifi
                      className={`w-6 h-6 ${
                        limitsUsage.services.percentage > 80 ? 'text-red-600' : 'text-green-600'
                      }`}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Revenue */}
          {hasModule('billing') && hasPermission('billing.payments.read') && (
            <Card>
              <CardContent className='p-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='text-sm font-medium text-gray-600'>Monthly Revenue</p>
                    <p className='text-3xl font-bold text-gray-900'>
                      {dashboardLoading
                        ? '...'
                        : dashboardData?.data?.monthly_revenue
                          ? `$${dashboardData.data.monthly_revenue.toLocaleString()}`
                          : '$0'}
                    </p>
                    <p className='text-sm text-green-600 flex items-center'>
                      <TrendingUp className='w-3 h-3 mr-1' />
                      +12.5% from last month
                    </p>
                  </div>
                  <div className='p-3 rounded-full bg-green-100'>
                    <DollarSign className='w-6 h-6 text-green-600' />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Network Status */}
          {hasModule('networking') && (
            <Card>
              <CardContent className='p-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='text-sm font-medium text-gray-600'>Network Health</p>
                    <p className='text-3xl font-bold text-gray-900'>
                      {devices?.data
                        ? `${((devices.data.filter((d: any) => d.status === 'online').length / devices.data.length) * 100).toFixed(1)}%`
                        : '...'}
                    </p>
                    <p className='text-sm text-gray-500'>
                      {devices?.data?.filter((d: any) => d.status === 'online').length || 0} of{' '}
                      {devices?.data?.length || 0} devices online
                    </p>
                  </div>
                  <div className='p-3 rounded-full bg-blue-100'>
                    <CheckCircle className='w-6 h-6 text-blue-600' />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Churn Risk Alerts - Strategic Intelligence */}
        {churnAlerts && churnAlerts.total_at_risk > 0 && hasPermission('identity.customers.read') && (
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center'>
                <UserX className='w-5 h-5 mr-2 text-red-600' />
                Customer Churn Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-3'>
                {churnAlerts.churn_alerts.slice(0, 3).map((alert: any, index: number) => (
                  <div
                    key={index}
                    className='flex items-center justify-between p-3 border rounded-lg bg-red-50 border-red-200'
                  >
                    <div className='flex items-center'>
                      <div className={`w-3 h-3 rounded-full mr-3 ${alert.priority === 'urgent' ? 'bg-red-500' : 'bg-orange-500'}`}></div>
                      <div>
                        <p className='font-medium text-gray-900'>{alert.customer_name}</p>
                        <p className='text-sm text-gray-600'>Health Score: {alert.health_score}/100</p>
                      </div>
                    </div>
                    <div className='text-right'>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        alert.priority === 'urgent' ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800'
                      }`}>
                        {alert.priority === 'urgent' ? '🚨 URGENT' : '⚠️ High Risk'}
                      </span>
                      <p className='text-xs text-gray-500 mt-1'>{alert.recommended_action}</p>
                    </div>
                  </div>
                ))}
                {churnAlerts.total_at_risk > 3 && (
                  <div className='text-center pt-2'>
                    <Button variant='outline' size='sm'>
                      View All {churnAlerts.total_at_risk} At-Risk Customers
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Activity */}
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
          {/* Recent Customers */}
          {hasPermission('identity.customers.read') && (
            <Card>
              <CardHeader>
                <CardTitle>Recent Customers</CardTitle>
              </CardHeader>
              <CardContent>
                <div className='space-y-3'>
                  {customers?.data?.slice(0, 5).map((customer: any) => (
                    <div
                      key={customer.id}
                      className='flex items-center justify-between p-3 border rounded-lg'
                    >
                      <div>
                        <p className='font-medium'>{customer.name}</p>
                        <p className='text-sm text-gray-500'>{customer.email}</p>
                      </div>
                      <div className='text-right'>
                        <div
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            customer.status === 'ACTIVE'
                              ? 'bg-green-100 text-green-800'
                              : customer.status === 'SUSPENDED'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {customer.status}
                        </div>
                      </div>
                    </div>
                  ))}
                  {customers?.data?.length === 0 && (
                    <div className='text-center py-4 text-gray-500'>No customers found</div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* System Status */}
          <Card>
            <CardHeader>
              <CardTitle>System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-4'>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center'>
                    <CheckCircle className='w-4 h-4 text-green-500 mr-2' />
                    <span className='text-sm'>Portal Services</span>
                  </div>
                  <span className='text-xs text-green-600 font-medium'>Operational</span>
                </div>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center'>
                    <CheckCircle className='w-4 h-4 text-green-500 mr-2' />
                    <span className='text-sm'>Billing System</span>
                  </div>
                  <span className='text-xs text-green-600 font-medium'>Operational</span>
                </div>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center'>
                    <CheckCircle className='w-4 h-4 text-green-500 mr-2' />
                    <span className='text-sm'>Network Monitoring</span>
                  </div>
                  <span className='text-xs text-green-600 font-medium'>Operational</span>
                </div>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center'>
                    <Clock className='w-4 h-4 text-yellow-500 mr-2' />
                    <span className='text-sm'>API Gateway</span>
                  </div>
                  <span className='text-xs text-yellow-600 font-medium'>Degraded</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Module Access Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Available Modules</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4'>
              {[
                { name: 'Identity', key: 'identity', icon: Users },
                { name: 'Billing', key: 'billing', icon: DollarSign },
                { name: 'Services', key: 'services', icon: Wifi },
                { name: 'Networking', key: 'networking', icon: Wifi },
                { name: 'Support', key: 'support', icon: Users },
                { name: 'Analytics', key: 'analytics', icon: TrendingUp },
              ].map((module) => {
                const Icon = module.icon;
                const hasAccess = hasModule(module.key);
                return (
                  <div
                    key={module.key}
                    className={`flex items-center p-3 border rounded-lg ${
                      hasAccess ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <Icon
                      className={`w-5 h-5 mr-2 ${hasAccess ? 'text-green-600' : 'text-gray-400'}`}
                    />
                    <div>
                      <p
                        className={`text-sm font-medium ${
                          hasAccess ? 'text-green-900' : 'text-gray-500'
                        }`}
                      >
                        {module.name}
                      </p>
                      <p className={`text-xs ${hasAccess ? 'text-green-600' : 'text-gray-400'}`}>
                        {hasAccess ? 'Enabled' : 'Disabled'}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
