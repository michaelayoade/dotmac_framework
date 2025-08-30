'use client';

import React, { useState, useMemo } from 'react';
import {
  CreditCard,
  FileText,
  TrendingUp,
  AlertTriangle,
  Settings,
  Plus,
  History,
  RefreshCw,
  Download,
  Filter
} from 'lucide-react';
import { cn, getPortalFeatures } from '../utils';
import { useBillingSystem } from '../hooks/useBillingSystem';
import { UniversalPaymentForm } from './UniversalPaymentForm';
import { UniversalInvoiceGenerator } from './UniversalInvoiceGenerator';
import { UniversalPaymentMethodManager } from './UniversalPaymentMethodManager';
import { UniversalBillingHistory } from './UniversalBillingHistory';
import { UniversalPaymentFailureHandler } from './UniversalPaymentFailureHandler';
import type { UniversalBillingProps } from '../types';

type TabType = 'overview' | 'invoices' | 'payments' | 'methods' | 'history' | 'failures';

export function UniversalBillingDashboard({
  portalType = 'customer',
  customerId,
  accountId,
  permissions = [],
  theme = 'light',
  locale = 'en-US',
  currency = 'USD',
  features,
  ...billingOptions
}: UniversalBillingProps & {
  apiEndpoint?: string;
  websocketUrl?: string;
  enableRealtime?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [showInvoiceGenerator, setShowInvoiceGenerator] = useState(false);

  // Get portal-specific features
  const portalFeatures = useMemo(() => {
    return features || getPortalFeatures(portalType);
  }, [features, portalType]);

  // Use the unified billing system hook
  const billing = useBillingSystem({
    portalType,
    customerId: customerId || '',
    accountId: accountId || '',
    currency,
    features: portalFeatures,
    ...billingOptions
  });

  // Calculate summary metrics
  const summaryMetrics = useMemo(() => {
    const totalInvoices = billing.invoices.length;
    const paidInvoices = billing.invoices.filter(inv => inv.status === 'paid').length;
    const overdue = billing.invoices.filter(inv => inv.status === 'overdue').length;
    const totalRevenue = billing.invoices.reduce((sum, inv) => sum + (inv.status === 'paid' ? inv.totalAmount : 0), 0);
    const outstanding = billing.invoices.reduce((sum, inv) => sum + (inv.status !== 'paid' ? inv.amountDue : 0), 0);

    return {
      totalInvoices,
      paidInvoices,
      overdue,
      totalRevenue,
      outstanding,
      paymentSuccessRate: billing.payments.length > 0
        ? (billing.payments.filter(p => p.status === 'completed').length / billing.payments.length) * 100
        : 0
    };
  }, [billing.invoices, billing.payments]);

  // Available tabs based on portal type and features
  const availableTabs = useMemo(() => {
    const tabs = [
      { id: 'overview', label: 'Overview', icon: TrendingUp, count: null }
    ];

    if (portalFeatures.invoiceGeneration || billing.invoices.length > 0) {
      tabs.push({ id: 'invoices', label: 'Invoices', icon: FileText, count: billing.invoices.length > 0 ? billing.invoices.length : null });
    }

    if (portalFeatures.paymentProcessing || billing.payments.length > 0) {
      tabs.push({ id: 'payments', label: 'Payments', icon: CreditCard, count: billing.payments.length > 0 ? billing.payments.length : null });
    }

    if (billing.paymentMethods.length > 0 || portalType !== 'admin') {
      tabs.push({ id: 'methods', label: 'Payment Methods', icon: Settings, count: billing.paymentMethods.length > 0 ? billing.paymentMethods.length : null });
    }

    tabs.push({ id: 'history', label: 'History', icon: History, count: (billing.invoices.length + billing.payments.length) > 0 ? (billing.invoices.length + billing.payments.length) : null });

    if (billing.failedPayments.length > 0 && portalFeatures.paymentProcessing) {
      tabs.push({ id: 'failures', label: 'Failed Payments', icon: AlertTriangle, count: billing.failedPayments.length > 0 ? billing.failedPayments.length : null });
    }

    return tabs;
  }, [portalFeatures, billing, portalType]);

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Invoices</p>
              <p className="text-2xl font-bold text-gray-900">{summaryMetrics.totalInvoices}</p>
              <p className="text-sm text-green-600">{summaryMetrics.paidInvoices} paid</p>
            </div>
            <FileText className="w-8 h-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Revenue</p>
              <p className="text-2xl font-bold text-green-600">
                {Intl.NumberFormat(locale, { style: 'currency', currency }).format(summaryMetrics.totalRevenue)}
              </p>
              <p className="text-sm text-gray-500">Collected</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Outstanding</p>
              <p className="text-2xl font-bold text-orange-600">
                {Intl.NumberFormat(locale, { style: 'currency', currency }).format(summaryMetrics.outstanding)}
              </p>
              <p className="text-sm text-gray-500">{summaryMetrics.overdue} overdue</p>
            </div>
            <AlertTriangle className="w-8 h-8 text-orange-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Success Rate</p>
              <p className="text-2xl font-bold text-blue-600">
                {summaryMetrics.paymentSuccessRate.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500">Payment success</p>
            </div>
            <CreditCard className="w-8 h-8 text-blue-600" />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {portalFeatures.paymentProcessing && (
            <button
              onClick={() => setShowPaymentForm(true)}
              className="flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <CreditCard className="w-5 h-5 mr-2" />
              Make Payment
            </button>
          )}

          {portalFeatures.invoiceGeneration && (
            <button
              onClick={() => setShowInvoiceGenerator(true)}
              className="flex items-center justify-center px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <FileText className="w-5 h-5 mr-2" />
              Create Invoice
            </button>
          )}

          <button
            onClick={() => setActiveTab('methods')}
            className="flex items-center justify-center px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Settings className="w-5 h-5 mr-2" />
            Manage Methods
          </button>

          <button
            onClick={billing.refreshData}
            disabled={billing.isLoading}
            className="flex items-center justify-center px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-5 h-5 mr-2", billing.isLoading && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
          <button
            onClick={() => setActiveTab('history')}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            View All
          </button>
        </div>

        <UniversalBillingHistory
          invoices={billing.invoices.slice(0, 5)}
          payments={billing.payments.slice(0, 5)}
          portalType={portalType}
          currency={currency}
          showFilters={false}
          showExport={false}
          showSearch={false}
          itemsPerPage={10}
        />
      </div>

      {/* Failed Payments Alert */}
      {billing.failedPayments.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertTriangle className="w-5 h-5 text-red-600 mr-3" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800">Payment Failures Detected</h4>
              <p className="text-sm text-red-700">
                {billing.failedPayments.length} payments need attention.
              </p>
            </div>
            <button
              onClick={() => setActiveTab('failures')}
              className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
            >
              Review
            </button>
          </div>
        </div>
      )}
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return renderOverviewTab();

      case 'invoices':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Invoice Management</h3>
              {portalFeatures.invoiceGeneration && (
                <button
                  onClick={() => setShowInvoiceGenerator(true)}
                  className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Invoice
                </button>
              )}
            </div>

            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Invoice
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Customer
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Due Date
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {billing.invoices.map((invoice) => (
                    <tr key={invoice.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{invoice.invoiceNumber}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{invoice.customerName}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {Intl.NumberFormat(locale, { style: 'currency', currency }).format(invoice.totalAmount)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={cn(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                          invoice.status === 'paid' ? 'bg-green-100 text-green-800' :
                          invoice.status === 'overdue' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        )}>
                          {invoice.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(invoice.dueDate).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );

      case 'payments':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Payment Transactions</h3>
              {portalFeatures.paymentProcessing && (
                <button
                  onClick={() => setShowPaymentForm(true)}
                  className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Make Payment
                </button>
              )}
            </div>

            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Payment ID
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
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {billing.payments.map((payment) => (
                    <tr key={payment.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{payment.id}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {Intl.NumberFormat(locale, { style: 'currency', currency }).format(payment.amount)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {payment.method.brand} •••• {payment.method.last4}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={cn(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                          payment.status === 'completed' ? 'bg-green-100 text-green-800' :
                          payment.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        )}>
                          {payment.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {payment.processedAt ? new Date(payment.processedAt).toLocaleDateString() : 'Processing'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );

      case 'methods':
        return (
          <UniversalPaymentMethodManager
            paymentMethods={billing.paymentMethods}
            onAdd={billing.addPaymentMethod}
            onUpdate={billing.updatePaymentMethod}
            onRemove={billing.removePaymentMethod}
            onSetDefault={billing.setDefaultPaymentMethod}
            customerId={customerId || ''}
            portalType={portalType}
            allowMultiple={true}
          />
        );

      case 'history':
        return (
          <UniversalBillingHistory
            invoices={billing.invoices}
            payments={billing.payments}
            portalType={portalType}
            currency={currency}
            showFilters={true}
            showExport={true}
            showSearch={true}
          />
        );

      case 'failures':
        return (
          <UniversalPaymentFailureHandler
            failedPayments={billing.failedPayments}
            onRetryPayment={async (paymentId, paymentMethodId) => {
              await billing.retryPayment(paymentId, paymentMethodId);
            }}
            onUpdatePaymentMethod={(paymentId) => {
              // Navigate to payment method manager or trigger update flow
              setActiveTab('methods');
            }}
            onContactCustomer={async (paymentId, method) => {
              // Implement customer contact logic
              console.log('Contact customer for payment:', paymentId, method);
            }}
            onSuspendService={async (paymentId) => {
              // Implement service suspension logic
              console.log('Suspend service for payment:', paymentId);
            }}
            onWaivePayment={async (paymentId, reason) => {
              // Implement payment waiving logic
              console.log('Waive payment:', paymentId, reason);
            }}
            paymentMethods={billing.paymentMethods}
            portalType={portalType}
            currency={currency}
          />
        );

      default:
        return renderOverviewTab();
    }
  };

  return (
    <div className={cn("min-h-screen", theme === 'dark' ? 'bg-gray-900' : 'bg-gray-50')}>
      {/* Header */}
      <div className={cn("border-b", theme === 'dark' ? 'border-gray-800 bg-gray-900' : 'border-gray-200 bg-white')}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <h1 className={cn("text-xl font-semibold", theme === 'dark' ? 'text-white' : 'text-gray-900')}>
                Billing Dashboard
              </h1>
              {billing.isConnected && (
                <div className="flex items-center space-x-1 text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs">Live</span>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <span className={cn("text-sm", theme === 'dark' ? 'text-gray-300' : 'text-gray-600')}>
                {portalType.charAt(0).toUpperCase() + portalType.slice(1)} Portal
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className={cn("border-b", theme === 'dark' ? 'border-gray-800 bg-gray-900' : 'border-gray-200 bg-white')}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            {availableTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as TabType)}
                  className={cn(
                    "flex items-center py-4 px-1 border-b-2 font-medium text-sm",
                    activeTab === tab.id
                      ? theme === 'dark'
                        ? "border-blue-400 text-blue-400"
                        : "border-blue-500 text-blue-600"
                      : theme === 'dark'
                        ? "border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300"
                        : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  )}
                >
                  <Icon className="w-4 h-4 mr-2" />
                  {tab.label}
                  {tab.count !== null && (
                    <span className={cn(
                      "ml-2 py-0.5 px-2 rounded-full text-xs",
                      activeTab === tab.id
                        ? "bg-blue-100 text-blue-600"
                        : "bg-gray-100 text-gray-900"
                    )}>
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {billing.isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
          </div>
        ) : billing.error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-red-900 mb-2">Error Loading Data</h3>
            <p className="text-red-700 mb-4">{billing.error}</p>
            <button
              onClick={billing.refreshData}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        ) : (
          renderTabContent()
        )}
      </div>

      {/* Modals */}
      {showPaymentForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <UniversalPaymentForm
              onPayment={async (paymentData) => {
                await billing.processPayment(paymentData);
                setShowPaymentForm(false);
              }}
              onCancel={() => setShowPaymentForm(false)}
              existingPaymentMethods={billing.paymentMethods}
              currency={currency}
              portalType={portalType}
            />
          </div>
        </div>
      )}

      {showInvoiceGenerator && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <UniversalInvoiceGenerator
              accounts={billing.accounts}
              onGenerate={async (invoiceData) => {
                // Use the mock generateInvoice function for now
                const mockResult = {
                  id: `inv-${Date.now()}`,
                  ...invoiceData,
                  status: 'draft' as const,
                  createdAt: new Date(),
                  updatedAt: new Date()
                };
                setShowInvoiceGenerator(false);
                return mockResult;
              }}
              onSend={billing.sendInvoice}
              onCancel={() => setShowInvoiceGenerator(false)}
              currency={currency}
              portalType={portalType}
            />
          </div>
        </div>
      )}
    </div>
  );
}
