'use client';

import { useCustomerBilling } from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/customer';
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
import { useState } from 'react';

// Mock billing data - in real app this would come from API
const _mockBillingData = {
  currentBalance: 0,
  nextBillDate: '2024-02-15',
  nextBillAmount: 109.98,
  lastPayment: {
    amount: 109.98,
    date: '2024-01-15',
    method: 'Auto Pay - Credit Card ending in 1234',
    confirmationNumber: 'PAY-20240115-001',
  },
  paymentMethod: {
    type: 'credit_card',
    last4: '1234',
    brand: 'Visa',
    expiryMonth: 12,
    expiryYear: 2026,
    isDefault: true,
    autoPayEnabled: true,
  },
  recentInvoices: [
    {
      id: 'INV-2024-001',
      invoiceNumber: 'INV-2024-001',
      amount: 109.98,
      dueDate: '2024-01-15',
      paidDate: '2024-01-15',
      status: 'paid',
      services: [
        { name: 'Fiber Internet 100/100', amount: 79.99 },
        { name: 'Basic Phone Service', amount: 29.99 },
      ],
    },
    {
      id: 'INV-2023-012',
      invoiceNumber: 'INV-2023-012',
      amount: 109.98,
      dueDate: '2023-12-15',
      paidDate: '2023-12-14',
      status: 'paid',
      services: [
        { name: 'Fiber Internet 100/100', amount: 79.99 },
        { name: 'Basic Phone Service', amount: 29.99 },
      ],
    },
    {
      id: 'INV-2023-011',
      invoiceNumber: 'INV-2023-011',
      amount: 109.98,
      dueDate: '2023-11-15',
      paidDate: '2023-11-15',
      status: 'paid',
      services: [
        { name: 'Fiber Internet 100/100', amount: 79.99 },
        { name: 'Basic Phone Service', amount: 29.99 },
      ],
    },
  ],
  paymentHistory: [
    {
      id: 'PAY-001',
      amount: 109.98,
      date: '2024-01-15',
      method: 'Credit Card',
      status: 'completed',
      invoiceId: 'INV-2024-001',
    },
    {
      id: 'PAY-002',
      amount: 109.98,
      date: '2023-12-14',
      method: 'Credit Card',
      status: 'completed',
      invoiceId: 'INV-2023-012',
    },
  ],
};

