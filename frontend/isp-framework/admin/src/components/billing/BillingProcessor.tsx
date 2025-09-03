/**
 * Billing Processor Management Component
 * Provides interface for managing payment processors and automation
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  CreditCard,
  Settings,
  CheckCircle,
  AlertTriangle,
  Zap,
  DollarSign,
  TrendingUp,
  Activity,
  RefreshCw,
} from 'lucide-react';
import { usePaymentProcessor } from '@dotmac/headless/hooks/usePaymentProcessor';
import { useISPTenant } from '@dotmac/headless/hooks/useISPTenant';
import type { PaymentProcessor } from '@dotmac/headless/types/billing';

interface BillingProcessorProps {
  className?: string;
}

export function BillingProcessor({ className = '' }: BillingProcessorProps) {
  const { tenant, hasPermission } = useISPTenant();
  const {
    processors,
    selectedProcessor,
    recentTransactions,
    isLoading,
    error,
    loadProcessors,
    selectProcessor,
    loadTransactions,
    formatAmount,
  } = usePaymentProcessor({
    autoLoadProcessors: true,
    enableWebhooks: true,
  });

  const [selectedTab, setSelectedTab] = useState<'processors' | 'transactions' | 'automation'>(
    'processors'
  );
  const [automationRules, setAutomationRules] = useState<any[]>([]);

  useEffect(() => {
    if (selectedProcessor) {
      loadTransactions({ processor_id: selectedProcessor.id, limit: 10 });
    }
  }, [selectedProcessor, loadTransactions]);

  if (!hasPermission('billing:read')) {
    return (
      <div className='bg-white rounded-lg border border-gray-200 p-6'>
        <div className='text-center'>
          <AlertTriangle className='w-12 h-12 text-orange-500 mx-auto mb-4' />
          <h3 className='text-lg font-medium text-gray-900 mb-2'>Access Denied</h3>
          <p className='text-gray-600'>You don't have permission to view billing information.</p>
        </div>
      </div>
    );
  }

  const getProcessorStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'text-green-700 bg-green-100';
      case 'TESTING':
        return 'text-blue-700 bg-blue-100';
      case 'INACTIVE':
        return 'text-gray-700 bg-gray-100';
      case 'ERROR':
        return 'text-red-700 bg-red-100';
      default:
        return 'text-gray-700 bg-gray-100';
    }
  };

  const getProcessorIcon = (type: PaymentProcessor['type']) => {
    const iconProps = { className: 'w-6 h-6' };
    switch (type) {
      case 'STRIPE':
        return <CreditCard {...iconProps} style={{ color: '#635BFF' }} />;
      case 'SQUARE':
        return <CreditCard {...iconProps} style={{ color: '#006AFF' }} />;
      case 'PAYPAL':
        return <CreditCard {...iconProps} style={{ color: '#00457C' }} />;
      default:
        return <CreditCard {...iconProps} />;
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='bg-white rounded-lg border border-gray-200 p-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h2 className='text-xl font-semibold text-gray-900'>Payment Processing</h2>
            <p className='text-gray-600 mt-1'>
              Manage payment processors and billing automation for {tenant?.company_name}
            </p>
          </div>
          <div className='flex space-x-3'>
            <button
              onClick={loadProcessors}
              disabled={isLoading}
              className='inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50'
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className='mt-4 p-4 bg-red-50 border border-red-200 rounded-md'>
            <div className='flex items-center'>
              <AlertTriangle className='w-5 h-5 text-red-500 mr-2' />
              <span className='text-red-700 text-sm'>{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className='bg-white rounded-lg border border-gray-200'>
        <div className='border-b border-gray-200'>
          <nav className='flex space-x-8 px-6' aria-label='Tabs'>
            {[
              { id: 'processors', name: 'Processors', icon: CreditCard },
              { id: 'transactions', name: 'Recent Transactions', icon: Activity },
              { id: 'automation', name: 'Automation Rules', icon: Zap },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id as any)}
                className={`${
                  selectedTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
              >
                <tab.icon className='w-4 h-4 mr-2' />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className='p-6'>
          {selectedTab === 'processors' && (
            <div className='space-y-6'>
              {/* Processor Grid */}
              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
                {processors.map((processor) => (
                  <motion.div
                    key={processor.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${
                      selectedProcessor?.id === processor.id
                        ? 'border-primary-500 ring-2 ring-primary-200 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => selectProcessor(processor.id)}
                  >
                    <div className='flex items-center justify-between mb-3'>
                      <div className='flex items-center space-x-3'>
                        {getProcessorIcon(processor.type)}
                        <h3 className='font-medium text-gray-900'>{processor.name}</h3>
                      </div>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getProcessorStatusColor(processor.status)}`}
                      >
                        {processor.status}
                      </span>
                    </div>

                    <div className='space-y-2 text-sm text-gray-600'>
                      <div className='flex justify-between'>
                        <span>Type:</span>
                        <span className='font-medium'>{processor.type}</span>
                      </div>
                      <div className='flex justify-between'>
                        <span>Capabilities:</span>
                        <span className='font-medium'>{processor.capabilities.length}</span>
                      </div>
                      {processor.status === 'ACTIVE' && (
                        <div className='flex items-center text-green-600 mt-2'>
                          <CheckCircle className='w-4 h-4 mr-1' />
                          <span>Ready to process</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>

              {processors.length === 0 && !isLoading && (
                <div className='text-center py-8'>
                  <CreditCard className='w-12 h-12 text-gray-400 mx-auto mb-4' />
                  <h3 className='text-lg font-medium text-gray-900 mb-2'>No Payment Processors</h3>
                  <p className='text-gray-600 mb-4'>
                    Set up a payment processor to start accepting payments.
                  </p>
                  <button className='inline-flex items-center px-4 py-2 bg-primary-600 border border-transparent rounded-md font-medium text-white hover:bg-primary-700'>
                    <Settings className='w-4 h-4 mr-2' />
                    Configure Processor
                  </button>
                </div>
              )}
            </div>
          )}

          {selectedTab === 'transactions' && (
            <div className='space-y-4'>
              {recentTransactions.length > 0 ? (
                <div className='overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg'>
                  <table className='min-w-full divide-y divide-gray-300'>
                    <thead className='bg-gray-50'>
                      <tr>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide'>
                          Transaction
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide'>
                          Amount
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide'>
                          Status
                        </th>
                        <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide'>
                          Date
                        </th>
                      </tr>
                    </thead>
                    <tbody className='bg-white divide-y divide-gray-200'>
                      {recentTransactions.map((transaction) => (
                        <tr key={transaction.id} className='hover:bg-gray-50'>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            <div className='text-sm font-medium text-gray-900'>
                              {transaction.id.slice(0, 8)}...
                            </div>
                            <div className='text-sm text-gray-500'>
                              {transaction.payment_method.type}
                            </div>
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            <div className='text-sm text-gray-900 font-medium'>
                              {formatAmount(transaction.amount, transaction.currency)}
                            </div>
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap'>
                            <span
                              className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                transaction.status === 'SUCCEEDED'
                                  ? 'bg-green-100 text-green-800'
                                  : transaction.status === 'FAILED'
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {transaction.status}
                            </span>
                          </td>
                          <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-500'>
                            {new Date(transaction.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className='text-center py-8'>
                  <Activity className='w-12 h-12 text-gray-400 mx-auto mb-4' />
                  <h3 className='text-lg font-medium text-gray-900 mb-2'>No Recent Transactions</h3>
                  <p className='text-gray-600'>
                    Transactions will appear here once you start processing payments.
                  </p>
                </div>
              )}
            </div>
          )}

          {selectedTab === 'automation' && (
            <div className='space-y-6'>
              <div className='bg-blue-50 border border-blue-200 rounded-lg p-4'>
                <div className='flex items-center'>
                  <Zap className='w-5 h-5 text-blue-500 mr-2' />
                  <h3 className='text-sm font-medium text-blue-800'>Billing Automation</h3>
                </div>
                <p className='text-blue-700 text-sm mt-1'>
                  Automate recurring billing, failed payment recovery, and dunning management.
                </p>
              </div>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                <div className='border border-gray-200 rounded-lg p-4'>
                  <div className='flex items-center justify-between mb-3'>
                    <h4 className='font-medium text-gray-900'>Recurring Billing</h4>
                    <CheckCircle className='w-5 h-5 text-green-500' />
                  </div>
                  <p className='text-gray-600 text-sm mb-3'>
                    Automatically charge customers for recurring subscriptions
                  </p>
                  <div className='flex items-center text-sm text-gray-500'>
                    <TrendingUp className='w-4 h-4 mr-1' />
                    <span>Active for 1,250+ customers</span>
                  </div>
                </div>

                <div className='border border-gray-200 rounded-lg p-4'>
                  <div className='flex items-center justify-between mb-3'>
                    <h4 className='font-medium text-gray-900'>Failed Payment Recovery</h4>
                    <AlertTriangle className='w-5 h-5 text-orange-500' />
                  </div>
                  <p className='text-gray-600 text-sm mb-3'>
                    Automatically retry failed payments and notify customers
                  </p>
                  <div className='flex items-center text-sm text-gray-500'>
                    <RefreshCw className='w-4 h-4 mr-1' />
                    <span>85% recovery rate</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
