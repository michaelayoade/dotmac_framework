'use client';

import { useCustomerDashboard, usePortalAuth } from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/customer';
import { useState, useEffect } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  CreditCard,
  Download,
  Globe,
  MessageSquare,
  TrendingUp,
  Upload,
  Wifi,
  Bell,
  Lightbulb,
} from 'lucide-react';

import { NetworkUsageChart, BandwidthChart } from '@dotmac/primitives/charts/InteractiveChart';
import { StatusBadge, UptimeIndicator, NetworkPerformanceIndicator, ServiceTierIndicator } from '@dotmac/primitives/indicators/StatusIndicators';
import { AnimatedCounter, FadeInWhenVisible, StaggeredFadeIn, StaggerChild, AnimatedCard, SlideIn, AnimatedProgressBar, PulseIndicator } from '@dotmac/primitives/animations/Animations';
import { CustomerLayout } from '../layout/CustomerLayout';

// Mock data - in real app this would come from API
const _mockCustomerData = {
  account: {
    id: 'CUST-001',
    name: 'John Doe',
    accountNumber: 'ACC-123456',
    serviceAddress: '123 Main St, City, State 12345',
    phone: '+1 (555) 123-4567',
    email: 'john.doe@email.com',
  },
  services: [
    {
      id: 'SVC-001',
      name: 'Fiber Internet 100/100',
      type: 'internet',
      status: 'active',
      speed: { download: 100, upload: 100 },
      usage: { current: 450, limit: 1000, unit: 'GB' },
      monthlyPrice: 79.99,
      installDate: '2024-01-15',
    },
    {
      id: 'SVC-002',
      name: 'Basic Phone Service',
      type: 'phone',
      status: 'active',
      monthlyPrice: 29.99,
      features: ['Unlimited Local', 'Voicemail', 'Caller ID'],
    },
  ],
  billing: {
    currentBalance: 0,
    nextBillDate: '2024-02-15',
    nextBillAmount: 109.98,
    lastPayment: {
      amount: 109.98,
      date: '2024-01-15',
      method: 'Auto Pay',
    },
    paymentMethod: 'Credit Card ending in 1234',
  },
  networkStatus: {
    connectionStatus: 'connected',
    currentSpeed: { download: 98.5, upload: 99.2 },
    uptime: 99.8,
    lastOutage: null,
    signalStrength: 'excellent',
  },
  supportTickets: [
    {
      id: 'TICK-001',
      subject: 'Slow internet speeds',
      status: 'resolved',
      priority: 'medium',
      createdDate: '2024-01-10',
      resolvedDate: '2024-01-12',
    },
  ],
};

interface CustomerDashboardProps {
  data?: any; // Override data from props if provided
}