export function BillingOverview() {
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'payments' | 'settings'>(
    'overview'
  );

  const { data: billingData, isLoading, _isUsingMockData } = useCustomerBilling();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'overdue':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return 'text-green-600';
      case 'pending':
        return 'text-yellow-600';
      case 'overdue':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading || !billingData) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Billing Summary */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-600 text-sm">Current Balance</p>
              <p className="font-bold text-3xl text-gray-900">
                {formatCurrency(billingData.currentBalance)}
              </p>
              {billingData.currentBalance === 0 && (
                <p className="text-green-600 text-sm">All caught up</p>
              )}
            </div>
            <DollarSign className="h-8 w-8 text-green-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-600 text-sm">Next Bill</p>
              <p className="font-bold text-2xl text-gray-900">
                {formatCurrency(billingData.nextBillAmount)}
              </p>
              <p className="text-gray-500 text-sm">Due {formatDate(billingData.nextBillDate)}</p>
            </div>
            <Calendar className="h-8 w-8 text-blue-600" />
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-600 text-sm">Auto Pay</p>
              <p className="font-semibold text-gray-900 text-lg">
                {billingData.paymentMethod.autoPayEnabled ? 'Enabled' : 'Disabled'}
              </p>
              <p className="text-gray-500 text-sm">
                {billingData.paymentMethod.brand} •••• {billingData.paymentMethod.last4}
              </p>
            </div>
            <CreditCard className="h-8 w-8 text-purple-600" />
          </div>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="border-gray-200 border-b">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'invoices', label: 'Invoices' },
            { id: 'payments', label: 'Payment History' },
            { id: 'settings', label: 'Payment Settings' },
          ].map(tab => (
            <button
              type="button"
              key={tab.id}
              onClick={() => setActiveTab(tab.id as unknown)}
              className={`border-b-2 px-1 py-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Last Payment */}
          <Card className="p-6">
            <h3 className="mb-4 font-semibold text-gray-900 text-lg">Last Payment</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Amount</span>
                <span className="font-medium">
                  {formatCurrency(billingData.lastPayment.amount)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Date</span>
                <span className="font-medium">{formatDate(billingData.lastPayment.date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Method</span>
                <span className="font-medium">{billingData.lastPayment.method}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Confirmation</span>
                <span className="font-medium text-sm">
                  {billingData.lastPayment.confirmationNumber}
                </span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6">
            <h3 className="mb-4 font-semibold text-gray-900 text-lg">Quick Actions</h3>
            <div className="space-y-3">
              <button
                type="button"
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
              >
                Make a Payment
              </button>
              <button
                type="button"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
              >
                Update Payment Method
              </button>
              <button
                type="button"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
              >
                Set Up Auto Pay
              </button>
              <button
                type="button"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
              >
                Download Tax Documents
              </button>
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'invoices' && (
        <Card className="p-6">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 text-lg">Recent Invoices</h3>
            <button type="button" className="font-medium text-blue-600 text-sm hover:text-blue-800">
              View All Invoices
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
                    Invoice
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
                    Due Date
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {billingData.recentInvoices.map(invoice => (
                  <tr key={invoice.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-6 py-4">
                      <div>
                        <div className="font-medium text-gray-900 text-sm">
                          {invoice.invoiceNumber}
                        </div>
                        <div className="text-gray-500 text-sm">
                          {invoice.services.map(s => s.name).join(', ')}
                        </div>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="font-medium text-gray-900 text-sm">
                        {formatCurrency(invoice.amount)}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="text-gray-900 text-sm">{formatDate(invoice.dueDate)}</div>
                      {invoice.paidDate ? (
                        <div className="text-gray-500 text-sm">
                          Paid {formatDate(invoice.paidDate)}
                        </div>
                      ) : null}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="flex items-center">
                        {getStatusIcon(invoice.status)}
                        <span
                          className={`ml-2 text-sm capitalize ${getStatusColor(invoice.status)}`}
                        >
                          {invoice.status}
                        </span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm">
                      <div className="flex space-x-2">
                        <button type="button" className="text-blue-600 hover:text-blue-800">
                          <Download className="h-4 w-4" />
                        </button>
                        <button type="button" className="text-blue-600 hover:text-blue-800">
                          <ExternalLink className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'payments' && (
        <Card className="p-6">
          <h3 className="mb-6 font-semibold text-gray-900 text-lg">Payment History</h3>

          <div className="space-y-4">
            {billingData.paymentHistory.map(payment => (
              <div
                key={payment.id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div className="flex items-center">
                  {getStatusIcon(payment.status)}
                  <div className="ml-3">
                    <div className="font-medium text-gray-900 text-sm">
                      {formatCurrency(payment.amount)}
                    </div>
                    <div className="text-gray-500 text-sm">
                      {formatDate(payment.date)} • {payment.method}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-gray-500 text-sm">Invoice: {payment.invoiceId}</div>
                  <div className={`text-sm capitalize ${getStatusColor(payment.status)}`}>
                    {payment.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'settings' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Payment Method */}
          <Card className="p-6">
            <h3 className="mb-4 font-semibold text-gray-900 text-lg">Payment Method</h3>
            <div className="space-y-4">
              <div className="rounded-lg border p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <CreditCard className="mr-3 h-5 w-5 text-gray-400" />
                    <div>
                      <div className="font-medium text-gray-900 text-sm">
                        {billingData.paymentMethod.brand} •••• {billingData.paymentMethod.last4}
                      </div>
                      <div className="text-gray-500 text-sm">
                        Expires {billingData.paymentMethod.expiryMonth}/
                        {billingData.paymentMethod.expiryYear}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {billingData.paymentMethod.isDefault ? (
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 font-medium text-blue-800 text-xs">
                        Default
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="flex space-x-3">
                <button
                  type="button"
                  className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
                >
                  Update Card
                </button>
                <button
                  type="button"
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
                >
                  Add New Card
                </button>
              </div>
            </div>
          </Card>

          {/* Auto Pay Settings */}
          <Card className="p-6">
            <h3 className="mb-4 font-semibold text-gray-900 text-lg">Auto Pay Settings</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <div className="font-medium text-gray-900 text-sm">Automatic Payments</div>
                  <div className="text-gray-500 text-sm">
                    Pay bills automatically on the due date
                  </div>
                </div>
                <button
                  type="button"
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    billingData.paymentMethod.autoPayEnabled ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      billingData.paymentMethod.autoPayEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              <div className="rounded-lg bg-blue-50 p-4 text-gray-600 text-sm">
                <FileText className="mr-2 inline h-4 w-4" />
                Auto Pay is currently enabled. Your payment method will be charged automatically on
                the due date.
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
