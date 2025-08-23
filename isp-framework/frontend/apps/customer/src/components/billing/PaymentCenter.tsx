'use client';

import { useState } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import {
  CreditCard,
  Calendar,
  DollarSign,
  Download,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  Shield,
  Banknote
} from 'lucide-react';

interface PaymentMethod {
  id: string;
  type: 'credit_card' | 'bank_account' | 'paypal';
  name: string;
  last4: string;
  expiryDate?: string;
  isDefault: boolean;
  brand?: string;
}

interface AutoPaySettings {
  enabled: boolean;
  paymentMethodId: string;
  daysBeforeDue: number;
  minBalanceRequired: number;
}

interface Invoice {
  id: string;
  invoiceNumber: string;
  amount: number;
  dueDate: string;
  issueDate: string;
  status: 'paid' | 'pending' | 'overdue' | 'processing';
  services: string[];
  pdfUrl?: string;
}

interface Payment {
  id: string;
  invoiceId: string;
  amount: number;
  date: string;
  method: string;
  status: 'completed' | 'pending' | 'failed';
  confirmationNumber: string;
}

export function PaymentCenter() {
  const [activeTab, setActiveTab] = useState<'overview' | 'methods' | 'autopay' | 'history'>('overview');
  const [showAddPayment, setShowAddPayment] = useState(false);
  const [selectedInvoices, setSelectedInvoices] = useState<string[]>([]);

  // Mock data
  const paymentMethods: PaymentMethod[] = [
    {
      id: 'pm_1',
      type: 'credit_card',
      name: 'Visa ending in 4242',
      last4: '4242',
      expiryDate: '12/25',
      isDefault: true,
      brand: 'visa'
    },
    {
      id: 'pm_2',
      type: 'bank_account',
      name: 'Bank Account ending in 1234',
      last4: '1234',
      isDefault: false
    }
  ];

  const autoPaySettings: AutoPaySettings = {
    enabled: true,
    paymentMethodId: 'pm_1',
    daysBeforeDue: 3,
    minBalanceRequired: 0
  };

  const recentInvoices: Invoice[] = [
    {
      id: 'inv_1',
      invoiceNumber: 'INV-2024-001',
      amount: 109.98,
      dueDate: '2024-02-15',
      issueDate: '2024-01-15',
      status: 'pending',
      services: ['Fiber Internet 100/100', 'Basic Phone Service']
    },
    {
      id: 'inv_2',
      invoiceNumber: 'INV-2024-002',
      amount: 109.98,
      dueDate: '2024-01-15',
      issueDate: '2023-12-15',
      status: 'paid',
      services: ['Fiber Internet 100/100', 'Basic Phone Service']
    }
  ];

  const recentPayments: Payment[] = [
    {
      id: 'pay_1',
      invoiceId: 'inv_2',
      amount: 109.98,
      date: '2024-01-12',
      method: 'Visa ***4242',
      status: 'completed',
      confirmationNumber: 'TXN123456789'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'pending':
      case 'processing':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'overdue':
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'pending':
      case 'processing':
        return <Clock className="h-4 w-4" />;
      case 'overdue':
      case 'failed':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const handlePayInvoices = () => {
    // Process payment for selected invoices
    console.log('Paying invoices:', selectedInvoices);
    setSelectedInvoices([]);
  };

  const toggleInvoiceSelection = (invoiceId: string) => {
    setSelectedInvoices(prev => 
      prev.includes(invoiceId)
        ? prev.filter(id => id !== invoiceId)
        : [...prev, invoiceId]
    );
  };

  const totalSelectedAmount = selectedInvoices.reduce((total, invoiceId) => {
    const invoice = recentInvoices.find(inv => inv.id === invoiceId);
    return total + (invoice?.amount || 0);
  }, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Payment Center</h1>
        <p className="text-gray-600">Manage your billing and payment information</p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center">
            <DollarSign className="h-8 w-8 text-green-600" />
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">$109.98</p>
              <p className="text-gray-600 text-sm">Current Balance</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center">
            <Calendar className="h-8 w-8 text-blue-600" />
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">Feb 15</p>
              <p className="text-gray-600 text-sm">Next Due Date</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-600" />
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">On Time</p>
              <p className="text-gray-600 text-sm">Payment Status</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center">
            <Shield className="h-8 w-8 text-purple-600" />
            <div className="ml-3">
              <p className="text-2xl font-bold text-gray-900">AutoPay</p>
              <p className="text-gray-600 text-sm">
                {autoPaySettings.enabled ? 'Enabled' : 'Disabled'}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Selected Invoices Actions */}
      {selectedInvoices.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <CheckCircle className="mr-2 h-5 w-5 text-green-600" />
              <span className="font-medium text-gray-900">
                {selectedInvoices.length} invoice{selectedInvoices.length > 1 ? 's' : ''} selected
              </span>
              <span className="ml-2 text-gray-600">
                Total: {formatCurrency(totalSelectedAmount)}
              </span>
            </div>
            <div className="space-x-2">
              <button
                onClick={() => setSelectedInvoices([])}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Clear Selection
              </button>
              <button
                onClick={handlePayInvoices}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700"
              >
                Pay Selected Invoices
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Recent Invoices', icon: DollarSign },
            { id: 'methods', label: 'Payment Methods', icon: CreditCard },
            { id: 'autopay', label: 'AutoPay', icon: RefreshCw },
            { id: 'history', label: 'Payment History', icon: Calendar }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {recentInvoices.map((invoice) => (
            <Card key={invoice.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedInvoices.includes(invoice.id)}
                    onChange={() => toggleInvoiceSelection(invoice.id)}
                    disabled={invoice.status === 'paid'}
                    className="mr-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <h3 className="font-semibold text-gray-900">{invoice.invoiceNumber}</h3>
                    <p className="text-gray-600 text-sm">
                      Issued: {formatDate(invoice.issueDate)} • Due: {formatDate(invoice.dueDate)}
                    </p>
                    <div className="mt-1">
                      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getStatusColor(invoice.status)}`}>
                        {getStatusIcon(invoice.status)}
                        <span className="ml-1 capitalize">{invoice.status}</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <p className="text-2xl font-bold text-gray-900">{formatCurrency(invoice.amount)}</p>
                  <div className="mt-2 space-x-2">
                    {invoice.pdfUrl && (
                      <button className="flex items-center text-blue-600 text-sm hover:text-blue-700">
                        <Download className="mr-1 h-4 w-4" />
                        Download
                      </button>
                    )}
                    {invoice.status === 'pending' && (
                      <button 
                        onClick={() => handlePayInvoices()}
                        className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700"
                      >
                        Pay Now
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-medium text-gray-900">Services</h4>
                <ul className="mt-1 space-y-1">
                  {invoice.services.map((service, index) => (
                    <li key={index} className="text-gray-600 text-sm">• {service}</li>
                  ))}
                </ul>
              </div>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'methods' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Payment Methods</h3>
            <button
              onClick={() => setShowAddPayment(true)}
              className="flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              <Plus className="mr-1 h-4 w-4" />
              Add Payment Method
            </button>
          </div>

          <div className="space-y-4">
            {paymentMethods.map((method) => (
              <Card key={method.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    {method.type === 'credit_card' ? (
                      <CreditCard className="mr-3 h-6 w-6 text-gray-400" />
                    ) : (
                      <Banknote className="mr-3 h-6 w-6 text-gray-400" />
                    )}
                    <div>
                      <p className="font-medium text-gray-900">{method.name}</p>
                      {method.expiryDate && (
                        <p className="text-gray-600 text-sm">Expires {method.expiryDate}</p>
                      )}
                      {method.isDefault && (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-green-800 text-xs font-medium">
                          Default
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {!method.isDefault && (
                      <button className="text-blue-600 text-sm hover:text-blue-700">
                        Set as Default
                      </button>
                    )}
                    <button className="text-gray-600 text-sm hover:text-gray-700">
                      Edit
                    </button>
                    <button className="text-red-600 text-sm hover:text-red-700">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'autopay' && (
        <Card className="p-6">
          <h3 className="mb-6 text-lg font-semibold text-gray-900">AutoPay Settings</h3>
          
          <div className="space-y-6">
            {/* AutoPay Toggle */}
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">Enable AutoPay</h4>
                <p className="text-gray-600 text-sm">
                  Automatically pay your bills before the due date
                </p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  type="checkbox"
                  checked={autoPaySettings.enabled}
                  className="peer sr-only"
                />
                <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
              </label>
            </div>

            {autoPaySettings.enabled && (
              <>
                {/* Payment Method Selection */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Default Payment Method</h4>
                  <select className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                    {paymentMethods.map((method) => (
                      <option key={method.id} value={method.id}>
                        {method.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* AutoPay Timing */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Payment Timing</h4>
                  <div className="flex items-center space-x-4">
                    <label className="text-gray-700 text-sm">Pay</label>
                    <select 
                      value={autoPaySettings.daysBeforeDue}
                      className="rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    >
                      <option value={1}>1 day</option>
                      <option value={3}>3 days</option>
                      <option value={5}>5 days</option>
                      <option value={7}>7 days</option>
                    </select>
                    <label className="text-gray-700 text-sm">before due date</label>
                  </div>
                </div>

                {/* Minimum Balance */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Minimum Balance Protection</h4>
                  <div className="flex items-center space-x-4">
                    <label className="text-gray-700 text-sm">Only pay if account balance stays above</label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <input
                        type="number"
                        value={autoPaySettings.minBalanceRequired}
                        className="pl-8 rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                        placeholder="0.00"
                      />
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      {activeTab === 'history' && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Payment History</h3>
          
          {recentPayments.map((payment) => (
            <Card key={payment.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  {getStatusIcon(payment.status)}
                  <div className="ml-3">
                    <p className="font-medium text-gray-900">
                      {formatCurrency(payment.amount)}
                    </p>
                    <p className="text-gray-600 text-sm">
                      {formatDate(payment.date)} • {payment.method}
                    </p>
                    <p className="text-gray-500 text-xs">
                      Confirmation: {payment.confirmationNumber}
                    </p>
                  </div>
                </div>
                
                <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getStatusColor(payment.status)}`}>
                  <span className="capitalize">{payment.status}</span>
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}