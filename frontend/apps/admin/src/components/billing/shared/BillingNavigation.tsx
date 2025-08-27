/**
 * Billing Navigation - Focused component for billing section navigation
 * Handles tab switching and displays counts for each section
 */

'use client';

type TabType = 'invoices' | 'payments' | 'reports' | 'analytics';

interface BillingNavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  counts?: {
    invoices?: number;
    payments?: number;
    reports?: number;
  };
}

export function BillingNavigation({ activeTab, onTabChange, counts = {} }: BillingNavigationProps) {
  const tabs = [
    { id: 'invoices', label: 'Invoices', count: counts.invoices },
    { id: 'payments', label: 'Payments', count: counts.payments },
    { id: 'reports', label: 'Reports', count: counts.reports },
    { id: 'analytics', label: 'Analytics', count: null },
  ] as const;

  return (
    <div className='border-b border-gray-200'>
      <nav className='flex space-x-8'>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id as TabType)}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
            {tab.count !== null && tab.count !== undefined && (
              <span className='ml-2 py-0.5 px-2 rounded-full bg-gray-100 text-xs'>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}