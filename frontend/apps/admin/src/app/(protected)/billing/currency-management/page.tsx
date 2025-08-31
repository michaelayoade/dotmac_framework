'use client';

import { useState } from 'react';
import { CurrencyManagementPanel } from '@dotmac/billing-system';

interface CurrencyManagementPageProps {
  searchParams: {
    customerId?: string;
  };
}

export default function CurrencyManagementPage({ searchParams }: CurrencyManagementPageProps) {
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>(
    searchParams.customerId || ''
  );

  const handleCurrencyUpdate = () => {
    // Refresh any parent components or show success message
    console.log('Currency configuration updated');
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Currency Management</h1>
        <p className="text-gray-600 mt-2">
          Configure multi-currency support for customers and manage exchange rates.
        </p>
      </div>

      {/* Customer Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Customer
        </label>
        <div className="flex gap-4 items-center">
          <input
            type="text"
            value={selectedCustomerId}
            onChange={(e) => setSelectedCustomerId(e.target.value)}
            placeholder="Enter customer ID"
            className="flex-1 max-w-md px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => {
              // In real implementation, this would open a customer picker modal
              console.log('Open customer picker');
            }}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Browse Customers
          </button>
        </div>
      </div>

      {/* Currency Management Panel */}
      {selectedCustomerId ? (
        <CurrencyManagementPanel
          customerId={selectedCustomerId}
          onCurrencyUpdate={handleCurrencyUpdate}
        />
      ) : (
        <div className="text-center py-12">
          <div className="text-gray-500 mb-4">No customer selected</div>
          <p className="text-sm text-gray-400">
            Please select a customer to manage their currency settings
          </p>
        </div>
      )}

      {/* Help Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-blue-900 mb-3">
          Multi-Currency Setup Guide
        </h2>
        <div className="space-y-2 text-sm text-blue-800">
          <p>
            <strong>1. Base Currency:</strong> Set the customer's primary accounting currency (e.g., NGN for Nigerian ISPs)
          </p>
          <p>
            <strong>2. Payment Currencies:</strong> Add currencies customers can pay in (e.g., USD, EUR, GBP)
          </p>
          <p>
            <strong>3. Exchange Rates:</strong> Set manual exchange rates during payment processing
          </p>
          <p>
            <strong>4. Accounting:</strong> All payments are converted to base currency for accounting
          </p>
        </div>
      </div>
    </div>
  );
}