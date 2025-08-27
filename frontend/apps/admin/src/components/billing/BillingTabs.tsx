/**
 * Billing Tabs Component
 * Navigation tabs for different billing sections
 */

'use client';

import { type ReactNode } from 'react';

export type BillingTabType = 'invoices' | 'payments' | 'reports' | 'analytics';

interface Tab {
  id: BillingTabType;
  label: string;
  count?: number;
}

interface BillingTabsProps {
  activeTab: BillingTabType;
  onTabChange: (tab: BillingTabType) => void;
  tabs: Tab[];
  className?: string;
}

export function BillingTabs({ 
  activeTab, 
  onTabChange, 
  tabs, 
  className = '' 
}: BillingTabsProps) {
  return (
    <div className={`border-b border-gray-200 ${className}`}>
      <nav className="flex space-x-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
            {tab.count !== null && tab.count !== undefined && (
              <span className={`ml-2 py-0.5 px-2 rounded-full text-xs ${
                activeTab === tab.id
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-600'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}

interface BillingTabContentProps {
  activeTab: BillingTabType;
  children: ReactNode;
  className?: string;
}

export function BillingTabContent({ 
  activeTab, 
  children, 
  className = '' 
}: BillingTabContentProps) {
  return (
    <div className={`mt-6 ${className}`}>
      {children}
    </div>
  );
}

// Individual tab panel component
interface TabPanelProps {
  value: BillingTabType;
  activeTab: BillingTabType;
  children: ReactNode;
  className?: string;
}

export function TabPanel({ 
  value, 
  activeTab, 
  children, 
  className = '' 
}: TabPanelProps) {
  if (value !== activeTab) {
    return null;
  }

  return (
    <div className={`fade-in ${className}`} role="tabpanel">
      {children}
    </div>
  );
}