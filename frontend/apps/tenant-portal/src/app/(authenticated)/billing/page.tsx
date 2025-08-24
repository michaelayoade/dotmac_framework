'use client';

import { useState, useEffect } from 'react';
import { 
  CreditCard, 
  Download, 
  Calendar,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';
import { useTenantAuth } from '@/components/auth/TenantAuthProvider';

interface PaymentMethod {
  payment_method_id: string;
  type: string;
  card_brand?: string;
  card_last_four?: string;
  card_exp_month?: number;
  card_exp_year?: number;
  is_default: boolean;
  created_at: Date;
}

interface Invoice {
  invoice_id: string;
  invoice_date: Date;
  due_date: Date;
  period_start: Date;
  period_end: Date;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  amount_due: number;
  status: string;
  payment_date?: Date;
  line_items: Array<{
    description: string;
    amount: number;
    quantity: number;
  }>;
  payment_method: string;
  download_url: string;
}

interface BillingData {
  subscription_id: string;
  subscription_tier: string;
  billing_cycle: string;
  current_period_start: Date;
  current_period_end: Date;
  next_billing_date: Date;
  current_amount: number;
  next_amount: number;
  usage_charges: Record<string, number>;
  overage_charges: Record<string, number>;
  payment_methods: PaymentMethod[];
  default_payment_method: string;
  recent_invoices: Invoice[];
  account_status: string;
  days_overdue: number;
}

export default function BillingPage() {
  const { tenant } = useTenantAuth();
  const [billingData, setBillingData] = useState<BillingData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'payment-methods'>('overview');

  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    setIsLoading(true);
    try {
      // Mock billing data - would fetch from management platform API
      const mockData: BillingData = {
        subscription_id: 'sub_tenant123',
        subscription_tier: 'standard',
        billing_cycle: 'monthly',
        current_period_start: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
        current_period_end: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000),
        next_billing_date: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000),
        current_amount: 2500.00,
        next_amount: 2650.00,
        usage_charges: {
          'API Requests': 150.00,
          'Storage Overage': 75.00,
          'Bandwidth Overage': 25.00,
        },
        overage_charges: {
          'Additional Users': 50.00,
        },
        payment_methods: [
          {
            payment_method_id: 'pm_123',
            type: 'card',
            card_brand: 'visa',
            card_last_four: '4242',
            card_exp_month: 12,
            card_exp_year: 2025,
            is_default: true,
            created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
          }
        ],
        default_payment_method: 'pm_123',
        recent_invoices: [
          {
            invoice_id: 'inv_456',
            invoice_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
            due_date: new Date(Date.now() - 23 * 24 * 60 * 60 * 1000),
            period_start: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000),
            period_end: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
            subtotal: 2500.00,
            tax_amount: 225.00,
            total_amount: 2725.00,
            amount_paid: 2725.00,
            amount_due: 0.00,
            status: 'paid',
            payment_date: new Date(Date.now() - 22 * 24 * 60 * 60 * 1000),
            line_items: [
              { description: 'Standard Plan', amount: 2500.00, quantity: 1 },
              { description: 'API Overages', amount: 150.00, quantity: 1 },
            ],
            payment_method: 'Visa ending in 4242',
            download_url: '/api/invoices/inv_456.pdf',
          },
        ],
        account_status: 'active',
        days_overdue: 0,
      };

      setBillingData(mockData);
    } catch (error) {
      console.error('Failed to load billing data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading || !billingData) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', name: 'Overview' },
    { id: 'invoices', name: 'Invoices' },
    { id: 'payment-methods', name: 'Payment Methods' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Billing & Subscriptions</h2>
        <p className="text-gray-600">
          Manage your {tenant?.display_name} subscription and billing information.
        </p>
      </div>

      {/* Account Status Alert */}
      {billingData.days_overdue > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
            <div>
              <h4 className="text-sm font-medium text-red-800">Payment Overdue</h4>
              <p className="text-sm text-red-700">
                Your account is {billingData.days_overdue} days overdue. Please update your payment method.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-tenant-500 text-tenant-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Current Subscription */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="metric-card">
              <div className="flex items-center justify-between">
                <div>
                  <div className="metric-value">${billingData.current_amount.toLocaleString()}</div>
                  <div className="metric-label">Current Period</div>
                </div>
                <DollarSign className="h-8 w-8 text-tenant-500" />
              </div>
              <div className="metric-trend neutral">
                Billing cycle: {billingData.billing_cycle}
              </div>
            </div>

            <div className="metric-card">
              <div className="flex items-center justify-between">
                <div>
                  <div className="metric-value">${billingData.next_amount.toLocaleString()}</div>
                  <div className="metric-label">Next Payment</div>
                </div>
                <Calendar className="h-8 w-8 text-tenant-500" />
              </div>
              <div className="metric-trend neutral">
                Due: {billingData.next_billing_date.toLocaleDateString()}
              </div>
            </div>

            <div className="metric-card">
              <div className="flex items-center justify-between">
                <div>
                  <div className={`metric-value ${billingData.account_status === 'active' ? 'text-green-600' : 'text-red-600'}`}>
                    {billingData.account_status.charAt(0).toUpperCase() + billingData.account_status.slice(1)}
                  </div>
                  <div className="metric-label">Account Status</div>
                </div>
                <CheckCircle className={`h-8 w-8 ${billingData.account_status === 'active' ? 'text-green-500' : 'text-red-500'}`} />
              </div>
              <div className="metric-trend neutral">
                Plan: {billingData.subscription_tier}
              </div>
            </div>
          </div>

          {/* Usage Breakdown */}
          <div className="tenant-card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Period Usage</h3>
            <div className="space-y-4">
              {Object.entries(billingData.usage_charges).map(([item, amount]) => (
                <div key={item} className="flex items-center justify-between py-2">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{item}</div>
                    <div className="text-sm text-gray-500">Usage-based charge</div>
                  </div>
                  <div className="text-lg font-semibold text-gray-900">
                    ${amount.toFixed(2)}
                  </div>
                </div>
              ))}

              {Object.keys(billingData.overage_charges).length > 0 && (
                <>
                  <div className="border-t border-gray-200 pt-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Overage Charges</h4>
                  </div>
                  {Object.entries(billingData.overage_charges).map(([item, amount]) => (
                    <div key={item} className="flex items-center justify-between py-2">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{item}</div>
                        <div className="text-sm text-red-600">Overage charge</div>
                      </div>
                      <div className="text-lg font-semibold text-red-600">
                        ${amount.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button className="tenant-button-secondary text-left p-4 h-auto">
              <CreditCard className="h-6 w-6 mb-2" />
              <div className="font-medium">Update Payment Method</div>
              <div className="text-sm text-gray-500 mt-1">Change your billing card</div>
            </button>
            
            <button className="tenant-button-secondary text-left p-4 h-auto">
              <Download className="h-6 w-6 mb-2" />
              <div className="font-medium">Download Invoices</div>
              <div className="text-sm text-gray-500 mt-1">Get PDF receipts</div>
            </button>
            
            <button className="tenant-button-secondary text-left p-4 h-auto">
              <TrendingUp className="h-6 w-6 mb-2" />
              <div className="font-medium">Upgrade Plan</div>
              <div className="text-sm text-gray-500 mt-1">Scale your resources</div>
            </button>
          </div>
        </div>
      )}

      {activeTab === 'invoices' && (
        <div className="space-y-6">
          <div className="tenant-card">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Invoice History</h3>
            </div>
            
            <div className="overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Invoice
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Period
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {billingData.recent_invoices.map((invoice) => (
                    <tr key={invoice.invoice_id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {invoice.invoice_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {invoice.period_start.toLocaleDateString()} - {invoice.period_end.toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${invoice.total_amount.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`status-badge ${
                          invoice.status === 'paid' ? 'status-active' :
                          invoice.status === 'pending' ? 'status-pending' :
                          'status-suspended'
                        }`}>
                          {invoice.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <button className="text-tenant-600 hover:text-tenant-700 flex items-center">
                          <Download className="h-4 w-4 mr-1" />
                          Download
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'payment-methods' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">Payment Methods</h3>
            <button className="tenant-button-primary">
              Add Payment Method
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {billingData.payment_methods.map((method) => (
              <div key={method.payment_method_id} className="tenant-card p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <CreditCard className="h-8 w-8 text-gray-400 mr-3" />
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {method.card_brand?.toUpperCase()} ending in {method.card_last_four}
                      </div>
                      <div className="text-sm text-gray-500">
                        Expires {method.card_exp_month}/{method.card_exp_year}
                      </div>
                    </div>
                  </div>
                  
                  {method.is_default && (
                    <span className="status-active">Default</span>
                  )}
                </div>
                
                <div className="mt-4 flex space-x-2">
                  {!method.is_default && (
                    <button className="text-sm text-tenant-600 hover:text-tenant-700">
                      Make Default
                    </button>
                  )}
                  <button className="text-sm text-red-600 hover:text-red-700">
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}