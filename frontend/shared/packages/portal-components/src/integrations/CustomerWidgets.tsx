'use client';

import { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useJourneyOrchestration } from '@dotmac/journey-orchestration';

/**
 * Customer-specific Dashboard Widgets
 * Focused on service status, billing, and support
 */

export function ServiceStatusWidget() {
  const { data: serviceStatus } = useQuery({
    queryKey: ['customer-service-status'],
    queryFn: async () => ({
      internetStatus: 'active',
      speed: '100 Mbps',
      uptime: '99.9%',
      lastOutage: null,
      planType: 'Premium',
    }),
    refetchInterval: 30000,
  });

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-3'>Service Status</h3>
      <div className='space-y-3'>
        <div className='flex justify-between items-center'>
          <span className='text-sm text-gray-600'>Internet</span>
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              serviceStatus?.internetStatus === 'active'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {serviceStatus?.internetStatus || 'Unknown'}
          </span>
        </div>
        <div className='flex justify-between items-center'>
          <span className='text-sm text-gray-600'>Speed</span>
          <span className='text-sm font-medium text-gray-900'>{serviceStatus?.speed || '—'}</span>
        </div>
        <div className='flex justify-between items-center'>
          <span className='text-sm text-gray-600'>Uptime</span>
          <span className='text-sm font-medium text-gray-900'>{serviceStatus?.uptime || '—'}</span>
        </div>
      </div>
    </div>
  );
}

export function BillingOverviewWidget() {
  const { data: billingData } = useQuery({
    queryKey: ['customer-billing'],
    queryFn: async () => ({
      currentBill: 89.99,
      dueDate: '2024-09-15',
      status: 'current',
      paymentMethod: '**** 1234',
      nextBillDate: '2024-10-15',
    }),
    refetchInterval: 300000, // 5 minutes
  });

  const getDaysUntilDue = (dueDate: string) => {
    const today = new Date();
    const due = new Date(dueDate);
    const diffTime = due.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const daysUntilDue = billingData?.dueDate ? getDaysUntilDue(billingData.dueDate) : null;

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-3'>Current Bill</h3>
      <div className='space-y-3'>
        <div className='text-center'>
          <div className='text-2xl font-bold text-gray-900'>
            ${billingData?.currentBill?.toFixed(2) || '—'}
          </div>
          <div className='text-sm text-gray-600'>
            {daysUntilDue !== null && (
              <span className={daysUntilDue <= 3 ? 'text-red-600' : 'text-gray-600'}>
                Due in {daysUntilDue} days
              </span>
            )}
          </div>
        </div>
        <div className='flex justify-between items-center pt-2 border-t'>
          <span className='text-sm text-gray-600'>Status</span>
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              billingData?.status === 'current'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}
          >
            {billingData?.status || 'Unknown'}
          </span>
        </div>
      </div>
    </div>
  );
}

