/**
 * Updated Billing Overview Component
 * NOW USES: Centralized ISP Business Operations (DRY-compliant)
 * BEFORE: Multiple individual hooks and duplicate logic
 */

'use client';

import { useCustomerBusiness, type DateRange } from '@dotmac/headless';
import { Card } from '@dotmac/ui/customer';
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  Clock,
  CreditCard,
  DollarSign,
  Download,
  ExternalLink,
  FileText,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuthStore } from '@dotmac/headless/auth';

interface BillingOverviewProps {
  customerId: string;
}

export default function BillingOverviewNew({ customerId }: BillingOverviewProps) {
  // ✅ NEW: Single centralized business operations hook
  // ❌ OLD: useCustomerBilling, useBilling, useInvoices, usePayments, etc.
  const business = useCustomerBusiness(customerId);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [billingData, setBillingData] = useState({
    profile: null as any,
    bills: [] as any[],
    serviceStatus: null as any,
    usage: [] as any[],
  });

  // Load all billing data using centralized operations
  useEffect(() => {
    const loadBillingData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // ✅ NEW: Single source of truth for all customer operations
        // These operations are now shared across ALL portals (Admin, Customer, Reseller, Management)
        const [profile, bills, serviceStatus, usage] = await Promise.all([
          business.getMyProfile(),
          business.getMyBills(),
          business.getMyServiceStatus(),
          business.getMyUsage({
            startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
            endDate: new Date(),
          }),
        ]);

        setBillingData({ profile, bills, serviceStatus, usage });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load billing data');
        console.error('Billing data error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadBillingData();
  }, [business, customerId]);

  // Handle payment using centralized operations
  const handlePayBill = async (invoiceId: string, paymentMethodId: string, amount: number) => {
    try {
      // ✅ NEW: Centralized payment processing
      // Same logic used in Admin portal for manual payments, Reseller for commission payments, etc.
      await business.payBill({
        customerId,
        amount,
        currency: 'USD',
        paymentMethodId,
        invoiceId,
        description: `Payment for invoice ${invoiceId}`,
      });

      // Refresh billing data
      const updatedBills = await business.getMyBills();
      setBillingData((prev) => ({ ...prev, bills: updatedBills }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Payment failed');
    }
  };

  if (isLoading) {
    return (
      <div className='space-y-6'>
        <div className='animate-pulse'>
          <div className='h-8 bg-gray-200 rounded mb-4'></div>
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
            {[1, 2, 3].map((i) => (
              <div key={i} className='h-32 bg-gray-200 rounded'></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <div className='flex items-center space-x-3 p-4'>
          <AlertCircle className='h-5 w-5 text-red-500' />
          <div>
            <h3 className='font-medium text-red-800'>Error Loading Billing Information</h3>
            <p className='text-sm text-red-600'>{error}</p>
          </div>
        </div>
      </Card>
    );
  }

  const { profile, bills, serviceStatus, usage } = billingData;
  const currentBill = bills.find((bill) => bill.status === 'sent') || bills[0];
  const totalUsage = usage.reduce((sum, day) => sum + day.totalGB, 0);

  return (
    <div className='space-y-6'>
      <div>
        <h2 className='text-2xl font-bold text-gray-900'>Billing Overview</h2>
        <p className='text-gray-600'>Manage your account billing and payments</p>
      </div>

      {/* Account Balance & Next Bill */}
      <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
        <Card>
          <div className='p-6'>
            <div className='flex items-center'>
              <div className='flex-shrink-0'>
                <DollarSign className='h-8 w-8 text-green-500' />
              </div>
              <div className='ml-5 w-0 flex-1'>
                <dl>
                  <dt className='text-sm font-medium text-gray-500 truncate'>Current Balance</dt>
                  <dd className='text-lg font-medium text-gray-900'>
                    ${profile?.accountBalance?.toFixed(2) || '0.00'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className='p-6'>
            <div className='flex items-center'>
              <div className='flex-shrink-0'>
                <Calendar className='h-8 w-8 text-blue-500' />
              </div>
              <div className='ml-5 w-0 flex-1'>
                <dl>
                  <dt className='text-sm font-medium text-gray-500 truncate'>Next Bill Date</dt>
                  <dd className='text-lg font-medium text-gray-900'>
                    {currentBill?.dueDate
                      ? new Date(currentBill.dueDate).toLocaleDateString()
                      : 'N/A'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className='p-6'>
            <div className='flex items-center'>
              <div className='flex-shrink-0'>
                <FileText className='h-8 w-8 text-purple-500' />
              </div>
              <div className='ml-5 w-0 flex-1'>
                <dl>
                  <dt className='text-sm font-medium text-gray-500 truncate'>Next Bill Amount</dt>
                  <dd className='text-lg font-medium text-gray-900'>
                    ${currentBill?.amount?.toFixed(2) || '0.00'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Service Status */}
      <Card>
        <div className='px-6 py-4 border-b border-gray-200'>
          <h3 className='text-lg font-medium text-gray-900'>Service Status</h3>
        </div>
        <div className='p-6'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <div
                className={`h-4 w-4 rounded-full ${
                  serviceStatus?.status === 'active'
                    ? 'bg-green-500'
                    : serviceStatus?.status === 'suspended'
                      ? 'bg-red-500'
                      : 'bg-yellow-500'
                }`}
              ></div>
              <div>
                <p className='font-medium capitalize'>{serviceStatus?.status || 'Unknown'}</p>
                <p className='text-sm text-gray-500'>
                  Current Speed: {serviceStatus?.currentSpeed?.download || 0} /{' '}
                  {serviceStatus?.currentSpeed?.upload || 0} Mbps
                </p>
              </div>
            </div>
            <div className='text-right'>
              <p className='font-medium'>{serviceStatus?.uptime || 0}% Uptime</p>
              <p className='text-sm text-gray-500'>Last 30 days</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Usage Overview */}
      <Card>
        <div className='px-6 py-4 border-b border-gray-200'>
          <h3 className='text-lg font-medium text-gray-900'>Usage Overview</h3>
        </div>
        <div className='p-6'>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
            <div>
              <p className='text-sm text-gray-500'>Total Usage (30 days)</p>
              <p className='text-2xl font-bold text-gray-900'>{totalUsage.toFixed(1)} GB</p>
            </div>
            <div>
              <p className='text-sm text-gray-500'>Daily Average</p>
              <p className='text-2xl font-bold text-gray-900'>{(totalUsage / 30).toFixed(1)} GB</p>
            </div>
            <div>
              <p className='text-sm text-gray-500'>Plan Limit</p>
              <p className='text-2xl font-bold text-gray-900'>
                {profile?.currentPlan?.dataLimit
                  ? `${profile.currentPlan.dataLimit} GB`
                  : 'Unlimited'}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Recent Bills */}
      <Card>
        <div className='px-6 py-4 border-b border-gray-200'>
          <div className='flex items-center justify-between'>
            <h3 className='text-lg font-medium text-gray-900'>Recent Bills</h3>
            <button className='text-blue-600 hover:text-blue-700 text-sm font-medium'>
              View All
            </button>
          </div>
        </div>
        <div className='divide-y divide-gray-200'>
          {bills.slice(0, 5).map((bill) => (
            <div key={bill.id} className='p-6 flex items-center justify-between'>
              <div className='flex items-center space-x-4'>
                <div
                  className={`p-2 rounded-full ${
                    bill.status === 'paid'
                      ? 'bg-green-100'
                      : bill.status === 'overdue'
                        ? 'bg-red-100'
                        : 'bg-yellow-100'
                  }`}
                >
                  {bill.status === 'paid' ? (
                    <CheckCircle className='h-5 w-5 text-green-600' />
                  ) : bill.status === 'overdue' ? (
                    <AlertCircle className='h-5 w-5 text-red-600' />
                  ) : (
                    <Clock className='h-5 w-5 text-yellow-600' />
                  )}
                </div>
                <div>
                  <p className='font-medium text-gray-900'>{bill.invoiceNumber}</p>
                  <p className='text-sm text-gray-500'>
                    Due: {new Date(bill.dueDate).toLocaleDateString()}
                    {bill.paidDate && <> • Paid: {new Date(bill.paidDate).toLocaleDateString()}</>}
                  </p>
                </div>
              </div>
              <div className='flex items-center space-x-4'>
                <span className='font-medium text-gray-900'>${bill.amount.toFixed(2)}</span>
                <div className='flex space-x-2'>
                  <button className='p-2 text-gray-400 hover:text-gray-500'>
                    <Download className='h-4 w-4' />
                  </button>
                  <button className='p-2 text-gray-400 hover:text-gray-500'>
                    <ExternalLink className='h-4 w-4' />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Payment Method */}
      <Card>
        <div className='px-6 py-4 border-b border-gray-200'>
          <h3 className='text-lg font-medium text-gray-900'>Payment Method</h3>
        </div>
        <div className='p-6'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-4'>
              <div className='p-3 bg-gray-100 rounded-lg'>
                <CreditCard className='h-6 w-6 text-gray-600' />
              </div>
              <div>
                <p className='font-medium text-gray-900'>
                  **** **** **** {profile?.paymentMethod?.lastFour || '1234'}
                </p>
                <p className='text-sm text-gray-500'>
                  Auto Pay {profile?.preferences?.autoPayEnabled ? 'Enabled' : 'Disabled'}
                </p>
              </div>
            </div>
            <button className='text-blue-600 hover:text-blue-700 font-medium'>Manage</button>
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
        <Card>
          <div className='p-6 text-center'>
            <h3 className='text-lg font-medium text-gray-900 mb-4'>Make a Payment</h3>
            <p className='text-gray-600 mb-4'>Pay your current bill or make an advance payment</p>
            <button
              className='w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium'
              onClick={() => {
                if (currentBill && currentBill.status !== 'paid') {
                  handlePayBill(currentBill.id, 'default', currentBill.amount);
                }
              }}
              disabled={!currentBill || currentBill.status === 'paid'}
            >
              Pay ${currentBill?.amount?.toFixed(2) || '0.00'}
            </button>
          </div>
        </Card>

        <Card>
          <div className='p-6 text-center'>
            <h3 className='text-lg font-medium text-gray-900 mb-4'>Upgrade Service</h3>
            <p className='text-gray-600 mb-4'>View available plans and upgrade your service</p>
            <button className='w-full bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 font-medium'>
              View Plans
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}

/**
 * COMPARISON: BEFORE vs AFTER
 *
 * BEFORE (Old approach):
 * ❌ Multiple hooks: useCustomerBilling, useBilling, useInvoices, usePayments
 * ❌ Duplicate API calls across components
 * ❌ Inconsistent error handling
 * ❌ Separate payment logic in each portal
 * ❌ No shared business rules
 * ❌ Manual data synchronization
 *
 * AFTER (New centralized approach):
 * ✅ Single hook: useCustomerBusiness
 * ✅ Shared business operations across ALL portals
 * ✅ Consistent error handling with ISPError
 * ✅ Centralized payment processing
 * ✅ Business rules enforced in one place
 * ✅ Automatic data consistency
 * ✅ Portal-optimized convenience methods
 * ✅ Same logic in Admin portal, Reseller portal, Management portal
 * ✅ DRY compliance achieved
 */
