/**
 * Refactored Billing Management Component
 * Clean, focused component using decomposed parts
 */

'use client';

import { useState } from 'react';
import { BillingMetrics } from './BillingMetrics';
import { BillingTabs, BillingTabContent, TabPanel, type BillingTabType } from './BillingTabs';
import { InvoicesTable } from './InvoicesTable';
import { useInvoices, usePayments, useReports } from '../../hooks/useBillingData';

interface BillingManagementProps {
  className?: string;
}

export function BillingManagement({ className = '' }: BillingManagementProps) {
  const [activeTab, setActiveTab] = useState<BillingTabType>('invoices');

  // Fetch data for tab counts
  const { data: invoicesData } = useInvoices({}, 1, 1); // Just for count
  const { data: paymentsData } = usePayments(1, 1); // Just for count
  const { data: reports } = useReports();

  const tabs = [
    { 
      id: 'invoices' as const, 
      label: 'Invoices', 
      count: invoicesData?.pagination.total
    },
    { 
      id: 'payments' as const, 
      label: 'Payments', 
      count: paymentsData?.pagination.total
    },
    { 
      id: 'reports' as const, 
      label: 'Reports', 
      count: reports?.length
    },
    { 
      id: 'analytics' as const, 
      label: 'Analytics', 
      count: null
    },
  ];

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Key Metrics */}
      <BillingMetrics />

      {/* Navigation Tabs */}
      <BillingTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        tabs={tabs}
      />

      {/* Tab Content */}
      <BillingTabContent activeTab={activeTab}>
        <TabPanel value="invoices" activeTab={activeTab}>
          <InvoicesTable />
        </TabPanel>

        <TabPanel value="payments" activeTab={activeTab}>
          <div className="bg-white rounded-lg border p-8 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Payments Management</h3>
            <p className="text-gray-600">Payments table component coming soon...</p>
          </div>
        </TabPanel>

        <TabPanel value="reports" activeTab={activeTab}>
          <div className="bg-white rounded-lg border p-8 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Reports</h3>
            <p className="text-gray-600">Reports management component coming soon...</p>
          </div>
        </TabPanel>

        <TabPanel value="analytics" activeTab={activeTab}>
          <div className="bg-white rounded-lg border p-8 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Analytics</h3>
            <p className="text-gray-600">Analytics dashboard component coming soon...</p>
          </div>
        </TabPanel>
      </BillingTabContent>
    </div>
  );
}