export function SupportTicketsWidget() {
  const { data: ticketsData } = useQuery({
    queryKey: ['customer-support-tickets'],
    queryFn: async () => ({
      openTickets: 1,
      recentTicket: {
        id: 'TK-12345',
        subject: 'Internet speed issue',
        status: 'in-progress',
        created: '2024-08-28',
        priority: 'medium',
      },
    }),
    refetchInterval: 120000, // 2 minutes
  });

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-3'>Support</h3>
      <div className='space-y-3'>
        <div className='flex justify-between items-center'>
          <span className='text-sm text-gray-600'>Open Tickets</span>
          <span className='text-lg font-semibold text-gray-900'>
            {ticketsData?.openTickets || 0}
          </span>
        </div>
        {ticketsData?.recentTicket && (
          <div className='pt-2 border-t'>
            <div className='text-sm font-medium text-gray-900'>#{ticketsData.recentTicket.id}</div>
            <div className='text-xs text-gray-600 truncate'>{ticketsData.recentTicket.subject}</div>
            <div className='flex justify-between items-center mt-1'>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${
                  ticketsData.recentTicket.status === 'in-progress'
                    ? 'bg-blue-100 text-blue-800'
                    : ticketsData.recentTicket.status === 'resolved'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                }`}
              >
                {ticketsData.recentTicket.status}
              </span>
              <span className='text-xs text-gray-500'>{ticketsData.recentTicket.created}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function UsageOverviewWidget() {
  const { data: usageData } = useQuery({
    queryKey: ['customer-usage'],
    queryFn: async () => ({
      dataUsed: 450, // GB
      dataLimit: 1000, // GB
      period: 'August 2024',
      daysRemaining: 5,
      averageDailyUsage: 15.2, // GB per day
    }),
    refetchInterval: 300000, // 5 minutes
  });

  const usagePercentage = usageData ? (usageData.dataUsed / usageData.dataLimit) * 100 : 0;

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-3'>Data Usage</h3>
      <div className='space-y-3'>
        <div>
          <div className='flex justify-between text-sm mb-1'>
            <span className='text-gray-600'>This Month</span>
            <span className='font-medium'>
              {usageData?.dataUsed || 0} / {usageData?.dataLimit || 0} GB
            </span>
          </div>
          <div className='w-full bg-gray-200 rounded-full h-2'>
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                usagePercentage > 90
                  ? 'bg-red-500'
                  : usagePercentage > 75
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(usagePercentage, 100)}%` }}
            />
          </div>
        </div>
        <div className='grid grid-cols-2 gap-4 pt-2 border-t text-sm'>
          <div>
            <div className='text-gray-600'>Days Left</div>
            <div className='font-medium'>{usageData?.daysRemaining || 0}</div>
          </div>
          <div>
            <div className='text-gray-600'>Daily Avg</div>
            <div className='font-medium'>{usageData?.averageDailyUsage?.toFixed(1) || 0} GB</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CustomerJourneyWidget() {
  const { getCustomerJourney } = useJourneyOrchestration();
  const { data: journeyData } = useQuery({
    queryKey: ['customer-journey'],
    queryFn: async () => {
      try {
        // Get current customer's journey status
        const journey = await getCustomerJourney();
        return {
          stage: journey?.currentStep?.name || 'Active Customer',
          completedSteps: journey?.completedSteps?.length || 0,
          totalSteps: journey?.template?.steps?.length || 0,
          satisfactionScore: 4.5,
          accountAge: '2 years',
        };
      } catch (error) {
        return {
          stage: 'Active Customer',
          satisfactionScore: 4.5,
          accountAge: '2 years',
        };
      }
    },
    refetchInterval: 300000,
  });

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-3'>Account Status</h3>
      <div className='space-y-3'>
        <div className='text-center'>
          <div className='text-sm font-medium text-gray-900'>{journeyData?.stage}</div>
          <div className='text-xs text-gray-600 mt-1'>Customer for {journeyData?.accountAge}</div>
        </div>

        <div className='flex justify-between items-center pt-2 border-t'>
          <span className='text-sm text-gray-600'>Satisfaction</span>
          <div className='flex items-center'>
            <span className='text-sm font-medium text-gray-900'>
              {journeyData?.satisfactionScore || 0}/5
            </span>
            <div className='ml-1'>
              {'★'.repeat(Math.floor(journeyData?.satisfactionScore || 0))}
              {'☆'.repeat(5 - Math.floor(journeyData?.satisfactionScore || 0))}
            </div>
          </div>
        </div>

        {journeyData?.completedSteps && journeyData?.totalSteps && (
          <div className='flex justify-between items-center'>
            <span className='text-sm text-gray-600'>Onboarding</span>
            <span className='text-sm font-medium text-gray-900'>
              {journeyData.completedSteps}/{journeyData.totalSteps} complete
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Combined Customer Dashboard Widgets Grid
 */
export function CustomerDashboardWidgets({ layout = 'grid' }: { layout?: 'grid' | 'row' }) {
  const gridClass =
    layout === 'grid'
      ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'
      : 'flex flex-col md:flex-row gap-4';

  return (
    <div className={gridClass}>
      <ServiceStatusWidget />
      <BillingOverviewWidget />
      <UsageOverviewWidget />
      <SupportTicketsWidget />
    </div>
  );
}

/**
 * Expanded Customer Dashboard with Journey Tracking
 */
export function CustomerDashboardExpanded() {
  return (
    <div className='space-y-6'>
      {/* Main service widgets */}
      <CustomerDashboardWidgets layout='grid' />

      {/* Secondary widgets */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <CustomerJourneyWidget />
        <div className='bg-white p-4 rounded-lg shadow'>
          <h3 className='text-lg font-semibold mb-3'>Quick Actions</h3>
          <div className='space-y-2'>
            <button className='w-full text-left px-3 py-2 rounded-md hover:bg-gray-50 text-sm'>
              Pay Bill
            </button>
            <button className='w-full text-left px-3 py-2 rounded-md hover:bg-gray-50 text-sm'>
              Submit Support Ticket
            </button>
            <button className='w-full text-left px-3 py-2 rounded-md hover:bg-gray-50 text-sm'>
              Speed Test
            </button>
            <button className='w-full text-left px-3 py-2 rounded-md hover:bg-gray-50 text-sm'>
              Update Payment Method
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
