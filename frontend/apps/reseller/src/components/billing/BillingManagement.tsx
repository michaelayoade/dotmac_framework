'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { useBilling } from '@dotmac/headless';
import { 
  useNotifications,
  VirtualizedTable,
  Modal 
} from '@dotmac/primitives';

interface BillingManagementProps {
  className?: string;
}

export function BillingManagement({ className = '' }: BillingManagementProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'payments' | 'accounts'>('overview');
  const [selectedInvoices, setSelectedInvoices] = useState<string[]>([]);
  const [showNewInvoiceModal, setShowNewInvoiceModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPaymentInvoice, setSelectedPaymentInvoice] = useState<any>(null);
  const [invoiceFilters, setInvoiceFilters] = useState({
    status: '',
    dateFrom: '',
    dateTo: '',
  });

  const billing = useBilling({
    websocketEndpoint: process.env.NEXT_PUBLIC_WS_URL,
    apiKey: process.env.NEXT_PUBLIC_API_KEY,
    stripePk: process.env.NEXT_PUBLIC_STRIPE_PK,
    enableRealtime: true,
    pollInterval: 60000,
  });

  const { addNotification } = useNotifications();

  // Quick Actions
  const handleBulkInvoiceSend = useCallback(async () => {
    if (selectedInvoices.length === 0) return;
    
    try {
      for (const invoiceId of selectedInvoices) {
        await billing.sendInvoice(invoiceId);
      }
      
      setSelectedInvoices([]);
      
      addNotification({
        type: 'success',
        priority: 'medium',
        title: 'Bulk Send Complete',
        message: `${selectedInvoices.length} invoices sent successfully`,
        channel: ['browser'],
        persistent: false,
      });
    } catch (error) {
      console.error('Failed to send invoices:', error);
    }
  }, [billing, selectedInvoices, addNotification]);

  const handleQuickPayment = useCallback((invoice: any) => {
    setSelectedPaymentInvoice(invoice);
    setShowPaymentModal(true);
  }, []);

  // Filtered data
  const filteredInvoices = useMemo(() => {
    return billing.invoices.filter(invoice => {
      if (invoiceFilters.status && invoice.status !== invoiceFilters.status) return false;
      if (invoiceFilters.dateFrom && invoice.issueDate < new Date(invoiceFilters.dateFrom)) return false;
      if (invoiceFilters.dateTo && invoice.issueDate > new Date(invoiceFilters.dateTo)) return false;
      return true;
    });
  }, [billing.invoices, invoiceFilters]);

  const stats = billing.stats || {
    totalRevenue: 0,
    monthlyRecurringRevenue: 0,
    averageRevenuePerUser: 0,
    churnRate: 0,
    totalInvoices: 0,
    paidInvoices: 0,
    overdueInvoices: 0,
    totalOutstanding: 0,
    collectionRate: 0,
    paymentMethodBreakdown: {},
    revenueByPlan: {},
    recentPayments: [],
    upcomingRenewals: [],
  };

  return (
    <div className={`billing-management ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Billing Management</h1>
          <div className="flex items-center space-x-2">
            {billing.isConnected ? (
              <div className="flex items-center space-x-1 text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm">Live Updates</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1 text-red-600">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-sm">Offline</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {selectedInvoices.length > 0 && (
            <button
              onClick={handleBulkInvoiceSend}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Send {selectedInvoices.length} Invoices
            </button>
          )}
          <button
            onClick={() => setShowNewInvoiceModal(true)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            disabled={billing.isLoading}
          >
            Create Invoice
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Total Revenue</p>
              <p className="text-2xl font-bold text-green-600">${stats.totalRevenue.toLocaleString()}</p>
            </div>
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
              <span className="text-green-600">💰</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              MRR: ${stats.monthlyRecurringRevenue.toLocaleString()}
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Outstanding</p>
              <p className="text-2xl font-bold text-orange-600">${billing.totalOutstanding.toLocaleString()}</p>
            </div>
            <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
              <span className="text-orange-600">⏰</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              {stats.overdueInvoices} overdue invoices
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Collection Rate</p>
              <p className="text-2xl font-bold text-blue-600">{stats.collectionRate.toFixed(1)}%</p>
            </div>
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600">📊</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              {stats.paidInvoices}/{stats.totalInvoices} paid
            </p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">ARPU</p>
              <p className="text-2xl font-bold text-purple-600">${stats.averageRevenuePerUser.toFixed(0)}</p>
            </div>
            <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
              <span className="text-purple-600">👤</span>
            </div>
          </div>
          <div className="mt-2">
            <p className="text-xs text-gray-500">
              Churn: {stats.churnRate.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'invoices', label: 'Invoices', count: billing.invoices.length },
            { id: 'payments', label: 'Payments', count: billing.payments.length },
            { id: 'accounts', label: 'Accounts', count: billing.accounts.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2.5 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && (
          <OverviewTab
            stats={stats}
            overdueInvoices={billing.overdueInvoices}
            failedPayments={billing.failedPayments}
            recentPayments={billing.recentPayments}
            onQuickPayment={handleQuickPayment}
          />
        )}

        {activeTab === 'invoices' && (
          <InvoicesTab
            invoices={filteredInvoices}
            filters={invoiceFilters}
            onFiltersChange={setInvoiceFilters}
            selectedInvoices={selectedInvoices}
            onSelectionChange={setSelectedInvoices}
            onUpdateStatus={billing.updateInvoiceStatus}
            onSendInvoice={billing.sendInvoice}
            onProcessPayment={handleQuickPayment}
            isLoading={billing.isLoading}
          />
        )}

        {activeTab === 'payments' && (
          <PaymentsTab
            payments={billing.payments}
            onRefund={billing.refundPayment}
            onRetry={billing.retryPayment}
            isProcessing={billing.paymentProcessing}
          />
        )}

        {activeTab === 'accounts' && (
          <AccountsTab
            accounts={billing.accounts}
            onSelectAccount={billing.selectAccount}
            selectedAccount={billing.selectedAccount}
          />
        )}
      </div>

      {/* New Invoice Modal */}
      {showNewInvoiceModal && (
        <NewInvoiceModal
          accounts={billing.accounts}
          onSubmit={async (invoiceData) => {
            try {
              await billing.createInvoice(invoiceData);
              setShowNewInvoiceModal(false);
            } catch (error) {
              console.error('Failed to create invoice:', error);
            }
          }}
          onClose={() => setShowNewInvoiceModal(false)}
        />
      )}

      {/* Payment Modal */}
      {showPaymentModal && selectedPaymentInvoice && (
        <PaymentModal
          invoice={selectedPaymentInvoice}
          onProcessPayment={async (paymentData) => {
            try {
              await billing.processPayment(paymentData);
              setShowPaymentModal(false);
              setSelectedPaymentInvoice(null);
            } catch (error) {
              console.error('Failed to process payment:', error);
            }
          }}
          onClose={() => {
            setShowPaymentModal(false);
            setSelectedPaymentInvoice(null);
          }}
          isProcessing={billing.paymentProcessing}
        />
      )}
    </div>
  );
}

// Overview Tab Component
interface OverviewTabProps {
  stats: any;
  overdueInvoices: any[];
  failedPayments: any[];
  recentPayments: any[];
  onQuickPayment: (invoice: any) => void;
}

function OverviewTab({ 
  stats, 
  overdueInvoices, 
  failedPayments, 
  recentPayments,
  onQuickPayment 
}: OverviewTabProps) {
  return (
    <div className="overview-tab">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payment Method Breakdown */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Payment Methods</h2>
          <div className="space-y-3">
            {Object.entries(stats.paymentMethodBreakdown).map(([method, count]) => (
              <div key={method} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 capitalize">{method.replace('_', ' ')}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 bg-gray-200 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full bg-blue-600" 
                      style={{ 
                        width: `${(count as number / Object.values(stats.paymentMethodBreakdown)
                          .reduce((sum, c) => sum + (c as number), 0)) * 100}%` 
                      }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">{count as number}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Revenue by Plan */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Revenue by Plan</h2>
          <div className="space-y-3">
            {Object.entries(stats.revenueByPlan).slice(0, 5).map(([plan, revenue]) => (
              <div key={plan} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{plan}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 bg-gray-200 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full bg-green-600" 
                      style={{ 
                        width: `${(revenue as number / Math.max(...Object.values(stats.revenueByPlan) as number[])) * 100}%` 
                      }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">${(revenue as number).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Overdue Invoices */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Overdue Invoices ({overdueInvoices.length})
          </h2>
          <div className="space-y-3">
            {overdueInvoices.slice(0, 5).map((invoice) => (
              <div 
                key={invoice.id}
                className="flex items-center justify-between p-3 border border-red-200 rounded-lg bg-red-50"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{invoice.invoiceNumber}</p>
                  <p className="text-xs text-gray-500">
                    Due: {new Date(invoice.dueDate).toLocaleDateString()} • 
                    ${invoice.amountDue.toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => onQuickPayment(invoice)}
                  className="text-xs bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
                >
                  Collect
                </button>
              </div>
            ))}
            {overdueInvoices.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No overdue invoices</p>
            )}
          </div>
        </div>

        {/* Recent Payments */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Recent Payments ({recentPayments.length})
          </h2>
          <div className="space-y-3">
            {recentPayments.slice(0, 5).map((payment) => (
              <div 
                key={payment.id}
                className="flex items-center justify-between p-3 border border-green-200 rounded-lg bg-green-50"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">${payment.amount.toLocaleString()}</p>
                  <p className="text-xs text-gray-500">
                    {payment.method?.type} ending in {payment.method?.lastFour} • 
                    {payment.processedAt ? new Date(payment.processedAt).toLocaleDateString() : 'Processing'}
                  </p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  payment.status === 'completed' ? 'bg-green-600 text-white' :
                  payment.status === 'failed' ? 'bg-red-600 text-white' :
                  'bg-yellow-600 text-white'
                }`}>
                  {payment.status}
                </span>
              </div>
            ))}
            {recentPayments.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No recent payments</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Invoices Tab Component
interface InvoicesTabProps {
  invoices: any[];
  filters: any;
  onFiltersChange: (filters: any) => void;
  selectedInvoices: string[];
  onSelectionChange: (ids: string[]) => void;
  onUpdateStatus: (id: string, status: string, notes?: string) => Promise<any>;
  onSendInvoice: (id: string, email?: string) => Promise<void>;
  onProcessPayment: (invoice: any) => void;
  isLoading: boolean;
}

function InvoicesTab({ 
  invoices, 
  filters, 
  onFiltersChange, 
  selectedInvoices, 
  onSelectionChange,
  onUpdateStatus,
  onSendInvoice,
  onProcessPayment,
  isLoading 
}: InvoicesTabProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid': return 'text-green-600 bg-green-50';
      case 'sent': return 'text-blue-600 bg-blue-50';
      case 'overdue': return 'text-red-600 bg-red-50';
      case 'draft': return 'text-gray-600 bg-gray-50';
      case 'cancelled': return 'text-gray-600 bg-gray-50';
      case 'refunded': return 'text-purple-600 bg-purple-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const columns = [
    {
      key: 'select',
      header: (
        <input
          type="checkbox"
          checked={selectedInvoices.length === invoices.length && invoices.length > 0}
          onChange={(e) => {
            if (e.target.checked) {
              onSelectionChange(invoices.map(inv => inv.id));
            } else {
              onSelectionChange([]);
            }
          }}
          className="rounded border-gray-300"
        />
      ),
      render: (invoice: any) => (
        <input
          type="checkbox"
          checked={selectedInvoices.includes(invoice.id)}
          onChange={(e) => {
            if (e.target.checked) {
              onSelectionChange([...selectedInvoices, invoice.id]);
            } else {
              onSelectionChange(selectedInvoices.filter(id => id !== invoice.id));
            }
          }}
          className="rounded border-gray-300"
        />
      ),
    },
    {
      key: 'invoice',
      header: 'Invoice',
      render: (invoice: any) => (
        <div>
          <p className="font-medium text-gray-900">{invoice.invoiceNumber}</p>
          <p className="text-sm text-gray-500">{invoice.customerId}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (invoice: any) => (
        <div>
          <p className="font-medium text-gray-900">${invoice.totalAmount.toLocaleString()}</p>
          {invoice.amountDue > 0 && (
            <p className="text-sm text-red-600">Due: ${invoice.amountDue.toLocaleString()}</p>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (invoice: any) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(invoice.status)}`}>
          {invoice.status}
        </span>
      ),
    },
    {
      key: 'issued',
      header: 'Issued',
      render: (invoice: any) => (
        <span className="text-sm text-gray-500">
          {new Date(invoice.issueDate).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'due',
      header: 'Due Date',
      render: (invoice: any) => (
        <span className={`text-sm ${
          new Date(invoice.dueDate) < new Date() && invoice.status !== 'paid' 
            ? 'text-red-600 font-medium' 
            : 'text-gray-500'
        }`}>
          {new Date(invoice.dueDate).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (invoice: any) => (
        <div className="flex space-x-2">
          {invoice.status === 'draft' && (
            <button
              onClick={() => onSendInvoice(invoice.id)}
              className="text-blue-600 hover:text-blue-900 text-sm"
            >
              Send
            </button>
          )}
          {['sent', 'overdue'].includes(invoice.status) && (
            <button
              onClick={() => onProcessPayment(invoice)}
              className="text-green-600 hover:text-green-900 text-sm"
            >
              Collect
            </button>
          )}
          {invoice.status === 'paid' && (
            <button
              onClick={() => onUpdateStatus(invoice.id, 'refunded')}
              className="text-red-600 hover:text-red-900 text-sm"
            >
              Refund
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="invoices-tab">
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => onFiltersChange({ ...filters, status: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="paid">Paid</option>
              <option value="overdue">Overdue</option>
              <option value="cancelled">Cancelled</option>
              <option value="refunded">Refunded</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => onFiltersChange({ ...filters, dateFrom: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => onFiltersChange({ ...filters, dateTo: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-500">Loading invoices...</p>
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">📄</div>
            <p className="text-gray-500">No invoices found</p>
          </div>
        ) : (
          <VirtualizedTable
            data={invoices}
            columns={columns}
            height={600}
            rowHeight={60}
            className="w-full"
          />
        )}
      </div>
    </div>
  );
}

// Payments Tab Component
interface PaymentsTabProps {
  payments: any[];
  onRefund: (paymentId: string, amount: number, reason: string) => Promise<any>;
  onRetry: (paymentId: string) => Promise<any>;
  isProcessing: boolean;
}

function PaymentsTab({ payments, onRefund, onRetry, isProcessing }: PaymentsTabProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50';
      case 'failed': return 'text-red-600 bg-red-50';
      case 'pending': return 'text-yellow-600 bg-yellow-50';
      case 'processing': return 'text-blue-600 bg-blue-50';
      case 'cancelled': return 'text-gray-600 bg-gray-50';
      case 'refunded': return 'text-purple-600 bg-purple-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="payments-tab">
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {payments.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">💳</div>
            <p className="text-gray-500">No payments found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Payment
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Method
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {payments.map((payment) => (
                  <tr key={payment.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{payment.id}</p>
                        <p className="text-sm text-gray-500">Invoice: {payment.invoiceId}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <p className="text-sm font-medium text-gray-900">${payment.amount.toLocaleString()}</p>
                      {payment.refundedAmount > 0 && (
                        <p className="text-sm text-red-600">Refunded: ${payment.refundedAmount.toLocaleString()}</p>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {payment.method?.type} ending in {payment.method?.lastFour}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(payment.status)}`}>
                        {payment.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {payment.processedAt ? new Date(payment.processedAt).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {payment.status === 'failed' && (
                        <button
                          onClick={() => onRetry(payment.id)}
                          disabled={isProcessing}
                          className="text-blue-600 hover:text-blue-900 mr-3 disabled:opacity-50"
                        >
                          Retry
                        </button>
                      )}
                      {payment.status === 'completed' && payment.refundedAmount < payment.amount && (
                        <button
                          onClick={() => {
                            const reason = prompt('Refund reason:');
                            if (reason) {
                              onRefund(payment.id, payment.amount - payment.refundedAmount, reason);
                            }
                          }}
                          disabled={isProcessing}
                          className="text-red-600 hover:text-red-900 disabled:opacity-50"
                        >
                          Refund
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// Accounts Tab Component
interface AccountsTabProps {
  accounts: any[];
  onSelectAccount: (account: any) => void;
  selectedAccount: any;
}

function AccountsTab({ accounts, onSelectAccount, selectedAccount }: AccountsTabProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-50';
      case 'suspended': return 'text-yellow-600 bg-yellow-50';
      case 'cancelled': return 'text-gray-600 bg-gray-50';
      case 'past_due': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="accounts-tab">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.map((account) => (
          <div 
            key={account.id} 
            className={`bg-white p-6 rounded-lg shadow cursor-pointer transition-all ${
              selectedAccount?.id === account.id ? 'ring-2 ring-blue-500' : 'hover:shadow-md'
            }`}
            onClick={() => onSelectAccount(account)}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">{account.accountNumber}</h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(account.status)}`}>
                {account.status}
              </span>
            </div>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-gray-600">Customer: <span className="font-medium">{account.customerId}</span></p>
              <p className="text-sm text-gray-600">Balance: <span className="font-medium">${account.balance.toLocaleString()}</span></p>
              <p className="text-sm text-gray-600">Billing: <span className="font-medium capitalize">{account.billingCycle}</span></p>
              <p className="text-sm text-gray-600">
                Next Bill: <span className="font-medium">{new Date(account.nextBillDate).toLocaleDateString()}</span>
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-gray-500">Billing Address:</p>
              <p className="text-sm text-gray-700">
                {account.billingAddress.street}<br/>
                {account.billingAddress.city}, {account.billingAddress.state} {account.billingAddress.zip}
              </p>
            </div>

            {account.paymentMethod && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Payment Method:</p>
                <p className="text-sm text-gray-700">
                  {account.paymentMethod.type} ending in {account.paymentMethod.lastFour}
                  {account.paymentMethod.isDefault && <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-1 rounded">Default</span>}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {accounts.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-4xl mb-4">🏦</div>
          <p className="text-gray-500">No billing accounts found.</p>
        </div>
      )}
    </div>
  );
}

// New Invoice Modal Component
interface NewInvoiceModalProps {
  accounts: any[];
  onSubmit: (invoiceData: any) => Promise<void>;
  onClose: () => void;
}

function NewInvoiceModal({ accounts, onSubmit, onClose }: NewInvoiceModalProps) {
  const [formData, setFormData] = useState({
    customerId: '',
    accountId: '',
    dueDate: '',
    lineItems: [{ description: '', quantity: 1, unitPrice: 0 }],
    notes: '',
    sendEmail: true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const invoiceData = {
      ...formData,
      dueDate: new Date(formData.dueDate),
      lineItems: formData.lineItems.map(item => ({
        ...item,
        amount: item.quantity * item.unitPrice,
      })),
    };

    await onSubmit(invoiceData);
  };

  const addLineItem = () => {
    setFormData({
      ...formData,
      lineItems: [...formData.lineItems, { description: '', quantity: 1, unitPrice: 0 }],
    });
  };

  return (
    <Modal onClose={onClose} className="max-w-2xl">
      <div className="p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Create New Invoice</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Customer ID</label>
              <input
                type="text"
                value={formData.customerId}
                onChange={(e) => setFormData({ ...formData, customerId: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
              <input
                type="date"
                value={formData.dueDate}
                onChange={(e) => setFormData({ ...formData, dueDate: e.target.value })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Line Items</label>
            <div className="space-y-2">
              {formData.lineItems.map((item, index) => (
                <div key={index} className="grid grid-cols-6 gap-2">
                  <div className="col-span-3">
                    <input
                      type="text"
                      placeholder="Description"
                      value={item.description}
                      onChange={(e) => {
                        const newLineItems = [...formData.lineItems];
                        newLineItems[index] = { ...item, description: e.target.value };
                        setFormData({ ...formData, lineItems: newLineItems });
                      }}
                      required
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <input
                      type="number"
                      placeholder="Qty"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => {
                        const newLineItems = [...formData.lineItems];
                        newLineItems[index] = { ...item, quantity: parseInt(e.target.value) || 1 };
                        setFormData({ ...formData, lineItems: newLineItems });
                      }}
                      required
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <input
                      type="number"
                      placeholder="Price"
                      min="0"
                      step="0.01"
                      value={item.unitPrice}
                      onChange={(e) => {
                        const newLineItems = [...formData.lineItems];
                        newLineItems[index] = { ...item, unitPrice: parseFloat(e.target.value) || 0 };
                        setFormData({ ...formData, lineItems: newLineItems });
                      }}
                      required
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="flex items-center">
                    <span className="text-sm text-gray-600">
                      ${(item.quantity * item.unitPrice).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
              <button
                type="button"
                onClick={addLineItem}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                + Add Line Item
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="sendEmail"
              checked={formData.sendEmail}
              onChange={(e) => setFormData({ ...formData, sendEmail: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="sendEmail" className="ml-2 text-sm text-gray-700">
              Send invoice via email
            </label>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700"
            >
              Create Invoice
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}

// Payment Modal Component
interface PaymentModalProps {
  invoice: any;
  onProcessPayment: (paymentData: any) => Promise<void>;
  onClose: () => void;
  isProcessing: boolean;
}

function PaymentModal({ invoice, onProcessPayment, onClose, isProcessing }: PaymentModalProps) {
  const [paymentData, setPaymentData] = useState({
    amount: invoice.amountDue,
    paymentMethodId: 'card_default', // This would come from a payment method selector
    gateway: 'stripe',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await onProcessPayment({
      invoiceId: invoice.id,
      ...paymentData,
    });
  };

  return (
    <Modal onClose={onClose} className="max-w-md">
      <div className="p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Process Payment</h2>
        
        <div className="mb-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="font-medium text-gray-900">Invoice {invoice.invoiceNumber}</h3>
            <p className="text-sm text-gray-600">Customer: {invoice.customerId}</p>
            <p className="text-sm text-gray-600">Amount Due: ${invoice.amountDue.toLocaleString()}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Amount</label>
            <input
              type="number"
              min="0.01"
              max={invoice.amountDue}
              step="0.01"
              value={paymentData.amount}
              onChange={(e) => setPaymentData({ 
                ...paymentData, 
                amount: parseFloat(e.target.value) || 0 
              })}
              required
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Gateway</label>
            <select
              value={paymentData.gateway}
              onChange={(e) => setPaymentData({ ...paymentData, gateway: e.target.value })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="stripe">Stripe</option>
              <option value="paypal">PayPal</option>
              <option value="manual">Manual Entry</option>
            </select>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50"
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isProcessing}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isProcessing && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              )}
              {isProcessing ? 'Processing...' : 'Process Payment'}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}

export default BillingManagement;