export function CustomerDashboard({ data = undefined }: CustomerDashboardProps = {}) {
  const { _user, _currentPortal } = usePortalAuth();
  const [serviceNotifications, setServiceNotifications] = useState<any>(null);
  const [usageInsights, setUsageInsights] = useState<any>(null);

  const { data: hookData, isLoading, isUsingMockData } = useCustomerDashboard();
  
  // Use prop data if provided, otherwise fall back to hook data
  const customerData = data || hookData;

  // Load intelligence data
  useEffect(() => {
    if (customerData?.account?.id) {
      fetchServiceIntelligence();
    }
  }, [customerData]);

  const fetchServiceIntelligence = async () => {
    try {
      // Get service notifications
      const notificationsResponse = await fetch(`/api/isp/services/customers/${customerData.account.id}/intelligence/service-status`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('customer-token')}`,
        },
      });

      if (notificationsResponse.ok) {
        const notifications = await notificationsResponse.json();
        setServiceNotifications(notifications);
      } else {
        // Demo data
        setServiceNotifications({
          notifications: [
            {
              type: 'service_health',
              priority: 'low',
              title: 'All Services Operating Normally',
              message: 'Your internet and phone services are running smoothly.',
              action_required: false
            }
          ],
          service_summary: { total_services: 2, active_services: 2, issues: 0 }
        });
      }

      // Get usage insights
      const insightsResponse = await fetch(`/api/isp/services/customers/${customerData.account.id}/intelligence/usage-insights`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('customer-token')}`,
        },
      });

      if (insightsResponse.ok) {
        const insights = await insightsResponse.json();
        setUsageInsights(insights);
      } else {
        // Demo data
        setUsageInsights({
          usage_insights: [
            {
              type: 'usage_optimization',
              title: 'Data Usage Insight',
              message: 'You consistently use less than 50% of your data. A smaller plan could save money.',
              recommendation: 'Downgrade to Basic Plan',
              potential_savings: 'Save $15/month'
            }
          ]
        });
      }
    } catch (error) {
      console.error('Failed to fetch service intelligence:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'connected':
      case 'resolved':
        return 'text-green-600';
      case 'suspended':
      case 'disconnected':
        return 'text-red-600';
      case 'pending':
      case 'in_progress':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
      case 'connected':
      case 'resolved':
        return <CheckCircle className='h-5 w-5 text-green-600' />;
      case 'suspended':
      case 'disconnected':
        return <AlertCircle className='h-5 w-5 text-red-600' />;
      case 'pending':
      case 'in_progress':
        return <Clock className='h-5 w-5 text-yellow-600' />;
      default:
        return <AlertCircle className='h-5 w-5 text-gray-600' />;
    }
  };

  if ((!data && isLoading) || !customerData) {
    return (
      <div className='flex h-64 items-center justify-center'>
        <div className='h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2' />
      </div>
    );
  }

  return (
    <div className='space-y-6'>
        {/* Development indicator */}
        {isUsingMockData && process.env.NODE_ENV === 'development' ? (
          <div className='rounded-lg border border-yellow-200 bg-yellow-50 p-3'>
            <div className='flex items-center'>
              <AlertCircle className='mr-2 h-4 w-4 text-yellow-600' />
              <span className='text-sm text-yellow-800'>Using mock data - API not available</span>
            </div>
          </div>
        ) : null}
        {/* Welcome Header */}
        <SlideIn direction="down">
          <AnimatedCard className='rounded-lg bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 p-6 text-white shadow-lg hover:shadow-xl'>
            <div className='flex items-center justify-between'>
              <div>
                <h1 className='font-bold text-2xl'>Welcome back, {customerData.account.name}!</h1>
                <p className='mt-1 text-blue-100'>Account: {customerData.account.accountNumber}</p>
                <ServiceTierIndicator tier="premium" className="mt-2" />
              </div>
              <div className='text-right'>
                <div className='text-blue-100 text-sm'>Current Balance</div>
                <AnimatedCounter 
                  value={customerData.billing.currentBalance} 
                  prefix="$" 
                  className='font-bold text-2xl'
                />
              </div>
            </div>
          </AnimatedCard>
        </SlideIn>

        {/* Proactive Service Notifications - Intelligence Enhancement */}
        {serviceNotifications && serviceNotifications.notifications.length > 0 && (
          <FadeInWhenVisible delay={0.1}>
            <AnimatedCard className='p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg shadow-sm hover:shadow-md'>
              <div className='flex items-center mb-3'>
                <Bell className='h-5 w-5 text-blue-600 mr-2' />
                <h3 className='font-semibold text-gray-900'>Service Updates</h3>
              </div>
              <div className='space-y-2'>
                {serviceNotifications.notifications.slice(0, 2).map((notification: any, index: number) => (
                  <div key={index} className={`p-3 rounded-lg ${
                    notification.priority === 'high' ? 'bg-red-50 border border-red-200' :
                    notification.priority === 'medium' ? 'bg-yellow-50 border border-yellow-200' :
                    'bg-green-50 border border-green-200'
                  }`}>
                    <div className='flex items-start'>
                      <div className={`w-2 h-2 rounded-full mt-2 mr-3 ${
                        notification.priority === 'high' ? 'bg-red-500' :
                        notification.priority === 'medium' ? 'bg-yellow-500' :
                        'bg-green-500'
                      }`}></div>
                      <div className='flex-1'>
                        <p className='font-medium text-gray-900 text-sm'>{notification.title}</p>
                        <p className='text-gray-600 text-sm'>{notification.message}</p>
                        {notification.estimated_resolution && (
                          <p className='text-xs text-gray-500 mt-1'>Estimated resolution: {notification.estimated_resolution}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </AnimatedCard>
          </FadeInWhenVisible>
        )}

        {/* Usage Insights - Intelligence Enhancement */}
        {usageInsights && usageInsights.usage_insights.length > 0 && (
          <FadeInWhenVisible delay={0.15}>
            <AnimatedCard className='p-4 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg shadow-sm hover:shadow-md'>
              <div className='flex items-center justify-between mb-3'>
                <div className='flex items-center'>
                  <Lightbulb className='h-5 w-5 text-green-600 mr-2' />
                  <h3 className='font-semibold text-gray-900'>Smart Insights</h3>
                </div>
                {usageInsights.summary?.potential_monthly_impact && (
                  <span className='text-sm font-medium text-green-600 bg-green-100 px-2 py-1 rounded-full'>
                    {usageInsights.summary.potential_monthly_impact}
                  </span>
                )}
              </div>
              <div className='space-y-2'>
                {usageInsights.usage_insights.slice(0, 1).map((insight: any, index: number) => (
                  <div key={index} className='p-3 bg-white/60 rounded-lg border border-green-100'>
                    <div className='flex items-start justify-between'>
                      <div className='flex-1'>
                        <p className='font-medium text-gray-900 text-sm'>{insight.title}</p>
                        <p className='text-gray-600 text-sm'>{insight.message}</p>
                        {insight.recommendation && (
                          <p className='text-green-700 text-sm font-medium mt-1'>💡 {insight.recommendation}</p>
                        )}
                      </div>
                      {insight.action_url && (
                        <button className='ml-4 px-3 py-1 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700 transition-colors'>
                          Learn More
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </AnimatedCard>
          </FadeInWhenVisible>
        )}

        {/* Service Status Overview */}
        <StaggeredFadeIn>
          <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
            <StaggerChild>
              <AnimatedCard className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='font-medium text-gray-600 text-sm'>Connection Status</p>
                    <div className='mt-2 flex items-center'>
                      <StatusBadge
                        variant={customerData.networkStatus.connectionStatus === 'connected' ? 'online' : 'offline'}
                        size="sm"
                        showDot={true}
                        pulse={true}
                      >
                        {customerData.networkStatus.connectionStatus}
                      </StatusBadge>
                    </div>
                  </div>
                  <PulseIndicator>
                    <Wifi className='h-8 w-8 text-blue-600' />
                  </PulseIndicator>
                </div>
              </AnimatedCard>
            </StaggerChild>

            <StaggerChild>
              <AnimatedCard className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='font-medium text-gray-600 text-sm'>Current Speed</p>
                    <div className='mt-1 flex items-baseline'>
                      <AnimatedCounter 
                        value={customerData.networkStatus.currentSpeed.download} 
                        className='font-bold text-2xl text-gray-900'
                      />
                      <span className='ml-1 text-gray-500 text-sm'>Mbps</span>
                    </div>
                  </div>
                  <TrendingUp className='h-8 w-8 text-green-600' />
                </div>
              </AnimatedCard>
            </StaggerChild>

            <StaggerChild>
              <AnimatedCard className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='font-medium text-gray-600 text-sm'>Data Usage</p>
                    <div className='mt-1 flex items-baseline'>
                      <AnimatedCounter 
                        value={customerData.services[0].usage.current} 
                        className='font-bold text-2xl text-gray-900'
                      />
                      <span className='text-gray-500 text-sm'>
                        /{customerData.services[0].usage.limit} GB
                      </span>
                    </div>
                    <div className='mt-3'>
                      <AnimatedProgressBar 
                        progress={(customerData.services[0].usage.current / customerData.services[0].usage.limit) * 100}
                        color={customerData.services[0].usage.current / customerData.services[0].usage.limit > 0.8 ? 'bg-red-500' : 'bg-purple-500'}
                        height="h-2"
                      />
                    </div>
                  </div>
                  <Activity className='h-8 w-8 text-purple-600' />
                </div>
              </AnimatedCard>
            </StaggerChild>

            <StaggerChild>
              <AnimatedCard className='p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='font-medium text-gray-600 text-sm'>Next Bill</p>
                    <div className='mt-1'>
                      <AnimatedCounter 
                        value={customerData.billing.nextBillAmount} 
                        prefix="$" 
                        className='font-bold text-2xl text-gray-900'
                      />
                    </div>
                    <p className='text-gray-500 text-sm'>
                      Due {new Date(customerData.billing.nextBillDate).toLocaleDateString()}
                    </p>
                  </div>
                  <CreditCard className='h-8 w-8 text-orange-600' />
                </div>
              </AnimatedCard>
            </StaggerChild>
          </div>
        </StaggeredFadeIn>

        {/* Services & Network Performance */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          {/* Active Services */}
          <FadeInWhenVisible delay={0.2}>
            <AnimatedCard className='p-6 bg-gradient-to-br from-green-50 to-emerald-100 border border-green-200 rounded-lg shadow-sm hover:shadow-md'>
              <div className='mb-6 flex items-center justify-between'>
                <h3 className='font-semibold text-gray-900 text-lg'>Your Services</h3>
                <Globe className='h-5 w-5 text-green-600' />
              </div>
              <div className='space-y-4'>
                {customerData.services.map((service, index) => (
                  <FadeInWhenVisible key={service.id} delay={index * 0.1}>
                    <AnimatedCard className='rounded-lg border border-gray-200 p-4 bg-white/80 backdrop-blur-sm hover:bg-white transition-all duration-200'>
                      <div className='mb-3 flex items-center justify-between'>
                        <h4 className='font-medium text-gray-900 flex items-center'>
                          {service.type === 'internet' ? '🌐' : '📞'} {service.name}
                        </h4>
                        <StatusBadge
                          variant={service.status === 'active' ? 'online' : 'offline'}
                          size="sm"
                          showDot={true}
                          pulse={service.status === 'active'}
                        >
                          {service.status}
                        </StatusBadge>
                      </div>
                      
                      <div className='grid grid-cols-2 gap-4 text-gray-600 text-sm mb-3'>
                        <div className='flex items-center justify-between'>
                          <span className='font-medium'>Monthly:</span>
                          <AnimatedCounter value={service.monthlyPrice} prefix="$" className="font-semibold text-green-600" />
                        </div>
                        {service.speed ? (
                          <div className='flex items-center justify-between'>
                            <span className='font-medium'>Speed:</span>
                            <span className='font-semibold'>
                              <AnimatedCounter value={service.speed.download} />/<AnimatedCounter value={service.speed.upload} /> Mbps
                            </span>
                          </div>
                        ) : null}
                      </div>
                      
                      {service.usage ? (
                        <div>
                          <div className='mb-2 flex justify-between text-gray-600 text-sm'>
                            <span className='font-medium'>Data Usage</span>
                            <span className='font-semibold'>
                              <AnimatedCounter value={service.usage.current} /> / 
                              <AnimatedCounter value={service.usage.limit} /> {service.usage.unit}
                            </span>
                          </div>
                          <AnimatedProgressBar 
                            progress={(service.usage.current / service.usage.limit) * 100}
                            color={service.usage.current / service.usage.limit > 0.8 ? 'bg-red-500' : service.usage.current / service.usage.limit > 0.6 ? 'bg-orange-500' : 'bg-blue-500'}
                            backgroundColor="bg-gray-200"
                            height="h-3"
                            showLabel={false}
                          />
                        </div>
                      ) : null}
                      
                      {service.features && (
                        <div className='mt-3 flex flex-wrap gap-1'>
                          {service.features.map((feature, idx) => (
                            <StatusBadge key={idx} variant="active" size="sm">
                              {feature}
                            </StatusBadge>
                          ))}
                        </div>
                      )}
                    </AnimatedCard>
                  </FadeInWhenVisible>
                ))}
              </div>
            </AnimatedCard>
          </FadeInWhenVisible>

          {/* Network Performance */}
          <FadeInWhenVisible delay={0.4}>
            <AnimatedCard className='p-6 bg-gradient-to-br from-blue-50 to-indigo-100 border border-blue-200 rounded-lg shadow-sm hover:shadow-md'>
              <div className='mb-6 flex items-center justify-between'>
                <h3 className='font-semibold text-gray-900 text-lg'>Network Performance</h3>
                <Activity className='h-5 w-5 text-blue-600' />
              </div>
              
              {/* Enhanced Network Performance Display */}
              <div className='mb-6'>
                <NetworkPerformanceIndicator
                  latency={12}
                  packetLoss={0.1}
                  bandwidth={customerData.networkStatus.currentSpeed.download}
                />
              </div>

              {/* Uptime Indicator */}
              <div className='mb-6'>
                <UptimeIndicator uptime={customerData.networkStatus.uptime} />
              </div>

              {/* Usage Chart */}
              <div className='mb-4'>
                <h4 className='text-sm font-medium text-gray-600 mb-3'>24-Hour Usage Pattern</h4>
                <NetworkUsageChart
                  data={[
                    { hour: '00:00', download: 2.1, upload: 0.8, peak: 5 },
                    { hour: '06:00', download: 3.2, upload: 1.2, peak: 5 },
                    { hour: '12:00', download: 8.5, upload: 3.1, peak: 5 },
                    { hour: '18:00', download: 12.3, upload: 4.8, peak: 5 },
                    { hour: '24:00', download: 6.7, upload: 2.3, peak: 5 },
                  ]}
                  height={200}
                />
              </div>

              <AnimatedCard 
                onClick={() => alert('Speed test launched!')}
                className='mt-4 w-full rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-white transition-all duration-200 hover:from-blue-700 hover:to-indigo-700 cursor-pointer text-center font-medium shadow-md hover:shadow-lg'
              >
                🚀 Run Speed Test
              </AnimatedCard>
            </AnimatedCard>
          </FadeInWhenVisible>
        </div>

        {/* Recent Activity & Quick Actions */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
          {/* Recent Billing */}
          <FadeInWhenVisible delay={0.3}>
            <AnimatedCard className='p-6 bg-gradient-to-br from-orange-50 to-amber-100 border border-orange-200 rounded-lg shadow-sm hover:shadow-md'>
              <div className='mb-6 flex items-center justify-between'>
                <h3 className='font-semibold text-gray-900 text-lg'>💳 Billing Summary</h3>
                <CreditCard className='h-5 w-5 text-orange-600' />
              </div>
              <div className='space-y-4'>
                <div className='flex justify-between items-center p-3 bg-white/60 rounded-lg'>
                  <span className='text-gray-600 font-medium'>Last Payment</span>
                  <AnimatedCounter value={customerData.billing.lastPayment.amount} prefix="$" className='font-semibold text-green-600' />
                </div>
                <div className='flex justify-between items-center p-3 bg-white/60 rounded-lg'>
                  <span className='text-gray-600 font-medium'>Payment Date</span>
                  <span className='font-medium text-gray-900'>
                    {new Date(customerData.billing.lastPayment.date).toLocaleDateString()}
                  </span>
                </div>
                <div className='flex justify-between items-center p-3 bg-white/60 rounded-lg'>
                  <span className='text-gray-600 font-medium'>Payment Method</span>
                  <StatusBadge variant="processing" size="sm">
                    {customerData.billing.paymentMethod}
                  </StatusBadge>
                </div>
                <div className='border-t border-orange-200 pt-4 bg-white/80 rounded-lg p-4'>
                  <div className='flex justify-between items-center text-lg'>
                    <span className='font-semibold text-gray-800'>Next Bill Amount</span>
                    <AnimatedCounter 
                      value={customerData.billing.nextBillAmount} 
                      prefix="$" 
                      className='font-bold text-2xl text-orange-600'
                    />
                  </div>
                  <p className='mt-2 text-gray-600 text-sm flex items-center'>
                    🗓️ Due {new Date(customerData.billing.nextBillDate).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </AnimatedCard>
          </FadeInWhenVisible>

          {/* Support & Quick Actions */}
          <FadeInWhenVisible delay={0.4}>
            <AnimatedCard className='p-6 bg-gradient-to-br from-purple-50 to-indigo-100 border border-purple-200 rounded-lg shadow-sm hover:shadow-md'>
              <div className='mb-6 flex items-center justify-between'>
                <h3 className='font-semibold text-gray-900 text-lg'>🎧 Support & Actions</h3>
                <MessageSquare className='h-5 w-5 text-purple-600' />
              </div>
              <div className='space-y-4'>
                {customerData.supportTickets.length > 0 ? (
                  <FadeInWhenVisible>
                    <div className='rounded-lg bg-white/80 p-4 border border-purple-100'>
                      <div className='flex items-center justify-between mb-2'>
                        <span className='font-medium text-gray-800'>🎫 Recent Ticket</span>
                        <StatusBadge
                          variant={customerData.supportTickets[0].status === 'resolved' ? 'paid' : 'pending'}
                          size="sm"
                          showDot={true}
                        >
                          {customerData.supportTickets[0].status}
                        </StatusBadge>
                      </div>
                      <p className='text-gray-600 text-sm'>
                        {customerData.supportTickets[0].subject}
                      </p>
                    </div>
                  </FadeInWhenVisible>
                ) : (
                  <div className='text-center py-4 text-gray-500 text-sm bg-white/60 rounded-lg'>
                    ✅ No recent support tickets - Everything looks good!
                  </div>
                )}

                <StaggeredFadeIn>
                  <div className='grid grid-cols-2 gap-3 pt-3'>
                    <StaggerChild>
                      <AnimatedCard
                        onClick={() => alert('Pay Bill clicked!')}
                        className='rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 text-sm text-white transition-all duration-200 hover:from-blue-700 hover:to-blue-800 cursor-pointer text-center font-medium shadow-md hover:shadow-lg'
                      >
                        💳 Pay Bill
                      </AnimatedCard>
                    </StaggerChild>
                    <StaggerChild>
                      <AnimatedCard
                        onClick={() => alert('Get Support clicked!')}
                        className='rounded-lg border-2 border-purple-300 bg-white/80 px-4 py-3 text-purple-700 text-sm transition-all duration-200 hover:bg-purple-50 cursor-pointer text-center font-medium'
                      >
                        🆘 Get Support
                      </AnimatedCard>
                    </StaggerChild>
                    <StaggerChild>
                      <AnimatedCard
                        onClick={() => alert('Upgrade Service clicked!')}
                        className='rounded-lg border-2 border-green-300 bg-white/80 px-4 py-3 text-green-700 text-sm transition-all duration-200 hover:bg-green-50 cursor-pointer text-center font-medium'
                      >
                        🚀 Upgrade
                      </AnimatedCard>
                    </StaggerChild>
                    <StaggerChild>
                      <AnimatedCard
                        onClick={() => alert('View Bills clicked!')}
                        className='rounded-lg border-2 border-gray-300 bg-white/80 px-4 py-3 text-gray-700 text-sm transition-all duration-200 hover:bg-gray-50 cursor-pointer text-center font-medium'
                      >
                        📄 View Bills
                      </AnimatedCard>
                    </StaggerChild>
                  </div>
                </StaggeredFadeIn>
              </div>
            </AnimatedCard>
          </FadeInWhenVisible>
        </div>
      </div>
    </div>
  );
}
