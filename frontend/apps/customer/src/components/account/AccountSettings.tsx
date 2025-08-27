/**
 * Account Settings Component
 * Manages basic account configuration and preferences
 */

'use client';

import { useState } from 'react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Input } from '../ui/Input';

interface AccountInfo {
  accountNumber: string;
  serviceAddress: string;
  billingAddress: string;
  planType: string;
  contractEndDate: string;
}

export function AccountSettings() {
  const [accountInfo] = useState<AccountInfo>({
    accountNumber: 'ACC-2024-001234',
    serviceAddress: '123 Main St, Anytown, ST 12345',
    billingAddress: '123 Main St, Anytown, ST 12345',
    planType: 'Residential Fiber 100/100',
    contractEndDate: '2025-12-31',
  });

  const [showAccountInfo, setShowAccountInfo] = useState(false);

  return (
    <Card>
      <div className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Information</h2>

        <div className="space-y-4">
          {/* Account Number */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Account Number</label>
            <div className="flex items-center space-x-3">
              <Input
                type={showAccountInfo ? 'text' : 'password'}
                value={accountInfo.accountNumber}
                readOnly
                className="flex-1"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAccountInfo(!showAccountInfo)}
              >
                {showAccountInfo ? 'Hide' : 'Show'}
              </Button>
            </div>
          </div>

          {/* Service Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Service Address</label>
            <Input value={accountInfo.serviceAddress} readOnly className="bg-gray-50" />
          </div>

          {/* Billing Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Billing Address</label>
            <Input value={accountInfo.billingAddress} readOnly className="bg-gray-50" />
          </div>

          {/* Plan Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Plan</label>
              <Input value={accountInfo.planType} readOnly className="bg-gray-50" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contract End Date
              </label>
              <Input value={accountInfo.contractEndDate} readOnly className="bg-gray-50" />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3 pt-4 border-t">
            <Button variant="outline" size="sm">
              Request Address Change
            </Button>
            <Button variant="outline" size="sm">
              View Plan Options
            </Button>
            <Button variant="outline" size="sm">
              Contract Details
            </Button>
          </div>
        </div>

        {/* Account Status */}
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Account Active</h3>
              <div className="mt-1 text-sm text-green-700">
                Your account is in good standing. Next billing date:{' '}
                {new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
